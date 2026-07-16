"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { AccessShell } from "@/components/auth/access-shell";
import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { captureTokenFromFragment } from "@/lib/identity";

export function PasswordResetForm() {
  const captured = useRef(false);
  const [token, setToken] = useState<string | null | undefined>(undefined);
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    if (password !== confirmation) {
      setError("As senhas precisam ser iguais.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.auth.resetPassword(token, password);
      setToken(null);
      setPassword("");
      setConfirmation("");
      setCompleted(true);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível redefinir a senha.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AccessShell
      eyebrow="Acesso seguro"
      title="Criar nova senha"
      description="Escolha uma senha exclusiva com pelo menos 12 caracteres. O link deixa de funcionar após o uso."
    >
      {token === undefined ? <LoadingState label="Verificando o link…" /> : null}

      {completed ? (
        <div className="space-y-5">
          <Alert tone="success">Senha redefinida com sucesso.</Alert>
          <Link
            href="/login"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white"
          >
            Entrar com a nova senha
          </Link>
        </div>
      ) : null}

      {token === null && !completed ? (
        <div className="space-y-5">
          <Alert>Este link está ausente, inválido ou já foi removido da barra.</Alert>
          <Link
            href="/recuperar-senha"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white"
          >
            Solicitar outro link
          </Link>
        </div>
      ) : null}

      {typeof token === "string" && !completed ? (
        <form className="space-y-5" onSubmit={handleSubmit}>
          {error ? <Alert>{error}</Alert> : null}
          <Field label="Nova senha" hint="Use pelo menos 12 caracteres." required>
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
          <Field label="Confirme a nova senha" required>
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
          <Button type="submit" busy={submitting} className="w-full">
            {submitting ? "Redefinindo…" : "Salvar nova senha"}
          </Button>
        </form>
      ) : null}
    </AccessShell>
  );
}
