from dataclasses import dataclass


@dataclass(frozen=True)
class TextGenerationRequest:
    brand_name: str
    objective: str
    channel: str
    format: str
    audience: str = ""
    tone_of_voice: str = ""
    cta: str = ""


@dataclass(frozen=True)
class TextGenerationResult:
    title: str
    caption: str
    audience: str
    cta: str
    provider_name: str


class MockTextProvider:
    """Provider local determinístico: não usa rede, relógio ou aleatoriedade."""

    name = "mock"

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        brand = request.brand_name.strip() or "Sua marca"
        objective = " ".join(request.objective.strip().split())
        audience = request.audience.strip() or "público da marca"
        tone = request.tone_of_voice.strip() or "claro e acolhedor"
        cta = request.cta.strip() or "Fale com nossa equipe para saber mais."
        title = f"{brand}: {objective}"
        caption = (
            f"{brand} apresenta um conteúdo sobre {objective.lower()}, "
            f"pensado para {audience}. Tom: {tone}. {cta}"
        )
        return TextGenerationResult(title, caption, audience, cta, self.name)
