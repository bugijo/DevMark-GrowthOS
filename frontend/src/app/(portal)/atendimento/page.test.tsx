import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ServiceSettingsPage from "@/app/(portal)/atendimento/page";
import { ApiError, api } from "@/lib/api";
import type { LeadPrivacy, Role } from "@/types/api";

const auth = vi.hoisted(() => ({ roles: ["CLIENT_OWNER"] as Role[] }));
vi.mock("@/contexts/auth-context", () => ({ useAuth: () => ({ activeOrganizationId: "org-1", roles: auth.roles }) }));

const draftNotice: LeadPrivacy = {
  id: "p-1", business_id: "biz-1", status: "DRAFT", version: 2, approved_at: null, approval_note: "",
  updated_at: "2026-10-28T12:00:00Z", controller_name: "Villa Pet", privacy_contact: "Canal oficial",
  purpose: "Responder ao pedido de agendamento.", legal_basis: "PROCEDIMENTOS_PRELIMINARES",
  data_categories: ["Nome"], retention_days: 90, notice_text: "Texto de exemplo.",
};

describe("Horários e privacidade", () => {
  beforeEach(() => {
    vi.spyOn(api.businesses, "list").mockResolvedValue([{ id: "biz-1", name: "Villa Pet" }] as never);
    vi.spyOn(api.landing, "availability").mockResolvedValue({
      business_id: "biz-1", slots: [], notes: "", confirmed_by_business: false, version: 0, updated_at: null,
    });
  });

  it("não inventa horários e só o responsável aprova o aviso", async () => {
    auth.roles = ["CLIENT_OWNER"];
    vi.spyOn(api.landing, "privacy").mockResolvedValue(draftNotice);
    render(<ServiceSettingsPage />);

    expect(await screen.findByText("Não informado")).toBeVisible();
    expect(screen.getByText("Nenhuma janela cadastrada.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Aprovar como responsável" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Salvar rascunho do aviso" })).not.toBeInTheDocument();
    expect(screen.getByText(/não equivale a parecer jurídico/)).toBeVisible();
  });

  it("deixa a agência redigir, mas não aprovar", async () => {
    auth.roles = ["AGENCY_ADMIN"];
    vi.spyOn(api.landing, "privacy").mockRejectedValue(new ApiError("Aviso de privacidade ainda não criado", 404));
    render(<ServiceSettingsPage />);

    expect(await screen.findByRole("button", { name: "Salvar rascunho do aviso" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Aprovar como responsável" })).not.toBeInTheDocument();
    expect(screen.getByText("Não criado")).toBeVisible();
  });
});
