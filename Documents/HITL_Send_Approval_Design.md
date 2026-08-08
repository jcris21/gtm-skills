# HITL de envío — gate diferenciado por volumen y riesgo

Status: **Draft spec — no construido aún** (decisiones abiertas marcadas en §6)
Complementa: `Documents/n8n_Reply_Handler_Automation.md` (que este documento corrige — ver su changelog)
Precondición ya implementada: ICP hard-gate en `.claude/skills/signal-builder/skill.md` Step 0 — un lead que no cumple `context/icp.md` nunca llega a generar un draft, así que nunca entra a este flujo.

---

## 1. Problema

Hoy el único gate humano antes de enviar un DM/email es "preguntar en el chat de Claude Code" (Step 7 de `email-writer`/`linkedin-dm`). Dos gaps:

1. **No hay medio fuera del chat** para revisar/editar/aprobar — todo pasa por la sesión interactiva del operador.
2. **Ese gate no escala.** Si el pipeline corre 100 leads, pedir aprobación uno por uno (en chat o en Slack, mensaje por mensaje) es un cuello de botella.

Este documento resuelve ambos, con un principio rector: **el medio de aprobación se elige por volumen y riesgo del evento, no un único mecanismo para todo.**

---

## 2. Principio rector — qué necesita gate y dónde

| Evento | ¿Gate humano? | Medio | Por qué |
|---|---|---|---|
| **Mensaje 1** (outbound inicial, cualquier lead) | **Siempre**, sin excepción | **Google Sheets** (bulk review) | El prospecto no inició el contacto — riesgo parejo en todos los casos. Alto volumen (potencialmente 100+ por corrida) → necesita un medio de revisión masiva, no mensaje-por-mensaje. |
| **Follow-up** que cumple trigger de escalamiento (§4, nuevo) | Sí | **Slack** (Approve / Edit-modal / Reject, individual) | Bajo volumen — es la excepción, no la regla. Slack por-item es apropiado cuando el volumen es bajo. |
| **Follow-up** normal (sin escalamiento) | No | — (auto-envía, solo log en Attio) | Ya pasó el gate de Mensaje 1 una vez; sin señal nueva de riesgo, no repetir la fricción. |
| **Reply** que cumple trigger de escalamiento (`reply-handler` Step 4, ya existe) | Sí | **Slack** (mismo subworkflow que follow-ups escalados) | Igual razonamiento — bajo volumen, necesita juicio humano real. |
| **Reply** normal (sin escalamiento) | No | — (auto-envía, solo log en Attio) | `reply-handler/skill.md` ya declara la intención: "keeps 90% of interactions automated and only escalates when a human is genuinely needed." El spec de n8n actual (`n8n_Reply_Handler_Automation.md`) contradecía esto — corregido, ver su changelog. |

---

## 3. Mensaje 1 — flujo Google Sheets

### 3.1 Cambio en el skill (Send Gate)

`email-writer/skill.md` y `linkedin-dm/skill.md` Step 7 cambian de "pedir autorización en el chat" a:

1. Redactar el draft (sin cambios en Steps 1-6).
2. Hacer `upsert` sobre la fila del lead en Google Sheets vía `utils/sheet_queue.py` (mismo patrón que `utils/unipile.py`: dotenv + client, CLI + función importable) — `upsert_draft(lead_id, canal, draft, metadata, timestamp_draft)`. Si el lead ya tiene fila (por ejemplo, el otro skill ya corrió para ese `lead_id`), actualiza esa fila en vez de crear una segunda; `canal_envio` pasa a `Both` automáticamente.
3. Detenerse — no preguntar en chat, no enviar. El chat solo confirma "draft escrito/actualizado en la fila N de la Sheet."

### 3.2 Columnas de la Sheet (consolidado con `Outbound_Pipeline_Tracker.md` — resuelto 2026-08-07)

Una sola sheet ancha: una fila por lead, con la metadata de Fase 1-3 del Tracker (para que el revisor vea score/signal/persona/ángulo sin ir a Attio) más las columnas de aprobación. `email-writer` y `linkedin-dm` hacen `upsert` sobre el mismo `lead_id` — si un lead tiene ambos canales, la misma fila termina con `canal_envio = Both` en vez de generar dos filas. Implementado en `utils/sheet_queue.py` (`upsert_draft`, `batch_insert_leads`).

