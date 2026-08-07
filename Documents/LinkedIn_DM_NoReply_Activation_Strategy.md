# LinkedIn DM — Estrategia de Activación de Interés en Ausencia de Reply

Status: **Implementado** (2026-08-06) — wireado en `.claude/skills/linkedin-dm/reference/sequence-framework.md` y `linkedin-dm/skill.md` Step 5 (ver §6)
Complementa: `.claude/skills/linkedin-dm/skill.md` Step 5 (cadencia tiered ya existente)
No reemplaza: `.claude/skills/reply-handler/skill.md` — este documento gobierna la secuencia **mientras no hay reply**; en el momento que llega cualquier reply, el control pasa por completo a `/reply-handler` (ver §4).

---

## 0. Principio rector

La secuencia de no-reply existe **solo en ausencia de reply**. No es un cron job que manda mensajes a ciegas — cada touch programado requiere, antes de dispararse, una verificación explícita de que no llegó respuesta desde el touch anterior. El momento en que llega un reply — de cualquier tipo, positivo o negativo — la secuencia se detiene por completo y el control pasa a `/reply-handler`. No hay estado intermedio donde ambos flujos corren en paralelo.

---

## 1. Revisión: ¿email-writer ya tiene este escenario definido?

**Sí, con bastante profundidad — LinkedIn no.** Comparación directa:

| Elemento | `email-writer` (vía `reference/sequence-framework.md`) | `linkedin-dm` (Step 5, `skill.md`) |
|---|---|---|
| Cadencia tiered por score | Sí — 8-10 (5 emails/~3 sem), 3-7 (3 emails), 1-2 (mínimo) | Sí — 8-10 (2 follow-ups), 3-7 (1 follow-up), 1-2 (0 follow-ups) |
| Ventanas de tiempo explícitas | Sí — Day 1 / 3-4 / 7-8 / 12-14 / 18-21, con regla de "no Lunes antes de 10am, no Viernes después de 2pm" | Parcial — solo día objetivo (Day 3-4, Day 10-12), sin regla de horario/día de semana |
| Rotación de ángulo por touch | Sí — tabla explícita Email1→Email2, Email2→Email3, con 3 variantes de cierre (case study / resource / breakup) | No — solo dice "rotate the angle same as email-writer's Email 2 logic," sin adaptar a formato LinkedIn (más corto, sin subject, tono casual) |
| Template de "breakup" no manipulativo | Sí, explícito, con ejemplo prohibido ("I've sent you 3 emails...") | No existe |
| Regla explícita "cualquier reply detiene la secuencia" | Sí — sección "Handling replies" dedicada | Implícito (vía el gate de envío que ya existe), pero nunca escrito como regla de secuencia |
| Archivo de referencia dedicado | Sí — `email-writer/reference/sequence-framework.md` | No existe equivalente |

**Conclusión:** el gap no es que LinkedIn no tenga cadencia — la tiene (se agregó esta sesión). El gap es que le falta la capa de *detalle operativo* que email sí tiene: ventanas horarias, contenido específico por touch, mecanismo de trigger explícito, y el manejo de reply escrito como regla, no solo implícito. Este documento cierra ese gap.

---

## 2. Tiers — misma escala que el resto del pipeline

Usa el mismo `Cadence Tier` ya definido en `context/crm/attio-schema.md`'s objeto `touches` y en `Documents/Outbound_Pipeline_Tracker.md` — no se inventa una escala nueva. El nivel se decide por `signal_score` (0-10, misma escala reconciliada entre `job-search` y `signal-builder`).

| Tier | Signal score | Touches totales | Ya definido en `linkedin-dm/skill.md` Step 5 |
|---|---|---|---|
| **Fallback** | 1-2 | 1 (solo Message 1 / connection note) | Sí |
| **Estándar** | 3-7 | 2 (Message 1 + 1 follow-up) | Sí |
| **Alto** | 8-10 | 3 (Message 1 + 2 follow-ups) | Sí |

Este documento no cambia esos conteos — los toma como fuente de verdad y les agrega ventana de tiempo, trigger, y contenido por touch.

---

## 3. Ventanas, trigger y contenido por tier

### Fallback (1-2)

