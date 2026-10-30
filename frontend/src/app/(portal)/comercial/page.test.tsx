import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CommercialPage from "./page";

const sales = vi.hoisted(() => ({
  list: vi.fn(), tasks: vi.fn(), briefing: vi.fn(), draftProposal: vi.fn(),
  create: vi.fn(), changeStage: vi.fn(), createTask: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ api: { sales } }));

describe("CommercialPage", () => {
  beforeEach(() => {
    sales.list.mockResolvedValue([{
      id: "lead-1", organization_id: "org-1", source: "MANUAL", stage: "NEW_LEAD",
      service_classification: "OUT_OF_SCOPE", classification_reason: "Fora do escopo",
      name: "Pessoa Teste", company: "Negócio Teste", email: "", whatsapp: "",
      business_type: "", goal: "Loja virtual", desired_timeline: "", additional_info: "",
      privacy_notice_version: null, consented_at: null, proposal_draft: null,
      created_at: "2026-10-08T00:00:00Z", updated_at: "2026-10-08T00:00:00Z",
    }]);
    sales.tasks.mockResolvedValue([]);
  });

  it("mostra triagem e impede proposta automática fora do escopo", async () => {
    render(<CommercialPage />);
    expect(await screen.findByRole("heading", { name: "Pipeline comercial" })).toBeVisible();
    fireEvent.click(await screen.findByRole("button", { name: /Negócio Teste/ }));
    await waitFor(() => expect(sales.tasks).toHaveBeenCalledWith("lead-1"));
    expect(screen.getByText("Fora do escopo")).toBeVisible();
    expect(screen.getByRole("button", { name: "Rascunho de proposta" })).toBeDisabled();
    expect(sales.draftProposal).not.toHaveBeenCalled();
  });
});
