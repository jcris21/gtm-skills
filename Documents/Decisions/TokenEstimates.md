# Token Estimates — Pipeline Prospects

Estimacion por proximidad de mencion en las transcripciones locales de Claude Code (ver `session_token_estimator.py`). Incluye solo prospectos que pasaron por una ejecucion real del pipeline (excluye filas de ejemplo sintetico y plantilla vacia de `Outbound_Pipeline_Tracker.md`). No es un ledger exacto — ver nota al pie de cada script/decision relacionada.

| Prospecto | Mentions | Input Tokens | Output Tokens | Cache Write 1h | Cache Write 5m | Cache Read | Costo Estimado (USD) |
|---|---|---|---|---|---|---|---|
| TEST — chriscob LinkedIn (Pipeline Dry Run) | 8 | 34 | 5,409 | 85,331 | 0 | 401,162 | $0.2803 |
| Christian Cobian G. (LinkedIn) | 4 | 6 | 3,548 | 4,126 | 0 | 530,351 | $0.1581 |
| TEST — Raymond Bailey (Pipeline Dry Run) | 0 | 0 | 0 | 0 | 0 | 0 | $0.0000 |
| TEST — Christopher Rosiak (Pipeline Dry Run) | 0 | 0 | 0 | 0 | 0 | 0 | $0.0000 |
| TEST — Dustin Cash (Pipeline Dry Run) | 0 | 0 | 0 | 0 | 0 | 0 | $0.0000 |
