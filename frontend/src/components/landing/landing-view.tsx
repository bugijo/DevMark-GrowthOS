"use client";

import { FormEvent, useState } from "react";

import type { LandingPriceItem, PublicIntake, PublicLanding } from "@/types/api";

const PERIODS = ["Manhã", "Tarde", "Sem preferência"] as const;
export const WEEKDAYS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"];
const HEARD_FROM: { value: string; label: string }[] = [
  { value: "INSTAGRAM_POST", label: "Post no Instagram" },
  { value: "INSTAGRAM_STORY", label: "Story no Instagram" },
  { value: "INDICACAO", label: "Indicação" },
  { value: "WHATSAPP_DIRETO", label: "WhatsApp" },
  { value: "OUTRO", label: "Outro" },
];
// Valores fixos exibidos na demonstração: os campos ficam bloqueados e nunca são enviados.
const DEMO_NAME = "Tutor de exemplo";
const DEMO_PHONE = "(00) 00000-0000";

export interface DemoLeadChoice {
  service_requested: string;
  price_item_label: string;
  preferred_period: string;
  preferred_weekday?: number;
  heard_from: string;
}

export interface RealLeadRequest extends DemoLeadChoice {
  contact_name: string;
  contact_phone: string;
  privacy_notice_version: number;
  privacy_accepted: boolean;
  website: string;
}

