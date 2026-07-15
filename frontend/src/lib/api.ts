import type {
  ApiProblem,
  AuditLog,
  BrandProfile,
  Business,
  ContentItem,
  ListEnvelope,
  LoginResponse,
  MeResponse,
  Membership,
  Notification,
  Organization,
  User,
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
  contents: {
    list: (businessId?: string) =>
      apiRequest<ContentItem[] | ListEnvelope<ContentItem>>(
        `/contents${query({ business_id: businessId })}`,
      ),
    generate: (input: {
      business_id: string;
      objective: string;
      channel: string;
      format: string;
    }) =>
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
