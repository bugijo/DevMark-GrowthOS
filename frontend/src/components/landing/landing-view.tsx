"use client";

import { FormEvent, useState } from "react";

import type { LandingPriceItem, PublicLanding } from "@/types/api";

const PERIODS = ["Manhã", "Tarde", "Sábado", "Sem preferência"] as const;
const HEARD_FROM: { value: string; label: string }[] = [
  { value: "INSTAGRAM_POST", label: "Post no Instagram" },
  { value: "INSTAGRAM_STORY", label: "Story no Instagram" },
  { value: "INDICACAO", label: "Indicação" },
  { value: "WHATSAPP_DIRETO", label: "WhatsApp" },
  { value: "OUTRO", label: "Outro" },
];

export interface DemoLeadChoice {
  service_requested: string;
  price_item_label: string;
  preferred_period: string;
  heard_from: string;
}

export function formatPrice(item: LandingPriceItem): string {
  if (item.price_cents === null || item.price_cents === undefined) return "Sob consulta";
  return (item.price_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/**
 * Renderiza uma landing page de negócio cliente. O formulário é demonstrativo:
 * só oferece escolhas fechadas e não tem nenhum campo de dado pessoal.
 */
export function LandingView({
  page,
  preview = false,
  onDemoSubmit,
}: {
  page: PublicLanding;
  preview?: boolean;
  onDemoSubmit?: (choice: DemoLeadChoice) => Promise<string>;
}) {
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onDemoSubmit) return;
    // currentTarget is cleared once the handler yields, so keep the form reference.
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form)) as unknown as DemoLeadChoice;
    setError("");
    setStatus("");
    setSending(true);
    try {
      setStatus(await onDemoSubmit(values));
      form.reset();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível registrar o pedido.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 text-slate-900">
      {page.demo_mode ? (
        <div role="note" className="bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-900">
          Página demonstrativa{preview ? " (prévia interna, não publicada)" : ""}. Não informe dados pessoais; nenhum contato será feito.
        </div>
      ) : null}

      <header className="bg-emerald-800 text-white">
        <div className="mx-auto grid max-w-5xl gap-6 px-5 py-14 md:grid-cols-[1.4fr_1fr] md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest text-emerald-200">{page.business_name}</p>
            <h1 className="mt-3 text-4xl font-bold leading-tight md:text-5xl">{page.headline}</h1>
            {page.subheadline ? <p className="mt-4 max-w-xl text-lg text-emerald-50">{page.subheadline}</p> : null}
            <a
              href="#agendar"
              className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-amber-400 px-6 text-base font-bold text-emerald-950 shadow-sm hover:bg-amber-300"
            >
              {page.cta_label}
            </a>
          </div>
          {page.highlights.length ? (
            <ul className="grid gap-3 rounded-2xl bg-emerald-900/60 p-6">
              {page.highlights.map((item) => (
                <li key={item} className="flex gap-3 text-emerald-50">
                  <span aria-hidden="true" className="mt-1 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-12 px-5 py-12">
        {page.price_items.length ? (
          <section aria-labelledby="precos">
            <h2 id="precos" className="text-2xl font-bold">Valores de referência por porte</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {page.price_items.map((item) => (
                <div key={item.label} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                  <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">{item.label}</p>
                  <p className="mt-2 text-3xl font-bold">{formatPrice(item)}</p>
                  {item.note ? <p className="mt-2 text-sm text-slate-600">{item.note}</p> : null}
                </div>
              ))}
            </div>
            {page.price_disclaimer ? <p className="mt-4 text-sm text-slate-600">{page.price_disclaimer}</p> : null}
          </section>
        ) : null}

        <section id="agendar" aria-labelledby="agendar-titulo" className="grid gap-8 rounded-3xl bg-white p-6 shadow-sm md:grid-cols-2 md:p-10">
          <div>
            <h2 id="agendar-titulo" className="text-2xl font-bold">{page.cta_label}</h2>
            <p className="mt-3 text-slate-600">
              Escolha o serviço, o porte e o melhor período. A equipe confirma disponibilidade, preço vigente e condições antes de qualquer agendamento.
            </p>
            {page.address ? <p className="mt-6 text-sm"><span className="font-semibold">Endereço:</span> {page.address}</p> : null}
            {page.contact_channel ? <p className="mt-2 text-sm"><span className="font-semibold">Atendimento:</span> {page.contact_channel}</p> : null}
          </div>
          <form className="grid gap-4" onSubmit={submit} aria-label="Pedido demonstrativo de agendamento">
            <label className="grid gap-1 text-sm font-semibold">
              Serviço
              <select name="service_requested" required className="min-h-11 rounded-xl border border-stone-300 bg-white px-3 font-normal">
                {page.service_options.map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
            {page.price_items.length ? (
              <label className="grid gap-1 text-sm font-semibold">
                Porte do pet
                <select name="price_item_label" required className="min-h-11 rounded-xl border border-stone-300 bg-white px-3 font-normal">
                  {page.price_items.map((item) => <option key={item.label}>{item.label}</option>)}
                </select>
              </label>
            ) : null}
            <label className="grid gap-1 text-sm font-semibold">
              Melhor período
              <select name="preferred_period" required className="min-h-11 rounded-xl border border-stone-300 bg-white px-3 font-normal">
                {PERIODS.map((period) => <option key={period}>{period}</option>)}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Como conheceu
              <select name="heard_from" className="min-h-11 rounded-xl border border-stone-300 bg-white px-3 font-normal">
                {HEARD_FROM.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <button
              type="submit"
              disabled={preview || sending || !onDemoSubmit}
              className="min-h-12 rounded-xl bg-emerald-700 px-4 font-bold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {preview ? "Envio desativado na prévia" : sending ? "Registrando…" : "Registrar pedido demonstrativo"}
            </button>
            {status ? <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">{status}</p> : null}
            {error ? <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
          </form>
        </section>
      </main>

      <footer className="border-t border-stone-200 py-6 text-center text-xs text-slate-500">
        {page.business_name} · página criada com DevMark GrowthOS
      </footer>
    </div>
  );
}
