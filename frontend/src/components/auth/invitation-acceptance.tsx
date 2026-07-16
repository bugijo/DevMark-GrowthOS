"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { AccessShell } from "@/components/auth/access-shell";
import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { formatDateTime, ROLE_LABELS } from "@/lib/format";
import { captureTokenFromFragment } from "@/lib/identity";
import type { InvitationInspection } from "@/types/api";

export function InvitationAcceptance() {
  const captured = useRef(false);
  const inspectionStarted = useRef(false);
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [inspection, setInspection] = useState<InvitationInspection | null>(null);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (captured.current) return;
    captured.current = true;
    setToken(captureTokenFromFragment());
  }, []);

  useEffect(() => {
    if (!token || inspectionStarted.current) return;
    inspectionStarted.current = true;
    void api.auth
      .inspectInvitation(token)
      .then(setInspection)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível verificar o convite.",
        );
      });
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !inspection) return;
    if (inspection.requires_account_setup && password !== confirmation) {
      setError("As senhas precisam ser iguais.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.auth.acceptInvitation(
        token,
        inspection.requires_account_setup ? { name: name.trim(), password } : undefined,
      );
      setToken(null);
      setPassword("");
      setConfirmation("");
      setCompleted(true);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível aceitar o convite.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AccessShell
      eyebrow="Convite seguro"
      title="Entrar para a organização"
      description="Confira os dados abaixo antes de concluir seu acesso ao DevMark GrowthOS."
    >
      {token === undefined || (token && !inspection && !error) ? (
        <LoadingState label="Verificando o convite…" />
      ) : null}

      {completed ? (
        <div className="space-y-5">
          <Alert tone="success">Convite aceito. Seu acesso já está ativo.</Alert>
          <Link
            href="/login"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white"
          >
            Entrar na minha conta
          </Link>
        </div>
      ) : null}

      {token === null && !completed ? (
        <div className="space-y-5">
          <Alert>O link do convite está ausente ou inválido.</Alert>
          <p className="text-sm leading-6 text-slate-600">
            Peça à pessoa administradora para enviar um novo convite.
          </p>
          <Link
            href="/login"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800"
          >
            Voltar para o login
          </Link>
        </div>
      ) : null}

      {error && !inspection ? (
        <div className="space-y-5">
          <Alert>{error}</Alert>
          <p className="text-sm leading-6 text-slate-600">
            O convite pode ter expirado, sido revogado ou já utilizado.
          </p>
          <Link
            href="/login"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800"
          >
            Voltar para o login
          </Link>
        </div>
      ) : null}

      {inspection && !completed ? (
        <form className="space-y-5" onSubmit={handleSubmit}>
          {error ? <Alert>{error}</Alert> : null}
          <dl className="grid gap-3 rounded-2xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-bold text-slate-500 uppercase">Organização</dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {inspection.organization.name}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold text-slate-500 uppercase">Papel</dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {ROLE_LABELS[inspection.role]}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold text-slate-500 uppercase">E-mail</dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {inspection.masked_email}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold text-slate-500 uppercase">Validade</dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {formatDateTime(inspection.expires_at)}
              </dd>
            </div>
            {inspection.business_name ? (
              <div className="sm:col-span-2">
                <dt className="text-xs font-bold text-slate-500 uppercase">Cliente</dt>
                <dd className="mt-1 font-semibold text-slate-900">
                  {inspection.business_name}
                </dd>
              </div>
            ) : null}
          </dl>

          {inspection.requires_account_setup ? (
            <>
              <Field label="Seu nome" required>
                <Input
                  autoComplete="name"
                  minLength={2}
                  maxLength={160}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </Field>
              <Field label="Crie uma senha" hint="Use pelo menos 12 caracteres." required>
                <Input
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={256}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </Field>
              <Field label="Confirme a senha" required>
                <Input
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={256}
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  required
                />
              </Field>
            </>
          ) : (
            <Alert tone="info">
              Este e-mail já possui uma conta. O convite será associado ao seu acesso atual.
            </Alert>
          )}

          <Button type="submit" busy={submitting} className="w-full">
            {submitting ? "Aceitando…" : "Aceitar convite"}
          </Button>
        </form>
      ) : null}
    </AccessShell>
  );
}
