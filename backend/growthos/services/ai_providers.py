from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    system: str
    prompt: str
    alternatives: int
    max_tokens: int


@dataclass(frozen=True, slots=True)
class ProviderResult:
    alternatives: list[dict[str, object]]
    provider: str
    model: str
    duration_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None = None


class AIProvider(Protocol):
    name: str

    def generate(self, request: ProviderRequest) -> ProviderResult: ...


def _extract_json(text: str) -> list[dict[str, object]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIProviderError("INVALID_JSON") from exc
    alternatives = value.get("alternatives") if isinstance(value, dict) else None
    if not isinstance(alternatives, list) or not alternatives:
        raise AIProviderError("INVALID_SCHEMA")
    normalized: list[dict[str, object]] = []
    for item in alternatives:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            raise AIProviderError("INVALID_SCHEMA")
        normalized.append(item)
    return normalized


class MockGrowthProvider:
    name = "mock"
    model = "growthos-mock-v1"

    def generate(self, request: ProviderRequest) -> ProviderResult:
        started = time.monotonic()
        alternatives = [
            {
                "title": f"Alternativa {position}: conteúdo alinhado à marca",
                "caption": "Conteúdo simulado para revisão humana, sem publicação automática.",
                "cta": "Converse com nossa equipe.",
                "script": "Apresente o tema, desenvolva o benefício e encerre com o CTA.",
                "visual_prompt": "Composição institucional coerente com o Brand Kit.",
                "strategy": "Educar, gerar confiança e conduzir para uma conversa.",
                "sensitive": False,
                "sensitivity_reason": "",
            }
            for position in range(1, request.alternatives + 1)
        ]
        return ProviderResult(
            alternatives=alternatives,
            provider=self.name,
            model=self.model,
            duration_ms=max(1, int((time.monotonic() - started) * 1000)),
            input_tokens=max(1, len(request.prompt) // 4),
            output_tokens=max(1, len(json.dumps(alternatives, ensure_ascii=False)) // 4),
        )


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        timeout: int,
        attempts: int,
        api_key: str | None = None,
        native_ollama: bool = False,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.attempts = attempts
        self.api_key = api_key
        self.native_ollama = native_ollama

    def generate(self, request: ProviderRequest) -> ProviderResult:
        started = time.monotonic()
        if self.native_ollama:
            url = f"{self.base_url}/api/chat"
            body = {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.prompt},
                ],
                "options": {"num_predict": request.max_tokens},
            }
        else:
            url = f"{self.base_url}/chat/completions"
            body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.prompt},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": request.max_tokens,
            }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last_code = "UNAVAILABLE"
        for _ in range(self.attempts):
            try:
                http_request = Request(
                    url,
                    data=json.dumps(body).encode(),
                    headers=headers,
                    method="POST",
                )
                with urlopen(http_request, timeout=self.timeout) as response:
                    payload = json.load(response)
                if self.native_ollama:
                    text = payload["message"]["content"]
                    input_tokens = int(payload.get("prompt_eval_count", 0))
                    output_tokens = int(payload.get("eval_count", 0))
                    answered_model = str(payload.get("model", self.model))
                else:
                    text = payload["choices"][0]["message"]["content"]
                    usage = payload.get("usage", {})
                    input_tokens = int(usage.get("prompt_tokens", 0))
                    output_tokens = int(usage.get("completion_tokens", 0))
                    answered_model = str(payload.get("model", self.model))
                return ProviderResult(
                    alternatives=_extract_json(text)[: request.alternatives],
                    provider=self.name,
                    model=answered_model,
                    duration_ms=max(1, int((time.monotonic() - started) * 1000)),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except HTTPError as exc:
                last_code = f"HTTP_{exc.code}"
                if exc.code < 500 and exc.code != 429:
                    break
            except (KeyError, TypeError, ValueError, URLError, TimeoutError, OSError):
                last_code = "UNAVAILABLE"
        raise AIProviderError(last_code)
