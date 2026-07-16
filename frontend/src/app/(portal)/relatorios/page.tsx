"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { monthBounds, periodReportCsv } from "@/lib/phase2";
import type { Business, PeriodReport } from "@/types/api";

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-bold tracking-wide text-slate-500 uppercase">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-950">{value}</p>
    </div>
  );
}

export default function ReportsPage() {
  const { activeOrganizationId } = useAuth();
  const period = monthBounds();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [startsOn, setStartsOn] = useState(period.startsOn);
  const [endsOn, setEndsOn] = useState(period.endsOn);
  const [report, setReport] = useState<PeriodReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const runReport = useCallback(async (selected: string, start: string, end: string) => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      setReport(await api.reports.period(selected, start, end));
    } catch (requestError) {
      setReport(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível gerar o relatório.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    try {
      const next = extractItems(await api.businesses.list());
      setBusinesses(next);
      const selected = next[0]?.id ?? "";
      setBusinessId(selected);
      if (selected) await runReport(selected, period.startsOn, period.endsOn);
      else setLoading(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar.");
      setLoading(false);
    }
  }, [activeOrganizationId, period.endsOn, period.startsOn, runReport]);

  useEffect(() => {
    void load();
  }, [load]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runReport(businessId, startsOn, endsOn);
  }

  function exportCsv() {
    if (!report) return;
    const blob = new Blob(["\uFEFF", periodReportCsv(report)], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `growthos-relatorio-${report.starts_on}-${report.ends_on}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader
        eyebrow="Dados operacionais"
        title="Relatório do período"
        description="Acompanhe produção, revisão e publicação manual. Métricas externas permanecem explicitamente indisponíveis."
        action={
          report ? (
            <Button variant="secondary" onClick={exportCsv}>
              Exportar CSV
            </Button>
          ) : null
        }
      />
      <Card>
        <form className="grid gap-4 sm:grid-cols-[1.3fr_1fr_1fr_auto] sm:items-end" onSubmit={submit}>
          <Field label="Cliente" required>
            <Select
              value={businessId}
              onChange={(event) => {
                setBusinessId(event.target.value);
                setReport(null);
                setError(null);
              }}
              required
            >
              {businesses.length === 0 ? <option value="">Nenhum cliente</option> : null}
              {businesses.map((business) => <option key={business.id} value={business.id}>{business.name}</option>)}
            </Select>
          </Field>
          <Field label="Início" required><Input type="date" value={startsOn} onChange={(event) => { setStartsOn(event.target.value); setReport(null); }} required /></Field>
          <Field label="Fim" required><Input type="date" value={endsOn} onChange={(event) => { setEndsOn(event.target.value); setReport(null); }} required /></Field>
          <Button type="submit" busy={loading}>Atualizar</Button>
        </form>
      </Card>
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <LoadingState label="Calculando relatório autorizado…" /> : null}
      {!loading && !businessId ? <EmptyState title="Nenhum cliente disponível" description="Cadastre um cliente para consultar seus dados operacionais." /> : null}
      {!loading && report ? (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Resumo do período">
            <Metric label="Conteúdos" value={report.content_total} />
            <Metric label="Versões" value={report.content_versions_total} />
            <Metric label="Revisões" value={report.revisions_total} />
            <Metric label="Publicações manuais" value={report.manual_publications_total} />
            <Metric label="Estratégias" value={report.strategies_total} />
            <Metric label="Estratégias aprovadas" value={report.approved_strategies_total} />
            <Metric label="Pautas" value={report.calendar_entries_total} />
          </section>
          <section className="grid gap-4 lg:grid-cols-3">
            <Card>
              <h2 className="font-bold text-slate-950">Conteúdos por estado</h2>
              <dl className="mt-4 space-y-2">
                {Object.entries(report.content_by_status).map(([status, total]) => (
                  <div key={status} className="flex justify-between gap-3 text-sm"><dt className="text-slate-600">{status}</dt><dd className="font-bold text-slate-950">{total}</dd></div>
                ))}
              </dl>
            </Card>
            <Card>
              <h2 className="font-bold text-slate-950">Aprovações</h2>
              <dl className="mt-4 space-y-2">
                {Object.entries(report.approvals_by_component).flatMap(([component, statuses]) =>
                  Object.entries(statuses).map(([status, total]) => (
                    <div key={`${component}-${status}`} className="flex justify-between gap-3 text-sm"><dt className="text-slate-600">{component} · {status}</dt><dd className="font-bold text-slate-950">{total}</dd></div>
                  )),
                )}
              </dl>
            </Card>
            <Card>
              <h2 className="font-bold text-slate-950">Publicações por canal</h2>
              {Object.keys(report.publications_by_channel).length === 0 ? <p className="mt-4 text-sm text-slate-500">Nenhuma publicação manual no período.</p> : (
                <dl className="mt-4 space-y-2">{Object.entries(report.publications_by_channel).map(([channel, total]) => <div key={channel} className="flex justify-between gap-3 text-sm"><dt className="text-slate-600">{channel}</dt><dd className="font-bold text-slate-950">{total}</dd></div>)}</dl>
              )}
            </Card>
          </section>
          <Alert tone="info">
            <strong>Métricas ainda indisponíveis:</strong>{" "}
            {report.unavailable_metrics.join(", ")}. O sistema não inventa números de redes ou campanhas sem integração real.
          </Alert>
        </>
      ) : null}
    </>
  );
}
