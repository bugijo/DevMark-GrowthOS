"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import type { Business } from "@/types/api";

export default function BusinessesPage() {
  const { activeOrganizationId } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    setError(null);
    try {
      setBusinesses(extractItems(await api.businesses.list()));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os clientes.",
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
        eyebrow="Operação"
        title="Clientes"
        description="Cadastre cada empresa e mantenha sua identidade de marca organizada."
        action={
          <Link
            href="/clientes/novo"
            className="inline-flex min-h-11 items-center rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-800"
          >
            Novo cliente
          </Link>
        }
      />

      {loading ? <LoadingState label="Carregando clientes…" /> : null}
      {!loading && error ? (
        <div className="space-y-4">
          <Alert>{error}</Alert>
          <Button onClick={() => void load()}>Tentar novamente</Button>
        </div>
      ) : null}
      {!loading && !error && businesses.length === 0 ? (
        <EmptyState
          title="Cadastre o primeiro cliente"
          description="Comece pela empresa piloto. Depois, preencha o Brand Kit para orientar os conteúdos."
          action={
            <Link className="font-bold text-emerald-700 underline" href="/clientes/novo">
              Cadastrar cliente
            </Link>
          }
        />
      ) : null}
      {!loading && !error && businesses.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {businesses.map((business) => (
            <Card key={business.id} className="flex flex-col">
              <div className="flex size-11 items-center justify-center rounded-xl bg-emerald-50 text-sm font-black text-emerald-800">
                {business.name.slice(0, 2).toUpperCase()}
              </div>
              <h2 className="mt-4 text-lg font-bold text-slate-950">{business.name}</h2>
              <p className="mt-1 text-sm text-slate-600">
                {business.segment || "Segmento ainda não informado"}
              </p>
              <Link
                href={`/clientes/${business.id}`}
                className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800 hover:bg-slate-50"
              >
                Abrir perfil e Brand Kit
              </Link>
            </Card>
          ))}
        </div>
      ) : null}
    </>
  );
}
