import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RequestsPage from "@/app/(portal)/solicitacoes/page";
import { api } from "@/lib/api";
import type { BusinessLead, Role } from "@/types/api";

const auth = vi.hoisted(() => ({ roles: ["CLIENT_OWNER"] as Role[] }));
vi.mock("@/contexts/auth-context", () => ({ useAuth: () => ({ activeOrganizationId: "org-1", roles: auth.roles }) }));

function lead(overrides: Partial<BusinessLead>): BusinessLead {
  return {
    id: "lead-1", business_id: "biz-1", source: "LANDING_DEMO", status: "NOVO", is_demo: true,
    service_requested: "Banho", price_item_label: "Pequeno", reference_price_cents: 5500,
    preferred_period: "Manhã", notes: "", next_action: "Confirmar horário", next_action_due_at: null,
    created_at: "2026-10-28T12:00:00Z", updated_at: "2026-10-28T12:00:00Z", ...overrides,
  };
}

describe("Solicitações", () => {
  beforeEach(() => {
    vi.spyOn(api.businesses, "list").mockResolvedValue([
      { id: "biz-1", organization_id: "org-1", name: "Villa Pet", segment: "Pet shop", timezone: "America/Sao_Paulo", onboarding_status: "COMPLETED" },
    ] as never);
    vi.spyOn(api.landing, "leads").mockResolvedValue([
      lead({}),
      lead({ id: "lead-2", status: "CONFIRMADO", service_requested: "Banho e tosa" }),
      lead({ id: "lead-3", status: "NOVO", source: "LANDING_PAGE", is_demo: false, contact_name: "Tutor Fictício", contact_phone: "16900000000" }),
    ]);
    vi.spyOn(api.landing, "summary").mockResolvedValue({
      business_id: "biz-1", total: 3, demo: 2, by_status: {}, by_source: {}, open_without_next_action: 0,
      overdue_next_actions: 0, awaiting_response: 2, real: 1, whatsapp_clicks_7d: 4, landing_status: "APPROVED",
    });
    vi.spyOn(api.landing, "get").mockResolvedValue({ service_options: ["Banho"], price_items: [] } as never);
  });

  it("mostra primeiro o que precisa de resposta e permite ao responsável agir", async () => {
    auth.roles = ["CLIENT_OWNER"];
    const update = vi.spyOn(api.landing, "updateLead").mockResolvedValue(lead({ status: "HORARIO_OFERTADO" }));
    const user = userEvent.setup();
    render(<RequestsPage />);

    expect(await screen.findByText("Contato: Tutor Fictício · 16900000000")).toBeVisible();
    expect(screen.queryByText(/Banho e tosa/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Exportar dados" })).toHaveLength(1);
    await user.click(screen.getAllByRole("button", { name: "Horário ofertado" })[0]);
    expect(update).toHaveBeenCalledWith("lead-1", { status: "HORARIO_OFERTADO" });

    await user.click(screen.getByRole("button", { name: "Todos" }));
    expect(screen.getByText(/Banho e tosa/)).toBeVisible();
  });

  it("confirma só após confirmação explícita da equipe e mostra o histórico auditado", async () => {
    auth.roles = ["CLIENT_OWNER"];
    const update = vi.spyOn(api.landing, "updateLead").mockResolvedValue(lead({ status: "CONFIRMADO" }));
    vi.spyOn(api.landing, "history").mockResolvedValue([
      { action: "business_lead.demo_created", at: "2026-10-28T12:00:00Z", actor: "Página pública", changes: { source: "LANDING_DEMO" } },
      { action: "business_lead.updated", at: "2026-10-28T13:00:00Z", actor: "Responsável Villa Pet", changes: { status: "NOVO->HORARIO_OFERTADO" } },
    ]);
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const user = userEvent.setup();
    render(<RequestsPage />);

    expect(await screen.findByText("Cliques no WhatsApp (7 dias)")).toBeVisible();
    expect(screen.getByText("4")).toBeVisible();
    const confirmButton = screen.getAllByRole("button", { name: "Confirmar agendamento" })[0];
    await user.click(confirmButton);
    expect(update).not.toHaveBeenCalled();
    await user.click(confirmButton);
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(update).toHaveBeenCalledWith("lead-1", { status: "CONFIRMADO" });

    await user.click(screen.getAllByRole("button", { name: "Ver histórico" })[0]);
    const history = await screen.findByRole("list", { name: "Histórico do pedido" });
    expect(history).toHaveTextContent("Recebido pela página (demo)");
    expect(history).toHaveTextContent("Atualizado (Novo → Horário ofertado) · Responsável Villa Pet");
    confirm.mockRestore();
  });

  it("deixa o revisor apenas consultar", async () => {
    auth.roles = ["CLIENT_REVIEWER"];
    render(<RequestsPage />);
    expect(await screen.findByText("Contato: Tutor Fictício · 16900000000")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Horário ofertado" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar agendamento" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Exportar dados" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Registrar pedido/)).not.toBeInTheDocument();
  });
});
