# Manual del Pipeline de Outbound con IA — Guía para Marketing y Negocio

**Para quién es este documento:** cualquier persona del lado de Marketing o Negocio que necesite entender qué hace el sistema, sin necesidad de leer código. El objetivo es que puedas: (1) entender el recorrido completo de un prospecto, de punta a punta; (2) detectar huecos o cosas que no te convencen; (3) dar feedback específico sobre qué cambiar.

No vas a encontrar nombres de archivos ni código acá salvo cuando ayuda a ubicar de qué se está hablando en otros documentos técnicos. Si en algún punto querés el detalle técnico, al final hay una sección "Dónde mirar más".

---

## 1. Qué hace este sistema, en una frase

Encuentra empresas que probablemente necesiten lo que vendemos *ahora* (no en general), les escribe un mensaje personalizado por email y/o LinkedIn, **espera que una persona lo apruebe**, lo envía, y cuando el prospecto contesta, sugiere cómo responder — todo sin inventar datos sobre el prospecto ni mandar nada sin luz verde humana.

No es un sistema de spam masivo. Es más lento y más selectivo que eso a propósito: prioriza calidad de la señal sobre volumen de envíos.

---

## 2. Antes de arrancar: los dos documentos que definen todo

Todo lo que el sistema escribe sale de dos documentos base. Si algo suena mal en un mensaje generado, la causa casi siempre está en uno de estos dos, no en la "IA":

- **A quién le vendemos (el ICP):** tamaño de empresa (15–100 empleados), industria (mayoristas, distribución, importación/exportación, e-commerce, manufactura ligera, bienes de consumo), geografía (Estados Unidos), y una señal de crecimiento (10+ contrataciones en 12 meses, o noticias de expansión/financiamiento). También define **6 tipos de compradores** (Founder/CEO, COO/VP Operaciones, Gerente de Operaciones, CFO, CIO/IT, Director Comercial) con sus dolores y beneficios específicos, y cuántos contactos perseguir por cuenta según su tamaño.
- **Qué vendemos (la Oferta):** "Intelligent Odoo Transformation™" — ayudamos a empresas en crecimiento a transformar Odoo (su ERP) de un sistema tradicional a un sistema operativo de negocio potenciado por IA, para que el equipo interno opere el sistema en vez de depender de agencias externas para cada cambio.

**Herramienta que arma estos dos documentos:** `gtm-context` — se corre una sola vez por proyecto (o cuando el ICP/Oferta cambian), a través de una serie de preguntas guiadas. Es la única herramienta que "sabe" cosas por conversación directa con una persona; todas las demás leen lo que `gtm-context` dejó escrito.

**Por qué importa para Marketing:** si el ICP o la Oferta están desactualizados, mal segmentados, o no reflejan el posicionamiento real, **todo lo que sigue hereda ese error** — el sistema no puede "saber" mejor que estos dos documentos. Revisarlos y mantenerlos al día es, literalmente, la palanca de mayor impacto sobre la calidad de todo el pipeline.

---

## 3. El viaje de un prospecto, de punta a punta

### Etapa 0 — Investigación (opcional)
**Qué pasa:** antes de escribirle a alguien, el sistema puede revisar (a) las vacantes de empleo que la empresa publicó recientemente, y (b) posts recientes de LinkedIn de la persona, buscando menciones de un tema específico (por ejemplo, quejas sobre su ERP actual).
**Herramientas:** `job-search` (vacantes publicadas, vía TheirStack) y `prospect-posts` (posts de LinkedIn, vía Apify) — corren de forma independiente, cada una es opcional.
**Por qué importa:** son pistas de contexto real, no suposiciones. Si la empresa está contratando un "ERP Administrator", eso es una pista mucho más fuerte que "tiene 40 empleados y está en el rubro correcto".
**Qué revisar:** ¿las categorías de vacantes que el sistema considera "relevantes" reflejan cómo Marketing/Ventas realmente reconoce una oportunidad? ¿hay temas de LinkedIn que deberíamos estar escaneando y no estamos?

