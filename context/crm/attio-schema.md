# Attio Schema — Signal-Led Outbound System

Defines how the GTM skill outputs map to Attio objects, attributes, and list stages.
This is the single source of truth for the CRM layer. The `/attio-crm` skill reads from here.

---

## Object Model

```
companies
  └── people              ← linked via company attribute
        ├── Notes         ← signal analysis, campaigns drafted, replies, buyer briefs
        ├── Tasks         ← follow-ups, meeting prep, AE notifications
        ├── Touches       ← one record per individual send (email, DM, or invite)
        └── List entries  ← pipeline stage in your outbound list
```

---

## companies

| Attio Attribute | Type | Source | Example |
|---|---|---|---|
| `name` | string | signal-builder / manual | "Acme Corp" |
| `domains` | string[] | manual / enrichment | ["acme.com"] |
| `description` | string | signal-builder output | "SaaS company running Salesforce + Outreach" |
| `employee_count` | number | enrichment | 120 |
| `industry` | string | enrichment / ICP filter | (per `context/icp.md`'s Industry field) |
| `funding_stage` | string | signal-builder | (per `context/icp.md`'s Growth Signal field — leave unset if the ICP isn't financing-event-driven) |

**Matching key:** `domains` — always upsert by domain to prevent duplicates.

---

## people

| Attio Attribute | Type | Source | Example |
|---|---|---|---|
| `name` | string | enrichment / manual | "Jane Smith" |
| `email_addresses` | string[] | enrichment / manual | ["jane@acme.com"] |
| `phone_numbers` | string[] | enrichment | ["+1 555 000 0000"] |
| `job_title` | string | enrichment / LinkedIn | "VP of Revenue Operations" |
| `linkedin_url` | string | prospect-posts / manual | "https://linkedin.com/in/janesmith" |
| `company` | record link | companies object | linked to Acme Corp record |
| `llm_input_tokens_total` | number | `utils/token_report.py` rollup | 12400 |
| `llm_output_tokens_total` | number | `utils/token_report.py` rollup | 3100 |
| `llm_cost_usd_total` | number | `utils/token_report.py` rollup | 0.09 |

`llm_*_total` fields are only populated when the pipeline runs programmatically against the API (see `utils/token_ledger.py` / `utils/token_report.py`) — a lead worked manually via Claude Code chat has no per-call usage data to roll up, so these stay unset for it rather than being estimated from session-level cost.

**Matching key:** `email_addresses` — primary deduplication key.

---

## touches

A **Touch** is one record per individual send — one email, one LinkedIn DM, or one LinkedIn invite. It is the structured, queryable ledger behind `combined_touch_count`: where a Note captures human-readable copy for one campaign, a Touch record captures the machine-checkable facts of one send event, so the pipeline tracker's Phase 5 (`Envío`) columns and the score-tier cadence gate (Step 5/Step 7 in `email-writer`/`linkedin-dm`) can be read directly instead of re-derived from note text.

**Created by:** `/attio-crm`, immediately after a send is confirmed — real send confirmation only (ESP confirmation for email, Unipile success response for LinkedIn). Never created at draft time; a drafted-but-unauthorized campaign has no Touch record, only a `Campaign Drafted` note.

**Cardinality:** many Touch records per Person — one per send, never updated after creation. Touches are an append-only log, not upserted.

| Attio Attribute | Type | Source | Example |
|---|---|---|---|
| `name` | string (title) | auto | "Touch 2 — Jane Doe — Acme Inc" |
| `person` | record link → people | required | linked to Jane Doe |
| `company` | record link → companies | derived from `person.company` | linked to Acme Corp |
| `touch_number` | number | attio-crm, at creation | 2 |
| `channel` | select: `Email` / `LinkedIn` | email-writer / linkedin-dm | "LinkedIn" |
| `send_action` | select: `Email` / `DM` / `Invite` | matches tracker's Send Action vocab | "DM" |
| `sequence_step` | string | email-writer / linkedin-dm | "Email 2 (Day 3-4)" / "Connection Note" |
| `sent_at` | datetime (ISO 8601) | actual send confirmation, not draft time | "2026-08-02T14:05:00Z" |
| `pattern` | select: `Pain-led` / `Value-led` / `Segment-fallback` / `Connection-note` | email-writer / linkedin-dm Step 3 | "Pain-led" |
| `angle` | string (1 line) | email-writer / linkedin-dm | "Vi que están armando RevOps desde cero" |
| `subject_line` | string | email-writer (email only; "—" for LinkedIn) | "revops tooling" |
| `message_text` | long text | verbatim copy sent — must match the drafted note byte-for-byte (see `linkedin-dm`'s Sending via Unipile step) | full email/DM body |
| `persona_matched` | string | resolved from `context/icp.md`'s Buyer Persona column at send time | "COO / VP Operations" |
| `proof_story_used` | string | resolved from `context/playbooks/segment-stories.md`, or "—" | "—" |
| `personalization_variable` | string | creative-variable | `{{recent_hire_role}} = RevOps Manager` |
| `signal_score_snapshot` | number 0-10 | signal-builder score at time of send (snapshot — the live score on Person/Company may change later) | 8 |
| `cadence_tier` | select: `Alto (8-10)` / `Estándar (3-7)` / `Fallback (1-2)` | derived from `signal_score_snapshot` | "Alto (8-10)" |
| `network_distance` | select: `1st` / `2nd` / `3rd` / `N/A` | Unipile `find-profile` response (LinkedIn only; "N/A" for email) | "N/A" |
| `qa_pass` | boolean | email-writer/linkedin-dm Step 6 self-check result | true |
| `combined_touch_count_after` | number | value of Person's `combined_touch_count` immediately after this send — audit trail, not the live counter | 1 |
| `source_skill` | select: `email-writer` / `linkedin-dm` | which skill produced this touch | "email-writer" |
| `status` | select: `Sent` / `Bounced` / `Failed` / `Skipped` | send confirmation result | "Sent" |
| `reply_linked` | record link → touches (self) or note (optional) | set by `/reply-handler` once a reply arrives referencing this specific touch | unset until reply |

**Matching key:** none — Touch is an immutable log, always create, never upsert. Before creating, `/attio-crm` should `search-records` for existing Touch records on the Person to compute the next `touch_number` and confirm the send isn't a duplicate (e.g. a retried webhook), not to merge into an existing record.

**Relationship to the `Campaign Drafted` / `Campaign Sent` notes below:** the Note stays the human-readable artifact a person reads in the Attio UI (full copy, one note per campaign draft). The Touch record is what the pipeline tracker, the cadence-cap gate, and any reporting query against — it's per-send, structured, and never edited after creation. Creating a Touch does not replace creating the `Campaign Sent` note; do both.

---

## Notes Schema

All notes follow this naming convention: `[Type] — [date YYYY-MM-DD]`

### Signal Analysis Note
Created by `/attio-crm` after `/signal-builder` runs.

```
Title: "Signal Analysis — 2026-06-17"

Body:
## Signal Analysis

**Prospect:** [Name], [Title] @ [Company]
**Signal score range:** [lowest]-[highest]/10

### Ranked Signals
1. [Signal description] — Score: X/10
   Recommended angle: [campaign approach]

2. [Signal description] — Score: X/10
   Recommended angle: [campaign approach]

[...]

### Top recommended approach
[Best signal + angle summary]

Source: /signal-builder
```

### Campaign Sent Note
Created by `/attio-crm` after `/email-writer` produces a campaign.

```
Title: "Campaign Sent — 2026-06-17"

Body:
## Outreach Campaign

**Signal used:** [signal name, score]
**Angle:** [Situation → Insight → Inquisition summary]

**Email 1 subject:** [subject line]
**Email 2 subject:** [subject line]
**Email 3 subject:** [subject line]

**Channel:** Email / LinkedIn DM
**Send cadence:** Email 1 now → Email 2 day 3-4 → Email 3 day 7-8

Source: /email-writer
```

### Reply Note
Created by `/attio-crm` after `/reply-handler` classifies a reply.

```
Title: "Reply — [CLASSIFICATION] — 2026-06-17"

Body:
## Reply Received

**Classification:** [INTERESTED / OBJECTION / NOT_NOW / NOT_INTERESTED / QUESTION / OUT_OF_OFFICE]
**Confidence:** [High / Medium / Low]

**Original reply:**
> [verbatim reply text]

**Response sent:**
> [verbatim AI-generated response]

**Attio actions taken:**
- Stage updated to: [stage]
- Task created: [Yes/No — content if Yes]
- Escalated to human: [Yes/No — reason if Yes]

Source: /reply-handler
```

### Buyer Brief Note
Created when a prospect is classified as INTERESTED and a meeting is being coordinated.

```
Title: "Buyer Brief — [Name] — 2026-06-17"

Body:
## Buyer Brief

### Contact
- Name: 
- Title: 
- Email: 
- LinkedIn: 
- Reports to (if known): 

### Signal Context
- Original trigger: 
- Signal score: /10
- Outreach timeline:
  - [date]: Initial email sent ([subject])
  - [date]: Reply received ([classification])

### Company Intelligence
- Size: [employees]
- Tech stack (detected): 
- Recent events: 
- Likely pain point: 

### Personalization Insights
- Communication style: [Concise / Detailed / Technical / Executive]
- Key concern raised: 
- Mutual connections: 
- Prior objections: 

### AE Preparation
- Lead with: 
- Avoid: 
- Discovery questions to confirm: 

Source: /reply-handler → /attio-crm
```

---

## Tasks Schema

| Field | Value |
|---|---|
| `content` | Descriptive: "Follow up with [Name] — [reason]" |
| `deadline_at` | ISO 8601 datetime |
| `linked_records` | Person record ID |
| `assignee` | AE workspace member ID (from `list-workspace-members`) |

**Standard tasks:**

| Trigger | Task content | Deadline |
|---|---|---|
| INTERESTED reply | "Meeting follow-up — [Name] replied INTERESTED" | +24h |
| NOT_NOW reply | "Re-engage [Name] — said to reach back [timeframe]" | [specified date] |
| OUT_OF_OFFICE | "Re-engage [Name] — returns from OOO" | Return date + 1 day |
| Meeting booked | "Prep buyer brief for [Name] call" | 1h before meeting |

---

## Pipeline List Stages

Used with `mcp__claude_ai_Attio__update-list-entry-by-record-id` or `update-list-entry-by-id`.

| Stage | Entry condition | Who sets it |
|---|---|---|
| `Outreach Sent` | Campaign logged in Attio | `/attio-crm` after `/email-writer` |
| `Replied` | Any reply received | `/attio-crm` after `/reply-handler` |
| `Interested` | Classification = INTERESTED | `/attio-crm` after `/reply-handler` |
| `Meeting Booked` | Calendar confirmed | AE / manual |
| `SQL` | AE confirms qualification post-meeting | AE / manual |
| `Nurture` | Classification = NOT_NOW | `/attio-crm` after `/reply-handler` |
| `Disqualified` | Classification = NOT_INTERESTED | `/attio-crm` after `/reply-handler` |

---

## ICP Qualification Fields

Custom attributes to track ICP fit at the company level. Set during `/gtm-context` or enrichment.

The `trigger_event` enum below is a generic superset covering any ICP this system might target — not every value is relevant to the current ICP. Check `context/icp.md`'s Growth Signal field to know which values `signal-builder` should actually populate (e.g., `funding` only applies if the current ICP is financing-event-driven).

| Attribute | Values | Source |
|---|---|---|
| `icp_fit` | Strong / Partial / Weak / Unknown | Manual / signal-builder |
| `signal_score` | 1–10 | signal-builder |
| `trigger_event` | job_change / funding / competitor_engagement / tech_install / post_engagement / website_activity | signal-builder |
| `sequence_status` | Active / Paused / Completed / Opted Out | attio-crm |
| `combined_touch_count` | number | email-writer / linkedin-dm | Incremented by both `email-writer` and `linkedin-dm` before every send (Step 7 send-gate in each). Enforces the tiered cadence from the ICP Qualification Fields' `signal_score` across both channels together, not per channel — check this count against the score-tier cap (see each skill's Step 5) before sending. This field is the fast, cheap counter to check at gate time; the [`touches`](#touches) object is the structured per-send ledger behind it — `combined_touch_count` should always equal `count(touches WHERE person = this)`, and any mismatch means a send happened without its Touch record (or vice versa) and should be reconciled. |
