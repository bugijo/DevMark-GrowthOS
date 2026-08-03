"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { StrategyComparisonSide, StrategyVersionComparison, StrategyVersionHistory } from "@/types/api";

const LABELS: Record<string, string> = {
  "strategy.objective": "Objetivo",
  "strategy.positioning": "Posicionamento",
  "strategy.funnel": "Funil",
  "strategy.channels": "Canais",
  "strategy.pillars": "Pilares",
  "strategy.planned_indicators": "Indicadores",
  "strategy.services": "Serviços",
  "strategy.audiences": "Públicos",
  "strategy.marketing_objectives": "Objetivos de marketing",
};

function readable(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => typeof item === "string" ? item : String(item.name ?? item.title ?? "Item")).join(", ");
  }
  return String(value || "Não informado");
}

function StrategySide({ side, label, changed }: { side: StrategyComparisonSide; label: string; changed: Set<string> }) {
  const rows: Array<[string, unknown]> = [
    ["objective", side.strategy.objective],
    ["positioning", side.strategy.positioning],
    ["funnel", side.strategy.funnel],
    ["channels", side.strategy.channels],
    ["pillars", side.strategy.pillars],
    ["planned_indicators", side.strategy.planned_indicators],
    ["services", side.strategy.services],
    ["audiences", side.strategy.audiences],
    ["marketing_objectives", side.strategy.marketing_objectives],
  ];
  return (
    <article className="min-w-0 rounded-xl border border-slate-200 p-4">
      <p className="text-xs font-bold uppercase text-emerald-700">{label} · versão {side.version_number}</p>
      <p className="mt-1 text-sm text-slate-600">{side.author.name} · {formatDateTime(side.created_at)}</p>
      {side.decisions.map((decision, index) => (
        <p key={index} className="mt-2 text-xs text-slate-600">
          {decision.status}{decision.decided_by ? ` por ${decision.decided_by.name}` : ""}{decision.comment ? ` — ${decision.comment}` : ""}
        </p>
      ))}
      <dl className="mt-3 divide-y divide-slate-100">
        {rows.map(([field, value]) => (
          <div key={field} className={changed.has(`strategy.${field}`) ? "rounded-lg bg-amber-50 p-3" : "p-3"}>
            <dt className="text-xs font-bold uppercase text-slate-500">{LABELS[`strategy.${field}`]}</dt>
            <dd className="mt-1 text-sm leading-6 text-slate-800">{readable(value)}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

export function StrategyVersionComparisonPanel({ strategyId }: { strategyId: string }) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState<StrategyVersionHistory | null>(null);
  const [comparison, setComparison] = useState<StrategyVersionComparison | null>(null);
  const [baseId, setBaseId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function show() {
    setOpen(true);
    if (history) return;
    setLoading(true);
    try {
      const result = await api.planning.strategies.history(strategyId);
      setHistory(result);
      setBaseId(result.versions.at(-2)?.id ?? "");
      setTargetId(result.versions.at(-1)?.id ?? "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar o histórico.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!open || !baseId || !targetId || baseId === targetId) return;
    let active = true;
    setLoading(true);
    void api.planning.strategies.compare(strategyId, baseId, targetId)
      .then((result) => { if (active) setComparison(result); })
      .catch((requestError: unknown) => { if (active) setError(requestError instanceof Error ? requestError.message : "Não foi possível comparar as estratégias."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [baseId, open, strategyId, targetId]);

  const changed = useMemo(() => new Set(comparison?.changed_fields ?? []), [comparison]);
  return (
    <section className="mt-4 border-t border-slate-200 pt-4" aria-label="Comparação de versões da estratégia">
      <Button type="button" variant="secondary" onClick={() => open ? setOpen(false) : void show()} aria-expanded={open}>
        {open ? "Fechar comparação" : "Comparar versões"}
      </Button>
      {open ? <div className="mt-4 space-y-4">
        {loading ? <LoadingState label="Carregando comparação da estratégia…" /> : null}
        {error ? <Alert>{error}</Alert> : null}
        {history && history.versions.length < 2 ? <Alert tone="info">Crie outra versão da estratégia para comparar.</Alert> : null}
        {history && history.versions.length >= 2 ? <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Estratégia anterior"><Select value={baseId} onChange={(event) => setBaseId(event.target.value)}>{history.versions.map((version) => <option key={version.id} value={version.id}>Versão {version.version_number}</option>)}</Select></Field>
          <Field label="Estratégia posterior"><Select value={targetId} onChange={(event) => setTargetId(event.target.value)}>{history.versions.map((version) => <option key={version.id} value={version.id}>Versão {version.version_number}</option>)}</Select></Field>
        </div> : null}
        {baseId && baseId === targetId ? <Alert>Escolha duas versões diferentes.</Alert> : null}
        {comparison ? <>
          <p aria-live="polite" className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-950"><strong>{comparison.changed_fields.length} campo(s) alterado(s):</strong> {comparison.changed_fields.map((field) => LABELS[field] ?? field).join(", ") || "nenhum"}.</p>
          <div className="grid min-w-0 gap-4 lg:grid-cols-2"><StrategySide side={comparison.base} label="Antes" changed={changed} /><StrategySide side={comparison.target} label="Depois" changed={changed} /></div>
        </> : null}
      </div> : null}
    </section>
  );
}
