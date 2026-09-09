# Batch Lead Ingestion — Plan de Implementación

## Context

El pipeline actual procesa leads de uno en uno, requiriendo consultas en terminal por cada lead (señal → copy → CRM → Sheet). Con volúmenes de 50-100 leads por lote, este flujo secuencial es un cuello de botella. Se necesita un comando único que:

1. Prepare el filesystem y parsee el CSV
2. Filtre leads que no pasan el ICP hard-gate (sin gastar tokens en WebFetch)
3. Ejecute la cadena de skills para los leads calificados
4. Genere un reporte conciso de leads rechazados

**CSV fuente:** `context/prospects_export_New list_20260907_185827.csv`  
**Schema CSV:** `First Name, Last Name, Email, Phone Number, LinkedIn Profile, Location, Headline, Job Title, Company Name, Company Website, Company LinkedIn, Company Location, Company Industry, Company Size, Company Revenue, Active job openings, Hiring SDR/BDR roles, Company technology stack`

---

## Arquitectura: Dos Fases

### Fase 1 — Preprocessing Python (`utils/batch_ingest.py`)
Parser, dedup, ICP pre-screen barato (columnas CSV), genera manifest JSON.

### Fase 2 — Pipeline Claude Code (`/batch-ingest` command)
Lee manifest, procesa leads calificados a través de la cadena de skills, escribe a Google Sheets, genera reporte.

---

## Paso 1: Script `utils/batch_ingest.py`

### Uso
```bash
python utils/batch_ingest.py prepare \
  --csv "context/prospects_export_New list_20260907_185827.csv" \
  --batch-name "batch-2026-09-08"
```

### Qué hace
1. **Parse CSV** — `csv.DictReader`, mapea campos al schema del pipeline
2. **Dedup** — cruza contra `Documents/Outbound_Pipeline_Tracker.md` (nombres existentes) + duplicados internos del CSV
3. **ICP Pre-screen** (barato, solo columnas CSV):
   - `Company Size` → rango 10-250
   - `Company Industry` → match contra ICP keywords
   - `Location`/`Company Location` → US o Canada
4. **Genera batch directory** → `batches/{batch-name}/`
5. **Escribe manifest** → `batches/{batch-name}/manifest.json`

### Filesystem preparado
```
batches/
  batch-2026-09-08/
    manifest.json          ← leads calificados + rechazados
    rejected.json          ← leads que no pasaron pre-screen
    processing.log         ← log de progreso durante Fase 2
    results/               ← output por lead
      {lead-slug}.json     ← resultado del pipeline
    summary.md             ← reporte final generado por Fase 2
```

### Manifest JSON
```json
{
  "batch_name": "batch-2026-09-08",
  "created_at": "2026-09-08T14:30:00Z",
  "csv_source": "context/prospects_export_New list_20260907_185827.csv",
  "stats": {
    "total_csv_rows": 26,
    "duplicates_removed": 2,
    "failed_pre_screen": 12,
    "qualified_for_pipeline": 12
  },
  "qualified_leads": [
    {
      "lead_id": "darren-nix-steadily",
      "first_name": "Darren",
      "last_name": "Nix",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/darrensnix",
      "location": "Austin, TX, United States",
      "job_title": "Founder, CEO",
      "company_name": "Steadily Insurance Company",
      "company_website": "https://www.steadily.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    }
  ],
  "rejected_leads": [
    {
      "lead_id": "paras-arora-qdesq",
      "first_name": "Paras",
      "last_name": "Arora",
      "company_name": "Qdesq",
      "reason": "geography",
      "detail": "Location: DL, India — outside US/Canada"
    }
  ]
}
```

### Mapeo CSV → Pipeline

| CSV Column | Pipeline Field |
|---|---|
| `First Name` + `Last Name` | `first_name`, `last_name` |
| `Email` | `email` |
| `LinkedIn Profile` | `linkedin_url` |
| `Job Title` | `job_title` |
| `Company Name` | `company_name` |
| `Company Website` | `company_website` |
| `Company Industry` | `company_industry` |
| `Company Size` | `company_size` |
| `Company Location` | `location` (fallback si `Location` vacío) |

### Reglas pre-screen (solo columnas CSV)

```python
# Geografía — substring match
GEO_KEYWORDS = [
    "united states", "us", "canada", "ca",
    "tx", "ny", "california", "ontario", "toronto", "vancouver",
    "florida", "texas", "colorado", "washington", "illinois", ...
]

# Industria — substring match contra ICP
INDUSTRY_KEYWORDS = [
    "wholesale", "distribution", "import", "export", "e-commerce",
    "ecommerce", "manufacturing", "consumer goods", "retail",
    "logistics", "3pl", "construction", "field service",
    "food", "beverage", "professional service", "franchise"
]

# Tamaño — parse rango
def parse_size(size_str: str) -> tuple[int|None, int|None]:
    # "11-50 employees" → (11, 50) → pass (within 10-250)
    # "201-500 employees" → (201, 500) → fail
    # "" → (None, None) → indeterminate, pass to Step 0
```

---

## Paso 2: Custom Command `.claude/commands/batch-ingest.md`

### Uso
```
/batch-ingest batches/batch-2026-09-08
```

### Qué ejecuta

