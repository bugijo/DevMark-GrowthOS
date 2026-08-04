import json

import pytest

from growthos.services.ai_providers import (
    AIProviderError,
    OpenAICompatibleProvider,
    ProviderRequest,
)


class FakeResponse:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def request() -> ProviderRequest:
    return ProviderRequest(system="system", prompt="prompt", alternatives=1, max_tokens=200)


def test_ollama_contract_uses_native_response_and_reported_model(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payload = {
        "model": "qwen3:4b-instruct",
        "message": {"content": '{"alternatives":[{"title":"Resposta"}]}'},
        "prompt_eval_count": 10,
        "eval_count": 5,
    }
    monkeypatch.setattr(
        "growthos.services.ai_providers.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )
    provider = OpenAICompatibleProvider(
        name="hermes_ollama",
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b-instruct",
        timeout=1,
        attempts=1,
        native_ollama=True,
    )
    result = provider.generate(request())
    assert result.model == "qwen3:4b-instruct"
    assert result.input_tokens == 10
    assert result.alternatives[0]["title"] == "Resposta"


def test_provider_rejects_unstructured_response(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payload = {"choices": [{"message": {"content": "texto livre"}}]}
    monkeypatch.setattr(
        "growthos.services.ai_providers.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )
    provider = OpenAICompatibleProvider(
        name="openrouter",
        base_url="https://example.test/v1",
        model="free",
        timeout=1,
        attempts=1,
        api_key="test-only",
    )
    with pytest.raises(AIProviderError, match="INVALID_JSON"):
        provider.generate(request())
