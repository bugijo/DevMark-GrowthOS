import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { formatPrice, LandingView, whatsAppLink } from "@/components/landing/landing-view";
import type { PublicIntake, PublicLanding } from "@/types/api";

const page: PublicLanding = {
  slug: "villa-pet-demo",
  business_name: "Villa Pet",
  headline: "Banho e tosa com cuidado",
  subheadline: "",
  cta_label: "Agendar banho e tosa",
  address: "Rua Expedicionário Solano, 510",
  contact_channel: "",
  whatsapp_number: "",
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
// Número fictício, só para teste.
const withWhatsApp: PublicLanding = { ...page, whatsapp_number: "5516900000000" };
const openIntake: PublicIntake = {
  collection_open: true,
  notice: {
    controller_name: "Villa Pet", privacy_contact: "privacidade@villapet.local", purpose: "Responder pedidos",
    legal_basis: "PROCEDIMENTOS_PRELIMINARES", data_categories: ["nome", "telefone"], retention_days: 90,
    notice_text: "Usamos nome e telefone só para responder.", version: 2,
  },
  availability: [{ weekday: 1, periods: ["Manhã"] }],
};

function chooseServiceAndSize() {
  fireEvent.change(screen.getByLabelText("Serviço"), { target: { value: "Banho e tosa" } });
  fireEvent.change(screen.getByLabelText("Porte do pet"), { target: { value: "Grande" } });
}

describe("LandingView", () => {
  it("na demonstração bloqueia nome e telefone com valores fictícios que não são enviados", () => {
    const { container } = render(<LandingView page={page} onDemoSubmit={vi.fn()} />);

    expect(screen.getByText("R$ 55,00")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome do tutor")).toBeDisabled();
    expect(screen.getByLabelText("Telefone para contato")).toBeDisabled();
    // Sem atributo name, esses campos nunca entram no FormData enviado.
    expect(container.querySelectorAll("input[name], textarea")).toHaveLength(0);
    expect(screen.getByRole("note")).toHaveTextContent("Não informe dados pessoais");
  });

  it("envia apenas escolhas fechadas no pedido demonstrativo", async () => {
    const onDemoSubmit = vi.fn().mockResolvedValue("Pedido demonstrativo registrado.");
    render(<LandingView page={page} onDemoSubmit={onDemoSubmit} />);

    chooseServiceAndSize();
    fireEvent.change(screen.getByLabelText("Período desejado"), { target: { value: "Tarde" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Registrar pedido demonstrativo" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("registrado"));
    expect(onDemoSubmit).toHaveBeenCalledWith({
      service_requested: "Banho e tosa",
      price_item_label: "Grande",
      preferred_period: "Tarde",
      heard_from: "OUTRO",
    });
    expect(screen.getByLabelText("Serviço")).toHaveValue("");
  });

  it("sem número configurado não mostra o botão do WhatsApp", () => {
    render(<LandingView page={page} />);
    expect(screen.queryByRole("link", { name: /WhatsApp/ })).not.toBeInTheDocument();
  });

  it("abre o WhatsApp do estabelecimento com serviço e porte, e só conta o clique", () => {
    const onWhatsAppClick = vi.fn();
    const onDemoSubmit = vi.fn();
    render(<LandingView page={withWhatsApp} onWhatsAppClick={onWhatsAppClick} onDemoSubmit={onDemoSubmit} />);

    const generic = screen.getByRole("link", { name: "Agendar pelo WhatsApp" });
    expect(generic.getAttribute("href")).toBe(whatsAppLink("5516900000000", "Villa Pet", "", ""));
    expect(decodeURIComponent(generic.getAttribute("href") ?? "")).toContain("agendar um horário");

    chooseServiceAndSize();
    const link = screen.getByRole("link", { name: "Conversar no WhatsApp" });
    const href = link.getAttribute("href") ?? "";
    expect(href.startsWith("https://wa.me/5516900000000?text=")).toBe(true);
    expect(decodeURIComponent(href)).toContain("Olá, Villa Pet! Gostaria de agendar banho e tosa para um pet de porte grande.");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");

    fireEvent.click(link);
    expect(onWhatsAppClick).toHaveBeenCalledTimes(1);
    expect(onDemoSubmit).not.toHaveBeenCalled();
  });

  it("com a coleta liberada envia contato, versão do aviso e dia, sem pôr dados pessoais no link", async () => {
    const onRealSubmit = vi.fn().mockResolvedValue("Pedido recebido.");
    render(<LandingView page={{ ...withWhatsApp, demo_mode: false }} intake={openIntake} onRealSubmit={onRealSubmit} />);

    fireEvent.change(screen.getByLabelText("Nome do tutor"), { target: { value: "Tutor Fictício" } });
    fireEvent.change(screen.getByLabelText("Telefone para contato"), { target: { value: "(11) 98888-7777" } });
    chooseServiceAndSize();
    expect(screen.getByLabelText("Dia desejado")).toHaveTextContent("Terça-feira");
    expect(screen.getByLabelText("Dia desejado")).not.toHaveTextContent("Segunda-feira");
    fireEvent.change(screen.getByLabelText("Dia desejado"), { target: { value: "1" } });
    expect(screen.getByLabelText("Período desejado")).not.toHaveTextContent("Tarde");

    for (const link of screen.getAllByRole("link", { name: /WhatsApp/ })) {
      const href = decodeURIComponent(link.getAttribute("href") ?? "");
      expect(href).not.toContain("Tutor Fictício");
      expect(href).not.toContain("98888");
    }

    fireEvent.click(screen.getByRole("checkbox", { name: /aviso de privacidade/ }));
    fireEvent.click(screen.getByRole("button", { name: "Solicitar horário" }));
    await waitFor(() => expect(onRealSubmit).toHaveBeenCalledTimes(1));
    expect(onRealSubmit).toHaveBeenCalledWith({
      service_requested: "Banho e tosa",
      price_item_label: "Grande",
      preferred_period: "Manhã",
      preferred_weekday: 1,
      heard_from: "OUTRO",
      contact_name: "Tutor Fictício",
      contact_phone: "(11) 98888-7777",
      privacy_notice_version: 2,
      privacy_accepted: true,
      website: "",
    });
  });

  it("fora da demonstração e sem coleta liberada, o formulário fica desativado e indica o WhatsApp", () => {
    render(<LandingView page={{ ...withWhatsApp, demo_mode: false }} intake={{ ...openIntake, collection_open: false }} onRealSubmit={vi.fn()} />);
    expect(screen.getByText(/Pedidos pelo site ainda não estão disponíveis. Use o WhatsApp/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Indisponível" })).toBeDisabled();
    expect(screen.getByLabelText("Nome do tutor")).toBeDisabled();
  });

  it("desativa o envio na prévia interna", () => {
    render(<LandingView page={page} preview />);
    expect(screen.getByRole("button", { name: "Envio desativado na prévia" })).toBeDisabled();
  });

  it("formata valores ausentes como sob consulta", () => {
    expect(formatPrice({ label: "Gato", price_cents: null })).toBe("Sob consulta");
  });
});
