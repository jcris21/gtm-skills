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
    parser.add_argument("--lead-name", required=True, help='e.g. "Christian Cobian"')
    parser.add_argument(
        "--session",
        action="append",
        help="Path to a specific session .jsonl file. Repeatable. Defaults to all sessions in this project's transcript dir.",
    )
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    if args.session:
        session_paths = [Path(s) for s in args.session]
    else:
        transcript_dir = _project_transcript_dir()
        session_paths = sorted(transcript_dir.glob("*.jsonl"))

    if not session_paths:
        print("No session transcripts found to scan.", file=sys.stderr)
        sys.exit(1)

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
