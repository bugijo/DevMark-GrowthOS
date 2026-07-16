"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { InviteForm } from "@/components/identity/invite-form";
import { MemberCard } from "@/components/identity/member-card";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState, LoadingState } from "@/components/ui/feedback";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { api, extractItems } from "@/lib/api";
import { formatDateTime, ROLE_LABELS } from "@/lib/format";
import { teamPolicyForRoles } from "@/lib/identity";
import type {
  Business,
  InviteStatus,
  OrganizationInvite,
  OrganizationMembership,
} from "@/types/api";

const INVITE_STATUS_LABELS: Record<InviteStatus, string> = {
  PENDING: "Pendente",
  ACCEPTED: "Aceito",
  EXPIRED: "Expirado",
  REVOKED: "Revogado",
};

export default function TeamPage() {
  const { activeOrganizationId, memberships: actorMemberships, roles, user } = useAuth();
  const [members, setMembers] = useState<OrganizationMembership[]>([]);
  const [invites, setInvites] = useState<OrganizationInvite[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const policy = useMemo(() => teamPolicyForRoles(roles), [roles]);
  const actorMembership = actorMemberships.find(
    (membership) => membership.organization_id === activeOrganizationId,
  );
  const actorBusinessId = actorMembership?.business_id ?? null;

  const load = useCallback(async () => {
    if (!activeOrganizationId || !policy.canView) return;
    setLoading(true);
    setError(null);
    try {
      const [nextMembers, nextInvites, nextBusinesses] = await Promise.all([
        api.members.list(),
        api.members.invitations.list(),
        api.businesses.list(),
      ]);
      setMembers(nextMembers);
      setInvites(nextInvites);
      setBusinesses(extractItems(nextBusinesses));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar a equipe.",
      );
    } finally {
      setLoading(false);
    }
  }, [activeOrganizationId, policy.canView]);

  useEffect(() => {
    void load();
  }, [load]);

  async function revokeInvitation(invite: OrganizationInvite) {
    if (!window.confirm("Revogar este convite? O link deixará de funcionar.")) return;
    setRevokingId(invite.id);
    setError(null);
    try {
      await api.members.invitations.revoke(invite.id);
      setInvites((current) =>
        current.map((item) =>
          item.id === invite.id
            ? { ...item, status: "REVOKED", revoked_at: new Date().toISOString() }
            : item,
        ),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível revogar o convite.",
      );
    } finally {
      setRevokingId(null);
    }
  }

  if (!policy.canView) {
    return (
      <Alert>
        Você não possui permissão para consultar ou administrar a equipe desta organização.
      </Alert>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Acessos"
        title="Equipe"
        description={
          policy.canManageClient
            ? "Gerencie revisores e pessoas com acesso de leitura somente na sua empresa."
            : "Convide pessoas, defina responsabilidades e suspenda acessos da organização."
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {loading ? <LoadingState label="Carregando equipe e convites…" /> : null}

      {!loading ? (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <div className="space-y-6">
            <Card>
              <h2 className="text-lg font-bold text-slate-950">Convidar uma pessoa</h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                O acesso só é criado depois que o destinatário usa o link enviado por e-mail.
              </p>
              <div className="mt-5">
                <InviteForm
                  businesses={businesses}
                  policy={policy}
                  actorBusinessId={actorBusinessId}
                  onCreated={(invite) => setInvites((current) => [invite, ...current])}
                />
              </div>
            </Card>

            <section aria-labelledby="pessoas-da-equipe">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 id="pessoas-da-equipe" className="text-lg font-bold text-slate-950">
                  Pessoas ({members.length})
                </h2>
                <Button variant="ghost" onClick={() => void load()}>
                  Atualizar
                </Button>
              </div>
              {members.length === 0 ? (
                <EmptyState
                  title="Nenhuma pessoa encontrada"
                  description="Crie o primeiro convite para formar a equipe desta organização."
                />
              ) : (
                <ul className="space-y-3">
                  {members.map((member) => (
                    <MemberCard
                      key={member.id}
                      member={member}
                      businesses={businesses}
                      policy={policy}
                      actorUserId={user?.id}
                      actorBusinessId={actorBusinessId}
                      onUpdated={(updated) =>
                        setMembers((current) =>
                          current.map((item) => (item.id === updated.id ? updated : item)),
                        )
                      }
                    />
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section aria-labelledby="convites-pendentes">
            <Card>
              <h2 id="convites-pendentes" className="text-lg font-bold text-slate-950">
                Convites ({invites.length})
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Links pendentes podem ser revogados antes do aceite.
              </p>
              {invites.length === 0 ? (
                <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                  Nenhum convite criado ainda.
                </p>
              ) : (
                <ul className="mt-5 space-y-3">
                  {invites.map((invite) => (
                    <li key={invite.id} className="rounded-xl border border-slate-200 p-4">
                      <p className="break-all text-sm font-bold text-slate-950">
                        {invite.email}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">
                        {ROLE_LABELS[invite.role]} · {INVITE_STATUS_LABELS[invite.status]}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        Expira em {formatDateTime(invite.expires_at)}
                      </p>
                      {invite.status === "PENDING" ? (
                        <Button
                          variant="danger"
                          className="mt-3 w-full"
                          busy={revokingId === invite.id}
                          onClick={() => void revokeInvitation(invite)}
                        >
                          Revogar convite
                        </Button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </section>
        </div>
      ) : null}
    </>
  );
}
