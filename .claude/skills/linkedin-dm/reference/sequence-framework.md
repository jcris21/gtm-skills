# Sequence Framework (LinkedIn)

Rules for follow-up DMs, day spacing, angle rotation, and when to stop — the LinkedIn-adapted counterpart to `email-writer/reference/sequence-framework.md`. Design rationale lives in `Documents/LinkedIn_DM_NoReply_Activation_Strategy.md`; this file is the operative version the skill actually follows.

**Core rule: this sequence only runs in the absence of a reply.** Before drafting any follow-up, check for a reply first (§4). Any reply — any classification — cancels the rest of this sequence and hands off to `/reply-handler`. There is no state where both run at once.

---

## Sequence structure by tier

Touch counts come from `linkedin-dm/skill.md` Step 5 — this file doesn't change them, it adds timing, trigger, and content detail on top.

| Tier | Signal score | Touches | Schedule |
|---|---|---|---|
| Fallback | 1-2 | 1 | Message 1 only, no follow-up |
| Estándar | 3-7 | 2 | Message 1 (Day 1) → Follow-up (Day 3-4) |
| Alto | 8-10 | 3 | Message 1 (Day 1) → Follow-up A (Day 3-4) → Follow-up B (Day 10-12) |

**Why Follow-up B sits at Day 10-12, not Day 7-8 like email's Email 3:** email's own Alto tier already runs out to Day 18-21. Spacing LinkedIn's second follow-up further out keeps an Alto-tier prospect from getting an email and a DM on the same day (see cross-channel rule below). This is a design choice, not a measured optimum.

**Recommended send window:** Tuesday-Thursday, mid-morning to mid-afternoon — same principle as email's "not Monday before 10am, not Friday after 2pm" rule, carried over as a reasonable default since there's no LinkedIn-specific open-rate data behind it yet.

---

## Angle rotation

Never repeat Message 1's angle in a follow-up — same principle as email's rotation table, adapted to LinkedIn's shorter, casual format.

| Message 1 was... | Follow-up A rotates to... |
|---|---|
| Pain-led | Value-led (lighter touch) or social proof ("talked to a few companies in a similar spot...") |
| Value-led | Pain-led — now name the concrete cost of not solving it |
| Segment fallback | Social proof — segment-level pattern, not individual-level |
| Connection note (not yet connected) | If they accept, the first real DM effectively *is* Message 1 — it does not count as a follow-up against the tier's cap |

**Follow-up B (Alto tier only)** is always one of two things:
1. **Brief proof point** — one line from `context/playbooks/segment-stories.md` if a real entry exists for the prospect's vertical/track (never fabricate one — see `email-writer/skill.md`'s proof-sourcing rule, same principle applies here)
2. **Clean breakup** — see template below

**Content source (not repeated logic, just a pointer):** every touch's actual copy is resolved the same way `linkedin-dm/skill.md` Step 2/4 already does — persona matched against `context/icp.md`, proof point (if any) against `context/playbooks/segment-stories.md`. This file only says *when* and *which angle*, never invents copy itself.

### Breakup template (Follow-up B, Alto tier, when no proof point exists)

> "[Brief situation, 1 line]. If this becomes a priority, let me know — I'm around."

**Never:**
- "Just wanted to make sure this didn't get lost"
- "I reached out a few days ago..."
- Any variant of a guilt-trip bump

---

## Cross-channel coordination

When the prospect has both channels (`Canal(es) = Both`), `combined_touch_count` already caps the combined total (`context/crm/attio-schema.md`). Additional spacing rule: **never schedule a LinkedIn touch on the same day as an already-scheduled email touch** for the same prospect — minimum 1-day gap between any two touches across channels.

---

## Trigger check — required before drafting any follow-up

Before drafting Follow-up A or Follow-up B, verify all three, in order:

1. **Window elapsed?** — count from the most recent Touch record's `sent_at` (`context/crm/attio-schema.md`'s `touches` object).
2. **Any reply since the last touch?** — check the chat via Attio/Unipile. If any inbound message arrived since the last send, **stop here** — do not draft the follow-up. See "Handling replies" below.
3. **Tier cap already reached?** — check `combined_touch_count` against the tier's total (same gate `linkedin-dm/skill.md` Step 7 already enforces at send time).

Only proceed to draft the follow-up if (1) is true, (2) is false, and (3) is false.

This is a manual check today — the pipeline runs via Claude Code chat invocation, not a scheduler. It becomes automatic once real-time signal alerting is built (`Documents/Decisions/Outbound_Playbook_Alignment.md` point 2, currently deferred); this file doesn't depend on that automation to be useful now.

---

## Handling replies

This skill drafts the sequence — it doesn't classify replies (`/reply-handler` does). But the sequence must react correctly to a reply's presence:

- **Any reply arrives, any classification:** cancel all remaining touches in this sequence. Hand off to `/reply-handler`. Do not draft or send the next scheduled touch.
- **`OUT_OF_OFFICE` is the one exception:** don't cancel — pause. Resume the tier's remaining touches after the stated return date, recalculating windows from the resume point, not from the original Day 1.
- If `/reply-handler` produces its own outbound touch (e.g. an objection response), that touch counts against `combined_touch_count` but does not restart this sequence — this sequence already ended the moment the reply arrived.

---

## When to stop / when to re-engage

- Never send a touch beyond what the tier defines — no Touch 4 on any tier.
- Never send an off-schedule "bump" or "checking in."
- Re-engage only on a genuinely new signal (new job post, new growth event per `context/icp.md`'s Growth Signal field) — treat it as a new sequence with fresh context, not a continuation. Re-run `/signal-builder` for a fresh score before restarting.
