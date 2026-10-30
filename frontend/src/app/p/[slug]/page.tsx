"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DemoLeadChoice, LandingView, RealLeadRequest } from "@/components/landing/landing-view";
import type { PublicIntake, PublicLanding } from "@/types/api";

const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? "/api/v1").replace(/\/$/, "");

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; page: PublicLanding; intake: PublicIntake | null }
  | { kind: "not_found" }
  | { kind: "unavailable" };

export default function PublicLandingPage() {
  const { slug } = useParams<{ slug: string }>();
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  // Sem o intake o formulário fica no modo mais restrito (demonstração ou fechado).
  const loadIntake = useCallback(async (): Promise<PublicIntake | null> => {
    try {
      const response = await fetch(`${apiBase}/public/landing/${encodeURIComponent(slug)}/intake`, {
        credentials: "omit",
        cache: "no-store",
      });
      return response.ok ? ((await response.json()) as PublicIntake) : null;
    } catch {
      return null;
    }
  }, [slug]);

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      // no-store: approval and revocation must be reflected on every visit.
      const response = await fetch(`${apiBase}/public/landing/${encodeURIComponent(slug)}`, {
        credentials: "omit",
        cache: "no-store",
      });
      if (response.status === 404) return setState({ kind: "not_found" });
      if (!response.ok) return setState({ kind: "unavailable" });
      const page = (await response.json()) as PublicLanding;
      setState({ kind: "ready", page, intake: await loadIntake() });
    } catch {
      // Network failure (e.g. backend or proxy restarting) is not the same as "page does not exist".
      setState({ kind: "unavailable" });
    }
  }, [slug, loadIntake]);

  useEffect(() => { void load(); }, [load]);

  async function post(path: string, body: unknown): Promise<string> {
    const response = await fetch(`${apiBase}/public/landing/${encodeURIComponent(slug)}/${path}`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const detail = await response.json().then((data: { detail?: unknown }) => data.detail, () => null);
      throw new Error(typeof detail === "string" ? detail : "Não foi possível registrar o pedido. Tente mais tarde.");
    }
    const receipt = (await response.json()) as { message: string };
    return receipt.message;
  }

  const submitDemo = (choice: DemoLeadChoice) => post("demo-leads", choice);
  const submitReal = (request: RealLeadRequest) => post("requests", request);

  function countWhatsAppClick() {
    // Só soma um clique no dia; não envia nada que identifique o visitante.
    void fetch(`${apiBase}/public/landing/${encodeURIComponent(slug)}/events`, {
      method: "POST",
      credentials: "omit",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: "whatsapp_click" }),
    }).catch(() => undefined);
  }

  if (state.kind === "not_found") {
    return (
      <main className="mx-auto grid min-h-screen max-w-xl place-content-center gap-2 px-5 text-center">
        <h1 className="text-2xl font-bold">Página indisponível</h1>
        <p className="text-slate-600">Esta página não existe ou ainda aguarda aprovação.</p>
      </main>
    );
  }
  if (state.kind === "unavailable") {
    return (
      <main className="mx-auto grid min-h-screen max-w-xl place-content-center gap-3 px-5 text-center">
        <h1 className="text-2xl font-bold">Não foi possível carregar a página</h1>
        <p className="text-slate-600">O serviço está temporariamente indisponível. Tente novamente em instantes.</p>
        <button
          type="button"
          onClick={() => void load()}
          className="mx-auto min-h-11 rounded-xl bg-emerald-700 px-5 font-semibold text-white hover:bg-emerald-800"
        >
          Tentar novamente
        </button>
      </main>
    );
  }
  if (state.kind === "loading") {
    return <main className="grid min-h-screen place-content-center text-slate-600">Carregando…</main>;
  }
  return (
    <LandingView
      page={state.page}
      intake={state.intake}
      onDemoSubmit={submitDemo}
      onRealSubmit={submitReal}
      onWhatsAppClick={countWhatsAppClick}
    />
  );
}
