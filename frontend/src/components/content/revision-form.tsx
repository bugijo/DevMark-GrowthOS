"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/form-controls";
import {
  hasMeaningfulRevisionChange,
  normalizeRevisionInput,
  revisionInputFrom,
} from "@/lib/content-revision";
import type { ContentItem, ContentRevisionInput } from "@/types/api";

export function RevisionForm({
  content,
  busy,
  onSubmit,
}: {
  content: ContentItem;
  busy: boolean;
  onSubmit: (input: ContentRevisionInput) => void | Promise<void>;
}) {
  const original = revisionInputFrom(content.current_version);
  const [draft, setDraft] = useState<ContentRevisionInput>(original);
  const changed = hasMeaningfulRevisionChange(original, draft);
  const requiredFieldsFilled = Boolean(
    draft.title.trim() && draft.caption.trim(),
  );
  const canSubmit = changed && requiredFieldsFilled;

  function update(field: keyof ContentRevisionInput, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    void onSubmit(normalizeRevisionInput(draft));
  }

  return (
    <div className="space-y-5">
      <section
        aria-labelledby={`feedback-${content.id}`}
        className="rounded-xl border border-orange-200 bg-orange-50 p-4"
      >
        <h3
          id={`feedback-${content.id}`}
          className="text-sm font-bold text-orange-950"
        >
          Feedback do cliente
        </h3>
        <p className="mt-2 whitespace-pre-line text-sm leading-6 text-orange-900">
          {content.change_request_comment?.trim() ||
            "O cliente não deixou um comentário adicional."}
        </p>
      </section>

      <form className="space-y-4" onSubmit={submit}>
        <p className="text-sm text-slate-600">
          Edite a versão abaixo. O sistema criará um novo rascunho; o envio
          para revisão interna será feito depois, na área Conteúdos.
        </p>
        <Field label="Título" required>
          <Input
            value={draft.title}
            onChange={(event) => update("title", event.target.value)}
            minLength={1}
            maxLength={300}
            required
          />
        </Field>
        <Field label="Legenda" required>
          <Textarea
            rows={6}
            value={draft.caption}
            onChange={(event) => update("caption", event.target.value)}
            minLength={1}
            required
          />
        </Field>
        <Field label="Chamada para ação (CTA)">
          <Input
            value={draft.cta}
            onChange={(event) => update("cta", event.target.value)}
            maxLength={300}
          />
        </Field>
        <p className="text-xs text-slate-500" aria-live="polite">
          {!requiredFieldsFilled
            ? "Título e legenda não podem ficar vazios."
            : changed
              ? "Alteração pronta para virar um novo rascunho."
              : "Altere ao menos um campo para criar uma nova versão."}
        </p>
        <Button type="submit" busy={busy} disabled={!canSubmit}>
          Criar rascunho revisado
        </Button>
      </form>
    </div>
  );
}
