"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ContentCard } from "@/components/content/content-card";
import { PublicationForm } from "@/components/content/publication-form";
import { RevisionForm } from "@/components/content/revision-form";
import { VisualRevisionForm } from "@/components/content/visual-revision-form";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Textarea } from "@/components/ui/form-controls";
import { PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { ApiError, api, extractItems } from "@/lib/api";
import { approvalFor } from "@/lib/phase2";
import type {
  ApprovalComponent,
  Business,
  ContentItem,
  ContentRevisionInput,
  ManualPublicationInput,
  MediaAsset,
  VisualPreset,
  VisualRevisionInput,
} from "@/types/api";

interface VisualOptions {
  presets: VisualPreset[];
  media: MediaAsset[];
}

export default function ApprovalsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [visualOptions, setVisualOptions] = useState<Record<string, VisualOptions>>({});
  const [mediaPreviewUrls, setMediaPreviewUrls] = useState<Record<string, string>>({});
  const [previewBusy, setPreviewBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const isClientReviewer = roles.some((role) =>
    ["CLIENT_OWNER", "CLIENT_REVIEWER"].includes(role),
  );
  const canSend = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"].includes(role),
  );
  const canEditText = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR"].includes(role),
  );
  const canEditVisual = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "DESIGNER"].includes(role),
  );
  const canPublish = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CONTENT_EDITOR"].includes(role),
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
      const nextBusinesses = extractItems(businessResponse);
      setBusinesses(nextBusinesses);
      setContents(extractItems(contentResponse));
      if (canEditVisual) {
        const loaded = await Promise.all(
          nextBusinesses.map(async (business) => {
            const [presets, media] = await Promise.all([
              api.catalogs.presets.list(business.id),
              api.media.list(business.id),
            ]);
            return [business.id, { presets, media }] as const;
          }),
        );
        setVisualOptions(Object.fromEntries(loaded));
      } else {
        setVisualOptions({});
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar as aprovações.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId, canEditVisual]);

  useEffect(() => {
    void load();
  }, [load]);

  const businessById = useMemo(
    () => new Map(businesses.map((business) => [business.id, business.name])),
    [businesses],
  );

  const actionable = contents.filter((content) => {
    if (isClientReviewer) {
      return ["CLIENT_REVIEW", "CHANGES_REQUESTED", "APPROVED"].includes(
        content.status,
      );
    }
    if (content.status === "INTERNAL_REVIEW") return canSend;
    if (content.status === "CHANGES_REQUESTED") return canEditText || canEditVisual;
    if (["APPROVED", "SCHEDULED"].includes(content.status)) return canPublish;
    return content.status === "CLIENT_REVIEW" && (canSend || canEditText || canEditVisual);
  });

  function commentKey(contentId: string, component: ApprovalComponent): string {
    return `${contentId}:${component}`;
  }

  function replaceContent(updated: ContentItem) {
    setContents((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
  }

  async function decideComponent(
    content: ContentItem,
    component: ApprovalComponent,
    decision: "approve" | "request-changes",
  ) {
    const key = commentKey(content.id, component);
    const comment = comments[key]?.trim() ?? "";
    if (
      component === "IMAGE" &&
      (content.current_version.media_asset_ids?.length ?? 0) === 0
    ) {
      setError("A imagem precisa estar vinculada e visível antes da decisão.");
      return;
    }
    if (decision === "request-changes" && !comment) {
      setError(`Explique o que precisa mudar em ${component === "TEXT" ? "texto" : "imagem"}.`);
      return;
    }
    setActionId(key);
    setError(null);
    setSuccess(null);
    try {
      replaceContent(
        await api.contents.decideComponent(content.id, component, decision, comment || undefined),
      );
      setComments((current) => ({ ...current, [key]: "" }));
      setSuccess(
        decision === "approve"
          ? `${component === "TEXT" ? "Texto aprovado" : "Imagem aprovada"}. O conteúdo só avança quando ambos estiverem aprovados.`
          : "Pedido de alteração registrado para o componente correto.",
      );
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        try {
          replaceContent(await api.contents.get(content.id));
        } catch {
          // A mensagem original continua sendo a informação mais útil.
        }
      }
      setError(
        requestError instanceof ApiError && requestError.status === 409
          ? `${requestError.message}. A versão atual foi recarregada.`
          : requestError instanceof Error
            ? requestError.message
            : "Não foi possível registrar a decisão.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function revealMedia(content: ContentItem) {
    const mediaAssetId = content.current_version.media_asset_ids?.[0];
    if (!mediaAssetId) {
      setError("Nenhuma imagem foi vinculada a esta versão.");
      return;
    }
    setPreviewBusy(content.id);
    setError(null);
    try {
      const signed = await api.media.signedUrl(mediaAssetId);
      setMediaPreviewUrls((current) => ({ ...current, [content.id]: signed.url }));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível abrir a imagem privada.",
      );
    } finally {
      setPreviewBusy(null);
    }
  }

  async function sendToClient(content: ContentItem) {
    setActionId(content.id);
    setError(null);
    try {
      replaceContent(await api.contents.sendToClient(content.id));
      setSuccess("Texto e imagem enviados em aprovações separadas.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível enviar.");
    } finally {
      setActionId(null);
    }
  }

  async function createTextRevision(content: ContentItem, input: ContentRevisionInput) {
    setActionId(content.id);
    setError(null);
    try {
      replaceContent(await api.contents.createRevision(content.id, input));
      setSuccess("Nova versão textual criada como rascunho.");
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Não foi possível criar a versão.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function createVisualRevision(content: ContentItem, input: VisualRevisionInput) {
    setActionId(content.id);
    setError(null);
    try {
      replaceContent(await api.contents.createVisualRevision(content.id, input));
      setSuccess("Nova versão visual criada. A versão anterior permaneceu imutável.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível criar a revisão visual.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function publish(content: ContentItem, input: ManualPublicationInput) {
    setActionId(content.id);
    setError(null);
    try {
      replaceContent(await api.contents.recordPublication(content.id, input));
      setSuccess("Publicação manual registrada. Nenhuma integração externa foi acionada.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível registrar a publicação.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Revisão por componente"
        title="Aprovações"
        description={
          isClientReviewer
            ? "Decida texto e imagem separadamente. A publicação nunca acontece por esta tela."
            : "Conduza revisões textuais e visuais e registre publicações feitas manualmente."
        }
      />
      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      {loading ? <LoadingState label="Carregando aprovações…" /> : null}
      {!loading && !error && actionable.length === 0 ? (
        <EmptyState
          title="Tudo revisado por enquanto"
          description="Quando uma versão precisar da sua ação, ela aparecerá aqui com suas decisões de texto e imagem."
        />
      ) : null}

      {!loading && actionable.length > 0 ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {actionable.map((content) => {
            const textApproval = approvalFor(content.approvals, "TEXT");
            const imageApproval = approvalFor(content.approvals, "IMAGE");
            const options = visualOptions[content.business_id] ?? { presets: [], media: [] };
            return (
              <ContentCard
                key={`${content.id}-${content.current_version.id}`}
                content={content}
                businessName={businessById.get(content.business_id)}
                mediaPreviewUrl={mediaPreviewUrls[content.id]}
                mediaPreviewBusy={previewBusy === content.id}
                onRevealMedia={
                  (content.current_version.media_asset_ids?.length ?? 0) > 0
                    ? () => void revealMedia(content)
                    : undefined
                }
              >
                {isClientReviewer && content.status === "CLIENT_REVIEW" ? (
                  <div className="space-y-5">
                    {(["TEXT", "IMAGE"] as const).map((component) => {
                      const approval = component === "TEXT" ? textApproval : imageApproval;
                      const key = commentKey(content.id, component);
                      return (
                        <section key={component} className="rounded-xl border border-slate-200 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <h3 className="font-bold text-slate-950">
                              {component === "TEXT" ? "Decisão do texto" : "Decisão da imagem"}
                            </h3>
                            <span className="text-xs font-bold text-slate-500">
                              {approval?.status ?? "INDISPONÍVEL"}
                            </span>
                          </div>
                          {approval?.status === "PENDING" ? (
                            <>
                              <label className="mt-3 block text-sm font-semibold text-slate-800">
                                Comentário
                                <Textarea
                                  rows={2}
                                  value={comments[key] ?? ""}
                                  onChange={(event) =>
                                    setComments((current) => ({ ...current, [key]: event.target.value }))
                                  }
                                  placeholder="Obrigatório ao pedir alteração"
                                  maxLength={2000}
                                />
                              </label>
                              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                <Button
                                  variant="secondary"
                                  busy={actionId === key}
                                  onClick={() => void decideComponent(content, component, "request-changes")}
                                >
                                  Pedir alteração
                                </Button>
                                <Button
                                  busy={actionId === key}
                                  disabled={
                                    component === "IMAGE" &&
                                    (content.current_version.media_asset_ids?.length ?? 0) === 0
                                  }
                                  onClick={() => void decideComponent(content, component, "approve")}
                                >
                                  Aprovar {component === "TEXT" ? "texto" : "imagem"}
                                </Button>
                              </div>
                              {component === "IMAGE" &&
                              (content.current_version.media_asset_ids?.length ?? 0) === 0 ? (
                                <p className="mt-2 text-xs font-semibold text-amber-700">
                                  A equipe precisa vincular uma imagem antes da aprovação.
                                </p>
                              ) : null}
                            </>
                          ) : (
                            <p className="mt-2 text-sm text-slate-600">
                              Esta parte já recebeu uma decisão nesta versão.
                            </p>
                          )}
                        </section>
                      );
                    })}
                  </div>
                ) : null}

                {canSend && content.status === "INTERNAL_REVIEW" ? (
                  <Button busy={actionId === content.id} onClick={() => void sendToClient(content)}>
                    Concluir revisão e enviar texto + imagem
                  </Button>
                ) : null}

                {canEditText &&
                content.status === "CHANGES_REQUESTED" &&
                (!textApproval || textApproval.status === "CHANGES_REQUESTED") ? (
                  <RevisionForm
                    content={content}
                    busy={actionId === content.id}
                    onSubmit={(input) => createTextRevision(content, input)}
                  />
                ) : null}

                {canEditVisual &&
                content.status === "CHANGES_REQUESTED" &&
                imageApproval?.status === "CHANGES_REQUESTED" ? (
                  <VisualRevisionForm
                    content={content}
                    presets={options.presets}
                    media={options.media}
                    busy={actionId === content.id}
                    onSubmit={(input) => createVisualRevision(content, input)}
                  />
                ) : null}

                {content.status === "CLIENT_REVIEW" && !isClientReviewer ? (
                  <p className="text-sm text-slate-600">
                    Aguardando as decisões separadas do cliente. O conteúdo só será aprovado quando texto e imagem estiverem aprovados.
                  </p>
                ) : null}

                {canPublish && ["APPROVED", "SCHEDULED"].includes(content.status) ? (
                  <PublicationForm
                    content={content}
                    busy={actionId === content.id}
                    onSubmit={(input) => publish(content, input)}
                  />
                ) : null}
              </ContentCard>
            );
          })}
        </div>
      ) : null}
    </>
  );
}
