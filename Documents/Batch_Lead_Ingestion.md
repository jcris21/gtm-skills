# Batch Lead Ingestion — Plan de Implementación

## Context

El pipeline actual procesa leads de uno en uno, requiriendo consultas en terminal por cada lead (señal → copy → CRM → Sheet). Con volúmenes de 50-100 leads por lote, este flujo secuencial es un cuello de botella. Se necesita un comando único que:

1. Prepare el filesystem y parsee el CSV
2. Filtre leads que no pasan el ICP hard-gate (sin gastar tokens en WebFetch)
3. Ejecute la cadena de skills para los leads calificados
4. Genere un reporte conciso de leads rechazados

**CSV fuente:** `context/Batch1.csv`  
**Schema CSV:** `First Name, Last Name, Email, Phone Number, LinkedIn Profile, Location, Headline, Job Title, Company Name, Company Website, Company LinkedIn, Company Location, Company Industry, Company Size, Company Revenue, Hiring Operations Manager, Hiring ERP Administrator, Hiring Business Systems Role, Hiring Systems Coordinator`

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
  --csv "context/Batch1.csv" \
  --batch-name "batch-2026-09-27-batch1"
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
  batch-2026-09-27-batch1/
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
  "batch_name": "batch-2026-09-27-batch1",
  "created_at": "2026-09-27T18:00:00Z",
  "csv_source": "context/Batch1.csv",
  "stats": {
    "total_csv_rows": 9,
    "duplicates_removed": 0,
    "failed_pre_screen": 0,
    "qualified_for_pipeline": 9
  },
  "qualified_leads": [
    {
      "lead_id": "ted-delong-trade-exchange",
      "first_name": "Ted",
      "last_name": "Delong",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/ted-delong-49391a2",
      "location": "Sacramento, CA, United States",
      "job_title": "Chief Executive Officer",
      "company_name": "Trade Exchange Canada",
      "company_website": "http://www.tradeexchangecanada.ca",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "michael-laksns-network-services",
      "first_name": "Michael",
      "last_name": "Laksns",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/michael-laksns-902b469b",
      "location": "Longueuil, QC, Canada",
      "job_title": "Chief Executive Officer",
      "company_name": "Network Services Company",
      "company_website": "http://www.networkdistribution.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "mike-rose-blue-chip",
      "first_name": "Mike",
      "last_name": "Rose",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/mike-rose-12b05b3",
      "location": "Cincinnati, OH, United States",
      "job_title": "Chief Executive Officer",
      "company_name": "Blue Chip Engineered Products",
      "company_website": "http://www.bcepi.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "katie-macsham-capstone",
      "first_name": "Katie",
      "last_name": "MacHam",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/katie-macham-883304204",
      "location": "Dartmouth, NS, Canada",
      "job_title": "Chief Operating Officer",
      "company_name": "Capstone Project Solutions",
      "company_website": "http://www.capstoneprojectsolutions.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "chris-heim-highjump",
      "first_name": "Chris",
      "last_name": "Heim",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/chris-heim-a75a0",
      "location": "Eden Prairie, MN, United States",
      "job_title": "Chief Executive Officer",
      "company_name": "Highjump",
      "company_website": "http://www.highjump.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "sheri-kuhn-tcg-continuum",
      "first_name": "Sheri",
      "last_name": "Kuhn",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/sheri-kuhn-653450308",
      "location": "Dublin, OH, United States",
      "job_title": "Chief Operating Officer",
      "company_name": "TCG Continuum, LLC",
      "company_website": "http://www.tcgcontinuum.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "steven-shepard-stealth",
      "first_name": "Steven",
      "last_name": "Shepard",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/stevenpshepard",
      "location": "CA, United States",
      "job_title": "Co-Founder and Chief Executive Officer",
      "company_name": "Stealth Startup",
      "company_website": "http://www.avanceservices.com",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "david-morgan-dw-morgan",
      "first_name": "David",
      "last_name": "Morgan",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/david-morgan-2a38441",
      "location": "Danville, CA, United States",
      "job_title": "Chief Executive Officer",
      "company_name": "d.w. Morgan Company",
      "company_website": "http://www.dwmorgan.com/",
      "company_industry": "",
      "company_size": "",
      "pre_screen": {
        "size_pass": null,
        "industry_pass": null,
        "geo_pass": true,
        "note": "Insufficient CSV data — verified at signal-builder Step 0"
      }
    },
    {
      "lead_id": "nilufer-durak-solvoyo",
      "first_name": "Nilufer",
      "last_name": "Durak",
      "email": "",
      "linkedin_url": "https://www.linkedin.com/in/niluferdurak",
      "location": "Boston, MA, United States",
      "job_title": "Chief Operating Officer, Head of Customer Success",
      "company_name": "Solvoyo",
      "company_website": "https://www.solvoyo.com",
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
  "rejected_leads": []
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
| `Headline` | `headline` |
| `Company LinkedIn` | `company_linkedin` |
| `Company Revenue` | `company_revenue` |
| `Hiring Operations Manager` | `hiring_operations_manager` |
| `Hiring ERP Administrator` | `hiring_erp_administrator` |
| `Hiring Business Systems Role` | `hiring_business_systems_role` |
| `Hiring Systems Coordinator` | `hiring_systems_coordinator` |

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
/batch-ingest batches/batch-2026-09-27-batch1
```

### Qué ejecuta

1. **Lee el manifest** del batch directory
2. **Procesa cada lead calificado** a través de la cadena:
   - `signal-builder` (ICP gate Step 0 + signal analysis + Attio log)
   - `creative-variable` (variable discovery)
   - `email-writer` + `linkedin-dm` en paralelo
3. **Valida el resultado contra el payload** — el JSON de cada lead en `batches/{batch}/results/{lead-slug}.json` debe coincidir con la estructura de **"Payload JSON para inserción en OutboundQueue → Estructura base — `batch_insert_leads()`"** (ver sección abajo). Si un campo falta o tiene formato incorrecto, el sub-agente debe corregirlo antes de continuar.
4. **Inserta en la spreadsheet** — tras completar cada lead, escribe la fila en `OutboundQueue` vía `sheet_queue.py upsert-draft` (o `batch-insert` para cargas frescas). No se considera "completado" hasta que la fila existe en la Sheet.
5. **Documenta rechazados del gate** — leads que pasaron CSV pre-screen pero fallaron ICP Step 0
6. **Genera `summary.md`**
7. **Notificación concisa** al usuario

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

### Requisito post-pre-screen: validación e inserción en Sheet

> **Regla obligatoria:** Después del pre-screen (Fase 1) y de que los skills generen el resultado para cada lead, el JSON escrito en `batches/{batch}/results/{lead-slug}.json` **debe coincidir campo a campo** con la estructura definida en **"Payload JSON para inserción en OutboundQueue → Estructura base — `batch_insert_leads()`"** (sección referenciada arriba en este documento).

**Checklist por lead:**

| Paso | Acción | Verificación |
|---|---|---|
| 1 | Sub-agente escribe `results/{lead-slug}.json` | El JSON contiene todas las keys del payload base (ver sección "Estructura base") |
| 2 | Validar formato | `signal_type` ∈ vocabulario fijo · `patron` ∈ vocabulario fijo · `score` es integer 0-10 · `email_disponible`/`linkedin_disponible` ∈ {Y, N, Pending} |
| 3 | Insertar en Sheet | `python utils/sheet_queue.py upsert-draft --lead-id ... --canal ... --draft ... --metadata-json ... --timestamp-draft ...` |
| 4 | Confirmar inserción | El campo `sheet_row` en el JSON de resultado se actualiza con el número de fila real retornado por `sheet_queue.py` |

**Si el JSON no coincide con el payload:** el sub-agente debe corregirlo antes de insertar. No se permite escribir a la Sheet con campos faltantes o mal formateados.

**Un lead no se considera "completado" hasta que su fila existe en la Sheet.**

---

## Paso 3: Reporte Final (`summary.md`)

```markdown
# Batch Report: batch-2026-09-27-batch1

**Processed:** 2026-09-27 18:00 UTC
**CSV Source:** context/Batch1.csv
**Duration:** —

## Stats
| Metric | Count |
|---|---|
| Total in CSV | 9 |
| Duplicates removed | 0 |
| Failed CSV pre-screen | 0 |
| Entered pipeline | 9 |
| Passed ICP gate (Step 0) | — |
| Failed ICP gate (Step 0) | — |
| Drafts queued to Sheet | — |

## Rejected — Gate 1 (CSV Pre-screen)
| Name | Company | Reason |
|---|---|---|
| *(none)* | | |

## Rejected — Gate 2 (ICP Step 0 — website)
| Name | Company | Reason |
|---|---|---|
| *(pending signal-builder run)* | | |

## Drafts Queued
| Name | Company | Score | Channel | Pattern | Row |
|---|---|---|---|---|---|
| Ted Delong | Trade Exchange Canada | — | — | — | — |
| Michael Laksns | Network Services Company | — | — | — | — |
| Mike Rose | Blue Chip Engineered Products | — | — | — | — |
| Katie MacHam | Capstone Project Solutions | — | — | — | — |
| Chris Heim | Highjump | — | — | — | — |
| Sheri Kuhn | TCG Continuum, LLC | — | — | — | — |
| Steven Shepard | Stealth Startup | — | — | — | — |
| David Morgan | d.w. Morgan Company | — | — | — | — |
| Nilufer Durak | Solvoyo | — | — | — | — |
```

---

## Payload JSON para inserción en OutboundQueue

> **Fuente:** derivado de `Documents/leyenda_tabla.md` (diccionario de datos de la hoja `OutboundQueue`). El orden de las keys respeta el orden real de columnas en `sheet_queue.py`.

### Estructura base — `batch_insert_leads()`

```json
{
  "lead_id": "string (requerido, único) — típicamente record_id de Attio o ID sintético",
  "prospecto": "string — nombre del lead",
  "empresa": "string — empresa del lead",
  "score": "integer 0-10 — prioridad de intención de compra (asignado por /signal-builder)",
  "signal_type": "enum: Role-replaced | Adjacent-hiring | Leadership-hire | Competitor-friction | Content-signal | Growth-event | Firmographic-only | None",
  "situacion": "string — resumen en 1 línea de la situación de negocio (el 'por qué ahora')",
  "senal_detectada": "string (transparencia) — hallazgo factual concreto que sustenta score/signal_type, 1 línea",
  "key_data_points": "string (transparencia) — datos concretos formato 'var: value' (p. ej. 'recent_hire_role: RevOps Manager; team_size: 12')",
  "email_disponible": "enum: Y | N | Pending",
  "linkedin_disponible": "enum: Y | N | Pending",
  "linkedin_url": "string — URL del perfil de LinkedIn (target directo de envío)",
  "variable_personalizacion": "string — formato '{{nombre_variable}} = valor' (p. ej. '{{recent_hire_role}} = RevOps Manager')",
  "fuente_variable": "string (transparencia) — página/URL específica + fecha (p. ej. 'Careers page, posting del 2026-07-28')",
  "patron": "enum: Pain-led | Value-led | Segment-fallback | Connection-note",
  "persona_matcheada": "string — debe coincidir exactamente con rol en 'Buyer Persona' de context/icp.md",
  "historia_prueba": "string — caso de éxito/social proof de context/playbooks/segment-stories.md, o '—' si no aplica",
  "angulo": "string — gancho/ángulo concreto del mensaje, 1 línea",
  "qa_pass": "enum: Y | N — resultado del check 'Would I reply?' del propio skill",
  "qa_rationale": "string (transparencia) — por qué pasó/falló el QA, 1 línea",
  "draft_email": "string — cuerpo del draft de email (antes de edición humana)",
  "draft_linkedin": "string — cuerpo del draft de LinkedIn (DM o invite)",
  "timestamp_draft": "string ISO — cuándo se generó/actualizó el draft",
  "aprobado": "enum: Si | No — default No; lo cambia manualmente el revisor humano",
  "enviado": "enum: Si | No — default No; lo pone mark_sent() tras envío exitoso"
}
```

### Columnas gestionadas por el sistema (NO incluir en payload)

| Columna | Cómo se calcula |
|---|---|
| `canal_envio` | Calculado por `_canal_envio()`: `Email`, `LinkedIn`, o `Both` según drafts no-vacíos |
| `editado_email` | Editado manualmente por el revisor en la hoja; n8n prefiere esta sobre `draft_email` si no está vacía |
| `editado_linkedin` | Editado manualmente por el revisor; idem para LinkedIn |

### Payload mínimo — Fase 1 (solo identidad + canales)

```json
{
  "lead_id": "darren-nix-steadily",
  "prospecto": "Darren Nix",
  "empresa": "Steadily Insurance Company",
  "email_disponible": "N",
  "linkedin_disponible": "Y",
  "linkedin_url": "https://www.linkedin.com/in/darrensnix"
}
```

### Payload completo — Fase 3 (listo para aprobación)

```json
{
  "lead_id": "darren-nix-steadily",
  "prospecto": "Darren Nix",
  "empresa": "Steadily Insurance Company",
  "score": 8,
  "signal_type": "Adjacent-hiring",
  "situacion": "RevOps team expanding post-Series B, replacing contractor with full-time hire",
  "senal_detectada": "Job posting for RevOps Manager on careers page, 2026-07-28",
  "key_data_points": "recent_hire_role: RevOps Manager; team_size: 12; funding: Series B $30M",
  "email_disponible": "N",
  "linkedin_disponible": "Y",
  "linkedin_url": "https://www.linkedin.com/in/darrensnix",
  "variable_personalizacion": "{{recent_hire_role}} = RevOps Manager",
  "fuente_variable": "Careers page, posting del 2026-07-28",
  "patron": "Pain-led",
  "persona_matcheada": "Founder",
  "historia_prueba": "—",
  "angulo": "RevOps scaling pain — replaced contractor with full-time, operations breaking",
  "qa_pass": "Y",
  "qa_rationale": "Specific hook tied to RevOps Manager hire, not generic segment copy",
  "draft_email": "",
  "draft_linkedin": "Hi Darren — noticed you're bringing RevOps in-house after 12 months on a contractor. Most founders we talk to hit the same wall: […]",
  "timestamp_draft": "2026-09-08T14:32:00Z",
  "aprobado": "No",
  "enviado": "No"
}
```

### Reglas de inserción

1. **`lead_id` es clave única** — permite upsert (actualizar la misma fila en vez de duplicar) cuando `email-writer` y `linkedin-dm` corren para el mismo prospecto
2. **Columnas de transparencia** (`senal_detectada`, `key_data_points`, `fuente_variable`, `qa_rationale`): 1 línea o lista corta `var: value`, nunca párrafos
3. **`signal_type` y `patron`** usan vocabulario fijo — no inventar variantes
4. **`persona_matcheada`** debe coincidir exactamente con el nombre de rol en `context/icp.md`
5. **Nuevas columnas** — solo agregar al final de `COLUMNS` (nunca intercalar)
6. **Drafts se actualizan por separado** vía `upsert_draft(canal="email"|"linkedin", ...)` — no requiere re-insertar la fila completa

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
   python utils/batch_ingest.py prepare --csv "context/Batch1.csv" --batch-name "batch-2026-09-27-batch1"
   # Verificar manifest.json: 9 leads calificados, 0 rechazados
   ```

2. **Pipeline dry-run (1 lead):**
   ```
   /batch-ingest batches/batch-2026-09-27-batch1 --limit 1
   # Verificar: lead procesado, draft en Sheet, summary.md generado
   ```

3. **Full batch:**
   ```
   /batch-ingest batches/batch-2026-09-27-batch1
   # Verificar: summary.md completo, todas las filas en Sheet
   ```
