# Batch 2 Pipeline Results

**Batch:** batch-2026-09-28-batch2
**CSV Source:** context/Batch2.csv
**Processed:** 2026-09-28
**Manifest:** batches/batch-2026-09-28-batch2/manifest.json

---

## Summary

| Metric | Count |
|---|---|
| Total CSV rows | 20 |
| Duplicates removed | 0 |
| Failed pre-screen | 0 |
| Entered pipeline | 20 |
| Completed (inserted to Sheet) | 15 |
| Rejected (ICP gate) | 5 |

---

## Rejected — ICP Gate

| Lead | Company | Reason |
|---|---|---|
| Vikas Indore | TallySolutions | Kuwait-based, already a Tally ERP partner |
| Vigyan Kaushik | Quantic | SaaS/POS software company, not operations |
| Kelly Long | The Arc Nature Coast | Nonprofit disability services |
| Diego Bellalta | GRAX | SaaS data backup software company |
| Jevgenij Polonis | GoRamp | B2B dock scheduling software vendor |

---

## Completed — Inserted to OutboundQueue Sheet

| # | Lead | Company | Score | Signal Type | Pattern | Persona |
|---|---|---|---|---|---|---|
| 1 | Kerry Wekelo | Actualize Consulting | 1 | None | Segment-fallback | COO |
| 2 | Scott Carper | Ready Industries | 2 | Firmographic-only | Segment-fallback | CEO |
| 3 | Chris Wrightsman | Dynamic Management Associates | 1 | None | Segment-fallback | CEO |
| 4 | Franklin Byrd | Albers Aerospace | 4 | Growth-event | Pain-led | COO |
| 5 | Greg Sprink | Admiral Distribution | 4 | Growth-event | Pain-led | COO |
| 6 | Scott Lindner | Lindner Logistics | 3 | Content-signal | Value-led | CEO |
| 7 | Wayne Wudyka | CRDN | 3 | Growth-event | Value-led | CEO |
| 8 | Ken Monroe | Bostrom | 3 | Content-signal | Value-led | CEO |
| 9 | Robert Loukusa | FCP Services, Inc | 3 | Adjacent-hallback | Pain-led | COO |
| 10 | Jerrold Krystoff | Hospitality Development Group | 2 | Firmographic-only | Segment-fallback | CEO |
| 11 | Kimberly Shepherd | Status Hospitality Management | 4 | Growth-event | Pain-led | VP Operations |
| 12 | Terry Morrison | Performance Group, Inc. | 2 | Firmographic-only | Segment-fallback | COO |
| 13 | Frank Piliero | East Coast Warehouse & Fulfillment | 3 | Firmographic-only | Segment-fallback | COO |
| 14 | David Brooks | ARMADA Supply Chain Solutions | 6 | Growth-event | Pain-led | COO |
| 15 | Shane Murray | Accutite | 2 | Firmographic-only | Segment-fallback | President of Operations |

---

## Top Scores

| Lead | Company | Score | Signal Type | Key Signal |
|---|---|---|---|---|
| David Brooks | ARMADA Supply Chain Solutions | 6 | Growth-event | ATEC Systems acquisition, Dallas Hub opening, new CEO, Chorus partnership, McDonald's Supplier of the Year 2025 |
| Franklin Byrd | Albers Aerospace | 4 | Growth-event | Parallel Ventures acquisition, TAS division launch, "buy & build" strategy, 80+ employees |
| Greg Sprink | Admiral Distribution | 4 | Growth-event | Veteran-owned, grew from 1→3 Texas locations since 2017, 4 active job postings |
| Kimberly Shepherd | Status Hospitality Management | 4 | Growth-event | Active regional expansion (Utah + SoCal), hotel acquisitions, live career page |

---

## Sheet Status

All 15 completed leads are in the `OutboundQueue` Google Sheet with:
- `canal_envio`: LinkedIn
- `aprobado`: No (pending human review)
- `enviado`: No
- Drafts populated in `draft_linkedin`
- Full metadata (score, signal type, persona, angle, QA)

---

## Result Files

All 20 result JSONs are in `batches/batch-2026-09-28-batch2/results/`.
