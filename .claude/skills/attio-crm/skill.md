# attio-crm

Push prospect data, signal context, and deal state into Attio. This is the CRM layer of the signal-led outbound system — it replaces HubSpot for all lead management operations.

## When to invoke

- After `/email-writer` produces a campaign and you want to log the prospect + campaign in Attio
- After `/linkedin-dm` sends a message and you want to log the prospect + DM in Attio
- After `/signal-builder` scores a prospect and you want to create a signal note
- When a reply comes in and `/reply-handler` classifies it as INTERESTED — create a follow-up task
- When a deal stage changes (e.g., meeting booked → SQL)

## What you need before running

- A contact record (name, email, company, LinkedIn URL if available)
- Signal context from `/signal-builder` (optional but strongly recommended)
- Campaign data from `/email-writer` and/or `/linkedin-dm` (optional)

## Operations

### 1. Upsert a contact

Find or create a Person record in Attio. Use email as the unique key.

```
Tool: mcp__claude_ai_Attio__upsert-record
Object: people
Matching attribute: email_addresses
Fields to set:
  - name
  - email_addresses
  - job_title
  - linkedin_url (if available)
  - company (link to company record if it exists)
```

### 2. Upsert a company

Find or create a Company record. Use domain as the unique key.

```
Tool: mcp__claude_ai_Attio__upsert-record
Object: companies
Matching attribute: domains
Fields to set:
  - name
  - domains
  - description (from signal-builder output)
```

### 3. Log signal context as a note

After `/signal-builder` runs, attach the ranked signal output as a note on the Person record.

```
Tool: mcp__claude_ai_Attio__create-note
Attach to: Person record
Title: "Signal Analysis — [date]"
Body: paste the full signal-builder output (signals 1-7, scores, recommended angles)
```

### 4. Create a follow-up task

When a prospect is INTERESTED (from `/reply-handler`) or a meeting is booked.

```
Tool: mcp__claude_ai_Attio__create-task
Linked record: Person
Content: "Follow up with [name] — classified INTERESTED on [date]"
Deadline: 24h from reply
Assignee: AE owner (use mcp__claude_ai_Attio__list-workspace-members to find the right person)
```

### 5. Update deal stage

When a prospect moves from outreach → replied → meeting booked → SQL.

```
Tool: mcp__claude_ai_Attio__update-record
Object: the relevant list entry (e.g., pipeline list)
Fields to update:
  - stage
  - last_contacted
  - signal_score (custom attribute)
```

### 6. Search before creating

Always check if a record exists before upserting to avoid duplicates.

```
Tool: mcp__claude_ai_Attio__search-records
Object: people
Query: prospect email or name
```

## Standard workflow

```
1. search-records        → check if contact exists
2. upsert-record         → create/update Person + Company
3. create-note           → attach signal context
4. [optional] create-task → if INTERESTED or meeting booked
5. [optional] update-record → update stage in pipeline list
```

## Output

After running, confirm:
- Person record exists with correct email + company linked
- Signal note attached to the record
- Task created (if applicable)
- Stage updated (if applicable)

Reference `context/crm/attio-schema.md` for the exact field mapping between signal-builder output and Attio attributes.