- **Touches:** 1 — solo el connection note / Message 1 inicial.
- **Follow-up:** ninguno. Una señal débil o ausente no gana intentos de reactivación — mismo principio que `email-writer` aplica a este tier ("a weak signal doesn't earn more attempts").
- **Trigger:** N/A.
- **Si no hay reply:** el prospecto queda en `Etapa = Outreach Sent`. No se reintenta salvo que aparezca una señal nueva (ver §5).

### Estándar (3-7)

| Touch | Ventana | Trigger para disparar | Contenido |
|---|---|---|---|
| Message 1 | Día 1 | Envío inicial (no aplica trigger de no-reply) | Pattern por Step 3 de `linkedin-dm/skill.md` (Pain-led / Value-led / Segment fallback / Connection note), framing por persona matcheada |
| Follow-up | Día 3-4 | **Sin reply detectado** en el chat desde Message 1, verificado antes de redactar/enviar (ver §4 mecanismo de verificación) | Ángulo rotado — ver tabla de rotación abajo |

**Ventana horaria recomendada:** martes a jueves, media mañana a media tarde — mismo principio de `sequence-framework.md`'s regla para email (evitar Lunes temprano / Viernes tarde), adaptado a LinkedIn sin datos propios de open-rate verificados; tratar como heurística razonable, no como cifra medida.

### Alto (8-10)

| Touch | Ventana | Trigger para disparar | Contenido |
|---|---|---|---|
| Message 1 | Día 1 | Envío inicial | Pattern por Step 3, framing por persona |
| Follow-up A | Día 3-4 | Sin reply desde Message 1 | Ángulo rotado (ver tabla) |
| Follow-up B | Día 10-12 | Sin reply desde Message 1 **ni** desde Follow-up A | Cierre — proof point breve o breakup no manipulativo (ver §3.3) |

**Por qué la ventana se abre a Día 10-12 (vs. Día 7-8 de email):** email en este mismo tier ya llega hasta Día 18-21 en su quinto touch — espaciar el segundo follow-up de LinkedIn más lejos evita que, en una semana dada, el prospecto reciba un email Y un DM el mismo día (ver §3.4, coordinación cross-channel). No es una cifra medida — es una decisión de diseño para no duplicar presión en la misma ventana que email ya cubre.

### 3.1 Rotación de ángulo por touch (adaptado de `sequence-framework.md`, formato LinkedIn)

| Message 1 fue... | Follow-up A rota a... |
|---|---|
| Pain-led | Value-led ligero, o social proof ("hablé con varias empresas en tu situación...") — nunca repetir el mismo pain con otras palabras |
| Value-led | Pain-led — ahora sí nombrar el costo concreto de no resolverlo |
| Segment fallback | Social proof — referencia genérica a patrones del segmento, no del prospecto individual |
| Connection note (aún no conectado) | Si aceptó la conexión, el primer DM real ya funciona como "Message 1" — no se cuenta como follow-up adicional dentro del cap del tier |

### 3.2 Fuente del contenido — no hardcodear, igual que el resto del pipeline

El contenido de cada touch se resuelve igual que `linkedin-dm/skill.md` Step 2/4 ya hace: persona matcheada contra `context/icp.md`, proof point (si existe) contra `context/playbooks/segment-stories.md`. Este documento no repite esa lógica ni la contradice — solo especifica *cuándo* y *qué ángulo* usar en cada touch, no *de dónde* sale el texto.

### 3.3 Template de cierre (Follow-up B, solo tier Alto)

No manipulativo, no menciona que ya se mandaron mensajes antes, deja la puerta abierta a un trigger futuro en vez de mendigar respuesta:

> "[Situación breve, 1 línea]. Si esto se vuelve prioridad, avísame — sigo por aquí."

Prohibido explícitamente (mismo principio que `sequence-framework.md` §"Angle rotation strategy" ya establece para email):
- "Solo quería asegurarme de que no se perdió esto"
- "Te escribí hace unos días..."
- Cualquier variante de "bump" o guilt-trip

### 3.4 Coordinación cross-channel

