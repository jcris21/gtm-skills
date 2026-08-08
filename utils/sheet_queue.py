"""
Google Sheets queue for the Message-1 send gate
(Documents/HITL_Send_Approval_Design.md §3), consolidated with the lead
metadata columns from Documents/Outbound_Pipeline_Tracker.md Fases 1-3 so a
reviewer sees full context (score, signal type, persona, angle, QA pass) in
the same row they approve/edit/reject.

`email-writer`/`linkedin-dm` Step 7 upsert a drafted Message 1 here instead
of asking for authorization in chat. One row = one lead, both channels can
land in the same row (`canal_envio` becomes "Both" once both are filled) —
each skill only fills its own channel's draft/editado columns and shared
metadata fields, so running both skills for the same lead_id converges on
one row rather than creating two. A human reviews/edits/approves rows in
the Sheet; n8n's manual-button flow (design doc §3.3) later reads approved,
unsent rows and sends them via Unipile/email, then marks `enviado`.

This script only handles the write side (upsert_draft, batch_insert_leads)
and the read side (list_approved_unsent, mark_sent) used by that n8n flow —
it does not send anything itself.

Usage:
    python utils/sheet_queue.py upsert-draft \
        --lead-id rec_abc123 --canal linkedin --draft "..." \
        --metadata-json '{"prospecto": "Jane Doe", "empresa": "Acme Inc", "score": 8, ...}' \
        --timestamp-draft 2026-08-07T12:00:00Z

    python utils/sheet_queue.py batch-insert --from-json leads.json

    python utils/sheet_queue.py list-approved

    python utils/sheet_queue.py mark-sent --row 5

Requires:
    - GOOGLE_SHEETS_CREDENTIALS_JSON (path to a service-account key file)
      and GOOGLE_SHEETS_SPREADSHEET_ID in .env
    - pip install gspread python-dotenv

Sheet columns, in order (metadata columns follow Outbound_Pipeline_Tracker.md's
Fase 1-3 vocabulary/labels exactly — see its "Leyenda de labels" section):
    lead_id | prospecto | empresa | score | signal_type | situacion |
    email_disponible | linkedin_disponible | linkedin_url | variable_personalizacion |
    canal_envio | patron | persona_matcheada | historia_prueba | angulo | qa_pass |
    draft_email | editado_email | draft_linkedin | editado_linkedin |
    aprobado | enviado | timestamp_draft

`linkedin_url` resolves n8n_Message1_Send_Flow.md §6 edge case 1's LinkedIn
half (a send target the n8n send flow can hit directly, no Attio lookup
needed) — the raw email address is still not a column, that half of edge
case 1 remains open.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")
_raw_credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
CREDENTIALS_PATH = (
    str(PROJECT_ROOT / _raw_credentials_path)
    if _raw_credentials_path and not Path(_raw_credentials_path).is_absolute()
    else _raw_credentials_path
)
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Message1Queue")

METADATA_COLUMNS = [
    "prospecto", "empresa", "score", "signal_type", "situacion",
    "email_disponible", "linkedin_disponible", "linkedin_url", "variable_personalizacion",
    "canal_envio", "patron", "persona_matcheada", "historia_prueba", "angulo", "qa_pass",
]
DRAFT_COLUMNS = ["draft_email", "editado_email", "draft_linkedin", "editado_linkedin"]
APPROVAL_COLUMNS = ["aprobado", "enviado", "timestamp_draft"]
COLUMNS = ["lead_id"] + METADATA_COLUMNS + DRAFT_COLUMNS + APPROVAL_COLUMNS


def _require_config() -> None:
    if not CREDENTIALS_PATH:
        print("Error: GOOGLE_SHEETS_CREDENTIALS_JSON not found in .env", file=sys.stderr)
        sys.exit(1)
    if not SPREADSHEET_ID:
        print("Error: GOOGLE_SHEETS_SPREADSHEET_ID not found in .env", file=sys.stderr)
        sys.exit(1)
    if not Path(CREDENTIALS_PATH).exists():
        print(f"Error: credentials file not found at {CREDENTIALS_PATH}", file=sys.stderr)
        sys.exit(1)


def _worksheet():
    """Lazy import gspread so the rest of the CLI works without it installed."""
    _require_config()
    import gspread

    client = gspread.service_account(filename=CREDENTIALS_PATH)
    sheet = client.open_by_key(SPREADSHEET_ID)
    try:
        return sheet.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
        return ws


def _canal_envio(draft_email: str, draft_linkedin: str) -> str:
    """Canal(es) label per Outbound_Pipeline_Tracker.md's fixed vocabulary."""
    has_email = bool(draft_email.strip())
    has_linkedin = bool(draft_linkedin.strip())
    if has_email and has_linkedin:
        return "Both"
    if has_email:
        return "Email"
    if has_linkedin:
        return "LinkedIn"
    return ""


def _find_row_by_lead_id(ws, lead_id: str) -> tuple[int, dict] | None:
    """Return (1-indexed row number, record dict) for an existing lead_id, or None."""
    records = ws.get_all_records()
    for i, record in enumerate(records, start=2):
        if str(record.get("lead_id", "")) == lead_id:
            return i, record
    return None


