# n8n Reply-Handler Automation — Workflow Spec

Status: **Draft spec — not yet built in n8n**
Owner: GTM automation
Replaces: manual `/reply-handler` invocation inside a Claude Code session
Source skill ported: `.claude/skills/reply-handler/skill.md`
Receptor URL: `https://n8n.odooconcept.com/webhook/01cca18f-fe2d-4138-aa23-6cccf8f54b32`

---

## 1. Why this exists

Today a LinkedIn DM reply from a prospect sits in Unipile/LinkedIn until someone manually copies the text into Claude Code and runs `/reply-handler`. Nothing listens for the reply and nothing triggers classification automatically. This spec closes that gap end-to-end:

```
LinkedIn reply → Unipile webhook → n8n → Claude (classify+draft) → Attio (log) → Slack (approve) → Unipile (send)
```

The classification rules, response templates, Attio actions, and escalation triggers are **ported 1:1** from `reply-handler/skill.md` into the n8n workflow (system prompt + branching logic), since Claude Code skills have no HTTP entry point n8n can call directly.

---

## 2. Trigger — Unipile webhook

Configure in Unipile (dashboard or `POST /api/v1/webhooks`) to fire on new inbound message events and point at the n8n receptor:

- **Event:** `message_received` (inbound LinkedIn DM, not messages the account itself sent)
- **Target URL:** `https://n8n.odooconcept.com/webhook/01cca18f-fe2d-4138-aa23-6cccf8f54b32`
- **Filter:** only for the connected LinkedIn account(s) used for outbound (avoid personal inbox noise if the account is shared)

> **Verify before building:** confirm the exact webhook payload shape from Unipile's current API docs (chat_id, sender provider_id, message text field name, account_id). Field names below are placeholders (`{{payload.X}}`) to be corrected against the real payload during build.

Expected payload (approx.):
```json
{
  "account_id": "unipile-account-id",
  "chat_id": "chat-id",
  "sender": { "provider_id": "...", "name": "Priscila Antunes", "public_identifier": "..." },
  "message": { "text": "...", "timestamp": "..." }
}
```

---

## 3. Workflow nodes (n8n)

