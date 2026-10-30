import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { ApiError, api } from "@/lib/api";
import type { Business, BusinessOnboarding } from "@/types/api";

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    activeOrganizationId: "organization-1",
    roles: ["AGENCY_ADMIN"],
  }),
}));

const business: Business = {
  id: "business-1",
  organization_id: "organization-1",
  name: "Clínica Vet Vida",
  segment: "Veterinária",
  timezone: "America/Sao_Paulo",
  onboarding_status: "IN_PROGRESS",
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

// O assistente renderiza um formulário grande e os testes digitam campo a campo.
// Sob CPU disputada (suíte completa em paralelo, disco HDD) qualquer teste passa
// de 5 s; o limite de 15 s, antes só no primeiro teste, vale para todos.
describe("OnboardingWizard", { timeout: 15_000 }, () => {
  beforeEach(() => {
    vi.spyOn(api.businesses, "get").mockResolvedValue(business);
    vi.spyOn(api.onboarding, "get").mockResolvedValue(onboarding());
    vi.spyOn(api.media, "list").mockResolvedValue([]);
    vi.spyOn(api.onboarding, "approvers").mockResolvedValue([]);
    vi.spyOn(api.catalogs.presets, "list").mockResolvedValue([]);
  });

  it("salva a etapa com a revisão atual e avança usando a resposta persistida", async () => {
    const save = vi.spyOn(api.onboarding, "saveStep").mockResolvedValue(
      onboarding({
        current_step: 2,
        completed_steps: [1],
        missing_steps: Array.from({ length: 14 }, (_, index) => index + 2),
        progress_percent: 7,
        revision: 2,
        step_data: {
          "1": {
            name: "Clínica Vet Vida Norte",
            brand_name: "Clínica Vet Vida",
            public_name: "Clínica Vet Vida",
            description: "",
            timezone: "America/Sao_Paulo",
          },
        },
      }),
    );
    const user = userEvent.setup();
    render(<OnboardingWizard businessId="business-1" />);

    expect(
      await screen.findByRole("heading", { name: "Empresa e marca" }),
    ).toBeVisible();
    const companyName = screen.getByLabelText(/Nome da empresa/);
    await user.clear(companyName);
    await user.type(companyName, "Clínica Vet Vida Norte");
    await user.click(screen.getByRole("button", { name: "Salvar e continuar" }));

    await waitFor(() =>
      expect(save).toHaveBeenCalledWith("business-1", {
        step: 1,
        revision: 1,
        name: "Clínica Vet Vida Norte",
        brand_name: "Clínica Vet Vida",
        public_name: "Clínica Vet Vida",
        description: "",
        timezone: "America/Sao_Paulo",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Segmento" })).toBeVisible();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "7");
  });

  it("reabre uma conclusão editada e exige uma nova revisão final", async () => {
    const completed = onboarding({
      status: "COMPLETED",
      current_step: 15,
      completed_steps: Array.from({ length: 15 }, (_, index) => index + 1),
      missing_steps: [],
      progress_percent: 100,
      revision: 20,
      completed_by_user_id: "user-1",
      completed_at: "2026-07-16T15:00:00Z",
      step_data: {
        "1": {
          name: "Clínica Vet Vida",
          brand_name: "Clínica Vet Vida",
          public_name: "Clínica Vet Vida",
          description: "",
          timezone: "America/Sao_Paulo",
        },
        "15": { confirmed: true, notes: "Revisado" },
      },
    });
    vi.mocked(api.onboarding.get).mockResolvedValue(completed);
    const save = vi
      .spyOn(api.onboarding, "saveStep")
      .mockResolvedValue({
        ...completed,
        status: "IN_PROGRESS",
        completed_steps: Array.from({ length: 14 }, (_, index) => index + 1),
        missing_steps: [15],
        progress_percent: 93,
        revision: 21,
        completed_by_user_id: null,
        completed_at: null,
        step_data: {
          "1": completed.step_data["1"],
        },
      });
    const user = userEvent.setup();
    render(<OnboardingWizard businessId="business-1" />);

    await user.click(
      await screen.findByRole("button", { name: "Editar onboarding" }),
    );
    await user.click(screen.getByRole("button", { name: "Empresa e marca" }));

    const stepTitle = screen.getByRole("heading", { name: "Empresa e marca" });
    expect(stepTitle).toHaveAttribute("tabindex", "-1");
    await user.click(screen.getByRole("button", { name: "Salvar e continuar" }));

    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Concluir onboarding" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Revisão final" })).toBeVisible();
    expect(screen.getByText(/Faça uma nova revisão final/i)).toBeVisible();
    expect(
      screen.getByRole("checkbox", {
        name: /Revisei os dados e confirmo que não incluí informações clínicas/i,
      }),
    ).not.toBeChecked();
    expect(screen.queryByRole("button", { name: "Voltar ao resumo" })).not.toBeInTheDocument();
  });

  it("mantém o rascunho ao voltar e avançar entre etapas disponíveis", async () => {
    vi.mocked(api.onboarding.get).mockResolvedValue(
      onboarding({
        current_step: 2,
        completed_steps: [1],
        missing_steps: Array.from({ length: 14 }, (_, index) => index + 2),
        progress_percent: 7,
        revision: 2,
        step_data: {
          "1": {
            name: "Clínica Vet Vida",
            brand_name: "Clínica Vet Vida",
            public_name: "Clínica Vet Vida",
            description: "",
            timezone: "America/Sao_Paulo",
          },
        },
      }),
    );
    const user = userEvent.setup();
    render(<OnboardingWizard businessId="business-1" />);

    const segment = await screen.findByRole("textbox", { name: "Segmento" });
    await user.clear(segment);
    await user.type(segment, "Saúde veterinária");
    await user.click(screen.getByRole("button", { name: "Voltar" }));
    await user.click(screen.getByRole("button", { name: "Segmento" }));

    expect(screen.getByRole("textbox", { name: "Segmento" })).toHaveValue(
      "Saúde veterinária",
    );
  });

  it("bloqueia nova gravação quando a revisão do servidor mudou", async () => {
    vi.spyOn(api.onboarding, "saveStep").mockRejectedValue(
      new ApiError("O onboarding foi atualizado em outra sessão.", 409),
    );
    const user = userEvent.setup();
    render(<OnboardingWizard businessId="business-1" />);

    await user.click(
      await screen.findByRole("button", { name: "Salvar e continuar" }),
    );

    expect(
      await screen.findByText("Há uma versão mais recente no servidor."),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Salvar e continuar" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Recarregar versão do servidor" }),
    ).toBeVisible();
  });
});
