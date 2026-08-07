"""
Aggregate utils/token_ledger.py's raw usage records into a per-lead rollup,
priced against context/pricing/model-pricing.json.

This is the only place cost gets computed — skills and token_ledger.py never
touch pricing directly, so a price change or new model only means editing
model-pricing.json, not this script's logic.

Usage:
    python utils/token_report.py --lead-id rec_abc123
    python utils/token_report.py --lead-id rec_abc123 --format json

Output feeds two places, both written by whatever calls this (the pipeline
runner or an operator), not by this script itself:
  - Attio Person attributes `llm_input_tokens_total` / `llm_output_tokens_total`
    / `llm_cost_usd_total` (context/crm/attio-schema.md), via the `update-record`
    MCP tool `/attio-crm` already uses.
  - The pipeline tracker's Input Tokens / Output Tokens / Costo LLM (USD) columns
    (Documents/Outbound_Pipeline_Tracker.md) — only when the pipeline actually
    ran programmatically; leave those columns as N/A for manually-run leads,
    since this report has nothing to aggregate for them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from token_ledger import read_ledger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRICING_PATH = PROJECT_ROOT / "context" / "pricing" / "model-pricing.json"


def load_pricing(pricing_path: Path = PRICING_PATH) -> dict:
    if not pricing_path.exists():
        print(f"Error: pricing file not found at {pricing_path}", file=sys.stderr)
        sys.exit(1)
    with pricing_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_cost(model: str, input_tokens: int, output_tokens: int,
                  cache_creation_input_tokens: int, cache_read_input_tokens: int,
                  pricing: dict) -> float:
    rates = pricing.get("models", {}).get(model)
    if rates is None:
        print(
            f"Warning: no pricing entry for model '{model}' in {PRICING_PATH.name} "
            f"— add it before trusting this cost total.",
            file=sys.stderr,
        )
        return 0.0
    # token_ledger.py doesn't yet distinguish 5-minute vs 1-hour cache writes,
    # so cache_creation_input_tokens is priced at the 5-minute rate (the common
    # case) until the ledger captures which duration was used.
    return (
        input_tokens / 1_000_000 * rates["input_per_million"]
        + output_tokens / 1_000_000 * rates["output_per_million"]
        + cache_creation_input_tokens / 1_000_000 * rates["cache_write_5m_per_million"]
        + cache_read_input_tokens / 1_000_000 * rates["cache_read_per_million"]
    )


def build_report(lead_id: str) -> dict:
    pricing = load_pricing()
    records = read_ledger(lead_id=lead_id)

    if pricing.get("_verified") is False:
        print(
            f"Warning: {PRICING_PATH.name} is marked unverified — confirm rates "
            f"against https://www.anthropic.com/pricing before treating this cost as real.",
            file=sys.stderr,
        )

    total_input = 0
    total_output = 0
    total_cost = 0.0
    by_skill: dict = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0})

    for r in records:
        cost = compute_cost(
            r["model"], r["input_tokens"], r["output_tokens"],
            r.get("cache_creation_input_tokens", 0), r.get("cache_read_input_tokens", 0),
            pricing,
        )
        total_input += r["input_tokens"]
        total_output += r["output_tokens"]
        total_cost += cost
        by_skill[r["skill"]]["input_tokens"] += r["input_tokens"]
        by_skill[r["skill"]]["output_tokens"] += r["output_tokens"]
        by_skill[r["skill"]]["cost_usd"] += cost
        by_skill[r["skill"]]["calls"] += 1

    return {
        "lead_id": lead_id,
        "call_count": len(records),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 6),
        "by_skill": {k: {**v, "cost_usd": round(v["cost_usd"], 6)} for k, v in by_skill.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-lead token usage and cost rollup.")
    parser.add_argument("--lead-id", required=True)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    report = build_report(args.lead_id)

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return

    if report["call_count"] == 0:
        print(f"No usage records found for lead_id={args.lead_id!r} in the ledger.")
        return

    print(f"Lead: {report['lead_id']}")
    print(f"Calls logged: {report['call_count']}")
    print(f"Total input tokens:  {report['total_input_tokens']:,}")
    print(f"Total output tokens: {report['total_output_tokens']:,}")
    print(f"Total cost (USD):    ${report['total_cost_usd']:.4f}")
    print("\nBy skill:")
    for skill, data in report["by_skill"].items():
        print(
            f"  {skill:<20} calls={data['calls']:<3} "
            f"in={data['input_tokens']:,} out={data['output_tokens']:,} "
            f"cost=${data['cost_usd']:.4f}"
        )


if __name__ == "__main__":
    main()