Cuando el prospecto tiene ambos canales (`Canal(es) = Both`), `combined_touch_count` ya limita el total combinado (ver `context/crm/attio-schema.md`). Regla adicional de espaciado: **no programar un touch de LinkedIn el mismo día que un touch de email ya programado** para el mismo prospecto — mínimo 1 día de separación entre cualquier par de touches cross-channel, para que no reciba dos mensajes el mismo día por canales distintos.

---

## 4. Mecanismo de verificación del trigger (hoy manual, no automatizado)

Este pipeline hoy se invoca por chat de Claude Code, no vía el runner programático ni la automatización n8n (`Documents/n8n_Signal_Alert_Automation.md`, aún deferred). Por eso, "trigger" aquí significa una verificación manual antes de cada touch programado, no un cron real:

1. **¿Se cumplió la ventana de tiempo?** — contar desde `sent_at` del último Touch registrado en Attio (`context/crm/attio-schema.md`'s objeto `touches`).
2. **¿Llegó algún reply?** — revisar el chat en Attio/Unipile antes de redactar el siguiente touch. Si llegó cualquier mensaje inbound desde el último envío, **no** se redacta el siguiente touch de la secuencia — se detiene aquí (ver §4.1).
3. **¿Ya se llegó al cap del tier?** — chequear `combined_touch_count` contra el tope del tier (mismo gate que `linkedin-dm/skill.md` Step 7 ya implementa).

Solo si (1) es verdadero, (2) es falso, y (3) es falso se redacta y envía el siguiente touch.

Cuando se construya la automatización de alertas en tiempo real (punto 2 de `Documents/Decisions/Outbound_Playbook_Alignment.md`, hoy deferred), este chequeo puede volverse automático — este documento no depende de esa automatización para ser útil hoy, solo describe el mismo chequeo hecho a mano.

### 4.1 Regla explícita: cualquier reply detiene la secuencia

- Un reply de cualquier clasificación (`INTERESTED`, `OBJECTION`, `NOT_NOW`, `NOT_INTERESTED`, `QUESTION`, `OUT_OF_OFFICE`) cancela **todos** los touches futuros de la secuencia de no-reply para ese prospecto. El control pasa a `/reply-handler`.
- **Excepción — `OUT_OF_OFFICE`:** no se cancela, se **pausa**. Se retoman los touches restantes del tier después de la fecha de regreso indicada, recalculando las ventanas desde el punto de reanudación, no desde el Día 1 original.
- Si `/reply-handler` genera un nuevo touch saliente (por ejemplo, una respuesta a una `OBJECTION`), ese nuevo touch cuenta contra `combined_touch_count` pero **no reinicia** la secuencia de no-reply original — esa secuencia ya terminó en el momento del reply.

---

## 5. Cuándo NO reactivar (mismo principio que `sequence-framework.md`)

- Nunca mandar un touch "extra" fuera de los definidos por tier — no hay Touch 4, 5, 6 en ningún tier.
- Nunca usar un "bump" o "checking in" fuera del trigger definido.
- Reactivar solo si aparece una **señal nueva** (nuevo job post, nuevo evento de crecimiento según el campo Growth Signal de `context/icp.md`) — eso es una secuencia nueva con contexto nuevo, no una continuación. Correr `/signal-builder` de nuevo para obtener un score fresco antes de reabrir.

---

## 6. Wireado al skill (2026-08-06)

Los tres pasos que faltaban ya están hechos:

1. **`.claude/skills/linkedin-dm/reference/sequence-framework.md`** — versión operativa de este documento, mismo formato que `email-writer/reference/sequence-framework.md`.
2. **`linkedin-dm/skill.md` Step 5** — ahora apunta a ese archivo de referencia, mismo patrón que `email-writer/skill.md` Step 5.
3. **Chequeo explícito de reply** — Step 5 ahora exige correr el trigger check de `reference/sequence-framework.md` (ventana cumplida / sin reply / cap no alcanzado) antes de redactar cualquier follow-up, con la excepción de `OUT_OF_OFFICE` (pausa, no cancela).

Este documento sigue siendo la referencia de diseño/racional — la lógica operativa que el skill realmente ejecuta vive en `reference/sequence-framework.md`. Si uno se edita, revisar que el otro siga siendo consistente.
