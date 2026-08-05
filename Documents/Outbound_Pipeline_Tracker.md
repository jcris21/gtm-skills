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
| 3. Personalización | `/email-writer`, `/linkedin-dm` | Canal(es) usados, patrón (Pain-led/Value-led/Segment fallback), ángulo en 1 línea, QA pass | Label + descriptivo corto |
| 4. Gate CRM | `/attio-crm` (nota "Campaign Drafted") | ¿Nota logueada?, ¿autorizado el envío?, fecha de autorización | Binario |
| 5. Envío | `/attio-crm` + Unipile | ¿Enviado?, fecha, acción (Email / DM / Invite), grado de conexión LinkedIn | Label + binario |
| 6. Respuesta | `/reply-handler` | ¿Respondió?, clasificación (6 categorías), ¿tarea de follow-up creada? | Label + binario |
| 7. Resultado | Attio (`Outbound Pipeline` list) | Etapa actual, próxima acción en 1 línea | Label + descriptivo corto |

---

## Leyenda de labels (vocabulario fijo — no inventar variantes)

**Binario:** `Y` / `N` / `Pending`

**Signal Type:** `Role-replaced` · `Adjacent-hiring` · `Leadership-hire` · `Competitor-friction` · `Content-signal` · `Firmographic-only` · `None`

**Pattern:** `Pain-led` · `Value-led` · `Segment-fallback` · `Connection-note`

**Channel:** `Email` · `LinkedIn` · `Both`

**Network Distance (LinkedIn):** `1st` · `2nd` · `3rd` · `N/A`

**Send Action:** `Email` · `DM` · `Invite`

**Reply Classification:** `INTERESTED` · `OBJECTION` · `NOT_NOW` · `NOT_INTERESTED` · `QUESTION` · `OUT_OF_OFFICE` · `—` (aún sin respuesta)

**Pipeline Stage:** `Prospecting` · `Signal Scored` · `Drafted` · `Outreach Sent` · `Replied` · `Meeting Booked` · `SQL` · `Closed-Won` · `Closed-Lost`

---

## Tabla maestra (detallada — uso del operador)

| Prospecto | Empresa | Score (0-10) | Signal Type | Situación (1 línea) | Email? | LinkedIn? | Variable Personalización | Canal(es) | Patrón | Ángulo (1 línea) | QA Pass | Nota Drafted? | Autorizado? | Fecha Autoriz. | Enviado? | Fecha Envío | Send Action | Network Dist. | Respondió? | Clasificación | Follow-up creado? | Etapa | Próxima Acción |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jane Doe | Acme Inc | 8 | Role-replaced | Contratando "RevOps Manager" — sin tooling de forecasting hoy | Y | Y | `{{recent_hire_role}}` = RevOps Manager | Both | Pain-led | Vi que están armando RevOps desde cero | Y | Y | Y | 2026-08-01 | Y | 2026-08-02 | Email | N/A | N | — | N | Outreach Sent | Esperar 3-4 días, evaluar Email 2 |
| *(fila por prospecto...)* | | | | | | | | | | | | | | | | | | | | | | | |

---

## Vista rápida — decisor GTM (subset para revisión semanal)

Para no perder 10 minutos escaneando 24 columnas: esta es la vista que un GTM lead revisa en la reunión semanal — solo lo que cambia una decisión.

| Prospecto | Score | Canal(es) | Etapa | Respondió? | Clasificación | Próxima Acción |
|---|---|---|---|---|---|---|
| Jane Doe | 8 | Both | Outreach Sent | N | — | Esperar 3-4 días |

**Cuándo escalar a atención humana inmediata:** `Clasificación = INTERESTED` sin `Follow-up creado? = Y`, o `Autorizado? = Pending` con más de 48h desde `Nota Drafted?`.

---

## Notas de uso

- El detalle completo del copy (asunto, 3 líneas del email, DM, seguimiento) **no vive aquí** — vive en la nota `Campaign Drafted` / `Campaign Sent` del Person record en Attio. Esta tabla enlaza (por nombre/empresa) a esa nota, no la duplica.
- **No inflar el Score.** Un 4/10 es información útil (calibra tono), no un fallo a esconder — mismo principio que usa `/signal-builder`.
- Actualizar `Etapa` solo cuando Attio cambia de estado real (no adelantarse) — esta tabla refleja el CRM, no lo reemplaza.
- Si un prospecto no tiene email, la fila igual se llena: `Email? = N`, `Canal(es) = LinkedIn`, y el resto del flujo corre igual vía `/linkedin-dm`.
