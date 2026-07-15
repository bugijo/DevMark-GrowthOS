"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditLog } from "@/types/api";

const ACTION_LABELS: Record<string, string> = {
  "auth.login": "Entrada no sistema",
  "auth.logout": "Saída do sistema",
  "business.created": "Cliente cadastrado",
  "business.updated": "Cliente atualizado",
  "business.archived": "Cliente arquivado",
  "brand_profile.created": "Brand Kit criado",
  "brand_profile.updated": "Brand Kit atualizado",
  "membership.client_reviewer_created": "Revisor adicionado",
  "content.generated": "Conteúdo gerado",
  "content.submitted_internal": "Enviado para revisão interna",
  "content.sent_to_client": "Enviado para o cliente",
  "content.approved_by_client": "Aprovado pelo cliente",
  "content.changes_requested": "Alteração solicitada",
  "notification.read": "Notificação lida",
};

export default function AuditLogsPage() {
  const { activeOrganizationId } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      setLogs(extractItems(await api.auditLogs.list()));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os registros.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <PageHeader
        eyebrow="Auditoria"
        title="Registros de atividade"
        description="Histórico somente de leitura das ações relevantes desta organização."
        action={
          <Button variant="secondary" onClick={() => void load()} disabled={loading}>
            Atualizar
          </Button>
        }
      />

      {error ? (
        <div className="space-y-4">
          <Alert>{error}</Alert>
          <Button onClick={() => void load()}>Tentar novamente</Button>
        </div>
      ) : null}
      {loading ? <LoadingState label="Carregando registros…" /> : null}
      {!loading && !error && logs.length === 0 ? (
        <EmptyState
          title="Nenhuma atividade registrada"
          description="Cadastros, mudanças de status e decisões aparecerão aqui de forma auditável."
        />
      ) : null}

      {!loading && !error && logs.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <ul className="divide-y divide-slate-200">
            {logs.map((log) => (
              <li key={log.id} className="p-4 sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="font-bold text-slate-950">
                      {ACTION_LABELS[log.action] ?? log.action}
                    </h2>
                    <p className="mt-1 text-sm text-slate-600">
                      {log.resource_type}
                      {log.resource_id ? ` · ${log.resource_id}` : ""}
                    </p>
                    {log.details && Object.keys(log.details).length > 0 ? (
                      <details className="mt-3 text-xs text-slate-600">
                        <summary className="min-h-9 cursor-pointer font-bold text-slate-700">
                          Ver detalhes seguros
                        </summary>
                        <pre className="mt-2 max-w-full overflow-x-auto rounded-lg bg-slate-950 p-3 text-slate-100">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </details>
                    ) : null}
                  </div>
                  <time className="shrink-0 text-xs text-slate-500" dateTime={log.created_at}>
                    {formatDateTime(log.created_at)}
                  </time>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
