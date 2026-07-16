"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { ApiError, api } from "@/lib/api";
import { joinCommaSeparated, splitCommaSeparated } from "@/lib/format";
import type { BrandProfile, Business } from "@/types/api";

interface BrandFormState {
  brand_name: string;
  public_name: string;
  description: string;
  segment: string;
  audience: string;
  primary_colors: string;
  tone_of_voice: string;
  preferred_words: string;
  forbidden_words: string;
  slogan: string;
  differentiators: string;
  services: string;
  contacts: string;
  links: string;
  calls_to_action: string;
  internal_notes: string;
}

function emptyBrand(business: Business): BrandFormState {
  return {
    brand_name: business.name,
    public_name: business.name,
    description: "",
    segment: business.segment,
    audience: "",
    primary_colors: "",
    tone_of_voice: "",
    preferred_words: "",
    forbidden_words: "",
    slogan: "",
    differentiators: "",
    services: "",
    contacts: "",
    links: "",
    calls_to_action: "",
    internal_notes: "",
  };
}

function brandToForm(profile: BrandProfile): BrandFormState {
  return {
    brand_name: profile.brand_name ?? "",
    public_name: profile.public_name ?? "",
    description: profile.description ?? "",
    segment: profile.segment ?? "",
    audience: profile.audience ?? "",
    primary_colors: joinCommaSeparated(profile.primary_colors),
    tone_of_voice: profile.tone_of_voice ?? "",
    preferred_words: joinCommaSeparated(profile.preferred_words),
    forbidden_words: joinCommaSeparated(profile.forbidden_words),
    slogan: profile.slogan ?? "",
    differentiators: joinCommaSeparated(profile.differentiators),
    services: joinCommaSeparated(profile.services),
    contacts:
      typeof profile.contacts === "string"
        ? profile.contacts
        : profile.contacts
          ? Object.values(profile.contacts).join(", ")
          : "",
    links: joinCommaSeparated(profile.links),
    calls_to_action: joinCommaSeparated(profile.calls_to_action),
    internal_notes: profile.internal_notes ?? "",
  };
}

function formToBrand(form: BrandFormState): BrandProfile {
  return {
    ...form,
    primary_colors: splitCommaSeparated(form.primary_colors),
    preferred_words: splitCommaSeparated(form.preferred_words),
    forbidden_words: splitCommaSeparated(form.forbidden_words),
    differentiators: splitCommaSeparated(form.differentiators),
    services: splitCommaSeparated(form.services),
    links: splitCommaSeparated(form.links),
    calls_to_action: splitCommaSeparated(form.calls_to_action),
  };
}

