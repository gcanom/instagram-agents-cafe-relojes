import unittest
from unittest.mock import patch

from swarm import config, pipeline, publisher
from swarm.llm import parse_json
from swarm.store import Store


class FakeLLM:
    """Responde según el agente (detecta por el system prompt). El reviewer rechaza la 1ª vez."""

    def __init__(self):
        self.reviews = 0

    def json(self, system, user, max_tokens=0):
        if "estratega" in system:
            return {"pillar": "cruce", "format": "carrusel", "topic": "V60 y escape", "angle": "a", "why_now": "b"}
        if "investigador" in system:
            return {"facts": [{"claim": "ok", "confidence": "alta", "source": "s"}, {"claim": "dudoso", "confidence": "baja", "source": ""}], "gaps": []}
        if "copywriter" in system:
            return {"hook": "h", "slides": ["1", "2"], "reel_script": "", "caption": "cap", "hashtags": ["#cafe"], "alt_text": "x"}
        if "editor" in system:
            self.reviews += 1
            return {"approved": self.reviews > 1, "issues": ["dato sin respaldo"], "score": 7}
        return {"style_guide": "s", "images": [{"slide": 1, "prompt": "p", "overlay_text": "t"}]}


class PipelineTests(unittest.TestCase):
    def test_revision_loop_and_queue(self):
        store = Store(":memory:")
        pid = pipeline.generate_post(FakeLLM(), store, log=lambda *_: None)
        post = store.get(pid)
        self.assertEqual(post["status"], "needs_assets")
        self.assertEqual(len([f for f in post["payload"]["research"]["facts"]]), 2)

    def test_rejected_after_max_revisions(self):
        class AlwaysNo(FakeLLM):
            def json(self, system, user, max_tokens=0):
                r = super().json(system, user)
                if "editor" in system:
                    r["approved"] = False
                return r

        store = Store(":memory:")
        pid = pipeline.generate_post(AlwaysNo(), store, log=lambda *_: None)
        self.assertEqual(store.get(pid)["status"], "rejected")

    def test_dry_run_never_calls_network(self):
        store = Store(":memory:")
        pid = pipeline.generate_post(FakeLLM(), store, log=lambda *_: None)
        with patch.object(config, "REQUIRE_APPROVAL", True):
            pipeline.attach_images(store, pid, ["https://x/1.jpg"])
        self.assertEqual(store.get(pid)["status"], "pending_approval")
        store.set_status(pid, "approved")
        with patch.object(config, "DRY_RUN", True), patch("swarm.publisher.requests.post") as net:
            publisher.publish_due(store, log=lambda *_: None)
            net.assert_not_called()

    def test_parse_json_fenced(self):
        self.assertEqual(parse_json('texto\n```json\n{"a":1}\n```'), {"a": 1})


if __name__ == "__main__":
    unittest.main()


def _real_png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (256, 320), (90, 60, 40)).save(buf, "PNG")
    return buf.getvalue()


class ImageTests(unittest.TestCase):
    def test_pipeline_renders_and_queues_for_approval(self):
        class P:
            def generate(self, prompt, **_):
                return _real_png()

        class S:
            def upload(self, data, name):
                return f"https://cdn/{name}.png"

        store = Store(":memory:")
        with patch.object(config, "REQUIRE_APPROVAL", True):
            pid = pipeline.generate_post(FakeLLM(), store, log=lambda *_: None, image_provider=P(), storage=S())
        post = store.get(pid)
        self.assertEqual(post["status"], "pending_approval")
        self.assertEqual(post["payload"]["image_urls"], [f"https://cdn/post{pid}-1.png"])

    def test_local_storage_leaves_needs_assets(self):
        from swarm.images import render_images

        class P:
            def generate(self, prompt, **_):
                return _real_png()

        class S:
            def upload(self, data, name):
                return None

        self.assertEqual(render_images({"images": [{"prompt": "x"}]}, P(), S(), "t", log=lambda *_: None), [])

    def test_bfl_polling(self):
        from swarm.images import BFLProvider

        post = type("R", (), {"status_code": 200, "json": lambda s: {"id": "1", "polling_url": "http://poll"}})()
        pending = type("R", (), {"json": lambda s: {"status": "Pending"}})()
        ready = type("R", (), {"json": lambda s: {"status": "Ready", "result": {"sample": "http://img"}}})()
        img = type("R", (), {"content": b"IMG", "raise_for_status": lambda s: None})()
        gets = iter([pending, ready, img])
        with patch("swarm.images.requests.post", return_value=post), patch(
            "swarm.images.requests.get", side_effect=lambda *a, **k: next(gets)
        ), patch("swarm.images.time.sleep"):
            self.assertEqual(BFLProvider(key="k").generate("p"), b"IMG")


class ComposeTests(unittest.TestCase):
    def test_overlay_returns_jpeg_same_size(self):
        import io

        from PIL import Image

        from swarm.compose import overlay

        src = io.BytesIO()
        Image.new("RGB", (1024, 1280), (90, 60, 40)).save(src, "PNG")
        out = overlay(src.getvalue(), "Un texto largo de prueba para comprobar el ajuste de línea en la slide", 2, 6)
        self.assertEqual(out[:3], b"\xff\xd8\xff")
        self.assertEqual(Image.open(io.BytesIO(out)).size, (1024, 1280))
