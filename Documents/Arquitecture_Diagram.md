# Pipeline de Outreach — Secuencia de Skills

```mermaid
sequenceDiagram
    actor U as Operador GTM
    participant GC as gtm-context
    participant PP as prospect-posts
    participant JS as job-search
    participant SB as signal-builder
    participant CV as creative-variable
    participant EW as email-writer
    participant LD as linkedin-dm
    participant AT as attio-crm
    participant UP as Unipile
    participant RH as reply-handler

    Note over U,GC: Setup (una sola vez por workspace)
    U->>GC: /gtm-context
    GC-->>U: context/offer.md + context/icp.md

    Note over U,PP: Investigación de prospectos (opcional)
    U->>PP: URL(s) de LinkedIn + tema
    PP-->>U: Reporte de menciones/señales sociales

    Note over U,JS: Señal de hiring (opcional)
    U->>JS: Dominios/nombres de empresas
    JS-->>U: Roles publicados, puntuados 0-10 en la misma escala que signal-builder

    Note over U,SB: Análisis de señales
    U->>SB: URL del prospecto (+ score de JS si se corrió)
    SB->>GC: lee context/offer.md (pains, señales) + context/icp.md (Growth Signal, Company Size, Industria)
    Note right of SB: context/icp.md decide qué categorías de signal-types.md aplican
    Note right of SB: ej. "funding" solo puntúa si el Growth Signal del ICP es financiamiento externo
    SB-->>U: Análisis de señales (0-10, misma escala que JS) + registro Person/Company en Attio

    Note over U,CV: Personalización
    U->>CV: Ángulo de campaña + perfil del prospecto
    Note right of CV: Variable "novel" requiere nombrar un pain point real de context/icp.md
    CV-->>U: Spec de variables (fuentes, prompts, fallbacks)

    Note over U,LD: Generación de copy — canales en paralelo
    par ¿Prospecto tiene email?
        U->>EW: Señales (SB) + oferta (GC) + variables (CV) + prospecto
        EW->>GC: lee context/icp.md para matchear el role del prospecto con una persona
        Note right of EW: Score de señal define la estructura, persona define el framing del Insight
        Note right of EW: Value-led toma la prueba de context/playbooks/segment-stories.md
        EW-->>U: Campaña de email (Situation, Insight, Inquisition)
        Note right of EW: Cadencia por tier — 8-10 = 5 touches en 3 semanas, 3-7 = 3 touches, 1-2 = mínimo
    and Siempre que haya LinkedIn (único canal si no hay email)
        U->>LD: Mismos inputs que email-writer + URL LinkedIn
        LD->>GC: lee context/icp.md, mismo matching de persona que email-writer
        LD-->>U: Nota de conexión o DM, mismos principios, más corto
        Note right of LD: Cadencia tiered igual que email, con topes más bajos por canal
    end

    Note over EW,AT: Gate de envío — obligatorio antes de enviar
    EW->>AT: chequea combined_touch_count contra el tope del tier de score
    LD->>AT: chequea combined_touch_count contra el tope del tier de score
    EW->>AT: create-note "Campaign Drafted — [fecha]" (copy completo)
    LD->>AT: create-note "Campaign Drafted — [fecha]" (copy completo)
    AT-->>U: URL de la nota en Attio
    U->>U: Autorización explícita: "¿Envío esto ahora?"

    Note over LD,UP: Envío vía Unipile (solo tras autorización)
    LD->>UP: find-profile (resuelve provider id + network_distance)
    alt 1er grado (FIRST_DEGREE)
        LD->>UP: send-dm (texto verbatim de la nota de Attio)
    else No conectado (2do/3er grado)
        LD->>UP: invite (nota de conexión ≤300 caracteres)
    end
    UP-->>LD: Confirmación de envío
    LD->>AT: create-note "Campaign Sent — [fecha]" + mover stage a "Outreach Sent" + incrementar combined_touch_count

    Note over U,AT: Registro en CRM (email)
    EW->>AT: (tras autorización) envío + create-note "Campaign Sent" + incrementar combined_touch_count

    Note over U,RH: Ciclo de respuesta
    U->>RH: Respuesta entrante (email o LinkedIn DM)
    RH->>RH: Clasifica intención + genera respuesta
    RH->>AT: Actualiza estado de la respuesta
    alt Interesado
        RH->>AT: Crea tarea de follow-up
    end
    RH-->>U: Respuesta lista + clasificación
```

## Notas del flujo