export default function BusinessProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [business, setBusiness] = useState<Business | null>(null);
  const [form, setForm] = useState<BrandFormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const businessData = await api.businesses.get(id);
      setBusiness(businessData);
      try {
        const profile = await api.businesses.getBrandProfile(id);
        setForm(brandToForm(profile));
      } catch (profileError) {
        if (profileError instanceof ApiError && profileError.status === 404) {
          setForm(emptyBrand(businessData));
        } else {
          throw profileError;
        }
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar o perfil.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  function update<K extends keyof BrandFormState>(key: K, value: BrandFormState[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  async function saveBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const saved = await api.businesses.updateBrandProfile(id, formToBrand(form));
      setForm(brandToForm(saved));
      setSuccess("Brand Kit salvo. Os próximos conteúdos já podem usar estas orientações.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível salvar o Brand Kit.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState label="Carregando perfil e Brand Kit…" />;

  if (error && !business) {
    return (
      <div className="space-y-4">
        <Alert>{error}</Alert>
        <Button onClick={() => void load()}>Tentar novamente</Button>
      </div>
    );
  }

  if (!business || !form) return null;

  return (
    <>
      <PageHeader
        eyebrow="Cliente"
        title={business.name}
        description="Mantenha as orientações da marca claras para a equipe e para o provider de conteúdo."
        action={
          <Link
            href={`/conteudos?business_id=${business.id}`}
            className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 bg-white px-4 text-sm font-bold text-slate-800 hover:bg-slate-50"
          >
            Ver conteúdos
          </Link>
        }
      />

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.5fr)]">
        <Card>
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-950">Brand Kit básico</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Campos separados por vírgula aceitam vários itens. Não inclua dados clínicos ou segredos.
            </p>
          </div>
          <form className="space-y-6" onSubmit={saveBrand}>
            {error ? <Alert>{error}</Alert> : null}
            {success ? <Alert tone="success">{success}</Alert> : null}

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Nome da marca" required>
                <Input
                  value={form.brand_name}
                  onChange={(event) => update("brand_name", event.target.value)}
                  required
                />
              </Field>
              <Field label="Nome público" required>
                <Input
                  value={form.public_name}
                  onChange={(event) => update("public_name", event.target.value)}
                  required
                />
              </Field>
              <Field label="Segmento" required>
                <Input
                  value={form.segment}
                  onChange={(event) => update("segment", event.target.value)}
                  required
                />
              </Field>
              <Field label="Cores principais" hint="Ex.: #146B5F, branco" required>
                <Input
                  value={form.primary_colors}
                  onChange={(event) => update("primary_colors", event.target.value)}
                  required
                />
              </Field>
            </div>

            <Field label="Descrição" required>
              <Textarea
                rows={4}
                value={form.description}
                onChange={(event) => update("description", event.target.value)}
                required
              />
            </Field>
            <Field label="Público principal" required>
              <Textarea
                rows={3}
                value={form.audience}
                onChange={(event) => update("audience", event.target.value)}
                required
              />
            </Field>
            <Field label="Tom de voz" required>
              <Input
                value={form.tone_of_voice}
                onChange={(event) => update("tone_of_voice", event.target.value)}
                placeholder="Acolhedor, claro e profissional"
                required
              />
            </Field>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Palavras preferidas">
                <Input
                  value={form.preferred_words}
                  onChange={(event) => update("preferred_words", event.target.value)}
                />
              </Field>
              <Field label="Palavras proibidas">
                <Input
                  value={form.forbidden_words}
                  onChange={(event) => update("forbidden_words", event.target.value)}
                />
              </Field>
              <Field label="Slogan">
                <Input
                  value={form.slogan}
                  onChange={(event) => update("slogan", event.target.value)}
                />
              </Field>
              <Field label="Diferenciais">
                <Input
                  value={form.differentiators}
                  onChange={(event) => update("differentiators", event.target.value)}
                />
              </Field>
              <Field label="Serviços">
                <Input
                  value={form.services}
                  onChange={(event) => update("services", event.target.value)}
                />
              </Field>
              <Field label="Chamadas para ação">
                <Input
                  value={form.calls_to_action}
                  onChange={(event) => update("calls_to_action", event.target.value)}
                />
              </Field>
            </div>

            <Field label="Contatos">
              <Input
                value={form.contacts}
                onChange={(event) => update("contacts", event.target.value)}
                placeholder="Telefone, e-mail ou endereço público"
              />
            </Field>
            <Field label="Links">
              <Input
                value={form.links}
                onChange={(event) => update("links", event.target.value)}
                placeholder="https://site.com.br, https://instagram.com/..."
              />
            </Field>
            <Field label="Observações internas">
              <Textarea
                rows={3}
                value={form.internal_notes}
                onChange={(event) => update("internal_notes", event.target.value)}
              />
            </Field>

            <div className="flex justify-end">
              <Button type="submit" busy={saving}>
                {saving ? "Salvando…" : "Salvar Brand Kit"}
              </Button>
            </div>
          </form>
        </Card>

        <ReviewerForm businessId={business.id} />
      </div>
    </>
  );
}

function ReviewerForm({ businessId }: { businessId: string }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(false);
    try {
      await api.businesses.addReviewer(businessId, {
        name: name.trim(),
        email: email.trim(),
        password,
      });
      setName("");
      setEmail("");
      setPassword("");
      setSuccess(true);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível adicionar o revisor.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-bold text-slate-950">Adicionar revisor</h2>
      <p className="mt-1 text-sm leading-6 text-slate-600">
        Acesso provisório para o piloto local. A senha temporária não será exibida novamente.
      </p>
      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        {success ? (
          <Alert tone="success">
            Revisor adicionado. Compartilhe o acesso somente por um canal seguro.
          </Alert>
        ) : null}
        <Field label="Nome" required>
          <Input value={name} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label="E-mail" required>
          <Input
            type="email"
            autoComplete="off"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </Field>
        <Field label="Senha temporária" hint="Use pelo menos 12 caracteres." required>
          <Input
            type="password"
            autoComplete="new-password"
            minLength={12}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </Field>
        <Button type="submit" busy={submitting} className="w-full">
          {submitting ? "Adicionando…" : "Adicionar revisor"}
        </Button>
      </form>
    </Card>
  );
}
