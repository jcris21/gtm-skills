# n8n Message-1 Send Flow — Workflow Spec

Status: **Draft spec — not yet built in n8n**
Owner: GTM automation
Implements: `Documents/HITL_Send_Approval_Design.md` §3.3 (Fase 3 of §7's build plan)
Reads from: Google Sheet `OutboundQueue` (spreadsheet ID `195CuTqAt_ty2oxI-KKbbS1A0BxTc8OEzbzRNIaQy6HM`), written by `utils/sheet_queue.py`'s `upsert_draft`/`batch_insert_leads`, called from `email-writer/skill.md` and `linkedin-dm/skill.md` Step 7.

---

## 1. Why this exists

Message 1 (email and/or LinkedIn) is never sent directly by `email-writer`/`linkedin-dm` — those skills only draft the copy and queue it to the `OutboundQueue` Sheet (`aprobado=No`, `enviado=No`). A human reviews/edits/approves rows in the Sheet (setting `aprobado=Sí`, optionally filling `editado_email`/`editado_linkedin`). This workflow is what actually sends: it runs on a manual button click, reads approved-and-unsent rows, sends each lead's Message 1 through whichever channel(s) it has, marks the row `enviado=Sí`, and logs the send to Attio.

```
Human approves rows in Sheet → clicks n8n button → n8n reads Sheet → sends via Gmail/Unipile → marks enviado → logs Attio
```

Trigger is a **manual button**, not a cron/poll (decided in `HITL_Send_Approval_Design.md` §3.3) — the operator finishes reviewing a batch, then explicitly fires the send, so nothing goes out mid-review.

---

## 2. Trigger — manual button

- Type: n8n `Manual Trigger` node (or a `Form Trigger` with a single "Send approved batch" button if you want it runnable outside the n8n editor).
- No payload needed — the workflow reads its own state from the Sheet.

---

## 3. Workflow nodes

### Node 1 — Manual Trigger
Fires the whole read → send → mark loop below.

### Node 2 — Google Sheets: read all rows
- Type: `Google Sheets` (Read)
- Spreadsheet: `195CuTqAt_ty2oxI-KKbbS1A0BxTc8OEzbzRNIaQy6HM`, sheet `OutboundQueue`
- Returns every row with n8n's built-in `row_number` field included in each item — needed later (Node 8) to update the exact row without a second lookup.

### Node 3 — Filter: approved and unsent
- Type: `Filter`
- Condition: `aprobado` == `Sí` (or `Si` — accept both, source data may vary) **AND** `enviado` == `No`
- Matches `list_approved_unsent()`'s logic in `utils/sheet_queue.py`, reimplemented natively in n8n since this workflow reads the Sheet directly rather than shelling out to Python.

### Node 4 — Split In Batches
- Type: `Split In Batches`, batch size 1
- Processes one lead's row per iteration so a failure on one lead (Node 6/7 below) doesn't block the rest of the batch — each iteration independently reaches Node 8 (mark sent) or falls into the error branch (§6).

### Node 5 — Switch: canal_envio
- Type: `Switch`, branch on `canal_envio`: `Email` / `LinkedIn` / `Both`
- `Email` → Node 6a only
- `LinkedIn` → Node 6b only
- `Both` → Node 6a **and** Node 6b (both branches run, converge at Node 7's Merge)

### Node 6a — Gmail: send Email 1
- Type: `Gmail` (send message), OAuth credential on the Workspace account used for outbound
- Body text: `editado_email` if non-empty, else `draft_email` — never send a blank fallback.
- `draft_email`/`editado_email` are stored as `"Subject: ...\n\n<body>"` (the shape `email-writer/skill.md` Step 7 writes). Add a small `Code` node before Gmail to split on the first `\n` after `Subject: ` into separate `subject`/`body` fields for the Gmail node's parameters — do this splitting in n8n, not by re-parsing in Gmail's own subject field expression, so it's testable independently.
- To: the lead's email — **not currently a Sheet column.** See §6 edge case 1.

### Node 6b — Unipile: send LinkedIn Message 1
- Type: `HTTP Request` chain, same calls `linkedin-dm/skill.md`'s "Sending via Unipile" section documents:
  1. `GET {{DSN}}/api/v1/users/{identifier}?account_id={{account_id}}` (find-profile) → `network_distance`
  2. `network_distance == FIRST_DEGREE` → `POST {{DSN}}/api/v1/chats` (`send-dm`, `attendees_ids: [recipient]`, `text: editado_linkedin || draft_linkedin`)
  3. else → `POST {{DSN}}/api/v1/users/invite` (`invite`, `provider_id`, `message: editado_linkedin || draft_linkedin`, ≤300 chars)
- Credential: `UNIPILE_API_KEY` / `UNIPILE_DSN` as n8n credentials (same values as `.env`)
- The LinkedIn identifier/provider id is **not currently a Sheet column** either — see §6 edge case 1.

### Node 7 — Merge
- Type: `Merge`, waits for both Node 6a and Node 6b branches when `canal_envio == Both`; passes through directly for single-channel rows.

### Node 8 — Google Sheets: mark enviado
- Type: `Google Sheets` (Update)
- Row: `row_number` carried from Node 2/4
- Set `enviado = Sí`
- Mirrors `utils/sheet_queue.py`'s `mark_sent(row_number)` — reimplemented natively here for the same reason as Node 3.

### Node 9 — Attio: log Campaign Sent + update pipeline
- Type: `HTTP Request` → Attio API
- `create-note` on the Person record (`lead_id` column = Attio record id): title `Campaign Sent — [date]`, body quoting the exact text sent (per `context/crm/attio-schema.md`'s "Campaign Sent Note" format) — mirrors `linkedin-dm/skill.md` Step 5 in "Sending via Unipile".
- `update-list-entry-by-record-id` on the `Outbound Pipeline` list: stage → `Outreach Sent`.
- Increment `combined_touch_count` by 1 (shared counter, same field `email-writer`/`linkedin-dm` already use).
- Credential: Attio API key — **not yet provisioned** for n8n (same open item already flagged in `n8n_Reply_Handler_Automation.md` §5/§8; one token covers both workflows).

Loop back to Node 4 for the next row until the batch is exhausted.

---

## 4. Flow diagram

```
Manual button (n8n)
        │
        ▼
Google Sheets: read OutboundQueue
        │
        ▼
Filter: aprobado=Sí AND enviado=No
        │
        ▼
Split In Batches (1 lead at a time)
        │
        ▼
Switch: canal_envio
   │Email        │LinkedIn        │Both
   ▼             ▼                ▼
 Gmail send   Unipile send    Gmail send + Unipile send (parallel)
   │             │                │
   └─────────────┴────────────────┘
                 ▼
              Merge
                 ▼
     Google Sheets: enviado = Sí
                 ▼
     Attio: Campaign Sent note + stage + touch count
                 │
                 ▼
        (loop → next row in batch)
```

---

## 5. Credentials needed in n8n

| Credential | Used by | Already exists? |
|---|---|---|
| Google Sheets OAuth | Nodes 2, 8 | **No** — needs the service account (`credentials/google-sheets-service-account.json`, gitignored) added as an n8n credential, or a separate OAuth connection if the n8n Google Sheets node uses OAuth instead of a service account |
| Gmail OAuth | Node 6a | **No** — connect the Workspace account used for outbound |
| Unipile API key + DSN | Node 6b | Yes — in project `.env` (`UNIPILE_API_KEY`, `UNIPILE_DSN`); needs to be added as an n8n credential separately (same open item as `n8n_Reply_Handler_Automation.md`) |
| Attio API key (bearer token) | Node 9 | **No** — same not-yet-provisioned token flagged in `n8n_Reply_Handler_Automation.md` §5 |

---

## 6. Edge cases to handle explicitly

1. **`lead_id`/email/LinkedIn identifier aren't Sheet columns.** `OutboundQueue`'s schema (`HITL_Send_Approval_Design.md` §3.2) has `lead_id` (Attio record id) but no raw email address or LinkedIn provider id/URL — those live only in Attio. Node 6a/6b need a lookup step (Attio `GET` by `lead_id`, or an Attio HTTP Request node before the Switch) to resolve the actual send target. **LinkedIn half resolved 2026-08-07 (option a):** `linkedin_url` added to `sheet_queue.py`'s `METADATA_COLUMNS`/`COLUMNS` — Node 6b can call `find-profile` with this column directly, no Attio lookup needed for LinkedIn sends. **Email half still open** — `email` is not yet a Sheet column; Node 6a still needs option (a) (add `email`) or (b) (Attio lookup by `lead_id`) decided before building.
2. **Partial send on `canal_envio = Both`.** The schema has one `enviado` flag per row, not one per channel. If Gmail succeeds but Unipile fails (or vice versa), Node 7's Merge still reaches Node 8, which would incorrectly mark the whole row `enviado=Sí` even though one channel never went out. **Not yet resolved** — either add `enviado_email`/`enviado_linkedin` columns (mirroring `draft_email`/`draft_linkedin`'s per-channel split) and only mark the row's single `enviado=Sí` once both are true, or make Node 8 conditional on both branches reporting success (n8n `IF` checking each branch's HTTP status before the Merge).
3. **Unipile `send-dm` 422 (not 1st-degree).** Already handled per `linkedin-dm/skill.md`'s existing logic (fall back to `invite`) — same handling here, not a new case.
4. **Approval race.** If a human is still editing a row in the Sheet (e.g. mid-edit on `editado_linkedin`) when the button is clicked, this workflow could send a half-edited draft. Since the trigger is a deliberate manual click (not a poll), this is an operator-discipline issue, not something to solve in the workflow — but worth a one-line warning in the Sheet's instructions tab.
5. **Send failure (Gmail/Unipile API error).** Row should NOT be marked `enviado=Sí` and should surface the error somewhere the operator will see it before the next run — either a Slack alert node on the error branch, or a dedicated `envio_error` Sheet column set on failure. **Not yet resolved** — pick one before building.

---

## 7. Open items before build

- [ ] Provision Google Sheets credential in n8n (service account `credentials/google-sheets-service-account.json`, gitignored — same key `sheet_queue.py` uses)
- [ ] Connect Gmail OAuth for the outbound-sending Workspace account
- [ ] Add Unipile API key/DSN as an n8n credential (shared open item with `n8n_Reply_Handler_Automation.md`)
- [ ] Provision Attio API token for n8n (shared open item with `n8n_Reply_Handler_Automation.md`)
- [ ] Resolve edge case 1: how n8n resolves a send target (email address / LinkedIn identifier) from `lead_id` — add Sheet columns or add an Attio lookup node
- [ ] Resolve edge case 2: per-channel `enviado` tracking for `canal_envio = Both` rows
- [ ] Resolve edge case 5: where send failures surface (Slack alert vs. Sheet error column)
- [ ] Build + test with a single-channel row first (Email-only or LinkedIn-only) before testing a `Both` row
