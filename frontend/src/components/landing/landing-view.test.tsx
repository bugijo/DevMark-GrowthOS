import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { formatPrice, LandingView } from "@/components/landing/landing-view";
import type { PublicLanding } from "@/types/api";

const page: PublicLanding = {
  slug: "villa-pet-demo",
  business_name: "Villa Pet",
  headline: "Banho e tosa com cuidado",
  subheadline: "",
  cta_label: "Agendar banho e tosa",
  address: "Rua Expedicionário Solano, 510",
  contact_channel: "",
  highlights: [],
  service_options: ["Banho", "Banho e tosa"],
  price_items: [
    { label: "Pequeno", price_cents: 5500 },
    { label: "Médio", price_cents: 7500 },
    { label: "Grande", price_cents: 9500 },
  ],
  price_disclaimer: "Valores de referência.",
  demo_mode: true,
};

describe("LandingView", () => {
  it("mostra preços de referência e não oferece campo de texto para dados pessoais", () => {
    const { container } = render(<LandingView page={page} onDemoSubmit={vi.fn()} />);

    expect(screen.getByText("R$ 55,00")).toBeInTheDocument();
    expect(screen.getByText("R$ 95,00")).toBeInTheDocument();
    expect(container.querySelectorAll("input, textarea")).toHaveLength(0);
    expect(screen.getByRole("note")).toHaveTextContent("Não informe dados pessoais");
  });

  it("envia apenas escolhas fechadas", async () => {
    const onDemoSubmit = vi.fn().mockResolvedValue("Pedido demonstrativo registrado.");
    render(<LandingView page={page} onDemoSubmit={onDemoSubmit} />);

    fireEvent.change(screen.getByLabelText("Melhor período"), { target: { value: "Tarde" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar pedido demonstrativo" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("registrado"));
    expect(screen.getByLabelText("Melhor período")).toHaveValue("Manhã");
    expect(onDemoSubmit).toHaveBeenCalledWith({
      service_requested: "Banho",
      price_item_label: "Pequeno",
      preferred_period: "Tarde",
      heard_from: "INSTAGRAM_POST",
    });
  });

  it("desativa o envio na prévia interna", () => {
    render(<LandingView page={page} preview />);
    expect(screen.getByRole("button", { name: "Envio desativado na prévia" })).toBeDisabled();
  });

  it("formata valores ausentes como sob consulta", () => {
    expect(formatPrice({ label: "Gato", price_cents: null })).toBe("Sob consulta");
  });
});
