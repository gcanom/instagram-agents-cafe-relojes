## Protocolo de Seguridad y Escalado
El orquestador principal DEBE pausar la ejecución y consultar al Asesor (Opus) en estos 3 escenarios:
1. Antes de bloquear y comenzar a ejecutar un plan de implementación.
2. Inmediatamente después de fallar en la resolución del mismo error por segunda vez.
3. Antes de marcar el objetivo final de un ticket/tarea como "completado".
