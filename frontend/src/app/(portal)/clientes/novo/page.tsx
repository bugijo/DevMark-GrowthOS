"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { api } from "@/lib/api";

export default function NewBusinessPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [segment, setSegment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const business = await api.businesses.create({
        name: name.trim(),
        segment: segment.trim(),
      });
      router.push(`/clientes/${business.id}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível cadastrar o cliente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Clientes"
        title="Novo cliente"
        description="Informe os dados básicos. O Brand Kit será o próximo passo."
      />
      <Card className="max-w-2xl">
        <form className="space-y-5" onSubmit={handleSubmit}>
          {error ? <Alert>{error}</Alert> : null}
          <Field label="Nome da empresa" required>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Ex.: Clínica Veterinária Amigo Pet"
              maxLength={160}
              required
              autoFocus
            />
          </Field>
          <Field
            label="Segmento"
            hint="Use uma descrição simples, como clínica veterinária ou pet shop."
            required
          >
            <Input
              value={segment}
              onChange={(event) => setSegment(event.target.value)}
              placeholder="Clínica veterinária"
              maxLength={120}
              required
            />
          </Field>
          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <Link
              href="/clientes"
              className="inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-sm font-bold text-slate-700 hover:bg-slate-100"
            >
              Cancelar
            </Link>
            <Button type="submit" busy={submitting}>
              {submitting ? "Cadastrando…" : "Cadastrar e continuar"}
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
