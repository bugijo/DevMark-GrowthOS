"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";

interface QuoteConfig { enabled: boolean; privacy_notice_url?: string | null; privacy_notice_version?: string | null; }
const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? "/api/v1").replace(/\/$/, "");

export default function QuotePage() {
  const [config, setConfig] = useState<QuoteConfig | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const idempotencyKey = useRef<string | null>(null);
  useEffect(() => { void fetch(`${apiBase}/public/quote-requests/config`, { credentials: "omit" }).then(r => r.json()).then(setConfig).catch(() => setConfig({ enabled: false })); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const values = Object.fromEntries(new FormData(form));
    setError(""); setStatus("");
    try {
      idempotencyKey.current ??= crypto.randomUUID();
      const response = await fetch(`${apiBase}/public/quote-requests`, { method: "POST", credentials: "omit", headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey.current }, body: JSON.stringify({ ...values, privacy_consent: values.privacy_consent === "on" }) });
      if (!response.ok) throw new Error("Não foi possível enviar a solicitação. Tente mais tarde.");
      idempotencyKey.current = null;
      setStatus("Solicitação recebida. A equipe fará a triagem; nenhum serviço foi contratado."); form.reset();
    } catch (e) { setError(e instanceof Error ? e.message : "Falha de conexão."); }
  }
  return <main className="mx-auto grid min-h-screen max-w-3xl content-start gap-6 px-5 py-12"><PageHeader eyebrow="DevMarkia" title="Solicite um orçamento" description="Landing pages e sites institucionais com escopo alinhado antes da proposta." />{error ? <Alert>{error}</Alert> : null}{status ? <Alert tone="success">{status}</Alert> : null}{config && !config.enabled ? <Card><h2 className="font-bold">Solicitações online temporariamente indisponíveis</h2><p className="mt-2 text-sm text-slate-600">Use os canais de contato já publicados pela DevMarkia. Nenhum dado foi coletado por este formulário.</p></Card> : null}{config?.enabled ? <Card><form className="grid gap-4" onSubmit={submit}><Field label="Nome" required><Input name="name" minLength={2} maxLength={160} required /></Field><Field label="Empresa"><Input name="company" maxLength={160} /></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="E-mail"><Input name="email" type="email" maxLength={320} /></Field><Field label="WhatsApp"><Input name="whatsapp" maxLength={24} /></Field></div><Field label="Segmento"><Input name="business_type" maxLength={120} /></Field><Field label="O que você precisa?" required><Textarea name="goal" minLength={3} maxLength={2000} required /></Field><Field label="Prazo desejado"><Input name="desired_timeline" maxLength={160} /></Field><Field label="Informações adicionais"><Textarea name="additional_info" maxLength={2000} /></Field><label className="flex items-start gap-2 text-sm"><input type="checkbox" name="privacy_consent" required className="mt-1" /><span>Li e aceito o <a className="underline" href={config.privacy_notice_url ?? "#"} target="_blank" rel="noreferrer">aviso de privacidade</a> (versão {config.privacy_notice_version}).</span></label><input name="honeypot" tabIndex={-1} autoComplete="off" aria-hidden="true" className="absolute -left-[10000px]" /><button className="min-h-11 rounded-xl bg-emerald-700 px-4 font-semibold text-white">Enviar solicitação</button></form></Card> : null}</main>;
}
