"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Card, PageHeader } from "@/components/ui/page";
import { StatusBadge } from "@/components/ui/status-badge";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type {
  Business,
  ContentItem,
  Notification,
  Organization,
} from "@/types/api";

interface DashboardData {
  organization: Organization;
  businesses: Business[];
  contents: ContentItem[];
  notifications: Notification[];
}

export default function DashboardPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      const [organization, businessesResponse, contentsResponse, notificationsResponse] =
        await Promise.all([
          api.organizations.current(),
          api.businesses.list(),
          api.contents.list(),
          api.notifications.list(),
        ]);
      setData({
        organization,
        businesses: extractItems(businessesResponse),
        contents: extractItems(contentsResponse),
        notifications: extractItems(notificationsResponse),
      });
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar o início.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingState label="Preparando seu painel…" />;

  if (error) {
    return (
      <div className="space-y-4">
        <Alert>{error}</Alert>
        <Button onClick={() => void load()}>Tentar novamente</Button>
      </div>
    );
  }

  if (!data) return null;

  const isClient = roles.some((role) =>
    ["CLIENT_OWNER", "CLIENT_REVIEWER", "VIEWER"].includes(role),
  );
  const pendingStatuses = isClient
    ? ["CLIENT_REVIEW"]
    : ["INTERNAL_REVIEW", "CHANGES_REQUESTED"];
  const pending = data.contents.filter((item) => pendingStatuses.includes(item.status));
  const approved = data.contents.filter((item) => item.status === "APPROVED");
  const unread = data.notifications.filter((item) => !item.read_at);
  const recent = [...data.contents]
    .sort(
      (a, b) =>
        new Date(b.updated_at ?? b.created_at ?? 0).getTime() -
        new Date(a.updated_at ?? a.created_at ?? 0).getTime(),
    )
    .slice(0, 4);

  return (
    <>
      <PageHeader
        eyebrow={data.organization.name}
        title="Visão geral"
        description="Veja o que precisa de atenção e acompanhe o trabalho mais recente."
        action={
          pending.length > 0 ? (
            <Link
              href="/aprovacoes"
              className="inline-flex min-h-11 items-center rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-800"
            >
              Revisar aprovações ({pending.length})
            </Link>
          ) : null
        }
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumo">
        {[
          ["Aguardando ação", pending.length, "Revise os itens pendentes"],
          ["Conteúdos aprovados", approved.length, "Prontos para o próximo passo"],
          ["Notificações novas", unread.length, "Avisos ainda não lidos"],
          ["Empresas", data.businesses.length, "Marcas no seu acesso"],
        ].map(([label, value, help]) => (
          <Card key={label}>
            <p className="text-sm font-medium text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{help}</p>
          </Card>
        ))}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-slate-950">Conteúdos recentes</h2>
          <Link href="/conteudos" className="text-sm font-bold text-emerald-700 underline">
            Ver todos
          </Link>
        </div>
        {recent.length === 0 ? (
          <EmptyState
            title="Nenhum conteúdo criado"
            description="Quando a equipe gerar o primeiro conteúdo, ele aparecerá aqui com seu status de revisão."
            action={
              !isClient ? (
                <Link className="font-bold text-emerald-700 underline" href="/conteudos">
                  Criar conteúdo
                </Link>
              ) : undefined
            }
          />
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {recent.map((item) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate font-bold text-slate-950">
                      {item.current_version.title}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.current_version.channel} · {item.current_version.format} · versão {" "}
                      {item.current_version.version_number}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600">
                  {item.current_version.caption}
                </p>
                <p className="mt-3 text-xs text-slate-500">
                  Atualizado em {formatDateTime(item.updated_at ?? item.created_at)}
                </p>
              </Card>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
