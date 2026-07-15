"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/form-controls";
import { useAuth } from "@/contexts/auth-context";

const DEMO_EMAIL = "admin@devmark.local";
const DEMO_PASSWORD = "local-demo-only-change-before-use";
const DEMO_CLIENT_EMAIL = "client@clinicafeliz.local";
const DEMO_CLIENT_PASSWORD = "local-demo-client-only-change-before-use";
const subscribeToHost = () => () => undefined;
const isLocalHost = () =>
  ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);

export function LoginForm() {
  const router = useRouter();
  const { user, loading: checkingSession, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLocal = useSyncExternalStore(subscribeToHost, isLocalHost, () => false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
      router.replace("/dashboard");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível entrar. Tente novamente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemo(nextEmail: string, nextPassword: string) {
    setEmail(nextEmail);
    setPassword(nextPassword);
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]">
      <section className="hidden overflow-hidden bg-emerald-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-xl bg-white text-sm font-black text-emerald-900">
            GO
          </span>
          <span className="font-bold">DevMark GrowthOS</span>
        </div>
        <div className="max-w-xl">
          <p className="text-sm font-bold tracking-[0.2em] text-emerald-200 uppercase">
            Growth Agent
          </p>
          <h1 className="mt-4 text-5xl leading-tight font-bold tracking-tight">
            Marketing organizado, com controle humano.
          </h1>
          <p className="mt-6 text-lg leading-8 text-emerald-100">
            Crie, revise e aprove conteúdos em um fluxo simples, seguro e rastreável.
          </p>
        </div>
        <p className="text-sm text-emerald-200">DevMark IA · versão 1.0</p>
      </section>

      <section className="flex items-center justify-center bg-white px-5 py-10 sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-9 lg:hidden">
            <div className="flex items-center gap-3">
              <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-700 text-sm font-black text-white">
                GO
              </span>
              <span className="font-bold text-slate-950">DevMark GrowthOS</span>
            </div>
          </div>

          <p className="text-sm font-bold text-emerald-700">Bem-vindo</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            Entre na sua conta
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Use seu e-mail e senha para acessar sua organização.
          </p>

          {user && !checkingSession ? (
            <Alert tone="info">
              Você já tem uma sessão ativa.{" "}
              <Link className="font-bold underline" href="/dashboard">
                Continuar para o início
              </Link>
            </Alert>
          ) : null}

          <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
            {error ? <Alert>{error}</Alert> : null}
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
            <Field label="Senha" required>
              <Input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" busy={submitting} className="w-full">
              {submitting ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          {isLocal ? (
            <aside className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-bold">Acesso de demonstração local</p>
              <div className="mt-3 space-y-4">
                <div>
                  <p className="text-xs font-bold uppercase">Equipe da agência</p>
                  <p className="mt-1 break-all">{DEMO_EMAIL}</p>
                  <p className="break-all">{DEMO_PASSWORD}</p>
                  <button
                    type="button"
                    onClick={() => fillDemo(DEMO_EMAIL, DEMO_PASSWORD)}
                    className="mt-1 min-h-9 rounded-lg font-bold text-amber-900 underline"
                  >
                    Usar acesso da agência
                  </button>
                </div>
                <div className="border-t border-amber-200 pt-3">
                  <p className="text-xs font-bold uppercase">Cliente revisor</p>
                  <p className="mt-1 break-all">{DEMO_CLIENT_EMAIL}</p>
                  <p className="break-all">{DEMO_CLIENT_PASSWORD}</p>
                  <button
                    type="button"
                    onClick={() => fillDemo(DEMO_CLIENT_EMAIL, DEMO_CLIENT_PASSWORD)}
                    className="mt-1 min-h-9 rounded-lg font-bold text-amber-900 underline"
                  >
                    Usar acesso do cliente
                  </button>
                </div>
              </div>
            </aside>
          ) : null}
        </div>
      </section>
    </main>
  );
}
