# Outbound Pipeline Tracker

Plantilla para registrar, por fase, los outputs clave que cada skill del pipeline produce sobre un prospecto — desde detección de señal hasta respuesta. Una fila = un prospecto, de punta a punta.

**Principio de diseño:** cada columna es o bien **binaria/label** (para escanear en segundos: Y/N, score, enum) o **descriptiva corta** (1 frase, para la nuance que una etiqueta no puede capturar — la Situación, el ángulo, la objeción). Nada de párrafos en la tabla: el detalle completo (copy generado, nota de Attio) vive en el CRM; esta tabla es el cockpit, no el archivo.

---

## Cómo se llena, por fase

| Fase | Skill que la produce | Qué escribir | Tipo de dato |
|---|---|---|---|
| 0. Contexto | `/gtm-context` | (no es por fila — una sola vez por workspace, ver `context/offer.md`) | — |
| 1. Señal | `/job-search`, `/prospect-posts`, `/signal-builder` | Score 0-10, tipo de señal, 1 línea de situación, canal disponible (email/LinkedIn) | Label + descriptivo corto |
| 2. Enriquecimiento | `/creative-variable` | Variable de personalización usada + su fuente | Descriptivo corto + label |
| 3. Personalización | `/email-writer`, `/linkedin-dm` | Canal(es) usados, patrón (Pain-led/Value-led/Segment fallback), persona matcheada (rol → fila de `context/icp.md`), historia de prueba usada (vertical/track de `context/playbooks/segment-stories.md`, o "—" si no hay), ángulo en 1 línea, QA pass | Label + descriptivo corto |
| 4. Gate CRM | `/attio-crm` (nota "Campaign Drafted") | ¿Nota logueada?, ¿autorizado el envío?, fecha de autorización, tier de cadencia (según `signal_score`) | Binario + label |
| 5. Envío | `/attio-crm` + Unipile | ¿Enviado?, fecha, acción (Email / DM / Invite), grado de conexión LinkedIn, `combined_touch_count` acumulado (compartido entre canales) | Label + binario + número |
| 6. Respuesta | `/reply-handler` | ¿Respondió?, clasificación (6 categorías), ¿tarea de follow-up creada? | Label + binario |
| 7. Resultado | Attio (`Outbound Pipeline` list) | Etapa actual, próxima acción en 1 línea | Label + descriptivo corto |

---

## Leyenda de labels (vocabulario fijo — no inventar variantes)

**Binario:** `Y` / `N` / `Pending`

**Signal Type:** `Role-replaced` · `Adjacent-hiring` · `Leadership-hire` · `Competitor-friction` · `Content-signal` · `Growth-event` · `Firmographic-only` · `None`
— `Growth-event` covers whatever `context/icp.md`'s Growth Signal field currently names (headcount growth, expansion, or a financing event) per `signal-builder/reference/signal-types.md`'s Section 3. Don't assume which sub-type applies; check the ICP file.

**Pattern:** `Pain-led` · `Value-led` · `Segment-fallback` · `Connection-note`

**Cadence Tier (por `signal_score`):** `Alto (8-10)` · `Estándar (3-7)` · `Fallback (1-2)` — determina cuántos touches y en qué ventana, ver `email-writer/skill.md` y `linkedin-dm/skill.md` Step 5.

**Persona Matcheada:** no es vocabulario fijo — usar el nombre de rol exactamente como aparece en la tabla de personas de `context/icp.md` (columna "Buyer Persona"). Si `icp.md` cambia sus personas, esta columna sigue el cambio automáticamente; no hardcodear una lista aquí.

**Channel:** `Email` · `LinkedIn` · `Both`

**Network Distance (LinkedIn):** `1st` · `2nd` · `3rd` · `N/A`

**Send Action:** `Email` · `DM` · `Invite`

**Reply Classification:** `INTERESTED` · `OBJECTION` · `NOT_NOW` · `NOT_INTERESTED` · `QUESTION` · `OUT_OF_OFFICE` · `—` (aún sin respuesta)

**Pipeline Stage:** `Prospecting` · `Signal Scored` · `Drafted` · `Outreach Sent` · `Replied` · `Meeting Booked` · `SQL` · `Closed-Won` · `Closed-Lost`

---

## Tabla maestra (detallada — uso del operador)

