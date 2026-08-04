"""Classificacao deterministica de risco veterinario em conteudo editorial.

As regras procuram afirmacoes e instrucoes em contexto. Termos isolados, negacoes e
itens listados apenas no prompt negativo nao tornam um conteudo sensivel.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from growthos.domain.enums import SensitivityCategory


@dataclass(frozen=True, slots=True)
class SensitivityDocument:
    title: str = ""
    caption: str = ""
    objective: str = ""
    audience: str = ""
    cta: str = ""
    notes: str = ""
    script: str = ""
    visual_prompt: str = ""
    negative_prompt: str = ""


@dataclass(frozen=True, slots=True)
class SensitivitySignal:
    code: str
    category: SensitivityCategory
    score: int
    field: str


@dataclass(frozen=True, slots=True)
class RuleAssessment:
    signals: tuple[SensitivitySignal, ...]

    @property
    def score(self) -> int:
        if not self.signals:
            return 0
        ordered = sorted((signal.score for signal in self.signals), reverse=True)
        return min(100, ordered[0] + min(20, sum(ordered[1:]) // 5))


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(character for character in decomposed if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", plain).strip()


_NEGATED_PREFIX = re.compile(
    r"(?:\bnao\b|\bsem\b|\bevitar\b|\bjamais\b|\bproibid[oa]s?\b|"
    r"\bnao mostrar\b|\bnao incluir\b).{0,45}$"
)


def _has_non_negated_match(text: str, pattern: re.Pattern[str]) -> bool:
    for match in pattern.finditer(text):
        prefix = text[max(0, match.start() - 55) : match.start()]
        if not _NEGATED_PREFIX.search(prefix):
            return True
    return False


_CONTEXT = re.compile(
    r"\b(?:pet|animal|cao|caes|gato|gatos|felino|canino|veterinari[oa]|clinica|paciente)\b"
)


_RULES: tuple[tuple[str, SensitivityCategory, int, re.Pattern[str]], ...] = (
    (
        "VET_DIAGNOSIS_ASSERTION",
        SensitivityCategory.DIAGNOSIS,
        78,
        re.compile(
            r"\b(?:diagnostic(?:o|ar|ado)|resultado do exame|exame (?:confirma|indica)|"
            r"seu (?:pet|animal|cao|gato) (?:tem|esta com))\b"
        ),
    ),
    (
        "VET_TREATMENT_DIRECTION",
        SensitivityCategory.TREATMENT,
        72,
        re.compile(
            r"\b(?:tratamento (?:para|indicado|veterinario|clinico)|"
            r"tratamento d[oa] (?:doenca|infeccao|animal|pet)|protocolo terapeutico|"
            r"trate (?:o|a|seu|sua)|deve ser tratad[oa]|recomendamos tratar)\b"
        ),
    ),
    (
        "VET_MEDICATION_RECOMMENDATION",
        SensitivityCategory.MEDICATION,
        82,
        re.compile(
            r"\b(?:prescrev(?:er|emos|a)|medicamento (?:indicado|recomendado)|"
            r"antibiotico (?:indicado|recomendado)|anti-inflamatorio (?:indicado|recomendado)|"
            r"vermifugo (?:indicado|recomendado)|administr(?:e|ar) (?:o )?medicamento)\b"
        ),
    ),
    (
        "VET_DOSAGE_INSTRUCTION",
        SensitivityCategory.DOSAGE,
        96,
        re.compile(
            r"\b(?:administr(?:e|ar)|apli(?:que|car)|dar|oferec(?:a|er)|tomar)\b"
            r".{0,75}\b\d+(?:[.,]\d+)?\s*(?:mg|ml|g|mcg|gotas?|comprimidos?)\b"
        ),
    ),
    (
        "VET_PROGNOSIS_ASSERTION",
        SensitivityCategory.PROGNOSIS,
        75,
        re.compile(
            r"\b(?:prognostico (?:e|sera)|chance de (?:cura|sobrevida)|"
            r"tempo de sobrevida|vai se recuperar|nao vai sobreviver)\b"
        ),
    ),
    (
        "VET_EMERGENCY_DIRECTION",
        SensitivityCategory.EMERGENCY,
        92,
        re.compile(
            r"\b(?:emergencia veterinaria|risco de morte|procure (?:um )?veterinari[oa]"
            r".{0,35}(?:agora|imediatamente)|leve (?:o|seu) (?:pet|animal).{0,35}imediatamente)\b"
        ),
    ),
    (
        "VET_PROCEDURE_GUIDANCE",
        SensitivityCategory.PROCEDURE,
        62,
        re.compile(
            r"\b(?:esquema de vacinacao|calendario vacinal|vacina (?:indicada|obrigatoria)|"
            r"procedimento cirurgico|pos-operatorio|pre-operatorio|"
            r"castracao (?:indicada|recomendada))\b"
        ),
    ),
    (
        "VET_CURE_GUARANTEE",
        SensitivityCategory.CURE_CLAIM,
        98,
        re.compile(
            r"\b(?:cura garantida|garante a cura|elimina (?:a )?doenca|"
            r"resultado clinico garantido|100% eficaz contra)\b"
        ),
    ),
    (
        "VET_CLINICAL_DIET",
        SensitivityCategory.CLINICAL_NUTRITION,
        68,
        re.compile(
            r"\b(?:dieta (?:para tratar|terapeutica|clinica)|racao terapeutica|"
            r"alimentacao (?:indicada|prescrita) para)\b"
        ),
    ),
    (
        "VET_MEDICAL_PREVENTION_CLAIM",
        SensitivityCategory.MEDICAL_CLAIM,
        58,
        re.compile(
            r"\b(?:previne (?:a |o )?(?:doenca|infeccao|parvovirose|cinomose|raiva)|"
            r"protege contra (?:a |o )?(?:doenca|infeccao|parvovirose|cinomose|raiva)|"
            r"comprovadamente eficaz (?:para|contra))\b"
        ),
    ),
)

_SYMPTOMS = re.compile(
    r"\b(?:vomit(?:o|ando)|diarreia|convuls(?:ao|oes)|sangramento|desmaio|"
    r"falta de ar|febre|apatia|dor intensa|perda de apetite)\b"
)
_SYMPTOM_DIRECTION = re.compile(
    r"\b(?:sinais de|sintomas de|pode indicar|indica que|o que fazer|quando procurar)\b"
)


class ContextualVeterinaryRules:
    """Motor puro de regras versionadas, sem rede nem persistencia."""

    version = "vet-context-rules-1.0"

    def assess(self, document: SensitivityDocument) -> RuleAssessment:
        signals: dict[str, SensitivitySignal] = {}
        fields = {
            "title": document.title,
            "caption": document.caption,
            "objective": document.objective,
            "audience": document.audience,
            "cta": document.cta,
            "notes": document.notes,
            "script": document.script,
            "visual_prompt": document.visual_prompt,
        }
        for field, raw_text in fields.items():
            text = _normalize(raw_text)
            if not text:
                continue
            has_veterinary_context = bool(_CONTEXT.search(text))
            for code, category, rule_score, pattern in _RULES:
                if not _has_non_negated_match(text, pattern):
                    continue
                # Dosagem, promessa de cura e emergencia sao intrinsecamente clinicas.
                if (
                    category
                    not in {
                        SensitivityCategory.DOSAGE,
                        SensitivityCategory.CURE_CLAIM,
                        SensitivityCategory.EMERGENCY,
                    }
                    and not has_veterinary_context
                ):
                    continue
                current = signals.get(code)
                signal = SensitivitySignal(code, category, rule_score, field)
                if current is None or signal.score > current.score:
                    signals[code] = signal
            symptom_count = len(_SYMPTOMS.findall(text))
            if has_veterinary_context and symptom_count >= 2 and _SYMPTOM_DIRECTION.search(text):
                signals["VET_SYMPTOM_INTERPRETATION"] = SensitivitySignal(
                    "VET_SYMPTOM_INTERPRETATION",
                    SensitivityCategory.SYMPTOMS,
                    70,
                    field,
                )
        return RuleAssessment(tuple(sorted(signals.values(), key=lambda item: item.code)))
