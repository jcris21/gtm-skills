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
2. Escribir una fila nueva en una Google Sheet vía un script nuevo `utils/sheet_queue.py` (mismo patrón que `utils/unipile.py`: dotenv + client, CLI + función importable).
3. Detenerse — no preguntar en chat, no enviar. El chat solo confirma "draft escrito en la fila N de la Sheet."

### 3.2 Columnas de la Sheet

| Columna | Contenido |
|---|---|
| `lead_id` | Record ID de Attio |
| `canal` | `linkedin` / `email` |
| `draft` | Texto del Mensaje 1 |
| `contexto` | Resumen de señal/persona usado (para que el revisor no tenga que ir a Attio) |
| `editado` | Texto final si el humano lo reescribió (vacío = usar `draft` tal cual) |
| `aprobado` | Sí/No, default No |
| `enviado` | Sí/No, default No — lo marca n8n después de enviar, evita doble envío |
| `timestamp_draft` | Cuándo se escribió la fila |

### 3.3 n8n — poll y envío

Workflow nuevo: trigger (cron o botón manual — **decisión pendiente, §6**) → lee filas `aprobado=Sí` AND `enviado=No` → envía vía Unipile (LinkedIn) o el sender correspondiente (email) usando `editado` si no está vacío, si no `draft` → marca `enviado=Sí` → log en Attio (nota + touch count).

---

## 4. Follow-ups — trigger de escalamiento (nuevo, análogo a `reply-handler` Step 4)

**Estado: sin definir — decisión pendiente, §6.** `reply-handler` ya tiene 4 triggers de escalamiento para replies (Step 4). `linkedin-dm`/`email-writer`'s `reference/sequence-framework.md` no tiene un concepto equivalente para follow-ups salientes. Candidatos a discutir (ninguno confirmado):
- El signal score cambió significativamente desde que se redactó Mensaje 1 (señal nueva detectada).
- Es el último follow-up del tier (Alto, Follow-up B) — el "cierre" antes de abandonar la secuencia.
- Nunca — todo follow-up no-escalado auto-envía siempre, sin excepción de este tipo.

Una vez definido, se documenta acá y en `sequence-framework.md`.

---

## 5. Subworkflow Slack HITL compartido (solo casos escalados)

Se extraen los Nodes 10-11 del spec original de `n8n_Reply_Handler_Automation.md` (Slack Interactive Blocks con Approve/Edit-vía-modal/Reject + envío Unipile) a un **subworkflow reusable**, parametrizado por canal y texto del draft. Lo llaman dos flujos:
- `reply-handler`, cuando su Node 6 (escalation gate) es `true`.
- El follow-up outbound, cuando cumple el trigger de §4.

No se usa para Mensaje 1 (eso va por Sheets, §3) ni para replies/follow-ups no-escalados (esos auto-envían, sin gate).

---

## 6. Decisiones abiertas — bloquean construcción

1. **Trigger de escalamiento para follow-ups (§4)** — sin definir.
2. **Trigger del envío de filas aprobadas en la Sheet (§3.3)** — ¿cron periódico (n8n barre la Sheet cada N horas) o botón/webhook manual que el operador dispara cuando termina de revisar un batch? Afecta la demora entre aprobar y enviar.
3. **Credencial Google Sheets API** — no existe hoy en `.env` ni en n8n. Provisionar cuenta de servicio + compartir la Sheet con ella.
4. **Volumen de redacción, no solo de aprobación** — 100 Mensajes 1 hoy se siguen redactando uno por uno en una sesión interactiva de Claude Code (se descartó explícitamente correr esto programáticamente contra la API de Anthropic por costo). Este documento resuelve el cuello de botella de *aprobación*; el de *redacción* queda fuera de alcance salvo que se decida lo contrario.

---

## 7. Fases de construcción

1. Definir trigger de escalamiento de follow-ups (§4) — bloqueado por decisión #1.
2. Send Gate: Step 7 de `email-writer`/`linkedin-dm` escribe a Sheet en vez de preguntar en chat (§3.1) + `utils/sheet_queue.py`.
3. n8n: poll + envío de filas aprobadas (§3.3) — bloqueado por decisión #2.
4. Subworkflow Slack HITL compartido (§5), extraído del spec de reply-handler.
5. Auto-send para casos no-escalados — ya reflejado en la corrección de `n8n_Reply_Handler_Automation.md` (ver su changelog); falta la contraparte para follow-ups una vez cerrado el punto 1.
6. Provisionar credencial Google Sheets (#3).
