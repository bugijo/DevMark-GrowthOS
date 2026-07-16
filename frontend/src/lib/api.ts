import type {
  ApiProblem,
  ApprovalComponent,
  AudienceSegment,
  AuditLog,
  BrandProfile,
  Business,
  CalendarEntry,
  ContentGenerateInput,
  ContentItem,
  ContentPlan,
  ContentRevisionInput,
  ContentStrategy,
  InvitationAcceptance,
  InvitationInspection,
  ListEnvelope,
  LoginResponse,
  ManualPublicationInput,
  MarketingObjective,
  MediaAsset,
  MeResponse,
  Membership,
  OrganizationInvite,
  OrganizationInviteInput,
  OrganizationMembership,
  OrganizationMembershipUpdate,
  Notification,
  Organization,
  PeriodReport,
  SecurityMessage,
  Service,
  StrategyInput,
  StrategyVersionInput,
  User,
  VisualPreset,
  VisualPresetInput,
  VisualPrompt,
  VisualRevisionInput,
} from "@/types/api";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "/api/v1").replace(
  /\/$/,
  "",
);
const ORGANIZATION_STORAGE_KEY = "growthos_organization_id";
const CSRF_STORAGE_KEY = "growthos_csrf_token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly problem?: ApiProblem,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;

  const prefix = `${encodeURIComponent(name)}=`;
  const value = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
    ?.slice(prefix.length);

  return value ? decodeURIComponent(value) : undefined;
}

export function getStoredOrganizationId(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.localStorage.getItem(ORGANIZATION_STORAGE_KEY) ?? undefined;
}

export function setStoredOrganizationId(id: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ORGANIZATION_STORAGE_KEY, id);
  }
}

export function storeCsrfToken(token: string): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(CSRF_STORAGE_KEY, token);
  }
}

export function clearStoredSession(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ORGANIZATION_STORAGE_KEY);
    window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
  }
}

function getCsrfToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return (
    readCookie("growthos_csrf") ??
    window.sessionStorage.getItem(CSRF_STORAGE_KEY) ??
    undefined
  );
}

