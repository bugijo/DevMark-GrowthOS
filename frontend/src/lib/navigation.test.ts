import { describe, expect, it } from "vitest";

import { navigationForRoles } from "@/lib/navigation";

describe("navigationForRoles", () => {
  it("mostra operação e auditoria para a administração", () => {
    const labels = navigationForRoles(["AGENCY_ADMIN"]).map((item) => item.label);
    expect(labels).toContain("Clientes");
    expect(labels).toContain("Conteúdos");
    expect(labels).toContain("Registros");
    expect(labels).toContain("Equipe");
  });

  it("mantém o portal do revisor simples", () => {
    const labels = navigationForRoles(["CLIENT_REVIEWER"]).map((item) => item.label);
    expect(labels).toEqual(["Início", "Conteúdos", "Aprovações", "Notificações"]);
  });

  it("permite ao responsável do cliente gerir apenas sua equipe", () => {
    const labels = navigationForRoles(["CLIENT_OWNER"]).map((item) => item.label);
    expect(labels).toContain("Equipe");
    expect(labels).not.toContain("Registros");
  });
});
