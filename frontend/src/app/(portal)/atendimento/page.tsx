"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  hasAnyRole,
  LEAD_MANAGERS,
  LEAD_PRIVACY_OPERATORS,
  PRIVACY_APPROVERS,
  PRIVACY_EDITORS,
  useBusinessSelection,
} from "@/components/landing/use-business-selection";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { ApiError, api } from "@/lib/api";
import type {
  AvailabilitySlot,
  BusinessAvailability,
  LeadLegalBasis,
  LeadPrivacy,
  LeadPrivacyContent,
  LeadRetentionResult,
} from "@/types/api";

const WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const LEGAL_BASIS: Record<LeadLegalBasis, string> = {
  PROCEDIMENTOS_PRELIMINARES: "Procedimentos preliminares a contrato (pedido do próprio tutor)",
  CONSENTIMENTO: "Consentimento",
  LEGITIMO_INTERESSE: "Legítimo interesse",
};
const emptyPrivacy: LeadPrivacyContent = {
  controller_name: "", privacy_contact: "", purpose: "", legal_basis: "PROCEDIMENTOS_PRELIMINARES",
  data_categories: ["Nome", "Telefone", "Serviço desejado"], retention_days: 90, notice_text: "",
};

export default function ServiceSettingsPage() {
  const { roles } = useAuth();
  const canEditSlots = hasAnyRole(roles, LEAD_MANAGERS);
  const canEditPrivacy = hasAnyRole(roles, PRIVACY_EDITORS);
  const canApprovePrivacy = hasAnyRole(roles, PRIVACY_APPROVERS);
  const canRunRetention = hasAnyRole(roles, LEAD_PRIVACY_OPERATORS);
  const selection = useBusinessSelection();
  const { businessId } = selection;
  const [availability, setAvailability] = useState<BusinessAvailability | null>(null);
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [slotNotes, setSlotNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [privacy, setPrivacy] = useState<LeadPrivacy | null>(null);
  const [draft, setDraft] = useState<LeadPrivacyContent>(emptyPrivacy);
  const [retention, setRetention] = useState<LeadRetentionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setBusy(true); setError("");
    try {
      const nextAvailability = await api.landing.availability(id);
      setAvailability(nextAvailability); setSlots(nextAvailability.slots);
      setSlotNotes(nextAvailability.notes); setConfirmed(nextAvailability.confirmed_by_business);
      try {
        const nextPrivacy = await api.landing.privacy(id);
        setPrivacy(nextPrivacy);
        const { controller_name, privacy_contact, purpose, legal_basis, data_categories, retention_days, notice_text } = nextPrivacy;
        setDraft({ controller_name, privacy_contact, purpose, legal_basis, data_categories, retention_days, notice_text });
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) { setPrivacy(null); setDraft(emptyPrivacy); } else throw e;
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar configurações."); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(businessId); }, [businessId, load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setError(""); setMessage("");
    try { await action(); setMessage(success); await load(businessId); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível concluir."); }
  }

  function saveSlots(event: FormEvent) {
    event.preventDefault();
    void run(() => api.landing.saveAvailability(businessId, { slots, notes: slotNotes, confirmed_by_business: confirmed }), "Horários salvos.");
  }

  function savePrivacy(event: FormEvent) {
    event.preventDefault();
    void run(() => api.landing.savePrivacy(businessId, draft), "Rascunho do aviso salvo. Ele precisa ser aprovado pelo responsável do estabelecimento.");
  }

  function approvePrivacy() {
    if (!privacy) return;
    const ok = window.confirm(
      `Aprovar a versão ${privacy.version} do aviso como responsável pelo estabelecimento?\n\n` +
      "Esta aprovação registra que você revisou o texto. Ela não substitui orientação jurídica e não libera, sozinha, a coleta de dados reais.",
    );
    if (!ok) return;
    const note = window.prompt("Observação da aprovação (opcional)", "") ?? "";
    void run(() => api.landing.approvePrivacy(businessId, privacy.version, note), "Aviso aprovado pelo responsável.");
  }

  const setSlot = (index: number, patch: Partial<AvailabilitySlot>) =>
    setSlots((current) => current.map((slot, i) => (i === index ? { ...slot, ...patch } : slot)));
  const setDraftField = <K extends keyof LeadPrivacyContent>(key: K, value: LeadPrivacyContent[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Atendimento"
        title="Horários e privacidade"
        description="Horários informados pelo próprio estabelecimento e o aviso de privacidade exigido antes de receber pedidos com contato."
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
      {selection.loading || (busy && !availability) ? <LoadingState label="Carregando…" /> : null}
      {!selection.loading && !businessId ? <EmptyState title="Nenhum cliente" description="Não há cliente disponível para este acesso." /> : null}

      {businessId && availability ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Horários de atendimento</h2>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${availability.confirmed_by_business ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>
                {availability.version === 0 ? "Não informado" : availability.confirmed_by_business ? `Confirmado · v${availability.version}` : `A confirmar · v${availability.version}`}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-600">Nenhum horário é sugerido automaticamente. Preencha apenas o que o estabelecimento informou.</p>
            <form className="mt-4 grid gap-3" onSubmit={saveSlots}>
              {slots.length === 0 ? <p className="text-sm text-slate-600">Nenhuma janela cadastrada.</p> : null}
              {slots.map((slot, index) => (
                <div key={index} className="grid grid-cols-[1fr_6rem_6rem_auto] items-end gap-2">
                  <Field label="Dia"><Select value={slot.weekday} disabled={!canEditSlots} onChange={(e) => setSlot(index, { weekday: Number(e.target.value) })}>{WEEKDAYS.map((day, i) => <option key={day} value={i}>{day}</option>)}</Select></Field>
                  <Field label="Início"><Input type="time" value={slot.start} disabled={!canEditSlots} onChange={(e) => setSlot(index, { start: e.target.value })} /></Field>
                  <Field label="Fim"><Input type="time" value={slot.end} disabled={!canEditSlots} onChange={(e) => setSlot(index, { end: e.target.value })} /></Field>
                  {canEditSlots ? <Button type="button" variant="secondary" onClick={() => setSlots((current) => current.filter((_, i) => i !== index))}>Remover</Button> : null}
                </div>
              ))}
              {canEditSlots ? (
                <>
                  <button type="button" className="justify-self-start text-sm font-semibold text-emerald-700 underline" onClick={() => setSlots((current) => [...current, { weekday: 0, start: "", end: "", label: "" }])}>Adicionar janela</button>
                  <Field label="Observações (ex.: feriados, encaixes)"><Textarea value={slotNotes} maxLength={1000} onChange={(e) => setSlotNotes(e.target.value)} /></Field>
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> Horários confirmados pelo estabelecimento</label>
                  <Button type="submit">Salvar horários</Button>
                </>
              ) : null}
            </form>
          </Card>

          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Aviso de privacidade</h2>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${privacy?.status === "APPROVED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>
                {privacy ? `${privacy.status === "APPROVED" ? "Aprovado pelo responsável" : "Rascunho"} · v${privacy.version}` : "Não criado"}
              </span>
            </div>
            <Alert>Modelo para revisão. A aprovação aqui é do estabelecimento e não equivale a parecer jurídico nem a declaração de conformidade com a LGPD.</Alert>
            <form className="mt-4 grid gap-3" onSubmit={savePrivacy}>
              <fieldset disabled={!canEditPrivacy} className="grid gap-3">
                <Field label="Controlador (estabelecimento responsável)" required><Input value={draft.controller_name} onChange={(e) => setDraftField("controller_name", e.target.value)} required /></Field>
                <Field label="Canal para pedidos do titular" required><Input value={draft.privacy_contact} onChange={(e) => setDraftField("privacy_contact", e.target.value)} required /></Field>
                <Field label="Finalidade" required><Textarea value={draft.purpose} onChange={(e) => setDraftField("purpose", e.target.value)} required /></Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Base legal"><Select value={draft.legal_basis} onChange={(e) => setDraftField("legal_basis", e.target.value as LeadLegalBasis)}>{(Object.keys(LEGAL_BASIS) as LeadLegalBasis[]).map((b) => <option key={b} value={b}>{LEGAL_BASIS[b]}</option>)}</Select></Field>
                  <Field label="Retenção (dias)"><Input type="number" min={1} max={730} value={draft.retention_days} onChange={(e) => setDraftField("retention_days", Number(e.target.value))} /></Field>
                </div>
                <Field label="Dados tratados (um por linha)"><Textarea value={draft.data_categories.join("\n")} onChange={(e) => setDraftField("data_categories", e.target.value.split("\n"))} /></Field>
                <Field label="Texto do aviso exibido no formulário" required><Textarea rows={6} value={draft.notice_text} onChange={(e) => setDraftField("notice_text", e.target.value)} required /></Field>
              </fieldset>
              <div className="flex flex-wrap gap-2">
                {canEditPrivacy ? <Button type="submit">Salvar rascunho do aviso</Button> : null}
                {canApprovePrivacy ? <Button type="button" variant="secondary" disabled={!privacy || privacy.status === "APPROVED"} onClick={approvePrivacy}>Aprovar como responsável</Button> : null}
              </div>
              {!canApprovePrivacy && privacy?.status === "DRAFT" ? <p className="text-xs text-slate-600">Aguardando aprovação do responsável pelo estabelecimento.</p> : null}
            </form>
            {canRunRetention && privacy ? (
              <div className="mt-6 grid gap-2 border-t border-slate-200 pt-4">
                <h3 className="font-semibold">Retenção</h3>
                <p className="text-xs text-slate-600">Pedidos com mais de {privacy.retention_days} dias têm contato e observações anonimizados. Rode a simulação antes.</p>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" onClick={() => void run(async () => setRetention(await api.landing.runRetention(businessId, true)), "Simulação concluída; nada foi alterado.")}>Simular retenção</Button>
                  <Button type="button" variant="secondary" disabled={!retention?.dry_run || retention.eligible === 0} onClick={() => {
                    if (window.confirm(`Anonimizar ${retention?.eligible ?? 0} pedido(s) antigos? A ação não pode ser desfeita.`)) {
                      void run(async () => setRetention(await api.landing.runRetention(businessId, false)), "Retenção aplicada.");
                    }
                  }}>Aplicar retenção</Button>
                </div>
                {retention ? <p className="text-sm">{retention.dry_run ? `${retention.eligible} pedido(s) seriam anonimizados.` : `${retention.anonymized} pedido(s) anonimizados.`}</p> : null}
              </div>
            ) : null}
          </Card>
        </div>
      ) : null}
    </div>
  );
}
