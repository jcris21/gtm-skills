# Leyenda — Tabla OutboundQueue (Google Sheets)

Diccionario de datos de la hoja `OutboundQueue` (`GOOGLE_SHEETS_WORKSHEET_NAME` en `.env`, spreadsheet `195CuTqAt_ty2oxI-KKbbS1A0BxTc8OEzbzRNIaQy6HM`), escrita/leída por `utils/sheet_queue.py`. El orden de columnas abajo es el orden real de `COLUMNS` en ese script — **no reordenar la hoja**, solo se permite agregar columnas nuevas al final (ver docstring de `sheet_queue.py`).

Una fila = un lead (`lead_id`). Ambos canales (email/LinkedIn) pueden convivir en la misma fila.

---

## 1. Identidad

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `lead_id` | Clave única del lead — permite hacer upsert (actualizar la misma fila en vez de duplicar) cuando `email-writer` y `linkedin-dm` corren para el mismo prospecto. | Provisto por quien llama a `upsert_draft`/`batch_insert_leads` (típicamente el `record_id` de Attio o un ID sintético en pruebas). No se calcula en la hoja. |

## 2. Metadata de señal (Fase 1 — `/job-search`, `/prospect-posts`, `/signal-builder`)

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `prospecto` | Nombre del lead, para escaneo humano rápido. | Texto libre, provisto por el skill que hace el upsert. |
| `empresa` | Empresa del lead, para escaneo humano rápido y contexto de ICP. | Texto libre, provisto por el skill. |
| `score` | Prioridad de intención de compra (0-10) — determina el tier de cadencia de envío. | Asignado por `/signal-builder` según la fuerza de la señal detectada: 8-10 = highest intent, 5-7 = strong, 3-4 = moderate, 1-2 = fallback (`signal-builder/skill.md`). Regla del skill: **no inflar el score** — un 4/10 es información útil, no un fallo a esconder. |
| `signal_type` | Categoriza qué tipo de evento disparó el outreach — vocabulario fijo, no inventar variantes. | Uno de: `Role-replaced` · `Adjacent-hiring` · `Leadership-hire` · `Competitor-friction` · `Content-signal` · `Growth-event` · `Firmographic-only` · `None`. Determinado por `/signal-builder` según qué señal ganó (ver `signal-builder/reference/signal-types.md` Sección 3; `Growth-event` sigue lo que `context/icp.md` defina como Growth Signal). |
| `situacion` | Resume en 1 línea la situación de negocio del lead (el "por qué ahora") — la nuance que un label no captura. | Descriptivo corto, redactado por `/signal-builder` a partir de la señal ganadora. |
| `senal_detectada` *(transparencia)* | Hallazgo factual concreto que sustenta el `score`/`signal_type`, para que un revisor no tenga que reabrir el scan de señales ni Attio. | Copiado por `email-writer`/`linkedin-dm` desde "What was detected" del signal scan de `/signal-builder` (Step 5, la señal que gana), al momento de redactar el draft — no en el momento del scan. 1 línea, sin párrafos. |
| `key_data_points` | Datos concretos (variable: valor) usados para justificar/personalizar la señal. | Copiado por `email-writer`/`linkedin-dm` desde "Key data points for copy" del mismo scan de `/signal-builder`. Formato corto tipo `var: value` (p. ej. `recent_hire_role: RevOps Manager; team_size: 12`). |

## 3. Canal disponible

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `email_disponible` | Indica si hay un email válido para este lead. | `Y` / `N` / `Pending` — determinado en Fase 1 al enriquecer el lead (no se guarda el email en sí, solo la disponibilidad; ver nota en `sheet_queue.py` sobre el edge case del email crudo). |
| `linkedin_disponible` | Indica si hay perfil de LinkedIn accesible. | `Y` / `N` / `Pending`, igual que arriba. |
| `linkedin_url` | Target directo de envío para LinkedIn (DM/Invite), sin necesitar lookup en Attio. | URL del perfil, provista en Fase 1. Resuelve la mitad "LinkedIn" del edge case 1 de `n8n_Message1_Send_Flow.md` §6. |

## 4. Enriquecimiento (Fase 2 — `/creative-variable`)

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `variable_personalizacion` | La variable específica usada para personalizar el mensaje (el gancho concreto, no genérico). | Producida por `/creative-variable`, formato `{{nombre_variable}} = valor` (p. ej. `{{recent_hire_role}} = RevOps Manager`). |
| `fuente_variable` *(transparencia)* | De dónde salió esa variable — permite verificar que no es inventada. | Página/URL específica + fecha, provista por `/creative-variable` (p. ej. "Careers page, posting del 2026-07-28"). |

