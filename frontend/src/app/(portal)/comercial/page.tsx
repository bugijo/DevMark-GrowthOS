"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { api } from "@/lib/api";
import type { SalesBriefing, SalesLead, SalesLeadStage, SalesLeadTask, SalesProposalDraft } from "@/types/api";

const nextStage: Partial<Record<SalesLeadStage, SalesLeadStage>> = {
  NEW_LEAD: "CONTACT_PENDING", CONTACT_PENDING: "BRIEFING", BRIEFING: "PROPOSAL_PREPARATION",
  PROPOSAL_PREPARATION: "PROPOSAL_SENT", PROPOSAL_SENT: "NEGOTIATION", NEGOTIATION: "CONTRACTED",
  CONTRACTED: "IN_PRODUCTION", IN_PRODUCTION: "DELIVERED", DELIVERED: "AFTER_SALES",
};
const emptyLead = { name: "", company: "", email: "", whatsapp: "", business_type: "", goal: "", desired_timeline: "", additional_info: "" };

export default function CommercialPage() {
  const [leads, setLeads] = useState<SalesLead[]>([]);
  const [form, setForm] = useState(emptyLead);
  const [selected, setSelected] = useState<string | null>(null);
  const [briefing, setBriefing] = useState<SalesBriefing | null>(null);
  const [proposal, setProposal] = useState<SalesProposalDraft | null>(null);
  const [tasks, setTasks] = useState<SalesLeadTask[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const nextLeads = await api.sales.list();
      setLeads(nextLeads);
    }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar pipeline."); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const active = leads.find((lead) => lead.id === selected) ?? null;

  async function selectLead(id: string) {
    setSelected(id); setBriefing(null); setProposal(null); setError("");
    try { setTasks(await api.sales.tasks(id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar tarefas."); }
  }

  async function createLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    try { const lead = await api.sales.create(form); setForm(emptyLead); setSelected(lead.id); setMessage("Lead interno registrado."); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao registrar lead."); }
  }
  async function advance() {
    if (!active || !nextStage[active.stage]) return;
    if (nextStage[active.stage] === "PROPOSAL_SENT" && !window.confirm("Confirme somente se a proposta já foi enviada manualmente e com aprovação. O Hermes apenas registrará o estado; não enviará nada.")) return;
    try { await api.sales.changeStage(active.id, nextStage[active.stage]!); setMessage("Etapa atualizada."); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao atualizar etapa."); }
  }
  async function buildBriefing() {
    if (!active) return;
    try { setBriefing(await api.sales.briefing(active.id)); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao gerar briefing."); }
  }
  async function buildProposal() {
    if (!active) return;
    try { setProposal(await api.sales.draftProposal(active.id)); setMessage("Rascunho interno criado; nada foi enviado."); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao preparar rascunho."); }
  }
  async function addTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!active || !taskTitle.trim()) return;
    try { await api.sales.createTask(active.id, taskTitle); setTaskTitle(""); setMessage("Tarefa interna registrada."); setTasks(await api.sales.tasks(active.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao registrar tarefa."); }
  }

  return <>
    <PageHeader eyebrow="DevMarkia · uso interno" title="Pipeline comercial" description="Lead → briefing → proposta → tarefas. Nenhuma mensagem, publicação ou proposta é enviada automaticamente." action={<Button variant="secondary" onClick={() => void load()}>Atualizar</Button>} />
    {error ? <Alert>{error}</Alert> : null}{message ? <Alert tone="success">{message}</Alert> : null}
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <Card><h2 className="text-lg font-bold">Registrar oportunidade</h2><form className="mt-4 grid gap-3" onSubmit={createLead}>
        <Field label="Nome" required><Input value={form.name} onChange={e => setForm({...form,name:e.target.value})} required /></Field>
        <Field label="Empresa"><Input value={form.company} onChange={e => setForm({...form,company:e.target.value})} /></Field>
        <div className="grid gap-3 sm:grid-cols-2"><Field label="E-mail"><Input type="email" value={form.email} onChange={e => setForm({...form,email:e.target.value})} /></Field><Field label="WhatsApp"><Input value={form.whatsapp} onChange={e => setForm({...form,whatsapp:e.target.value})} /></Field></div>
        <Field label="Segmento"><Input value={form.business_type} onChange={e => setForm({...form,business_type:e.target.value})} /></Field>
        <Field label="Objetivo solicitado" required><Textarea value={form.goal} onChange={e => setForm({...form,goal:e.target.value})} required /></Field>
        <Field label="Prazo desejado"><Input value={form.desired_timeline} onChange={e => setForm({...form,desired_timeline:e.target.value})} /></Field>
        <Field label="Informações adicionais"><Textarea value={form.additional_info} onChange={e => setForm({...form,additional_info:e.target.value})} /></Field>
        <Button type="submit">Salvar lead interno</Button>
      </form></Card>
      <div className="grid content-start gap-4"><Card><h2 className="text-lg font-bold">Oportunidades</h2>{busy ? <LoadingState label="Carregando oportunidades…" /> : leads.length === 0 ? <EmptyState title="Pipeline vazio" description="Cadastre uma oportunidade para começar o fluxo interno." /> : <div className="mt-3 space-y-2">{leads.map(lead => <button key={lead.id} onClick={() => void selectLead(lead.id)} className={`w-full rounded-xl border p-3 text-left ${selected===lead.id ? "border-emerald-600 bg-emerald-50" : "border-slate-200"}`}><span className="block font-semibold">{lead.company || lead.name}</span><span className="text-xs text-slate-600">{lead.stage.replaceAll("_", " ")} · {lead.source}</span></button>)}</div>}</Card>
      {active ? <Card><h2 className="text-lg font-bold">{active.company || active.name}</h2><p className="mt-1 text-sm text-slate-600">Etapa: {active.stage.replaceAll("_", " ")}</p><p className="mt-2 text-sm font-semibold">Triagem: {active.service_classification.replaceAll("_", " ")}</p><p className="text-sm text-slate-600">{active.classification_reason}</p><p className="mt-3 text-sm">{active.goal}</p><div className="mt-4 flex flex-wrap gap-2"><Button variant="secondary" disabled={!nextStage[active.stage]} onClick={() => void advance()}>{nextStage[active.stage] === "PROPOSAL_SENT" ? "Registrar envio manual" : "Avançar etapa"}</Button><Button variant="secondary" onClick={() => void buildBriefing()}>Preparar briefing</Button><Button disabled={active.service_classification !== "IN_SCOPE_LANDING_PAGE" || !["BRIEFING", "PROPOSAL_PREPARATION"].includes(active.stage)} onClick={() => void buildProposal()}>Rascunho de proposta</Button></div>
        {briefing ? <div className="mt-4 rounded-xl bg-slate-50 p-4"><h3 className="font-bold">Briefing determinístico · sem IA</h3><p className="mt-2 text-sm">Serviço: {briefing.requested_service}. Escopo de referência: {briefing.scope_reference}.</p><p className="mt-2 text-sm">Faltam: {briefing.missing_before_proposal.join("; ")}.</p></div> : null}
        {proposal ? <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm">{proposal.body}</pre> : null}
        <form className="mt-4 flex gap-2" onSubmit={e => void addTask(e)}><Input aria-label="Nova tarefa" placeholder="Próxima ação interna" value={taskTitle} onChange={e => setTaskTitle(e.target.value)} required /><Button type="submit" variant="secondary">Adicionar tarefa</Button></form>
        {tasks.length ? <div className="mt-3"><h3 className="text-sm font-bold">Próximas ações</h3><ul className="mt-2 list-disc pl-5 text-sm">{tasks.map(task => <li key={task.id}>{task.title}</li>)}</ul></div> : null}
      </Card> : null}</div>
    </div>
  </>;
}
