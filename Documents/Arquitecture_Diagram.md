Diagrama actualizado en la misma URL: https://claude.ai/code/artifact/31d0b78c-dd83-45ea-9fe0-096277a0c706

Cambios en el diagrama:

Agregado el flujo paralelo email-writer / linkedin-dm (bloque par), dependiendo de si el prospecto tiene email.
Nuevo participante Unipile, con la lógica de find-profile → DM directo (1er grado) o invitación con nota (no conectado).
Agregado el gate de aprobación: ambas skills crean una nota Campaign Drafted en Attio y requieren autorización explícita del operador antes de enviar — nada sale automáticamente.
Nota Campaign Sent + cambio de etapa del pipeline tras el envío confirmado.