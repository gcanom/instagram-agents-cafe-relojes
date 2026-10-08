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
