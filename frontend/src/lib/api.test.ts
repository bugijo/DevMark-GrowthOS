import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  api,
  apiRequest,
  clearStoredSession,
  extractItems,
  setStoredOrganizationId,
  storeCsrfToken,
} from "@/lib/api";

describe("apiRequest", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("envia organização, CSRF e cookies nas mutações", async () => {
    setStoredOrganizationId("org-123");
    storeCsrfToken("csrf-456");
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: "business-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );

    await apiRequest("/businesses", {
      method: "POST",
      body: JSON.stringify({ name: "Clínica", segment: "Veterinária" }),
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(url).toBe("/api/v1/businesses");
    expect(init?.credentials).toBe("include");
    expect(headers.get("X-Organization-ID")).toBe("org-123");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-456");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("converte um problema HTTP em mensagem simples", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Papel sem permissão" }), {
        status: 403,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiRequest("/audit-logs")).rejects.toEqual(
      expect.objectContaining<ApiError>({
        name: "ApiError",
        message: "Papel sem permissão",
        status: 403,
      }),
    );
  });

  it("cria uma revisão real com os campos editados", async () => {
    storeCsrfToken("csrf-456");
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: "content-1", status: "DRAFT" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    await api.contents.createRevision("content-1", {
      title: "Novo título",
      caption: "Nova legenda",
      cta: "Agende agora",
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/contents/content-1/revisions");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      title: "Novo título",
      caption: "Nova legenda",
      cta: "Agende agora",
    });
  });

  it("envia token de convite apenas no corpo do endpoint público", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          organization: { id: "org-1", name: "Organização" },
          role: "CLIENT_REVIEWER",
          masked_email: "p***@example.com",
          expires_at: "2026-07-16T12:00:00Z",
          requires_account_setup: false,
          business_id: null,
          business_name: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    await api.auth.inspectInvitation("fragment-token-value");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/auth/invitations/inspect");
    expect(String(url)).not.toContain("fragment-token-value");
    expect(JSON.parse(String(init?.body))).toEqual({ token: "fragment-token-value" });
  });
});

describe("extractItems", () => {
  it("aceita lista direta e envelope paginado", () => {
    expect(extractItems([{ id: "1" }])).toEqual([{ id: "1" }]);
    expect(extractItems({ items: [{ id: "2" }], total: 1 })).toEqual([
      { id: "2" },
    ]);
  });
});

describe("clearStoredSession", () => {
  it("remove o contexto local da sessão", () => {
    setStoredOrganizationId("org-123");
    storeCsrfToken("csrf-456");
    clearStoredSession();
    expect(window.localStorage.getItem("growthos_organization_id")).toBeNull();
    expect(window.sessionStorage.getItem("growthos_csrf_token")).toBeNull();
  });
});
