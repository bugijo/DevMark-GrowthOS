"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { useAuth } from "@/contexts/auth-context";
import { displayName, ROLE_LABELS } from "@/lib/format";
import { navigationForRoles } from "@/lib/navigation";

function Brand() {
  return (
    <Link href="/dashboard" className="flex items-center gap-3 rounded-xl">
      <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-700 text-sm font-black text-white shadow-sm">
        GO
      </span>
      <span>
        <span className="block text-sm font-bold text-slate-950">DevMark GrowthOS</span>
        <span className="block text-xs text-slate-500">Operação de marketing</span>
      </span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    user,
    memberships,
    activeOrganizationId,
    roles,
    loading,
    error,
    refresh,
    signOut,
    selectOrganization,
  } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading) {
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <LoadingState label="Verificando sua sessão…" />
      </main>
    );
  }

  if (!user) return null;

  if (error) {
    return (
      <main className="mx-auto max-w-xl space-y-4 px-4 py-16">
        <Alert>{error}</Alert>
        <Button onClick={() => void refresh()}>Tentar novamente</Button>
      </main>
    );
  }

  if (!activeOrganizationId) {
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <EmptyState
          title="Nenhuma organização disponível"
          description="Seu acesso está ativo, mas ainda não há uma organização associada. Fale com a pessoa administradora."
        />
      </main>
    );
  }

  const navigation = navigationForRoles(roles);
  const activeMembership = memberships.find(
    (membership) => membership.organization_id === activeOrganizationId,
  );

  async function handleSignOut() {
    await signOut();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[264px_minmax(0,1fr)]">
      <a
        href="#conteudo-principal"
        className="fixed top-2 left-2 z-50 -translate-y-20 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white focus:translate-y-0"
      >
        Pular para o conteúdo
      </a>

      <aside className="hidden border-r border-slate-200 bg-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col lg:p-5">
        <Brand />

        <nav aria-label="Navegação principal" className="mt-9 space-y-1">
          {navigation.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center rounded-xl px-3.5 text-sm font-semibold transition ${
                  active
                    ? "bg-emerald-50 text-emerald-800"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="truncate text-sm font-semibold text-slate-900">
            {displayName(user)}
          </p>
          <p className="mt-0.5 truncate text-xs text-slate-500">{user.email}</p>
          <p className="mt-2 text-xs font-semibold text-emerald-700">
            {roles[0] ? ROLE_LABELS[roles[0]] : "Acesso básico"}
          </p>
          <Button
            variant="ghost"
            className="mt-3 w-full"
            onClick={() => void handleSignOut()}
          >
            Sair
          </Button>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 border-b border-slate-200/90 bg-white/95 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <Brand />
            <div className="flex items-center gap-1">
              <span
                className="flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700"
                title={displayName(user)}
              >
                {displayName(user).slice(0, 2).toUpperCase()}
              </span>
              <button
                type="button"
                onClick={() => void handleSignOut()}
                className="min-h-10 rounded-lg px-2 text-xs font-bold text-slate-600 underline"
              >
                Sair
              </button>
            </div>
          </div>
          <nav
            aria-label="Navegação principal"
            className="flex gap-1 overflow-x-auto px-3 pb-2"
          >
            {navigation.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`min-h-10 shrink-0 rounded-xl px-3 py-2 text-sm font-semibold ${
                    active ? "bg-emerald-700 text-white" : "text-slate-600"
                  }`}
                >
                  {item.shortLabel}
                </Link>
              );
            })}
          </nav>
        </header>

        <div className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6 lg:px-10">
          <label className="flex max-w-md items-center gap-3 text-xs font-semibold text-slate-500">
            <span className="shrink-0">Organização</span>
            {memberships.length > 1 ? (
              <select
                className="min-h-10 min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800"
                value={activeOrganizationId}
                onChange={(event) => selectOrganization(event.target.value)}
              >
                {memberships.map((membership) => (
                  <option
                    key={`${membership.organization_id}-${membership.role}`}
                    value={membership.organization_id}
                  >
                    {membership.organization?.name ??
                      membership.organization_name ??
                      "Organização"}
                  </option>
                ))}
              </select>
            ) : (
              <span className="truncate text-sm text-slate-900">
                {activeMembership?.organization?.name ??
                  activeMembership?.organization_name ??
                  "Organização atual"}
              </span>
            )}
          </label>
        </div>

        <main
          id="conteudo-principal"
          className="mx-auto w-full max-w-7xl space-y-7 px-4 py-6 sm:px-6 sm:py-8 lg:px-10"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