1. **Lee el manifest** del batch directory
2. **Procesa cada lead calificado** a través de la cadena:
   - `signal-builder` (ICP gate Step 0 + signal analysis + Attio log)
   - `creative-variable` (variable discovery)
   - `email-writer` + `linkedin-dm` en paralelo
   - `sheet_queue.py upsert-draft` — escribe draft a Google Sheets
3. **Documenta rechazados del gate** — leads que pasaron CSV pre-screen pero fallaron ICP Step 0
4. **Genera `summary.md`**
5. **Notificación concisa** al usuario

### Paralelización: Sub-agentes en sub-batches

```
50 leads → 5 sub-batches de 10
Cada sub-batch → 3 sub-agentes en paralelo (~3-4 leads cada uno)
Total: ~15 sub-agentes, corriendo en background

Cada sub-agente:
  1. Lee context (icp.md, offer.md, outreach-principles.md)
  2. Ejecuta signal-builder para sus leads
  3. Ejecuta creative-variable
  4. Ejecuta email-writer + linkedin-dm
  5. Escribe resultado a batches/{batch}/results/{lead-slug}.json
  6. Si tiene_ATTIO MCP_, log note; si no, omite CRM step
```

**Sub-batching** por rate limits: no lanzar todos los agentes de golpe. Procesar en oleadas de 3-5 agentes paralelos.

### Prompt del sub-agente (autónomo)

```
You are processing a batch of leads through the outbound pipeline.
Process these leads sequentially: [lead1, lead2, lead3]

For EACH lead:
1. Read context/icp.md and context/offer.md
2. Run signal-builder skill (Step 0 ICP gate first — if disqualified, write rejection to results file and skip to next lead)
3. If passes gate: run creative-variable, then email-writer + linkedin-dm in parallel
4. Write draft to Sheet: python utils/sheet_queue.py upsert-draft ...
5. Write result JSON to batches/{batch}/results/{lead-slug}.json

Output format per lead (write to file, do NOT output to chat):
{"lead_id": "...", "status": "completed"|"rejected_icp_gate", "score": N, "email_drafted": bool, "linkedin_drafted": bool, "sheet_row": N}

When ALL leads are done, write a 1-line summary to stdout: "Processed X leads: Y completed, Z rejected at ICP gate"
```

### Resultado JSON por lead
```json
{
  "lead_id": "darren-nix-steadily",
  "pipeline_status": "completed",
  "signal_score": 8,
  "signal_type": "Adjacent-hiring",
  "rejection_reason": null,
  "email_drafted": true,
  "linkedin_drafted": true,
  "sheet_row": 15,
  "processing_time_seconds": 45
}
```

---

## Paso 3: Reporte Final (`summary.md`)

```markdown
# Batch Report: batch-2026-09-08

**Processed:** 2026-09-08 14:30 UTC
**CSV Source:** context/prospects_export_New list_20260907_185827.csv
**Duration:** 12m 34s

## Stats
| Metric | Count |
|---|---|
| Total in CSV | 26 |
| Duplicates removed | 2 |
| Failed CSV pre-screen | 12 |
| Entered pipeline | 12 |
| Passed ICP gate (Step 0) | 8 |
| Failed ICP gate (Step 0) | 4 |
| Drafts queued to Sheet | 8 |

## Rejected — Gate 1 (CSV Pre-screen)
| Name | Company | Reason |
|---|---|---|
| Paras Arora | Qdesq | Geography: India |
| Rajesh Kotta | hustlehub | Geography: India |

## Rejected — Gate 2 (ICP Step 0 — website)
| Name | Company | Reason |
|---|---|---|
| Sébastien Aubert | Adastra Films | Industry: Film production — outside ICP |

## Drafts Queued
| Name | Company | Score | Channel | Pattern | Row |
|---|---|---|---|---|---|
| Darren Nix | Steadily Insurance | 8 | Both | Pain-led | 15 |
```

---

## Archivos a Crear

| Archivo | Tipo | Descripción |
|---|---|---|
| `utils/batch_ingest.py` | Nuevo | Preprocessing: CSV parse, dedup, ICP pre-screen, manifest gen |
| `.claude/commands/batch-ingest.md` | Nuevo | Custom command para Claude Code |

## Archivos Existentes (referencia, no modificar)

| Archivo | Uso |
|---|---|
| `utils/sheet_queue.py` | `batch_insert_leads()`, `upsert_draft()` |
| `context/icp.md` | ICP definition |
| `context/offer.md` | Offer context |
| `.claude/skills/signal-builder/skill.md` | Se ejecuta por lead |
| `.claude/skills/email-writer/skill.md` | Se ejecuta por lead |
| `.claude/skills/linkedin-dm/skill.md` | Se ejecuta por lead |
| `.claude/skills/creative-variable/skill.md` | Se ejecuta por lead |

---

## Verificación

1. **Pre-screen test:**
   ```bash
   python utils/batch_ingest.py prepare --csv "context/prospects_export_New list_20260907_185827.csv" --batch-name "test"
   # Verificar manifest.json: leads de India en rejected, leads US/CA en qualified
   ```

2. **Pipeline dry-run (1 lead):**
   ```
   /batch-ingest batches/test --limit 1
   # Verificar: lead procesado, draft en Sheet, summary.md generado
   ```

3. **Full batch:**
   ```
   /batch-ingest batches/batch-2026-09-08
   # Verificar: summary.md completo, todas las filas en Sheet
   ```
