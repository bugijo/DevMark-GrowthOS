"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { splitLines, visualPresetMissingFields } from "@/lib/phase2";
import type {
  AudienceSegment,
  Business,
  MarketingObjective,
  MediaAsset,
  Service,
  VisualPreset,
  VisualPresetInput,
  VisualPrompt,
} from "@/types/api";

type CatalogKind = "service" | "audience" | "objective";

const EMPTY_PRESET: VisualPresetInput = {
  name: "",
  objective: "",
  format: "FEED",
  aspect_ratio: "1:1",
  creation_mode: "HYBRID",
  color_palette: [],
  fonts: [],
  logo_media_asset_id: null,
  logo_position: "inferior direito",
  logo_scale_percent: 16,
  safe_margins: { top: 8, right: 8, bottom: 8, left: 8 },
  background_style: "",
  photographic_style: "",
  realism_level: "alto",
  lighting: "",
  composition: "",
  max_text_characters: 90,
  text_rules: [],
  base_prompt: "",
  negative_prompt: "",
  allowed_elements: [],
  forbidden_elements: [],
  visual_signature: "",
  default_cta: "",
};

function presetInputFrom(item: VisualPreset): VisualPresetInput {
  return {
    name: item.name,
    objective: item.objective,
    format: item.format,
    aspect_ratio: item.aspect_ratio,
    creation_mode: item.creation_mode,
    color_palette: item.color_palette,
    fonts: item.fonts,
    logo_media_asset_id: item.logo_media_asset_id,
    logo_position: item.logo_position,
    logo_scale_percent: item.logo_scale_percent,
    safe_margins: item.safe_margins,
    background_style: item.background_style,
    photographic_style: item.photographic_style,
    realism_level: item.realism_level,
    lighting: item.lighting,
    composition: item.composition,
    max_text_characters: item.max_text_characters,
    text_rules: item.text_rules,
    base_prompt: item.base_prompt,
    negative_prompt: item.negative_prompt,
    allowed_elements: item.allowed_elements,
    forbidden_elements: item.forbidden_elements,
    visual_signature: item.visual_signature,
    default_cta: item.default_cta,
  };
}

