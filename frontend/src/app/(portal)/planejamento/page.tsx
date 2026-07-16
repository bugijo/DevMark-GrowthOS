"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { localDateTimeToIso, monthBounds, splitLines } from "@/lib/phase2";
import type {
  AudienceSegment,
  Business,
  CalendarEntry,
  ContentPlan,
  ContentStrategy,
  MarketingObjective,
  Service,
  StrategyInput,
  StrategyVersionInput,
  VisualPreset,
} from "@/types/api";

interface StrategyForm {
  name: string;
  starts_on: string;
  ends_on: string;
  objective: string;
  positioning: string;
  funnel: string;
  channels: string;
  pillars: string;
  planned_indicators: string;
  service_ids: string[];
  audience_ids: string[];
  marketing_objective_ids: string[];
}

const EMPTY_STRATEGY: StrategyForm = {
  name: "",
  starts_on: "",
  ends_on: "",
  objective: "",
  positioning: "",
  funnel: "AWARENESS, CONSIDERATION, CONVERSION",
  channels: "INSTAGRAM",
  pillars: "",
  planned_indicators: "conteúdos aprovados",
  service_ids: [],
  audience_ids: [],
  marketing_objective_ids: [],
};

function dateInput(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function strategyLabel(value: string | Record<string, unknown>): string {
  if (typeof value === "string") return value;
  return String(value.name ?? value.title ?? value.id ?? "Item registrado");
}

export default function PlanningPage() {
  const { activeOrganizationId, roles } = useAuth();
  const currentMonth = monthBounds();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [audiences, setAudiences] = useState<AudienceSegment[]>([]);
  const [objectives, setObjectives] = useState<MarketingObjective[]>([]);
  const [presets, setPresets] = useState<VisualPreset[]>([]);
  const [strategies, setStrategies] = useState<ContentStrategy[]>([]);
  const [plans, setPlans] = useState<ContentPlan[]>([]);
  const [calendar, setCalendar] = useState<CalendarEntry[]>([]);
  const [startsOn, setStartsOn] = useState(currentMonth.startsOn);
  const [endsOn, setEndsOn] = useState(currentMonth.endsOn);
  const [strategyForm, setStrategyForm] = useState<StrategyForm>(EMPTY_STRATEGY);
  const [editingStrategyId, setEditingStrategyId] = useState<string | null>(null);
  const [planForm, setPlanForm] = useState({
    strategy_id: "",
    name: "",
    starts_on: "",
    ends_on: "",
    frequency: "SEMANAL",
  });
  const [entryForm, setEntryForm] = useState({
    plan_id: "",
    title: "",
    objective: "",
    audience: "",
    channel: "INSTAGRAM",
    format: "FEED",
    suggested_for: "",
    visual_preset_id: "",
    notes: "",
  });
  const [comments, setComments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canManageStrategy = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR"].includes(role),
  );
  const canReviewInternal = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"].includes(role),
  );
  const canDecideClient = roles.some((role) =>
    ["CLIENT_OWNER", "CLIENT_REVIEWER"].includes(role),
  );
  const canManageCalendar = canManageStrategy;

  const loadCalendar = useCallback(async (selected: string, start: string, end: string) => {
    if (!selected) return;
    try {
      setCalendar(await api.planning.calendar.list(selected, start, end));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar o calendário.",
      );
    }
  }, []);

  const loadResources = useCallback(
    async (selected: string, start = startsOn, end = endsOn) => {
      if (!selected) return;
      setLoading(true);
      setError(null);
      try {
        const [nextServices, nextAudiences, nextObjectives, nextPresets, nextStrategies, nextPlans] =
          await Promise.all([
            api.catalogs.services.list(selected),
            api.catalogs.audiences.list(selected),
            api.catalogs.objectives.list(selected),
            api.catalogs.presets.list(selected),
            api.planning.strategies.list(selected),
            api.planning.plans.list(selected),
          ]);
        setServices(nextServices);
        setAudiences(nextAudiences);
        setObjectives(nextObjectives);
        setPresets(nextPresets);
        setStrategies(nextStrategies);
        setPlans(nextPlans);
        const approved = nextStrategies.find((item) => item.status === "APPROVED");
        setPlanForm((current) => ({
          ...current,
          strategy_id: approved?.id ?? "",
          starts_on: approved?.starts_on ?? current.starts_on,
          ends_on: approved?.ends_on ?? current.ends_on,
        }));
        setEntryForm((current) => ({
          ...current,
          plan_id: nextPlans[0]?.id ?? "",
        }));
        await loadCalendar(selected, start, end);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível carregar o planejamento.",
        );
      } finally {
        setLoading(false);
      }
    },
    [endsOn, loadCalendar, startsOn],
  );

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    try {
      const next = extractItems(await api.businesses.list());
      setBusinesses(next);
      const selected = next[0]?.id ?? "";
      setBusinessId(selected);
      if (selected) await loadResources(selected);
      else setLoading(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar.");
      setLoading(false);
    }
  }, [activeOrganizationId, loadResources]);

  useEffect(() => {
    void load();
    // A edição do período recarrega apenas o calendário; a troca de organização
    // reinicializa todos os recursos explicitamente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrganizationId]);

  function toggleSelection(field: "service_ids" | "audience_ids" | "marketing_objective_ids", id: string) {
    setStrategyForm((current) => ({
      ...current,
      [field]: current[field].includes(id)
        ? current[field].filter((item) => item !== id)
        : [...current[field], id],
    }));
  }

  async function saveStrategy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!businessId) return;
    setBusy("strategy");
    setError(null);
    setSuccess(null);
    const versionInput: StrategyVersionInput = {
      objective: strategyForm.objective,
      positioning: strategyForm.positioning,
      funnel: splitLines(strategyForm.funnel),
      channels: splitLines(strategyForm.channels),
      pillars: splitLines(strategyForm.pillars),
      planned_indicators: splitLines(strategyForm.planned_indicators),
      service_ids: strategyForm.service_ids,
      audience_ids: strategyForm.audience_ids,
      marketing_objective_ids: strategyForm.marketing_objective_ids,
    };
    try {
      const saved = editingStrategyId
        ? await api.planning.strategies.createVersion(editingStrategyId, versionInput)
        : await api.planning.strategies.create(businessId, {
            ...versionInput,
            name: strategyForm.name,
            starts_on: strategyForm.starts_on,
            ends_on: strategyForm.ends_on,
          } satisfies StrategyInput);
      setStrategies((current) => [
        saved,
        ...current.filter((item) => item.id !== saved.id),
      ]);
      setStrategyForm(EMPTY_STRATEGY);
      setEditingStrategyId(null);
      setSuccess(editingStrategyId ? "Nova versão da estratégia criada." : "Estratégia criada.");
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Não foi possível salvar a estratégia.",
      );
    } finally {
      setBusy(null);
    }
  }

  function startVersion(strategy: ContentStrategy) {
    const version = strategy.current_version;
    const snapshotIds = (items: Array<Record<string, unknown>>) =>
      items.map((item) => String(item.id ?? "")).filter(Boolean);
    setEditingStrategyId(strategy.id);
    setStrategyForm({
      name: strategy.name,
      starts_on: strategy.starts_on,
      ends_on: strategy.ends_on,
      objective: version.objective,
      positioning: version.positioning,
      funnel: version.funnel.join(", "),
      channels: version.channels.join(", "),
      pillars: version.pillars.map(String).join("\n"),
      planned_indicators: version.planned_indicators.join("\n"),
      service_ids: snapshotIds(version.service_snapshots),
      audience_ids: snapshotIds(version.audience_snapshots),
      marketing_objective_ids: snapshotIds(version.objective_snapshots),
    });
    document.getElementById("strategy-form")?.scrollIntoView();
  }

  async function strategyAction(
    strategy: ContentStrategy,
    action: "submit" | "send" | "approve" | "changes",
  ) {
    const comment = comments[strategy.id]?.trim();
    if (action === "changes" && !comment) {
      setError("Explique o ajuste necessário na estratégia.");
      return;
    }
    setBusy(strategy.id);
    setError(null);
    setSuccess(null);
    try {
      let updated: ContentStrategy;
      if (action === "submit") updated = await api.planning.strategies.submitInternal(strategy.id);
      else if (action === "send") updated = await api.planning.strategies.sendToClient(strategy.id);
      else {
        updated = await api.planning.strategies.decide(
          strategy.id,
          action === "approve" ? "APPROVE" : "CHANGES_REQUESTED",
          comment,
        );
      }
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccess("Etapa da estratégia registrada e auditada.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível avançar.");
    } finally {
      setBusy(null);
    }
  }

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!businessId) return;
    setBusy("plan");
    setError(null);
    try {
      const created = await api.planning.plans.create(businessId, planForm);
      setPlans((current) => [created, ...current]);
      setEntryForm((current) => ({ ...current, plan_id: created.id }));
      setSuccess("Plano editorial ativo.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível criar o plano.");
    } finally {
      setBusy(null);
    }
  }

  async function generateCalendar(plan: ContentPlan) {
    setBusy(plan.id);
    setError(null);
    try {
      const created = await api.planning.plans.generateMock(plan.id);
      setCalendar((current) => [...current, ...created].sort((a, b) => a.suggested_for.localeCompare(b.suggested_for)));
      setSuccess(`${created.length} pauta(s) criada(s) pelo provider mock.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível gerar as pautas.");
    } finally {
      setBusy(null);
    }
  }

  async function createEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!entryForm.plan_id) return;
    setBusy("entry");
    setError(null);
    try {
      const created = await api.planning.plans.createEntry(entryForm.plan_id, {
        title: entryForm.title,
        objective: entryForm.objective,
        audience: entryForm.audience,
        channel: entryForm.channel,
        format: entryForm.format,
        suggested_for: localDateTimeToIso(entryForm.suggested_for),
        visual_preset_id: entryForm.visual_preset_id || null,
        notes: entryForm.notes,
      });
      setCalendar((current) => [...current, created].sort((a, b) => a.suggested_for.localeCompare(b.suggested_for)));
      setEntryForm((current) => ({ ...current, title: "", objective: "", notes: "" }));
      setSuccess("Pauta adicionada ao calendário.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível criar a pauta.");
    } finally {
      setBusy(null);
    }
  }

  async function choosePeriod(kind: "month" | "week") {
    const now = new Date();
    const next =
      kind === "month"
        ? monthBounds(now)
        : { startsOn: dateInput(now), endsOn: dateInput(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 6)) };
    setStartsOn(next.startsOn);
    setEndsOn(next.endsOn);
    await loadCalendar(businessId, next.startsOn, next.endsOn);
  }

  return (
    <>
      <PageHeader
        eyebrow="Estratégia e execução"
        title="Planejamento editorial"
        description="Versione a estratégia mensal, obtenha aprovação e transforme-a em planos e pautas semanais."
      />
      <Card>
        <Field label="Cliente" required>
          <Select
            value={businessId}
            onChange={(event) => {
              setBusinessId(event.target.value);
              void loadResources(event.target.value);
            }}
          >
            {businesses.length === 0 ? <option value="">Nenhum cliente</option> : null}
            {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
          </Select>
        </Field>
      </Card>
      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      {loading ? <LoadingState label="Carregando estratégia e calendário…" /> : null}
      {!loading && !businessId ? <EmptyState title="Nenhum cliente disponível" description="Cadastre um cliente para começar o planejamento." /> : null}

      {!loading && businessId ? (
        <>
          <section className="space-y-4" aria-labelledby="strategies-title">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 id="strategies-title" className="text-xl font-bold text-slate-950">Estratégias mensais</h2>
                <p className="text-sm text-slate-600">{strategies.length} estratégia(s) ativa(s)</p>
              </div>
            </div>
            {strategies.length === 0 ? <EmptyState title="Nenhuma estratégia" description="Crie a direção mensal usando os cadastros reais da marca." /> : null}
            <div className="grid gap-4 xl:grid-cols-2">
              {strategies.map((strategy) => (
                <Card key={strategy.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-emerald-700 uppercase">{strategy.status} · versão {strategy.current_version.version_number}</p>
                      <h3 className="mt-1 text-lg font-bold text-slate-950">{strategy.name}</h3>
                      <p className="text-sm text-slate-500">{strategy.starts_on} a {strategy.ends_on}</p>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-700">{strategy.current_version.objective}</p>
                  <details className="mt-4 rounded-xl border border-slate-200 p-4">
                    <summary className="cursor-pointer text-sm font-bold text-slate-900">
                      Ver direção completa desta versão
                    </summary>
                    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="font-bold text-slate-600">Posicionamento</dt>
                        <dd className="mt-1 text-slate-800">
                          {strategy.current_version.positioning || "Não informado"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-600">Funil</dt>
                        <dd className="mt-1 text-slate-800">
                          {strategy.current_version.funnel.join(", ") || "Não informado"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-600">Canais</dt>
                        <dd className="mt-1 text-slate-800">
                          {strategy.current_version.channels.join(", ") || "Não informado"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-600">Pilares</dt>
                        <dd className="mt-1 text-slate-800">
                          {strategy.current_version.pillars.map(strategyLabel).join(", ") ||
                            "Não informado"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-600">Indicadores</dt>
                        <dd className="mt-1 text-slate-800">
                          {strategy.current_version.planned_indicators.join(", ") ||
                            "Não informado"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-600">Contextos vinculados</dt>
                        <dd className="mt-1 text-slate-800">
                          {[
                            ...strategy.current_version.service_snapshots,
                            ...strategy.current_version.audience_snapshots,
                            ...strategy.current_version.objective_snapshots,
                          ]
                            .map(strategyLabel)
                            .join(", ") || "Nenhum"}
                        </dd>
                      </div>
                    </dl>
                  </details>
                  {strategy.decision_comment ? <Alert tone="info">Feedback: {strategy.decision_comment}</Alert> : null}
                  {canDecideClient && strategy.status === "CLIENT_REVIEW" ? (
                    <div className="mt-4 space-y-3">
                      <Field label="Comentário">
                        <Textarea value={comments[strategy.id] ?? ""} onChange={(e) => setComments((current) => ({ ...current, [strategy.id]: e.target.value }))} rows={2} />
                      </Field>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <Button variant="secondary" busy={busy === strategy.id} onClick={() => void strategyAction(strategy, "changes")}>Pedir alterações</Button>
                        <Button busy={busy === strategy.id} onClick={() => void strategyAction(strategy, "approve")}>Aprovar estratégia</Button>
                      </div>
                    </div>
                  ) : null}
                  {canManageStrategy ? (
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-200 pt-4">
                      {strategy.status === "DRAFT" ? <Button busy={busy === strategy.id} onClick={() => void strategyAction(strategy, "submit")}>Enviar à revisão interna</Button> : null}
                      {strategy.status === "INTERNAL_REVIEW" && canReviewInternal ? <Button busy={busy === strategy.id} onClick={() => void strategyAction(strategy, "send")}>Enviar ao cliente</Button> : null}
                      {["DRAFT", "APPROVED"].includes(strategy.status) ? <Button variant="secondary" onClick={() => startVersion(strategy)}>Criar nova versão</Button> : null}
                    </div>
                  ) : null}
                </Card>
              ))}
            </div>
          </section>

          {canManageStrategy ? (
            <Card>
              <form id="strategy-form" className="space-y-5" onSubmit={saveStrategy}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-lg font-bold text-slate-950">{editingStrategyId ? "Nova versão da estratégia" : "Criar estratégia mensal"}</h2>
                  {editingStrategyId ? <Button type="button" variant="ghost" onClick={() => { setEditingStrategyId(null); setStrategyForm(EMPTY_STRATEGY); }}>Cancelar</Button> : null}
                </div>
                {!editingStrategyId ? (
                  <div className="grid gap-4 sm:grid-cols-3">
                    <Field label="Nome" required><Input value={strategyForm.name} onChange={(e) => setStrategyForm((current) => ({ ...current, name: e.target.value }))} required /></Field>
                    <Field label="Início" required><Input type="date" value={strategyForm.starts_on} onChange={(e) => setStrategyForm((current) => ({ ...current, starts_on: e.target.value }))} required /></Field>
                    <Field label="Fim" required><Input type="date" value={strategyForm.ends_on} onChange={(e) => setStrategyForm((current) => ({ ...current, ends_on: e.target.value }))} required /></Field>
                  </div>
                ) : null}
                <Field label="Objetivo estratégico" required><Textarea rows={3} value={strategyForm.objective} onChange={(e) => setStrategyForm((current) => ({ ...current, objective: e.target.value }))} minLength={2} required /></Field>
                <Field label="Posicionamento"><Textarea rows={2} value={strategyForm.positioning} onChange={(e) => setStrategyForm((current) => ({ ...current, positioning: e.target.value }))} /></Field>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Funil" hint="Separado por vírgulas"><Input value={strategyForm.funnel} onChange={(e) => setStrategyForm((current) => ({ ...current, funnel: e.target.value }))} /></Field>
                  <Field label="Canais" hint="Separados por vírgulas"><Input value={strategyForm.channels} onChange={(e) => setStrategyForm((current) => ({ ...current, channels: e.target.value }))} /></Field>
                  <Field label="Pilares" hint="Um por linha"><Textarea rows={3} value={strategyForm.pillars} onChange={(e) => setStrategyForm((current) => ({ ...current, pillars: e.target.value }))} /></Field>
                  <Field label="Indicadores planejados" hint="Um por linha"><Textarea rows={3} value={strategyForm.planned_indicators} onChange={(e) => setStrategyForm((current) => ({ ...current, planned_indicators: e.target.value }))} /></Field>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  {[
                    { label: "Serviços", field: "service_ids" as const, items: services },
                    { label: "Públicos", field: "audience_ids" as const, items: audiences },
                    { label: "Objetivos", field: "marketing_objective_ids" as const, items: objectives },
                  ].map((group) => (
                    <fieldset key={group.field} className="rounded-xl border border-slate-200 p-4">
                      <legend className="px-1 text-sm font-bold text-slate-800">{group.label}</legend>
                      {group.items.length === 0 ? <p className="text-xs text-slate-500">Nenhum cadastro.</p> : group.items.map((item) => (
                        <label key={item.id} className="flex min-h-10 items-center gap-2 text-sm text-slate-700">
                          <input type="checkbox" checked={strategyForm[group.field].includes(item.id)} onChange={() => toggleSelection(group.field, item.id)} className="size-4 accent-emerald-700" />
                          {item.name}
                        </label>
                      ))}
                    </fieldset>
                  ))}
                </div>
                <div className="flex justify-end"><Button type="submit" busy={busy === "strategy"}>{editingStrategyId ? "Salvar nova versão" : "Criar estratégia"}</Button></div>
              </form>
            </Card>
          ) : null}

          <section className="grid items-start gap-5 xl:grid-cols-2">
            <Card>
              <h2 className="text-lg font-bold text-slate-950">Planos editoriais</h2>
              {plans.length === 0 ? <p className="mt-3 text-sm text-slate-500">Aprove uma estratégia para criar o plano.</p> : (
                <ul className="mt-4 space-y-3">
                  {plans.map((plan) => (
                    <li key={plan.id} className="rounded-xl border border-slate-200 p-4">
                      <p className="font-bold text-slate-900">{plan.name}</p>
                      <p className="text-sm text-slate-500">{plan.starts_on} a {plan.ends_on} · {plan.frequency}</p>
                      {canManageCalendar ? <Button className="mt-3" variant="secondary" busy={busy === plan.id} onClick={() => void generateCalendar(plan)}>Gerar pautas mock</Button> : null}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            {canManageCalendar ? (
              <Card>
                <h2 className="text-lg font-bold text-slate-950">Novo plano</h2>
                <form className="mt-4 space-y-4" onSubmit={createPlan}>
                  <Field label="Estratégia aprovada" required><Select value={planForm.strategy_id} onChange={(e) => { const strategy = strategies.find((item) => item.id === e.target.value); setPlanForm((current) => ({ ...current, strategy_id: e.target.value, starts_on: strategy?.starts_on ?? current.starts_on, ends_on: strategy?.ends_on ?? current.ends_on })); }} required><option value="">Escolha</option>{strategies.filter((item) => item.status === "APPROVED").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
                  <Field label="Nome" required><Input value={planForm.name} onChange={(e) => setPlanForm((current) => ({ ...current, name: e.target.value }))} required /></Field>
                  <div className="grid gap-4 sm:grid-cols-2"><Field label="Início" required><Input type="date" value={planForm.starts_on} onChange={(e) => setPlanForm((current) => ({ ...current, starts_on: e.target.value }))} required /></Field><Field label="Fim" required><Input type="date" value={planForm.ends_on} onChange={(e) => setPlanForm((current) => ({ ...current, ends_on: e.target.value }))} required /></Field></div>
                  <Button type="submit" busy={busy === "plan"} disabled={!planForm.strategy_id}>Criar plano</Button>
                </form>
              </Card>
            ) : null}
          </section>

          {canManageCalendar && plans.length > 0 ? (
            <Card>
              <h2 className="text-lg font-bold text-slate-950">Adicionar pauta manual</h2>
              <form className="mt-4 grid gap-4 md:grid-cols-3" onSubmit={createEntry}>
                <Field label="Plano" required><Select value={entryForm.plan_id} onChange={(e) => setEntryForm((current) => ({ ...current, plan_id: e.target.value }))} required>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</Select></Field>
                <Field label="Data e hora" required><Input type="datetime-local" value={entryForm.suggested_for} onChange={(e) => setEntryForm((current) => ({ ...current, suggested_for: e.target.value }))} required /></Field>
                <Field label="Preset visual"><Select value={entryForm.visual_preset_id} onChange={(e) => setEntryForm((current) => ({ ...current, visual_preset_id: e.target.value }))}><option value="">Sem preset</option>{presets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
                <Field label="Título" required><Input value={entryForm.title} onChange={(e) => setEntryForm((current) => ({ ...current, title: e.target.value }))} required /></Field>
                <Field label="Canal"><Select value={entryForm.channel} onChange={(e) => setEntryForm((current) => ({ ...current, channel: e.target.value }))}><option>INSTAGRAM</option><option>FACEBOOK</option><option>LINKEDIN</option></Select></Field>
                <Field label="Formato"><Select value={entryForm.format} onChange={(e) => setEntryForm((current) => ({ ...current, format: e.target.value }))}><option>FEED</option><option>CAROUSEL</option><option>STORY</option><option>REELS</option></Select></Field>
                <div className="md:col-span-2"><Field label="Objetivo" required><Textarea rows={2} value={entryForm.objective} onChange={(e) => setEntryForm((current) => ({ ...current, objective: e.target.value }))} required /></Field></div>
                <Field label="Público"><Textarea rows={2} value={entryForm.audience} onChange={(e) => setEntryForm((current) => ({ ...current, audience: e.target.value }))} /></Field>
                <div className="md:col-span-3"><Field label="Notas"><Textarea rows={2} value={entryForm.notes} onChange={(e) => setEntryForm((current) => ({ ...current, notes: e.target.value }))} /></Field></div>
                <div className="md:col-span-3 md:justify-self-end"><Button type="submit" busy={busy === "entry"}>Adicionar pauta</Button></div>
              </form>
            </Card>
          ) : null}

          <section aria-labelledby="calendar-title" className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div><h2 id="calendar-title" className="text-xl font-bold text-slate-950">Calendário editorial</h2><p className="text-sm text-slate-600">Visualização mensal ou semanal, sempre no período autorizado.</p></div>
              <div className="flex gap-2"><Button variant="secondary" onClick={() => void choosePeriod("month")}>Este mês</Button><Button variant="secondary" onClick={() => void choosePeriod("week")}>Próximos 7 dias</Button></div>
            </div>
            <Card><div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"><Field label="De"><Input type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} /></Field><Field label="Até"><Input type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} /></Field><Button variant="secondary" onClick={() => void loadCalendar(businessId, startsOn, endsOn)}>Aplicar período</Button></div></Card>
            {calendar.length === 0 ? <EmptyState title="Nenhuma pauta no período" description="Gere o calendário mock ou adicione uma pauta manual." /> : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {calendar.map((entry) => (
                  <Card key={entry.id}>
                    <p className="text-xs font-bold text-emerald-700 uppercase">{entry.status} · {formatDateTime(entry.suggested_for)}</p>
                    <h3 className="mt-1 font-bold text-slate-950">{entry.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{entry.objective}</p>
                    <p className="mt-2 text-xs text-slate-500">{entry.channel} · {entry.format}</p>
                    {entry.content_item_id ? <Link href={`/conteudos?business_id=${businessId}`} className="mt-4 inline-flex min-h-10 items-center text-sm font-bold text-emerald-700 underline">Ver conteúdo vinculado</Link> : <Link href={`/conteudos?business_id=${businessId}&calendar_entry_id=${entry.id}`} className="mt-4 inline-flex min-h-10 items-center text-sm font-bold text-emerald-700 underline">Criar conteúdo desta pauta</Link>}
                  </Card>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </>
  );
}
