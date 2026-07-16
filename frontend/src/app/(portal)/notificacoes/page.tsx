"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Notification } from "@/types/api";

export default function NotificationsPage() {
  const { activeOrganizationId } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [loading, setLoading] = useState(true);
  const [readingId, setReadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      setNotifications(extractItems(await api.notifications.list()));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar as notificações.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function markAsRead(notification: Notification) {
    setReadingId(notification.id);
    setError(null);
    try {
      const updated = await api.notifications.read(notification.id);
      setNotifications((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível marcar a notificação como lida.",
      );
    } finally {
      setReadingId(null);
    }
  }

  const unreadCount = notifications.filter((notification) => !notification.read_at).length;
  const visible =
    filter === "unread"
      ? notifications.filter((notification) => !notification.read_at)
      : notifications;

  return (
    <>
      <PageHeader
        eyebrow="Central de avisos"
        title="Notificações"
        description="Acompanhe solicitações de revisão, decisões e avisos da sua organização."
      />

      <div className="flex gap-2" role="group" aria-label="Filtrar notificações">
        <Button
          variant={filter === "all" ? "primary" : "secondary"}
          onClick={() => setFilter("all")}
        >
          Todas ({notifications.length})
        </Button>
        <Button
          variant={filter === "unread" ? "primary" : "secondary"}
          onClick={() => setFilter("unread")}
        >
          Não lidas ({unreadCount})
        </Button>
      </div>

      {error ? <Alert>{error}</Alert> : null}
      {loading ? <LoadingState label="Carregando notificações…" /> : null}

      {!loading && !error && visible.length === 0 ? (
        <EmptyState
          title={filter === "unread" ? "Nenhum aviso novo" : "Nenhuma notificação"}
          description={
            filter === "unread"
              ? "Você já leu todos os avisos disponíveis."
              : "Solicitações de revisão e decisões aparecerão aqui."
          }
        />
      ) : null}

      {!loading && visible.length > 0 ? (
        <ul className="space-y-3">
          {visible.map((notification) => (
            <li
              key={notification.id}
              className={`rounded-2xl border p-5 ${
                notification.read_at
                  ? "border-slate-200 bg-white"
                  : "border-emerald-200 bg-emerald-50/60"
              }`}
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-bold text-slate-950">{notification.title}</h2>
                    {!notification.read_at ? (
                      <span className="rounded-full bg-emerald-700 px-2 py-0.5 text-xs font-bold text-white">
                        Nova
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {notification.message}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {formatDateTime(notification.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  {notification.resource_type === "content_item" ? (
                    <Link
                      href="/aprovacoes"
                      className="inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-bold text-emerald-700 underline"
                    >
                      Ver conteúdo
                    </Link>
                  ) : null}
                  {!notification.read_at ? (
                    <Button
                      variant="secondary"
                      busy={readingId === notification.id}
                      onClick={() => void markAsRead(notification)}
                    >
                      Marcar como lida
                    </Button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