### Node 1 — Webhook (Trigger)
- Type: `Webhook`
- Method: POST
- Path: `01cca18f-fe2d-4138-aa23-6cccf8f54b32` (already registered — reuse as-is)
- Response mode: "Immediately" with `200 OK` (don't make Unipile wait on the full pipeline)

### Node 2 — Filter: ignore outbound/self events
- Type: `IF`
- Condition: `sender.provider_id != our own account's provider_id` (guards against echoing our own sent messages back through the pipeline)

### Node 3 — Attio Lookup: find Person by LinkedIn identifier
- Type: `HTTP Request` → Attio API (`POST /v2/objects/people/records/query`, filter on `linkedin_url` contains sender's public identifier)
- Purpose: recover `record_id`, prospect name, and the most recent Note (original outbound email/DM + signal context) needed for classification context
- Credential: Attio API key (n8n credential, separate from the Claude-side Attio MCP connector)
- **On no match found:** branch to Node 3b (see §6 edge cases)

### Node 4 — Attio: fetch context notes
- Type: `HTTP Request` → `GET /v2/objects/people/records/{record_id}/notes` (or `search-notes-by-metadata` equivalent)
- Pulls the most recent "Campaign Sent" note (original message + signal used) and any prior "Reply" notes, so the classifier has the same three inputs `reply-handler` requires manually: reply text, original message, signal context.

### Node 5 — Claude: classify + draft (the ported skill)
- Type: `HTTP Request` → `POST https://api.anthropic.com/v1/messages`
- Credential: `ANTHROPIC_API_KEY` (n8n credential — **new**, not currently in this repo's `.env`; provision separately for n8n)
- Model: `claude-sonnet-5`
- **System prompt:** the full content of `reply-handler/skill.md` Steps 1–2 (classification table + rules + per-category response templates), reproduced verbatim so behavior matches the manual skill exactly. See §7.
- **User message:** reply text (Node 1), original outbound message + signal context (Node 4), prospect name/title/company (Node 3)
- **Structured output:** force JSON via a tool/schema so n8n can branch on it reliably:
  ```json
  {
    "classification": "INTERESTED | OBJECTION | NOT_NOW | NOT_INTERESTED | QUESTION | OUT_OF_OFFICE",
    "confidence": "High | Medium | Low",
    "draft_response": "string, under the category's word limit",
    "task_needed": true,
    "task_deadline": "ISO 8601 or null",
    "escalate": true,
    "escalate_reason": "string or null"
  }
  ```

### Node 6 — Switch: escalation gate
- Type: `Switch`, branch on `escalate == true` OR `confidence == "Low"`
- Escalation triggers (ported verbatim from skill.md §Step 4):
  - INTERESTED + company size signal above threshold (>200 employees) — needs Attio company lookup joined in Node 3/4
  - Question requires confidential pricing/custom scoping
  - Classification confidence < 80% (i.e. not "High")
  - OBJECTION mentions a named competitor
- **If escalated:** skip the normal approval flow, send a **high-priority** Slack alert to a human AE directly (different message template — "needs your judgment, not just your approval") and stop the auto-pipeline (Node 9 still creates the Attio task, no auto-send at all).

### Node 7 — Attio: log the Reply Note (auto, always happens)
- Type: `HTTP Request` → `POST /v2/objects/people/records/{record_id}/notes`
- Uses the exact template from `context/crm/attio-schema.md` → "Reply Note":
  ```
  Title: "Reply — {{classification}} — {{today}}"

  Body:
  ## Reply Received

  **Classification:** {{classification}}
  **Confidence:** {{confidence}}

  **Original reply:**
  > {{reply_text}}

  **Response sent:**
  > {{draft_response}}   ← filled in AFTER Slack approval + send (see Node 11)

  **Attio actions taken:**
  - Stage updated to: {{stage}}
  - Task created: {{task_yes_no}}
  - Escalated to human: {{escalate_yes_no}}

  Source: n8n reply-handler automation
  ```
- Runs immediately for the audit trail, then gets a follow-up PATCH once the actual sent text is confirmed (Node 11b).

### Node 8 — Attio: update pipeline stage (auto, always happens)
- Type: `HTTP Request` → `PATCH` list entry stage, mapping straight from `attio-schema.md`:

  | Classification | Stage |
  |---|---|
  | INTERESTED | `Interested` |
  | OBJECTION | `Replied` |
  | NOT_NOW | `Nurture` |
  | NOT_INTERESTED | `Disqualified` |
  | QUESTION | `Replied` |
  | OUT_OF_OFFICE | *(no change)* |

### Node 9 — Attio: create task (conditional)
- Type: `HTTP Request` → `POST /v2/tasks`
- Fires when `task_needed == true`:
  - INTERESTED → "Meeting follow-up — {{name}} replied INTERESTED", deadline +24h
  - NOT_NOW → "Re-engage {{name}} — said to reach back {{timeframe}}", deadline = specified date
  - OUT_OF_OFFICE → "Re-engage {{name}} — returns from OOO", deadline = return date + 1 day

### Node 10 — Slack: HITL approval (the gate before anything is sent)
- Type: `Slack` node using **Interactive Blocks** (Block Kit) posted to a review channel, e.g. `#gtm-reply-approvals`
- Message content:
  ```
  New reply classified: *{{classification}}* ({{confidence}} confidence)
  Prospect: {{name}} — {{title}} @ {{company}}

  > {{reply_text}}

  Drafted response:
  > {{draft_response}}

  [Approve & Send]   [Edit]   [Reject]
  ```
- **Approve & Send** → continues pipeline to Node 11 with the draft unmodified
- **Edit** → opens a Slack modal (or a follow-up thread reply) where the human pastes an edited version; the edited text replaces `draft_response` before Node 11
- **Reject** → stops the pipeline; no send; Node 7's note gets a follow-up PATCH marking "Response sent: (rejected, no send)"; Attio stage stays as set in Node 8 but a task is created for manual handling
- n8n implementation: `Slack Trigger` (or the same workflow resuming via `Wait for Webhook`) listening for the button `action_id` callback, with a **wait node** timeout (e.g. 48h) after which it auto-escalates to Node 6's high-priority alert rather than silently expiring.
- Skipped entirely for OUT_OF_OFFICE (no reply drafted — see §6.4).

### Node 11 — Unipile: send the approved reply
- Type: `HTTP Request` → reuse `send_dm` logic from `utils/unipile.py` (`POST {{DSN}}/api/v1/chats` with `attendees_ids: [sender.provider_id]`, `text: {{approved_draft}}`)
- Credential: `UNIPILE_API_KEY` / `UNIPILE_DSN` (n8n credential, same values as `.env`)
- Only reached after Slack approval (Node 10) — **never auto-sends without a human click**, per your requirement.

### Node 11b — Attio: patch the Reply Note with final sent text + approval outcome
- Type: `HTTP Request` → `PATCH` the note created in Node 7 (or append a second note) recording:
  - Final response actually sent (may differ from AI draft if edited)
  - Who approved it (Slack user)
  - Timestamp of send

### Node 12 — Buyer Brief trigger (INTERESTED only)
- Type: `IF` → `classification == "INTERESTED"`
- Action: create the "Buyer Brief" note template from `attio-schema.md`, pre-filled with what's available (signal context from Node 4, reply content) and a task "Prep buyer brief for {{name}} call" — flagged incomplete since some fields (tech stack, mutual connections) still need manual AE input.

---

## 4. Full flow diagram

```
[Unipile message_received]
        │
        ▼
   Webhook (n8n)
        │
        ▼
  Filter: not our own account? ──No──▶ (stop)
        │Yes
        ▼
  Attio: find Person by LinkedIn id ──not found──▶ Slack alert "unknown sender, create record?" (stop)
        │found
        ▼
  Attio: fetch context (last campaign note, prior replies)
        │
        ▼
  Claude API: classify + draft (system prompt = ported skill.md)
        │
        ▼
  Escalation gate (size / pricing / low-confidence / competitor)
   │Yes                                   │No
   ▼                                      ▼
 Slack: high-priority alert      Attio: log Reply Note (draft only, unsent)
 Attio: log note + task          Attio: update pipeline stage
 (stop — human takes over)       Attio: create task if needed
                                          │
                                          ▼
                                 Slack: HITL approval (Approve/Edit/Reject)
                                   │Approve/Edit        │Reject
                                   ▼                     ▼
                          Unipile: send DM        Attio: mark rejected, create manual task
                                   │
                                   ▼
                          Attio: patch note with final sent text
                                   │
                                   ▼
                          If INTERESTED → create Buyer Brief note + task
```

---

## 5. Credentials needed in n8n

| Credential | Used by | Already exists? |
|---|---|---|
| Unipile API key + DSN | Node 11 (send), webhook config | Yes — in project `.env` (`UNIPILE_API_KEY`, `UNIPILE_DSN`); needs to be added as an n8n credential separately |
| Anthropic API key | Node 5 (classify/draft) | **No** — must be provisioned. This is a raw Anthropic API key, distinct from Claude Code/claude.ai session auth, which cannot be reused by n8n |
| Attio API key (bearer token) | Nodes 3, 4, 7, 8, 9, 11b, 12 | **No** — this repo currently only uses Attio via the Claude-side MCP connector, not a standalone API key. Generate one in Attio workspace settings → API tokens |
| Slack bot token (or incoming webhook + Interactivity enabled) | Node 10 | **No** — needs a Slack app with `chat:write` and Interactive Components enabled, posting to `#gtm-reply-approvals` (or your preferred channel) |

---

## 6. Edge cases to handle explicitly

1. **Sender not found in Attio** (cold inbound DM, not a prospect we outreached to) — don't silently drop it; alert Slack so a human decides whether to create a new record.
2. **Multiple rapid replies in one thread before approval completes** — debounce: if a new webhook fires for the same `chat_id` while a prior approval is still pending, append to the same Slack thread rather than opening a second approval card.
3. **Approval timeout** — if nobody responds in Slack within 48h, escalate to the high-priority channel rather than leaving the draft stuck.
4. **OUT_OF_OFFICE** — per skill.md, no reply is drafted/sent; only a task is created for the return date. Node 10 is skipped for this classification (auto-complete after Node 9).
5. **Low confidence output from Claude** (malformed JSON, model uncertainty) — treat as automatic escalation (Node 6), never let a malformed classification fall through to auto-send.

---

## 7. System prompt to paste into Node 5 (ported from `reply-handler/skill.md`)

Use the classification table (6 categories + examples), the classification rules (QUESTION-over-INTERESTED tie-break, NOT_NOW always gets a task, NOT_INTERESTED removes from sequences), and the six per-category response templates verbatim from `.claude/skills/reply-handler/skill.md` §Step 1–2 as the system prompt. Keep this file as the single source of truth — if `skill.md` is edited later (tone, word limits, category rules), copy the change into the n8n Claude node's system prompt too, since the two are separate files and won't stay in sync automatically.

---

## 8. Open items before build

- [ ] Confirm real Unipile webhook payload schema (field names in §2)
- [ ] Register the webhook with Unipile pointing at the n8n URL
- [ ] Provision Anthropic API key, Attio API token, Slack app — none exist yet in this project's automation surface
- [ ] Decide the Slack approval channel and who's in it
- [ ] Decide the escalation channel (same channel, different formatting, or a separate `#gtm-escalations`?)
- [ ] Build + test with a low-risk category first (e.g. OUT_OF_OFFICE, no send involved) before enabling INTERESTED/OBJECTION auto-draft
