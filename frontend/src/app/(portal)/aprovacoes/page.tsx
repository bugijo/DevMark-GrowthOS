"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ContentCard } from "@/components/content/content-card";
import { RevisionForm } from "@/components/content/revision-form";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Textarea } from "@/components/ui/form-controls";
import { PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import type {
  Business,
  ContentItem,
  ContentRevisionInput,
} from "@/types/api";

export default function ApprovalsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const isClientReviewer = roles.some((role) =>
    ["CLIENT_OWNER", "CLIENT_REVIEWER"].includes(role),
  );
  const isAgencyManager = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN"].includes(role),
  );

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      const [businessResponse, contentResponse] = await Promise.all([
        api.businesses.list(),
        api.contents.list(),
      ]);
      setBusinesses(extractItems(businessResponse));
      setContents(extractItems(contentResponse));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar as aprovações.",
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

  const actionable = contents.filter((content) => {
    if (isClientReviewer) return content.status === "CLIENT_REVIEW";
    if (isAgencyManager) {
      return ["INTERNAL_REVIEW", "CHANGES_REQUESTED", "CLIENT_REVIEW"].includes(
        content.status,
      );
    }
    return false;
  });

  async function act(
    content: ContentItem,
    action: "approve" | "changes" | "send",
  ) {
    const comment = comments[content.id]?.trim() ?? "";
    if (action === "changes" && !comment) {
      setError("Explique o que precisa mudar antes de enviar o pedido.");
      return;
    }

    setActionId(content.id);
    setError(null);
    setSuccess(null);
    try {
      let updated: ContentItem;
      if (action === "approve") updated = await api.contents.approve(content.id);
      else if (action === "changes") {
        updated = await api.contents.requestChanges(content.id, comment);
      } else {
        updated = await api.contents.sendToClient(content.id);
      }

      setContents((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setComments((current) => ({ ...current, [content.id]: "" }));
      const messages = {
        approve: "Conteúdo aprovado. A equipe foi notificada.",
        changes: "Pedido de alteração registrado. A equipe foi notificada.",
        send: "Conteúdo enviado para o cliente revisar.",
      };
      setSuccess(messages[action]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível registrar a decisão.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function createRevision(
    content: ContentItem,
    input: ContentRevisionInput,
  ) {
    setActionId(content.id);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.contents.createRevision(content.id, input);
      setContents((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSuccess(
        "Novo rascunho criado. Revise-o na área Conteúdos antes de enviá-lo para revisão interna.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível criar a nova versão.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Revisão"
        title="Aprovações"
        description={
          isClientReviewer
            ? "Confira a versão atual e registre sua decisão. Nada será publicado automaticamente."
            : "Revise o conteúdo antes de enviá-lo ao cliente."
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      {loading ? <LoadingState label="Carregando aprovações…" /> : null}

      {!loading && !error && actionable.length === 0 ? (
        <EmptyState
          title="Tudo revisado por enquanto"
          description="Quando um conteúdo precisar da sua decisão, ele aparecerá aqui com a versão exata que está em análise."
        />
      ) : null}

      {!loading && actionable.length > 0 ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {actionable.map((content) => (
            <ContentCard
              key={content.id}
              content={content}
              businessName={businessById.get(content.business_id)}
            >
              {isClientReviewer && content.status === "CLIENT_REVIEW" ? (
                <div className="space-y-4">
                  <label className="block text-sm font-semibold text-slate-800">
                    Comentário para pedir alteração
                    <Textarea
                      rows={3}
                      value={comments[content.id] ?? ""}
                      onChange={(event) =>
                        setComments((current) => ({
                          ...current,
                          [content.id]: event.target.value,
                        }))
                      }
                      placeholder="Explique de forma objetiva o que precisa mudar"
                      maxLength={2000}
                    />
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Button
                      variant="secondary"
                      busy={actionId === content.id}
                      onClick={() => void act(content, "changes")}
                    >
                      Pedir alteração
                    </Button>
                    <Button
                      busy={actionId === content.id}
                      onClick={() => void act(content, "approve")}
                    >
                      Aprovar esta versão
                    </Button>
                  </div>
                </div>
              ) : null}

              {isAgencyManager && content.status === "INTERNAL_REVIEW" ? (
                <Button
                  busy={actionId === content.id}
                  onClick={() => void act(content, "send")}
                >
                  Concluir revisão e enviar ao cliente
                </Button>
              ) : null}

              {isAgencyManager && content.status === "CHANGES_REQUESTED" ? (
                <RevisionForm
                  key={content.current_version.id}
                  content={content}
                  busy={actionId === content.id}
                  onSubmit={(input) => createRevision(content, input)}
                />
              ) : null}

              {isAgencyManager && content.status === "CLIENT_REVIEW" ? (
                <p className="text-sm text-slate-600">
                  Aguardando a decisão do cliente. O sistema não aprova por silêncio.
                </p>
              ) : null}
            </ContentCard>
          ))}
        </div>
      ) : null}
    </>
  );
}
