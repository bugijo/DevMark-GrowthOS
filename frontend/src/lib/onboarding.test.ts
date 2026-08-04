import { describe, expect, it } from "vitest";

import {
  buildOnboardingStepPayload,
  createOnboardingFormState,
  splitOnboardingList,
  validateOnboardingStep,
} from "@/lib/onboarding";
import type { Business, BusinessOnboarding } from "@/types/api";

const business: Business = {
  id: "business-1",
  organization_id: "organization-1",
  name: "Clínica Vet Vida",
  segment: "Veterinária",
  timezone: "America/Sao_Paulo",
};

function onboarding(
  overrides: Partial<BusinessOnboarding> = {},
): BusinessOnboarding {
  return {
    id: "onboarding-1",
    organization_id: "organization-1",
    business_id: "business-1",
    status: "IN_PROGRESS",
    current_step: 1,
    completed_steps: [],
    missing_steps: Array.from({ length: 15 }, (_, index) => index + 1),
    progress_percent: 0,
    revision: 1,
    step_data: {},
    summary: {
      business_id: "business-1",
      brand_profile_id: null,
      service_ids: [],
      audience_ids: [],
      objective_ids: [],
      logo_media_asset_ids: [],
      visual_reference_media_asset_ids: [],
      approver_membership_ids: [],
      initial_preset_id: null,
      notification_settings_configured: false,
    },
    started_by_user_id: "user-1",
    updated_by_user_id: "user-1",
    completed_by_user_id: null,
    completed_at: null,
    created_at: "2026-07-16T12:00:00Z",
    updated_at: "2026-07-16T12:00:00Z",
    ...overrides,
  };
}

describe("onboarding da empresa", () => {
  it("restaura dados persistidos e preserva os identificadores do catálogo", () => {
    const state = createOnboardingFormState(
      business,
      onboarding({
        current_step: 4,
        completed_steps: [1, 2, 3],
        step_data: {
          "1": {
            name: "Vet Vida Centro",
            brand_name: "Vet Vida",
            public_name: "Vet Vida",
            timezone: "America/Sao_Paulo",
          },
          "3": {
            services: [
              {
                id: "service-1",
                name: "Consulta preventiva",
                description: "Avaliação de rotina",
                category: "Consulta",
                warnings: ["Não prometer diagnóstico sem avaliação"],
              },
            ],
          },
        },
      }),
    );

    expect(state.company.name).toBe("Vet Vida Centro");
    expect(state.services[0]).toMatchObject({
      id: "service-1",
      name: "Consulta preventiva",
      warnings: "Não prometer diagnóstico sem avaliação",
    });
    expect(buildOnboardingStepPayload(3, 8, state)).toEqual({
      step: 3,
      revision: 8,
      services: [
        {
          id: "service-1",
          name: "Consulta preventiva",
          description: "Avaliação de rotina",
          category: "Consulta",
          warnings: ["Não prometer diagnóstico sem avaliação"],
        },
      ],
    });
  });

  it("normaliza listas e bloqueia itens repetidos antes de chamar a API", () => {
    const state = createOnboardingFormState(business, onboarding());
    state.services = [
      { name: "Vacinação", description: "", category: "", warnings: "" },
      { name: " vacinação ", description: "", category: "", warnings: "" },
    ];

    expect(splitOnboardingList(" prevenção, acolhimento\nprevenção ")).toEqual([
      "prevenção",
      "acolhimento",
    ]);
    expect(validateOnboardingStep(3, state)).toEqual({
      services: "Não repita o mesmo serviço.",
    });
  });

  it("cria um preset mock completo com as escolhas salvas no Brand Kit", () => {
    const state = createOnboardingFormState(business, onboarding());
    state.logoIds = ["asset-logo"];
    state.visual.primaryColors = "#146B5F\n#FFFFFF";
    state.visual.fonts = "Inter";
    state.rules.imageRestrictions = "Sem marcas de terceiros";
    state.preset.source = "new";
    state.preset.name = "Feed Vet Vida";

    const payload = buildOnboardingStepPayload(14, 14, state);

    expect(payload).toMatchObject({
      step: 14,
      revision: 14,
      preset: {
        name: "Feed Vet Vida",
        creation_mode: "HYBRID",
        color_palette: ["#146B5F", "#FFFFFF"],
        fonts: ["Inter"],
        logo_media_asset_id: "asset-logo",
        forbidden_elements: ["Sem marcas de terceiros"],
      },
    });
  });

  it("exige a confirmação final e rejeita fuso horário inválido", () => {
    const state = createOnboardingFormState(business, onboarding());
    state.company.timezone = "Brasil/SemCidade";

    expect(validateOnboardingStep(1, state).timezone).toMatch(/fuso horário válido/i);
    expect(validateOnboardingStep(15, state)).toEqual({
      confirmed: "Confirme a revisão para salvar esta etapa.",
    });
  });
});