| Columna | Contenido | Vocabulario fijo (ver `Outbound_Pipeline_Tracker.md`) |
|---|---|---|
| `lead_id` | Record ID de Attio | — |
| `prospecto` | Nombre del lead | — |
| `empresa` | Empresa del lead | — |
| `score` | Signal score 0-10 | — |
| `signal_type` | Tipo de señal | `Role-replaced` · `Adjacent-hiring` · `Leadership-hire` · `Competitor-friction` · `Content-signal` · `Growth-event` · `Firmographic-only` · `None` |
| `situacion` | 1 línea — la realidad del lunes del prospecto | — |
| `email_disponible` | ¿Hay email? | `Y` / `N` |
| `linkedin_disponible` | ¿Hay LinkedIn? | `Y` / `N` |
| `linkedin_url` | URL del perfil de LinkedIn del prospecto (send target para `linkedin-dm`/n8n, resuelve la mitad LinkedIn del edge case 1 de `n8n_Message1_Send_Flow.md` §6) | — |
| `variable_personalizacion` | Variable usada + su fuente | — |
| `canal_envio` | Canal(es) con draft en esta fila | `Email` · `LinkedIn` · `Both` — recalculado automáticamente por `upsert_draft` |
| `patron` | Patrón de mensaje | `Pain-led` · `Value-led` · `Segment-fallback` · `Connection-note` |
| `persona_matcheada` | Rol de `context/icp.md` | — |
| `historia_prueba` | Prueba de `context/playbooks/segment-stories.md`, o `—` | — |
| `angulo` | 1 línea | — |
| `qa_pass` | ¿Pasó el self-check del skill? | `Y` / `N` |
| `draft_email` | Texto del Email 1 (vacío si no aplica) | — |
| `editado_email` | Texto final si el humano reescribió el email (vacío = usar `draft_email`) | — |
| `draft_linkedin` | Texto de la connection note / DM 1 (vacío si no aplica) | — |
| `editado_linkedin` | Texto final si el humano reescribió el DM (vacío = usar `draft_linkedin`) | — |
| `aprobado` | default No | `Sí` / `No` |
| `enviado` | default No — lo marca n8n después de enviar, evita doble envío | `Sí` / `No` |
| `timestamp_draft` | Cuándo se escribió/actualizó la fila | — |

**Insert masivo:** `batch_insert_leads()` acepta una lista de leads (dicts con cualquier columna de arriba) y hace un solo write — cubre el caso "cargar una lista de leads de una vez" en vez de un upsert por lead. `upsert_draft()` sigue siendo el camino normal por-skill-run (incremental, uno a la vez, converge en la misma fila por `lead_id`).

### 3.3 n8n — botón manual y envío (resuelto — 2026-08-07)

Trigger: **botón manual** (no cron). El operador dispara el envío cuando termina de revisar un batch, en vez de que n8n barra la Sheet automáticamente cada N horas — evita que un envío salga mientras la revisión todavía está en curso. Flujo: botón manual → lee filas `aprobado=Sí` AND `enviado=No` → envía vía Unipile (LinkedIn) o el sender correspondiente (email) usando `editado` si no está vacío, si no `draft` → marca `enviado=Sí` → log en Attio (nota + touch count).

---

## 4. Follow-ups — no existe un trigger de escalamiento propio (resuelto — 2026-08-07)

No hace falta inventar uno. Un follow-up de la secuencia de no-reply solo existe mientras **no hubo reply** — y por la regla ya escrita en `LinkedIn_DM_NoReply_Activation_Strategy.md` §4.1, cualquier reply (de cualquier clasificación) cancela toda la secuencia de follow-ups pendiente de ese lead. La única condición de escalamiento que existe (`reply-handler` Step 4) solo se evalúa *después* de un reply — momento en el cual ya no queda ningún follow-up de no-reply por enviar.

Conclusión: **todo follow-up de la secuencia de no-reply auto-envía siempre**, sin gate de escalamiento propio. El único escalamiento relevante en todo este diseño es el de `reply-handler` (§5), que no es "un follow-up escalado" sino la respuesta a un reply real.

