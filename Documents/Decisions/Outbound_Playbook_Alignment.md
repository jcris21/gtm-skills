# Outbound Playbook Alignment — Systems-Thinking Impact Analysis

A cold-outbound playbook (intent-based segmentation / Buyer Intent Pyramid, segment-based prioritization, who-to-contact orchestration, persona-driven messaging, the subject-line/opener/pain-hypothesis/proof/CTA email formula, follow-up cadence) was checked point-by-point against the current outbound system (`signal-builder`, `job-search`, `prospect-posts`, `creative-variable`, `email-writer`, `linkedin-dm`, `attio-crm`, `reply-handler`, `gtm-context`, `context/icp.md`, `context/offer.md`, `context/crm/attio-schema.md`, `utils/unipile.py`). The system is not starting from zero — several playbook ideas are already built, some more rigorously than the playbook itself describes. Others are real gaps. The point of this document is to say, for each playbook point, exactly what's already there, what's missing, which file(s) would change to close the gap, and whether closing it would actually **improve** the system or risk **degrading** something the current design already got right on purpose.

## Implementation status (2026-08-05)

Points 1, 3, 4, 6, 7, 8, 9, and 10 are now implemented. Points 2 and 5 remain deferred, as originally scoped (infrastructure and data-availability blockers, not effort). Implementation followed one added constraint beyond what's written below: **no skill file hardcodes ICP-specific facts** (industries, company-size numbers, persona copy, funding relevance). Every skill that needs ICP detail — `signal-builder`, `job-search`, `email-writer`, `linkedin-dm`, `creative-variable` — now loads it dynamically from `context/icp.md` (and the new `context/playbooks/segment-stories.md`) at runtime instead. `context/icp.md` and `context/crm/attio-schema.md`'s generic-superset enums are the only places ICP peculiarities live; if the ICP changes, only those files should need edits, not the skill logic. `signal-types.md`'s funding-round category is a case in point: rather than deleting it outright (which would hardcode "never funded" the same way the original text hardcoded "always funded"), it's now conditional on what `context/icp.md`'s Growth Signal field says.

## Summary

| # | Point | File(s) to change | Type | Priority |
|---|-------|--------------------|------|----------|
| 6 | Persona-driven message branching | `email-writer/skill.md`, `linkedin-dm/skill.md` | Edit | **Top** — reuses data already collected, biggest structural gap found |
| 1 | Reconcile signal-score scales, drop funding-round signal (ICP mismatch), name competitor-content signal | `job-search/skill.md`, `signal-builder/skill.md`, `context/crm/attio-schema.md` | Edit | High — low effort, removes silent disagreement between two skills and a signal type this ICP doesn't produce |
| 8 | Tier follow-up cadence by signal strength | `email-writer/skill.md`, `linkedin-dm/skill.md` | Edit | High — resolves the clearest improve-vs-degrade tension |
| 3 | Segment story library | new `context/playbooks/segment-stories.md` + edits to `email-writer`, `linkedin-dm` | New file + edits | Medium |
| 4 | Contact-count / bottom-up-top-down table | `context/icp.md` | Edit | Medium — cheap, mostly a documentation gap |
| 9 | Shared cross-channel touch counter | `context/crm/attio-schema.md`, `email-writer/skill.md`, `linkedin-dm/skill.md` | Edit | Medium — sequence after #8 |
| 10 | Tighten "novel" variable justification | `creative-variable/skill.md` | Edit | Low — small tightening, already mostly aligned |
| 7 | Proof-story sourcing | `email-writer/skill.md` | Edit | Low — depends on #3 |
| 2 | Real-time intent alerting | new `Documents/n8n_Signal_Alert_Automation.md` (spec only) | New spec doc | Deferred — highest infrastructure effort |
| 5 | In-account seniority/tenure prioritization | new `.claude/skills/contact-prioritizer/skill.md` | New skill | Deferred — required data isn't captured today |

---

## 1. Intent-based segmentation — how much is actually built

