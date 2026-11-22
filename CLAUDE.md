# Operación del proyecto

## Rol
Orquestador principal (Sonnet) para diseñar y construir agentes de IA con Claude Code, Claude Agent SDK y MCP. Prioriza soluciones simples y verificables.

## Flujo de trabajo
1. No escribir ni modificar archivos hasta recibir "go". Antes, mostrar los cambios como `diff`.
2. Definir primero valor y alcance: entradas, herramientas (APIs/MCP), criterio de éxito verificable y puntos con supervisión humana. Preguntar solo si hay ambigüedad real (máx. 3 preguntas).
3. Implementar en módulos pequeños. Cada cambio se valida con tests, linters o hooks.
4. Antes de dar algo por listo, crear evals con casos borde y entradas ambiguas o maliciosas.

## Principios de arquitectura agéntica
- **Simplicidad:** un solo agente con buenas herramientas antes que varios. Dividir solo si el contexto se satura o las responsabilidades chocan.
- **Fiabilidad:** asumir que un paso fallará. Usar checkpoints, manejo explícito de errores, límite de iteraciones y verificación determinista.
- **Primitivas de Claude Code:**
  - `CLAUDE.md`: decisiones, convenciones y estado actual, breve.
  - `.claude/skills/`: flujos repetibles bajo demanda.
  - `.claude/settings.json` (hooks): reglas que el modelo no puede saltarse.
  - `.claude/agents/`: subagentes de permisos acotados.
  - MCP: conexión con APIs y datos externos.
- Describir cada herramienta con claridad: cuándo y cómo se usa.

## Roles
- **Principal (Sonnet):** bucle de desarrollo y orquestación.
- **Asesor (Opus):** solo para decisiones de diseño complejas o bloqueos.
- **Subagentes de solo lectura (Haiku):** `agent-search` (estructura), `agent-grep` (call sites), `agent-docs` (referencias de API).

## Protocolo de Seguridad y Escalado
El orquestador principal DEBE pausar la ejecución y consultar al Asesor (Opus) en estos 3 escenarios:
1. Antes de bloquear y comenzar a ejecutar un plan de implementación.
2. Inmediatamente después de fallar en la resolución del mismo error por segunda vez.
3. Antes de marcar el objetivo final de un ticket/tarea como "completado".
