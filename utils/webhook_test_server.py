"""
Minimal local FastAPI receiver to capture the real Unipile webhook payload
shape before building the n8n automation (see Documents/n8n_Reply_Handler_Automation.md).

Not production code — logs raw payloads to stdout and to a local JSONL file
so we can inspect the exact field names Unipile sends for `message_received`.

Usage:
    uvicorn utils.webhook_test_server:app --reload --port 8000

Then expose it publicly with ngrok:
    ngrok http 8000

Register the resulting https://*.ngrok-free.app/webhook/unipile URL as the
Unipile webhook target, send a test LinkedIn DM to the connected account,
and watch this terminal / captured_payloads.jsonl for the incoming event.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request

app = FastAPI()

CAPTURE_FILE = Path(__file__).resolve().parent.parent / "captured_payloads.jsonl"


@app.post("/webhook/unipile")
async def receive_unipile_webhook(request: Request) -> dict:
    body = await request.json()
    record = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": dict(request.headers),
        "body": body,
    }
    print(json.dumps(record, indent=2))
    with CAPTURE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {"status": "received"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
