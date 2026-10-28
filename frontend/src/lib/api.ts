import type {
  ApiProblem,
  AIGeneration,
  AIGenerationInput,
  ApprovalComponent,
  AudienceSegment,
  AuditLog,
  BrandProfile,
  Business,
  BusinessOnboarding,
  CalendarEntry,
  ContentGenerateInput,
  ContentItem,
  ContentVersionComparison,
  ContentVersionHistory,
  ConsentRecord,
  DataPurpose,
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
  OnboardingApprover,
  OnboardingStepPayload,
  Organization,
  PeriodReport,
  ProviderConfig,
  ProviderTestResult,
  PrivacyRequest,
  RetentionPolicy,
  SecurityMessage,
  Service,
  SalesLead,
  SalesLeadStage,
  SalesLeadTask,
  SalesBriefing,
  SalesProposalDraft,
  LandingPage,
  LandingPageContent,
  BusinessLead,
  BusinessLeadSource,
  BusinessLeadSummary,
  StrategyInput,
  StrategyVersionComparison,
  StrategyVersionHistory,
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
  landing: {
    get: (businessId: string) => apiRequest<LandingPage>(`/businesses/${businessId}/landing-page`),
    save: (businessId: string, input: LandingPageContent) =>
      apiRequest<LandingPage>(`/businesses/${businessId}/landing-page`, { method: "PUT", body: JSON.stringify(input) }),
    approve: (businessId: string, version: number) =>
      apiRequest<LandingPage>(`/businesses/${businessId}/landing-page/approve`, { method: "POST", body: JSON.stringify({ version }) }),
    revoke: (businessId: string) =>
      apiRequest<LandingPage>(`/businesses/${businessId}/landing-page/revoke`, { method: "POST" }),
    leads: (businessId: string) => apiRequest<BusinessLead[]>(`/businesses/${businessId}/leads`),
    summary: (businessId: string) => apiRequest<BusinessLeadSummary>(`/businesses/${businessId}/leads/summary`),
    createLead: (businessId: string, input: { source: BusinessLeadSource; service_requested: string; price_item_label: string; preferred_period: string; notes: string }) =>
      apiRequest<BusinessLead>(`/businesses/${businessId}/leads`, { method: "POST", body: JSON.stringify(input) }),
    updateLead: (leadId: string, input: Partial<Pick<BusinessLead, "status" | "notes" | "next_action" | "next_action_due_at">>) =>
      apiRequest<BusinessLead>(`/business-leads/${leadId}`, { method: "PATCH", body: JSON.stringify(input) }),
  },
  sales: {
    list: () => apiRequest<SalesLead[]>("/sales/leads"),
    create: (input: Pick<SalesLead, "name" | "company" | "email" | "whatsapp" | "business_type" | "goal" | "desired_timeline" | "additional_info">) => apiRequest<SalesLead>("/sales/leads", { method: "POST", body: JSON.stringify(input) }),
    changeStage: (id: string, stage: SalesLeadStage) => apiRequest<SalesLead>(`/sales/leads/${id}/stage`, { method: "PATCH", body: JSON.stringify({ stage }) }),
    briefing: (id: string) => apiRequest<SalesBriefing>(`/sales/leads/${id}/briefing`),
    draftProposal: (id: string) => apiRequest<SalesProposalDraft>(`/sales/leads/${id}/proposal-draft`, { method: "POST" }),
    tasks: (id: string) => apiRequest<SalesLeadTask[]>(`/sales/leads/${id}/tasks`),
    createTask: (id: string, title: string, notes = "") => apiRequest<SalesLeadTask>(`/sales/leads/${id}/tasks`, { method: "POST", body: JSON.stringify({ title, notes }) }),
  },
  ai: {
    generate: (businessId: string, input: AIGenerationInput) =>
      apiRequest<AIGeneration>(`/businesses/${businessId}/ai/generations`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    list: (businessId: string) =>
      apiRequest<AIGeneration[]>(`/businesses/${businessId}/ai/generations`),
    regenerate: (id: string, idempotencyKey = crypto.randomUUID()) =>
      apiRequest<AIGeneration>(`/ai/generations/${id}/regenerate`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
      }),
    cancel: (id: string) =>
      apiRequest<AIGeneration>(`/ai/generations/${id}/cancel`, {
        method: "POST",
      }),
    applyAlternative: (
      generationId: string,
      alternativeId: string,
      input: { channel: string; format: string; objective: string },
    ) =>
      apiRequest<ContentItem>(
        `/ai/generations/${generationId}/alternatives/${alternativeId}/apply`,
        { method: "POST", body: JSON.stringify(input) },
      ),
    feedback: (id: string, rating: "HELPFUL" | "NOT_HELPFUL", comment = "") =>
      apiRequest<void>(`/ai/generations/${id}/feedback`, {
        method: "POST",
        body: JSON.stringify({ rating, comment }),
      }),
  },
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
  onboarding: {
    approvers: (businessId: string) =>
      apiRequest<OnboardingApprover[]>(
        `/businesses/${businessId}/onboarding/approvers`,
      ),
    get: (businessId: string) =>
      apiRequest<BusinessOnboarding>(`/businesses/${businessId}/onboarding`),
    start: (businessId: string) =>
      apiRequest<BusinessOnboarding>(`/businesses/${businessId}/onboarding`, {
        method: "POST",
      }),
    saveStep: (businessId: string, payload: OnboardingStepPayload) =>
      apiRequest<BusinessOnboarding>(
        `/businesses/${businessId}/onboarding/steps/${payload.step}`,
        {
          method: "PUT",
          body: JSON.stringify(payload),
        },
      ),
    complete: (businessId: string, revision: number) =>
      apiRequest<BusinessOnboarding>(
        `/businesses/${businessId}/onboarding/complete`,
        {
          method: "POST",
          body: JSON.stringify({ revision }),
        },
      ),
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
      history: (id: string) =>
        apiRequest<StrategyVersionHistory>(`/strategies/${id}/history`),
      compare: (id: string, baseVersionId: string, targetVersionId: string) =>
        apiRequest<StrategyVersionComparison>(
          `/strategies/${id}/compare${query({
            base_version_id: baseVersionId,
            target_version_id: targetVersionId,
          })}`,
        ),
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
  providers: {
    list: () => apiRequest<ProviderConfig[]>("/providers"),
    update: (config: ProviderConfig) =>
      apiRequest<ProviderConfig>(`/providers/${config.kind}/${config.provider}`, {
        method: "PUT",
        body: JSON.stringify({
          is_active: config.is_active,
          priority: config.priority,
          fallback_provider: config.fallback_provider,
          timeout_seconds: config.timeout_seconds,
          max_attempts: config.max_attempts,
          test_mode: config.test_mode,
          secret_environment_key: config.secret_environment_key,
        }),
      }),
    test: (config: ProviderConfig) =>
      apiRequest<ProviderTestResult>(`/providers/${config.kind}/${config.provider}/test`, { method: "POST" }),
  },
  privacy: {
    purposes: () => apiRequest<DataPurpose[]>("/privacy/purposes"),
    consents: () => apiRequest<ConsentRecord[]>("/privacy/consents"),
    consent: (purposeCode: string, policyVersion: string, accepted: boolean) => apiRequest<ConsentRecord>("/privacy/consents", { method: "POST", body: JSON.stringify({ purpose_code: purposeCode, policy_version: policyVersion, accepted }) }),
    export: () => apiRequest<Record<string, unknown>>("/privacy/export"),
    requests: () => apiRequest<PrivacyRequest[]>("/privacy/requests"),
    createRequest: (requestType: "EXPORT" | "DELETION", reason: string) => apiRequest<PrivacyRequest>("/privacy/requests", { method: "POST", body: JSON.stringify({ request_type: requestType, reason }) }),
    adminRequests: () => apiRequest<PrivacyRequest[]>("/privacy/admin/requests"),
    resolve: (id: string, decision: "COMPLETE" | "REJECT", notes: string) => apiRequest<PrivacyRequest>(`/privacy/admin/requests/${id}/resolve`, { method: "POST", body: JSON.stringify({ decision, notes }) }),
    retention: () => apiRequest<RetentionPolicy[]>("/privacy/admin/retention"),
    saveRetention: (resourceType: string, retentionDays: number, legalHold: boolean, justification: string) => apiRequest<RetentionPolicy>(`/privacy/admin/retention/${resourceType}`, { method: "PUT", body: JSON.stringify({ retention_days: retentionDays, legal_hold: legalHold, justification }) }),
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
    history: (id: string) =>
      apiRequest<ContentVersionHistory>(`/contents/${id}/history`),
    compare: (id: string, baseVersionId: string, targetVersionId: string) =>
      apiRequest<ContentVersionComparison>(
        `/contents/${id}/compare${query({
          base_version_id: baseVersionId,
          target_version_id: targetVersionId,
        })}`,
      ),
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
