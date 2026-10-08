"""Publisher: Instagram Graph API (imagen única y carrusel). Reels requieren video_url; ver README."""
import time

import requests

from . import config
from .store import Store


class PublishError(Exception):
    pass


def _api(path: str, **params) -> dict:
    r = requests.post(
        f"https://graph.facebook.com/{config.GRAPH_VERSION}/{path}",
        data={**params, "access_token": config.IG_ACCESS_TOKEN},
        timeout=60,
    )
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise PublishError(data.get("error", data))
    return data


def build_caption(copy: dict) -> str:
    tags = " ".join(copy.get("hashtags", []))
    return f"{copy.get('caption', '').strip()}\n\n{tags}".strip()


def publish(post: dict, log=print) -> str:
    caption = build_caption(post["payload"]["copy"])
    urls = post["payload"].get("image_urls", [])
    if not urls:
        raise PublishError("El post no tiene image_urls")
    if len(caption) > 2200:
        raise PublishError("Caption excede 2200 caracteres")

    if config.DRY_RUN:
        log(f"[DRY_RUN] publicaría {len(urls)} imagen(es):\n{caption}")
        return "dry-run"
    if not (config.IG_USER_ID and config.IG_ACCESS_TOKEN):
        raise PublishError("Faltan IG_USER_ID / IG_ACCESS_TOKEN")

    uid = config.IG_USER_ID
    if len(urls) == 1:
        creation = _api(f"{uid}/media", image_url=urls[0], caption=caption)["id"]
    else:
        children = [_api(f"{uid}/media", image_url=u, is_carousel_item="true")["id"] for u in urls[:10]]
        creation = _api(f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    time.sleep(5)  # el contenedor tarda en procesarse
    return _api(f"{uid}/media_publish", creation_id=creation)["id"]


def publish_due(store: Store, log=print) -> int:
    done = 0
    for post in store.due():
        if store.published_today() >= config.MAX_POSTS_PER_DAY:
            log("[publisher] tope diario alcanzado")
            break
        try:
            if not config.DRY_RUN:
                # Si el proceso muere a mitad de publicación, queda en "publishing" para revisión manual
                # en vez de reintentarse y duplicar el post en Instagram.
                store.set_status(post["id"], "publishing")
            media_id = publish(post, log)
            if media_id != "dry-run":
                store.set_status(post["id"], "published")
                done += 1
        except Exception as e:  # noqa: BLE001 - queremos registrar cualquier fallo y seguir
            store.set_status(post["id"], "failed", str(e))
            log(f"[publisher] post {post['id']} falló: {e}")
    return done
