"use client";

import { FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Select, Textarea } from "@/components/ui/form-controls";
import type {
  ContentItem,
  MediaAsset,
  VisualPreset,
  VisualRevisionInput,
} from "@/types/api";

const KEEP = "__keep__";
const CLEAR = "__clear__";

export function VisualRevisionForm({
  content,
  presets,
  media,
  busy,
  onSubmit,
}: {
  content: ContentItem;
  presets: VisualPreset[];
  media: MediaAsset[];
  busy: boolean;
  onSubmit: (input: VisualRevisionInput) => void | Promise<void>;
}) {
  const version = content.current_version;
  const [presetChoice, setPresetChoice] = useState(KEEP);
  const [mediaChoice, setMediaChoice] = useState(KEEP);
  const [visualPrompt, setVisualPrompt] = useState(version.visual_prompt ?? "");
  const [negativePrompt, setNegativePrompt] = useState(version.negative_prompt ?? "");

  const input = useMemo<VisualRevisionInput>(() => {
    const next: VisualRevisionInput = {};
    if (presetChoice !== KEEP) {
      next.visual_preset_id = presetChoice === CLEAR ? null : presetChoice;
    }
    if (mediaChoice !== KEEP) {
      next.media_asset_id = mediaChoice === CLEAR ? null : mediaChoice;
    }
    if (visualPrompt.trim() !== (version.visual_prompt ?? "").trim()) {
      next.visual_prompt = visualPrompt.trim();
    }
    if (negativePrompt.trim() !== (version.negative_prompt ?? "").trim()) {
      next.negative_prompt = negativePrompt.trim();
    }
    return next;
  }, [mediaChoice, negativePrompt, presetChoice, version, visualPrompt]);
  const changed = Object.keys(input).length > 0;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (changed) void onSubmit(input);
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
        <h3 className="text-sm font-bold text-orange-950">Revisão da imagem</h3>
        <p className="mt-1 text-sm text-orange-900">
          {content.change_request_comment || "Ajuste a direção visual desta versão."}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Preset visual">
          <Select value={presetChoice} onChange={(event) => setPresetChoice(event.target.value)}>
            <option value={KEEP}>Manter preset atual</option>
            <option value={CLEAR}>Remover preset</option>
            {presets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name} · v{preset.version}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Imagem principal">
          <Select value={mediaChoice} onChange={(event) => setMediaChoice(event.target.value)}>
            <option value={KEEP}>Manter mídia atual</option>
            <option value={CLEAR}>Remover mídia</option>
            {media.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.display_name}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Field label="Prompt visual">
        <Textarea rows={5} value={visualPrompt} onChange={(event) => setVisualPrompt(event.target.value)} />
      </Field>
      <Field label="Prompt negativo">
        <Textarea rows={3} value={negativePrompt} onChange={(event) => setNegativePrompt(event.target.value)} />
      </Field>
      <p className="text-xs text-slate-500">
        A revisão cria uma nova versão imutável. Trocar o preset regenera o prompt com o provider mock antes de aplicar ajustes manuais.
      </p>
      <Button type="submit" busy={busy} disabled={!changed}>
        Criar nova versão visual
      </Button>
    </form>
  );
}
