"""
Estimate token usage and cost per lead from Claude Code's own local session
transcripts (~/.claude/projects/<project>/<session-id>.jsonl), instead of
calling the Anthropic API programmatically.

Rationale: this project's token_ledger.py only fills up when a skill runs
programmatically against the Anthropic API (a separate, billed call). For
work done interactively inside Claude Code, no such call happens — but the
session transcript already records per-turn `usage` (input/output/cache
tokens, and cache_creation split into 1h vs 5m) because that's what Claude
Code itself uses to show cost. This script re-reads that same data and
attributes it to a lead by proximity to mentions of the lead's name, so a
per-lead estimate is possible without spending anything extra.

This is an ESTIMATE, not a ledger entry: transcripts aren't segmented by
lead, so attribution works by scanning each user message for the lead name
and attributing every assistant turn's usage between one mention and the
next (or the following unrelated mention) to that lead. Turns before the
first mention or after the topic clearly moves on are not counted.

Usage:
    python utils/session_token_estimator.py --lead-name "Christian Cobian"
    python utils/session_token_estimator.py --lead-name "Christian Cobian" --session <path.jsonl>
    python utils/session_token_estimator.py --lead-name "Christian Cobian" --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRICING_PATH = PROJECT_ROOT / "context" / "pricing" / "model-pricing.json"
TRACKER_PATH = PROJECT_ROOT / "Documents" / "Outbound_Pipeline_Tracker.md"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "Documents" / "Decisions" / "TokenEstimates.md"
TRACKER_TABLE_HEADER = "| Prospecto |"
SYNTHETIC_PROSPECT_MARKERS = ("Jane Doe", "*(fila por prospecto")

# Claude Code stores transcripts under a directory named after the project
# path with path separators replaced by dashes.
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def _project_transcript_dir() -> Path:
    slug = "".join(
        c if c.isalnum() else "-" for c in str(PROJECT_ROOT)
    )
    candidate = CLAUDE_PROJECTS_DIR / slug
    if candidate.is_dir():
        return candidate
    # Fall back to a fuzzy match in case Claude Code's slug rule differs
    # slightly (e.g. drive letter casing) from the naive transform above.
    matches = [
        p for p in CLAUDE_PROJECTS_DIR.iterdir()
        if p.is_dir() and PROJECT_ROOT.name.replace(" ", "-") in p.name
    ]
    if matches:
        return matches[0]
    raise FileNotFoundError(
        f"Could not find a Claude Code transcript directory for {PROJECT_ROOT} "
        f"under {CLAUDE_PROJECTS_DIR}. Pass --session explicitly."
    )


@dataclass
class Turn:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    cache_write_1h: int
    cache_write_5m: int


@dataclass
class LeadEstimate:
    lead_name: str
    mention_count: int = 0
    turns: list = field(default_factory=list)

    def totals(self) -> dict:
        return {
            "input_tokens": sum(t.input_tokens for t in self.turns),
            "output_tokens": sum(t.output_tokens for t in self.turns),
            "cache_creation_input_tokens": sum(t.cache_creation_input_tokens for t in self.turns),
            "cache_read_input_tokens": sum(t.cache_read_input_tokens for t in self.turns),
            "cache_write_1h": sum(t.cache_write_1h for t in self.turns),
            "cache_write_5m": sum(t.cache_write_5m for t in self.turns),
        }


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def _iter_turns_with_mentions(session_path: Path, lead_name: str):
    """
    Walk a transcript in order, yielding (role, has_mention, Turn|None) per
    line. has_mention is True on the line where the lead's name appears
    (user or assistant text); Turn is populated only on assistant lines
    carrying a unique (deduped) `usage` block.
    """
    lead_lower = lead_name.lower()
    seen_message_ids = set()

    with session_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = obj.get("message", {})
            role = msg.get("role")
            text = _extract_text(msg.get("content"))
            has_mention = lead_lower in text.lower()

            turn = None
            if obj.get("type") == "assistant":
                mid = msg.get("id")
                usage = msg.get("usage")
                # Same API response can appear across multiple transcript
                # lines (one per content block) — count it once.
                if usage and mid and mid not in seen_message_ids:
                    seen_message_ids.add(mid)
                    cache_creation = usage.get("cache_creation") or {}
                    turn = Turn(
                        timestamp=obj.get("timestamp", ""),
                        model=msg.get("model", "unknown"),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
                        cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
                        cache_write_1h=cache_creation.get("ephemeral_1h_input_tokens", 0),
                        cache_write_5m=cache_creation.get("ephemeral_5m_input_tokens", 0),
                    )

            yield role, has_mention, turn


def estimate_for_lead(lead_name: str, session_paths: list) -> LeadEstimate:
    """
    Attribution rule: track an "active lead" flag. It turns on at any line
    (user or assistant) that mentions lead_name, and turns off at the next
    user message that does NOT mention lead_name (i.e. the conversation
    moved to something else). All assistant usage turns seen while active
    are attributed to this lead. This undercounts tool-only turns far from
    any textual mention, and overcounts if unrelated turns happen between
    two mentions without an intervening topic-change message — it's an
    estimate, not a ledger.
    """
    estimate = LeadEstimate(lead_name=lead_name)
    for session_path in session_paths:
        active = False
        for role, has_mention, turn in _iter_turns_with_mentions(session_path, lead_name):
            if has_mention:
                if not active:
                    estimate.mention_count += 1
                active = True
            elif role == "user" and not has_mention:
                active = False

            if active and turn is not None:
                estimate.turns.append(turn)
    return estimate


def parse_pipeline_prospects(tracker_path: Path = TRACKER_PATH) -> list:
    """
    Extract prospect names from the "Tabla maestra" in Outbound_Pipeline_Tracker.md,
    excluding rows that are documentation examples rather than real pipeline runs
    (the synthetic "Jane Doe" example row and the empty template placeholder row).
    """
    prospects = []
    in_table = False
    with tracker_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(TRACKER_TABLE_HEADER):
                in_table = True
                continue
            if not in_table:
                continue
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < 2:
                continue
            name = cells[1]
            if not name or set(name) <= {"-"}:
                continue
            if any(marker in name for marker in SYNTHETIC_PROSPECT_MARKERS):
                continue
            prospects.append(name)
    return prospects


def build_multi_prospect_report(prospect_names: list, session_paths: list) -> list:
    return [build_report(name, session_paths) for name in prospect_names]


def write_markdown_report(reports: list, output_path: Path = DEFAULT_REPORT_PATH) -> None:
    lines = [
        "# Token Estimates — Pipeline Prospects",
        "",
        (
            "Estimacion por proximidad de mencion en las transcripciones locales de "
            "Claude Code (ver `session_token_estimator.py`). Incluye solo prospectos "
            "que pasaron por una ejecucion real del pipeline (excluye filas de ejemplo "
            "sintetico y plantilla vacia de `Outbound_Pipeline_Tracker.md`). No es un "
            "ledger exacto — ver nota al pie de cada script/decision relacionada."
        ),
        "",
        "| Prospecto | Mentions | Input Tokens | Output Tokens | Cache Write 1h | Cache Write 5m | Cache Read | Costo Estimado (USD) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for report in reports:
        lines.append(
            "| {lead_name} | {mention_count} | {input_tokens:,} | {output_tokens:,} "
            "| {cache_write_1h:,} | {cache_write_5m:,} | {cache_read_input_tokens:,} "
            "| ${estimated_cost_usd:.4f} |".format(**report)
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_pricing(pricing_path: Path = PRICING_PATH) -> dict:
    if not pricing_path.exists():
        print(f"Error: pricing file not found at {pricing_path}", file=sys.stderr)
        sys.exit(1)
    with pricing_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_cost(turn: Turn, pricing: dict) -> float:
    rates = pricing.get("models", {}).get(turn.model)
    if rates is None:
        return 0.0
    return (
        turn.input_tokens / 1_000_000 * rates["input_per_million"]
        + turn.output_tokens / 1_000_000 * rates["output_per_million"]
        + turn.cache_write_5m / 1_000_000 * rates["cache_write_5m_per_million"]
        + turn.cache_write_1h / 1_000_000 * rates["cache_write_1h_per_million"]
        + turn.cache_read_input_tokens / 1_000_000 * rates["cache_read_per_million"]
    )


def build_report(lead_name: str, session_paths: list) -> dict:
    pricing = load_pricing()
    estimate = estimate_for_lead(lead_name, session_paths)

    total_cost = sum(compute_cost(t, pricing) for t in estimate.turns)
    unpriced_models = sorted({
        t.model for t in estimate.turns
        if t.model not in pricing.get("models", {})
    })

    totals = estimate.totals()
    return {
        "lead_name": lead_name,
        "sessions_scanned": [str(p) for p in session_paths],
        "mention_count": estimate.mention_count,
        "assistant_turns_attributed": len(estimate.turns),
        **totals,
        "estimated_cost_usd": round(total_cost, 6),
        "unpriced_models": unpriced_models,
        "note": (
            "Estimate only — attribution is by proximity to name mentions in "
            "the transcript, not an explicit per-lead log. See docstring for "
            "the attribution rule."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate per-lead token usage/cost from local Claude Code session transcripts."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lead-name", help='e.g. "Christian Cobian"')
    group.add_argument(
        "--all-pipeline-prospects",
        action="store_true",
        help=(
            "Estimate every prospect that went through a real pipeline run, read from "
            f"{TRACKER_PATH.relative_to(PROJECT_ROOT)} (excludes synthetic/template rows), "
            f"and write a markdown report to --output (default {DEFAULT_REPORT_PATH.relative_to(PROJECT_ROOT)})."
        ),
    )
    parser.add_argument(
        "--session",
        action="append",
        help="Path to a specific session .jsonl file. Repeatable. Defaults to all sessions in this project's transcript dir.",
    )
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Only used with --all-pipeline-prospects: path to write the markdown report.",
    )
    args = parser.parse_args()

    if args.session:
        session_paths = [Path(s) for s in args.session]
    else:
        transcript_dir = _project_transcript_dir()
        session_paths = sorted(transcript_dir.glob("*.jsonl"))

    if not session_paths:
        print("No session transcripts found to scan.", file=sys.stderr)
        sys.exit(1)

    if args.all_pipeline_prospects:
        prospects = parse_pipeline_prospects()
        if not prospects:
            print(f"No pipeline prospects found in {TRACKER_PATH}.", file=sys.stderr)
            sys.exit(1)
        reports = build_multi_prospect_report(prospects, session_paths)
        write_markdown_report(reports, args.output)
        print(f"Wrote token estimates for {len(reports)} prospect(s) to {args.output}")
        if args.format == "json":
            print(json.dumps(reports, indent=2))
        return

    report = build_report(args.lead_name, session_paths)

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return

    print(f"Lead: {report['lead_name']}")
    print(f"Sessions scanned: {len(report['sessions_scanned'])}")
    print(f"Mentions found: {report['mention_count']}")
    print(f"Assistant turns attributed: {report['assistant_turns_attributed']}")
    if report["assistant_turns_attributed"] == 0:
        print("\nNo turns attributed — the lead name may not appear in any scanned transcript.")
        return
    print(f"Input tokens:          {report['input_tokens']:,}")
    print(f"Output tokens:         {report['output_tokens']:,}")
    print(f"Cache write (1h):      {report['cache_write_1h']:,}")
    print(f"Cache write (5m):      {report['cache_write_5m']:,}")
    print(f"Cache read:            {report['cache_read_input_tokens']:,}")
    print(f"Estimated cost (USD):  ${report['estimated_cost_usd']:.4f}")
    if report["unpriced_models"]:
        print(f"\nWarning: no pricing entry for model(s) {report['unpriced_models']} — those turns cost $0 in this estimate.")
    print(f"\nNote: {report['note']}")


if __name__ == "__main__":
    main()