## 5. Personalización / Draft (Fase 3 — `/email-writer`, `/linkedin-dm`)

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `canal_envio` | Qué canal(es) tienen draft cargado en esta fila. | **Calculado, no manual**: `_canal_envio()` en `sheet_queue.py` revisa si `draft_email`/`draft_linkedin` están no-vacíos → `Email`, `LinkedIn`, o `Both`. Se recalcula en cada upsert. |
| `patron` | Estrategia retórica del mensaje. | Uno de `Pain-led` · `Value-led` · `Segment-fallback` · `Connection-note`, elegido por `email-writer`/`linkedin-dm` según la fuerza de la señal (score alto → Pain-led; sin señal → Segment-fallback/Connection-note). |
| `persona_matcheada` | Rol/buyer persona al que se dirige el mensaje. | No es vocabulario fijo — debe coincidir exactamente con el nombre de rol en la columna "Buyer Persona" de `context/icp.md`. Si `icp.md` cambia sus personas, esta columna sigue el cambio automáticamente. |
| `historia_prueba` | Caso de éxito / social proof usado, si aplica. | Vertical/track tomado de `context/playbooks/segment-stories.md`, o `—` si el segmento no tiene historia aún. |
| `angulo` | El gancho/ángulo concreto del mensaje, en 1 línea. | Redactado por `email-writer`/`linkedin-dm` combinando señal + variable de personalización + patrón. |
| `qa_pass` | Si el draft pasó el control de calidad interno antes de entrar a la cola de aprobación humana. | `Y`/`N`, resultado del check "Would I reply?" que corre el propio skill (`email-writer`/`linkedin-dm`) sobre su propio draft — mensaje específico y no genérico = pass. |
| `qa_rationale` *(transparencia)* | Por qué pasó o falló el QA, en 1 línea — para que el revisor no tenga que re-auditar el draft. | Redactado por el skill junto con `qa_pass` (p. ej. "Falla — mensaje genérico de segmento, no hay hook específico del prospecto"). |
| `draft_email` | Cuerpo del draft de email tal como lo generó el skill (antes de edición humana). | Escrito por `/email-writer` vía `upsert_draft(canal="email", ...)`. |
| `editado_email` | Versión editada por el humano revisor, si edita el draft antes de aprobar. | Editado manualmente en la hoja por el reviewer; el flujo de n8n debería preferir esta columna sobre `draft_email` si no está vacía. |
| `draft_linkedin` | Cuerpo del draft de LinkedIn (DM o invite) tal como lo generó el skill. | Escrito por `/linkedin-dm` vía `upsert_draft(canal="linkedin", ...)`. |
| `editado_linkedin` | Versión editada por el humano, análoga a `editado_email` pero para LinkedIn. | Editado manualmente en la hoja. |

## 6. Aprobación / envío (Gate HITL — `Documents/HITL_Send_Approval_Design.md` §3)

| Header | Objetivo | Cómo se calcula / de dónde sale |
|---|---|---|
| `aprobado` | Gate humano: si `Si`, la fila queda elegible para que n8n la envíe. | Default `No` al crear la fila; lo cambia manualmente el revisor humano en la hoja tras revisar/editar el draft. |
| `enviado` | Marca si el mensaje ya salió, para no reenviar. | Default `No` al crear la fila; lo pone `Si` automáticamente `mark_sent()` (llamado por el flujo n8n) tras un envío exitoso vía Unipile/email. |
| `timestamp_draft` | Cuándo se generó/actualizó el draft — usado para detectar filas estancadas (p. ej. `Autorizado? = Pending` con +48h). | ISO timestamp pasado explícitamente por el skill al llamar `upsert_draft`. |

---

## Notas generales

- **Columnas de transparencia** (`senal_detectada`, `key_data_points`, `fuente_variable`, `qa_rationale`): no son de decisión — existen para que un revisor entienda el *por qué* del `score`/`signal_type`/`variable_personalizacion`/`qa_pass` sin abrir Attio. Regla: 1 línea o lista corta `var: value`, nunca párrafos; el razonamiento completo sigue viviendo en el output del skill y la nota de Attio.
- El detalle completo del copy (asunto, cuerpo final, seguimiento) **no vive en esta hoja** — vive en la nota `Campaign Drafted`/`Campaign Sent` del Person record en Attio; esta hoja es el gate de aprobación, no el archivo.
- Estas 4 columnas de transparencia se agregaron **al final** de la hoja (no intercaladas) a propósito: insertar una columna antes de una existente desalinearía los valores de filas ya escritas, porque `sheet_queue.py` escribe por posición. Cualquier columna nueva futura debe seguir el mismo patrón: solo agregar al final de `COLUMNS`.
- `combined_touch_count`, `Fecha Envío`, `Send Action`, `Network Dist.`, `Respondió?`, `Clasificación`, `Etapa` (Fases 5-7) **no viven en esta hoja** — viven en Attio (`context/crm/attio-schema.md`, objeto `touches`) y en `Documents/Outbound_Pipeline_Tracker.md`. `OutboundQueue` cubre solo hasta el gate de aprobación/envío (Fases 1-3 + envío mecánico).
- Fuente completa de vocabulario fijo (labels): sección "Leyenda de labels" en `Documents/Outbound_Pipeline_Tracker.md`.


 Step 0 — Hard gate (pasa/no pasa): compara Company Size/Industry/Geography/Person contra context/icp.md. Raymond pasa en Industry (Consumer Goods) y Person (Founder). Esto es lo que "matchea ICP".
- Step 1-4 — Signal Score (0-10): no mide "encaja con el ICP" — mide timing, es decir, evidencia concreta de que ahora mismo tiene el dolor que resolvemos (vacante de rol reemplazado, queja pública, evento de crecimiento, competidor con fricción). Eso es un dato completamente distinto del fit demográfico.