export default function BrandOperationsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [audiences, setAudiences] = useState<AudienceSegment[]>([]);
  const [objectives, setObjectives] = useState<MarketingObjective[]>([]);
  const [presets, setPresets] = useState<VisualPreset[]>([]);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [catalogKind, setCatalogKind] = useState<CatalogKind>("service");
  const [catalogName, setCatalogName] = useState("");
  const [catalogDescription, setCatalogDescription] = useState("");
  const [catalogDetails, setCatalogDetails] = useState("");
  const [catalogObjections, setCatalogObjections] = useState("");
  const [catalogLocation, setCatalogLocation] = useState("");
  const [editingCatalog, setEditingCatalog] = useState<{
    kind: CatalogKind;
    id: string;
  } | null>(null);
  const [preset, setPreset] = useState<VisualPresetInput>(EMPTY_PRESET);
  const [editingPresetId, setEditingPresetId] = useState<string | null>(null);
  const [promptObjective, setPromptObjective] = useState("");
  const [promptPresetId, setPromptPresetId] = useState("");
  const [prompt, setPrompt] = useState<VisualPrompt | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canCatalog = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR"].includes(role),
  );
  const canPreset = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "DESIGNER"].includes(role),
  );
  const canGeneratePrompt = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR", "DESIGNER"].includes(
      role,
    ),
  );

  const loadResources = useCallback(async (selected: string) => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const [nextServices, nextAudiences, nextObjectives, nextPresets, nextMedia] =
        await Promise.all([
          api.catalogs.services.list(selected),
          api.catalogs.audiences.list(selected),
          api.catalogs.objectives.list(selected),
          api.catalogs.presets.list(selected),
          api.media.list(selected),
        ]);
      setServices(nextServices);
      setAudiences(nextAudiences);
      setObjectives(nextObjectives);
      setPresets(nextPresets);
      setMedia(nextMedia);
      setPromptPresetId((current) =>
        nextPresets.some((item) => item.id === current) ? current : nextPresets[0]?.id ?? "",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os dados da marca.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBusinesses = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      const next = extractItems(await api.businesses.list());
      setBusinesses(next);
      const selected = next.some((item) => item.id === businessId)
        ? businessId
        : next[0]?.id ?? "";
      setBusinessId(selected);
      if (selected) await loadResources(selected);
      else setLoading(false);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os clientes.",
      );
      setLoading(false);
    }
  }, [activeOrganizationId, businessId, loadResources]);

  useEffect(() => {
    void loadBusinesses();
    // A troca de empresa é tratada explicitamente pelo seletor abaixo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrganizationId]);

  async function selectBusiness(next: string) {
    setBusinessId(next);
    setEditingCatalog(null);
    setCatalogName("");
    setCatalogDescription("");
    setCatalogDetails("");
    setCatalogObjections("");
    setCatalogLocation("");
    setEditingPresetId(null);
    setPreset(EMPTY_PRESET);
    setPrompt(null);
    await loadResources(next);
  }

  async function createCatalog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!businessId) return;
    setBusy("catalog");
    setError(null);
    setSuccess(null);
    try {
      const details = splitLines(catalogDetails);
      if (catalogKind === "service") {
        const input = {
          name: catalogName,
          description: catalogDescription,
          category: details[0] ?? null,
          warnings: details.slice(1),
        };
        const saved =
          editingCatalog?.kind === "service"
            ? await api.catalogs.services.update(businessId, editingCatalog.id, input)
            : await api.catalogs.services.create(businessId, input);
        setServices((current) =>
          [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
            a.name.localeCompare(b.name),
          ),
        );
      } else if (catalogKind === "audience") {
        const input = {
          name: catalogName,
          description: catalogDescription,
          needs: details,
          objections: splitLines(catalogObjections),
          location: catalogLocation.trim() || null,
        };
        const saved =
          editingCatalog?.kind === "audience"
            ? await api.catalogs.audiences.update(businessId, editingCatalog.id, input)
            : await api.catalogs.audiences.create(businessId, input);
        setAudiences((current) =>
          [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
            a.name.localeCompare(b.name),
          ),
        );
      } else {
        const input = {
          name: catalogName,
          description: catalogDescription,
          planned_indicators: details,
        };
        const saved =
          editingCatalog?.kind === "objective"
            ? await api.catalogs.objectives.update(businessId, editingCatalog.id, input)
            : await api.catalogs.objectives.create(businessId, input);
        setObjectives((current) =>
          [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
            a.name.localeCompare(b.name),
          ),
        );
      }
      setCatalogName("");
      setCatalogDescription("");
      setCatalogDetails("");
      setCatalogObjections("");
      setCatalogLocation("");
      setEditingCatalog(null);
      setSuccess("Cadastro salvo e disponível para estratégia e conteúdo.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar.");
    } finally {
      setBusy(null);
    }
  }

  function editCatalog(
    kind: CatalogKind,
    item: Service | AudienceSegment | MarketingObjective,
  ) {
    setCatalogKind(kind);
    setEditingCatalog({ kind, id: item.id });
    setCatalogName(item.name);
    setCatalogDescription(item.description);
    if (kind === "service") {
      const service = item as Service;
      setCatalogDetails([service.category, ...service.warnings].filter(Boolean).join("\n"));
    } else if (kind === "audience") {
      const audience = item as AudienceSegment;
      setCatalogDetails(audience.needs.join("\n"));
      setCatalogObjections(audience.objections.join("\n"));
      setCatalogLocation(audience.location);
    } else {
      setCatalogDetails((item as MarketingObjective).planned_indicators.join("\n"));
    }
    document.getElementById("catalog-form")?.scrollIntoView();
  }

  async function archiveCatalog(kind: CatalogKind, id: string) {
    if (!businessId || !window.confirm("Arquivar este cadastro?")) return;
    setBusy(id);
    setError(null);
    try {
      if (kind === "service") {
        await api.catalogs.services.archive(businessId, id);
        setServices((current) => current.filter((item) => item.id !== id));
      } else if (kind === "audience") {
        await api.catalogs.audiences.archive(businessId, id);
        setAudiences((current) => current.filter((item) => item.id !== id));
      } else {
        await api.catalogs.objectives.archive(businessId, id);
        setObjectives((current) => current.filter((item) => item.id !== id));
      }
      setSuccess("Cadastro arquivado.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível arquivar.");
    } finally {
      setBusy(null);
    }
  }

  function updatePreset<K extends keyof VisualPresetInput>(key: K, value: VisualPresetInput[K]) {
    setPreset((current) => ({ ...current, [key]: value }));
  }

  async function savePreset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!businessId) return;
    setBusy("preset");
    setError(null);
    setSuccess(null);
    try {
      const saved = editingPresetId
        ? await api.catalogs.presets.update(businessId, editingPresetId, preset)
        : await api.catalogs.presets.create(businessId, preset);
      setPresets((current) => {
        const without = current.filter((item) => item.id !== saved.id);
        return [...without, saved].sort((a, b) => a.name.localeCompare(b.name));
      });
      setPromptPresetId(saved.id);
      setEditingPresetId(null);
      setPreset(EMPTY_PRESET);
      setSuccess(editingPresetId ? "Preset atualizado com nova versão." : "Preset visual criado.");
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Não foi possível salvar o preset.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function archivePreset(id: string) {
    if (!businessId || !window.confirm("Arquivar este preset visual?")) return;
    setBusy(id);
    setError(null);
    try {
      await api.catalogs.presets.archive(businessId, id);
      setPresets((current) => current.filter((item) => item.id !== id));
      if (editingPresetId === id) {
        setEditingPresetId(null);
        setPreset(EMPTY_PRESET);
      }
      setSuccess("Preset arquivado.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível arquivar.");
    } finally {
      setBusy(null);
    }
  }

  async function generatePrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!businessId || !promptPresetId) return;
    setBusy("prompt");
    setError(null);
    try {
      setPrompt(
        await api.catalogs.presets.generatePrompt({
          business_id: businessId,
          preset_id: promptPresetId,
          objective: promptObjective,
        }),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Não foi possível gerar o prompt.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Fundação da marca"
        title="Marca e presets visuais"
        description="Cadastre serviços, públicos e objetivos; depois transforme o Brand Kit em regras visuais reutilizáveis."
      />

      <Card>
        <Field label="Cliente" required>
          <Select
            value={businessId}
            onChange={(event) => void selectBusiness(event.target.value)}
            disabled={loading}
          >
            {businesses.length === 0 ? <option value="">Nenhum cliente disponível</option> : null}
            {businesses.map((business) => (
              <option key={business.id} value={business.id}>
                {business.name}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      {loading ? <LoadingState label="Carregando dados da marca…" /> : null}
      {!loading && !businessId ? (
        <EmptyState
          title="Cadastre um cliente primeiro"
          description="Os catálogos e presets sempre pertencem a um cliente autorizado."
        />
      ) : null}

      {!loading && businessId ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3" aria-label="Catálogos da marca">
            {[
              { title: "Serviços", kind: "service" as const, items: services },
              { title: "Públicos", kind: "audience" as const, items: audiences },
              { title: "Objetivos", kind: "objective" as const, items: objectives },
            ].map((group) => (
              <Card key={group.kind}>
                <h2 className="text-lg font-bold text-slate-950">{group.title}</h2>
                {group.items.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-500">Nenhum cadastro ativo.</p>
                ) : (
                  <ul className="mt-3 divide-y divide-slate-100">
                    {group.items.map((item) => (
                      <li key={item.id} className="flex items-start justify-between gap-3 py-3">
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900">{item.name}</p>
                          <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                            {item.description || "Sem descrição"}
                          </p>
                        </div>
                        {canCatalog ? (
                          <div className="flex shrink-0 flex-col gap-1">
                            <Button
                              variant="ghost"
                              className="px-2"
                              onClick={() => editCatalog(group.kind, item)}
                            >
                              Editar
                            </Button>
                            <Button
                              variant="ghost"
                              className="px-2 text-red-700"
                              busy={busy === item.id}
                              onClick={() => void archiveCatalog(group.kind, item.id)}
                            >
                              Arquivar
                            </Button>
                          </div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            ))}
          </section>

          {canCatalog ? (
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-bold text-slate-950">
                  {editingCatalog ? "Editar cadastro" : "Adicionar ao catálogo"}
                </h2>
                {editingCatalog ? (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setEditingCatalog(null);
                      setCatalogName("");
                      setCatalogDescription("");
                      setCatalogDetails("");
                      setCatalogObjections("");
                      setCatalogLocation("");
                    }}
                  >
                    Cancelar edição
                  </Button>
                ) : null}
              </div>
              <form id="catalog-form" className="mt-4 grid gap-4 md:grid-cols-3" onSubmit={createCatalog}>
                <Field label="Tipo" required>
                  <Select
                    value={catalogKind}
                    onChange={(event) => {
                      setCatalogKind(event.target.value as CatalogKind);
                      setEditingCatalog(null);
                      setCatalogName("");
                      setCatalogDescription("");
                      setCatalogDetails("");
                      setCatalogObjections("");
                      setCatalogLocation("");
                    }}
                    disabled={Boolean(editingCatalog)}
                  >
                    <option value="service">Serviço</option>
                    <option value="audience">Público</option>
                    <option value="objective">Objetivo</option>
                  </Select>
                </Field>
                <Field label="Nome" required>
                  <Input
                    value={catalogName}
                    onChange={(event) => setCatalogName(event.target.value)}
                    required
                    maxLength={300}
                  />
                </Field>
                <Field
                  label={
                    catalogKind === "service"
                      ? "Categoria e alertas"
                      : catalogKind === "audience"
                        ? "Necessidades"
                        : "Indicadores planejados"
                  }
                  hint={
                    catalogKind === "service"
                      ? "Categoria na primeira linha; alertas nas seguintes"
                      : "Um item por linha"
                  }
                >
                  <Textarea
                    rows={3}
                    value={catalogDetails}
                    onChange={(event) => setCatalogDetails(event.target.value)}
                  />
                </Field>
                {catalogKind === "audience" ? (
                  <>
                    <Field label="Objeções" hint="Uma por linha">
                      <Textarea
                        rows={3}
                        value={catalogObjections}
                        onChange={(event) => setCatalogObjections(event.target.value)}
                      />
                    </Field>
                    <Field label="Localização">
                      <Input
                        value={catalogLocation}
                        onChange={(event) => setCatalogLocation(event.target.value)}
                        maxLength={300}
                      />
                    </Field>
                  </>
                ) : null}
                <div className="md:col-span-3">
                  <Field label="Descrição">
                    <Textarea
                      rows={3}
                      value={catalogDescription}
                      onChange={(event) => setCatalogDescription(event.target.value)}
                    />
                  </Field>
                </div>
                <div className="md:col-span-3 md:justify-self-end">
                  <Button type="submit" busy={busy === "catalog"}>
                    {editingCatalog ? "Salvar alterações" : "Salvar cadastro"}
                  </Button>
                </div>
              </form>
            </Card>
          ) : null}

          <Card>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">Presets visuais</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Cada alteração cria uma nova versão do preset, preservada nos conteúdos.
                </p>
              </div>
              <span className="text-sm font-semibold text-slate-500">{presets.length} ativo(s)</span>
            </div>
            {presets.length === 0 ? (
              <p className="mt-5 text-sm text-slate-500">
                Salve o Brand Kit do cliente antes de criar o primeiro preset.
              </p>
            ) : (
              <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {presets.map((item) => (
                  <article key={item.id} className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs font-bold text-emerald-700 uppercase">
                      {item.creation_mode} · v{item.version}
                    </p>
                    <h3 className="mt-1 font-bold text-slate-950">{item.name}</h3>
                    <p className="mt-1 text-sm text-slate-600">
                      {item.format} · {item.aspect_ratio}
                    </p>
                    {(canPreset || canGeneratePrompt) &&
                    visualPresetMissingFields(presetInputFrom(item)).length > 0 ? (
                      <p className="mt-2 text-xs font-semibold text-amber-700">
                        Faltam {visualPresetMissingFields(presetInputFrom(item)).join(", ")}.
                      </p>
                    ) : canPreset || canGeneratePrompt ? (
                      <p className="mt-2 text-xs font-semibold text-emerald-700">
                        Preset completo para produção.
                      </p>
                    ) : null}
                    <div className="mt-4 flex flex-wrap gap-2">
                      {canPreset ? (
                        <>
                          <Button
                            variant="secondary"
                            onClick={() => {
                              setEditingPresetId(item.id);
                              setPreset(presetInputFrom(item));
                              document.getElementById("preset-form")?.scrollIntoView();
                            }}
                          >
                            Editar
                          </Button>
                          <Button
                            variant="ghost"
                            className="text-red-700"
                            busy={busy === item.id}
                            onClick={() => void archivePreset(item.id)}
                          >
                            Arquivar
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>

          {canPreset ? (
            <Card>
              <form id="preset-form" className="space-y-5" onSubmit={savePreset}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-slate-950">
                      {editingPresetId ? "Editar preset" : "Novo preset completo"}
                    </h2>
                    <p className="text-sm text-slate-600">
                      O provider mock usa estas regras para gerar prompts determinísticos.
                    </p>
                  </div>
                  {editingPresetId ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setEditingPresetId(null);
                        setPreset(EMPTY_PRESET);
                      }}
                    >
                      Cancelar edição
                    </Button>
                  ) : null}
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Field label="Nome" required>
                    <Input value={preset.name} onChange={(e) => updatePreset("name", e.target.value)} required />
                  </Field>
                  <Field label="Formato" required>
                    <Select value={preset.format} onChange={(e) => updatePreset("format", e.target.value)}>
                      <option value="FEED">Feed</option>
                      <option value="CAROUSEL">Carrossel</option>
                      <option value="STORY">Story</option>
                      <option value="REELS">Reels</option>
                    </Select>
                  </Field>
                  <Field label="Proporção" required>
                    <Select
                      value={preset.aspect_ratio}
                      onChange={(e) => updatePreset("aspect_ratio", e.target.value)}
                    >
                      <option value="1:1">1:1</option>
                      <option value="4:5">4:5</option>
                      <option value="9:16">9:16</option>
                      <option value="16:9">16:9</option>
                    </Select>
                  </Field>
                  <Field label="Modo" required>
                    <Select
                      value={preset.creation_mode}
                      onChange={(e) =>
                        updatePreset(
                          "creation_mode",
                          e.target.value as VisualPresetInput["creation_mode"],
                        )
                      }
                    >
                      <option value="HYBRID">Híbrido</option>
                      <option value="AI_IMAGE">Imagem por IA</option>
                      <option value="TEMPLATE">Template</option>
                      <option value="MANUAL">Manual</option>
                    </Select>
                  </Field>
                </div>
                <Field label="Objetivo visual">
                  <Textarea rows={2} value={preset.objective} onChange={(e) => updatePreset("objective", e.target.value)} />
                </Field>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Paleta" hint="Cores separadas por vírgula">
                    <Input
                      value={preset.color_palette.join(", ")}
                      onChange={(e) => updatePreset("color_palette", splitLines(e.target.value))}
                    />
                  </Field>
                  <Field label="Fontes" hint="Separadas por vírgula">
                    <Input value={preset.fonts.join(", ")} onChange={(e) => updatePreset("fonts", splitLines(e.target.value))} />
                  </Field>
                  <Field label="Logo da biblioteca">
                    <Select
                      value={preset.logo_media_asset_id ?? ""}
                      onChange={(e) => updatePreset("logo_media_asset_id", e.target.value || null)}
                    >
                      <option value="">Sem logo</option>
                      {media.map((asset) => (
                        <option key={asset.id} value={asset.id}>{asset.display_name}</option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Posição do logo">
                    <Input value={preset.logo_position} onChange={(e) => updatePreset("logo_position", e.target.value)} />
                  </Field>
                  <Field label="Escala do logo (%)">
                    <Input
                      type="number"
                      min={1}
                      max={100}
                      value={preset.logo_scale_percent ?? ""}
                      onChange={(e) =>
                        updatePreset(
                          "logo_scale_percent",
                          e.target.value ? Number(e.target.value) : null,
                        )
                      }
                    />
                  </Field>
                </div>
                <details className="rounded-xl border border-slate-200 p-4">
                  <summary className="cursor-pointer font-bold text-slate-900">Direção visual detalhada</summary>
                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    {[
                      ["background_style", "Estilo de fundo"],
                      ["photographic_style", "Estilo fotográfico"],
                      ["lighting", "Iluminação"],
                      ["composition", "Composição"],
                      ["visual_signature", "Assinatura visual"],
                    ].map(([key, label]) => (
                      <Field key={key} label={label}>
                        <Textarea
                          rows={2}
                          value={String(preset[key as keyof VisualPresetInput] ?? "")}
                          onChange={(e) =>
                            updatePreset(key as keyof VisualPresetInput, e.target.value as never)
                          }
                        />
                      </Field>
                    ))}
                    <Field label="Nível de realismo">
                      <Input value={preset.realism_level} onChange={(e) => updatePreset("realism_level", e.target.value)} />
                    </Field>
                    <Field label="CTA padrão">
                      <Input value={preset.default_cta} onChange={(e) => updatePreset("default_cta", e.target.value)} />
                    </Field>
                    <Field label="Prompt base">
                      <Textarea rows={3} value={preset.base_prompt} onChange={(e) => updatePreset("base_prompt", e.target.value)} />
                    </Field>
                    <Field label="Prompt negativo">
                      <Textarea rows={3} value={preset.negative_prompt} onChange={(e) => updatePreset("negative_prompt", e.target.value)} />
                    </Field>
                    <Field label="Elementos permitidos" hint="Um por linha">
                      <Textarea rows={3} value={preset.allowed_elements.join("\n")} onChange={(e) => updatePreset("allowed_elements", splitLines(e.target.value))} />
                    </Field>
                    <Field label="Elementos proibidos" hint="Um por linha">
                      <Textarea rows={3} value={preset.forbidden_elements.join("\n")} onChange={(e) => updatePreset("forbidden_elements", splitLines(e.target.value))} />
                    </Field>
                    <Field label="Regras de texto" hint="Uma por linha">
                      <Textarea rows={3} value={preset.text_rules.join("\n")} onChange={(e) => updatePreset("text_rules", splitLines(e.target.value))} />
                    </Field>
                    <Field label="Máximo de caracteres">
                      <Input
                        type="number"
                        min={0}
                        value={preset.max_text_characters ?? ""}
                        onChange={(e) => updatePreset("max_text_characters", e.target.value ? Number(e.target.value) : null)}
                      />
                    </Field>
                    <fieldset className="sm:col-span-2 rounded-xl border border-slate-200 p-4">
                      <legend className="px-1 text-sm font-bold text-slate-800">
                        Margens seguras (%)
                      </legend>
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        {[
                          ["top", "Superior"],
                          ["right", "Direita"],
                          ["bottom", "Inferior"],
                          ["left", "Esquerda"],
                        ].map(([side, label]) => (
                          <Field key={side} label={label}>
                            <Input
                              type="number"
                              min={0}
                              max={100}
                              value={preset.safe_margins[side] ?? ""}
                              onChange={(event) =>
                                updatePreset("safe_margins", {
                                  ...preset.safe_margins,
                                  [side]: Number(event.target.value),
                                })
                              }
                            />
                          </Field>
                        ))}
                      </div>
                    </fieldset>
                  </div>
                </details>
                {visualPresetMissingFields(preset).length > 0 ? (
                  <Alert tone="info">
                    Preview de completude: faltam {visualPresetMissingFields(preset).join(", ")}.
                  </Alert>
                ) : (
                  <Alert tone="success">Preview de completude: preset pronto.</Alert>
                )}
                <div className="flex justify-end">
                  <Button type="submit" busy={busy === "preset"}>
                    {editingPresetId ? "Salvar nova versão" : "Criar preset"}
                  </Button>
                </div>
              </form>
            </Card>
          ) : null}

          {canGeneratePrompt ? (
            <Card>
              <h2 className="text-lg font-bold text-slate-950">Prévia do prompt visual</h2>
              <form className="mt-4 grid gap-4 md:grid-cols-[minmax(220px,0.4fr)_1fr_auto] md:items-end" onSubmit={generatePrompt}>
                <Field label="Preset" required>
                  <Select value={promptPresetId} onChange={(e) => setPromptPresetId(e.target.value)} required>
                    <option value="">Escolha</option>
                    {presets.map((item) => <option key={item.id} value={item.id}>{item.name} · v{item.version}</option>)}
                  </Select>
                </Field>
                <Field label="Objetivo da peça" required>
                  <Input value={promptObjective} onChange={(e) => setPromptObjective(e.target.value)} minLength={2} required />
                </Field>
                <Button type="submit" busy={busy === "prompt"} disabled={!promptPresetId}>Gerar com mock</Button>
              </form>
              {prompt ? (
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-4">
                    <h3 className="text-sm font-bold text-slate-900">Prompt</h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{prompt.prompt}</p>
                  </div>
                  <div className="rounded-xl bg-red-50 p-4">
                    <h3 className="text-sm font-bold text-red-900">Evitar</h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-red-800">{prompt.negative_prompt}</p>
                  </div>
                </div>
              ) : null}
            </Card>
          ) : null}
        </>
      ) : null}
    </>
  );
}
