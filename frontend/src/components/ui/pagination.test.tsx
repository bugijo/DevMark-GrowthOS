import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination, paginationTokens } from "@/components/ui/pagination";

describe("Pagination", () => {
  it("identifica a página atual e oferece navegação por botões nomeados", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();
    render(
      <Pagination page={4} totalPages={10} onPageChange={onPageChange} />,
    );

    expect(screen.getByRole("navigation", { name: "Paginação" })).toBeVisible();
    expect(screen.getByText("Página 4 de 10")).toHaveClass("sr-only");
    expect(screen.getByRole("button", { name: "Página 4, atual" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: "Anterior" }));
    await user.click(screen.getByRole("button", { name: "Próxima" }));
    await user.click(screen.getByRole("button", { name: "Ir para a página 10" }));

    expect(onPageChange).toHaveBeenNthCalledWith(1, 3);
    expect(onPageChange).toHaveBeenNthCalledWith(2, 5);
    expect(onPageChange).toHaveBeenNthCalledWith(3, 10);
  });

  it("desabilita os limites e omite paginação de uma única página", () => {
    const { rerender } = render(
      <Pagination page={1} totalPages={3} onPageChange={() => undefined} />,
    );

    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeEnabled();

    rerender(
      <Pagination page={1} totalPages={1} onPageChange={() => undefined} />,
    );
    expect(screen.queryByRole("navigation", { name: "Paginação" })).not.toBeInTheDocument();
  });

  it("resume intervalos longos sem omitir primeira, atual e última página", () => {
    expect(paginationTokens(50, 100)).toEqual([
      1,
      "start-ellipsis",
      49,
      50,
      51,
      "end-ellipsis",
      100,
    ]);
  });
});
