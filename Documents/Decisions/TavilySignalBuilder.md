Plan: Upgrade Signal Builder — Tavily Discovery + WebFetch Deep Extraction

Context

The current signal-builder skill uses only WebFetch to scan a prospect's own website (homepage, about, careers, blog, etc.). This is reactive and limited — it only sees what the company publishes on its own domain.

The upgrade adds a two-phase research pipeline:

1. Phase 1 — Tavily Discovery: Search the broader internet for external signals (press releases, CEO interviews, sector news, funding announcements, industry problems). Tavily returns relevant URLs + summaries.
2. Phase 2 — WebFetch Deep Extraction: Use WebFetch to extract full content from the most promising URLs discovered by Tavily.

This compounds the signal quality: Tavily finds what the world says about the prospect; WebFetch reads the full context. Combined with the existing website scan, the signal-builder gets 3 data streams instead of 1.

---

Files to Modify

File: .claude/skills/signal-builder/skill.md
Change: Restructure Steps 1-2 into Tavily discovery → WebFetch extraction;
keep Steps 3-6 mostly intact
────────────────────────────────────────
File: .claude/skills/signal-builder/reference/signal-types.md
Change: Add external-source field to signal entries (Tavily-sourced signals
vs. website-sourced)
────────────────────────────────────────
File: .env.example
Change: Add TAVILY_API_KEY variable
────────────────────────────────────────
File: utils/sheet_queue.py
Change: Add fuente_senal column to TRANSPARENCY_COLUMNS (tracks whether
signal came from website/Tavily/both)

New file

File: .claude/skills/signal-builder/reference/tavily-queries.md
Purpose: Query templates for different signal types (funding, hiring, CEO
content, sector news)

---

Detailed Changes

1. .claude/skills/signal-builder/skill.md — Restructure Steps

Step 0 (ICP hard-gate): Unchanged.

Step 1: Load context (was Step 1): Unchanged — load offer.md, icp.md, signal-types.md.

NEW Step 2: Tavily Discovery Scan

Replace the old "Fetch and analyze website" step with a Tavily-first approach:

### Step 2: Tavily Discovery Scan

Use the Tavily Search API to scan the internet for external signals about the prospect.

#### 2a: Build search queries

Generate 3-5 targeted queries from `reference/tavily-queries.md` templates:

1. **Company news**: `"[Company Name]" press release expansion hiring 2026`
2. **CEO/founder content**: `"[Founder Name]" interview podcast blog [industry topic]`
3. **Sector signals**: `[industry] trends challenges [pain point from offer.md]`
4. **Competitive landscape**: `"[Company Name]" vs OR alternative OR competitor [your category]`
5. **Funding/growth**: `"[Company Name]" funding raised series round`

Adjust queries based on what data is available (skip CEO queries if no founder name; skip funding if ICP doesn't match).

#### 2b: Execute Tavily searches

For each query, use the Tavily Search API:
- `search_depth: "advanced"` for company-spresults)
- `search_depth: "basic"` for sector/trend queries (broader coverage)
- `max_results: 5` per query
- `include_answer: true` to get Tavily's synthesized summary
- `include_raw_content: false` (WebFetch handles full extraction in next step)

#### 2c: Rank and select URLs for extraction

From all Tavily results, rank by relevance:
- **Tier 1 (must-extract)**: Official company press releases, CEO-authored content, recent news (< 90 days)
- **Tier 2 (should-extract)**: Industry analysis mentioning the company, competitor comparisons, job market signals
- **Tier 3 (skip)**: Generic industry news with no direct company mention, results older than 6 months

Select top 3-5 URLs for deep extraction. Deduplicate by domain.

#### 2d: Output intermediate findings

Before proceeding to Step 3, output a brief discovery summary:
Tavily Discovery: [Company Name]

Queries run: [list]
Total results: [N]
Tier 1 URLs (must-extract): [list with titles + summaries]
Tier 2 URLs (should-extract): [list with titles + summaries]
Key finding: [1-sentence synthesis of most actionable discovery]


