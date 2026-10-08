# instagram-agents-cafe-relojes
Sistema multi-agente para automatización de contenidos de Instagram sobre café de especialidad y alta relojería. | Multi-agent system to automate content creation and scheduling for an Instagram account focused on specialty coffee and horology..
# Instagram Agent Swarm: Specialty Coffee & Horology

Sistema automatizado basado en un enjambre de agentes de IA para la investigación, redacción, generación de multimedia y publicación de contenido temático en Instagram.

## 🎯 Nicho y Enfoque
- **Café de especialidad:** Métodos de extracción (V60, Chemex, etc.), orígenes, notas de cata y cultura cafetera.
- **Relojería:** Historia horológica, calibres, micro-reseñas y análisis técnico/estético de piezas de colección.

## 🤖 Arquitectura del Enjambre
1. **Researcher Agent:** Curaduría de noticias, especificaciones técnicas y tendencias.
2. **Copywriter Agent:** Redacción de carruseles, micro-ensayos y guiones para Reels/posts.
3. **Visual Agent:** Generación de prompts multimedia y maquetación de assets.
4. **Editor/Reviewer Agent:** Control de calidad y consistencia técnica.
5. **Publisher Agent:** Integración con Instagram Graph API para programación y publicación.

## 🛠️ Stack Tecnológico
- **Orquestación:** CrewAI / LangGraph / Python
- **Automatización:** Webhooks / n8n / Make
- **Publicación:** Instagram Graph API

---

## 🚀 Uso rápido

```bash
pip install -r requirements.txt
cp .env.example .env   # pon ANTHROPIC_API_KEY; el resto puede esperar
export $(grep -v '^#' .env | xargs)

python -m swarm.cli generate --topic "Por qué el V60 se parece a un escape de ancla"
python -m swarm.cli list
python -m swarm.cli show 1
python -m swarm.cli images 1 https://tu-cdn/s1.jpg https://tu-cdn/s2.jpg   # URLs públicas
python -m swarm.cli approve 1 --at 2026-10-09T14:00:00+00:00
python -m swarm.cli publish          # con DRY_RUN=true solo simula
python -m unittest discover -s tests
```

## 🧠 Motor de lenguaje (con o sin API key)

`LLM_BACKEND=auto` usa el SDK si existe `ANTHROPIC_API_KEY`; si no, llama a `claude -p` (Claude Code en modo no interactivo, sin herramientas ni persistencia, desde un directorio vacío). Requiere la CLI instalada y autenticada (`claude login`) en la máquina que corra el ciclo, y consume los límites de tu plan. Revisa que tu plan permita uso automatizado antes de depender de esto.

Ciclo automático (cron): `python -m swarm.cli run` genera un post si hay menos de 3 en espera y publica los aprobados que ya tocan.

## 🔄 Flujo

`Strategist → Researcher → Copywriter ⇄ Reviewer (máx. 2 revisiones) → Visual → cola SQLite → (tú apruebas) → Publisher`

- Notas propias en `sources/*.md`: el Researcher solo usa eso + conocimiento canónico. Datos de confianza "baja" se descartan antes del copy.
- **Seguridad por defecto:** `DRY_RUN=true` y `REQUIRE_APPROVAL=true`. Nada se publica de verdad hasta que lo cambies.
- Tope diario `MAX_POSTS_PER_DAY`.

## ⚠️ Pendientes / límites reales

1. **Imágenes:** FLUX (Black Forest Labs, `BFL_API_KEY`) genera las imágenes en 4:5. Instagram exige URL pública, así que con `IMAGE_STORAGE=cloudinary` se suben solas; con `local` quedan en `data/images/` y debes alojarlas tú (`swarm images`). `swarm render ID` regenera las de un post existente. Requiere que el entorno permita salida a `api.bfl.ai`.
2. **Reels:** no implementado (requiere `video_url` y `media_type=REELS`).
3. **Cuenta:** debe ser Business/Creator vinculada a página de Facebook; app de Meta con permiso `instagram_content_publish`. El token long-lived dura ~60 días y hay que renovarlo.
4. **Scheduler:** correr `generate` y `publish` por cron/systemd/GitHub Actions. La cola SQLite necesita disco persistente (en Actions, no persiste).
5. **Alucinaciones en datos de relojes:** el Reviewer ayuda, pero un humano debería revisar cualquier cifra técnica antes de aprobar.
6. Instagram penaliza/limita automatización agresiva: mantén frecuencia baja y contenido con valor real.