export function formatPrice(item: LandingPriceItem): string {
  if (item.price_cents === null || item.price_cents === undefined) return "Sob consulta";
  return (item.price_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/**
 * Link wa.me com mensagem pronta. Leva só o nome do estabelecimento, o serviço e o
 * porte escolhidos — nunca nome ou telefone do tutor. Quem envia é o próprio tutor.
 */
export function whatsAppLink(number: string, businessName: string, service: string, size: string): string {
  const what = service ? ` ${service.toLowerCase()}` : " um horário";
  const forWhom = size ? ` para um pet de porte ${size.toLowerCase()}` : "";
  const text = `Olá, ${businessName}! Gostaria de agendar${what}${forWhom}. Quais horários vocês têm disponíveis?`;
  return `https://wa.me/${number}?text=${encodeURIComponent(text)}`;
}

type FormMode = "real" | "demo" | "closed";

/**
 * Landing de um negócio cliente com dois caminhos de agendamento: WhatsApp (o tutor
 * abre a conversa e envia se quiser) e solicitação pelo site. O formulário só coleta
 * nome e telefone quando o backend declara a coleta aberta; em demonstração esses
 * campos ficam bloqueados com valores fictícios e não são enviados.
 */
export function LandingView({
  page,
  intake = null,
  preview = false,
  onDemoSubmit,
  onRealSubmit,
  onWhatsAppClick,
}: {
  page: PublicLanding;
  intake?: PublicIntake | null;
  preview?: boolean;
  onDemoSubmit?: (choice: DemoLeadChoice) => Promise<string>;
  onRealSubmit?: (request: RealLeadRequest) => Promise<string>;
  onWhatsAppClick?: () => void;
}) {
  const [service, setService] = useState("");
  const [size, setSize] = useState("");
  const [weekday, setWeekday] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const mode: FormMode = intake?.collection_open && intake.notice ? "real" : page.demo_mode ? "demo" : "closed";
  const availability = intake?.availability ?? [];
  const day = availability.find((item) => String(item.weekday) === weekday);
  const periods = day ? [...day.periods, "Sem preferência"] : PERIODS;
  const whatsapp = page.whatsapp_number ? whatsAppLink(page.whatsapp_number, page.business_name, service, size) : "";
  const canSubmit = !preview && !sending && (mode === "real" ? !!onRealSubmit : mode === "demo" && !!onDemoSubmit);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    // currentTarget is cleared once the handler yields, so keep the form reference.
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form)) as Record<string, string>;
    const choice: DemoLeadChoice = {
      service_requested: values.service_requested,
      price_item_label: values.price_item_label ?? "",
      preferred_period: values.preferred_period,
      heard_from: values.heard_from,
      ...(values.preferred_weekday ? { preferred_weekday: Number(values.preferred_weekday) } : {}),
    };
    setError(""); setStatus(""); setSending(true);
    try {
      if (mode === "real" && onRealSubmit && intake?.notice) {
        setStatus(await onRealSubmit({
          ...choice,
          contact_name: values.contact_name,
          contact_phone: values.contact_phone,
          privacy_notice_version: intake.notice.version,
          privacy_accepted: values.privacy_accepted === "on",
          website: values.website ?? "",
        }));
      } else if (onDemoSubmit) {
        setStatus(await onDemoSubmit(choice));
      }
      form.reset();
      setService(""); setSize(""); setWeekday("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível registrar o pedido.");
    } finally {
      setSending(false);
    }
  }

  const whatsappButton = (className: string, label: string) => (
    <a
      href={whatsapp}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => onWhatsAppClick?.()}
      className={`inline-flex min-h-12 items-center justify-center rounded-xl px-6 text-base font-bold shadow-sm ${className}`}
    >
      {label}
    </a>
  );
  const control = "min-h-11 rounded-xl border border-stone-300 bg-white px-3 font-normal disabled:bg-stone-100 disabled:text-slate-500";

  return (
    <div className="min-h-screen bg-stone-50 text-slate-900">
      {page.demo_mode ? (
        <div role="note" className="bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-900">
          Página demonstrativa{preview ? " (prévia interna, não publicada)" : ""}. Não informe dados pessoais; o formulário não coleta contato nem confirma agendamentos.
        </div>
      ) : null}

      <header className="bg-emerald-800 text-white">
        <div className="mx-auto grid max-w-5xl gap-6 px-5 py-14 md:grid-cols-[1.4fr_1fr] md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest text-emerald-200">{page.business_name}</p>
            <h1 className="mt-3 text-4xl font-bold leading-tight md:text-5xl">{page.headline}</h1>
            {page.subheadline ? <p className="mt-4 max-w-xl text-lg text-emerald-50">{page.subheadline}</p> : null}
            <div className="mt-8 flex flex-wrap gap-3">
              {whatsapp ? whatsappButton("bg-amber-400 text-emerald-950 hover:bg-amber-300", "Agendar pelo WhatsApp") : null}
              <a
                href="#agendar"
                className={`inline-flex min-h-12 items-center rounded-xl px-6 text-base font-bold shadow-sm ${whatsapp ? "border border-emerald-200 text-white hover:bg-emerald-700" : "bg-amber-400 text-emerald-950 hover:bg-amber-300"}`}
              >
                {whatsapp ? "Solicitar horário pelo site" : page.cta_label}
              </a>
            </div>
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
            {whatsapp ? (
              <div className="mt-6 rounded-2xl bg-emerald-50 p-4">
                <p className="font-semibold">Prefere falar agora?</p>
                <p className="mt-1 text-sm text-slate-700">
                  O WhatsApp abre com uma mensagem pronta{service || size ? " com o serviço e o porte escolhidos" : ""}. Você revisa e envia se quiser; o horário só vale depois de confirmado pela equipe.
                </p>
                <div className="mt-3">{whatsappButton("bg-emerald-700 text-white hover:bg-emerald-800", "Conversar no WhatsApp")}</div>
              </div>
            ) : null}
            {page.address ? <p className="mt-6 text-sm"><span className="font-semibold">Endereço:</span> {page.address}</p> : null}
            {page.contact_channel ? <p className="mt-2 text-sm"><span className="font-semibold">Atendimento:</span> {page.contact_channel}</p> : null}
          </div>

          <form className="grid gap-4" onSubmit={submit} aria-label="Solicitação de horário">
            {mode === "closed" ? (
              <p role="note" className="rounded-xl bg-stone-100 p-3 text-sm text-slate-700">
                Pedidos pelo site ainda não estão disponíveis.{whatsapp ? " Use o WhatsApp para falar com a equipe." : ""}
              </p>
            ) : null}
            <fieldset disabled={mode === "closed"} className="grid gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-1 text-sm font-semibold">
                  Nome do tutor
                  {mode === "real" ? (
                    <input name="contact_name" required minLength={2} maxLength={120} autoComplete="name" className={control} />
                  ) : (
                    <input value={DEMO_NAME} disabled readOnly aria-describedby="dados-bloqueados" className={control} />
                  )}
                </label>
                <label className="grid gap-1 text-sm font-semibold">
                  Telefone para contato
                  {mode === "real" ? (
                    <input name="contact_phone" type="tel" required inputMode="tel" maxLength={20} autoComplete="tel" className={control} />
                  ) : (
                    <input value={DEMO_PHONE} disabled readOnly aria-describedby="dados-bloqueados" className={control} />
                  )}
                </label>
              </div>
              {mode !== "real" ? (
                <p id="dados-bloqueados" className="-mt-2 text-xs text-slate-600">
                  Nome e telefone ficam bloqueados até a coleta real ser aprovada; nada disso é enviado.
                </p>
              ) : null}
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-1 text-sm font-semibold">
                  Serviço
                  <select name="service_requested" required value={service} onChange={(e) => setService(e.target.value)} className={control}>
                    <option value="">Escolha o serviço</option>
                    {page.service_options.map((option) => <option key={option}>{option}</option>)}
                  </select>
                </label>
                {page.price_items.length ? (
                  <label className="grid gap-1 text-sm font-semibold">
                    Porte do pet
                    <select name="price_item_label" required value={size} onChange={(e) => setSize(e.target.value)} className={control}>
                      <option value="">Escolha o porte</option>
                      {page.price_items.map((item) => <option key={item.label}>{item.label}</option>)}
                    </select>
                  </label>
                ) : null}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {availability.length ? (
                  <label className="grid gap-1 text-sm font-semibold">
                    Dia desejado
                    <select name="preferred_weekday" value={weekday} onChange={(e) => setWeekday(e.target.value)} className={control}>
                      <option value="">Sem preferência</option>
                      {availability.map((item) => <option key={item.weekday} value={item.weekday}>{WEEKDAYS[item.weekday]}</option>)}
                    </select>
                  </label>
                ) : null}
                <label className="grid gap-1 text-sm font-semibold">
                  Período desejado
                  <select name="preferred_period" required className={control} key={weekday}>
                    {periods.map((period) => <option key={period}>{period}</option>)}
                  </select>
                </label>
              </div>
              {!availability.length ? (
                <p className="-mt-2 text-xs text-slate-600">Os dias de atendimento ainda não foram informados; a equipe combina o dia com você.</p>
              ) : null}
              <label className="grid gap-1 text-sm font-semibold">
                Como conheceu
                <select name="heard_from" defaultValue="OUTRO" className={control}>
                  {HEARD_FROM.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              {mode === "real" && intake?.notice ? (
                <>
                  <details className="rounded-xl bg-stone-100 p-3 text-sm">
                    <summary className="cursor-pointer font-semibold">Aviso de privacidade (versão {intake.notice.version})</summary>
                    <p className="mt-2 whitespace-pre-line">{intake.notice.notice_text}</p>
                    <p className="mt-2 text-xs text-slate-600">
                      Responsável: {intake.notice.controller_name} · Contato: {intake.notice.privacy_contact} · Guardamos os dados por até {intake.notice.retention_days} dias.
                    </p>
                  </details>
                  <label className="flex gap-2 text-sm">
                    <input type="checkbox" name="privacy_accepted" required className="mt-1" />
                    Li e estou ciente do aviso de privacidade.
                  </label>
                  {/* Campo-isca para robôs: fora da tela e fora da navegação por teclado. */}
                  <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="absolute -left-[9999px] h-px w-px" />
                </>
              ) : (
                <label className="flex gap-2 text-sm">
                  <input type="checkbox" required className="mt-1" />
                  Entendo que esta é uma demonstração: nenhum dado pessoal é coletado e nada é agendado.
                </label>
              )}
              <button
                type="submit"
                disabled={!canSubmit}
                className="min-h-12 rounded-xl bg-emerald-700 px-4 font-bold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {preview ? "Envio desativado na prévia" : sending ? "Enviando…" : mode === "real" ? "Solicitar horário" : mode === "demo" ? "Registrar pedido demonstrativo" : "Indisponível"}
              </button>
            </fieldset>
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
