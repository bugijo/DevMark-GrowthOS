import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Alert, EmptyState } from "@/components/ui/feedback";

describe("Alert", () => {
  it("anuncia erros imediatamente", () => {
    render(<Alert>Não foi possível salvar.</Alert>);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveAttribute("aria-atomic", "true");
  });

  it("anuncia informações e sucesso sem interromper a leitura", () => {
    const { rerender } = render(<Alert tone="info">Processamento iniciado.</Alert>);

    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");

    rerender(<Alert tone="success">Alterações salvas.</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Alterações salvas.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("explica o próximo passo", () => {
    render(
      <EmptyState
        title="Nenhum conteúdo"
        description="Gere o primeiro rascunho para começar."
      />,
    );
    expect(screen.getByRole("heading", { name: "Nenhum conteúdo" })).toBeVisible();
    expect(screen.getByText("Gere o primeiro rascunho para começar.")).toBeVisible();
  });
});
