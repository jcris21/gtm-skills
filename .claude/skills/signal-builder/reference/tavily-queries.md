# Tavily Query Templates

Query templates for the Tavily Discovery Scan (signal-builder Step 2). Each template produces a search query; the agent fills in bracketed variables from the prospect's data and the loaded offer/ICP context.

---

## Company-Specific Queries

These target the prospect company directly. Always include at least one.

| Template | When to use |
|----------|-------------|
| `"[Company Name]" press release announcement` | Always — catches official company news |
| `"[Company Name]" hiring expansion growth team` | When ICP's Growth Signal includes headcount/expansion |
| `"[Founder/CEO Name]" interview podcast blog` | When founder/CEO name is known from prospect data |
| `"[Company Name]" funding raise investment round series` | Only when ICP's Growth Signal names financing events |
| `"[Company Name]" partnership integration launch product` | When the company is in a partnership-heavy industry |
| `"[Company Name]" challenges problems navigating` | When you need to find pain signals or operational struggles |
| `"[Company Name]" case study results customer` | When looking for proof points or customer stories to reference |

## Sector / Trend Queries

These find industry-level signals that contextualize the prospect's situation. Include 1-2 tied to offer.md's pain point.

| Template | When to use |
|----------|-------------|
| `[Industry] trends challenges [current year]` | Always — establishes sector context |
| `[Pain point category] solutions [industry]` | When the offer solves a specific, nameable problem |
| `[Competitor category] market landscape comparison` | When mapping the competitive space |
| `[Industry] technology adoption shifting tools` | When the offer is a tech/tool replacement play |
| `[Industry] regulation compliance changes` | When regulatory shifts create buying urgency |

## Competitive Queries

These surface competitor-specific intelligence. Include when a direct competitor is known or likely.

| Template | When to use |
|----------|-------------|
| `"[Company Name]" vs alternative competitor [your category]` | When comparing against known competitors |
| `"[Competitor name]" problems complaints negative review` | When you want switching-intent signals |
| `"[Company category]" best tools comparison review` | When prospect is likely in evaluation mode |

## Query Construction Rules

1. **Always include at least 1 company-specific query** — the prospect's own news is the highest-signal starting point.
2. **Include CEO/founder query if the name is known** — executive content reveals strategy and priorities.
3. **Include 1 sector query tied to offer.md's pain point** — this finds external validation of the problem.
4. **Skip funding queries if ICP's Growth Signal doesn't mention financing** — don't waste a query slot on irrelevant signal types.
5. **Max 5 queries per scan** — controls API costs while maintaining coverage.
6. **Use current year in date-bounded queries** — stale results waste extraction budget.
7. **Quote company names** — prevents false positives from common words.
8. **Use OR for alternative terms** — `"hiring OR recruitment OR talent"` broadens without losing focus.

## Query Adaptation

Adapt templates based on available data:

- **No founder/CEO name?** Skip CEO queries, add a company-specific query instead.
- **No industry data?** Use the company's own website positioning to infer the industry, then query that.
- **Niche company with few results?** Widen to sector-level queries and look for the company in broader industry roundups.
- **Very large company?** Add location-specific queries (`"[Company] [City] office expansion"`) to find local signals.

## Cost Control

At 5 queries × 5 results each = 25 Tavily results per scan. With the free tier (1,000 searches/month):
- ~40 signal scans per month before hitting the limit
- For higher volume, consider `search_depth: "basic"` on all queries (uses fewer API credits)
- Track usage if running batch scans on prospect lists
