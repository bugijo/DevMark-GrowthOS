"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { formatPrice } from "@/components/landing/landing-view";
import {
  hasAnyRole,
  LEAD_MANAGERS,
  LEAD_PRIVACY_OPERATORS,
  useBusinessSelection,
} from "@/components/landing/use-business-selection";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type {
  BusinessLead,
  BusinessLeadHistoryEntry,
  BusinessLeadSource,
  BusinessLeadStatus,
  BusinessLeadSummary,
  LandingPage,
} from "@/types/api";

const STATUS_LABEL: Record<BusinessLeadStatus, string> = {
  NOVO: "Novo", AGUARDANDO_DADOS: "Aguardando dados", HORARIO_OFERTADO: "Horário ofertado",
  CONFIRMADO: "Confirmado", REALIZADO: "Realizado", CANCELADO: "Cancelado", NAO_COMPARECEU: "Não compareceu",
};
const NEXT_STATUS: Record<BusinessLeadStatus, BusinessLeadStatus[]> = {
  NOVO: ["AGUARDANDO_DADOS", "HORARIO_OFERTADO", "CONFIRMADO", "CANCELADO"],
  AGUARDANDO_DADOS: ["HORARIO_OFERTADO", "CONFIRMADO", "CANCELADO"],
  HORARIO_OFERTADO: ["CONFIRMADO", "AGUARDANDO_DADOS", "CANCELADO"],
  CONFIRMADO: ["REALIZADO", "NAO_COMPARECEU", "CANCELADO"],
  REALIZADO: [], CANCELADO: [], NAO_COMPARECEU: [],
};
const SOURCE_LABEL: Record<BusinessLeadSource, string> = {
  LANDING_DEMO: "Landing (demo)", LANDING_PAGE: "Landing", INSTAGRAM_POST: "Post Instagram",
  INSTAGRAM_STORY: "Story Instagram", INDICACAO: "Indicação", WHATSAPP_DIRETO: "WhatsApp direto", OUTRO: "Outro",
};
const ACTION_LABEL: Record<string, string> = {
  "business_lead.created": "Registrado pela equipe", "business_lead.demo_created": "Recebido pela página (demo)",
  "business_lead.received": "Recebido pela página", "business_lead.updated": "Atualizado",
  "business_lead.exported": "Dados exportados", "business_lead.anonymized": "Anonimizado",
};

function describeChanges(changes: Record<string, unknown>): string {
  const status = typeof changes.status === "string" ? changes.status.split("->") : null;
  const parts = status?.length === 2
    ? [`${STATUS_LABEL[status[0] as BusinessLeadStatus] ?? status[0]} → ${STATUS_LABEL[status[1] as BusinessLeadStatus] ?? status[1]}`]
    : [];
  if (changes.next_action) parts.push("próxima ação");
  if (changes.notes) parts.push("observações");
  return parts.join(", ");
}

const FILTERS = [
  { value: "abertos", label: "Precisam de resposta" },
  { value: "todos", label: "Todos" },
] as const;

function downloadJson(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url; link.download = name; link.click();
  URL.revokeObjectURL(url);
}

