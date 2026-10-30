import json
from decimal import Decimal
from pathlib import Path
from urllib.error import URLError

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
        allow_test_transport=True,
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
        allow_test_transport=True,
    )
    with pytest.raises(AIProviderError, match="INVALID_JSON"):
        provider.generate(request())


def test_external_provider_construction_is_blocked_during_tests() -> None:
    with pytest.raises(AIProviderError, match="EXTERNAL_PROVIDER_DISABLED_IN_TEST"):
        OpenAICompatibleProvider(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            model="openrouter/free",
            timeout=1,
            attempts=1,
            api_key="must-not-be-used",
        )


@pytest.mark.parametrize(
    ("usage", "expected_cost", "expected_status", "expected_origin"),
    [
        ({"cost": "0.00012000"}, Decimal("0.00012000"), "CONFIRMED", "PROVIDER_USAGE_COST"),
        ({"cost": 0}, Decimal("0"), "CONFIRMED", "PROVIDER_USAGE_COST"),
        ({}, None, "UNKNOWN", None),
        ({"cost": None}, None, "UNKNOWN", None),
        ({"cost": "inválido"}, None, "UNKNOWN", "INVALID_PROVIDER_VALUE"),
        (
            {"estimated_cost": "0.0002"},
            Decimal("0.0002"),
            "ESTIMATED",
            "PROVIDER_USAGE_ESTIMATE",
        ),
    ],
)
def test_openrouter_cost_contract(
    monkeypatch: pytest.MonkeyPatch,
    usage: dict[str, object],
    expected_cost: Decimal | None,
    expected_status: str,
    expected_origin: str | None,
) -> None:
    payload = {
        "model": "provider/free-model:free",
        "choices": [{"message": {"content": '{"alternatives":[{"title":"Resposta"}]}'}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, **usage},
    }
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
        allow_test_transport=True,
    )
    result = provider.generate(request())
    assert result.cost_usd == expected_cost
    assert result.cost_status == expected_status
    assert result.cost_origin == expected_origin


def test_sanitized_openrouter_fixture_records_decimal_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "openrouter_chat_completion_cost.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
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
        allow_test_transport=True,
    )
    result = provider.generate(request())
    assert result.cost_usd == Decimal("0.00012000")
    assert result.cost_status == "CONFIRMED"
    assert result.model == "provider/free-model:free"


def test_retry_returns_provider_cost_only_from_successful_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    payload = {
        "model": "provider/free-model:free",
        "choices": [{"message": {"content": '{"alternatives":[{"title":"Resposta"}]}'}}],
        "usage": {"cost": "0.25"},
    }

    def flaky_transport(*args: object, **kwargs: object) -> FakeResponse:
        nonlocal calls
        del args, kwargs
        calls += 1
        if calls == 1:
            raise URLError("offline")
        return FakeResponse(payload)

    monkeypatch.setattr("growthos.services.ai_providers.urlopen", flaky_transport)
    provider = OpenAICompatibleProvider(
        name="openrouter",
        base_url="https://example.test/v1",
        model="free",
        timeout=1,
        attempts=2,
        api_key="test-only",
        allow_test_transport=True,
    )
    result = provider.generate(request())
    assert calls == 2
    assert result.cost_usd == Decimal("0.25")
    assert result.cost_status == "CONFIRMED"
