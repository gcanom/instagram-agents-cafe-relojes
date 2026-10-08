"""Generación (FLUX vía Black Forest Labs) y alojamiento de imágenes."""
import hashlib
import time
from pathlib import Path

import requests

from . import config


class ImageError(Exception):
    pass


class BFLProvider:
    """API asíncrona de BFL: POST -> polling_url -> GET hasta status=Ready -> descarga el sample."""

    def __init__(self, key: str | None = None, model: str | None = None):
        self.key = key or config.BFL_API_KEY
        self.model = model or config.BFL_MODEL
        if not self.key:
            raise ImageError("Falta BFL_API_KEY")

    @property
    def headers(self) -> dict:
        return {"x-key": self.key, "accept": "application/json"}

    def generate(self, prompt: str, width: int | None = None, height: int | None = None, timeout: int = 180) -> bytes:
        r = requests.post(
            f"{config.BFL_BASE}/{self.model}",
            headers=self.headers,
            json={"prompt": prompt, "width": width or config.IMAGE_WIDTH, "height": height or config.IMAGE_HEIGHT},
            timeout=60,
        )
        if r.status_code >= 400:
            raise ImageError(f"BFL {r.status_code}: {r.text[:300]}")
        job = r.json()
        poll_url = job.get("polling_url") or f"{config.BFL_BASE}/get_result?id={job['id']}"

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(1.5)
            s = requests.get(poll_url, headers=self.headers, timeout=60).json()
            status = s.get("status")
            if status == "Ready":
                img = requests.get(s["result"]["sample"], timeout=120)
                img.raise_for_status()
                return img.content
            if status not in ("Pending", "Queued", "Processing", "Task not found"):
                raise ImageError(f"BFL terminó con estado {status}: {s}")
        raise ImageError("BFL: timeout esperando la imagen")


class LocalStorage:
    """Guarda en disco. No produce URL pública: sirve para revisar o subir a mano."""

    def upload(self, data: bytes, name: str) -> str | None:
        path = Path("data/images") / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return None


class CloudinaryStorage:
    def upload(self, data: bytes, name: str) -> str:
        if not (config.CLOUDINARY_CLOUD_NAME and config.CLOUDINARY_API_KEY and config.CLOUDINARY_API_SECRET):
            raise ImageError("Faltan credenciales de Cloudinary")
        params = {"folder": "swarm", "public_id": name, "timestamp": str(int(time.time()))}
        to_sign = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + config.CLOUDINARY_API_SECRET
        signature = hashlib.sha1(to_sign.encode()).hexdigest()
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{config.CLOUDINARY_CLOUD_NAME}/image/upload",
            data={**params, "api_key": config.CLOUDINARY_API_KEY, "signature": signature},
            files={"file": (f"{name}.png", data)},
            timeout=120,
        )
        body = r.json()
        if r.status_code >= 400 or "secure_url" not in body:
            raise ImageError(f"Cloudinary: {body}")
        return body["secure_url"]


def make_storage():
    return CloudinaryStorage() if config.IMAGE_STORAGE == "cloudinary" else LocalStorage()


def render_images(visual: dict, provider, storage, tag: str, log=print) -> list[str]:
    """Genera cada imagen del Visual Agent y devuelve las URLs públicas (vacía si el storage no publica)."""
    style = visual.get("style_guide", "")
    items = visual.get("images", [])[: config.MAX_IMAGES_PER_POST]
    urls: list[str] = []
    for n, item in enumerate(items, 1):
        prompt = f"{item['prompt']}. {style}. No text, no logos, no watermark."
        data = provider.generate(prompt)
        url = storage.upload(data, f"{tag}-{n}")
        log(f"[images] {n}/{len(items)} -> {url or 'guardada en data/images (sin URL pública)'}")
        if url:
            urls.append(url)
    return urls if len(urls) == len(items) else []
