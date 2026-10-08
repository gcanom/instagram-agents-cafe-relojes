import json
import re

from . import config


class LLM:
    """Envoltorio mínimo sobre el SDK de Anthropic. Se inyecta para poder testear sin red."""

    def __init__(self):
        from anthropic import Anthropic

        self.client = Anthropic()

    def complete(self, system: str, user: str, max_tokens: int = 3000) -> str:
        r = self.client.messages.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in r.content if b.type == "text")

    def json(self, system: str, user: str, max_tokens: int = 3000) -> dict:
        return parse_json(self.complete(system + "\n\nResponde ÚNICAMENTE con un objeto JSON válido.", user, max_tokens))


def parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)
