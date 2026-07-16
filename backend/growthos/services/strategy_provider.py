import hashlib
import json
from dataclasses import dataclass


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


@dataclass(frozen=True, slots=True)
class StrategyGenerationRequest:
    brand_name: str
    objective: str
    positioning: str = ""
    funnel: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    pillars: tuple[str, ...] = ()
    planned_indicators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyGenerationResult:
    positioning: str
    funnel: tuple[str, ...]
    channels: tuple[str, ...]
    pillars: tuple[str, ...]
    planned_indicators: tuple[str, ...]
    provider_name: str
    provider_reference: str


class MockStrategyProvider:
    name = "mock"

    def generate(self, request: StrategyGenerationRequest) -> StrategyGenerationResult:
        brand = _clean(request.brand_name)
        objective = _clean(request.objective)
        if not brand or not objective:
            raise ValueError("marca e objetivo são obrigatórios")
        positioning = _clean(request.positioning) or (
            f"Posicionar {brand} como referência confiável em {objective.casefold()}."
        )
        funnel = self._items(request.funnel) or ("DESCOBERTA", "CONSIDERAÇÃO", "AÇÃO")
        channels = self._items(request.channels) or ("INSTAGRAM",)
        pillars = self._items(request.pillars) or (
            "Educação responsável",
            "Bastidores e confiança",
            "Serviços e diferenciais",
        )
        indicators = self._items(request.planned_indicators) or (
            "conteúdos planejados",
            "aprovações concluídas",
            "publicações registradas",
        )
        canonical = json.dumps(
            {
                "brand": brand,
                "objective": objective,
                "positioning": positioning,
                "funnel": funnel,
                "channels": channels,
                "pillars": pillars,
                "indicators": indicators,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        reference = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return StrategyGenerationResult(
            positioning=positioning,
            funnel=funnel,
            channels=channels,
            pillars=pillars,
            planned_indicators=indicators,
            provider_name=self.name,
            provider_reference=f"mock-strategy-{reference}",
        )

    @staticmethod
    def _items(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(cleaned for value in values if (cleaned := _clean(value))))
