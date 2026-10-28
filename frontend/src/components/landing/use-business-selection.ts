"use client";

import { useEffect, useState } from "react";

import { api, extractItems } from "@/lib/api";
import type { Business, Role } from "@/types/api";

export const LEAD_MANAGERS: Role[] = ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST", "CLIENT_OWNER"];
export const LEAD_PRIVACY_OPERATORS: Role[] = ["SUPER_ADMIN", "AGENCY_ADMIN", "CLIENT_OWNER"];
export const PRIVACY_EDITORS: Role[] = ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"];
export const PRIVACY_APPROVERS: Role[] = ["SUPER_ADMIN", "CLIENT_OWNER"];

export function hasAnyRole(roles: Role[], allowed: Role[]): boolean {
  return roles.some((role) => allowed.includes(role));
}

/** Lista os clientes visíveis e pré-seleciona o piloto (Villa Pet) quando existir. */
export function useBusinessSelection() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.businesses.list()
      .then((payload) => {
        const items = extractItems(payload);
        setBusinesses(items);
        setBusinessId((current) => current || items.find((b) => /villa pet/i.test(b.name))?.id || items[0]?.id || "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Falha ao carregar clientes."))
      .finally(() => setLoading(false));
  }, []);

  return { businesses, businessId, setBusinessId, loading, error };
}
