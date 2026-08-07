"""
Append-only token usage ledger for the outbound pipeline.

Every programmatic call to an LLM (signal-builder, creative-variable,
email-writer, linkedin-dm, reply-handler — when run via a script/Agent SDK
against the Anthropic API rather than interactively in Claude Code chat)
should log its usage here, keyed by lead. This is the source of truth that
`token_report.py` aggregates into a per-lead rollup for Attio and the
pipeline tracker.

Does not talk to Attio directly — Attio writes happen via the MCP tools the
skills already use (`update-record` on the Person object), reading the
rollup this module/`token_report.py` produces.

Usage as a CLI (mainly for manual testing):
    python utils/token_ledger.py log --lead-id rec_abc123 --skill email-writer \
        --model claude-sonnet-5 --input-tokens 1200 --output-tokens 340

Usage as a library (the normal path, from a pipeline runner script):
    from utils.token_ledger import log_usage
    response = client.messages.create(...)
    log_usage(
        lead_id=person_record_id,
        skill="email-writer",
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
        cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
    )
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = PROJECT_ROOT / "logs" / "token_ledger.jsonl"


@dataclass(frozen=True)
class UsageRecord:
    timestamp: str
    lead_id: str
    skill: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


def log_usage(
    lead_id: str,
    skill: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    ledger_path: Path = LEDGER_PATH,
) -> UsageRecord:
    """Append one usage record to the ledger. Never overwrites — one row per call."""
    record = UsageRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        lead_id=lead_id,
        skill=skill,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record)) + "\n")
    return record


def read_ledger(lead_id: str | None = None, ledger_path: Path = LEDGER_PATH) -> list[dict]:
    """Read all records, optionally filtered to one lead. Used by token_report.py."""
    if not ledger_path.exists():
        return []
    records = []
    with ledger_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if lead_id is None or record.get("lead_id") == lead_id:
                records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Log LLM token usage for a lead.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    log_parser = subparsers.add_parser("log", help="Append a usage record")
    log_parser.add_argument("--lead-id", required=True)
    log_parser.add_argument("--skill", required=True)
    log_parser.add_argument("--model", required=True)
    log_parser.add_argument("--input-tokens", type=int, required=True)
    log_parser.add_argument("--output-tokens", type=int, required=True)
    log_parser.add_argument("--cache-creation-input-tokens", type=int, default=0)
    log_parser.add_argument("--cache-read-input-tokens", type=int, default=0)

    args = parser.parse_args()

    if args.command == "log":
        record = log_usage(
            lead_id=args.lead_id,
            skill=args.skill,
            model=args.model,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            cache_creation_input_tokens=args.cache_creation_input_tokens,
            cache_read_input_tokens=args.cache_read_input_tokens,
        )
        print(json.dumps(asdict(record), indent=2))


if __name__ == "__main__":
    main()
