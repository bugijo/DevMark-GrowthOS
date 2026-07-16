import { describe, expect, it } from "vitest";

import { navigationForRoles } from "@/lib/navigation";

describe("navigationForRoles", () => {
  it("mostra operação e auditoria para a administração", () => {
    const labels = navigationForRoles(["AGENCY_ADMIN"]).map((item) => item.label);
    expect(labels).toContain("Clientes");
    expect(labels).toContain("Marca e presets");
    expect(labels).toContain("Planejamento");
    expect(labels).toContain("Biblioteca de mídia");
    expect(labels).toContain("Conteúdos");
    expect(labels).toContain("Relatórios");
    expect(labels).toContain("Registros");
    expect(labels).toContain("Equipe");
  });

  it("mantém o portal do revisor simples", () => {
    const labels = navigationForRoles(["CLIENT_REVIEWER"]).map((item) => item.label);
    expect(labels).toEqual([
      "Início",
      "Marca e presets",
      "Planejamento",
      "Biblioteca de mídia",
      "Conteúdos",
      "Aprovações",
      "Relatórios",
      "Notificações",
      "Registros",
    ]);
  });

  it("leva o designer às revisões visuais sem liberar decisões do cliente", () => {
    const labels = navigationForRoles(["DESIGNER"]).map((item) => item.label);
    expect(labels).toContain("Aprovações");
    expect(labels).not.toContain("Equipe");
  });

  it("permite ao responsável do cliente gerir equipe e consultar histórico limitado", () => {
    const labels = navigationForRoles(["CLIENT_OWNER"]).map((item) => item.label);
    expect(labels).toContain("Equipe");
    expect(labels).toContain("Registros");
  });
});
