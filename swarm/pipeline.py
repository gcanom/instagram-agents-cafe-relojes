"""Orquestador: Strategist → Researcher → Copywriter ⇄ Reviewer → Visual → cola."""
from pathlib import Path

from . import config
from .agents import COPYWRITER, RESEARCHER, REVIEWER, STRATEGIST, VISUAL
from .llm import LLM
from .store import Store


def load_sources(folder: str = "sources") -> str:
    p = Path(folder)
    if not p.exists():
        return ""
    return "\n\n".join(f"## {f.name}\n{f.read_text()}" for f in sorted(p.glob("*.md")))


def generate_post(llm: LLM, store: Store, topic: str | None = None, log=print) -> int:
    plan = STRATEGIST.run(llm, {"user_topic": topic, "recent_topics": store.recent_topics()})
    log(f"[strategist] {plan.get('format')} · {plan.get('topic')}")

    research = RESEARCHER.run(llm, {"plan": plan, "sources": load_sources()})
    usable = [f for f in research.get("facts", []) if f.get("confidence") in ("alta", "media")]
    log(f"[researcher] {len(usable)}/{len(research.get('facts', []))} hechos utilizables")

    copy, review, feedback = {}, {}, None
    for attempt in range(config.MAX_REVISIONS + 1):
        copy = COPYWRITER.run(llm, {"plan": plan, "facts": usable, "review_feedback": feedback})
        review = REVIEWER.run(llm, {"plan": plan, "facts": usable, "post": copy})
        log(f"[reviewer] intento {attempt + 1}: aprobado={review.get('approved')} score={review.get('score')}")
        if review.get("approved"):
            break
        feedback = review.get("issues")

    payload = {"plan": plan, "research": research, "copy": copy, "review": review, "image_urls": []}
    if not review.get("approved"):
        post_id = store.add("rejected", payload)
        store.set_status(post_id, "rejected", "; ".join(review.get("issues", [])))
        log(f"[pipeline] post {post_id} rechazado tras {config.MAX_REVISIONS} revisiones")
        return post_id

    payload["visual"] = VISUAL.run(llm, {"plan": plan, "copy": copy})
    # Sin URLs públicas de imagen no se puede publicar: Graph API exige image_url accesible.
    post_id = store.add("needs_assets", payload)
    log(f"[pipeline] post {post_id} listo; faltan imágenes (ver payload.visual)")
    return post_id


def attach_images(store: Store, post_id: int, urls: list[str]):
    """Registra URLs públicas de imágenes y pasa el post a aprobación (o aprobado)."""
    post = store.get(post_id)
    payload = post["payload"]
    payload["image_urls"] = urls
    store.update_payload(post_id, payload)
    store.set_status(post_id, "pending_approval" if config.REQUIRE_APPROVAL else "approved")
