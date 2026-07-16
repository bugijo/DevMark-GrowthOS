"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ContentCard } from "@/components/content/content-card";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import type {
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
      setLinks(EMPTY_LINKS);
      return;
    }
    setLoadingOptions(true);
    setError(null);
    const bounds = calendarYearBounds();
    try {
      const [nextStrategies, nextPlans, nextCalendar, nextPresets, nextServices, nextAudiences, nextObjectives, nextMedia] =
        await Promise.all([
          api.planning.strategies.list(businessId),
          api.planning.plans.list(businessId),
          api.planning.calendar.list(businessId, bounds.startsOn, bounds.endsOn),
          api.catalogs.presets.list(businessId),
          api.catalogs.services.list(businessId),
          api.catalogs.audiences.list(businessId),
          api.catalogs.objectives.list(businessId),
          api.media.list(businessId),
        ]);
      setStrategies(nextStrategies);
      setPlans(nextPlans);
      setCalendar(nextCalendar.filter((entry) => !entry.content_item_id));
      setPresets(nextPresets);
      setServices(nextServices);
      setAudiences(nextAudiences);
      setObjectives(nextObjectives);
      setMedia(nextMedia);

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
            <h2 className="text-lg font-bold text-slate-950">Criar conteúdo mock</h2>
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
            </ContentCard>
          ))}
        </div>
      ) : null}
    </>
  );
}
