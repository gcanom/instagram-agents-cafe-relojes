import json
import os
import re
import subprocess
import tempfile

from . import config


class BaseLLM:
    """Interfaz común. Se inyecta en el pipeline para poder testear sin red."""

    def complete(self, system: str, user: str, max_tokens: int = 3000) -> str:
        raise NotImplementedError

    def json(self, system: str, user: str, max_tokens: int = 3000) -> dict:
        prompt = system + "\n\nResponde ÚNICAMENTE con un objeto JSON válido."
        last = None
        for _ in range(2):  # un reintento si el modelo devuelve algo no parseable
            try:
                return parse_json(self.complete(prompt, user, max_tokens))
            except (json.JSONDecodeError, ValueError) as e:
                last = e
        raise ValueError(f"Respuesta no es JSON válido tras 2 intentos: {last}")


class LLM(BaseLLM):
    """Backend API: SDK de Anthropic con ANTHROPIC_API_KEY."""

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


class ClaudeCLI(BaseLLM):
    """Backend CLI: `claude -p` en modo no interactivo, sin API key.

    Usa la autenticación de la propia CLI (`claude login` o la sesión del entorno). Sin herramientas,
    sin persistencia de sesión y desde un directorio vacío para que no cargue CLAUDE.md ni hooks del repo.
    """

    def __init__(self, timeout: int = 240):
        self.timeout = timeout

    def complete(self, system: str, user: str, max_tokens: int = 3000) -> str:
        cmd = [
            os.getenv("CLAUDE_BIN", "claude"), "-p", "--tools", "", "--no-session-persistence",
            "--output-format", "json", "--model", config.MODEL, "--system-prompt", system,
        ]
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=self.timeout, cwd=cwd)
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"claude -p falló (código {proc.returncode}): {(proc.stderr or proc.stdout)[:300]}")
        if proc.returncode != 0 or out.get("is_error"):
            raise RuntimeError(f"claude -p devolvió error: {str(out.get('result'))[:300]}")
        return out["result"]


def make_llm() -> BaseLLM:
    backend = config.LLM_BACKEND
    if backend == "auto":
        backend = "api" if os.getenv("ANTHROPIC_API_KEY") else "cli"
    return LLM() if backend == "api" else ClaudeCLI()


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
