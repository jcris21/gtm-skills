# Outbound Pipeline Tracker

Plantilla para registrar, por fase, los outputs clave que cada skill del pipeline produce sobre un prospecto — desde detección de señal hasta respuesta. Una fila = un prospecto, de punta a punta.

**Principio de diseño:** cada columna es o bien **binaria/label** (para escanear en segundos: Y/N, score, enum) o **descriptiva corta** (1 frase, para la nuance que una etiqueta no puede capturar — la Situación, el ángulo, la objeción). Nada de párrafos en la tabla: el detalle completo (copy generado, nota de Attio) vive en el CRM; esta tabla es el cockpit, no el archivo.

---

## Cómo se llena, por fase

| Fase | Skill que la produce | Qué escribir | Tipo de dato |
|---|---|---|---|
| 0. Contexto | `/gtm-context` | (no es por fila — una sola vez por workspace, ver `context/offer.md`) | — |
| 1. Señal | `/job-search`, `/prospect-posts`, `/signal-builder` | Score 0-10, tipo de señal, 1 línea de situación, canal disponible (email/LinkedIn), **+ transparencia:** qué se detectó (hallazgo factual que sustenta el score) y los key data points usados | Label + descriptivo corto |
| 2. Enriquecimiento | `/creative-variable` | Variable de personalización usada + su fuente (página/URL específica) | Descriptivo corto + label |
| 3. Personalización | `/email-writer`, `/linkedin-dm` | Canal(es) usados, patrón (Pain-led/Value-led/Segment fallback), persona matcheada (rol → fila de `context/icp.md`), historia de prueba usada (vertical/track de `context/playbooks/segment-stories.md`, o "—" si no hay), ángulo en 1 línea, QA pass, **+ transparencia:** 1 línea de por qué QA pasó/falló | Label + descriptivo corto |
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

