"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ApiError,
  api,
  clearStoredSession,
  getStoredOrganizationId,
  setStoredOrganizationId,
  storeCsrfToken,
} from "@/lib/api";
import type { LoginResponse, Membership, Role, User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  memberships: Membership[];
  activeOrganizationId: string | null;
  roles: Role[];
  loading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
  selectOrganization: (organizationId: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function rolesForOrganization(
  memberships: Membership[],
  organizationId: string | null,
): Role[] {
  const roles = memberships
    .filter((membership) => membership.organization_id === organizationId)
    .flatMap((membership) => membership.roles ?? [membership.role]);
  return Array.from(new Set(roles));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [activeOrganizationId, setActiveOrganizationId] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applySession = useCallback((nextUser: User, nextMemberships: Membership[]) => {
    const activeMemberships = nextMemberships.filter(
      (membership) => membership.is_active !== false,
    );
    const storedOrganization = getStoredOrganizationId();
    const selected =
      activeMemberships.find(
        (membership) => membership.organization_id === storedOrganization,
      )?.organization_id ?? activeMemberships[0]?.organization_id;

    setUser(nextUser);
    setMemberships(activeMemberships);
    setActiveOrganizationId(selected ?? null);
    if (selected) setStoredOrganizationId(selected);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const session = await api.auth.me();
      storeCsrfToken(session.csrf_token);
      applySession(session.user, [
        {
          ...session.membership,
          organization_id: session.organization.id,
          organization: session.organization,
        },
      ]);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        setUser(null);
        setMemberships([]);
        setActiveOrganizationId(null);
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível verificar sua sessão.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, [applySession]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const session: LoginResponse = await api.auth.login({ email, password });
      storeCsrfToken(session.csrf_token);
      setStoredOrganizationId(session.organization.id);
      applySession(session.user, [
        {
          ...session.membership,
          organization_id: session.organization.id,
          organization: session.organization,
        },
      ]);

      // Atualiza memberships adicionais sem impedir o login se a leitura atrasar.
      try {
        const current = await api.auth.me();
        storeCsrfToken(current.csrf_token);
        applySession(current.user, [
          {
            ...current.membership,
            organization_id: current.organization.id,
            organization: current.organization,
          },
        ]);
      } catch {
        // A resposta de login já contém uma sessão válida e utilizável.
      }
    },
    [applySession],
  );

  const signOut = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // A sessão local é encerrada mesmo se o servidor estiver temporariamente indisponível.
    } finally {
      clearStoredSession();
      setUser(null);
      setMemberships([]);
      setActiveOrganizationId(null);
      setError(null);
    }
  }, []);

  const selectOrganization = useCallback((organizationId: string) => {
    setStoredOrganizationId(organizationId);
    setActiveOrganizationId(organizationId);
  }, []);

  const roles = useMemo(
    () => rolesForOrganization(memberships, activeOrganizationId),
    [memberships, activeOrganizationId],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      memberships,
      activeOrganizationId,
      roles,
      loading,
      error,
      signIn,
      signOut,
      refresh,
      selectOrganization,
    }),
    [
      user,
      memberships,
      activeOrganizationId,
      roles,
      loading,
      error,
      signIn,
      signOut,
      refresh,
      selectOrganization,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return value;
}
