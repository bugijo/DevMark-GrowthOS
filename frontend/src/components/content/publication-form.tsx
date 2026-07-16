"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/form-controls";
import { localDateTimeToIso, manualPublicationKey } from "@/lib/phase2";
import type { ContentItem, ManualPublicationInput } from "@/types/api";

function currentLocalDateTime(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

export function PublicationForm({
  content,
  busy,
  onSubmit,
}: {
  content: ContentItem;
  busy: boolean;
  onSubmit: (input: ManualPublicationInput) => void | Promise<void>;
}) {
  const [channel, setChannel] = useState(content.current_version.channel || "INSTAGRAM");
  const [publishedAt, setPublishedAt] = useState(currentLocalDateTime);
  const [reference, setReference] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const iso = localDateTimeToIso(publishedAt);
    if (!iso || !confirmed) return;
    void onSubmit({
      channel,
      published_at: iso,
      reference: reference.trim() || undefined,
      idempotency_key: manualPublicationKey(content.id, iso),
    });
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <h3 className="text-sm font-bold text-emerald-950">Registrar publicação manual</h3>
        <p className="mt-1 text-sm text-emerald-900">
          Esta ação só registra o que uma pessoa já publicou. O GrowthOS não enviará nada à rede social.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Canal" required>
          <Select value={channel} onChange={(event) => setChannel(event.target.value)}>
            <option value="INSTAGRAM">Instagram</option>
            <option value="FACEBOOK">Facebook</option>
            <option value="LINKEDIN">LinkedIn</option>
            <option value="OUTRO">Outro</option>
          </Select>
        </Field>
        <Field label="Publicado em" required>
          <Input type="datetime-local" value={publishedAt} onChange={(event) => setPublishedAt(event.target.value)} required />
        </Field>
      </div>
      <Field label="Link ou referência">
        <Input type="url" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="https://…" maxLength={2048} />
      </Field>
      <label className="flex items-start gap-3 text-sm text-slate-700">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-0.5 size-5 accent-emerald-700" />
        Confirmo que esta publicação já foi realizada manualmente fora do GrowthOS.
      </label>
      <Button type="submit" busy={busy} disabled={!confirmed || !publishedAt}>
        Registrar como publicado
      </Button>
    </form>
  );
}
