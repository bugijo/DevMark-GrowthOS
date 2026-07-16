from growthos.services.providers import MockTextProvider, TextGenerationRequest


def test_mock_provider_respects_persisted_field_limits() -> None:
    provider = MockTextProvider()

    result = provider.generate(
        TextGenerationRequest(
            brand_name="M" * 200,
            objective="O" * 1000,
            channel="INSTAGRAM",
            format="FEED",
            cta="C" * 1000,
        )
    )

    assert len(result.title) == provider.title_max_length
    assert len(result.cta) == provider.cta_max_length
    assert result.provider_name == "mock"