The playbook's "Intent-based segmentation" section makes five distinct asks. Scoring each against what's actually implemented (not just "gap / no gap"):

**(a) Identify high-intent signal types** — playbook names job postings, funding rounds, and engagement with competitor content. The funding-round signal doesn't transfer as-is: the playbook example assumes a VC-backed/startup buyer, and this ICP is the opposite — 15-100 employee wholesale, distribution, import/export, e-commerce, light-manufacturing, and consumer-goods companies (`context/icp.md:4`), which are traditionally financed operating businesses, not funding-round companies. Scoring each against what's actually implemented:
- **Job postings — fully covered**, by two skills: `job-search`'s TheirStack-based scanner (`job-search/skill.md:95-99`: High 8-10 / Medium 5-7 / Low 1-4 / None 0) and `signal-builder`'s own categories ("active job post for a role your product replaces or augments," `signal-builder/skill.md:55`).
- **Funding rounds — implemented, but a mismatch for this ICP and should be removed rather than credited as a strength.** `signal-builder/skill.md:57` currently lists "Recent event (funding, acquisition, expansion) that creates immediate need" in the top (8-10) tier, and `context/crm/attio-schema.md:218` defines a `trigger_event` enum that includes `funding` as a first-class value, backed by a `companies.funding_stage` attribute (`attio-schema.md:29`). None of that reflects how this ICP actually grows — a wholesale/distribution/light-manufacturing operator in this size band isn't raising Series B rounds. Carrying this category forward invites the system to chase or wait on a signal that will rarely, if ever, fire true for a real prospect, while diluting rubric attention that should go to signals this ICP actually produces (headcount growth, expansion into new SKUs/warehouses, existing-ERP pain). Treat this as a signal type to **delete**, not keep.
- **Engagement with competitor content — not covered.** `signal-builder`'s competitor-related category is "using a direct competitor with visible friction" (`signal-builder/skill.md:54`) — that's tech-stack/tool usage, not content engagement. There's no category for "liked/commented on a competitor's LinkedIn post," and `attio-schema.md`'s `trigger_event` enum has no matching value. The only path to catching this is running `prospect-posts` manually with "competitor" as the scan theme — nothing routes that into a signal score automatically.
- **Net: of the playbook's 3 named signal types, 1 (job postings) is solidly implemented and worth keeping, 1 (funding rounds) is implemented but should be removed as an ICP mismatch, and 1 (competitor-content engagement) is a real, narrow gap worth closing.**

**(b) Categorize leads by signal strength (playbook: 3-tier High/Medium/Low)** — implemented, and more granular than the playbook, but **fragmented across two unreconciled scales**: `signal-builder` runs its own 4-tier 1-10 rubric (`signal-builder/skill.md:53-72`), `job-search` runs a separate 4-tier High/Medium/Low/None heuristic (`job-search/skill.md:95-99`) that is never mapped onto signal-builder's numbers. Both write into the same `signal_score` field conceptually, but nothing in either file states how a job-search "High" becomes a signal-builder "8-10." The concept is more mature than the playbook's 3 buckets; the execution is split.

**(c) Tailor messaging to intent level** — implemented (~80%) via `email-writer`/`linkedin-dm`'s score-driven pattern selection: Pain-led for score 7+ (`email-writer/skill.md:76`), Value-led for strong enrichment (`:77`), Segment fallback for score 3-6 (`:78`). This is a working analog to the playbook's High/Medium/Low messaging split — the gap is that it's driven by signal score alone, not combined with persona (see point 6).

