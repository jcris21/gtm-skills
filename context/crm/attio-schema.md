# Attio Schema — Signal-Led Outbound System

Defines how the GTM skill outputs map to Attio objects, attributes, and list stages.
This is the single source of truth for the CRM layer. The `/attio-crm` skill reads from here.

---

## Object Model

```
companies
  └── people              ← linked via company attribute
        ├── Notes         ← signal analysis, campaigns sent, replies, buyer briefs
        ├── Tasks         ← follow-ups, meeting prep, AE notifications
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
| `industry` | string | enrichment / ICP filter | "FinTech" |
| `funding_stage` | string | signal-builder | "Series B" |

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

**Matching key:** `email_addresses` — primary deduplication key.

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

| Attribute | Values | Source |
|---|---|---|
| `icp_fit` | Strong / Partial / Weak / Unknown | Manual / signal-builder |
| `signal_score` | 1–10 | signal-builder |
| `trigger_event` | job_change / funding / tech_install / post_engagement / website_activity | signal-builder |
| `sequence_status` | Active / Paused / Completed / Opted Out | attio-crm |
