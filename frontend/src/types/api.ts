export type Role =
  | "SUPER_ADMIN"
  | "AGENCY_ADMIN"
  | "STRATEGIST"
  | "CONTENT_EDITOR"
  | "DESIGNER"
  | "CLIENT_OWNER"
  | "CLIENT_REVIEWER"
  | "VIEWER";

export type MembershipStatus = "ACTIVE" | "SUSPENDED" | "REVOKED";
export type InviteStatus = "PENDING" | "ACCEPTED" | "EXPIRED" | "REVOKED";

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

export interface OrganizationMembership {
  id: string;
  organization_id: string;
  user: User;
  role: Role;
  business_id: string | null;
  status: MembershipStatus;
  invited_by_user_id: string | null;
  joined_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationInvite {
  id: string;
  organization_id: string;
  business_id: string | null;
  email: string;
  role: Role;
  status: InviteStatus;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  invited_by_user_id: string;
  created_at: string;
}

export interface OrganizationInviteInput {
  name: string;
  email: string;
  role: Role;
  business_id: string | null;
}

export interface OrganizationMembershipUpdate {
  role?: Role;
  business_id?: string | null;
  status?: MembershipStatus;
}

export interface InvitationInspection {
  organization: Organization;
  business_id: string | null;
  business_name: string | null;
  masked_email: string;
  role: Role;
  expires_at: string;
  requires_account_setup: boolean;
}

export interface InvitationAcceptance {
  user: User;
  membership: Membership;
  organization: Organization;
  accepted_at: string;
  login_required: boolean;
}

export interface SecurityMessage {
  message: string;
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
  is_active?: boolean;
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

export interface CatalogResource {
  id: string;
  organization_id: string;
  business_id: string;
  name: string;
  description: string;
  is_active: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Service extends CatalogResource {
  category: string;
  warnings: string[];
}

export interface AudienceSegment extends CatalogResource {
  needs: string[];
  objections: string[];
  location: string;
}

export interface MarketingObjective extends CatalogResource {
  planned_indicators: string[];
}

export type VisualCreationMode = "TEMPLATE" | "AI_IMAGE" | "HYBRID" | "MANUAL";

export interface VisualPreset {
  id: string;
  organization_id: string;
  business_id: string;
  brand_profile_id: string;
  name: string;
  objective: string;
  format: string;
  aspect_ratio: string;
  creation_mode: VisualCreationMode;
  color_palette: string[];
  fonts: string[];
  logo_media_asset_id: string | null;
  logo_position: string;
  logo_scale_percent: number | null;
  safe_margins: Record<string, number>;
  background_style: string;
  photographic_style: string;
  realism_level: string;
  lighting: string;
  composition: string;
  max_text_characters: number | null;
  text_rules: string[];
  base_prompt: string;
  negative_prompt: string;
  allowed_elements: string[];
  forbidden_elements: string[];
  visual_signature: string;
  default_cta: string;
  version: number;
  is_active: boolean;
  archived_at: string | null;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export type VisualPresetInput = Omit<
  VisualPreset,
  | "id"
  | "organization_id"
  | "business_id"
  | "brand_profile_id"
  | "version"
  | "is_active"
  | "archived_at"
  | "created_by_user_id"
  | "updated_by_user_id"
  | "created_at"
  | "updated_at"
>;

export interface VisualPrompt {
  business_id: string;
  preset_id: string;
  preset_version: number;
  prompt: string;
  negative_prompt: string;
  provider_name: string;
  provider_reference: string;
}

export interface StrategyVersion {
  id: string;
  version_number: number;
  objective: string;
  positioning: string;
  funnel: string[];
  channels: string[];
  pillars: Array<string | Record<string, unknown>>;
  planned_indicators: string[];
  service_snapshots: Array<Record<string, unknown>>;
  audience_snapshots: Array<Record<string, unknown>>;
  objective_snapshots: Array<Record<string, unknown>>;
  source: string;
  provider_name: string;
  provider_reference: string;
  created_at: string;
}

export interface ContentStrategy {
  id: string;
  organization_id: string;
  business_id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  status: string;
  current_version: StrategyVersion;
  approved_version_id: string | null;
  decision_comment: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StrategyVersionInput {
  objective: string;
  positioning: string;
  funnel: string[];
  channels: string[];
  pillars: string[];
  planned_indicators: string[];
  service_ids: string[];
  audience_ids: string[];
  marketing_objective_ids: string[];
}

export interface StrategyInput extends StrategyVersionInput {
  name: string;
  starts_on: string;
  ends_on: string;
}

export interface ContentPlan {
  id: string;
  organization_id: string;
  business_id: string;
  content_strategy_id: string;
  strategy_version_id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  frequency: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarEntry {
  id: string;
  organization_id: string;
  business_id: string;
  content_plan_id: string;
  content_item_id: string | null;
  visual_preset_id: string | null;
  title: string;
  objective: string;
  audience: string;
  channel: string;
  format: string;
  suggested_for: string;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface MediaAsset {
  id: string;
  organization_id: string;
  business_id: string;
  kind: string;
  storage_provider: string;
  display_name: string;
  mime_type: string;
  byte_size: number;
  checksum_sha256: string;
  width: number | null;
  height: number | null;
  origin: string;
  processing_status: string;
  created_at: string;
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
  service_id?: string | null;
  audience_segment_id?: string | null;
  marketing_objective_id?: string | null;
  notes?: string;
  script?: string;
  visual_prompt?: string;
  negative_prompt?: string;
  brand_context_snapshot?: Record<string, unknown>;
  visual_preset_snapshot?: Record<string, unknown>;
  media_asset_ids?: string[];
  provider_name?: string;
  created_at?: string;
}

export type ApprovalComponent = "TEXT" | "IMAGE";
export type ApprovalStatus = "PENDING" | "APPROVED" | "CHANGES_REQUESTED" | "CANCELLED";

export interface Approval {
  id: string;
  content_item_id: string;
  content_version_id: string;
  stage: "INTERNAL" | "CLIENT";
  component: ApprovalComponent;
  status: ApprovalStatus;
  requested_by_user_id: string | null;
  decided_by_user_id: string | null;
  decision_comment: string | null;
  decided_at: string | null;
}

export interface ContentItem {
  id: string;
  organization_id?: string;
  business_id: string;
  status: ContentStatus;
  content_strategy_id?: string | null;
  strategy_version_id?: string | null;
  content_plan_id?: string | null;
  calendar_entry_id?: string | null;
  visual_preset_id?: string | null;
  scheduled_for?: string | null;
  published_at?: string | null;
  publication_channel?: string | null;
  publication_reference?: string | null;
  published_by_user_id?: string | null;
  change_request_comment?: string | null;
  current_version: ContentVersion;
  approvals?: Approval[];
  created_at?: string;
  updated_at?: string;
}

export interface ContentRevisionInput {
  title: string;
  caption: string;
  cta: string;
  notes?: string;
  script?: string;
}

export interface ContentGenerateInput {
  business_id: string;
  objective: string;
  channel: string;
  format: string;
  content_strategy_id?: string;
  strategy_version_id?: string;
  content_plan_id?: string;
  calendar_entry_id?: string;
  visual_preset_id?: string;
  service_id?: string;
  audience_segment_id?: string;
  marketing_objective_id?: string;
  media_asset_id?: string;
  notes?: string;
  script?: string;
}

export interface VisualRevisionInput {
  visual_preset_id?: string | null;
  media_asset_id?: string | null;
  visual_prompt?: string | null;
  negative_prompt?: string | null;
}

export interface ManualPublicationInput {
  channel: string;
  published_at: string;
  reference?: string;
  idempotency_key: string;
}

export interface PeriodReport {
  organization_id: string;
  business_id: string;
  starts_on: string;
  ends_on: string;
  content_total: number;
  content_by_status: Record<string, number>;
  content_versions_total: number;
  revisions_total: number;
  approvals_by_component: Record<string, Record<string, number>>;
  manual_publications_total: number;
  publications_by_channel: Record<string, number>;
  strategies_total: number;
  approved_strategies_total: number;
  calendar_entries_total: number;
  unavailable_metrics: string[];
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
