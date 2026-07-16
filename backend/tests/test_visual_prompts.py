import pytest

from growthos.services.visual_prompts import MockVisualPromptProvider, VisualPromptRequest


def test_mock_visual_prompt_is_deterministic_after_normalization() -> None:
    provider = MockVisualPromptProvider()
    first = provider.generate(
        VisualPromptRequest(
            brand_name="  Clínica   Demo ",
            objective="Educar sobre prevenção",
            audience="Tutores responsáveis",
            allowed_elements=("animais felizes", "ambiente claro"),
            forbidden_elements=("agulhas", "ferimentos"),
        )
    )
    second = provider.generate(
        VisualPromptRequest(
            brand_name="Clínica Demo",
            objective="Educar  sobre prevenção",
            audience="Tutores responsáveis",
            allowed_elements=("ambiente claro", "animais felizes"),
            forbidden_elements=("ferimentos", "agulhas"),
        )
    )

    assert first == second
    assert first.provider_name == "mock"
    assert first.provider_reference.startswith("mock-visual-")


def test_mock_visual_prompt_keeps_text_out_of_the_generated_image() -> None:
    result = MockVisualPromptProvider().generate(
        VisualPromptRequest(
            brand_name="Clínica Demo",
            objective="Apresentar atendimento preventivo",
            base_prompt="fotografia acolhedora",
            background_style="consultório organizado",
            lighting="luz natural suave",
            forbidden_elements=("promessas terapêuticas",),
        )
    )

    assert "Não inserir texto" in result.prompt
    assert "renderização determinística" in result.prompt
    assert "fotografia acolhedora" in result.prompt
    assert "promessas terapêuticas" in result.negative_prompt
    assert "logotipo deformado" in result.negative_prompt


@pytest.mark.parametrize(
    ("prompt_request", "message"),
    [
        (VisualPromptRequest(brand_name=" ", objective="Educar"), "brand_name"),
        (VisualPromptRequest(brand_name="Clínica Demo", objective=" "), "objective"),
        (
            VisualPromptRequest(
                brand_name="Clínica Demo",
                objective="Educar",
                creation_mode="UNKNOWN",
            ),
            "creation_mode",
        ),
    ],
)
def test_mock_visual_prompt_rejects_missing_or_unsupported_context(
    prompt_request: VisualPromptRequest,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        MockVisualPromptProvider().generate(prompt_request)
