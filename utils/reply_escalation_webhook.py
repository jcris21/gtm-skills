"""
Hand off an already-classified reply to the n8n Slack-HITL escalation flow
(Documents/n8n_Reply_Handler_Automation.md Node 6/10) when it needs a human.

Classification itself is NOT done here — it's done by `/reply-handler`
running interactively in Claude Code chat (see reply-handler/skill.md's
"Output format" block). This script's only job is: given that already-
classified result, POST it to the n8n webhook if and only if `escalate` is
true. Non-escalated replies never call this script's webhook path — they
auto-send per Documents/HITL_Send_Approval_Design.md §2.

Usage:
    python utils/reply_escalation_webhook.py \
        --lead-id rec_abc123 --name "Jane Doe" --company "Acme Co" \
        --reply-text "..." --classification OBJECTION --confidence Low \
        --draft-response "..." --escalate true --escalate-reason "confidence below 80%"

    # Or from a JSON file matching reply-handler's Output format:
    python utils/reply_escalation_webhook.py --from-json classified_reply.json

Requires:
    - N8N_ESCALATION_WEBHOOK_URL in .env
    - pip install requests python-dotenv
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")
WEBHOOK_URL = os.getenv("N8N_ESCALATION_WEBHOOK_URL")


def _require_config() -> None:
    if not WEBHOOK_URL:
        print("Error: N8N_ESCALATION_WEBHOOK_URL not found in .env", file=sys.stderr)
        sys.exit(1)


def notify_escalation(
    lead_id: str,
    name: str,
    company: str,
    reply_text: str,
    classification: str,
    confidence: str,
    draft_response: str,
    escalate: bool,
    escalate_reason: str | None = None,
    webhook_url: str | None = None,
) -> dict | None:
    """POST to the n8n escalation webhook only when escalate is True.

    Returns the webhook response JSON, or None if escalate was False (no
    call made — non-escalated replies auto-send, they never reach n8n
    through this path).
    """
    if not escalate:
        return None

    url = webhook_url or WEBHOOK_URL
    if not url:
        _require_config()

    payload = {
        "lead_id": lead_id,
        "name": name,
        "company": company,
        "reply_text": reply_text,
        "classification": classification,
        "confidence": confidence,
        "draft_response": draft_response,
        "escalate": True,
        "escalate_reason": escalate_reason,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json() if resp.content else {"status": "sent", "http_status": resp.status_code}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="POST an already-classified escalated reply to the n8n Slack-HITL webhook."
    )
    parser.add_argument("--from-json", help="Path to a JSON file with all fields below (overrides individual flags)")
    parser.add_argument("--lead-id")
    parser.add_argument("--name")
    parser.add_argument("--company")
    parser.add_argument("--reply-text")
    parser.add_argument("--classification", choices=[
        "INTERESTED", "OBJECTION", "NOT_NOW", "NOT_INTERESTED", "QUESTION", "OUT_OF_OFFICE",
    ])
    parser.add_argument("--confidence", choices=["High", "Medium", "Low"])
    parser.add_argument("--draft-response")
    parser.add_argument("--escalate", choices=["true", "false"])
    parser.add_argument("--escalate-reason", default=None)
    parser.add_argument("--webhook-url", default=None, help="Override N8N_ESCALATION_WEBHOOK_URL (e.g. for local test server)")
    args = parser.parse_args()

    if args.from_json:
        with open(args.from_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        required = ["lead_id", "name", "company", "reply_text", "classification", "confidence", "draft_response", "escalate"]
        missing = [f"--{r.replace('_', '-')}" for r in required if getattr(args, r) is None]
        if missing:
            print(f"Error: missing required flags: {', '.join(missing)}", file=sys.stderr)
            sys.exit(1)
        data = {
            "lead_id": args.lead_id,
            "name": args.name,
            "company": args.company,
            "reply_text": args.reply_text,
            "classification": args.classification,
            "confidence": args.confidence,
            "draft_response": args.draft_response,
            "escalate": args.escalate == "true",
            "escalate_reason": args.escalate_reason,
        }

    result = notify_escalation(
        lead_id=data["lead_id"],
        name=data["name"],
        company=data["company"],
        reply_text=data["reply_text"],
        classification=data["classification"],
        confidence=data["confidence"],
        draft_response=data["draft_response"],
        escalate=bool(data["escalate"]),
        escalate_reason=data.get("escalate_reason"),
        webhook_url=args.webhook_url,
    )

    if result is None:
        print(json.dumps({"escalated": False, "webhook_called": False, "note": "Not escalated — auto-send path, no webhook call made."}, indent=2))
    else:
        print(json.dumps({"escalated": True, "webhook_called": True, "response": result}, indent=2))


if __name__ == "__main__":
    main()