| Prospecto | Empresa | URL LinkedIn Profile | Score (0-10) | Signal Type | Situación (1 línea) | Email? | LinkedIn? | Variable Personalización | Canal(es) | Patrón | Persona Matcheada | Historia de Prueba | Ángulo (1 línea) | QA Pass | Nota Drafted? | Autorizado? | Fecha Autoriz. | Cadence Tier | Enviado? | Fecha Envío | Send Action | Network Dist. | Combined Touch Count | Respondió? | Clasificación | Follow-up creado? | Etapa | Próxima Acción | Input Tokens | Output Tokens | Costo LLM (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jane Doe | Acme Inc | — (lead sintético de ejemplo, sin perfil real) | 8 | Role-replaced | Contratando "RevOps Manager" — sin tooling de forecasting hoy | Y | Y | `{{recent_hire_role}}` = RevOps Manager | Both | Pain-led | COO / VP Operations | — (segmento sin historia aún) | Vi que están armando RevOps desde cero | Y | Y | Y | 2026-08-01 | Alto (8-10) | Y | 2026-08-02 | Email | N/A | 1 | N | — | N | Outreach Sent | Esperar 3-4 días, evaluar Email 2 | N/A | N/A | N/A |
| TEST — chriscob LinkedIn (Pipeline Dry Run) | — (sin empresa ICP; perfil resuelve a org. de gobierno) | — (no registrada en Attio para esta fila de prueba) | 1 | None | Sin dolor operativo propio detectado; perfil de gobierno, sin fit de ICP | N | Y | — (sin señal suficiente para justificar variable) | LinkedIn | Segment-fallback | — (no aplica, no hay persona ICP) | — (sin fit de vertical/track) | Genérico de segmento (dependencia de ERP/partners) — sintético, no personalizado | N (falló "Would I reply?" honestamente) | Y | N | — | Fallback (1-2) | N | — | — | N/A | 0 | N | — | N | Drafted | Prueba mecánica completa — no perseguir, no hay lead real detrás | N/A | N/A | N/A |
| Christian Cobian G. (LinkedIn) | — (independiente, sin empresa) | https://www.linkedin.com/in/christian-j-cobian | 1 | None | AI consultant/PM independiente, en búsqueda de empleo; sin rol operativo ni empresa ICP | N | Y | — (sin señal suficiente para justificar variable) | LinkedIn | Connection-note | — (no aplica, no hay persona ICP) | — (sin fit de vertical/track) | Sin ángulo — prueba mecánica de invite, no hay ICP match | Pass (honesto, transparente) | Y | Y | 2026-08-06 | Fallback (1-2) | Y | 2026-08-06 | Invite | 2nd | 1 | Y | INTERESTED (Low confidence) | Y (escalación, no follow-up normal) | Interested | Reply ambiguo "It's interesting" — /reply-handler corrido y logueado en Attio (nota eae93a11, tarea cbaadef7); NO es lead real (no ICP) — tarea de escalación pide confirmar si se manda la respuesta como mensaje personal, no como campaña | N/A | N/A | N/A |
| *(fila por prospecto...)* | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |

---

## Vista rápida — decisor GTM (subset para revisión semanal)

Para no perder 10 minutos escaneando 24 columnas: esta es la vista que un GTM lead revisa en la reunión semanal — solo lo que cambia una decisión.

| Prospecto | Score | Canal(es) | Etapa | Respondió? | Clasificación | Próxima Acción |
|---|---|---|---|---|---|---|
| Jane Doe | 8 | Both | Outreach Sent | N | — | Esperar 3-4 días |
| TEST — chriscob LinkedIn | 1 | LinkedIn | Drafted | N | — | Prueba mecánica completa — no perseguir |

**Cuándo escalar a atención humana inmediata:** `Clasificación = INTERESTED` sin `Follow-up creado? = Y`, `Autorizado? = Pending` con más de 48h desde `Nota Drafted?`, o `Combined Touch Count` acercándose al tope del `Cadence Tier` (Alto=5, Estándar=3+2, Fallback=1+1) sin respuesta — señal de que toca revisar el signal score, no seguir insistiendo.

---

## Notas de uso

- El detalle completo del copy (asunto, 3 líneas del email, DM, seguimiento) **no vive aquí** — vive en la nota `Campaign Drafted` / `Campaign Sent` del Person record en Attio. Esta tabla enlaza (por nombre/empresa) a esa nota, no la duplica.
- **No inflar el Score.** Un 4/10 es información útil (calibra tono), no un fallo a esconder — mismo principio que usa `/signal-builder`.
- Actualizar `Etapa` solo cuando Attio cambia de estado real (no adelantarse) — esta tabla refleja el CRM, no lo reemplaza.
- Si un prospecto no tiene email, la fila igual se llena: `Email? = N`, `Canal(es) = LinkedIn`, y el resto del flujo corre igual vía `/linkedin-dm`.
- `Combined Touch Count` es un contador compartido entre `/email-writer` y `/linkedin-dm` (campo `combined_touch_count` en `context/crm/attio-schema.md`) — un email y un DM al mismo prospecto suman al mismo número. No lo dupliques por canal en esta tabla.
- El detalle completo de cada envío individual (fecha exacta, copy verbatim, patrón, ángulo, QA pass) vive en el objeto `touches` de `context/crm/attio-schema.md` — un registro Touch por cada email/DM/invite enviado. Las columnas de Fase 5 de esta tabla (`Fecha Envío`, `Send Action`, `Network Dist.`) reflejan el Touch más reciente; para el historial completo de touches de un prospecto, consultar Attio directamente.
- `Persona Matcheada` y `Historia de Prueba` no son vocabulario fijo de esta tabla — reflejan lo que `context/icp.md` y `context/playbooks/segment-stories.md` dicen en el momento del envío. Si esos archivos cambian, los valores válidos cambian con ellos; no hardcodear una lista aparte aquí.
- `Input Tokens` / `Output Tokens` / `Costo LLM (USD)` solo se llenan cuando el pipeline corrió programáticamente contra la API (`utils/token_ledger.py` registrando cada llamada, `utils/token_report.py --lead-id <id>` generando el rollup). Si el lead se trabajó a mano por chat de Claude Code, estas columnas quedan en `N/A` — no estimarlas desde el costo de sesión, que mezcla todos los leads y no es atribuible a uno solo. El precio por modelo vive en `context/pricing/model-pricing.json` (marcado `_verified: false` hasta confirmar contra la página oficial de precios de Anthropic), no hardcodeado en los scripts.