### Etapa 1 — Puntaje de interés (0 a 10)
**Qué pasa:** el sistema junta todas las pistas disponibles (vacantes, tecnología que usan, quejas públicas, eventos de crecimiento) y les pone un puntaje del 0 al 10 de "qué tan probable es que esta empresa necesite lo que vendemos *ahora mismo*". No es un puntaje de "encaja con el ICP" — es un puntaje de **timing**.
**Herramienta:** `signal-builder` — es la que arma el puntaje final; toma el resultado de `job-search` (Etapa 0) como uno de sus insumos, además de escanear el sitio web del prospecto por su cuenta.
**Ejemplo:** una empresa que publicó una vacante para el rol que nuestro producto reemplaza saca 8-10. Una empresa que solo cumple los datos generales del ICP (tamaño, industria) pero no mostró ninguna señal de dolor activo, saca 1-2.
**Importante:** el catálogo de "qué cuenta como señal" se ajusta automáticamente según el ICP actual — por ejemplo, una ronda de financiamiento (funding) solo cuenta como señal si el ICP actual son empresas que se financian externamente. Como nuestro ICP actual son negocios operativos tradicionales, ese tipo de señal específica no aplica hoy — el sistema lo sabe y no la usa.
**Qué revisar:** ¿el puntaje que el sistema le pone a una empresa real coincide con lo que un vendedor experimentado diría con la misma información? Si no, la brecha está en qué cuenta como "señal fuerte" — este es un buen lugar para feedback concreto con ejemplos de cuentas reales.

### Etapa 2 — Personalización (qué datos usar del prospecto)
**Qué pasa:** antes de escribir el mensaje, el sistema decide qué dato específico del prospecto vale la pena mencionar (el nombre de una herramienta que usan, un cargo, un proceso manual que detectó) — y siempre define un "plan B" por si ese dato no está disponible para todos.
**Herramienta:** `creative-variable`.
**Regla dura:** si un dato personalizado no se puede justificar con un dolor real y documentado del comprador (de la tabla de personas del ICP), se rechaza — no se inventa una conexión personal forzada solo para sonar personalizado.
**Qué revisar:** ¿los datos que el sistema elige personalizar son los que realmente mueven la aguja en una conversación de venta, o son detalles superficiales ("vi que estudiaste en...") que a nadie le importan?

### Etapa 3 — Redacción del mensaje (email y/o LinkedIn, en paralelo)
**Herramientas:** `email-writer` (email) y `linkedin-dm` (LinkedIn) — corren en paralelo con los mismos insumos (señal, oferta, datos del prospecto); `linkedin-dm` se activa siempre que haya un perfil de LinkedIn, incluso si no hay email.
**Qué pasa:** el sistema escribe el mensaje siguiendo una estructura fija de 3 líneas: **Situación** (describe la realidad del prospecto, no nuestro producto), **Insight** (una observación que demuestra que entendemos el problema) y **Pregunta** (le pide al prospecto que confirme si acertamos — nunca pide una reunión directamente en el primer mensaje).
**Esto ahora se cruza con quién es la persona:** el mismo puntaje de señal ya no produce el mismo mensaje para todos los cargos — un CFO recibe una línea de Insight enfocada en costos/reportes, un CIO recibe una enfocada en deuda técnica/integraciones, un Gerente de Operaciones recibe una enfocada en sobrecarga administrativa. La tabla de dolores por persona sale directamente del ICP.
**Si hay caso de éxito real disponible**, el mensaje lo usa (nombre del cliente, métrica verificable) en vez de inventar una cifra — y si no hay uno para ese segmento todavía, usa el mensaje general de la Oferta en vez de fabricar un número. *(Hoy esta librería de casos de éxito por segmento está vacía — ver sección de limitaciones.)*
**Reglas de asunto de email:** 2 a 5 palabras, minúsculas, sin trucos de puntuación, nunca "Quick question".
**Canal:** si el prospecto tiene email, se escribe el email. Si tiene LinkedIn, se escribe el mensaje de LinkedIn **en paralelo**, siempre — es el único canal si no hay email disponible.
**Qué revisar:** leé 5-10 mensajes generados como si fueras el prospecto. ¿Suenan a una persona que entiende tu negocio, o a una plantilla con el nombre insertado? ¿El tono coincide con cómo la marca quiere sonar?

