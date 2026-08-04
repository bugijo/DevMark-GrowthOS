from datetime import UTC, datetime

from growthos.domain.enums import SensitivityCategory
from growthos.domain.sensitivity import ContextualVeterinaryRules, SensitivityDocument
from growthos.services.sensitivity import VeterinarySensitivityClassifier


def test_contextual_rules_do_not_treat_isolated_marketing_terms_as_clinical() -> None:
    result = ContextualVeterinaryRules().assess(
        SensitivityDocument(
            title="Diagnóstico de marca",
            caption="Nosso tratamento de dados melhora a estratégia da clínica.",
            objective="Apresentar uma análise de posicionamento veterinário.",
        )
    )

    assert result.score == 0
    assert result.signals == ()


def test_classifier_flags_contextual_dosage_and_medication_instruction() -> None:
    now = datetime(2026, 7, 16, 12, tzinfo=UTC)
    classifier = VeterinarySensitivityClassifier(clock=lambda: now)

    first = classifier.assess(
        SensitivityDocument(
            title="Orientação ao tutor",
            caption="Para o seu cão, administre o medicamento recomendado na dose de 5 mg.",
        )
    )
    second = classifier.assess(
        SensitivityDocument(
            title="Orientação ao tutor",
            caption="Para o seu cão, administre o medicamento recomendado na dose de 5 mg.",
        )
    )

    assert first == second
    assert first.is_sensitive is True
    assert first.score >= 90
    assert SensitivityCategory.DOSAGE in first.categories
    assert "VET_DOSAGE_INSTRUCTION" in first.codes
    assert first.assessed_at == now


def test_classifier_ignores_exclusions_in_negative_prompt() -> None:
    assessment = VeterinarySensitivityClassifier().assess(
        SensitivityDocument(
            title="Boas-vindas à clínica",
            caption="Conheça nossa equipe e nossos espaços acolhedores para pets.",
            negative_prompt=(
                "não mostrar cirurgia, medicamento recomendado, dose de 5 mg ou emergência"
            ),
        )
    )

    assert assessment.is_sensitive is False
    assert assessment.codes == ()


def test_mock_provider_does_not_promote_a_negated_clinical_claim() -> None:
    assessment = VeterinarySensitivityClassifier().assess(
        SensitivityDocument(
            caption=(
                "Para seu pet, não recomendamos administrar medicamento sem avaliação "
                "individual do veterinário."
            )
        )
    )

    assert assessment.is_sensitive is False
    assert "MOCK_VET_CLINICAL_ASSERTION" not in assessment.codes


def test_classifier_requires_veterinary_context_for_ambiguous_procedure() -> None:
    safe = VeterinarySensitivityClassifier().assess(
        SensitivityDocument(caption="O tratamento indicado para a madeira preserva o acabamento.")
    )
    sensitive = VeterinarySensitivityClassifier().assess(
        SensitivityDocument(
            caption="Para seu pet, o tratamento indicado deve seguir o protocolo terapêutico."
        )
    )

    assert safe.is_sensitive is False
    assert sensitive.is_sensitive is True
    assert SensitivityCategory.TREATMENT in sensitive.categories
