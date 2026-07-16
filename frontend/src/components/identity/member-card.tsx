"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { displayName, formatDateTime, ROLE_LABELS } from "@/lib/format";
import {
  BUSINESS_SCOPED_ROLES,
  canEditMembership,
  type TeamPolicy,
} from "@/lib/identity";
import type {
  Business,
  MembershipStatus,
  OrganizationMembership,
  Role,
} from "@/types/api";

const STATUS_LABELS: Record<MembershipStatus, string> = {
  ACTIVE: "Ativo",
  SUSPENDED: "Suspenso",
  REVOKED: "Revogado",
};

export function MemberCard({
  member,
  businesses,
  policy,
  actorUserId,
  actorBusinessId,
  onUpdated,
}: {
  member: OrganizationMembership;
  businesses: Business[];
  policy: TeamPolicy;
  actorUserId: string | undefined;
  actorBusinessId: string | null;
  onUpdated: (member: OrganizationMembership) => void;
}) {
  const [role, setRole] = useState<Role>(member.role);
  const [status, setStatus] = useState<MembershipStatus>(member.status);
  const [businessId, setBusinessId] = useState(member.business_id ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editable = canEditMembership(policy, actorUserId, member);
  const requiresBusiness = BUSINESS_SCOPED_ROLES.has(role);

  useEffect(() => {
    setRole(member.role);
    setStatus(member.status);
    setBusinessId(member.business_id ?? "");
  }, [member]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editable) return;
    if (requiresBusiness && !businessId) {
      setError("Escolha a empresa permitida.");
      return;
    }
    if (
      member.status === "ACTIVE" &&
      status !== "ACTIVE" &&
      !window.confirm("Suspender este acesso agora?")
    ) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await api.members.update(member.id, {
        role,
        status,
        business_id: requiresBusiness
          ? policy.canManageClient
            ? actorBusinessId
            : businessId
          : null,
      });
      onUpdated(updated);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível atualizar o acesso.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="truncate font-bold text-slate-950">{displayName(member.user)}</h3>
          <p className="mt-1 break-all text-sm text-slate-600">{member.user.email}</p>
          <p className="mt-2 text-xs text-slate-500">
            Na equipe desde {formatDateTime(member.joined_at ?? member.created_at)}
          </p>
        </div>
        <span
          className={`w-fit rounded-full px-2.5 py-1 text-xs font-bold ${
            member.status === "ACTIVE"
              ? "bg-emerald-50 text-emerald-800"
              : "bg-amber-50 text-amber-900"
          }`}
        >
          {STATUS_LABELS[member.status]}
        </span>
      </div>

      {editable ? (
        <form className="mt-5 space-y-4 border-t border-slate-100 pt-5" onSubmit={handleSubmit}>
          {error ? <Alert>{error}</Alert> : null}
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Papel">
              <Select
                value={role}
                onChange={(event) => {
                  const nextRole = event.target.value as Role;
                  setRole(nextRole);
                  if (!BUSINESS_SCOPED_ROLES.has(nextRole)) setBusinessId("");
                  if (policy.canManageClient && actorBusinessId) {
                    setBusinessId(actorBusinessId);
                  }
                }}
              >
                {policy.invitableRoles.map((option) => (
                  <option key={option} value={option}>
                    {ROLE_LABELS[option]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Status">
              <Select
                value={status}
                onChange={(event) => setStatus(event.target.value as MembershipStatus)}
              >
                <option value="ACTIVE">Ativo</option>
                <option value="SUSPENDED">Suspenso</option>
              </Select>
            </Field>
            {requiresBusiness ? (
              <Field label="Empresa">
                <Select
                  value={businessId}
                  onChange={(event) => setBusinessId(event.target.value)}
                  disabled={policy.canManageClient}
                  required
                >
                  <option value="">Selecione</option>
                  {businesses.map((business) => (
                    <option key={business.id} value={business.id}>
                      {business.name}
                    </option>
                  ))}
                </Select>
              </Field>
            ) : null}
          </div>
          <Button type="submit" variant="secondary" busy={saving}>
            {saving ? "Salvando…" : "Salvar acesso"}
          </Button>
        </form>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-600">
          <span className="rounded-full bg-slate-100 px-2.5 py-1">
            {ROLE_LABELS[member.role]}
          </span>
          {member.user.id === actorUserId ? (
            <span className="rounded-full bg-sky-50 px-2.5 py-1 text-sky-800">
              Seu acesso
            </span>
          ) : null}
        </div>
      )}
    </li>
  );
}
