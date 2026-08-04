"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ContentCard } from "@/components/content/content-card";
import { ContentVersionComparisonPanel } from "@/components/content/version-comparison";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import type {
  AIGeneration,
  AITask,
  AudienceSegment,
  Business,
  CalendarEntry,
  ContentItem,
  ContentPlan,
  ContentStrategy,
  MarketingObjective,
  MediaAsset,
  Service,
  VisualPreset,
} from "@/types/api";

interface GenerationLinks {
  strategyId: string;
  strategyVersionId: string;
  planId: string;
  calendarEntryId: string;
  presetId: string;
  serviceId: string;
  audienceId: string;
  objectiveId: string;
  mediaId: string;
}

const EMPTY_LINKS: GenerationLinks = {
  strategyId: "",
  strategyVersionId: "",
  planId: "",
  calendarEntryId: "",
  presetId: "",
  serviceId: "",
  audienceId: "",
  objectiveId: "",
  mediaId: "",
};

function calendarYearBounds(): { startsOn: string; endsOn: string } {
  const year = new Date().getFullYear();
  return { startsOn: `${year}-01-01`, endsOn: `${year}-12-31` };
}

export default function ContentsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState("all");
  const [strategies, setStrategies] = useState<ContentStrategy[]>([]);
  const [plans, setPlans] = useState<ContentPlan[]>([]);
  const [calendar, setCalendar] = useState<CalendarEntry[]>([]);
  const [presets, setPresets] = useState<VisualPreset[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [audiences, setAudiences] = useState<AudienceSegment[]>([]);
  const [objectives, setObjectives] = useState<MarketingObjective[]>([]);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [links, setLinks] = useState<GenerationLinks>(EMPTY_LINKS);
  const [objective, setObjective] = useState("");
  const [channel, setChannel] = useState("INSTAGRAM");
  const [format, setFormat] = useState("FEED");
  const [notes, setNotes] = useState("");
  const [script, setScript] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [aiTask, setAiTask] = useState<AITask>("CONTENT_IDEAS");
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiAlternatives, setAiAlternatives] = useState<1 | 3>(1);
  const [aiHistory, setAiHistory] = useState<AIGeneration[]>([]);
  const [aiGenerating, setAiGenerating] = useState(false);

  const canCreate = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR"].includes(role),
  );
  const canSubmit = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR", "DESIGNER"].includes(
      role,
    ),
  );
  const canSend = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"].includes(role),
  );

  const loadOptions = useCallback(async (businessId: string) => {
    if (!businessId || businessId === "all") {
      setStrategies([]);
      setPlans([]);
      setCalendar([]);
      setPresets([]);
      setServices([]);
      setAudiences([]);
      setObjectives([]);
      setMedia([]);
      setAiHistory([]);
      setLinks(EMPTY_LINKS);
      return;
    }
    setLoadingOptions(true);
    setError(null);
    const bounds = calendarYearBounds();
    try {
      const [nextStrategies, nextPlans, nextCalendar, nextPresets, nextServices, nextAudiences, nextObjectives, nextMedia, nextAiHistory] =
        await Promise.all([
          api.planning.strategies.list(businessId),
          api.planning.plans.list(businessId),
          api.planning.calendar.list(businessId, bounds.startsOn, bounds.endsOn),
          api.catalogs.presets.list(businessId),
          api.catalogs.services.list(businessId),
          api.catalogs.audiences.list(businessId),
          api.catalogs.objectives.list(businessId),
          api.media.list(businessId),
          api.ai.list(businessId),
        ]);
      setStrategies(nextStrategies);
      setPlans(nextPlans);
      setCalendar(nextCalendar.filter((entry) => !entry.content_item_id));
      setPresets(nextPresets);
      setServices(nextServices);
      setAudiences(nextAudiences);
      setObjectives(nextObjectives);
      setMedia(nextMedia);
      setAiHistory(nextAiHistory);

      const requestedEntry = new URLSearchParams(window.location.search).get("calendar_entry_id");
      const entry = nextCalendar.find(
        (item) => item.id === requestedEntry && !item.content_item_id,
      );
      const plan = entry
        ? nextPlans.find((item) => item.id === entry.content_plan_id)
        : undefined;
      setLinks({
        ...EMPTY_LINKS,
        strategyId: plan?.content_strategy_id ?? "",
        strategyVersionId: plan?.strategy_version_id ?? "",
        planId: plan?.id ?? "",
        calendarEntryId: entry?.id ?? "",
        presetId: entry?.visual_preset_id ?? "",
      });
      if (entry) {
        setObjective(entry.objective);
        setChannel(entry.channel);
        setFormat(entry.format);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os vínculos do conteúdo.",
      );
    } finally {
      setLoadingOptions(false);
    }
  }, []);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      const [businessResponse, contentResponse] = await Promise.all([
        api.businesses.list(),
        api.contents.list(),
      ]);
      const nextBusinesses = extractItems(businessResponse);
      setBusinesses(nextBusinesses);
      setContents(extractItems(contentResponse));

      const requestedBusiness = new URLSearchParams(window.location.search).get("business_id");
      const selected = requestedBusiness && nextBusinesses.some((item) => item.id === requestedBusiness)
        ? requestedBusiness
        : nextBusinesses.length === 1
          ? nextBusinesses[0].id
          : "all";
      setSelectedBusiness(selected);
      if (selected !== "all") await loadOptions(selected);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os conteúdos.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId, loadOptions]);

  useEffect(() => {
    void load();
  }, [load]);

  const businessById = useMemo(
    () => new Map(businesses.map((business) => [business.id, business.name])),
    [businesses],
  );
  const filtered =
    selectedBusiness === "all"
      ? contents
      : contents.filter((content) => content.business_id === selectedBusiness);
  const filteredPlans = links.strategyId
    ? plans.filter((plan) => plan.content_strategy_id === links.strategyId)
    : plans;
  const filteredCalendar = links.planId
    ? calendar.filter((entry) => entry.content_plan_id === links.planId)
    : calendar;

  async function chooseBusiness(next: string) {
    setSelectedBusiness(next);
    setLinks(EMPTY_LINKS);
    await loadOptions(next);
  }

  function chooseStrategy(strategyId: string) {
    const strategy = strategies.find((item) => item.id === strategyId);
    setLinks((current) => ({
      ...current,
      strategyId,
      strategyVersionId:
        strategy?.approved_version_id ?? strategy?.current_version.id ?? "",
      planId: "",
      calendarEntryId: "",
    }));
  }

  function choosePlan(planId: string) {
    const plan = plans.find((item) => item.id === planId);
    setLinks((current) => ({
      ...current,
      strategyId: plan?.content_strategy_id ?? current.strategyId,
      strategyVersionId: plan?.strategy_version_id ?? current.strategyVersionId,
      planId,
      calendarEntryId: "",
    }));
  }

  function chooseCalendar(entryId: string) {
    const entry = calendar.find((item) => item.id === entryId);
    const plan = plans.find((item) => item.id === entry?.content_plan_id);
    setLinks((current) => ({
      ...current,
      strategyId: plan?.content_strategy_id ?? current.strategyId,
      strategyVersionId: plan?.strategy_version_id ?? current.strategyVersionId,
      planId: plan?.id ?? current.planId,
      calendarEntryId: entryId,
      presetId: entry?.visual_preset_id ?? current.presetId,
    }));
    if (entry) {
      setObjective(entry.objective);
      setChannel(entry.channel);
      setFormat(entry.format);
    }
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedBusiness === "all") {
      setError("Escolha um cliente antes de gerar o conteúdo.");
      return;
    }
    setGenerating(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await api.contents.generate({
        business_id: selectedBusiness,
        objective: objective.trim(),
        channel,
        format,
        ...(links.strategyId ? { content_strategy_id: links.strategyId } : {}),
        ...(links.strategyVersionId
          ? { strategy_version_id: links.strategyVersionId }
          : {}),
        ...(links.planId ? { content_plan_id: links.planId } : {}),
        ...(links.calendarEntryId ? { calendar_entry_id: links.calendarEntryId } : {}),
        ...(links.presetId ? { visual_preset_id: links.presetId } : {}),
        ...(links.serviceId ? { service_id: links.serviceId } : {}),
        ...(links.audienceId ? { audience_segment_id: links.audienceId } : {}),
        ...(links.objectiveId ? { marketing_objective_id: links.objectiveId } : {}),
        ...(links.mediaId ? { media_asset_id: links.mediaId } : {}),
        notes: notes.trim(),
        script: script.trim(),
      });
      setContents((current) => [created, ...current]);
      if (links.calendarEntryId) {
        setCalendar((current) => current.filter((item) => item.id !== links.calendarEntryId));
      }
      setObjective("");
      setNotes("");
      setScript("");
      setLinks(EMPTY_LINKS);
      setSuccess("Rascunho vinculado criado com providers mock. Revise antes de enviar.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível gerar o conteúdo.",
      );
    } finally {
      setGenerating(false);
    }
  }

  async function generateWithAI() {
    if (selectedBusiness === "all") {
      setError("Escolha um cliente antes de gerar com IA.");
      return;
    }
    setAiGenerating(true);
    setError(null);
    setSuccess(null);
    try {
      const generated = await api.ai.generate(selectedBusiness, {
        task: aiTask,
        instruction: aiInstruction,
        alternatives: aiAlternatives,
        source_text: objective,
      });
      setAiHistory((current) => [generated, ...current]);
      setSuccess(
        generated.simulated
          ? "Resposta simulada pelo mock. Revise antes de criar qualquer conteúdo."
          : "Alternativas geradas. Revisão e aprovação continuam obrigatórias.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível gerar com IA.",
      );
    } finally {
      setAiGenerating(false);
    }
  }

  async function regenerateWithAI(generation: AIGeneration) {
    setAiGenerating(true);
    setError(null);
    try {
      const regenerated = await api.ai.regenerate(generation.id);
      setAiHistory((current) => [regenerated, ...current]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Falha ao regenerar.");
    } finally {
      setAiGenerating(false);
    }
  }

  async function transition(content: ContentItem, action: "internal" | "client") {
    setActionId(content.id);
    setError(null);
    setSuccess(null);
    try {
      const updated =
        action === "internal"
          ? await api.contents.submitInternal(content.id)
          : await api.contents.sendToClient(content.id);
      setContents((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSuccess(
        action === "internal"
          ? "Conteúdo enviado para revisão interna."
          : "Texto e imagem enviados separadamente à aprovação do cliente.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível atualizar o conteúdo.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Produção vinculada"
        title="Conteúdos"
        description="Crie versões ligadas à estratégia, pauta, preset e mídia. Nada é publicado automaticamente."
      />

      {canCreate ? (
        <Card>
          <div className="mb-5">
            <h2 className="text-lg font-bold text-slate-950">Growth Agent</h2>
            <p className="mt-1 text-sm text-slate-600">
              Usa o contexto autorizado do cliente. Nada é publicado ou aprovado automaticamente.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Tipo de geração">
              <Select value={aiTask} onChange={(event) => setAiTask(event.target.value as AITask)}>
                <option value="CONTENT_IDEAS">Ideias de conteúdo</option>
                <option value="MONTHLY_STRATEGY">Estratégia mensal</option>
                <option value="EDITORIAL_CALENDAR">Calendário editorial</option>
                <option value="CAPTION">Legenda</option>
                <option value="TITLE">Título</option>
                <option value="CTA">CTA</option>
                <option value="SCRIPT">Roteiro</option>
                <option value="VISUAL_PROMPT">Prompt visual</option>
                <option value="CONTENT_REPURPOSE">Reaproveitamento</option>
                <option value="TONE_REVIEW">Revisão de tom</option>
                <option value="AUDIT">Auditoria</option>
                <option value="SENSITIVITY_CLASSIFICATION">Conteúdo sensível</option>
              </Select>
            </Field>
            <Field label="Alternativas">
              <Select
                value={String(aiAlternatives)}
                onChange={(event) => setAiAlternatives(event.target.value === "3" ? 3 : 1)}
              >
                <option value="1">1 alternativa</option>
                <option value="3">3 alternativas</option>
              </Select>
            </Field>
            <div className="flex items-end">
              <Button
                type="button"
                busy={aiGenerating}
                disabled={selectedBusiness === "all"}
                onClick={() => void generateWithAI()}
              >
                {aiGenerating ? "Gerando…" : "Gerar com IA"}
              </Button>
            </div>
          </div>
          <div className="mt-4">
            <Field label="Instrução adicional (opcional)">
              <Textarea
                rows={3}
                value={aiInstruction}
                onChange={(event) => setAiInstruction(event.target.value)}
                maxLength={2000}
                placeholder="Ex.: priorize uma linguagem acolhedora e educativa"
              />
            </Field>
          </div>
          {aiHistory.map((generation) => (
            <section key={generation.id} className="mt-5 rounded-xl border border-slate-200 p-4" aria-label="Resultado da geração com IA">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-900">
                  {generation.provider} · {generation.model} · {generation.duration_ms} ms
                </p>
                <Button type="button" variant="secondary" onClick={() => void regenerateWithAI(generation)}>
                  Gerar outra versão
                </Button>
              </div>
              {generation.simulated ? <Alert tone="info">Resposta simulada pelo provider mock.</Alert> : null}
              {generation.used_fallback ? <Alert tone="info">Foi necessário usar fallback.</Alert> : null}
              <p className="mt-2 text-xs text-slate-600">Revisão humana obrigatória · sem publicação automática</p>
              <div className="mt-3 grid gap-3 lg:grid-cols-3">
                {generation.alternatives.map((alternative) => (
                  <article key={alternative.id} className="rounded-lg bg-slate-50 p-3">
                    <h3 className="font-semibold text-slate-950">{String(alternative.payload.title ?? `Alternativa ${alternative.position}`)}</h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{String(alternative.payload.caption ?? alternative.payload.strategy ?? "")}</p>
                    {alternative.is_sensitive ? <p className="mt-2 text-sm font-semibold text-amber-800">Conteúdo sensível: exige revisão profissional.</p> : null}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </Card>
      ) : null}

      {canCreate ? (
        <Card>
          <div className="mb-5">
            <h2 className="text-lg font-bold text-slate-950">Criar rascunho vinculado</h2>
            <p className="mt-1 text-sm text-slate-600">
              Os vínculos são opcionais, mas preservam o contexto aprovado em snapshots.
            </p>
          </div>
          <form className="space-y-5" onSubmit={generate}>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Cliente" required>
                <Select
                  value={selectedBusiness}
                  onChange={(event) => void chooseBusiness(event.target.value)}
                  required
                >
                  <option value="all">Escolha um cliente</option>
                  {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
                </Select>
              </Field>
              <Field label="Canal" required><Select value={channel} onChange={(event) => setChannel(event.target.value)}><option value="INSTAGRAM">Instagram</option><option value="FACEBOOK">Facebook</option><option value="LINKEDIN">LinkedIn</option></Select></Field>
              <Field label="Formato" required><Select value={format} onChange={(event) => setFormat(event.target.value)}><option value="FEED">Feed</option><option value="CAROUSEL">Carrossel</option><option value="STORY">Story</option><option value="REELS">Reels</option></Select></Field>
              <Field label="Serviço"><Select value={links.serviceId} onChange={(event) => setLinks((current) => ({ ...current, serviceId: event.target.value }))}><option value="">Sem vínculo</option>{services.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
            </div>

            {loadingOptions ? <Alert tone="info">Carregando vínculos autorizados do cliente…</Alert> : null}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Estratégia"><Select value={links.strategyId} onChange={(event) => chooseStrategy(event.target.value)}><option value="">Sem vínculo</option>{strategies.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.status}</option>)}</Select></Field>
              <Field label="Plano"><Select value={links.planId} onChange={(event) => choosePlan(event.target.value)}><option value="">Sem vínculo</option>{filteredPlans.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
              <Field label="Pauta do calendário"><Select value={links.calendarEntryId} onChange={(event) => chooseCalendar(event.target.value)}><option value="">Sem pauta</option>{filteredCalendar.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</Select></Field>
              <Field label="Preset visual"><Select value={links.presetId} onChange={(event) => setLinks((current) => ({ ...current, presetId: event.target.value }))}><option value="">Sem preset</option>{presets.map((item) => <option key={item.id} value={item.id}>{item.name} · v{item.version}</option>)}</Select></Field>
              <Field label="Público"><Select value={links.audienceId} onChange={(event) => setLinks((current) => ({ ...current, audienceId: event.target.value }))}><option value="">Público do Brand Kit</option>{audiences.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
              <Field label="Objetivo de marketing"><Select value={links.objectiveId} onChange={(event) => setLinks((current) => ({ ...current, objectiveId: event.target.value }))}><option value="">Sem vínculo</option>{objectives.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></Field>
              <Field label="Imagem principal"><Select value={links.mediaId} onChange={(event) => setLinks((current) => ({ ...current, mediaId: event.target.value }))}><option value="">Sem imagem</option>{media.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</Select></Field>
            </div>
            <Field label="Objetivo do conteúdo" required><Textarea rows={3} value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Ex.: explicar por que consultas preventivas são importantes" minLength={2} maxLength={1000} required /></Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Notas internas"><Textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={10000} /></Field>
              <Field label="Roteiro"><Textarea rows={3} value={script} onChange={(event) => setScript(event.target.value)} maxLength={30000} /></Field>
            </div>
            <div className="flex justify-end"><Button type="submit" busy={generating} disabled={selectedBusiness === "all" || loadingOptions}>{generating ? "Gerando…" : "Gerar rascunho vinculado"}</Button></div>
          </form>
        </Card>
      ) : null}

      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div><h2 className="text-lg font-bold text-slate-950">Biblioteca</h2><p className="text-sm text-slate-600">{filtered.length} conteúdo(s) neste filtro</p></div>
        {businesses.length > 1 ? <label className="text-sm font-semibold text-slate-700">Filtrar por cliente<Select className="sm:min-w-64" value={selectedBusiness} onChange={(event) => void chooseBusiness(event.target.value)}><option value="all">Todos os clientes</option>{businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}</Select></label> : null}
      </div>

      {loading ? <LoadingState label="Carregando conteúdos…" /> : null}
      {!loading && !error && filtered.length === 0 ? <EmptyState title="Nenhum conteúdo neste filtro" description={canCreate ? "Escolha um cliente e gere o primeiro rascunho vinculado." : "A equipe ainda não disponibilizou conteúdos para o seu acesso."} /> : null}
      {!loading && filtered.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {filtered.map((content) => (
            <ContentCard key={content.id} content={content} businessName={businessById.get(content.business_id)}>
              <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                {content.content_strategy_id ? <span>Estratégia vinculada</span> : null}
                {content.calendar_entry_id ? <span>Pauta vinculada</span> : null}
                {content.visual_preset_id ? <span>Preset preservado</span> : null}
              </div>
              {canSubmit && content.status === "DRAFT" ? <Button variant="secondary" busy={actionId === content.id} onClick={() => void transition(content, "internal")}>Enviar para revisão interna</Button> : null}
              {canSend && content.status === "INTERNAL_REVIEW" ? <Button busy={actionId === content.id} onClick={() => void transition(content, "client")}>Enviar texto e imagem ao cliente</Button> : null}
              {!canCreate ? <p className="text-sm text-slate-600">Use Aprovações quando esta versão aguardar sua decisão.</p> : null}
              <ContentVersionComparisonPanel contentId={content.id} />
            </ContentCard>
          ))}
        </div>
      ) : null}
    </>
  );
}