Step 3: WebFetch Deep Extraction (was Step 2)

Restructure into two sub-steps:

### Step 3: WebFetch Deep Extraction

Now combine two data streams:

#### 3a: Extract Tavily-discovered URLs

For each Tier 1 and Tier 2 URL from Step 2:
- Use `WebFetch` with `prompt: "Extract all factual information relevant to [offer.md's pain point]. Focus on: company strategy, challenges mentioned, technology choices, growth signals, executive quotes, competitive positioning. Return structured bullet points."`
- Capture the URL as `source_url` for transparency.

#### 3b: Scan prospect's own website (existing behavior)

Same as current Step 2 — scan homepage, about, careers, product/pricing, blog, footer/integrations.

#### 3c: Merge findings

Combine signals from both streams into a unified list. When the same signal appears from multiple sources (e.g., hiring signal from both Tavily news AND the careers page), boost its confidence score by +1.

Flag the source of each signal:
- `source: "tavily"` — found only via Tavily
- `source: "website"` — found only via website scan
- `source: "both"` — confirmed by multiple sources (highest confidence)

Steps 4-6: Unchanged (Identify signals, Rank signals, Recommend campaign approach, Log to Attio).

2. .claude/skills/signal-builder/reference/tavily-queries.md (New)

Query template library:

# Tavily Query Templates

## Company-Specific Queries
- `"[Company]" press release announcement 2026`
- `"[Company]" hiring expansion growth`
- `"[Founder/CEO Name]" interview podcast insights`
- `"[Company]" funding raise investment round`
- `"[Company]" partnership integration launch`
- `"[Company]" challenges problems navigating`

## Sector/Trend Queries
- `[Industry] trends challenges [current year]`
- `[Pain point category] solutions [industry]`
- `[Competitor category] market landscape`
- `[Industry] technology adoption shifting`

## Competitive Queries
- `"[Company]" vs OR alternative OR competitor`
- `"[Competitor name]" problems complaints`
- `"[Company category]" comparison review`

## Query Selection Rules
1. Always include at least 1 company-specific query
2. Include CEO/founder query if name is known
3. Include 1 sector query tied to offer.md's pain point
4. Skip funding queries if ICP's Growth Signal doesn't mention financing
5. Max 5 queries per scan to control API costs

3. .env.example — Add Tavily Key

# Tavily — used by signal-builder for internet discovery scans
# Get an API key at https://tavily.com
TAVILY_API_KEY=

4. utils/sheet_queue.py — Add Transparency Column

Add fuente_senal to TRANSPARENCY_COLUMNS to track signal origin:

TRANSPARENCY_COLUMNS = [
    "senal_detectada", "key_data_points", "fuente_variable",
    "fuente_senal",  # NEW: "tavily" | "website" | "both"
    "qa_rationale",
]

5. .claude/skills/signal-builder/reference/signal-types.md — Add Source 
1. Always include at least 1 company-specific query
2. Include CEO/founder query if name is known
3. Include 1 sector query tied to offer.md's pain point
4. Skip funding queries if ICP's Growth Signal doesn't mention financing
5. Max 5 queries per scan to control API costs

3. .env.example — Add Tavily Key

# Tavily — used by signal-builder for internet discovery scans
# Get an API key at https://tavily.com
TAVILY_API_KEY=

4. utils/sheet_queue.py — Add Transparency Column

Add fuente_senal to TRANSPARENCY_COLUMNS to track signal origin:

TRANSPARENCY_COLUMNS = [
    "senal_detectada", "key_data_points", "fuente_variable",
    "fuente_senal",  # NEW: "tavily" | "website" | "both"
    "qa_rationale",
]

5. .claude/skills/signal-builder/reference/signal-types.md — Add Source Field

Add a Source field to each signal entry's output description, indicating whether the signal was Tavily-sourced, website-sourced, or both. This is a documentation-only change to the output format guidance — the actual source tracking happens in skill.md's Step 3c.

---

Pipeline Impact Assessment

