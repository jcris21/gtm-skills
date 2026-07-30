# Reply Classification Prompts & Examples

Reference examples for each classification category. Use these to calibrate judgment when classifying ambiguous replies.

---

## INTERESTED

**Signals:** Clear intent to continue the conversation, request for more info, explicit openness.

**Examples:**
- "This is actually timely — we're evaluating options right now. Can you send more details?"
- "Interesting. Tell me more about how it works for teams like ours."
- "Let's find 20 minutes this week."
- "I forwarded this to our VP of Ops who owns this. She'll be in touch."
- "What does this look like for a 150-person company?"

**Note format for Attio:**
```
Title: "Reply — INTERESTED — [date]"
Body:
  Classification: INTERESTED
  Confidence: High
  Original reply: "[verbatim]"
  Response sent: "[verbatim draft]"
  Buyer Brief generated: Yes/No
```

**Draft response pattern:**
```
[Acknowledge in one clause]. [Specific proof point — 1-2 sentences from offer.md].

[Concrete next step — suggest a time or send a link, don't ask "when are you free?"].
```

**Example response:**
```
Good to hear — this is exactly the scenario we built for. We helped [similar company] 
cut their RevOps overhead by 40% in the first 90 days by replacing their manual 
enrichment workflow with this.

Here's a 15-minute slot that works for us: [calendar link]. Or reply with a time 
that's better for you.
```

---

## OBJECTION

**Signals:** Concern raised, but prospect hasn't ended the conversation.

**Subtypes:**
- **Price:** "Too expensive", "Not in budget right now", "What does this cost?"
- **Timing:** "Bad timing", "We just signed a contract with [vendor]", "Revisiting next quarter"
- **Authority:** "Not my decision", "Need to loop in [person]", "I don't own this budget"
- **Fit doubt:** "We're different", "Our situation is more complex", "I don't think this applies to us"

**Examples:**
- "We're locked into a contract with [competitor] until EOY."
- "This sounds interesting but I'm not the right person — you'd need to talk to our CRO."
- "Budget is frozen until Q1."
- "We tried something similar before and it didn't work."

**Note format for Attio:**
```
Title: "Reply — OBJECTION ([subtype]) — [date]"
Body:
  Objection type: [Price / Timing / Authority / Fit]
  Original reply: "[verbatim]"
  Response sent: "[verbatim draft]"
  Recommended follow-up: [date or trigger]
```

**Draft response pattern (Price):**
```
Totally fair — [empathize with constraint in one clause].

[One proof point that reframes cost as ROI]. Most teams we work with see [outcome] 
within [timeframe], which more than offsets the investment.

If the math works out, it's worth a 15-minute conversation. If not, I'll leave you alone.
```

**Draft response pattern (Authority):**
```
Appreciate the heads up. Is [person/role] the right contact, or is there a better way 
to get this in front of them?
```

---

## NOT_NOW

**Signals:** Positive framing but explicit timing block.

**Examples:**
- "Reach back out in Q2 — we're mid-migration right now."
- "Too buried to give this attention until after our conference in March."
- "We're not buying anything until the new fiscal year starts in July."
- "Come back in 6 weeks, we'll have a better picture of our roadmap."

**Note format for Attio:**
```
Title: "Reply — NOT_NOW — follow up [date]"
Body:
  Follow-up date: [specific date extracted from reply]
  Original reply: "[verbatim]"
  Response sent: "[verbatim draft]"
```

**Task in Attio:**
```
Content: "Follow up with [name] — said to reach back in [timeframe]"
Deadline: [specific date from reply, or best estimate if vague]
```

**Draft response pattern:**
```
Makes sense — I'll drop back in [specific month/timeframe they mentioned].

[Optional: one sentence of value if highly relevant, e.g., "In the meantime, here's 
a quick breakdown of how teams in [their situation] usually approach this."]
```

---

## NOT_INTERESTED

**Signals:** Clear, unambiguous rejection. No future interest signaled.

**Examples:**
- "Please remove me from your list."
- "Not interested."
- "We handle this internally and aren't looking at vendors."
- "This doesn't apply to us."
- "Stop emailing me."

**Note format for Attio:**
```
Title: "Reply — NOT_INTERESTED — [date]"
Body:
  Original reply: "[verbatim]"
  Action: Removed from sequence. Stage → Disqualified.
```

**Draft response pattern:**
```
Understood — I'll take you off the list. Thanks for your time, [first name].

If anything changes down the road, you know where to find us.
```

**Do not:**
- Ask "Can I ask why?"
- Push back on their decision
- Send a follow-up email after this

---

## QUESTION

**Signals:** Prospect asks a specific, answerable question. May or may not signal interest beyond curiosity.

**Examples:**
- "How does the integration with Salesforce work?"
- "What's your pricing model?"
- "Do you work with companies under $5M ARR?"
- "Is this self-serve or do you need an implementation team?"
- "How long does onboarding take?"

**Note format for Attio:**
```
Title: "Reply — QUESTION — [date]"
Body:
  Question asked: "[verbatim]"
  Response sent: "[verbatim draft]"
  Follow-up intent: [did we invite next step? Yes/No]
```

**Draft response pattern:**
```
[Answer the question directly and specifically in 1-3 sentences.]

[If the answer naturally opens a next step]: Does that change how you're thinking 
about it? Happy to walk through [relevant scenario] on a quick call.
```

---

## OUT_OF_OFFICE

**Signals:** Auto-responder language, no human content.

**Examples:**
- "I'm out of the office until [date]..."
- "I'm currently on leave..."
- "For immediate assistance, contact [colleague]..."
- "This is an automated reply..."

**Action:**
- Do NOT reply
- Extract return date from the message
- Create Attio task: "Re-engage [name] — returns [date]" with deadline = return date + 1 business day
- If a colleague is mentioned with a relevant role, consider whether to reach out to them instead

**Note format for Attio:**
```
Title: "OOO detected — return [date]"
Body:
  Detected return date: [date]
  Backup contact mentioned: [name + email if available]
  Action: Task set for [date + 1 business day]
```
