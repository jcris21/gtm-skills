# Gap Analysis — AI-Powered Outbound Strategy Framework vs. Current Pipeline

Audits the current pipeline (`.claude/skills/*`, `context/*`, `utils/*`) against the 4-block outbound framework supplied 2026-08-12 (Who to contact → AI lead prioritization → Persona-driven message → Outbound sequencing). This is a state-as-of-today audit, not a diff against `Documents/Decisions/Outbound_Playbook_Alignment.md` (2026-08-05) — that doc covers a similar but differently-organized 10-point framework and is the primary prior source; this doc re-verifies its "implemented" claims against the actual skill files (all confirmed current) and re-maps everything onto the framework as pasted.

**Verdict up front:** three of the four blocks are substantially built, most of it more rigorously than the framework itself specifies. The real gaps cluster in one block — AI lead prioritization — plus one channel gap inside sequencing that wasn't previously called out.

---

## 1. WHO TO CONTACT? (Account + Persona)

### Account qualification
**Built.** `signal-builder/skill.md` Step 0 is a hard ICP gate — company size, industry, geography, and buyer-role checked against `context/icp.md` before any scan runs; a lead that fails is disqualified with no CRM write. This is the "Account" half of the framework block.

### How many contacts, and who first
**Built, closely matching the framework's SMB/Mid-Market logic — but only two of the framework's three size bands apply, by design.** `context/icp.md`'s "Contact Orchestration" table:

| ICP sub-band | Contacts | Direction |
|---|---|---|
| 15–40 employees | 1–2 | Top-down — Founder/CEO or COO/VP Ops first |
| 40–100 employees | 2–3 | Top-down — primary contact first, layer in CFO/CIO once engaged |

This matches the framework's SMB (1–2, direct decision, short cycle) and Mid-Market (2–4, balance stakeholders) rows almost exactly. **The framework's Enterprise row (5+, multi-department, higher ACV) has no counterpart** — but that's a scope match, not a gap: the whole ICP caps at 100 employees (`context/icp.md:3`), so an enterprise band would describe accounts this system never targets. Flag only if the ICP itself ever expands upward.

### Bottom-up vs. top-down
**Only top-down is implemented — bottom-up doesn't exist as a path.** The framework offers both directions depending on product type (technical/end-user products → bottom-up adoption champion; strategic/executive products → top-down cascade). The current ICP's own persona star-table (`icp.md:51-58`) ranks Founder/CEO and COO/VP Ops highest, and every orchestration rule in the codebase (contact orchestration table, `email-writer`/`linkedin-dm` persona sequencing) is written top-down-only. This is consistent with the offer being a strategic/operational transformation sell, not a bottom-up PLG-style technical product — **not a gap for this specific ICP**, but worth naming explicitly: if the offer ever adds a technical/end-user entry point (e.g. selling to an Operations Manager as adoption champion before looping in the COO), there's no sequencing logic for that direction today.

**Net: solidly built for this ICP's actual shape. No file changes needed unless the ICP or motion changes.**

---

## 2. AI LEAD PRIORITIZATION — the weakest block

The framework names three prioritization dimensions. Scored individually:

### Organizational structure (hierarchy, reporting, departments)
**Not implemented.** Nothing in the pipeline maps a company's internal reporting structure. `icp.md`'s persona table ranks *role types* in the abstract ("COO ranks above Operations Manager"), but there's no per-account org chart — the system doesn't know, for a specific prospect company, who reports to whom.

### Persona / role (seniority, influence, decision power)
**Built, and this is the one dimension of the three that's genuinely mature.** `icp.md`'s 6-persona table (`:41-48`) plus its star-priority ranking (`:51-58`, ⭐⭐⭐⭐⭐ down to ⭐⭐⭐) gives every persona a decision-power rank, and `email-writer`/`linkedin-dm` Step 2 (confirmed live in both `skill.md` files) matches a prospect's `role` field against this table at write time, driving message framing per persona (see block 3).

