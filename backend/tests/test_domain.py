import pytest

from growthos.domain.content import InvalidContentTransition, validate_transition
from growthos.domain.enums import ContentStatus
from growthos.services.providers import MockTextProvider, TextGenerationRequest


def test_content_transition_matrix_accepts_expected_path() -> None:
    validate_transition(ContentStatus.DRAFT, ContentStatus.INTERNAL_REVIEW)
    validate_transition(ContentStatus.INTERNAL_REVIEW, ContentStatus.CLIENT_REVIEW)
    validate_transition(ContentStatus.CLIENT_REVIEW, ContentStatus.APPROVED)


def test_content_transition_matrix_rejects_shortcut() -> None:
    with pytest.raises(InvalidContentTransition):
        validate_transition(ContentStatus.DRAFT, ContentStatus.APPROVED)


def test_mock_provider_is_deterministic_and_offline() -> None:
    provider = MockTextProvider()
    request = TextGenerationRequest(
        brand_name="Clínica Feliz",
        objective="Vacinação preventiva",
        channel="INSTAGRAM",
        format="FEED",
        audience="tutores responsáveis",
    )
    assert provider.generate(request) == provider.generate(request)
    assert provider.generate(request).provider_name == "mock"

