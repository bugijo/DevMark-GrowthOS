"""Orquestracao do classificador sensivel com provider mock deterministico."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from growthos.domain.enums import SensitivityCategory
from growthos.domain.sensitivity import (
    ContextualVeterinaryRules,
    SensitivityDocument,
    SensitivitySignal,
)
from growthos.models.base import utcnow


@dataclass(frozen=True, slots=True)
class SensitivityAssessment:
    is_sensitive: bool
    categories: tuple[SensitivityCategory, ...]
    codes: tuple[str, ...]
    score: int
    provider: str
    provider_version: str
    assessed_at: datetime


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


class MockVeterinarySensitivityProvider:
    """Provider local que simula classificacao sem API ou dado probabilistico."""

    name = "mock_veterinary_safety"
    version = "mock-vet-safety-1.0"

    _clinical_action = re.compile(
        r"\b(?:tratar|tratamento|prescrever|administrar|diagnosticar|diagnostico|"
        r"vacinar|vacinacao|cirurgia|prognostico|dose|dosagem)\b"
    )
    _animal_subject = re.compile(
        r"\b(?:pet|animal|cao|caes|gato|gatos|felino|canino|veterinari[oa])\b"
    )
    _assertion = re.compile(
        r"\b(?:deve|indicado|recomendado|confirma|garante|previne|cura|protocolo)\b"
    )
    _negated_claim = re.compile(
        r"\b(?:nao|sem|evite|evitar|proibid[oa]s?|jamais)\b.{0,70}"
        r"(?:tratar|tratamento|prescrever|administrar|diagnosticar|diagnostico|"
        r"vacinar|vacinacao|cirurgia|prognostico|dose|dosagem|recomendado|garante|cura)\b"
    )

    def assess(self, document: SensitivityDocument) -> tuple[SensitivitySignal, ...]:
        # O prompt negativo descreve exclusoes visuais, nao uma afirmacao publicada.
        fields = (
            document.title,
            document.caption,
            document.objective,
            document.audience,
            document.cta,
            document.notes,
            document.script,
            document.visual_prompt,
        )
        contextual_claim = False
        for raw_field in fields:
            for segment in re.split(r"[.!?;\n]+", _plain(raw_field)):
                if self._negated_claim.search(segment):
                    continue
                if (
                    self._clinical_action.search(segment)
                    and self._animal_subject.search(segment)
                    and self._assertion.search(segment)
                ):
                    contextual_claim = True
                    break
            if contextual_claim:
                break
        if not contextual_claim:
            return ()
        return (
            SensitivitySignal(
                code="MOCK_VET_CLINICAL_ASSERTION",
                category=SensitivityCategory.MEDICAL_CLAIM,
                score=56,
                field="document",
            ),
        )


class VeterinarySensitivityClassifier:
    """Combina sinais explicaveis das regras e do provider mock."""

    threshold = 50

    def __init__(
        self,
        *,
        rules: ContextualVeterinaryRules | None = None,
        provider: MockVeterinarySensitivityProvider | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._rules = rules or ContextualVeterinaryRules()
        self._provider = provider or MockVeterinarySensitivityProvider()
        self._clock = clock or utcnow

    def assess(self, document: SensitivityDocument) -> SensitivityAssessment:
        rule_result = self._rules.assess(document)
        signals_by_code = {signal.code: signal for signal in rule_result.signals}
        for signal in self._provider.assess(document):
            signals_by_code.setdefault(signal.code, signal)
        signals = tuple(sorted(signals_by_code.values(), key=lambda item: item.code))
        scores = sorted((signal.score for signal in signals), reverse=True)
        score = min(100, scores[0] + min(20, sum(scores[1:]) // 5)) if scores else 0
        categories = tuple(sorted({signal.category for signal in signals}, key=str))
        return SensitivityAssessment(
            is_sensitive=score >= self.threshold,
            categories=categories,
            codes=tuple(signal.code for signal in signals),
            score=score,
            provider=f"contextual_rules+{self._provider.name}",
            provider_version=f"{self._rules.version}+{self._provider.version}",
            assessed_at=self._clock(),
        )


def content_document(
    *,
    title: str,
    caption: str,
    objective: str,
    audience: str,
    cta: str,
    notes: str,
    script: str,
    visual_prompt: str,
    negative_prompt: str,
) -> SensitivityDocument:
    return SensitivityDocument(
        title=title,
        caption=caption,
        objective=objective,
        audience=audience,
        cta=cta,
        notes=notes,
        script=script,
        visual_prompt=visual_prompt,
        negative_prompt=negative_prompt,
    )


def assessment_fields(assessment: SensitivityAssessment) -> dict[str, object]:
    """Traduz o snapshot sem persistir o texto que originou a decisao."""

    return {
        "is_sensitive": assessment.is_sensitive,
        "sensitivity_categories": [category.value for category in assessment.categories],
        "sensitivity_codes": list(assessment.codes),
        "sensitivity_score": assessment.score,
        "sensitivity_provider": assessment.provider,
        "sensitivity_provider_version": assessment.provider_version,
        "sensitivity_assessed_at": assessment.assessed_at,
    }