export default function RequestsPage() {
  const { roles } = useAuth();
  const canManage = hasAnyRole(roles, LEAD_MANAGERS);
  const canPrivacy = hasAnyRole(roles, LEAD_PRIVACY_OPERATORS);
  const selection = useBusinessSelection();
  const { businessId } = selection;
  const [page, setPage] = useState<LandingPage | null>(null);
  const [leads, setLeads] = useState<BusinessLead[]>([]);
  const [summary, setSummary] = useState<BusinessLeadSummary | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["value"]>("abertos");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<{ leadId: string; entries: BusinessLeadHistoryEntry[] } | null>(null);

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setBusy(true); setError("");
    try {
      const [nextLeads, nextSummary] = await Promise.all([api.landing.leads(id), api.landing.summary(id)]);
      setLeads(nextLeads); setSummary(nextSummary);
      setPage(await api.landing.get(id).catch(() => null));
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar pedidos."); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(businessId); }, [businessId, load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setError(""); setMessage(""); setHistory(null);
    try { await action(); setMessage(success); await load(businessId); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível concluir."); }
  }

  async function createLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form)) as Record<string, string>;
    await run(async () => {
      await api.landing.createLead(businessId, {
        source: values.source as BusinessLeadSource, service_requested: values.service_requested,
        price_item_label: values.price_item_label ?? "", preferred_period: values.preferred_period, notes: values.notes,
      });
      form.reset();
    }, "Pedido demonstrativo registrado.");
  }

  const visible = filter === "todos"
    ? leads
    : leads.filter((lead) => lead.status === "NOVO" || lead.status === "AGUARDANDO_DADOS");

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Atendimento"
        title="Solicitações de banho e tosa"
        description="Pedidos recebidos pela página e registrados pela equipe. A resposta ao tutor é sempre feita por uma pessoa; nada é enviado automaticamente."
      />
      {selection.error || error ? <Alert>{selection.error || error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}

      {selection.businesses.length > 1 ? (
        <Card>
          <Field label="Cliente">
            <Select value={businessId} onChange={(e) => selection.setBusinessId(e.target.value)}>
              {selection.businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </Select>
          </Field>
        </Card>
      ) : null}
      {selection.loading ? <LoadingState label="Carregando…" /> : null}
      {!selection.loading && !businessId ? <EmptyState title="Nenhum cliente" description="Não há cliente disponível para este acesso." /> : null}

      {businessId && summary ? (
        <dl className="grid grid-cols-2 gap-3 text-center sm:grid-cols-5">
          <div className="rounded-xl bg-white p-3 shadow-sm"><dt className="text-xs text-slate-600">Precisam de resposta</dt><dd className="text-2xl font-bold">{summary.awaiting_response ?? 0}</dd></div>
          <div className="rounded-xl bg-white p-3 shadow-sm"><dt className="text-xs text-slate-600">Sem próxima ação</dt><dd className="text-2xl font-bold">{summary.open_without_next_action}</dd></div>
          <div className="rounded-xl bg-white p-3 shadow-sm"><dt className="text-xs text-slate-600">Ações atrasadas</dt><dd className="text-2xl font-bold">{summary.overdue_next_actions}</dd></div>
          <div className="rounded-xl bg-white p-3 shadow-sm"><dt className="text-xs text-slate-600">Total ({summary.demo} demo)</dt><dd className="text-2xl font-bold">{summary.total}</dd></div>
          <div className="rounded-xl bg-white p-3 shadow-sm" title="Contagem agregada de cliques no botão. Não identifica ninguém e não é um agendamento."><dt className="text-xs text-slate-600">Cliques no WhatsApp (7 dias)</dt><dd className="text-2xl font-bold">{summary.whatsapp_clicks_7d ?? 0}</dd></div>
        </dl>
      ) : null}

      {businessId ? (
        <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Pedidos</h2>
              <div role="group" aria-label="Filtro" className="flex gap-2">
                {FILTERS.map((item) => (
                  <Button key={item.value} variant={filter === item.value ? "primary" : "secondary"} onClick={() => setFilter(item.value)}>{item.label}</Button>
                ))}
              </div>
            </div>
            <div className="mt-4 grid gap-3">
              {busy && !leads.length ? <LoadingState label="Carregando pedidos…" /> : null}
              {!busy && visible.length === 0 ? <EmptyState title="Nada por aqui" description={filter === "abertos" ? "Nenhum pedido aguardando resposta." : "Nenhum pedido registrado."} /> : null}
              {visible.map((lead) => (
                <article key={lead.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">
                      {lead.service_requested}{lead.price_item_label ? ` · ${lead.price_item_label}` : ""}
                      {lead.reference_price_cents !== null ? ` · ref. ${formatPrice({ label: "", price_cents: lead.reference_price_cents })}` : ""}
                    </p>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{STATUS_LABEL[lead.status]}{lead.is_demo ? " · demo" : ""}</span>
                  </div>
                  <p className="text-xs text-slate-600">{SOURCE_LABEL[lead.source]} · {lead.preferred_period || "sem período"} · {new Date(lead.created_at).toLocaleString("pt-BR")}</p>
                  {lead.contact_name ? <p className="mt-1 text-xs">Contato: {lead.contact_name} · {lead.contact_phone}</p> : null}
                  {lead.anonymized_at ? <p className="mt-1 text-xs text-slate-600">Dados de contato anonimizados em {new Date(lead.anonymized_at).toLocaleDateString("pt-BR")}.</p> : null}
                  {lead.notes ? <p className="mt-1 text-xs text-slate-600">{lead.notes}</p> : null}
                  <p className="mt-1 text-xs"><span className="font-semibold">Próxima ação:</span> {lead.next_action || "—"}</p>
                  <button type="button" className="mt-1 text-xs font-semibold text-emerald-700 underline" onClick={() => {
                    if (history?.leadId === lead.id) return setHistory(null);
                    void api.landing.history(lead.id).then((entries) => setHistory({ leadId: lead.id, entries }), (e) => setError(e instanceof Error ? e.message : "Falha ao carregar histórico."));
                  }}>{history?.leadId === lead.id ? "Ocultar histórico" : "Ver histórico"}</button>
                  {history?.leadId === lead.id ? (
                    <ol aria-label="Histórico do pedido" className="mt-1 grid gap-1 border-l-2 border-slate-200 pl-3 text-xs text-slate-700">
                      {history.entries.map((entry, index) => (
                        <li key={index}>
                          {new Date(entry.at).toLocaleString("pt-BR")} · {ACTION_LABEL[entry.action] ?? entry.action}
                          {describeChanges(entry.changes) ? ` (${describeChanges(entry.changes)})` : ""} · {entry.actor}
                        </li>
                      ))}
                    </ol>
                  ) : null}
                  {canManage ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {NEXT_STATUS[lead.status].map((next) => (
                        <Button key={next} variant={next === "CONFIRMADO" ? "primary" : "secondary"} onClick={() => {
                          if (next === "CONFIRMADO" && !window.confirm("Confirmar este agendamento? Faça isso só depois de combinar dia, horário e preço com o tutor. Nenhuma mensagem será enviada.")) return;
                          void run(() => api.landing.updateLead(lead.id, { status: next }), `Pedido marcado como ${STATUS_LABEL[next].toLowerCase()}.`);
                        }}>{next === "CONFIRMADO" ? "Confirmar agendamento" : STATUS_LABEL[next]}</Button>
                      ))}
                      <Button variant="secondary" onClick={() => {
                        const action = window.prompt("Próxima ação", lead.next_action);
                        if (action !== null) void run(() => api.landing.updateLead(lead.id, { next_action: action }), "Próxima ação registrada.");
                      }}>Definir próxima ação</Button>
                      {canPrivacy && !lead.is_demo ? (
                        <>
                          <Button variant="secondary" onClick={() => void run(async () => downloadJson(`pedido-${lead.id}.json`, await api.landing.exportLead(lead.id)), "Cópia dos dados gerada.")}>Exportar dados</Button>
                          {!lead.anonymized_at ? (
                            <Button variant="secondary" onClick={() => {
                              if (window.confirm("Anonimizar este pedido? Nome, telefone e observações serão apagados de forma definitiva.")) {
                                void run(() => api.landing.anonymizeLead(lead.id), "Pedido anonimizado.");
                              }
                            }}>Anonimizar</Button>
                          ) : null}
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          </Card>

          {canManage ? (
            <Card>
              <h2 className="text-lg font-bold">Registrar pedido recebido por outro canal</h2>
              <p className="mt-1 text-xs text-slate-600">Use para conversas do WhatsApp, Instagram ou indicação depois que o tutor falar com a equipe. Cliques no botão do WhatsApp não viram pedido sozinhos. Enquanto a coleta real não for aprovada, use apenas dados fictícios: não registre nome, telefone ou e-mail.</p>
              <form className="mt-3 grid gap-3" onSubmit={createLead}>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Origem"><Select name="source" defaultValue="WHATSAPP_DIRETO">{(Object.keys(SOURCE_LABEL) as BusinessLeadSource[]).filter((s) => !s.startsWith("LANDING")).map((s) => <option key={s} value={s}>{SOURCE_LABEL[s]}</option>)}</Select></Field>
                  <Field label="Serviço"><Select name="service_requested">{(page?.service_options ?? []).map((s) => <option key={s}>{s}</option>)}</Select></Field>
                  <Field label="Porte"><Select name="price_item_label"><option value="">—</option>{(page?.price_items ?? []).map((p) => <option key={p.label}>{p.label}</option>)}</Select></Field>
                  <Field label="Período"><Input name="preferred_period" maxLength={120} placeholder="Manhã" /></Field>
                </div>
                <Field label="Observações"><Textarea name="notes" maxLength={1000} /></Field>
                <Button type="submit" disabled={!page?.service_options.length}>Registrar</Button>
              </form>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
