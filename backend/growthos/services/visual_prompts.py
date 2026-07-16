import hashlib
import json
from dataclasses import dataclass
from typing import TypedDict


class _NormalizedPrompt(TypedDict):
    brand_name: str
    objective: str
    audience: str
    format: str
    aspect_ratio: str
    creation_mode: str
    tone_of_voice: str
    base_prompt: str
    negative_prompt: str
    background_style: str
    photographic_style: str
    lighting: str
    composition: str
    realism_level: str
    allowed_elements: tuple[str, ...]
    forbidden_elements: tuple[str, ...]


def _normalized_text(value: str) -> str:
    return " ".join(value.strip().split())


def _normalized_items(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {_normalized_text(value) for value in values if _normalized_text(value)}
    return tuple(sorted(normalized, key=str.casefold))


@dataclass(frozen=True)
class VisualPromptRequest:
    brand_name: str
    objective: str
    audience: str = ""
    format: str = "FEED"
    aspect_ratio: str = "1:1"
    creation_mode: str = "HYBRID"
    tone_of_voice: str = ""
    base_prompt: str = ""
    negative_prompt: str = ""
    background_style: str = ""
    photographic_style: str = ""
    lighting: str = ""
    composition: str = ""
    realism_level: str = ""
    allowed_elements: tuple[str, ...] = ()
    forbidden_elements: tuple[str, ...] = ()


@dataclass(frozen=True)
class VisualPromptResult:
    prompt: str
    negative_prompt: str
    provider_name: str
    provider_reference: str


class MockVisualPromptProvider:
    """Gera uma direção visual determinística sem rede, relógio ou API paga."""

    name = "mock"
    supported_creation_modes = frozenset({"TEMPLATE", "AI_IMAGE", "HYBRID", "MANUAL"})

    def generate(self, request: VisualPromptRequest) -> VisualPromptResult:
        normalized = self._normalize(request)
        prompt_parts = [
            f"Imagem-base para a marca {normalized['brand_name']}.",
            f"Objetivo visual: {normalized['objective']}.",
            f"Formato {normalized['format']} na proporção {normalized['aspect_ratio']}.",
            f"Modo de criação: {normalized['creation_mode']}.",
        ]
        self._append_optional(prompt_parts, "Público", normalized["audience"])
        self._append_optional(prompt_parts, "Tom visual", normalized["tone_of_voice"])
        self._append_optional(prompt_parts, "Direção-base", normalized["base_prompt"])
        self._append_optional(prompt_parts, "Fundo", normalized["background_style"])
        self._append_optional(prompt_parts, "Estilo fotográfico", normalized["photographic_style"])
        self._append_optional(prompt_parts, "Iluminação", normalized["lighting"])
        self._append_optional(prompt_parts, "Composição", normalized["composition"])
        self._append_optional(prompt_parts, "Realismo", normalized["realism_level"])
        if normalized["allowed_elements"]:
            prompt_parts.append(
                "Elementos permitidos: " + ", ".join(normalized["allowed_elements"]) + "."
            )
        prompt_parts.append(
            "Não inserir texto, letras, preço, CTA ou logotipo na imagem-base; "
            "esses elementos serão aplicados por renderização determinística."
        )

        negative_parts = [
            "texto ilegível",
            "letras",
            "tipografia",
            "logotipo deformado",
            "marca-d'água",
        ]
        if normalized["negative_prompt"]:
            negative_parts.append(normalized["negative_prompt"])
        negative_parts.extend(normalized["forbidden_elements"])
        unique_negative = tuple(dict.fromkeys(negative_parts))

        canonical = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return VisualPromptResult(
            prompt=" ".join(prompt_parts),
            negative_prompt=", ".join(unique_negative),
            provider_name=self.name,
            provider_reference=f"mock-visual-{digest}",
        )

    @staticmethod
    def _append_optional(parts: list[str], label: str, value: object) -> None:
        if value:
            parts.append(f"{label}: {value}.")

    def _normalize(self, request: VisualPromptRequest) -> _NormalizedPrompt:
        brand_name = _normalized_text(request.brand_name)
        objective = _normalized_text(request.objective)
        creation_mode = _normalized_text(request.creation_mode).upper()
        if not brand_name:
            raise ValueError("brand_name is required")
        if not objective:
            raise ValueError("objective is required")
        if creation_mode not in self.supported_creation_modes:
            raise ValueError("unsupported creation_mode")
        return {
            "brand_name": brand_name,
            "objective": objective,
            "audience": _normalized_text(request.audience),
            "format": _normalized_text(request.format).upper() or "FEED",
            "aspect_ratio": _normalized_text(request.aspect_ratio) or "1:1",
            "creation_mode": creation_mode,
            "tone_of_voice": _normalized_text(request.tone_of_voice),
            "base_prompt": _normalized_text(request.base_prompt),
            "negative_prompt": _normalized_text(request.negative_prompt),
            "background_style": _normalized_text(request.background_style),
            "photographic_style": _normalized_text(request.photographic_style),
            "lighting": _normalized_text(request.lighting),
            "composition": _normalized_text(request.composition),
            "realism_level": _normalized_text(request.realism_level),
            "allowed_elements": _normalized_items(request.allowed_elements),
            "forbidden_elements": _normalized_items(request.forbidden_elements),
        }
