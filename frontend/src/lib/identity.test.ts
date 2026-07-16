import { beforeEach, describe, expect, it } from "vitest";

import {
  canEditMembership,
  captureTokenFromFragment,
  teamPolicyForRoles,
} from "@/lib/identity";
import type { OrganizationMembership } from "@/types/api";

const member: OrganizationMembership = {
  id: "membership-1",
  organization_id: "organization-1",
  user: { id: "user-2", email: "reviewer@example.com", name: "Revisor" },
  role: "CLIENT_REVIEWER",
  business_id: "business-1",
  status: "ACTIVE",
  invited_by_user_id: null,
  joined_at: "2026-07-15T12:00:00Z",
  created_at: "2026-07-15T12:00:00Z",
  updated_at: "2026-07-15T12:00:00Z",
};

describe("teamPolicyForRoles", () => {
  it("oferece a matriz completa ao administrador da agência", () => {
    const policy = teamPolicyForRoles(["AGENCY_ADMIN"]);
    expect(policy.canManageOrganization).toBe(true);
    expect(policy.invitableRoles).toContain("STRATEGIST");
    expect(policy.invitableRoles).toContain("CLIENT_OWNER");
    expect(policy.invitableRoles).not.toContain("SUPER_ADMIN");
  });

  it("limita o responsável cliente a revisor e visualização", () => {
    const policy = teamPolicyForRoles(["CLIENT_OWNER"]);
    expect(policy.invitableRoles).toEqual(["CLIENT_REVIEWER", "VIEWER"]);
    expect(canEditMembership(policy, "owner", member)).toBe(true);
    expect(canEditMembership(policy, member.user.id, member)).toBe(false);
  });
});

describe("captureTokenFromFragment", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("captura somente o fragmento e o remove imediatamente", () => {
    const token = `invite.${"a".repeat(43)}`;
    window.history.replaceState(
      { navigation: true },
      "",
      `/convites/aceitar?token=query-value#token=${token}`,
    );

    expect(captureTokenFromFragment()).toBe(token);
    expect(window.location.hash).toBe("");
    expect(window.location.search).toBe("?token=query-value");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("ignora token presente apenas na query string", () => {
    window.history.replaceState(null, "", "/redefinir-senha?token=query-value");
    expect(captureTokenFromFragment()).toBeNull();
  });
});