**Trigger del escalamiento de reply-handler (aclarado — no es un evento de Attio):** quien decide el escalamiento es el propio skill/clasificación de `reply-handler` (Node 5 en el spec n8n — el modelo evalúa los triggers de Step 4 al mismo tiempo que clasifica el reply), y ese resultado (`escalate: true/false`) branchea directo dentro de la misma ejecución del workflow (Node 6 → Node 10) hacia el nodo Slack HITL. No es un webhook disparado por una automation de "task creada" en Attio — Attio solo registra el resultado (nota + task), no dispara nada.

---

## 5. Subworkflow Slack HITL compartido (solo casos escalados)

Se extraen los Nodes 10-11 del spec original de `n8n_Reply_Handler_Automation.md` (Slack Interactive Blocks con Approve/Edit-vía-modal/Reject + envío Unipile) a un **subworkflow reusable**, parametrizado por canal y texto del draft. Lo llaman dos flujos:
- `reply-handler`, cuando su Node 6 (escalation gate) es `true`.
- El follow-up outbound, cuando cumple el trigger de §4.

No se usa para Mensaje 1 (eso va por Sheets, §3) ni para replies/follow-ups no-escalados (esos auto-envían, sin gate).

---

## 6. Decisiones abiertas — bloquean construcción

1. ~~Trigger de escalamiento para follow-ups (§4)~~ — **resuelto 2026-08-07:** no existe uno propio; ver §4.
2. ~~Trigger del envío de filas aprobadas en la Sheet (§3.3)~~ — **resuelto 2026-08-07:** botón manual; ver §3.3.
3. **Credencial Google Sheets API** — no existe hoy en `.env` ni en n8n. Provisionar cuenta de servicio + compartir la Sheet con ella.
4. **Volumen de redacción, no solo de aprobación** — 100 Mensajes 1 hoy se siguen redactando uno por uno en una sesión interactiva de Claude Code (se descartó explícitamente correr esto programáticamente contra la API de Anthropic por costo). Este documento resuelve el cuello de botella de *aprobación*; el de *redacción* queda fuera de alcance salvo que se decida lo contrario.

---

## 7. Fases de construcción

1. ~~Definir trigger de escalamiento de follow-ups (§4)~~ — **resuelto 2026-08-07:** no existe uno propio; ver §4.
2. ~~Send Gate: Step 7 de `email-writer`/`linkedin-dm` escribe a Sheet en vez de preguntar en chat (§3.1) + `utils/sheet_queue.py`~~ — **construido 2026-08-07, consolidado con `Outbound_Pipeline_Tracker.md` el mismo día (§3.2):** ambos skills reescritos para hacer `upsert-draft` con metadata completa; `utils/sheet_queue.py` creado (`upsert_draft`, `batch_insert_leads`, `list_approved_unsent`, `mark_sent`). Bloqueado en runtime hasta que exista la credencial (#3 abajo) — el código corre pero `_require_config()` falla sin ella.
3. n8n: poll + envío de filas aprobadas (§3.3) — **spec escrito 2026-08-07:** `Documents/n8n_Message1_Send_Flow.md` (9 nodos, credenciales, diagrama, edge cases). Bloqueado por: credencial de n8n para Google Sheets (distinta de la que ya usa `sheet_queue.py`), credencial Gmail, credencial Unipile/Attio en n8n, y 2 decisiones de schema abiertas (ver ese doc §6, edge cases 1 y 2: falta columna de email/identificador LinkedIn en la Sheet, y tracking de envío por canal cuando `canal_envio = Both`). Construcción en sí fuera de este repo (sin acceso a la UI de n8n).
4. Subworkflow Slack HITL compartido (§5), extraído del spec de reply-handler.
5. Auto-send para casos no-escalados — ya reflejado en la corrección de `n8n_Reply_Handler_Automation.md` (ver su changelog) y en el Step 7 de `email-writer`/`linkedin-dm` (punto 5, follow-ups).
6. Provisionar credencial Google Sheets (#3) — en curso, el usuario la está creando.
