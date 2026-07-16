"use client";

import { FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Input, Select } from "@/components/ui/form-controls";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/format";
import { BUSINESS_SCOPED_ROLES, type TeamPolicy } from "@/lib/identity";
import type { Business, OrganizationInvite, Role } from "@/types/api";

export function InviteForm({
  businesses,
  policy,
  actorBusinessId,
  onCreated,
}: {
  businesses: Business[];
  policy: TeamPolicy;
  actorBusinessId: string | null;
  onCreated: (invite: OrganizationInvite) => void;
}) {
  const initialRole = policy.invitableRoles[0] ?? "VIEWER";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>(initialRole);
  const [businessId, setBusinessId] = useState(actorBusinessId ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const activeBusinesses = useMemo(
    () => businesses.filter((business) => business.is_active !== false),
    [businesses],
  );
  const requiresBusiness = BUSINESS_SCOPED_ROLES.has(role);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (requiresBusiness && !businessId) {
      setError("Escolha a empresa que esta pessoa poderá acessar.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const invite = await api.members.invitations.create({
        name: name.trim(),
        email: email.trim(),
        role,
        business_id: requiresBusiness ? businessId : null,
      });
      onCreated(invite);
      setName("");
      setEmail("");
      setSuccess("Convite criado e colocado na fila de e-mail.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível criar o convite.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nome" required>
          <Input
            autoComplete="name"
            minLength={2}
            maxLength={160}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </Field>
        <Field label="E-mail" required>
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </Field>
        <Field label="Papel" required>
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
        {requiresBusiness ? (
          <Field label="Empresa permitida" required>
            <Select
              value={businessId}
              onChange={(event) => setBusinessId(event.target.value)}
              disabled={policy.canManageClient}
              required
            >
              <option value="">Selecione uma empresa</option>
              {activeBusinesses.map((business) => (
                <option key={business.id} value={business.id}>
                  {business.name}
                </option>
              ))}
            </Select>
          </Field>
        ) : null}
      </div>
      <Button
        type="submit"
        busy={submitting}
        disabled={policy.invitableRoles.length === 0}
        className="w-full sm:w-auto"
      >
        {submitting ? "Enviando…" : "Enviar convite seguro"}
      </Button>
    </form>
  );
}
