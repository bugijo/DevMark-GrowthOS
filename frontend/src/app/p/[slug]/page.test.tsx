import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import PublicLandingPage from "@/app/p/[slug]/page";

vi.mock("next/navigation", () => ({ useParams: () => ({ slug: "villa-pet" }) }));

const landing = {
  slug: "villa-pet",
  business_name: "Villa Pet",
  headline: "Banho e tosa com cuidado",
  subheadline: "",
  cta_label: "Agendar banho e tosa",
  address: "",
  contact_channel: "",
  whatsapp_number: "",
  highlights: [],
  service_options: ["Banho"],
  price_items: [{ label: "Pequeno", price_cents: 5500 }],
  price_disclaimer: "Valores de referência.",
  demo_mode: true,
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.unstubAllGlobals());

describe("PublicLandingPage", () => {
  it("mostra 'não existe ou aguarda aprovação' somente para 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(404, { detail: "Página não encontrada" })));
    render(<PublicLandingPage />);
    expect(await screen.findByText("Esta página não existe ou ainda aguarda aprovação.")).toBeInTheDocument();
  });

  it("trata falha de rede como indisponibilidade temporária e recupera ao tentar de novo", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(jsonResponse(200, landing));
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicLandingPage />);

    expect(await screen.findByText("Não foi possível carregar a página")).toBeInTheDocument();
    expect(screen.queryByText(/aguarda aprovação/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("heading", { name: "Banho e tosa com cuidado" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/public/landing/villa-pet",
      expect.objectContaining({ credentials: "omit", cache: "no-store" }),
    );
  });

  it("trata 503 do proxy como indisponibilidade, não como página inexistente", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(503, { detail: "API indisponível" })));
    render(<PublicLandingPage />);
    expect(await screen.findByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("conta o clique no WhatsApp sem credenciais e sem dados do visitante", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, { ...landing, whatsapp_number: "5516900000000" }))
      .mockResolvedValueOnce(jsonResponse(200, { collection_open: false, notice: null, availability: [] }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicLandingPage />);

    const link = await screen.findByRole("link", { name: "Agendar pelo WhatsApp" });
    link.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(link);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/public/landing/villa-pet/events",
      expect.objectContaining({ method: "POST", credentials: "omit", body: JSON.stringify({ event: "whatsapp_click" }) }),
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
