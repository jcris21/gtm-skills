"""
Unipile API client for LinkedIn DM sending.
Used by the linkedin-dm skill to look up connected accounts, resolve a
prospect's LinkedIn profile to a Unipile provider id, and send a message.

Usage:
    python utils/unipile.py accounts
    python utils/unipile.py find-profile --account-id <id> --identifier https://www.linkedin.com/in/someone/
    python utils/unipile.py send-dm --account-id <id> --recipient <provider-id-or-identifier> --text "..."
    python utils/unipile.py invite --account-id <id> --provider-id <id> --message "..."

Requires:
    - UNIPILE_API_KEY and UNIPILE_DSN in .env (DSN is the account-specific
      base URL Unipile assigns, e.g. https://api60.unipile.com:19028)
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
API_KEY = os.getenv("UNIPILE_API_KEY")
DSN = os.getenv("UNIPILE_DSN")


def _require_config() -> None:
    if not API_KEY:
        print("Error: UNIPILE_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)
    if not DSN:
        print("Error: UNIPILE_DSN not found in .env", file=sys.stderr)
        sys.exit(1)


def _headers() -> dict:
    return {"X-API-KEY": API_KEY, "accept": "application/json"}


def list_accounts() -> dict:
    _require_config()
    resp = requests.get(f"{DSN}/api/v1/accounts", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_profile(account_id: str, identifier: str) -> dict:
    """Resolve a LinkedIn public URL or public id to Unipile's provider record."""
    _require_config()
    resp = requests.get(
        f"{DSN}/api/v1/users/{identifier}",
        headers=_headers(),
        params={"account_id": account_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_dm(account_id: str, recipient: str, text: str) -> dict:
    """Start (or reuse) a chat with `recipient` and send `text`.

    `recipient` is the Unipile provider id returned by find_profile, or a
    LinkedIn public identifier Unipile can resolve directly. Only works for
    1st-degree connections; use `send_invite` for everyone else.
    """
    _require_config()
    headers = {**_headers(), "Content-Type": "application/json"}
    payload = {
        "account_id": account_id,
        "attendees_ids": [recipient],
        "text": text,
    }
    resp = requests.post(f"{DSN}/api/v1/chats", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_chats(account_id: str, limit: int = 20) -> dict:
    """List recent chats for an account — used to spot-check which threads have an inbound reply."""
    _require_config()
    resp = requests.get(
        f"{DSN}/api/v1/chats",
        headers=_headers(),
        params={"account_id": account_id, "limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_chat_messages(chat_id: str, limit: int = 20) -> dict:
    """Fetch a chat's messages — used by the no-reply follow-up gate to check if a reply
    (any message with is_sender == False since the last outbound touch) has arrived."""
    _require_config()
    resp = requests.get(
        f"{DSN}/api/v1/chats/{chat_id}/messages",
        headers=_headers(),
        params={"limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def has_unreplied_inbound(chat_id: str, since_iso: str | None = None) -> bool:
    """True if the chat has any inbound message (not sent by our account) — optionally
    only counting messages after `since_iso` (the last outbound touch's timestamp). This is
    the reply-detection primitive the no-reply follow-up gate
    (LinkedIn_DM_NoReply_Activation_Strategy.md §4) needs before sending a follow-up: if this
    returns True, do NOT send the follow-up.

    NOTE: verified against a real Unipile response that `is_sender` comes back as an int
    (0/1), not a JSON boolean, despite the field being documented/treated as boolean
    elsewhere in this project (e.g. the webhook payload in
    Documents/n8n_Reply_Handler_Automation.md §2). `is msg.get("is_sender") is False` would
    silently never match `0` — comparing with `not` handles both 0 and false.
    """
    data = get_chat_messages(chat_id)
    for msg in data.get("items", []):
        is_sender = msg.get("is_sender")
        if is_sender is not None and not is_sender:
            if since_iso is None or msg.get("timestamp", "") > since_iso:
                return True
    return False


def send_invite(account_id: str, provider_id: str, message: str | None = None) -> dict:
    """Send a LinkedIn connection invitation to a non-1st-degree profile.

    `provider_id` is the Unipile provider id returned by find_profile.
    `message` is the connection note, max 300 characters (LinkedIn's limit).
    """
    _require_config()
    if message and len(message) > 300:
        print(f"Error: message is {len(message)} chars, max 300", file=sys.stderr)
        sys.exit(1)
    headers = {**_headers(), "Content-Type": "application/json"}
    payload: dict = {"account_id": account_id, "provider_id": provider_id}
    if message:
        payload["message"] = message
    resp = requests.post(f"{DSN}/api/v1/users/invite", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Unipile LinkedIn DM CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("accounts", help="List connected Unipile accounts")

    fp = sub.add_parser("find-profile", help="Resolve a LinkedIn identifier to a Unipile provider id")
    fp.add_argument("--account-id", required=True, help="Unipile account id (LinkedIn account)")
    fp.add_argument("--identifier", required=True, help="LinkedIn profile URL or public id")

    sd = sub.add_parser("send-dm", help="Send a LinkedIn direct message (1st-degree only)")
    sd.add_argument("--account-id", required=True, help="Unipile account id (LinkedIn account)")
    sd.add_argument("--recipient", required=True, help="Recipient provider id or LinkedIn identifier")
    sd.add_argument("--text", required=True, help="Message body")

    inv = sub.add_parser("invite", help="Send a LinkedIn connection invitation (non-1st-degree)")
    inv.add_argument("--account-id", required=True, help="Unipile account id (LinkedIn account)")
    inv.add_argument("--provider-id", required=True, help="Recipient's Unipile provider id (from find-profile)")
    inv.add_argument("--message", default=None, help="Connection note, max 300 characters")

    lc = sub.add_parser("list-chats", help="List recent chats for an account")
    lc.add_argument("--account-id", required=True)
    lc.add_argument("--limit", type=int, default=20)

    gm = sub.add_parser("get-messages", help="Fetch a chat's messages")
    gm.add_argument("--chat-id", required=True)
    gm.add_argument("--limit", type=int, default=20)

    hr = sub.add_parser("has-reply", help="Check if a chat has an inbound reply (no-reply follow-up gate)")
    hr.add_argument("--chat-id", required=True)
    hr.add_argument("--since", default=None, help="ISO timestamp — only count replies after this")

    args = parser.parse_args()

    if args.command == "accounts":
        print(json.dumps(list_accounts(), indent=2))
    elif args.command == "find-profile":
        print(json.dumps(find_profile(args.account_id, args.identifier), indent=2))
    elif args.command == "send-dm":
        print(json.dumps(send_dm(args.account_id, args.recipient, args.text), indent=2))
    elif args.command == "invite":
        print(json.dumps(send_invite(args.account_id, args.provider_id, args.message), indent=2))
    elif args.command == "list-chats":
        print(json.dumps(list_chats(args.account_id, args.limit), indent=2))
    elif args.command == "get-messages":
        print(json.dumps(get_chat_messages(args.chat_id, args.limit), indent=2))
    elif args.command == "has-reply":
        print(json.dumps({"has_unreplied_inbound": has_unreplied_inbound(args.chat_id, args.since)}, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
