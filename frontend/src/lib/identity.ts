import type { OrganizationMembership, Role } from "@/types/api";

export const BUSINESS_SCOPED_ROLES = new Set<Role>([
  "CLIENT_OWNER",
  "CLIENT_REVIEWER",
  "VIEWER",
]);

const AGENCY_INVITABLE_ROLES: Role[] = [
  "AGENCY_ADMIN",
  "STRATEGIST",
  "CONTENT_EDITOR",
  "DESIGNER",
  "CLIENT_OWNER",
  "CLIENT_REVIEWER",
  "VIEWER",
];

const CLIENT_INVITABLE_ROLES: Role[] = ["CLIENT_REVIEWER", "VIEWER"];

export interface TeamPolicy {
  canView: boolean;
  canManageOrganization: boolean;
  canManageClient: boolean;
  invitableRoles: Role[];
}

export function teamPolicyForRoles(roles: Role[]): TeamPolicy {
  const canManageOrganization = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN"].includes(role),
  );
  const canManageClient = !canManageOrganization && roles.includes("CLIENT_OWNER");
  return {
    canView: canManageOrganization || canManageClient,
    canManageOrganization,
    canManageClient,
    invitableRoles: canManageOrganization
      ? [...AGENCY_INVITABLE_ROLES]
      : canManageClient
        ? [...CLIENT_INVITABLE_ROLES]
        : [],
  };
}

export function canEditMembership(
  policy: TeamPolicy,
  actorUserId: string | undefined,
  membership: OrganizationMembership,
): boolean {
  if (!actorUserId || membership.user.id === actorUserId) return false;
  if (membership.role === "SUPER_ADMIN") return false;
  if (policy.canManageOrganization) return true;
  return (
    policy.canManageClient &&
    ["CLIENT_REVIEWER", "VIEWER"].includes(membership.role)
  );
}

export function captureTokenFromFragment(): string | null {
  if (typeof window === "undefined") return null;
  const parameters = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = parameters.get("token");

  // Remove todo o fragmento imediatamente. Query string e estado de navegação
  // são preservados, mas nunca são usados como fonte do token.
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${window.location.search}`,
  );

  if (!token || token.length < 32 || token.length > 512 || /\s/.test(token)) {
    return null;
  }
  return token;
}