**(d) Tie the intent signal to the pain it causes, don't just state the event** — the playbook's own "Weak vs. Strong Outreach" example (don't say "congrats on your funding," say what the funding round is about to strain). **Fully implemented, and enforced as a hard rule**, arguably exceeding the playbook: `signal-builder`'s "Situations over demographics" rule (`signal-builder/skill.md:123`: "Describe what the prospect's team is dealing with, not just what the company looks like on paper") plus `email-writer`'s hard-rule QA checklist item "First line describes THEIR situation, not your product" (`email-writer/skill.md:93,108`) already do exactly what the playbook's example asks for.

**(e) Real-time AI alerting when a signal fires** — **0% implemented.** Both `signal-builder` and `job-search` are pull-only, invoked on demand; there is no monitoring/push layer. See point 2.

**Net measure: 4 of 5 sub-asks are solidly built (a mostly, b, c, d), with two concrete integration gaps (two unreconciled scoring scales; one missing signal type) and one fully absent capability (e).** Intent-based segmentation as a concept is one of the more mature parts of this system, not a blank slate.

**Proposed change:**
- Edit `.claude/skills/job-search/skill.md`'s "Signal strength heuristics" (`:95-99`) to output on `signal-builder`'s 1-10 scale directly (conversion: High→8-10, Medium→5-7, Low→1-4, None→0-2) instead of a separate label set.
- Edit `.claude/skills/signal-builder/skill.md`'s Step 4 rubric (`:53-72`) to cite job-search's mapped score as one input, remove "funding" from the "Recent event (funding, acquisition, expansion)" bullet at `:57` (keep "acquisition, expansion" — those can still apply to a traditionally financed operating company; funding rounds specifically cannot), and add "engagement with competitor's content (LinkedIn, blog comments)" as an explicitly named signal category (likely 5-7 tier, alongside "adjacent/related tools").
- Remove `funding` from `context/crm/attio-schema.md:218`'s `trigger_event` enum and drop the `companies.funding_stage` attribute at `attio-schema.md:29` — neither reflects a real data source for this ICP. Add `competitor_engagement` as its replacement value in the same enum.

**Leverage:** high, low effort → **improves** the system by removing silent disagreement between two skills, dropping a signal category that doesn't match this ICP, and closing one named content gap. Does not require new infrastructure.

---

## 2. Real-time AI alerting on intent signals

**Current:** `signal-builder` and `job-search` only run when a user explicitly invokes them (`signal-builder/skill.md:5-13`, `job-search/skill.md:5-13`). There is no scheduler, webhook, or monitoring loop that re-scans tracked accounts and pushes a notification when a signal crosses a threshold. This is the playbook's clearest unimplemented ask ("Set up AI-powered alerts to notify SDRs when a target company shows an intent signal").

**Proposed change:** this isn't a skill edit — Claude Code skills are pull-invoked by design, so "real-time" requires infrastructure outside a skill.md file. Precedent already exists for this pattern: `Documents/n8n_Reply_Handler_Automation.md` is a drafted (not yet built) n8n workflow that ports `reply-handler`'s logic to an HTTP-triggered automation because the reply-handling use case also needed an entry point skills don't have. Mirror that: draft `Documents/n8n_Signal_Alert_Automation.md` — a scheduled n8n job that periodically re-runs `job-search` + `signal-builder` logic (via their underlying CLIs, `utils/theirstack.py` and the website-scan logic) against a tracked-account list, and posts a Slack message / creates an Attio task when a composite score (once point 1's reconciliation lands) crosses a threshold (e.g. ≥8).

**Leverage:** medium/high value, but the highest infrastructure cost of all ten points (new scheduler, new webhook target, ongoing hosting) → **improves** the system if built, but is the one point where "adopt the playbook" means "build new infrastructure," not "edit an existing file." Scoped as a spec-only deliverable for now, same as the reply-handler automation currently sits in draft.

---

## 3. Segment-based prioritization / named use-case story library

**Current:** `context/offer.md` defines the Track A (pre-system) / Track B (stuck-with-a-system) split (`context/icp.md:9`), and `email-writer`'s Segment-fallback pattern (`email-writer/skill.md:56-61`) already writes to "the most common pain for their profile" when signals are moderate. What's missing is what the playbook's Snowflake example has and this system doesn't: a **persisted library of named customer stories/proof points per segment**. Today, every campaign re-derives proof points from `offer.md`'s general value prop rather than pulling a specific, reusable story ("Media & Gaming companies using X saw Y").

