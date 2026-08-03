"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type {
  ContentComparisonSide,
  ContentVersionComparison,
  ContentVersionHistory,
} from "@/types/api";

const FIELD_LABELS: Record<string, string> = {
  "text.title": "Título",
  "text.caption": "Legenda",
  "text.cta": "CTA",
  "text.objective": "Objetivo",
  "text.audience": "Público",
  "text.script": "Roteiro",
  "visual.channel": "Canal",
  "visual.format": "Formato",
  "visual.visual_prompt": "Prompt visual",
  "visual.preset": "Preset visual",
  "visual.media_asset_ids": "Imagem",
};

type ImageMode = "side-by-side" | "base" | "target";

function VersionMeta({ side, label }: { side: ContentComparisonSide; label: string }) {
  return (
    <header>
      <p className="text-xs font-bold uppercase text-emerald-700">{label} · versão {side.version_number}</p>
      <p className="mt-1 text-sm text-slate-600">
        {side.author.name} · {formatDateTime(side.created_at)}
      </p>
      {side.decisions.map((decision, index) => (
        <p key={`${decision.component ?? "strategy"}-${index}`} className="mt-2 text-xs text-slate-600">
          {decision.component ? `${decision.component === "TEXT" ? "Texto" : "Imagem"}: ` : ""}
          {decision.status}
          {decision.decided_by ? ` por ${decision.decided_by.name}` : ""}
          {decision.comment ? ` — ${decision.comment}` : ""}
        </p>
      ))}
    </header>
  );
}

function TextField({ label, value, changed }: { label: string; value: string; changed: boolean }) {
  return (
    <div className={changed ? "rounded-lg bg-amber-50 p-3" : "p-3"}>
      <dt className="text-xs font-bold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">
        {value || "Não informado"}
      </dd>
    </div>
  );
}

function ImagePanel({
  label,
  url,
  zoom,
}: {
  label: string;
  url?: string;
  zoom: number;
}) {
  return (
    <figure className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-3">
      <figcaption className="mb-2 text-sm font-bold text-slate-800">{label}</figcaption>
      {url ? (
        // Signed URLs are short-lived and scoped by the backend before being rendered.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt={`Imagem da versão ${label.toLocaleLowerCase("pt-BR")}`}
          className="mx-auto max-h-[32rem] max-w-full origin-center rounded-lg object-contain transition-transform"
          style={{ transform: `scale(${zoom / 100})` }}
        />
      ) : (
        <p className="py-12 text-center text-sm text-slate-500">Sem imagem vinculada.</p>
      )}
    </figure>
  );
}

