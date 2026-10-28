"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { formatPrice, LandingView } from "@/components/landing/landing-view";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { ApiError, api, extractItems } from "@/lib/api";
import type {
  Business,
  BusinessLead,
  BusinessLeadSource,
  BusinessLeadStatus,
  BusinessLeadSummary,
  LandingPage,
  LandingPageContent,
} from "@/types/api";

const STATUS_LABEL: Record<BusinessLeadStatus, string> = {
  NOVO: "Novo", AGUARDANDO_DADOS: "Aguardando dados", HORARIO_OFERTADO: "Horário ofertado",
  CONFIRMADO: "Confirmado", REALIZADO: "Realizado", CANCELADO: "Cancelado", NAO_COMPARECEU: "Não compareceu",
};
const NEXT_STATUS: Record<BusinessLeadStatus, BusinessLeadStatus[]> = {
  NOVO: ["AGUARDANDO_DADOS", "HORARIO_OFERTADO", "CANCELADO"],
  AGUARDANDO_DADOS: ["HORARIO_OFERTADO", "CANCELADO"],
  HORARIO_OFERTADO: ["CONFIRMADO", "AGUARDANDO_DADOS", "CANCELADO"],
  CONFIRMADO: ["REALIZADO", "NAO_COMPARECEU", "CANCELADO"],
  REALIZADO: [], CANCELADO: [], NAO_COMPARECEU: [],
};
const SOURCE_LABEL: Record<BusinessLeadSource, string> = {
  LANDING_DEMO: "Landing (demo)", INSTAGRAM_POST: "Post Instagram", INSTAGRAM_STORY: "Story Instagram",
  INDICACAO: "Indicação", WHATSAPP_DIRETO: "WhatsApp direto", OUTRO: "Outro",
};

interface EditorState {
  slug: string; headline: string; subheadline: string; cta_label: string; address: string;
  contact_channel: string; highlights: string; service_options: string; prices: { label: string; price: string }[];
  price_disclaimer: string;
}

const emptyEditor: EditorState = {
  slug: "", headline: "", subheadline: "", cta_label: "Agendar", address: "", contact_channel: "",
  highlights: "", service_options: "", prices: [{ label: "", price: "" }], price_disclaimer: "",
};

function toEditor(page: LandingPage): EditorState {
  return {
    slug: page.slug, headline: page.headline, subheadline: page.subheadline, cta_label: page.cta_label,
    address: page.address, contact_channel: page.contact_channel, highlights: page.highlights.join("\n"),
    service_options: page.service_options.join("\n"),
    prices: page.price_items.length
      ? page.price_items.map((item) => ({ label: item.label, price: item.price_cents === null ? "" : (item.price_cents / 100).toFixed(2) }))
      : [{ label: "", price: "" }],
    price_disclaimer: page.price_disclaimer,
  };
}

function toContent(editor: EditorState): LandingPageContent {
  const lines = (text: string) => text.split("\n").map((line) => line.trim()).filter(Boolean);
  return {
    slug: editor.slug.trim(), headline: editor.headline, subheadline: editor.subheadline, cta_label: editor.cta_label,
    address: editor.address, contact_channel: editor.contact_channel, highlights: lines(editor.highlights),
    service_options: lines(editor.service_options),
    price_items: editor.prices.filter((row) => row.label.trim()).map((row) => ({
      label: row.label.trim(),
      price_cents: row.price.trim() ? Math.round(Number(row.price.replace(",", ".")) * 100) : null,
    })),
    price_disclaimer: editor.price_disclaimer,
  };
}

