# Batch Lead Ingestion — Phase 2: Pipeline Processing

Process a batch of qualified leads through the outbound pipeline.

## Usage

```
/batch-ingest batches/batch-2026-09-08
/batch-ingest batches/batch-2026-09-08 --limit 1
/batch-ingest batches/batch-2026-09-08 --limit 5
```

## Arguments

- `$ARGUMENTS` — path to batch directory (required), optionally followed by `--limit N` to process only N leads

## Instructions

You are executing Phase 2 of Batch Lead Ingestion. Read and follow these steps precisely.

### Step 0: Load the manifest

1. Parse `$ARGUMENTS` to extract the batch directory path and optional `--limit N` flag.
2. Read `{batch-dir}/manifest.json`.
3. If `--limit N` is present, slice `qualified_leads` to the first N entries.
4. Print a one-line summary: `"Processing {N} leads from {batch_name}"`.

### Step 1: Process leads via sub-agents

Process leads in **sub-batches of 3 sub-agents running in parallel**. Each sub-agent handles up to 3 leads sequentially.

**Sub-batching math:**
- 12 qualified leads → 4 sub-agents (3 leads each)
- Launch in waves: first 3 sub-agents, then the next when one finishes
- If `--limit N`, adjust sub-batch count accordingly

**For each sub-agent, pass this prompt** (adapt the lead list and batch path):

```
You are processing a batch of leads through the outbound pipeline.

Batch directory: {batch-dir}
Process these leads sequentially: {lead_1.lead_id}, {lead_2.lead_id}, {lead_3.lead_id}

For EACH lead:
1. Read context/icp.md and context/offer.md for targeting context
2. Run the signal-builder skill (Step 0 ICP gate first — if the lead is disqualified at Step 0, write rejection to results file and skip to next lead)
3. If the lead passes the ICP gate:
   a. Run creative-variable skill for variable discovery
   b. Run email-writer skill AND linkedin-dm skill (in parallel if possible, or sequentially)
   c. Write draft to Google Sheet: python utils/sheet_queue.py upsert-draft --lead-id {lead_id} --canal email --draft "{draft}" --metadata-json '{...}' --timestamp-draft {ISO timestamp}
   d. If LinkedIn was drafted too, run a second upsert-draft with --canal linkedin
4. Write result JSON to {batch-dir}/results/{lead_id}.json

Output format per lead (write to file, do NOT output to chat):
{
  "lead_id": "...",
  "pipeline_status": "completed" | "rejected_icp_gate",
  "signal_score": N,
  "signal_type": "...",
  "rejection_reason": null | "...",
  "email_drafted": true | false,
  "linkedin_drafted": true | false,
  "sheet_row": N,
  "processing_time_seconds": N
}

When ALL leads are done, write a 1-line summary to stdout:
"Processed X leads: Y completed, Z rejected at ICP gate"
```

**Sub-agent launch pattern:**

```
# Wave 1: up to 3 sub-agents in parallel
Launch Agent 1 with leads [1-3]
Launch Agent 2 with leads [4-6]
Launch Agent 3 with leads [7-9]

# Wave 2 (if >9 leads):
Launch Agent 4 with leads [10-12]
...
```

Use the Agent tool with `run_in_background: true` for each sub-agent. Wait for all agents in a wave to complete before launching the next wave.

### Step 2: Collect results

After all sub-agents complete:

1. Read all `{batch-dir}/results/*.json` files.
2. Count completed vs rejected_icp_gate leads.
3. Append a summary line to `{batch-dir}/processing.log`.

### Step 3: Generate summary.md

Create `{batch-dir}/summary.md` with this template:

```markdown
# Batch Report: {batch_name}

**Processed:** {timestamp UTC}
**CSV Source:** {manifest.csv_source}
**Duration:** {calculated from processing.log timestamps}

## Stats
| Metric | Count |
|---|---|
| Total in CSV | {stats.total_csv_rows} |
| Duplicates removed | {stats.duplicates_removed} |
| Failed CSV pre-screen | {stats.failed_pre_screen} |
| Entered pipeline | {stats.qualified_for_pipeline} |
| Passed ICP gate (Step 0) | {count of completed} |
| Failed ICP gate (Step 0) | {count of rejected_icp_gate} |
| Drafts queued to Sheet | {count where email_drafted or linkedin_drafted is true} |

## Rejected — Gate 1 (CSV Pre-screen)
| Name | Company | Reason |
|---|---|---|
| {rejected_leads where reason=geography/industry/size} |

## Rejected — Gate 2 (ICP Step 0 — website)
| Name | Company | Reason |
|---|---|---|
| {results where pipeline_status=rejected_icp_gate} |

## Drafts Queued
| Name | Company | Score | Channel | Pattern | Row |
|---|---|---|---|---|---|
| {completed leads with sheet_row} |
```

### Step 4: Notify user

Print a concise final notification:

```
Batch {batch_name} complete.
- {N} leads processed, {Y} drafts queued to Sheet
- {Z} rejected at ICP gate (Step 0)
- Summary: {batch-dir}/summary.md
```

### Error handling

- If a sub-agent fails, log the error to `processing.log` and continue with remaining leads.
- If `sheet_queue.py upsert-draft` fails, log the error but still write the result JSON (with `sheet_row: null`).
- If a skill is not found, skip that step and note it in the result JSON.
- Always generate `summary.md` even if some leads failed partially.
