import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Breadcrumbs } from "@/components/ui/breadcrumbs";

describe("Breadcrumbs", () => {
  it("expõe a trilha e identifica a página atual sem transformá-la em link", () => {
    render(
      <Breadcrumbs
        items={[
          { label: "Início", href: "/dashboard" },
          { label: "Clientes", href: "/clientes" },
          { label: "Novo cliente" },
        ]}
      />,
    );

    expect(
      screen.getByRole("navigation", { name: "Navegação estrutural" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Início" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Clientes" })).toHaveAttribute(
      "href",
      "/clientes",
    );
    expect(screen.getByText("Novo cliente")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("link", { name: "Novo cliente" })).not.toBeInTheDocument();
  });

  it("não cria um landmark vazio", () => {
    const { container } = render(<Breadcrumbs items={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
