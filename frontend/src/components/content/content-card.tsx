import type { ReactNode } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateTime } from "@/lib/format";
import type { ContentItem } from "@/types/api";

export function ContentCard({
  content,
  businessName,
  mediaPreviewUrl,
  mediaPreviewBusy = false,
  onRevealMedia,
  children,
}: {
  content: ContentItem;
  businessName?: string;
  mediaPreviewUrl?: string;
  mediaPreviewBusy?: boolean;
  onRevealMedia?: () => void;
  children?: ReactNode;
}) {
  const version = content.current_version;
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {businessName ? (
            <p className="text-xs font-bold tracking-wide text-emerald-700 uppercase">
              {businessName}
            </p>
          ) : null}
          <h2 className="mt-1 text-lg font-bold text-slate-950">{version.title}</h2>
          <p className="mt-1 text-xs text-slate-500">
            {version.channel} · {version.format} · versão {version.version_number}
          </p>
        </div>
        <StatusBadge status={content.status} />
      </div>

      <p className="mt-5 whitespace-pre-line text-sm leading-6 text-slate-700">
        {version.caption}
      </p>

      <dl className="mt-5 grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-bold text-slate-500 uppercase">Objetivo</dt>
          <dd className="mt-1 text-slate-800">{version.objective}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold text-slate-500 uppercase">Público</dt>
          <dd className="mt-1 text-slate-800">{version.audience || "Não informado"}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold text-slate-500 uppercase">Chamada para ação</dt>
          <dd className="mt-1 text-slate-800">{version.cta || "Não informada"}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold text-slate-500 uppercase">Origem</dt>
          <dd className="mt-1 text-slate-800">
            {version.provider_name === "mock"
              ? "Provider de demonstração"
              : version.provider_name || "Registrada no sistema"}
          </dd>
        </div>
      </dl>

      {(version.media_asset_ids?.length ?? 0) > 0 &&
      (mediaPreviewUrl || onRevealMedia) ? (
        <div className="mt-4 rounded-xl border border-slate-200 p-4">
          {mediaPreviewUrl ? (
            // A URL é curta, assinada e autorizada pelo backend para esta sessão.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={mediaPreviewUrl}
              alt={`Imagem em aprovação: ${version.title}`}
              className="max-h-[32rem] w-full rounded-xl bg-slate-100 object-contain"
            />
          ) : (
            <div className="flex aspect-video items-center justify-center rounded-xl bg-slate-100 text-sm font-semibold text-slate-500">
              Prévia visual privada
            </div>
          )}
          {onRevealMedia ? (
            <button
              type="button"
              onClick={onRevealMedia}
              disabled={mediaPreviewBusy}
              className="mt-3 min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800 disabled:cursor-wait disabled:opacity-60"
            >
              {mediaPreviewBusy
                ? "Liberando prévia…"
                : mediaPreviewUrl
                  ? "Renovar acesso à imagem"
                  : "Abrir imagem para revisar"}
            </button>
          ) : null}
        </div>
      ) : null}

      {version.visual_prompt ? (
        <details className="mt-4 rounded-xl border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-bold text-slate-900">
            Direção visual e prompt
          </summary>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
            {version.visual_prompt}
          </p>
          {version.negative_prompt ? (
            <p className="mt-3 whitespace-pre-wrap border-t border-slate-200 pt-3 text-xs leading-5 text-red-700">
              <strong>Evitar:</strong> {version.negative_prompt}
            </p>
          ) : null}
          <p className="mt-3 text-xs font-semibold text-slate-500">
            {version.media_asset_ids?.length ?? 0} arquivo(s) de mídia nesta versão
          </p>
        </details>
      ) : null}

      {content.approvals && content.approvals.length > 0 ? (
        <div className="mt-4 grid grid-cols-2 gap-2" aria-label="Decisões da versão">
          {content.approvals.map((approval) => (
            <div key={approval.id} className="rounded-xl border border-slate-200 px-3 py-2">
              <p className="text-xs font-bold text-slate-500 uppercase">
                {approval.component === "TEXT" ? "Texto" : "Imagem"}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {approval.status === "PENDING"
                  ? "Aguardando"
                  : approval.status === "APPROVED"
                    ? "Aprovado"
                    : approval.status === "CHANGES_REQUESTED"
                      ? "Alteração pedida"
                      : "Cancelado"}
              </p>
              {approval.decided_at ? (
                <p className="mt-1 text-xs text-slate-500">
                  Decisão em {formatDateTime(approval.decided_at)}
                </p>
              ) : null}
              {approval.decision_comment ? (
                <p className="mt-2 text-xs leading-5 text-slate-600">
                  {approval.decision_comment}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      {content.published_at ? (
        <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          Publicação manual registrada em {formatDateTime(content.published_at)}
          {content.publication_channel ? ` · ${content.publication_channel}` : ""}
        </p>
      ) : null}

      <p className="mt-4 text-xs text-slate-500">
        Atualizado em {formatDateTime(content.updated_at ?? content.created_at)}
      </p>

      {children ? (
        <div className="mt-5 border-t border-slate-200 pt-4">{children}</div>
      ) : null}
    </article>
  );
}