### Etapa 4 — Aprobación humana (obligatoria, sin excepción)
**Herramienta:** `attio-crm` (el CRM, Attio) — ahí queda guardada la nota con el borrador exacto y la fecha, y es donde se registra la autorización.
**Qué pasa:** nada se envía automáticamente. El sistema arma el borrador completo, lo guarda con fecha y contenido exacto en el CRM, y **le pregunta explícitamente a un operador**: "¿envío esto ahora?". Aprobar el contenido no es lo mismo que autorizar el envío — son dos pasos separados a propósito.
**Por qué importa para Marketing/Negocio:** este es el punto de control de marca. Cualquier mensaje que salga con el logo/nombre de la empresa pasó por revisión humana antes de salir — no hay forma de que el sistema mande algo sin que alguien lo haya visto primero.

### Etapa 5 — Envío y ritmo de seguimiento
**Herramientas:** `linkedin-dm` junto con `Unipile` (el servicio que efectivamente manda el mensaje/invitación de LinkedIn) para el envío en sí; `attio-crm` para registrar el envío, mover la etapa del pipeline, y llevar el contador compartido de contactos. El envío de email pasa por `email-writer` + `attio-crm` de la misma forma.
**Qué pasa:** una vez autorizado, el mensaje se manda (por LinkedIn se decide automáticamente si es un mensaje directo o una invitación de conexión, según si ya estás conectado con esa persona). El **ritmo de los siguientes contactos no es el mismo para todos** — depende de qué tan fuerte era la señal original:
- Señal fuerte (8-10): hasta 5 contactos de email a lo largo de ~3 semanas.
- Señal media (3-7): el ritmo estándar — 3 emails + 1 seguimiento de LinkedIn.
- Señal débil (1-2): el mínimo — no se insiste más allá de un par de intentos.
**Además**, email y LinkedIn comparten un mismo contador de "cuántas veces le escribimos" — no se cuenta por separado, para que un prospecto no reciba, sin querer, el doble de volumen solo por tener dos canales activos.
**Por qué importa:** esto es una decisión de diseño deliberada — el sistema **no** manda la misma cantidad de mensajes a todo el mundo aunque eso sea técnicamente posible, para no quemar la reputación de envío ni cansar a prospectos de baja probabilidad.
**Qué revisar:** ¿el ritmo actual (topes de contactos y semanas) coincide con lo que Marketing/Ventas considera razonable para nuestra categoría de producto y ciclo de venta? Este es un número que se puede ajustar con feedback de negocio.

### Etapa 6 — Cuando el prospecto contesta
**Herramienta:** `reply-handler` — clasifica y redacta la respuesta sugerida; se apoya en `attio-crm` para actualizar el estado y crear tareas de seguimiento.
**Qué pasa:** el sistema lee la respuesta y la clasifica en una de seis categorías (Interesado, Objeción, Ahora no, No interesado, Pregunta, Fuera de oficina), redacta una respuesta sugerida con un límite de palabras por categoría, y actualiza el estado en el CRM. Si detecta una cuenta grande, una pregunta que requiere precio/alcance confidencial, baja confianza en la clasificación, o que mencionan a un competidor por nombre, **avisa a un humano** en vez de responder solo.
**Qué revisar:** las categorías y los umbrales de escalamiento a humano — ¿capturan los casos donde Marketing/Ventas realmente quiere estar en el loop?

---

## 4. Reglas de oro que protegen la marca

Estas son decisiones de diseño explícitas, no casualidad — vale la pena que Marketing las conozca porque son la base de "por qué confiar en que esto no va a hacer algo vergonzoso":

1. **Nunca inventa un caso de éxito, una métrica o un dato personal.** Si no hay una fuente real, usa un mensaje genérico en vez de fabricar algo específico.
2. **Nada se envía sin aprobación humana explícita**, en cada mensaje, en cada canal.
3. **El volumen de contacto se ajusta a qué tan justificado está**, no se manda el máximo posible a todo el mundo.
4. **Toda decisión de personalización tiene que poder explicarse** apuntando a un dolor real documentado del tipo de comprador — si no, se descarta.

---

## 5. Glosario rápido

