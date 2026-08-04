"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Input, Select } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ProviderConfig } from "@/types/api";

const KIND_LABELS: Record<string, string> = { TEXT: "Texto", IMAGE: "Imagem", EMAIL: "E-mail", STORAGE: "Armazenamento", ORCHESTRATION: "Orquestração" };

export default function IntegrationsPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [configs, setConfigs] = useState<ProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const canManage = roles.some((role) => ["SUPER_ADMIN", "AGENCY_ADMIN"].includes(role));
  const load = useCallback(async () => {
    if (!activeOrganizationId) return;
    setLoading(true);
    try { setConfigs(await api.providers.list()); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar os providers."); }
    finally { setLoading(false); }
  }, [activeOrganizationId]);
  useEffect(() => { void load(); }, [load]);

  function change(index: number, patch: Partial<ProviderConfig>) {
    setConfigs((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }
  async function save(index: number) {
    const config = configs[index];
    setBusy(`${config.kind}-${config.provider}-save`); setError(null); setSuccess(null);
    try { const saved = await api.providers.update(config); change(index, saved); setSuccess(`${config.provider} salvo sem expor segredos.`); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar o provider."); }
    finally { setBusy(null); }
  }
  async function test(index: number) {
    const config = configs[index];
    setBusy(`${config.kind}-${config.provider}-test`); setError(null); setSuccess(null);
    try { const result = await api.providers.test(config); setSuccess(result.message); await load(); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível testar o provider."); }
    finally { setBusy(null); }
  }
  return <>
    <PageHeader eyebrow="Operação segura" title="Integrações e providers" description="Configure apenas a orquestração da versão 1.0. Redes sociais, anúncios e gastos permanecem desativados." />
    <Alert tone="info">O mock permanece disponível e não exige API paga. Segredos são lidos somente de variáveis de ambiente e nunca retornam ao navegador.</Alert>
    {error ? <Alert>{error}</Alert> : null}{success ? <Alert tone="success">{success}</Alert> : null}
    {loading ? <LoadingState label="Carregando providers…" /> : null}
    {!loading && configs.length === 0 ? <EmptyState title="Nenhum provider disponível" description="A configuração estrutural ainda não foi carregada." /> : null}
    <div className="grid gap-4 xl:grid-cols-2">
      {configs.map((config, index) => {
        const key = `${config.kind}-${config.provider}`;
        return <Card key={key}>
          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase text-emerald-700">{KIND_LABELS[config.kind]}</p><h2 className="mt-1 text-lg font-bold text-slate-950">{config.provider}</h2></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{config.last_status}</span></div>
          <p className="mt-3 text-sm text-slate-600">{config.configured_by_environment ? "Ambiente configurado" : "Sem configuração no ambiente"}{config.is_required ? " · obrigatório" : " · opcional"}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Field label="Ativo"><Select value={config.is_active ? "true" : "false"} disabled={config.is_required || !canManage} onChange={(event) => change(index, { is_active: event.target.value === "true" })}><option value="true">Sim</option><option value="false">Não</option></Select></Field>
            <Field label="Modo"><Select value={config.test_mode ? "test" : "live"} disabled={!canManage} onChange={(event) => change(index, { test_mode: event.target.value === "test" })}><option value="test">Teste</option><option value="live">Operacional controlado</option></Select></Field>
            <Field label="Prioridade"><Input type="number" min="0" max="1000" value={config.priority} disabled={!canManage} onChange={(event) => change(index, { priority: Number(event.target.value) })} /></Field>
            <Field label="Fallback"><Select value={config.fallback_provider ?? ""} disabled={config.is_required || !canManage} onChange={(event) => change(index, { fallback_provider: event.target.value || null })}><option value="">Sem fallback</option><option value="MOCK">MOCK</option></Select></Field>
            <Field label="Timeout em segundos"><Input type="number" min="1" max="120" value={config.timeout_seconds} disabled={!canManage} onChange={(event) => change(index, { timeout_seconds: Number(event.target.value) })} /></Field>
            <Field label="Tentativas"><Input type="number" min="1" max="10" value={config.max_attempts} disabled={!canManage} onChange={(event) => change(index, { max_attempts: Number(event.target.value) })} /></Field>
          </div>
          {config.provider === "EXTERNAL_FUTURE" ? <Field label="Nome da variável de ambiente" hint="O valor secreto nunca é exibido"><Input value={config.secret_environment_key ?? ""} disabled={!canManage} onChange={(event) => change(index, { secret_environment_key: event.target.value || null })} /></Field> : null}
          {config.last_checked_at ? <p className="mt-3 text-xs text-slate-500">Última verificação: {formatDateTime(config.last_checked_at)}</p> : null}
          {config.last_error ? <Alert>{config.last_error}</Alert> : null}
          {canManage ? <div className="mt-4 flex flex-wrap gap-2"><Button variant="secondary" busy={busy === `${key}-test`} onClick={() => void test(index)}>Testar conexão</Button><Button busy={busy === `${key}-save`} onClick={() => void save(index)}>Salvar</Button></div> : null}
        </Card>;
      })}
    </div>
  </>;
}