def upsert_draft(
    lead_id: str,
    canal: str,
    draft: str,
    metadata: dict,
    timestamp_draft: str,
) -> dict:
    """Create or update a lead's row with one channel's draft plus shared metadata.

    `canal` is "email" or "linkedin" — only that channel's draft column is
    touched. `metadata` may include any of METADATA_COLUMNS except
    `canal_envio` (recomputed here from which draft columns are non-empty).
    Calling this twice for the same lead_id with different canals converges
    on one row with `canal_envio = "Both"`, matching the Tracker's schema.
    """
    if canal not in ("email", "linkedin"):
        raise ValueError(f"canal must be 'email' or 'linkedin', got {canal!r}")

    ws = _worksheet()
    existing = _find_row_by_lead_id(ws, lead_id)

    if existing is None:
        row_data = {col: "" for col in COLUMNS}
        row_data["lead_id"] = lead_id
        row_data["aprobado"] = "No"
        row_data["enviado"] = "No"
    else:
        _, row_data = existing
        row_data = {col: str(row_data.get(col, "")) for col in COLUMNS}

    for key, value in metadata.items():
        if key in METADATA_COLUMNS and key != "canal_envio":
            row_data[key] = str(value)

    draft_col = "draft_email" if canal == "email" else "draft_linkedin"
    row_data[draft_col] = draft
    row_data["canal_envio"] = _canal_envio(row_data["draft_email"], row_data["draft_linkedin"])
    row_data["timestamp_draft"] = timestamp_draft

    values = [row_data[col] for col in COLUMNS]

    if existing is None:
        ws.append_row(values, value_input_option="RAW")
        return {"upserted": "inserted", "row": row_data}
    else:
        row_number, _ = existing
        ws.update(f"A{row_number}:{chr(ord('A') + len(COLUMNS) - 1)}{row_number}", [values])
        return {"upserted": "updated", "row_number": row_number, "row": row_data}


def batch_insert_leads(leads: list[dict]) -> dict:
    """Append a prepared list of leads in one write — each dict may set any
    COLUMNS key directly (draft_email/draft_linkedin, all metadata, etc.).
    Missing keys default to "" (or "No" for aprobado/enviado). Does not
    check for existing lead_id rows — use upsert_draft for incremental,
    per-skill-run writes; use this for a fresh bulk load of a lead list.
    """
    ws = _worksheet()
    rows = []
    for lead in leads:
        row_data = {col: "" for col in COLUMNS}
        row_data["aprobado"] = "No"
        row_data["enviado"] = "No"
        for key, value in lead.items():
            if key in COLUMNS:
                row_data[key] = str(value)
        if not row_data.get("canal_envio"):
            row_data["canal_envio"] = _canal_envio(row_data["draft_email"], row_data["draft_linkedin"])
        rows.append([row_data[col] for col in COLUMNS])
    ws.append_rows(rows, value_input_option="RAW")
    return {"inserted": len(rows)}


def list_approved_unsent() -> list[dict]:
    """Rows where aprobado=Si and enviado=No — what n8n's manual-button flow sends next."""
    ws = _worksheet()
    records = ws.get_all_records()
    return [
        r for r in records
        if str(r.get("aprobado", "")).strip().lower() == "si"
        and str(r.get("enviado", "")).strip().lower() == "no"
    ]


def mark_sent(row_number: int) -> dict:
    """Set enviado=Si on a 1-indexed sheet row (header is row 1, first data row is 2)."""
    ws = _worksheet()
    enviado_col = COLUMNS.index("enviado") + 1
    ws.update_cell(row_number, enviado_col, "Si")
    return {"row": row_number, "enviado": "Si"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Lead outreach queue CLI (Google Sheets)")
    sub = parser.add_subparsers(dest="command")

    ud = sub.add_parser("upsert-draft", help="Create or update a lead's row with one channel's draft")
    ud.add_argument("--lead-id", required=True)
    ud.add_argument("--canal", required=True, choices=["linkedin", "email"])
    ud.add_argument("--draft", required=True)
    ud.add_argument("--metadata-json", default="{}", help="JSON object with any of: " + ", ".join(METADATA_COLUMNS))
    ud.add_argument("--timestamp-draft", required=True, help="ISO timestamp of when the draft was written")

    bi = sub.add_parser("batch-insert", help="Insert a prepared list of leads in one write")
    bi.add_argument("--from-json", required=True, help="Path to a JSON file: an array of row objects")

    sub.add_parser("list-approved", help="List rows with aprobado=Si and enviado=No")

    ms = sub.add_parser("mark-sent", help="Mark a row as enviado=Si after a successful send")
    ms.add_argument("--row", type=int, required=True, help="1-indexed sheet row number")

    args = parser.parse_args()

    if args.command == "upsert-draft":
        metadata = json.loads(args.metadata_json)
        print(json.dumps(
            upsert_draft(args.lead_id, args.canal, args.draft, metadata, args.timestamp_draft),
            indent=2, ensure_ascii=False,
        ))
    elif args.command == "batch-insert":
        with open(args.from_json, "r", encoding="utf-8") as f:
            leads = json.load(f)
        print(json.dumps(batch_insert_leads(leads), indent=2, ensure_ascii=False))
    elif args.command == "list-approved":
        print(json.dumps(list_approved_unsent(), indent=2, ensure_ascii=False))
    elif args.command == "mark-sent":
        print(json.dumps(mark_sent(args.row), indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