export function ContentVersionComparisonPanel({ contentId }: { contentId: string }) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState<ContentVersionHistory | null>(null);
  const [comparison, setComparison] = useState<ContentVersionComparison | null>(null);
  const [baseId, setBaseId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});
  const [imageMode, setImageMode] = useState<ImageMode>("side-by-side");
  const [zoom, setZoom] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    setOpen(true);
    if (history) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.contents.history(contentId);
      setHistory(result);
      if (result.versions.length >= 2) {
        setBaseId(result.versions.at(-2)?.id ?? "");
        setTargetId(result.versions.at(-1)?.id ?? "");
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar o histórico.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!open || !baseId || !targetId || baseId === targetId) return;
    let active = true;
    setLoading(true);
    setError(null);
    void api.contents.compare(contentId, baseId, targetId)
      .then(async (result) => {
        if (!active) return;
        setComparison(result);
        const mediaIds = [...new Set([
          ...result.base.visual.media_asset_ids,
          ...result.target.visual.media_asset_ids,
        ])];
        const entries = await Promise.all(mediaIds.map(async (id) => [id, (await api.media.signedUrl(id)).url] as const));
        if (active) setImageUrls(Object.fromEntries(entries));
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : "Não foi possível comparar as versões.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [baseId, contentId, open, targetId]);

  const changed = useMemo(() => new Set(comparison?.changed_fields ?? []), [comparison]);
  const baseImage = comparison?.base.visual.media_asset_ids[0];
  const targetImage = comparison?.target.visual.media_asset_ids[0];

  return (
    <section className="mt-4 border-t border-slate-200 pt-4" aria-label="Comparação de versões do conteúdo">
      <Button type="button" variant="secondary" onClick={() => open ? setOpen(false) : void loadHistory()} aria-expanded={open}>
        {open ? "Fechar comparação" : "Comparar versões"}
      </Button>
      {open ? (
        <div className="mt-4 space-y-4">
          {loading ? <LoadingState label="Carregando comparação…" /> : null}
          {error ? <Alert>{error}</Alert> : null}
          {history && history.versions.length < 2 ? <Alert tone="info">Crie uma nova versão para habilitar a comparação.</Alert> : null}
          {history && history.versions.length >= 2 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Versão anterior">
                <Select value={baseId} onChange={(event) => setBaseId(event.target.value)}>
                  {history.versions.map((version) => <option key={version.id} value={version.id}>Versão {version.version_number} · {version.author.name}</option>)}
                </Select>
              </Field>
              <Field label="Versão posterior">
                <Select value={targetId} onChange={(event) => setTargetId(event.target.value)}>
                  {history.versions.map((version) => <option key={version.id} value={version.id}>Versão {version.version_number} · {version.author.name}</option>)}
                </Select>
              </Field>
            </div>
          ) : null}
          {baseId && baseId === targetId ? <Alert>Escolha duas versões diferentes.</Alert> : null}
          {comparison ? (
            <>
              <div aria-live="polite" className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-950">
                <strong>{comparison.changed_fields.length} campo(s) alterado(s):</strong>{" "}
                {comparison.changed_fields.map((field) => FIELD_LABELS[field] ?? field).join(", ") || "nenhum"}.
              </div>
              <div className="grid min-w-0 gap-4 lg:grid-cols-2">
                {[{ side: comparison.base, label: "Antes" }, { side: comparison.target, label: "Depois" }].map(({ side, label }) => (
                  <article key={side.id} className="min-w-0 rounded-xl border border-slate-200 p-4">
                    <VersionMeta side={side} label={label} />
                    <dl className="mt-3 divide-y divide-slate-100">
                      <TextField label="Título" value={side.text.title} changed={changed.has("text.title")} />
                      <TextField label="Legenda" value={side.text.caption} changed={changed.has("text.caption")} />
                      <TextField label="CTA" value={side.text.cta} changed={changed.has("text.cta")} />
                      <TextField label="Objetivo" value={side.text.objective} changed={changed.has("text.objective")} />
                      <TextField label="Prompt visual" value={side.visual.visual_prompt ?? "Disponível somente para a equipe interna"} changed={changed.has("visual.visual_prompt")} />
                    </dl>
                  </article>
                ))}
              </div>
              <div className="space-y-3 rounded-xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-end gap-3">
                  <Field label="Visualização das imagens">
                    <Select value={imageMode} onChange={(event) => setImageMode(event.target.value as ImageMode)}>
                      <option value="side-by-side">Lado a lado</option>
                      <option value="base">Somente antes</option>
                      <option value="target">Somente depois</option>
                    </Select>
                  </Field>
                  <label className="text-sm font-semibold text-slate-700">
                    Zoom: {zoom}%
                    <input className="mt-2 block w-48 accent-emerald-700" type="range" min="50" max="200" step="10" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} aria-label="Zoom das imagens" />
                  </label>
                </div>
                <div className={imageMode === "side-by-side" ? "grid min-w-0 gap-4 md:grid-cols-2" : "grid min-w-0 gap-4"}>
                  {imageMode !== "target" ? <ImagePanel label="Antes" url={baseImage ? imageUrls[baseImage] : undefined} zoom={zoom} /> : null}
                  {imageMode !== "base" ? <ImagePanel label="Depois" url={targetImage ? imageUrls[targetImage] : undefined} zoom={zoom} /> : null}
                </div>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