| Prospecto | Empresa | URL LinkedIn Profile | Score (0-10) | Signal Type | Situación (1 línea) | Qué se Detectó (1 línea) | Key Data Points | Email? | LinkedIn? | Variable Personalización | Fuente Variable | Canal(es) | Patrón | Persona Matcheada | Historia de Prueba | Ángulo (1 línea) | QA Pass | QA Rationale (1 línea) | Nota Drafted? | Autorizado? | Fecha Autoriz. | Cadence Tier | Enviado? | Fecha Envío | Send Action | Network Dist. | Combined Touch Count | Respondió? | Clasificación | Follow-up creado? | Etapa | Próxima Acción | Input Tokens | Output Tokens | Costo LLM (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jane Doe | Acme Inc | — (lead sintético de ejemplo, sin perfil real) | 8 | Role-replaced | Contratando "RevOps Manager" — sin tooling de forecasting hoy | Job post activo para "RevOps Manager", 0 menciones de forecasting tooling en su stack | recent_hire_role: RevOps Manager; team_size: 12 | Y | Y | `{{recent_hire_role}}` = RevOps Manager | Careers page, posting del 2026-07-28 | Both | Pain-led | COO / VP Operations | — (segmento sin historia aún) | Vi que están armando RevOps desde cero | Y | Pasa "Would I reply?" — mensaje específico, no genérico | Y | Y | 2026-08-01 | Alto (8-10) | Y | 2026-08-02 | Email | N/A | 1 | N | — | N | Outreach Sent | Esperar 3-4 días, evaluar Email 2 | N/A | N/A | N/A |
| TEST — chriscob LinkedIn (Pipeline Dry Run) | — (sin empresa ICP; perfil resuelve a org. de gobierno) | — (no registrada en Attio para esta fila de prueba) | 1 | None | Sin dolor operativo propio detectado; perfil de gobierno, sin fit de ICP | Perfil de gobierno, sin firmographic match con el ICP | — (sin key data points, sin señal) | N | Y | — (sin señal suficiente para justificar variable) | — (no aplica, sin señal) | LinkedIn | Segment-fallback | — (no aplica, no hay persona ICP) | — (sin fit de vertical/track) | Genérico de segmento (dependencia de ERP/partners) — sintético, no personalizado | N (falló "Would I reply?" honestamente) | Falla — mensaje genérico de segmento, no hay hook específico del prospecto | Y | N | — | Fallback (1-2) | N | — | — | N/A | 0 | N | — | N | Drafted | Prueba mecánica completa — no perseguir, no hay lead real detrás | N/A | N/A | N/A |
| Christian Cobian G. (LinkedIn) | — (independiente, sin empresa) | https://www.linkedin.com/in/christian-j-cobian | 1 | None | AI consultant/PM independiente, en búsqueda de empleo; sin rol operativo ni empresa ICP | Perfil individual sin empresa; sin firmographic match | — (sin key data points, sin señal) | N | Y | — (sin señal suficiente para justificar variable) | — (no aplica, sin señal) | LinkedIn | Connection-note | — (no aplica, no hay persona ICP) | — (sin fit de vertical/track) | Sin ángulo — prueba mecánica de invite, no hay ICP match | Pass (honesto, transparente) | Pasa — invite transparente, no pretende ser algo que no es | Y | Y | 2026-08-06 | Fallback (1-2) | Y | 2026-08-06 | Invite | 2nd | 1 | Y | INTERESTED (Low confidence) | Y (escalación, no follow-up normal) | Interested | Reply ambiguo "It's interesting" — /reply-handler corrido y logueado en Attio (nota eae93a11, tarea cbaadef7); NO es lead real (no ICP) — tarea de escalación pide confirmar si se manda la respuesta como mensaje personal, no como campaña | N/A | N/A | N/A |
| TEST — Raymond Bailey (Pipeline Dry Run) | Yumwoof Natural Pet Food | https://www.linkedin.com/in/raymond-bailey-561b5259 | 2 | Firmographic-only | Co-Founder de marca de pet food (Consumer Goods) creciendo en 2 regiones sobre Shopify; sin señal operativa activa detectada | Industria y rol matchean ICP (Consumer Goods, Founder); sin careers page, sin mención de ERP/ops en el sitio | industry: Consumer Goods (pet food); hq: Austin TX + London; ecommerce_platform: Shopify | N | Y | — (sin señal suficiente para justificar variable específica de dolor) | Sitio yumwoof.com (WebFetch, sin careers/ERP mencionados) | LinkedIn | Segment-fallback | Founder / CEO | — (sin fit de vertical/track cargado aún) | Genérico de segmento — cómo manejan ops/inventario al escalar entre regiones | N (falló "Would I reply?" honestamente) | Falla — no hay hook específico del prospecto, solo firmographic match | Y (Attio person 83e27eda-9ebe-404c-a0cb-bfbf87e0748f, notas Signal Analysis + Campaign Drafted 2026-08-17) | Pending | — | Fallback (1-2) | N | — | — | 3rd | 0 | N | — | N | Drafted | Registrado en Sheet (OutboundQueue, fila 2) a pedido explícito del usuario para probar el gate a score bajo — pendiente de aprobación humana (`aprobado=No`), QA ya falló "Would I reply?" | N/A | N/A | N/A |
| TEST — Christopher Rosiak (Pipeline Dry Run) | — (sin empresa identificable en el perfil) | https://www.linkedin.com/in/christopher-rosiak-7b1aa830/ | 1 | None | CEO/Founder, LA; perfil sin nombre de empresa visible — imposible evaluar criterios Company-level del ICP | Perfil sin empresa asociada; sin firmographic match verificable | — (sin key data points, sin señal) | N | Y | — (sin señal suficiente para justificar variable) | — (no aplica, sin señal) | LinkedIn | Connection-note | — (no aplica, no hay empresa que matchear) | — (sin fit de vertical/track) | Sin ángulo — prueba mecánica de connection note, no hay ICP match | Pass (honesto, transparente) | Pasa — nota genérica de founder-to-founder, no finge un hook que no existe | N (no se logueó en Attio — prueba mecánica local) | N | — | Fallback (1-2) | N | — | — | 3rd | 0 | N | — | N | Drafted | Registrado en Sheet (OutboundQueue, lead_id `test-christopher-rosiak`, fila 13) a pedido explícito del usuario — pendiente de aprobación humana | N/A | N/A | N/A |
| TEST — Dustin Cash (Pipeline Dry Run) | SOS Beauty Group | https://www.linkedin.com/in/dcash/ | 2 | Firmographic-only | Co-Founder/CEO de brand incubator de belleza (8 marcas gestionadas); sitio real es sosbty.com (sosbeauty.com/sosbeautygroup.com están caídos/parkeados) | Sitio recorrido completo (Home, Our Team, Press, Brand Incubation) — sin careers page, sin queja pública, press desactualizado (2020-2021, sin evento de crecimiento reciente). Fit de industria ambiguo: es agencia de brand management/incubation, no un operador directo de Wholesale/Distribution/E-commerce — zona gris del hard gate, no un fail claro | industry: brand incubation agency (adyacente a Consumer Goods, no operador directo); role: Co-Founder & CEO; team_size_publico: 2 (Dustin Cash + Charlene Valledor); site_status: accesible (sosbty.com) | N | Y | — (sin señal suficiente para justificar variable específica de dolor) | sosbty.com — Home, /pages/our-team, /pages/press, /pages/brand-incubation (navegador, recorrido completo) | LinkedIn | Segment-fallback | Founder / CEO | — (sin fit de vertical/track cargado aún) | Genérico de segmento — cómo manejan ops/reporting across multiple brands | N (falló "Would I reply?" honestamente) | Falla — sitio confirmado sin señal de dolor operativo activo, solo firmographic match | N (no se logueó en Attio — prueba mecánica local) | N | — | Fallback (1-2) | N | — | — | 3rd | 0 | N | — | N | Drafted | Registrado en Sheet (OutboundQueue, lead_id `test-dustin-cash`, fila 14) a pedido explícito del usuario — pendiente de aprobación humana | N/A | N/A | N/A |
| TEST — Iqbal Safdar (Pipeline Dry Run) | Unknown (sin empresa identificable en el perfil) | https://www.linkedin.com/in/iqbal-safdar-cpa-fca-03148629/ | 1 | None | CPA/FCA, sin empresa asociada visible — imposible evaluar criterios Company-level del ICP | Perfil individual sin empresa; sin firmographic match verificable | — (sin key data points, sin señal) | N | Y | — (sin señal suficiente para justificar variable) | — (no aplica, sin señal) | LinkedIn | Segment-fallback | — (no aplica, no hay persona ICP) | — (sin fit de vertical/track) | Sin ángulo — prueba mecánica de connection note, no hay ICP match | N (falló "Would I reply?" honestamente) | Falla — CPA/FCA individual, no matchea con buyer personas del ICP (no es Founder/COO/VP Ops) | Y (Sheet, lead_id `test-iqbal-safdar`, fila 15) | N | — | Fallback (1-2) | N | — | — | N/A | 0 | N | — | N | Drafted | Registrado en Sheet a pedido explícito del usuario — pendiente de aprobación humana | N/A | N/A | N/A |
| Sébastien Aubert | Adastra Films | https://www.linkedin.com/in/adastrafilms | 1 | None | Film production company en Cannes (~5 staff, est. 2008); sin dolor operativo ICP detectable — **override del hard gate aprobado por el usuario** | Ninguna señal ICP: industria film/entretenimiento fuera de verticales, sin hiring/crecimiento/stack operativo; único match: persona (Founder/CEO) | industry: film production; hq: Cannes FR; team_size: ~5; credits: Sundance/Berlinale/Netflix; founders: Aubert + Guiraud | N | Y | — (sin señal suficiente para justificar variable — rechazada como personalización forzada) | — (no aplica, sin señal) | LinkedIn | Connection-note | Founder / CEO | — (sin fit de vertical/track) | Sin señal ICP — nota transparente founder-to-founder, sin hook operativo fabricado | Y (honesto, transparente) | Pasa — nota de conexión transparente, no finge un hook de dolor que no existe | Y (Sheet Message1Queue, lead_id `adastra-films-sebastien-aubert`; **Attio pendiente — sin MCP de Attio esta sesión**) | Pending | — | Fallback (1-2) | N | — | — | — (por resolver en find-profile) | 0 | N | — | N | Drafted | En Sheet (Message1Queue) pendiente de aprobación humana (aprobado=No) — editar/autorizar ahí, n8n envía; loguear nota Signal Analysis + Campaign Drafted en Attio manualmente | N/A | N/A | N/A |
| *(fila por prospecto...)* | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |

---

## Vista rápida — decisor GTM (subset para revisión semanal)

Para no perder 10 minutos escaneando 24 columnas: esta es la vista que un GTM lead revisa en la reunión semanal — solo lo que cambia una decisión.

| Prospecto | Score | Canal(es) | Etapa | Respondió? | Clasificación | Próxima Acción |
|---|---|---|---|---|---|---|
| Jane Doe | 8 | Both | Outreach Sent | N | — | Esperar 3-4 días |
| TEST — chriscob LinkedIn | 1 | LinkedIn | Drafted | N | — | Prueba mecánica completa — no perseguir |
| TEST — Raymond Bailey | 2 | LinkedIn | Drafted | N | — | En Sheet, pendiente de aprobación humana |
| TEST — Christopher Rosiak | 1 | LinkedIn | Drafted | N | — | En Sheet, pendiente de aprobación humana |
| TEST — Dustin Cash | 2 | LinkedIn | Drafted | N | — | En Sheet, pendiente de aprobación humana |
| TEST — Iqbal Safdar | 1 | LinkedIn | Drafted | N | — | En Sheet, pendiente de aprobación humana |
| Sébastien Aubert | 1 | LinkedIn | Drafted | N | — | En Sheet (Message1Queue), pendiente de aprobación humana — Attio note pendiente (sin MCP esta sesión) |

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
- `Qué se Detectó`, `Key Data Points`, `Fuente Variable` y `QA Rationale` son columnas de **transparencia**, no de decisión: existen para que un revisor entienda *por qué* el Score/Signal Type/Variable Personalización/QA Pass salieron como salieron, sin tener que abrir Attio. Mismo principio de la sección de arriba — label o 1 línea, nunca párrafos; el razonamiento completo del skill (todas las señales rankeadas, no solo la ganadora) sigue viviendo solo en el output del skill y la nota de Attio. Por eso no aparecen en la "Vista rápida — decisor GTM": esa vista es solo lo que cambia una decisión en la reunión semanal, no el audit trail.
- `Input Tokens` / `Output Tokens` / `Costo LLM (USD)` solo se llenan cuando el pipeline corrió programáticamente contra la API (`utils/token_ledger.py` registrando cada llamada, `utils/token_report.py --lead-id <id>` generando el rollup). Si el lead se trabajó a mano por chat de Claude Code, estas columnas quedan en `N/A` — no estimarlas desde el costo de sesión, que mezcla todos los leads y no es atribuible a uno solo. El precio por modelo vive en `context/pricing/model-pricing.json` (marcado `_verified: false` hasta confirmar contra la página oficial de precios de Anthropic), no hardcodeado en los scripts.
