# reply-handler

Classify an incoming prospect reply and generate the appropriate response. This is the AI-powered reply handling layer — it keeps 90% of interactions automated and only escalates when a human is genuinely needed.

## When to invoke

Whenever a prospect replies to an outbound email or LinkedIn DM and you need to:
1. Classify the intent of the reply
2. Generate a contextually appropriate response
3. Update Attio with the reply classification
4. Trigger follow-up actions if the prospect is INTERESTED

## What you need before running

- The prospect's reply (verbatim text)
- The original email that prompted the reply (for context)
- The signal that triggered the outreach (from `/signal-builder`)
- Prospect's Attio record ID (if already in CRM)

## Step 1 — Classify the reply

Analyze the reply and assign one of these six categories:

| Category | What it means | Example signals |
|---|---|---|
| `INTERESTED` | Prospect wants to learn more or take a next step | "Tell me more", "Let's chat", "Send me the details", "I'm open to a call" |
| `OBJECTION` | Prospect raises a specific concern but hasn't closed the door | Price, timing, authority, current vendor, headcount freeze |
| `NOT_NOW` | Timing issue — potential future interest signaled | "Reach out in Q2", "We're mid-migration", "Too busy until [date]" |
| `NOT_INTERESTED` | Clear rejection with no future opening | "Not a fit", "Please remove me", "We don't need this" |
| `QUESTION` | Prospect asks a specific product or process question | "How does X work?", "Do you integrate with Y?", "What's pricing?" |
| `OUT_OF_OFFICE` | Auto-responder detected | "I'll be back on...", "Contact [name] in my absence" |

**Classification rules:**
- If in doubt between INTERESTED and QUESTION, classify as QUESTION (safer — answer first, then invite next step)
- If the reply contains BOTH a question AND positive signals, classify as INTERESTED and answer the question in the response
- NOT_NOW always gets a task in Attio for the specified follow-up date
- NOT_INTERESTED removes the prospect from active sequences immediately

## Step 2 — Generate the response

### INTERESTED

```
Acknowledge their interest in one line.
Reference the specific signal or angle that landed.
Provide 1-2 sentences of relevant context (case study or proof point from offer.md).
Suggest a specific next step with a concrete ask.
Keep the entire response under 80 words.
Tone: warm, direct, no corporate fluff.
```

### OBJECTION

```
Empathize with the specific concern in one line (don't argue, don't pivot immediately).
Provide one relevant proof point that reframes the concern.
Offer a low-commitment next step (15 min call, a doc, a specific answer).
Keep the door open explicitly.
Under 75 words.
```

### NOT_NOW

```
Acknowledge their timing.
Confirm you'll reach back out at the time they mentioned.
Leave them with one useful thought or resource (optional — only if highly relevant).
Under 40 words.
Do NOT ask for a meeting or push for engagement.
```

### NOT_INTERESTED

```
Thank them for their time.
Confirm removal from sequences.
Leave the door open in one line ("If circumstances change, feel free to reach out").
Under 30 words.
No pushback. No "can I ask why?".
```

### QUESTION

```
Answer the question directly and specifically. No hedging.
If the answer opens a natural next step, suggest it.
Under 60 words.
```

### OUT_OF_OFFICE

```
No reply needed immediately.
Log the return date.
Set a task in Attio to follow up 1 business day after their return.
```

## Step 3 — Update Attio

After classifying and drafting the response:

1. **Log the reply** — create a Note on the Person record (see `reference/classification-prompts.md` for format)
2. **Update pipeline stage** — use `mcp__claude_ai_Attio__update-list-entry-by-record-id`
   - INTERESTED → "Interested"
   - OBJECTION → "Replied"
   - NOT_NOW → "Nurture"
   - NOT_INTERESTED → "Disqualified"
   - QUESTION → "Replied"
   - OUT_OF_OFFICE → no stage change, set task for return date
3. **Create task** if INTERESTED or NOT_NOW (with specific follow-up date)
4. **Generate Buyer Brief** if INTERESTED — see `context/crm/attio-schema.md`

## Step 4 — Human escalation triggers

Escalate to a human AE (Slack alert / Attio task with high priority) when:
- Classification is INTERESTED AND deal size signals are above threshold (e.g., company >200 employees)
- Prospect asks a question that requires confidential pricing or custom scoping
- The reply is ambiguous enough that confidence in classification is below 80%
- Prospect mentions a specific competitor by name in an OBJECTION

## Output format

```
CLASSIFICATION: [category]
CONFIDENCE: [High / Medium / Low]

DRAFT RESPONSE:
---
[response text]
---

ATTIO ACTIONS:
- Note: [what to log]
- Stage update: [new stage]
- Task: [task content + deadline, if applicable]
- Escalate to human: [Yes / No — reason if Yes]
```