function messageFromProblem(problem: ApiProblem | undefined, status: number): string {
  if (typeof problem?.detail === "string") return problem.detail;
  if (Array.isArray(problem?.detail)) {
    const validationMessage = problem.detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join("; ");
    if (validationMessage) return validationMessage;
  }
  if (problem?.message) return problem.message;
  if (problem?.error) return problem.error;
  if (status === 401) return "Sua sessão expirou. Entre novamente.";
  if (status === 403) return "Você não tem permissão para esta ação.";
  if (status === 404) return "O item solicitado não foi encontrado.";
  if (status >= 500) return "O servidor não conseguiu concluir a operação.";
  return "Não foi possível concluir a operação.";
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  const organizationId = getStoredOrganizationId();

  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (organizationId) {
    headers.set("X-Organization-ID", organizationId);
  }
  if (MUTATING_METHODS.has(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path.startsWith("/") ? path : `/${path}`}`, {
      ...init,
      method,
      headers,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar ao servidor. Confira se a API está disponível.",
      0,
    );
  }

  const hasBody = response.status !== 204;
  let payload: unknown;
  if (hasBody) {
    const contentType = response.headers.get("content-type") ?? "";
    payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  }

  if (!response.ok) {
    const problem =
      payload && typeof payload === "object" ? (payload as ApiProblem) : undefined;
    throw new ApiError(messageFromProblem(problem, response.status), response.status, problem);
  }

  return payload as T;
}

export function extractItems<T>(
  payload: T[] | ListEnvelope<T> | { data?: T[] },
): T[] {
  if (Array.isArray(payload)) return payload;
  if ("items" in payload && Array.isArray(payload.items)) return payload.items;
  if ("data" in payload && Array.isArray(payload.data)) return payload.data;
  return [];
}

function query(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  const result = search.toString();
  return result ? `?${result}` : "";
}

export const api = {
  auth: {
    login: (input: { email: string; password: string }) =>
      apiRequest<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    me: () => apiRequest<MeResponse>("/auth/me"),
    logout: () => apiRequest<void>("/auth/logout", { method: "POST" }),
    requestPasswordRecovery: (email: string) =>
      apiRequest<SecurityMessage>("/auth/password-recovery", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, newPassword: string) =>
      apiRequest<SecurityMessage>("/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      }),
    inspectInvitation: (token: string) =>
      apiRequest<InvitationInspection>("/auth/invitations/inspect", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),
    acceptInvitation: (
      token: string,
      account?: { name: string; password: string },
    ) =>
      apiRequest<InvitationAcceptance>("/auth/invitations/accept", {
        method: "POST",
        body: JSON.stringify({ token, ...account }),
      }),
  },
  organizations: {
    current: () => apiRequest<Organization>("/organizations/current"),
  },
  businesses: {
    list: () => apiRequest<Business[] | ListEnvelope<Business>>("/businesses"),
    create: (input: { name: string; segment: string }) =>
      apiRequest<Business>("/businesses", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    get: (id: string) => apiRequest<Business>(`/businesses/${id}`),
    update: (id: string, input: Partial<Pick<Business, "name" | "segment">>) =>
      apiRequest<Business>(`/businesses/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    remove: (id: string) =>
      apiRequest<void>(`/businesses/${id}`, { method: "DELETE" }),
    addReviewer: (
      id: string,
      input: { name: string; email: string; password: string },
    ) =>
      apiRequest<{ user: User; membership: Membership }>(
        `/businesses/${id}/reviewers`,
        {
          method: "POST",
          body: JSON.stringify(input),
        },
      ),
    getBrandProfile: (id: string) =>
      apiRequest<BrandProfile>(`/businesses/${id}/brand-profile`),
    updateBrandProfile: (id: string, input: BrandProfile) =>
      apiRequest<BrandProfile>(`/businesses/${id}/brand-profile`, {
        method: "PUT",
        body: JSON.stringify(input),
      }),
  },
  catalogs: {
    services: {
      list: (businessId: string) =>
        apiRequest<Service[]>(`/businesses/${businessId}/services`),
      create: (
        businessId: string,
        input: {
          name: string;
          description: string;
          category?: string | null;
          warnings: string[];
        },
      ) =>
        apiRequest<Service>(`/businesses/${businessId}/services`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      update: (
        businessId: string,
        id: string,
        input: Partial<{
          name: string;
          description: string;
          category: string | null;
          warnings: string[];
        }>,
      ) =>
        apiRequest<Service>(`/businesses/${businessId}/services/${id}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
      archive: (businessId: string, id: string) =>
        apiRequest<void>(`/businesses/${businessId}/services/${id}`, {
          method: "DELETE",
        }),
    },
    audiences: {
      list: (businessId: string) =>
        apiRequest<AudienceSegment[]>(`/businesses/${businessId}/audiences`),
      create: (
        businessId: string,
        input: {
          name: string;
          description: string;
          needs: string[];
          objections: string[];
          location?: string | null;
        },
      ) =>
        apiRequest<AudienceSegment>(`/businesses/${businessId}/audiences`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      update: (
        businessId: string,
        id: string,
        input: Partial<{
          name: string;
          description: string;
          needs: string[];
          objections: string[];
          location: string | null;
        }>,
      ) =>
        apiRequest<AudienceSegment>(`/businesses/${businessId}/audiences/${id}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
      archive: (businessId: string, id: string) =>
        apiRequest<void>(`/businesses/${businessId}/audiences/${id}`, {
          method: "DELETE",
        }),
    },
    objectives: {
      list: (businessId: string) =>
        apiRequest<MarketingObjective[]>(`/businesses/${businessId}/objectives`),
      create: (
        businessId: string,
        input: Pick<MarketingObjective, "name" | "description" | "planned_indicators">,
      ) =>
        apiRequest<MarketingObjective>(`/businesses/${businessId}/objectives`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      update: (
        businessId: string,
        id: string,
        input: Partial<
          Pick<MarketingObjective, "name" | "description" | "planned_indicators">
        >,
      ) =>
        apiRequest<MarketingObjective>(`/businesses/${businessId}/objectives/${id}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
      archive: (businessId: string, id: string) =>
        apiRequest<void>(`/businesses/${businessId}/objectives/${id}`, {
          method: "DELETE",
        }),
    },
    presets: {
      list: (businessId: string) =>
        apiRequest<VisualPreset[]>(`/businesses/${businessId}/visual-presets`),
      create: (businessId: string, input: VisualPresetInput) =>
        apiRequest<VisualPreset>(`/businesses/${businessId}/visual-presets`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      update: (businessId: string, id: string, input: Partial<VisualPresetInput>) =>
        apiRequest<VisualPreset>(`/businesses/${businessId}/visual-presets/${id}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
      archive: (businessId: string, id: string) =>
        apiRequest<void>(`/businesses/${businessId}/visual-presets/${id}`, {
          method: "DELETE",
        }),
      generatePrompt: (input: {
        business_id: string;
        preset_id: string;
        objective: string;
        audience?: string;
        format?: string;
        aspect_ratio?: string;
      }) =>
        apiRequest<VisualPrompt>("/visual-prompts/generate", {
          method: "POST",
          body: JSON.stringify(input),
        }),
    },
  },
  planning: {
    strategies: {
      list: (businessId: string) =>
        apiRequest<ContentStrategy[]>(`/businesses/${businessId}/strategies`),
      create: (businessId: string, input: StrategyInput) =>
        apiRequest<ContentStrategy>(`/businesses/${businessId}/strategies`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      createVersion: (id: string, input: StrategyVersionInput) =>
        apiRequest<ContentStrategy>(`/strategies/${id}/versions`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      submitInternal: (id: string) =>
        apiRequest<ContentStrategy>(`/strategies/${id}/submit-internal`, {
          method: "POST",
        }),
      sendToClient: (id: string) =>
        apiRequest<ContentStrategy>(`/strategies/${id}/send-to-client`, {
          method: "POST",
        }),
      decide: (id: string, decision: "APPROVE" | "CHANGES_REQUESTED", comment?: string) =>
        apiRequest<ContentStrategy>(`/strategies/${id}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision, comment }),
        }),
    },
    plans: {
      list: (businessId: string) =>
        apiRequest<ContentPlan[]>(`/businesses/${businessId}/plans`),
      create: (
        businessId: string,
        input: {
          strategy_id: string;
          name: string;
          starts_on: string;
          ends_on: string;
          frequency: string;
        },
      ) =>
        apiRequest<ContentPlan>(`/businesses/${businessId}/plans`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      generateMock: (id: string) =>
        apiRequest<CalendarEntry[]>(`/plans/${id}/generate-mock`, {
          method: "POST",
        }),
      createEntry: (
        id: string,
        input: Pick<
          CalendarEntry,
          | "title"
          | "objective"
          | "audience"
          | "channel"
          | "format"
          | "suggested_for"
          | "visual_preset_id"
          | "notes"
        >,
      ) =>
        apiRequest<CalendarEntry>(`/plans/${id}/entries`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
    },
    calendar: {
      list: (businessId: string, startsOn: string, endsOn: string) =>
        apiRequest<CalendarEntry[]>(
          `/businesses/${businessId}/calendar${query({
            starts_on: startsOn,
            ends_on: endsOn,
          })}`,
        ),
      update: (id: string, input: Partial<CalendarEntry>) =>
        apiRequest<CalendarEntry>(`/calendar/${id}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
    },
  },
  media: {
    list: (businessId: string) =>
      apiRequest<MediaAsset[]>(`/businesses/${businessId}/media`),
    upload: (businessId: string, file: File, kind = "IMAGE") => {
      const body = new FormData();
      body.set("file", file);
      body.set("kind", kind);
      return apiRequest<MediaAsset>(`/businesses/${businessId}/media`, {
        method: "POST",
        body,
      });
    },
    signedUrl: (id: string) =>
      apiRequest<{ url: string; expires_at: string }>(`/media/${id}/download-url`),
    archive: (id: string) =>
      apiRequest<void>(`/media/${id}`, { method: "DELETE" }),
  },
  members: {
    list: () => apiRequest<OrganizationMembership[]>("/members"),
    update: (id: string, input: OrganizationMembershipUpdate) =>
      apiRequest<OrganizationMembership>(`/members/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    invitations: {
      list: () => apiRequest<OrganizationInvite[]>("/members/invitations"),
      create: (input: OrganizationInviteInput) =>
        apiRequest<OrganizationInvite>("/members/invitations", {
          method: "POST",
          body: JSON.stringify(input),
        }),
      revoke: (id: string) =>
        apiRequest<void>(`/members/invitations/${id}`, { method: "DELETE" }),
    },
  },
  contents: {
    list: (businessId?: string) =>
      apiRequest<ContentItem[] | ListEnvelope<ContentItem>>(
        `/contents${query({ business_id: businessId })}`,
      ),
    get: (id: string) => apiRequest<ContentItem>(`/contents/${id}`),
    generate: (input: ContentGenerateInput) =>
      apiRequest<ContentItem>("/contents/generate", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    submitInternal: (id: string) =>
      apiRequest<ContentItem>(`/contents/${id}/submit-internal`, {
        method: "POST",
      }),
    sendToClient: (id: string) =>
      apiRequest<ContentItem>(`/contents/${id}/send-to-client`, {
        method: "POST",
      }),
    approve: (id: string) =>
      apiRequest<ContentItem>(`/contents/${id}/approve`, { method: "POST" }),
    requestChanges: (id: string, comment: string) =>
      apiRequest<ContentItem>(`/contents/${id}/request-changes`, {
        method: "POST",
        body: JSON.stringify({ comment }),
      }),
    createRevision: (id: string, input: ContentRevisionInput) =>
      apiRequest<ContentItem>(`/contents/${id}/revisions`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    decideComponent: (
      id: string,
      component: ApprovalComponent,
      decision: "approve" | "request-changes",
      comment?: string,
    ) =>
      apiRequest<ContentItem>(`/contents/${id}/decisions/${component}/${decision}`, {
        method: "POST",
        body: JSON.stringify({ comment }),
      }),
    createVisualRevision: (id: string, input: VisualRevisionInput) =>
      apiRequest<ContentItem>(`/contents/${id}/visual-revisions`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    recordPublication: (id: string, input: ManualPublicationInput) =>
      apiRequest<ContentItem>(`/contents/${id}/publication`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
  },
  reports: {
    period: (businessId: string, startsOn: string, endsOn: string) =>
      apiRequest<PeriodReport>(
        `/businesses/${businessId}/reports/period${query({
          starts_on: startsOn,
          ends_on: endsOn,
        })}`,
      ),
  },
  notifications: {
    list: () =>
      apiRequest<Notification[] | ListEnvelope<Notification>>("/notifications"),
    read: (id: string) =>
      apiRequest<Notification>(`/notifications/${id}/read`, { method: "POST" }),
  },
  auditLogs: {
    list: () => apiRequest<AuditLog[] | ListEnvelope<AuditLog>>("/audit-logs"),
  },
};
