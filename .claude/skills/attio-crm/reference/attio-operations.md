# Attio Operations Reference

Maps the playbook's CRM fields to Attio MCP tool calls.

## Object Model

```
Company (companies)
  └── Person (people)         ← linked via company attribute
        └── Note              ← signal analysis, buyer brief
        └── Task              ← follow-up, meeting prep
        └── List Entry        ← pipeline stage tracking
```

## Field Mapping: Playbook → Attio

### Contact Information (from lead enrichment)

| Playbook Field | Attio Attribute | MCP Object | Notes |
|---|---|---|---|
| Name | `name` | people | First + Last |
| Email | `email_addresses` | people | Primary matching key |
| Phone | `phone_numbers` | people | Optional |
| LinkedIn | `linkedin_url` | people | Custom attribute |
| Title / Role | `job_title` | people | |
| Company name | `name` | companies | Linked record |
| Company domain | `domains` | companies | Matching key |

### Signal Context (from signal-builder)

Stored as a **Note** on the Person record.

```
Title: "Signal Analysis — YYYY-MM-DD"
Body format:
  Signal 1: [description] — Score: X/10
  Signal 2: [description] — Score: X/10
  ...
  Recommended angle: [campaign approach]
  Source: /signal-builder
```

### Outreach Tracking

Stored as a **Note** on the Person record after `/email-writer` runs.

```
Title: "Campaign Sent — YYYY-MM-DD"
Body format:
  Sequence: [Email 1 subject], [Email 2 subject], [Email 3 subject]
  Signal used: [signal name]
  Angle: [campaign angle]
  Sent via: [channel]
```

### Reply Classification (from reply-handler)

Stored as a **Note** + **Task** on the Person record.

```
Note title: "Reply Received — YYYY-MM-DD"
Note body:
  Classification: [INTERESTED / OBJECTION / NOT_NOW / ...]
  Original reply: "[verbatim reply text]"
  AI response sent: "[generated response]"

Task (if INTERESTED):
  Content: "Meeting follow-up — [name] replied INTERESTED"
  Deadline: +24h
```

### Pipeline Stage Values

Used with `mcp__claude_ai_Attio__update-list-entry-by-record-id` on your pipeline list.

| Stage | Trigger |
|---|---|
| `Outreach Sent` | After `/email-writer` campaign logged |
| `Replied` | Any reply received (any classification) |
| `Interested` | Classification = INTERESTED |
| `Meeting Booked` | Calendar link clicked / confirmed |
| `SQL` | AE confirms qualification |
| `Disqualified` | Classification = NOT_INTERESTED |
| `Nurture` | Classification = NOT_NOW |

## MCP Tool Quick Reference

| Operation | Tool | Key Parameters |
|---|---|---|
| Find person | `mcp__claude_ai_Attio__search-records` | `object_type: "people"`, `query: email` |
| Create/update person | `mcp__claude_ai_Attio__upsert-record` | `object_type: "people"`, `matching_attribute: "email_addresses"` |
| Create/update company | `mcp__claude_ai_Attio__upsert-record` | `object_type: "companies"`, `matching_attribute: "domains"` |
| Add signal note | `mcp__claude_ai_Attio__create-note` | `record_id`, `title`, `content` |
| Create task | `mcp__claude_ai_Attio__create-task` | `linked_records`, `content`, `deadline_at` |
| List pipeline | `mcp__claude_ai_Attio__list-lists` | — |
| Update stage | `mcp__claude_ai_Attio__update-list-entry-by-record-id` | `list_id`, `entry_id`, `stage` |
| Get workspace members | `mcp__claude_ai_Attio__list-workspace-members` | For AE assignment |
| Semantic search notes | `mcp__claude_ai_Attio__semantic-search-notes` | Find prior context on a prospect |

## Buyer Brief Template

Generated when a prospect becomes INTERESTED. Attach as a Note to the Person record.

```
## Buyer Brief — [Name], [Title] @ [Company]

### Contact
- Email: 
- LinkedIn: 
- Reporting to: (if known)

### Signal Context
- Original trigger: 
- Signal score: /10
- Timeline of interactions:

### Company Intelligence
- Tech stack: (from signal-builder)
- Recent events: (funding, hiring, news)
- Likely pain: 

### Personalization Insights
- Communication style: (from reply analysis)
- Key concern raised: 
- Mutual connections: (if any)

### Recommended AE prep
- Lead with: 
- Avoid: 
```
