import type { ReactNode } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateTime } from "@/lib/format";
import type { ContentItem } from "@/types/api";

export function ContentCard({
  content,
  businessName,
  children,
}: {
  content: ContentItem;
  businessName?: string;
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

      <p className="mt-4 text-xs text-slate-500">
        Atualizado em {formatDateTime(content.updated_at ?? content.created_at)}
      </p>

      {children ? (
        <div className="mt-5 border-t border-slate-200 pt-4">{children}</div>
      ) : null}
    </article>
  );
}