- **`job-search`** (nuevo en el diagrama) corre opcionalmente antes de `signal-builder` y puntúa hiring signals 0-10 en la **misma escala** que `signal-builder` — ya no hay dos escalas de intent sin reconciliar (High/Medium/Low vs. 1-10).
- **`signal-builder`** ahora carga `context/icp.md` además de `context/offer.md`: el Growth Signal, Company Size e Industria del ICP deciden qué categorías del catálogo genérico `reference/signal-types.md` aplican. El catálogo quedó ICP-agnóstico — no tiene hardcodeado si "funding" aplica o no, lo decide `context/icp.md` en cada corrida.
- **`email-writer`** y **`linkedin-dm`** ahora resuelven el patrón de copy con una **matriz 2D**: el score de señal define la estructura (Pain-led / Value-led / Segment fallback), y la persona matcheada contra `context/icp.md` (por el campo `role` del prospecto) define cómo se enmarca la línea Insight — antes solo se usaba el score.
- **Value-led** en ambas skills busca la prueba/caso de uso en `context/playbooks/segment-stories.md` (nuevo archivo) antes de inventar una métrica; si no hay entrada para ese segmento, cae al value prop general de `offer.md`.
- **Cadencia de follow-up** ahora es tiered por score en vez de fija: score 8-10 llega a 5 touches de email en ~3 semanas, 3-7 se queda en el ritmo original (3 email + 1 LinkedIn), 1-2 se queda en el mínimo — evita mandar el mismo volumen a un prospecto de señal débil.
- **`combined_touch_count`** (nuevo campo en Attio) es un contador compartido entre `email-writer` y `linkedin-dm`: el gate de envío de ambas skills lo chequea contra el tope del tier antes de mandar, así el total de touches cross-channel respeta la cadencia tiered, no solo el conteo por canal.
- **`creative-variable`**: una variable "novel" ya no se acepta solo con "justificación" genérica — tiene que nombrar un pain point real de la tabla de personas en `context/icp.md`, si no, se rechaza de vuelta a uno de los 4 arquetipos estándar.
- **`context/icp.md`** ahora también trae una tabla de **Contact Orchestration** (cuántos contactos perseguir por tamaño de cuenta y en qué dirección — top-down dado el ranking de personas ya existente).
- El gate de aprobación original se mantiene igual: ninguna copia se manda sin nota `Campaign Drafted` en Attio y autorización explícita del operador. Tras el envío, nota `Campaign Sent` + cambio de etapa del pipeline, ahora sumado al incremento de `combined_touch_count`.

---

Diagrama actualizado en la misma URL: https://claude.ai/code/artifact/31d0b78c-dd83-45ea-9fe0-096277a0c706

Cambios en el diagrama (2026-08-05) — implementación de los puntos 1, 3, 4, 6, 7, 8, 9 y 10 de `Documents/Decisions/Outbound_Playbook_Alignment.md`:

Nuevo participante job-search, corriendo opcional antes de signal-builder y puntuando en la misma escala 0-10 (ya no hay dos escalas de intent sin reconciliar).
signal-builder ahora lee context/icp.md (Growth Signal, Company Size, Industria) además de offer.md, para decidir qué categorías de reference/signal-types.md aplican a la ICP actual — el catálogo quedó ICP-agnóstico.
email-writer y linkedin-dm ahora resuelven el patrón de copy con una matriz 2D: score de señal define la estructura, persona matcheada contra context/icp.md (por el role del prospecto) define el framing de la línea Insight.
Value-led en ambas skills busca la prueba en el nuevo context/playbooks/segment-stories.md antes de inventar una métrica.
Cadencia de follow-up tiered por score (8-10 = 5 touches/3 semanas, 3-7 = ritmo original, 1-2 = mínimo) en vez de fija.
Nuevo campo combined_touch_count en Attio, compartido entre email-writer y linkedin-dm — el gate de envío de ambas skills lo chequea contra el tope del tier antes de mandar.
creative-variable: variable "novel" ahora requiere que la justificación nombre un pain point real de la tabla de personas en context/icp.md.
context/icp.md suma una tabla de Contact Orchestration (contactos por tamaño de cuenta y dirección top-down/bottom-up).

Cambios previos en el diagrama:

Agregado el flujo paralelo email-writer / linkedin-dm (bloque par), dependiendo de si el prospecto tiene email.
Nuevo participante Unipile, con la lógica de find-profile → DM directo (1er grado) o invitación con nota (no conectado).
Agregado el gate de aprobación: ambas skills crean una nota Campaign Drafted en Attio y requieren autorización explícita del operador antes de enviar — nada sale automáticamente.
Nota Campaign Sent + cambio de etapa del pipeline tras el envío confirmado.