**Proposed change:** new file `context/playbooks/segment-stories.md` — one entry per vertical from `context/icp.md`'s industry list (Wholesale, Distribution, Import/Export, E-commerce, Light Manufacturing, Consumer Goods) and per Track (A/B), each with: named use case, specific proof point/metric, and the jargon that segment actually uses (mirrors the playbook's "specific customer stories / namedropping / specific jargon" pattern). Edit `email-writer/skill.md`'s Step 2 ("Load offer context," `:68-74`) and the Value-led/Segment-fallback pattern descriptions (`:44-61`) to read this file when drafting the Insight/proof line, instead of inventing proof language per campaign. Mirror the same edit in `linkedin-dm/skill.md`'s Step 2 (`:38-39`).

**Leverage:** medium → **improves** consistency and campaign-writing speed. Small risk flagged: a story library only helps if kept current — if segment-stories.md isn't refreshed as new customers close, it becomes a source of stale/generic proof points, which is worse than deriving proof fresh each time. Recommend a refresh trigger (e.g., update after every closed-won deal) rather than treating it as a one-time write.

---

## 4. Who to contact per account — contact count and bottom-up vs. top-down

**Current:** `context/icp.md` has a 6-persona table (`:41-48`) and a star-priority ranking (`:51-58`, Founder/CEO and COO/VP Ops at ⭐⭐⭐⭐⭐) — this answers "who matters most," but nothing in the system states **how many** contacts to pursue per account, or whether to start at the top (Founder/CEO) or bottom (Operations Manager) of that ranking for a given deal size.

**Proposed change:** add a "Contact Orchestration" table to `context/icp.md`, keyed to the existing company-size field (15-100 employees is the whole current ICP band, so this would likely be a sub-band split, e.g. 15-40 vs. 40-100 employees) mapping to recommended contact count and default direction (top-down, given the existing star table already privileges Founder/CEO and COO as the top two priorities — this is a documentation decision, not new data collection). No skill logic changes required; `email-writer`/`linkedin-dm` would consume this once persona branching (point 6) exists and needs to know how many personas to sequence per account.

**Leverage:** low effort, medium value → **improves**, mostly closes a documentation/decision gap rather than a code gap.

---

## 5. AI-based in-account lead prioritization (org hierarchy, seniority, tenure, trajectory, timing)

**Current:** nothing in the system scores individual contacts *within* one account by these dimensions. `icp.md`'s star table ranks personas (roles), not individual people; there's no tenure/trajectory data source wired in.

**Proposed change:** a new skill, `.claude/skills/contact-prioritizer/skill.md` — given a company and a set of known contacts, rank them against `icp.md`'s persona star-ratings plus whatever seniority signal is available. **This is flagged as only partially buildable today**: `utils/unipile.py`'s `find_profile()` (`utils/unipile.py`) resolves a LinkedIn identifier to a provider ID and connection distance, but does not expose tenure or job-change-trajectory data — Unipile's API would need a richer profile-fetch call, or a paid enrichment source (Apollo/Clay), to actually deliver "tenure" and "trajectory" as the playbook describes. Without that, this skill would only be able to rank by persona-title-match, which point 6 already does implicitly once built.

**Leverage:** highest effort and most uncertain data availability of all ten points → **improves in theory, adopt cautiously.** Recommend deferring until a tenure/trajectory data source is confirmed available; building it now would mean shipping a skill whose scoring dimensions the system can't actually populate.

---

## 6. Persona-driven messaging branching — the centerpiece finding

