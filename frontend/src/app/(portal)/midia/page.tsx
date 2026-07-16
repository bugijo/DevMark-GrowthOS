"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/form-controls";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatBytes } from "@/lib/phase2";
import type { Business, MediaAsset } from "@/types/api";

export default function MediaLibraryPage() {
  const { activeOrganizationId, roles } = useAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [signedUrls, setSignedUrls] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canUpload = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "CONTENT_EDITOR", "DESIGNER"].includes(role),
  );
  const canArchive = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN", "DESIGNER"].includes(role),
  );

  const loadAssets = useCallback(async (selected: string) => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      setAssets(await api.media.list(selected));
      setSignedUrls({});
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar a biblioteca.",
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
      if (selected) await loadAssets(selected);
      else setLoading(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar.");
      setLoading(false);
    }
  }, [activeOrganizationId, loadAssets]);

  useEffect(() => {
    void load();
  }, [load]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError(null);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !businessId) return;
    setBusy("upload");
    setError(null);
    setSuccess(null);
    try {
      const created = await api.media.upload(businessId, file);
      setAssets((current) => [created, ...current]);
      setFile(null);
      const input = document.getElementById("media-file") as HTMLInputElement | null;
      if (input) input.value = "";
      setSuccess("Imagem validada e guardada na biblioteca privada.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível enviar.");
    } finally {
      setBusy(null);
    }
  }

  async function reveal(asset: MediaAsset) {
    setBusy(asset.id);
    setError(null);
    try {
      const signed = await api.media.signedUrl(asset.id);
      setSignedUrls((current) => ({ ...current, [asset.id]: signed.url }));
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Não foi possível liberar o acesso.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function archive(asset: MediaAsset) {
    if (!window.confirm(`Arquivar “${asset.display_name}”?`)) return;
    setBusy(asset.id);
    setError(null);
    try {
      await api.media.archive(asset.id);
      setAssets((current) => current.filter((item) => item.id !== asset.id));
      setSuccess("Arquivo removido da biblioteca ativa.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível arquivar.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Arquivos privados"
        title="Biblioteca de mídia"
        description="Envie imagens validadas e abra cada arquivo por uma URL assinada de curta duração."
      />

      <Card>
        <Field label="Cliente" required>
          <Select
            value={businessId}
            onChange={(event) => {
              setBusinessId(event.target.value);
              void loadAssets(event.target.value);
            }}
          >
            {businesses.length === 0 ? <option value="">Nenhum cliente disponível</option> : null}
            {businesses.map((business) => (
              <option key={business.id} value={business.id}>
                {business.name}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      {canUpload && businessId ? (
        <Card>
          <h2 className="text-lg font-bold text-slate-950">Enviar imagem</h2>
          <p className="mt-1 text-sm text-slate-600">
            O backend verifica conteúdo, tipo e tamanho; o nome interno é gerado pelo servidor.
          </p>
          <form className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end" onSubmit={upload}>
            <Field label="Imagem PNG, JPEG ou WebP" required>
              <input
                id="media-file"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={chooseFile}
                required
                className="mt-1.5 block min-h-12 w-full rounded-xl border border-slate-300 bg-white p-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:font-semibold file:text-emerald-800"
              />
            </Field>
            <Button type="submit" busy={busy === "upload"} disabled={!file}>
              Enviar com segurança
            </Button>
          </form>
        </Card>
      ) : null}

      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      {loading ? <LoadingState label="Carregando mídia privada…" /> : null}
      {!loading && !businessId ? (
        <EmptyState
          title="Nenhum cliente disponível"
          description="A biblioteca precisa de um cliente para aplicar o isolamento dos arquivos."
        />
      ) : null}
      {!loading && businessId && assets.length === 0 ? (
        <EmptyState
          title="Biblioteca vazia"
          description="Envie a primeira imagem segura para vinculá-la a presets e conteúdos."
        />
      ) : null}

      {!loading && assets.length > 0 ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Arquivos de mídia">
          {assets.map((asset) => (
            <Card key={asset.id}>
              {signedUrls[asset.id] ? (
                // A URL é autorizada pelo backend e expira rapidamente.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={signedUrls[asset.id]}
                  alt={asset.display_name}
                  className="aspect-video w-full rounded-xl bg-slate-100 object-cover"
                />
              ) : (
                <div className="flex aspect-video items-center justify-center rounded-xl bg-slate-100 text-sm font-semibold text-slate-500">
                  Prévia privada
                </div>
              )}
              <h2 className="mt-4 break-words font-bold text-slate-950">{asset.display_name}</h2>
              <p className="mt-1 text-sm text-slate-600">
                {asset.mime_type} · {formatBytes(asset.byte_size)}
              </p>
              <p className="text-xs text-slate-500">
                {asset.width && asset.height ? `${asset.width} × ${asset.height} px` : "Dimensões indisponíveis"}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  busy={busy === asset.id}
                  onClick={() => void reveal(asset)}
                >
                  {signedUrls[asset.id] ? "Renovar acesso" : "Abrir prévia"}
                </Button>
                {canArchive ? (
                  <Button
                    variant="ghost"
                    className="text-red-700"
                    busy={busy === asset.id}
                    onClick={() => void archive(asset)}
                  >
                    Arquivar
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </section>
      ) : null}
    </>
  );
}
