import { describe, expect, it } from "vitest";

import { navigationForRoles } from "@/lib/navigation";

describe("navigationForRoles", () => {
  it("mostra operação e auditoria para a administração", () => {
    const labels = navigationForRoles(["AGENCY_ADMIN"]).map((item) => item.label);
    expect(labels).toContain("Clientes");
    expect(labels).toContain("Conteúdos");
    expect(labels).toContain("Registros");
  });

  it("mantém o portal do revisor simples", () => {
    const labels = navigationForRoles(["CLIENT_REVIEWER"]).map((item) => item.label);
    expect(labels).toEqual(["Início", "Conteúdos", "Aprovações", "Notificações"]);
  });
});