**Current:** `email-writer`'s pattern selection (Step 3, `email-writer/skill.md:75-79`) and `linkedin-dm`'s mirrored version (`linkedin-dm/skill.md:44`) branch **only on signal score** — Pain-led / Value-led / Segment fallback. Both skills already collect prospect `role` as a **required input** (`email-writer/skill.md:10`: "Prospect info (required) — first name, company name, role"; `linkedin-dm/skill.md:17`), and `context/icp.md` already defines six distinct personas each with its own "Top 3 Challenges," "Symptoms," "Impact on KPIs," and "Benefit" language (`icp.md:41-48`) — e.g. Founder/CEO's benefit framing is "reduces operating costs and removes dependency on agencies" while CIO/IT Director's is "lower technical debt and reduced reliance on external developers." None of that per-persona language is currently read by either writing skill. The signal tells you *what to lead with*; the persona table already tells you *how to frame it*, and the two are never combined.

**Proposed change:** edit `email-writer/skill.md`'s Step 3 and the three pattern templates (`:30-61`) so pattern selection becomes a 2D matrix — signal-score tier (unchanged) × persona matched from `icp.md`'s `role` field — instead of 1D. Concretely: the same Pain-led Line 2 (Insight) would pull its framing from the matched persona's "Symptoms"/"Impact on KPIs" columns rather than being freshly invented per campaign (CFO gets cash-flow/reporting framing per `icp.md:46`, CIO gets technical-debt/integration framing per `icp.md:47`, Operations Manager gets administrative-overload framing per `icp.md:45`). Mirror in `linkedin-dm/skill.md:41-44`. No new data collection is required — `role` is already a mandatory input field in both skills.

**Leverage:** highest of all ten points — reuses data the system already has, touches only two files, and closes the single largest structural gap found in the whole review → **strongly improves.** Top recommendation.

---

## 7. Subject line / opener / pain-hypothesis / proof / CTA formula

**Current:** already closely aligned with the playbook, and in most cases enforced as hard rules rather than guidelines: subject lines 2-5 words, lowercase, no punctuation tricks, no "Quick question" (`email-writer/skill.md:104,111,138`); opener describes the prospect's situation, not the product (`:93,108`); the Situation→Insight→Inquisition structure (`:24,34-37`) is a direct implementation of "opener-as-observation + pain-hypothesis"; CTA is explicitly required to be an inquisition, not a meeting ask (`:110`, mirrored in `linkedin-dm/skill.md:59`).

**Proposed change:** minimal — one dependent edit: once point 3's `segment-stories.md` exists, edit `email-writer/skill.md`'s Value-led pattern (`:44-54`) to require sourcing the proof line from that file rather than inventing it per campaign.

**Leverage:** low — this is validation of existing design, not a gap. The playbook's formula and this system's hard-rule QA checklist are, point for point, describing the same thing.

---

## 8. Follow-up cadence (playbook: 5-7 touches over 2-3 weeks) vs. current fixed cadence

**Current:** `email-writer` runs exactly 3 touches — Day 1, Day 3-4, Day 7-8 (`email-writer/skill.md:84-87`) — and `linkedin-dm` runs exactly 2 — Day 1, Day 3-4 — with an explicit design rule against adding a third: "No Email 3 equivalent — if two DMs don't land, the channel isn't the fix; revisit the signal" (`linkedin-dm/skill.md:51`). That's 5 touches total across both channels if a prospect has both, but capped at 8 days, well short of the playbook's 2-3 week window, and the cadence is fixed regardless of signal strength.

**Proposed change:** edit `email-writer/skill.md`'s Step 5 (`:84-87`) and `linkedin-dm/skill.md`'s Step 5 (`:50-51`) to tier cadence by signal score instead of using one fixed schedule:
- Score 8-10 → extend to up to 5 email touches over 3 weeks (justified by high-confidence signal, matching the playbook's volume guidance where it's most likely to pay off).
- Score 3-7 → keep the current 3 email + 2 LinkedIn touches.
- Score 1-2 (fallback-only) → keep the current minimum; explicitly do not extend.

