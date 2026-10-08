import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import QuotePage from "./page";

describe("QuotePage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("não coleta dados enquanto o intake público estiver desligado", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ json: async () => ({ enabled: false }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuotePage />);
    expect(await screen.findByText("Solicitações online temporariamente indisponíveis")).toBeVisible();
    expect(screen.queryByRole("textbox", { name: "Nome" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/public/quote-requests/config", { credentials: "omit" });
  });

  it("envia consentimento e dados somente para a rota pública configurada", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ json: async () => ({ enabled: true, privacy_notice_url: "https://example.test/privacy", privacy_notice_version: "v1" }) })
      .mockResolvedValueOnce({ ok: true, status: 202 });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", { randomUUID: () => "quote-request-key" });
    render(<QuotePage />);
    const name = await screen.findByLabelText(/Nome/);
    fireEvent.change(name, { target: { value: "Pessoa de Teste" } });
    fireEvent.change(screen.getByLabelText(/O que você precisa/), { target: { value: "Landing page" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "pessoa@example.test" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.submit(screen.getByRole("button", { name: "Enviar solicitação" }).closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [url, request] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(url).toBe("/api/v1/public/quote-requests");
    expect(request.credentials).toBe("omit");
    expect(request.headers).toMatchObject({ "Idempotency-Key": "quote-request-key" });
    expect(JSON.parse(String(request.body))).toMatchObject({
      name: "Pessoa de Teste", email: "pessoa@example.test", privacy_consent: true,
    });
    expect(await screen.findByText(/Solicitação recebida/)).toBeVisible();
  });
});
