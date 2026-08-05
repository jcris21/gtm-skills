 TheirStack extrae job postings, pero el punto no es solo "quién está contratando", sino qué implica esa contratación sobre el dolor del prospecto ahora mismo. Así se conecta con signal-builder:

1. theirstack.py → job-search skill
El CLI (utils/theirstack.py) es solo el cliente HTTP: search_jobs() pega contra POST /v1/jobs/search con filtros (dominio, título, antigüedad, tamaño de empresa, etc.), y search --format json te da el output crudo. La skill job-search es la que interpreta ese resultado — agrupa por empresa y clasifica cada vacante en categorías (GTM/Sales, Técnico, Liderazgo) con un heurístico de fuerza de señal (job-search/skill.md:95-99):

8-10: 3+ roles GTM en 30 días, o contratación VP/Head de GTM
5-7: 1-2 roles GTM, o roles técnicos que sugieren push de product-market fit
1-4: solo backfill, sin roles GTM
0: nada relevante
2. job-search → signal-builder (el scoring real)
signal-builder es quien produce el score final 0-10 por prospecto, y la contratación es solo uno de los tipos de señal que considera (signal-types.md). Ahí hay tres sub-patrones de señal de hiring, cada uno con distinta fuerza:

Patrón	Qué implica	Score
Rol que tu producto reemplaza/aumenta (ej. contratan un "Data Analyst" y tú vendes analytics automation)	Sienten el dolor tanto que le están tirando headcount — si tu producto cuesta menos que el salario, el caso de ROI se escribe solo	8-10
Hiring en función adyacente (crece el equipo que tu producto sirve, pero no el rol exacto)	Más gente = más coordinación = más necesidad de tooling	5-7
Leadership hire en la función relevante (nuevo VP/Director)	Los nuevos líderes auditan sistemas en sus primeros 90 días — están evaluando herramientas activamente	7-9
3. El filtro clave — no es señal sin tu oferta
signal-builder/skill.md:24: "A hiring signal is noise unless your offer solves a problem that hiring indicates." Antes de puntuar nada, signal-builder lee context/offer.md para saber qué vendés — el mismo dato de TheirStack (ej. "contratando SDR") es un 9/10 si vendés herramientas de sales enablement, pero es irrelevante si vendés DevOps tooling.

4. Output final
signal-builder combina la señal de hiring con las demás (web scan, prospect-posts, firmográficos) y produce el bloque ### Signal N: [Nombre] (Score: X/10) con "qué se detectó" + "qué situación implica" — eso es lo que email-writer/linkedin-dm usan para elegir el patrón (Pain-led si score 7+) y escribir la línea de Situación.

En resumen: theirstack.py extrae, job-search categoriza y le pone un score preliminar de volumen/tipo de rol, signal-builder es quien decide el score final ponderándolo contra tu oferta y combinándolo con otras señales.