| Término | Qué significa en este sistema |
|---|---|
| **ICP** | El perfil de cliente ideal — a quién le vendemos y por qué. |
| **Señal** | Una pista concreta (vacante, tecnología usada, queja pública, evento de crecimiento) de que un prospecto podría necesitar lo que vendemos ahora. |
| **Puntaje de señal (0-10)** | Qué tan fuerte es esa pista — no es "encaja con el ICP", es "el momento es ahora". |
| **Persona** | El tipo de comprador (Founder/CEO, CFO, CIO, etc.) — cada uno tiene dolores y beneficios distintos que el mensaje debe reflejar. |
| **Cadencia** | El ritmo y cantidad de contactos de seguimiento — ahora varía según qué tan fuerte era la señal. |
| **Segment story / caso de éxito** | Una historia real y verificable de un cliente en el mismo rubro, usada como prueba en el mensaje en vez de una afirmación genérica. |
| **Gate de envío** | El paso obligatorio de aprobación humana antes de que cualquier mensaje salga. |

---

## 6. Qué NO hace todavía (limitaciones conocidas)

Sé honesto con estos huecos al evaluar el sistema — son gaps identificados y documentados, no sorpresas:

- **No hay alertas en tiempo real.** El sistema no vigila cuentas por su cuenta ni avisa apenas aparece una señal nueva — hoy alguien tiene que correr el análisis manualmente. (Hay una automatización planeada para esto, todavía no construida.)
- **No prioriza contactos dentro de una misma cuenta por antigüedad o trayectoria.** Sabe qué *cargo* priorizar (según la tabla de personas), pero no sabe, por ejemplo, si una persona lleva 2 meses o 5 años en el puesto — porque hoy no tenemos esa información disponible de forma confiable.
- **La librería de casos de éxito por segmento está vacía todavía.** Existe la estructura para guardar historias reales de clientes por rubro, pero no se cargó ningún caso real todavía — hasta que eso pase, el sistema usa el mensaje general de la Oferta en vez de un caso específico.

---

## 7. Cómo dar feedback (checklist)

La forma más útil de dar feedback no es "esto está mal" — es señalar el punto exacto del recorrido y por qué. Usá esta checklist:

- [ ] **ICP y Oferta (sección 2):** ¿siguen reflejando el negocio real hoy? ¿falta algún segmento, cambió el posicionamiento?
- [ ] **Puntaje de señal (Etapa 1):** tomá 3 cuentas reales — ¿el puntaje que les pondría un vendedor coincide con el del sistema?
- [ ] **Personalización (Etapa 2):** ¿los datos elegidos son relevantes o superficiales?
- [ ] **Tono y estructura del mensaje (Etapa 3):** leé mensajes reales generados — ¿suenan a la marca?
- [ ] **Ritmo de seguimiento (Etapa 5):** ¿el número de contactos y el tiempo entre ellos es razonable para nuestro ciclo de venta?
- [ ] **Casos de éxito (Etapa 3 y sección 6):** ¿qué clientes cerrados deberían cargarse ya en la librería de casos por segmento?
- [ ] **Manejo de respuestas (Etapa 6):** ¿las categorías y los momentos de escalamiento a un humano son los correctos para nuestro proceso de ventas?

---

## 8. Tabla resumen — herramienta por etapa

| Etapa | Herramienta(s) |
|---|---|
| Setup (ICP + Oferta) | `gtm-context` |
| 0. Investigación (opcional) | `job-search` (vacantes) + `prospect-posts` (LinkedIn) |
| 1. Puntaje de interés | `signal-builder` (usa el resultado de `job-search`) |
| 2. Personalización | `creative-variable` |
| 3. Redacción del mensaje | `email-writer` + `linkedin-dm` (en paralelo) |
| 4. Aprobación humana | `attio-crm` (registro y gate de envío) |
| 5. Envío y cadencia | `linkedin-dm` + `Unipile` (envío LinkedIn), `email-writer` (envío email), `attio-crm` (registro y contador) |
| 6. Respuestas | `reply-handler` + `attio-crm` |

---

## 9. Dónde mirar más

- **Diagrama visual del flujo completo (técnico):** `Documents/Arquitecture_Diagram.md`
- **Análisis detallado de qué se implementó y por qué, punto por punto:** `Documents/Decisions/Outbound_Playbook_Alignment.md`
- **Definición completa del ICP y las personas:** `context/icp.md`
- **Definición completa de la Oferta:** `context/offer.md`
- **Librería de casos de éxito por segmento (hoy vacía):** `context/playbooks/segment-stories.md`
