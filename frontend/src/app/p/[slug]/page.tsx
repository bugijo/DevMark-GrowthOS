"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DemoLeadChoice, LandingView } from "@/components/landing/landing-view";
import type { PublicLanding } from "@/types/api";

const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? "/api/v1").replace(/\/$/, "");

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; page: PublicLanding }
  | { kind: "not_found" }
  | { kind: "unavailable" };

export default function PublicLandingPage() {
  const { slug } = useParams<{ slug: string }>();
  const [state, setState] = useState<LoadState>({ kind: "loading" });

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
      setState({ kind: "ready", page: (await response.json()) as PublicLanding });
    } catch {
      // Network failure (e.g. backend or proxy restarting) is not the same as "page does not exist".
      setState({ kind: "unavailable" });
    }
  }, [slug]);

  useEffect(() => { void load(); }, [load]);

  async function submitDemo(choice: DemoLeadChoice): Promise<string> {
    const response = await fetch(`${apiBase}/public/landing/${encodeURIComponent(slug)}/demo-leads`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(choice),
    });
    if (!response.ok) throw new Error("Não foi possível registrar o pedido. Tente mais tarde.");
    const receipt = (await response.json()) as { message: string };
    return receipt.message;
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
  return <LandingView page={state.page} onDemoSubmit={submitDemo} />;
}