**Leverage:** medium, but this is **the clearest improve-vs-degrade tension in the entire analysis.** Uniformly adopting "5-7 touches" for every prospect — which is what a literal playbook adoption would mean — risks overloading `reply-handler` and the AE queue, and increases deliverability/brand risk on low-signal prospects who were never going to convert. The current system's "revisit the signal instead of adding a third touch" rule is a deliberate, considered anti-spam stance, not an oversight. The tiered proposal captures the playbook's upside (more reps against prospects worth it) without discarding that stance — recommend this as a **partial, conditional adoption**, not a straight copy of the playbook's numbers.

---

## 9. Multi-channel orchestration — shared touch state across email + LinkedIn

**Current:** `linkedin-dm` already runs in parallel with `email-writer` whenever a LinkedIn identifier exists, independent of whether the prospect also has an email (`linkedin-dm/skill.md:7-10`) — this is already a close match to the playbook's "vary channels" guidance, and arguably more decisive than the playbook itself (the playbook doesn't specify a firing rule this precise). The gap: each channel's cadence and send-gate (`email-writer/skill.md:119-126`, `linkedin-dm/skill.md:65-72`) is tracked independently — there's no single counter for "how many total touches has this prospect received across both channels."

**Proposed change:** extend `context/crm/attio-schema.md`'s Notes/Tasks schema with a shared "combined touch count" tracked per Person record; edit both skills' send-gate steps (`email-writer/skill.md:119`, `linkedin-dm/skill.md:65`) to check/increment that shared counter before sending, so the tiered cadence from point 8 is enforced across channels, not per channel.

**Leverage:** medium, and only meaningful once point 8's tiering exists → **improves**, but sequence it after point 8, not before.

---

## 10. "Don't over-personalize" AI pro-tip

**Current:** already well-aligned. `creative-variable`'s coverage rule — ">80% can stay hardcoded, 40-80% should be variablized, <40% must be removed or segmented" (`creative-variable/skill.md:73`) — and its "reuse before invent" rule (`:38,153`) already guard against exactly what the playbook warns about (forced personalization, e.g. "I see you studied chemistry..."). `email-writer`'s variable rules cap at 3 variables per email and treat exceeding that as a targeting problem, not a personalization opportunity (`email-writer/skill.md:179`: "Don't over-variablize — if >3 variables per email, the targeting probably needs tightening instead"). The one soft spot: the "novel" archetype escape hatch (`creative-variable/skill.md:63,68`) already requires "justification" but doesn't specify what a valid justification looks like, leaving room for drift back toward the playbook's warned-against forced personalization.

**Proposed change:** edit `creative-variable/skill.md`'s Step 3/Step 4 novel-archetype language (`:63,68`) to require the justification name a specific pain point from `icp.md`'s persona table, or the variable is rejected back to one of the four standard archetypes.

**Leverage:** low — validation with a small tightening edit, not a gap.

---

## Closing synthesis

Ranked by leverage (impact achievable per unit of change effort), not by playbook order:

1. **Point 6 (persona-driven message branching)** — the single highest-leverage change. It closes the biggest structural gap found, uses data the system already collects (`role` is a required field in both `email-writer` and `linkedin-dm`, and `icp.md` already has the per-persona framing language), and touches only two files.
2. **Point 1 (reconcile the two signal-score scales)** — low effort, removes a real structural risk (two skills silently disagreeing about how strong a signal is). The analysis also surfaced that one existing signal category — funding rounds — doesn't fit this ICP at all (traditionally financed wholesale/distribution/light-manufacturing operators, not VC-backed startups) and should be removed from `signal-builder` and `attio-schema` rather than kept; competitor-content engagement remains the one genuine missing category to add.
3. **Point 8 (tiered follow-up cadence)** — the one place a naive playbook adoption would actively **degrade** the system if copied literally (uniform 5-7 touches risks reply-handler overload and deliverability damage on low-signal prospects). The tiered version is the recommended resolution: adopt the playbook's volume upside only where the system's own signal-strength logic says it's earned.

Everything else (points 2-5, 7, 9-10) is either a smaller, more mechanical edit, or — for points 2 and 5 specifically — genuinely blocked on infrastructure or data the system doesn't have yet, and is called out as deferred rather than force-fit into this pass.