export default function LandingWorkspacePage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [page, setPage] = useState<LandingPage | null>(null);
  const [editor, setEditor] = useState<EditorState>(emptyEditor);
  const [leads, setLeads] = useState<BusinessLead[]>([]);
  const [summary, setSummary] = useState<BusinessLeadSummary | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    void api.businesses.list()
      .then((payload) => {
        const items = extractItems(payload);
        setBusinesses(items);
        setBusinessId((current) => current || items.find((b) => /villa pet/i.test(b.name))?.id || items[0]?.id || "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Falha ao carregar clientes."))
      .finally(() => setBusy(false));
  }, []);

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setBusy(true); setError("");
    try {
      const [nextLeads, nextSummary] = await Promise.all([api.landing.leads(id), api.landing.summary(id)]);
      setLeads(nextLeads); setSummary(nextSummary);
      try {
        const nextPage = await api.landing.get(id);
        setPage(nextPage); setEditor(toEditor(nextPage));
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) { setPage(null); setEditor(emptyEditor); } else throw e;
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar dados."); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(businessId); }, [businessId, load]);

  const business = businesses.find((b) => b.id === businessId);
  const previewPage = useMemo(
    () => ({ ...toContent(editor), business_name: business?.name ?? "", demo_mode: true }),
    [editor, business?.name],
  );

  async function save(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const saved = await api.landing.save(businessId, toContent(editor));
      setPage(saved); setEditor(toEditor(saved));
      setMessage("Rascunho salvo. A página só fica visível depois de aprovada.");
      await load(businessId);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível salvar."); }
  }

  async function approve() {
    if (!page) return;
    if (!window.confirm(`Aprovar a versão ${page.version} para exibição? Confira textos, preços e endereço.`)) return;
    setError(""); setMessage("");
    try {
      const approved = await api.landing.approve(businessId, page.version);
      setPage(approved);
      setMessage("Página aprovada. Ela fica visível apenas neste ambiente local; nada foi publicado externamente.");
      await load(businessId);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível aprovar."); }
  }

  async function revoke() {
    if (!window.confirm("Tirar a página do ar agora? O conteúdo volta para rascunho.")) return;
    setError(""); setMessage("");
    try {
      setPage(await api.landing.revoke(businessId));
      setMessage("Página retirada do ar e devolvida para rascunho.");
      await load(businessId);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível revogar."); }
  }

  async function updateLead(lead: BusinessLead, input: Parameters<typeof api.landing.updateLead>[1]) {
    setError("");
    try { await api.landing.updateLead(lead.id, input); await load(businessId); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível atualizar."); }
  }

  async function createLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form)) as Record<string, string>;
    setError("");
    try {
      await api.landing.createLead(businessId, {
        source: values.source as BusinessLeadSource, service_requested: values.service_requested,
        price_item_label: values.price_item_label ?? "", preferred_period: values.preferred_period, notes: values.notes,
      });
      form.reset(); setMessage("Interessado demonstrativo registrado."); await load(businessId);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível registrar."); }
  }

  const setField = (key: keyof EditorState) => (value: string) => setEditor((current) => ({ ...current, [key]: value }));

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Clientes · captação"
        title="Landing e interessados"
        description="Página do cliente com aprovação humana, captação demonstrativa sem dados pessoais e acompanhamento dos pedidos."
      />
      {error ? <Alert>{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}

      <Card>
        <Field label="Cliente">
          <Select value={businessId} onChange={(e) => setBusinessId(e.target.value)}>
            {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </Select>
        </Field>
      </Card>

      {busy && !businesses.length ? <LoadingState label="Carregando clientes…" /> : null}
      {!busy && !businesses.length ? <EmptyState title="Nenhum cliente" description="Cadastre um cliente em Clientes para criar a página." /> : null}

      {businessId ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Página</h2>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${page?.status === "APPROVED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>
                {page ? `${page.status === "APPROVED" ? "Aprovada" : "Rascunho"} · v${page.version}` : "Não criada"}
              </span>
            </div>
            <form className="mt-4 grid gap-4" onSubmit={save}>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Endereço da página (slug)" required><Input value={editor.slug} onChange={(e) => setField("slug")(e.target.value)} required /></Field>
                <Field label="Texto do botão" required><Input value={editor.cta_label} onChange={(e) => setField("cta_label")(e.target.value)} required /></Field>
              </div>
              <Field label="Título" required><Input value={editor.headline} onChange={(e) => setField("headline")(e.target.value)} required /></Field>
              <Field label="Subtítulo"><Textarea value={editor.subheadline} onChange={(e) => setField("subheadline")(e.target.value)} /></Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Endereço do estabelecimento"><Input value={editor.address} onChange={(e) => setField("address")(e.target.value)} /></Field>
                <Field label="Canal de atendimento"><Input value={editor.contact_channel} onChange={(e) => setField("contact_channel")(e.target.value)} /></Field>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Destaques (um por linha)"><Textarea value={editor.highlights} onChange={(e) => setField("highlights")(e.target.value)} /></Field>
                <Field label="Serviços do formulário (um por linha)" required><Textarea value={editor.service_options} onChange={(e) => setField("service_options")(e.target.value)} required /></Field>
              </div>
              <fieldset className="grid gap-2">
                <legend className="text-sm font-semibold">Preços de referência</legend>
                {editor.prices.map((row, index) => (
                  <div key={index} className="grid grid-cols-[1fr_8rem] gap-2">
                    <Input aria-label={`Rótulo ${index + 1}`} placeholder="Ex.: Pequeno" value={row.label} onChange={(e) => setEditor((c) => ({ ...c, prices: c.prices.map((r, i) => i === index ? { ...r, label: e.target.value } : r) }))} />
                    <Input aria-label={`Valor ${index + 1}`} placeholder="55,00" inputMode="decimal" value={row.price} onChange={(e) => setEditor((c) => ({ ...c, prices: c.prices.map((r, i) => i === index ? { ...r, price: e.target.value } : r) }))} />
                  </div>
                ))}
                <button type="button" className="justify-self-start text-sm font-semibold text-emerald-700 underline" onClick={() => setEditor((c) => ({ ...c, prices: [...c.prices, { label: "", price: "" }] }))}>Adicionar item</button>
              </fieldset>
              <Field label="Aviso sobre preços"><Textarea value={editor.price_disclaimer} onChange={(e) => setField("price_disclaimer")(e.target.value)} /></Field>
              <div className="flex flex-wrap gap-2">
                <Button type="submit">Salvar rascunho</Button>
                <Button type="button" variant="secondary" onClick={() => setShowPreview((v) => !v)}>{showPreview ? "Fechar prévia" : "Ver prévia"}</Button>
                <Button type="button" variant="secondary" disabled={!page || page.status === "APPROVED"} onClick={() => void approve()}>Aprovar versão atual</Button>
                {page?.status === "APPROVED" ? <Button type="button" variant="secondary" onClick={() => void revoke()}>Revogar publicação</Button> : null}
              </div>
              {page?.status === "APPROVED" ? (
                <p className="text-sm">Visível localmente em <a className="font-semibold text-emerald-700 underline" href={`/p/${page.slug}`} target="_blank" rel="noreferrer">/p/{page.slug}</a>. Qualquer edição volta a página para rascunho.</p>
              ) : null}
            </form>
          </Card>

          <div className="grid content-start gap-6">
            <Card>
              <h2 className="text-lg font-bold">Acompanhamento</h2>
              {summary ? (
                <dl className="mt-3 grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-600">Interessados</dt><dd className="text-2xl font-bold">{summary.total}</dd></div>
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-600">Sem próxima ação</dt><dd className="text-2xl font-bold">{summary.open_without_next_action}</dd></div>
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-600">Ações atrasadas</dt><dd className="text-2xl font-bold">{summary.overdue_next_actions}</dd></div>
                </dl>
              ) : null}
              <p className="mt-3 text-xs text-slate-600">Todos os registros são demonstrativos enquanto o gate de privacidade não for aprovado. Nenhuma mensagem é enviada a partir desta tela.</p>
              <div className="mt-4 grid gap-3">
                {leads.length === 0 ? <EmptyState title="Sem interessados" description="Use a página aprovada ou o registro manual abaixo." /> : leads.map((lead) => (
                  <div key={lead.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold">{lead.service_requested}{lead.price_item_label ? ` · ${lead.price_item_label}` : ""}{lead.reference_price_cents !== null ? ` · ref. ${formatPrice({ label: "", price_cents: lead.reference_price_cents })}` : ""}</p>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{STATUS_LABEL[lead.status]}{lead.is_demo ? " · demo" : ""}</span>
                    </div>
                    <p className="text-xs text-slate-600">{SOURCE_LABEL[lead.source]} · {lead.preferred_period || "sem período"} · {new Date(lead.created_at).toLocaleString("pt-BR")}</p>
                    {lead.notes ? <p className="mt-1 text-xs text-slate-600">{lead.notes}</p> : null}
                    <p className="mt-1 text-xs"><span className="font-semibold">Próxima ação:</span> {lead.next_action || "—"}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {NEXT_STATUS[lead.status].map((next) => (
                        <Button key={next} variant="secondary" onClick={() => void updateLead(lead, { status: next })}>{STATUS_LABEL[next]}</Button>
                      ))}
                      <Button variant="secondary" onClick={() => {
                        const action = window.prompt("Próxima ação (sem dados pessoais)", lead.next_action);
                        if (action !== null) void updateLead(lead, { next_action: action });
                      }}>Definir próxima ação</Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <h2 className="text-lg font-bold">Registrar interessado (manual)</h2>
              <p className="mt-1 text-xs text-slate-600">Use somente dados fictícios. Não registre nome, telefone ou e-mail.</p>
              <form className="mt-3 grid gap-3" onSubmit={createLead}>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Origem"><Select name="source" defaultValue="INSTAGRAM_POST">{(Object.keys(SOURCE_LABEL) as BusinessLeadSource[]).filter((s) => s !== "LANDING_DEMO").map((s) => <option key={s} value={s}>{SOURCE_LABEL[s]}</option>)}</Select></Field>
                  <Field label="Serviço"><Select name="service_requested">{toContent(editor).service_options.map((s) => <option key={s}>{s}</option>)}</Select></Field>
                  <Field label="Porte"><Select name="price_item_label"><option value="">—</option>{toContent(editor).price_items.map((p) => <option key={p.label}>{p.label}</option>)}</Select></Field>
                  <Field label="Período"><Input name="preferred_period" maxLength={120} placeholder="Manhã" /></Field>
                </div>
                <Field label="Observações"><Textarea name="notes" maxLength={1000} /></Field>
                <Button type="submit" disabled={!toContent(editor).service_options.length}>Registrar</Button>
              </form>
            </Card>
          </div>
        </div>
      ) : null}

      {showPreview && businessId ? (
        <Card>
          <h2 className="mb-3 text-lg font-bold">Prévia (não publicada)</h2>
          <div className="overflow-hidden rounded-2xl border border-slate-200"><LandingView page={previewPage} preview /></div>
        </Card>
      ) : null}
    </div>
  );
}
