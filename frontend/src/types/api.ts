export type Role =
  | "SUPER_ADMIN"
  | "AGENCY_ADMIN"
  | "STRATEGIST"
  | "CONTENT_EDITOR"
  | "DESIGNER"
  | "CLIENT_OWNER"
  | "CLIENT_REVIEWER"
  | "VIEWER";

export interface User {
  id: string;
  email: string;
  name?: string;
  full_name?: string;
  is_active?: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  created_at?: string;
}

export interface Membership {
  id?: string;
  organization_id: string;
  organization_name?: string;
  organization?: Organization;
  role: Role;
  roles?: Role[];
  business_id?: string | null;
  business_ids?: string[];
  is_active?: boolean;
}

export interface LoginResponse {
  user: User;
  membership: Membership;
  organization: Organization;
  csrf_token: string;
}

export type MeResponse = LoginResponse;

export interface Business {
  id: string;
  organization_id?: string;
  name: string;
  segment: string;
  created_at?: string;
  updated_at?: string;
}

export interface BrandProfile {
  id?: string;
  organization_id?: string;
  business_id?: string;
  brand_name: string;
  public_name: string;
  description: string;
  segment: string;
  audience: string;
  primary_colors: string[];
  tone_of_voice: string;
  preferred_words: string[];
  forbidden_words: string[];
  slogan: string;
  differentiators: string[];
  services: string[];
  contacts: string | Record<string, unknown> | null;
  links: string[];
  calls_to_action: string[];
  internal_notes: string;
  created_at?: string;
  updated_at?: string;
}

export type ContentStatus =
  | "DRAFT"
  | "INTERNAL_REVIEW"
  | "CLIENT_REVIEW"
  | "CHANGES_REQUESTED"
  | "APPROVED"
  | "SCHEDULED"
  | "PUBLISHED"
  | "FAILED"
  | "ARCHIVED";

export interface ContentVersion {
  id: string;
  version_number: number;
  title: string;
  caption: string;
  channel: string;
  format: string;
  objective: string;
  audience?: string;
  cta?: string;
  provider_name?: string;
  created_at?: string;
}

export interface ContentItem {
  id: string;
  organization_id?: string;
  business_id: string;
  status: ContentStatus;
  change_request_comment?: string | null;
  current_version: ContentVersion;
  created_at?: string;
  updated_at?: string;
}

export interface ContentRevisionInput {
  title: string;
  caption: string;
  cta: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type?: string;
  read_at?: string | null;
  created_at: string;
  resource_type?: string;
  resource_id?: string;
}

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  actor_user_id?: string;
  actor_name?: string;
  actor_email?: string;
  result?: string;
  details?: Record<string, unknown>;
  created_at: string;
}

export interface ListEnvelope<T> {
  items: T[];
  total?: number;
  page?: number;
  page_size?: number;
}

export interface ApiProblem {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
  message?: string;
  error?: string;
}