┌───────────────────┬──────────────────┬───────────────────────────────┐
│ Downstream Skill  │      Impact      │         Change Needed         │
├───────────────────┼──────────────────┼───────────────────────────────┤
│                   │ Positive —       │ No code changes; it already   │
│ email-writer      │ richer signal    │ consumes senal_detectada and  │
│                   │ data = better    │ key_data_points from the      │
│                   │ copy             │ Sheet queue                   │
├───────────────────┼──────────────────┼───────────────────────────────┤
│ linkedin-dm       │ Positive — same  │ No changes                    │
│                   │ as email-writer  │                               │
├───────────────────┼──────────────────┼───────────────────────────────┤
│                   │ Positive — more  │                               │
│ creative-variable │ sources for      │ No changes                    │
│                   │ variable         │                               │
│                   │ discovery        │                               │
├───────────────────┼──────────────────┼───────────────────────────────┤
│                   │ Positive —       │                               │
│ attio-crm         │ signal notes     │ No changes (note format is    │
│                   │ will include     │ flexible)                     │
│                   │ Tavily sources   │                               │
├───────────────────┼──────────────────┼───────────────────────────────┤
│                   │ Minor — new      │ Add fuente_senal to           │
│ sheet_queue.py    │ transparency     │ TRANSPARENCY_COLUMNS          │
│                   │ column           │                               │
└───────────────────┴──────────────────┴───────────────────────────────┘

---

Prerequisites / User Action Required

Tavily API Key: The user needs to:
1. Sign up at https://tavily.com (free tier: 1,000 searches/month)
2. Add TAVILY_API_KEY=tvly-xxxxx to .env

No MCP server needed: Tavily can be called via WebFetch (Tavily has a REST API at https://api.tavily.com/search) or via a simple Python utility. Since this is a Claude Code skill (not code), the skill instructs the agent to call the Tavily API directly.

---

Verification Plan

1. Dry run: Run signal-builder on Sébastien Aubert (Adastra Films) with the new two-phase pipeline
2. Compare output: Verify that Tavily finds signals the old WebFetch-only approach would miss (e.g., external press mentions, CEO interviews)
3. Check transparency: Confirm fuente_senal column populates correctly in Sheet output
4. Downstream flow: Run email-writer on the enriched signal to verify copy quality improvement
5. API cost check: Verify Tavily usage stays within free tier (1,000 searches/month) at expected scan volume

● Auto mode lets Claude handle permission prompts automatically — Claude checks each tool call for risky actions and prompt injection before executing. Actions Claude identifies as safe are executed, while actions Claude identifies as risky are blocked and Claude may try a different approach. Ideal for long-running tasks. Sessions are slightly more expensive. Claude can make mistakes that allow harmful commands to run, it's recommended to only use in isolated environments. Shift+Tab to change mode.

  Thought for 3s

Plan aprobado. Vamos a implementar.

  Thought for 10s

● Write(.claude\skills\signal-builder\reference\tavily-queries.md)
Error: [Fact-Forcing Gate]

Before creating E:\FILES 2026\Agentic GTM\Claude Project\.claude\skills\signal-builder\reference\tavily-queries.md, present these facts:

1. Name the file(s) and line(s) that will call this new file
2. Confirm no existing file serves the same purpose (search the tree — Glob/Grep, or find/grep via Bash)
3. If this file reads/writes data files, show field names, structure, and date format (use redacted or synthetic values, not raw production data)
4. Quote the user's current instruction verbatim

Present the facts, then retry the same operation.
… +2 lines

● Update(.env.example)
Error: [Fact-Forcing Gate]

2. Compare output: Verify that Tavily finds signals the old WebFetch-only approach would miss (e.g., external press mentions, CEO interviews)
3. Check transparency: Confirm fuente_senal column populates correctly in Sheet output
4. Downstream flow: Run email-writer on the enriched signal to verify copy quality improvement
5. API cost check: Verify Tavily usage stays within free tier (1,000 searches/month) at expected scan volume