### Context / timing (tenure, company trajectory, campaign context)
**Split — "campaign context" is built; tenure and trajectory are not.**
- **Campaign context** (i.e. is *now* a good time, based on signal) is well covered: `signal-builder`'s 1-10 rubric and `job-search`'s hiring-signal heuristic write to the *same* scale (confirmed in both `skill.md` files — job-search's Step 5 explicitly states it scores "0-10 directly on signal-builder's scale... so both skills write the same number into `signal_score` without a separate conversion step"). This resolves what the 2026-08-05 doc flagged as two unreconciled scales — verified fixed.
- **Individual tenure / trajectory** (how long has this specific person been in-role, are they newly promoted, is their career trajectory upward) has **no data source wired in at all.** `utils/unipile.py`'s `find_profile()` resolves a LinkedIn identifier to a provider ID and connection distance only — no tenure or job-change history.

### Net for this block
Two of three dimensions have real gaps. This mirrors the 2026-08-05 doc's Point 5, still correctly flagged as deferred — **not a regression, just still open.** Closing it requires either a richer Unipile profile call or a paid enrichment source (Apollo/Clay); there's no cheap fix here. A `contact-prioritizer` skill was proposed previously and correctly deferred — building it now would ship a skill with scoring dimensions (org hierarchy, tenure) the system still can't populate.

**This is the block to prioritize if "AI lead prioritization" is the framework element you care most about closing** — it's the one place where two of three sub-dimensions are still blank, versus every other block being mostly-to-fully built.

---

## 3. PERSONA-DRIVEN MESSAGE

### Buyer-type framing (Technical / Business / End-user)
**Built, more granular than the framework's 3-way split.** `context/icp.md`'s persona table covers 6 personas, each with distinct Top-3-Challenges / Symptoms / Impact-on-KPIs / Benefit language — e.g. CFO gets cash-flow/reporting framing, CIO gets technical-debt/integration framing, Operations Manager gets administrative-overload framing (`icp.md:41-48`). `email-writer/skill.md` Step 3 (confirmed live) states pattern selection is explicitly "two-dimensional: signal-score tier picks structure; matched persona picks Insight-line framing" — this is the framework's persona-driven branching, implemented as a real 2D matrix, not just a label.

### Three-layer message (Relevance / Pain / Proof)
**Relevance and Pain: built and enforced as hard QA rules.** The Situation→Insight→Inquisition structure (`email-writer/skill.md:24,34-37`) is a direct match: Situation = Relevance ("I understand your context"), Insight = Pain Hypothesis ("you may be facing X"), framed through the matched persona's own language, not generic copy.

**Proof: the mechanism exists, but the content behind it is currently empty.** `context/playbooks/segment-stories.md` is built exactly as designed — one entry slot per vertical × Discovery Track, with a strict "never fabricate a story" rule enforced in both `email-writer/skill.md` ("Proof sourcing" section) and the file itself. Read directly: **every single section in the file today reads `_No story yet — do not fabricate one._`** — zero of 12 vertical/track slots are populated. The fallback (generic `offer.md` value prop) is working as designed, but the framework's "Company X achieved Y" proof layer has no real ammunition yet. This is a content gap, not a code gap — the refresh trigger ("update after every closed-won deal") is documented but depends on deals actually closing and someone writing the entry back.

### Easy next step (yes/no question)
**Built and enforced as a hard rule in both channels.** CTA is required to be an inquisition ("Is this you?"), never a meeting ask — confirmed in `email-writer/skill.md` QA checklist and mirrored in `linkedin-dm/skill.md`.

**Net: the framework's message architecture is fully implemented mechanically. The one real gap is operational, not structural — the proof layer is a well-designed empty shelf.**

---

## 4. OUTBOUND SEQUENCING

### Touch volume and timing (framework: 5-7+ touches over 2-3 weeks)
**Built, but tiered — and deliberately not uniform, which is the correct call, not a shortfall.** Confirmed directly in both skill files:

| Signal tier | Email touches | LinkedIn touches | Combined max | Window |
|---|---|---|---|---|
| 8-10 (Alto) | 5 (Day 1, 3-4, 7-8, 12-14, 18-21) | 2 (Day 3-4, 10-12) | 7 | ~3 weeks |
| 3-7 (Estándar) | 3 (Day 1, 3-4, 7-8) | 1 (Day 3-4) | 4 | ~8 days |
| 1-2 (Fallback) | 2 (Day 1, 3-4) | 1 (Day 1 only) | 2-3 | ~4 days |

The framework's literal "5-7+ touches over 2-3 weeks" is matched almost exactly, but **only at the top signal tier.** Lower tiers deliberately stay short. This is the same tension the 2026-08-05 doc flagged (its Point 8) — a uniform "always 5-7 touches" reading of the framework would mean spamming low-signal prospects, which the pipeline's own design explicitly refuses to do ("a weak signal doesn't earn more attempts," `email-writer/skill.md:95`). Treat this as intentional divergence, not a gap.

### Channels (framework: Email / LinkedIn / Call)
**Two of three channels built; Call is a genuine, previously-unflagged gap.** Email and LinkedIn both run in parallel whenever a prospect has both identifiers, share a single `combined_touch_count` gate (`context/crm/attio-schema.md`), and each rotates angle/proof/insight per touch per the sequence-framework files. **Call has no equivalent anywhere in the system** — no skill, no cadence rule, and `context/crm/attio-schema.md`'s `touches.channel` enum is hard-limited to `Email` / `LinkedIn` (`attio-schema.md:70`), with no `Call` value. This wasn't called out in the 2026-08-05 doc (which only ever discussed the two channels that existed) — it's a real omission relative to *this* framework, not a regression.

### Measure response → qualify/meet or continue/change angle
**Built and matches the framework closely.** `reply-handler/skill.md` classifies replies into 6 categories and drives exactly the framework's two branches:
- **Positive → Qualify/meet:** `INTERESTED` triggers a Buyer Brief, an Attio task, and (if deal-size signals warrant) human escalation (`reply-handler/skill.md` Step 4).
- **No response → Continue/change angle/channel:** the sequence-framework files' angle-rotation tables (never repeat an angle touch-to-touch) plus explicit re-engage rules ("only on a genuinely new signal... re-run `/signal-builder` for a fresh score before restarting") cover the framework's "change angle / channel" branch directly.

**Net: sequencing is the most complete block overall, with one clean gap (no Call channel) worth a decision — is Call in scope for this pipeline at all, or is email+LinkedIn the intended full channel set?**

---

## Summary table

| Framework block | Status | Real gap(s) | File(s) if closing |
|---|---|---|---|
| 1. Who to contact | Built | None for current ICP; no bottom-up path if motion ever changes | — |
| 2. AI lead prioritization | **Weakest block** | Org hierarchy: not built. Tenure/trajectory: not built (blocked on data source, not effort) | new `contact-prioritizer` skill — hold until Apollo/Clay-grade enrichment is available |
| 3. Persona-driven message | Built (mechanism) | Proof layer has zero populated entries — content gap, not code gap | `context/playbooks/segment-stories.md` — needs real closed-won stories written in |
| 4. Outbound sequencing | Built, most complete block | No Call channel anywhere in the system | `attio-schema.md` `touches.channel` enum + a new call-logging path, only if Call is actually in scope |

## What to do next
1. **Decide if Call is in scope.** If yes, this is a real, scoped gap worth its own small plan (log-only at minimum — call outcomes into a Touch record — before any dialer/script skill).
2. **Populate `segment-stories.md`.** Zero-effort mechanically, pure operational discipline — write an entry the next time any deal closes.
3. **Org hierarchy / tenure prioritization stays correctly deferred** — don't build `contact-prioritizer` until a real data source (paid enrichment) is confirmed; a skill with unpopulatable scoring dimensions is worse than no skill.
