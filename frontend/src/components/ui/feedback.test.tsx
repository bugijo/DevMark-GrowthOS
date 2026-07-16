import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/ui/feedback";

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
