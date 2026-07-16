"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AccessShell } from "@/components/auth/access-shell";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/form-controls";
import { api } from "@/lib/api";

export const GENERIC_RECOVERY_MESSAGE =
  "Se o e-mail estiver cadastrado, você receberá uma mensagem com os próximos passos.";

export function PasswordRecoveryForm() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.auth.requestPasswordRecovery(email.trim());
    } catch {
      // A resposta visual é deliberadamente idêntica para não permitir
      // inferência sobre contas ou detalhes do mecanismo de recuperação.
    } finally {
      setSubmitting(false);
      setCompleted(true);
    }
  }

  return (
    <AccessShell
      eyebrow="Acesso seguro"
      title="Recuperar senha"
      description="Informe seu e-mail. Se houver uma conta ativa, enviaremos um link curto e de uso único."
    >
      {completed ? (
        <div className="space-y-5">
          <Alert tone="info">{GENERIC_RECOVERY_MESSAGE}</Alert>
          <p className="text-sm leading-6 text-slate-600">
            Verifique também a caixa de spam. Por segurança, o link expira em pouco tempo.
          </p>
          <Link
            href="/login"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white"
          >
            Voltar para o login
          </Link>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          <Field label="E-mail" required>
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="voce@empresa.com.br"
              required
            />
          </Field>
          <Button type="submit" busy={submitting} className="w-full">
            {submitting ? "Solicitando…" : "Enviar orientações"}
          </Button>
          <Link
            href="/login"
            className="inline-flex min-h-10 w-full items-center justify-center text-sm font-bold text-emerald-700 underline"
          >
            Lembrei minha senha
          </Link>
        </form>
      )}
    </AccessShell>
  );
}
