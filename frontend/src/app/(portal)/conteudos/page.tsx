"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ContentCard } from "@/components/content/content-card";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Select, Textarea } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import type { Business, ContentItem } from "@/types/api";

const MANAGER_ROLES = ["SUPER_ADMIN", "AGENCY_ADMIN"];

export default function ContentsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState("all");
  const [objective, setObjective] = useState("");
  const [channel, setChannel] = useState("INSTAGRAM");
  const [format, setFormat] = useState("FEED");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canManage = roles.some((role) => MANAGER_ROLES.includes(role));

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

      const requestedBusiness = new URLSearchParams(window.location.search).get(
        "business_id",
      );
      if (
        requestedBusiness &&
        nextBusinesses.some((business) => business.id === requestedBusiness)
      ) {
        setSelectedBusiness(requestedBusiness);
      } else {
        setSelectedBusiness((current) =>
          nextBusinesses.some((business) => business.id === current) ? current : "all",
        );
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os conteúdos.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId]);

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

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedBusiness === "all") {
      setError("Escolha uma empresa antes de gerar o conteúdo.");
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
      });
      setContents((current) => [created, ...current]);
      setObjective("");
      setSuccess("Rascunho criado com o provider mock. Revise antes de enviar.");
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

  async function transition(
    content: ContentItem,
    action: "internal" | "client",
  ) {
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
          : "Conteúdo enviado ao cliente e notificação criada.",
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
        eyebrow="Produção"
        title="Conteúdos"
        description="Gere rascunhos com o provider mock e conduza cada versão pelas revisões."
      />

      {canManage ? (
        <Card>
          <div className="mb-5">
            <h2 className="text-lg font-bold text-slate-950">Criar conteúdo mock</h2>
            <p className="mt-1 text-sm text-slate-600">
              O resultado é um rascunho. Nada será publicado automaticamente.
            </p>
          </div>
          <form className="grid gap-4 lg:grid-cols-4" onSubmit={generate}>
            <Field label="Empresa" required>
              <Select
                value={selectedBusiness}
                onChange={(event) => setSelectedBusiness(event.target.value)}
                required
              >
                <option value="all">Escolha uma empresa</option>
                {businesses.map((business) => (
                  <option key={business.id} value={business.id}>
                    {business.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Canal" required>
              <Select value={channel} onChange={(event) => setChannel(event.target.value)}>
                <option value="INSTAGRAM">Instagram</option>
                <option value="FACEBOOK">Facebook</option>
                <option value="LINKEDIN">LinkedIn</option>
              </Select>
            </Field>
            <Field label="Formato" required>
              <Select value={format} onChange={(event) => setFormat(event.target.value)}>
                <option value="FEED">Feed</option>
                <option value="CAROUSEL">Carrossel</option>
                <option value="STORY">Story</option>
                <option value="REELS">Reels</option>
              </Select>
            </Field>
            <div className="lg:col-span-4">
              <Field label="Objetivo do conteúdo" required>
                <Textarea
                  rows={3}
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  placeholder="Ex.: explicar por que consultas preventivas são importantes"
                  minLength={2}
                  maxLength={1000}
                  required
                />
              </Field>
            </div>
            <div className="lg:col-span-4 lg:justify-self-end">
              <Button type="submit" busy={generating} disabled={businesses.length === 0}>
                {generating ? "Gerando…" : "Gerar rascunho"}
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-950">Biblioteca</h2>
          <p className="text-sm text-slate-600">{filtered.length} conteúdo(s) neste filtro</p>
        </div>
        {businesses.length > 1 ? (
          <label className="text-sm font-semibold text-slate-700">
            Filtrar por empresa
            <Select
              className="sm:min-w-64"
              value={selectedBusiness}
              onChange={(event) => setSelectedBusiness(event.target.value)}
            >
              <option value="all">Todas as empresas</option>
              {businesses.map((business) => (
                <option key={business.id} value={business.id}>
                  {business.name}
                </option>
              ))}
            </Select>
          </label>
        ) : null}
      </div>

      {loading ? <LoadingState label="Carregando conteúdos…" /> : null}
      {!loading && !error && filtered.length === 0 ? (
        <EmptyState
          title="Nenhum conteúdo neste filtro"
          description={
            canManage
              ? "Escolha uma empresa, descreva o objetivo e gere o primeiro rascunho."
              : "A equipe ainda não disponibilizou conteúdos para o seu acesso."
          }
        />
      ) : null}
      {!loading && filtered.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {filtered.map((content) => (
            <ContentCard
              key={content.id}
              content={content}
              businessName={businessById.get(content.business_id)}
            >
              {canManage &&
              ["DRAFT", "CHANGES_REQUESTED"].includes(content.status) ? (
                <Button
                  variant="secondary"
                  busy={actionId === content.id}
                  onClick={() => void transition(content, "internal")}
                >
                  Enviar para revisão interna
                </Button>
              ) : null}
              {canManage && content.status === "INTERNAL_REVIEW" ? (
                <Button
                  busy={actionId === content.id}
                  onClick={() => void transition(content, "client")}
                >
                  Enviar ao cliente
                </Button>
              ) : null}
              {!canManage ? (
                <p className="text-sm text-slate-600">
                  Consulte a área de aprovações para tomar uma decisão quando solicitado.
                </p>
              ) : null}
            </ContentCard>
          ))}
        </div>
      ) : null}
    </>
  );
}
