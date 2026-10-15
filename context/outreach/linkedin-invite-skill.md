# LinkedIn Invitation Message Skill

## Purpose

Generate LinkedIn connection request messages (the "invite note" shown when sending a connection request) that prioritize starting a conversation over pitching. The invite note is **not** the place for a commercial pitch — it is the lowest-friction touchpoint in the entire sequence.

## Core Principle: Conversation Over Pitch

The goal of an invite note is **not** to sell. It is to earn a connection acceptance and, ideally, a reply. Structure the invite around context and the possibility of a conversation, not a full commercial pitch.

## The 3-Block Structure

Every invite note follows this structure, prioritized by conversation potential:

### Block 1: Specific Signal

Name a **verifiable** data point that makes it evident why you are reaching out to this specific person.

- Company expansion (new locations, funding, headcount growth)
- Number of operations, facilities, or markets served
- Diversity of services or product lines
- Recent leadership changes, job postings, or public announcements
- Industry-specific operational scale (throughput, SKU count, transaction volume)

**Good examples:**
- "Saw [Company] just opened a third facility in [location]"
- "Noticed your team grew from 15 to 40 operations roles this year"
- "Your distribution network now covers 12 states — that's a big shift from last year"

**Bad examples:**
- "I came across your profile and was impressed" (generic, no signal)
- "Your company is a leader in the space" (unverifiable flattery)

### Block 2: Value Hypothesis

Connect the signal to a **possible** operational challenge — without asserting the prospect necessarily has it.

- Cross-team coordination complexity
- Disconnected systems or manual processes
- Scaling bottlenecks in procurement, logistics, or operations
- Vendor or carrier management at scale

**Good examples:**
- "Teams at that scale often end up coordinating across disconnected systems"
- "When operations span multiple facilities, procurement visibility tends to get fragmented"
- "Growth like that usually creates friction between ops and finance on spend tracking"

**Bad examples:**
- "I know you're struggling with [problem]" (presumptuous diagnosis)
- "Your current processes are inefficient" (unverifiable insult)

### Block 3: Low-Friction Question

Ask a simple, easy-to-answer question — preferably one that does not require revealing confidential information.

- "Is that a priority for your team?"
- "Is that something you're actively working on?"
- "How are you handling [operational area] at that scale?"

**Good examples:**
- "Is that a priority for your team right now?"
- "How are you managing that coordination today?"

**Bad examples:**
- "Can we schedule a 30-min call to discuss solutions?" (high-friction CTA)
- "Would you like a free demo?" (commercial, not conversational)

---

## Two Archetypes

### Archetype A — Personalization + Question

**Structure:** Signal → "Is that a priority for your team?"

**Best for:** Initial connection requests, cold outreach, first touch. Lower friction, higher acceptance rate.

**Example:**
> Saw [Company] expanded to 3 new facilities this year. Is that kind of cross-site coordination a priority for your team?

### Archetype B — Personalization + Operational Hypothesis

**Structure:** Signal → Hypothesis about operational challenge → "How are you handling [X]?"

**Best for:** When you have richer data (tech stack, job postings, public ops details). Slightly higher friction but signals deeper research.

**Example:**
> Noticed your team is scaling from 15 to 40 operations roles across 4 locations. At that growth rate, procurement visibility across sites tends to get fragmented — how are you managing that today?

---

## Recommendation

- **Default to Archetype A** for connection requests — it is the lowest-friction path to acceptance.
- **Test B against A** per segment. B may outperform when the signal is strong enough to make the hypothesis feel credible.
- Never lead with a pitch. The pitch belongs in the DM sequence *after* the connection is accepted.

---

## Quality Rules

| Rule | Criterion |
|------|-----------|
| **Personalization** | Include at least one specific signal about the contact or their company. No signal = no send. |
| **Relevance** | Connect the signal to a plausible challenge for that industry or operational scale. |
| **Brevity** | Eliminate any phrase that does not add personalization, context, or intent. Three lines max. |
| **Naturalness** | Prefer conversational English over corporate jargon. Write like a peer, not a vendor. |
| **Uncertainty** | Frame the problem as a question, not a confirmed diagnosis. "Tends to..." not "You have..." |
| **Single objective** | Prioritize connecting and starting a conversation. Leave the pitch for after they accept. |
| **CTA** | Use one simple question. Never stack multiple questions or add commercial requests. |
| **Veracity** | Never fabricate metrics, challenges, recognitions, or systems the prospect uses. Only use verifiable signals. |

---

## What to Avoid

- **Generic compliments:** "Impressive profile" / "Love what you're building" — meaningless without signal.
- **Leading with yourself:** "We are a platform that..." — the invite is about them, not you.
- **Presumptuous diagnoses:** "You probably struggle with [X]" — frame as hypothesis, not fact.
- **Commercial CTAs:** "Book a demo" / "Let me show you" — the invite is a conversation opener, not a sales pitch.
- **Stacked questions:** "Is that a priority? Would you be open to chatting? Can I send more info?" — one question only.
- **Invented data:** Never fabricate metrics, tools, or operational details about the prospect.
- **Over-length:** LinkedIn invite notes have a 300-character limit. If you cannot fit it, cut the hypothesis — keep the signal and the question.

---

## Character Limit Constraint

LinkedIn invite notes are capped at **300 characters**. This constraint enforces discipline:

- Archetype A typically fits comfortably (~150–250 chars).
- Archetype B must be tighter (~220–290 chars) — prioritize signal quality over hypothesis detail.
- If a message exceeds 300 chars, cut Block 2 (hypothesis) first. Blocks 1 and 3 are non-negotiable.

---

## Integration with Outreach Sequence

1. **Invite note** (this skill) → Connection request with personalized note
2. **Connection accepted** → `linkedin-dm` skill takes over with the DM sequence
3. **No reply after invite** → Wait for connection acceptance before any further touch

The invite note is **step 0** in the sequence. Its only job is to get accepted. The DM sequence (handled by `linkedin-dm`) is where the conversation continues.

---

## QA Checklist (self-check before sending)

- [ ] Contains at least one specific, verifiable signal about the prospect or company
- [ ] Signal is connected to a plausible operational challenge (not generic)
- [ ] Challenge is framed as a question/hypothesis, not a confirmed diagnosis
- [ ] Contains exactly one low-friction CTA question
- [ ] No commercial pitch, no product mention, no meeting request
- [ ] No fabricated data or invented operational details
- [ ] Under 300 characters
- [ ] Reads like a peer wrote it, not a vendor
- [ ] If no verifiable signal exists → **do not send** (fall back to no-note request or skip)
