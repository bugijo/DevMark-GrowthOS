import type {
  Business,
  BusinessOnboarding,
  NotificationCategory,
  OnboardingStepPayload,
  VisualPresetInput,
} from "@/types/api";

export const ONBOARDING_STEPS = [
  "Empresa e marca",
  "Segmento",
  "Serviços",
  "Públicos",
  "Objetivos",
  "Diferenciais",
  "Tom de voz",
  "Logos",
  "Cores e fontes",
  "Referências visuais",
  "Regras da marca",
  "Responsáveis pela aprovação",
  "Notificações",
  "Preset visual inicial",
  "Revisão final",
] as const;

export const NOTIFICATION_CATEGORIES: ReadonlyArray<{
  value: NotificationCategory;
  label: string;
}> = [
  { value: "CONTENT_AWAITING_APPROVAL", label: "Conteúdo aguardando aprovação" },
  { value: "CONTENT_CHANGES_REQUESTED", label: "Alterações solicitadas" },
  { value: "CONTENT_APPROVED", label: "Conteúdo aprovado" },
  { value: "STRATEGY_AWAITING_APPROVAL", label: "Estratégia aguardando aprovação" },
  { value: "INVITATION", label: "Convites" },
  { value: "PROCESSING_FAILED", label: "Falhas de processamento" },
  { value: "PUBLICATION_RECORDED", label: "Publicação registrada" },
  { value: "REPORT_AVAILABLE", label: "Relatório disponível" },
];

export interface ServiceDraft {
  id?: string;
  name: string;
  description: string;
  category: string;
  warnings: string;
}

export interface AudienceDraft {
  id?: string;
  name: string;
  description: string;
  needs: string;
  objections: string;
  location: string;
}

export interface ObjectiveDraft {
  id?: string;
  name: string;
  description: string;
  indicators: string;
}

export interface OnboardingFormState {
  company: {
    name: string;
    brandName: string;
    publicName: string;
    description: string;
    timezone: string;
  };
  segment: string;
  services: ServiceDraft[];
  audiences: AudienceDraft[];
  objectives: ObjectiveDraft[];
  differentiators: string;
  tone: {
    description: string;
    preferredWords: string;
    forbiddenWords: string;
  };
  logoIds: string[];
  visual: {
    primaryColors: string;
    secondaryColors: string;
    fonts: string;
  };
  referenceIds: string[];
  rules: {
    allowed: string;
    forbidden: string;
    requiredTerms: string;
    legal: string;
    imageRestrictions: string;
  };
  approverIds: string[];
  notifications: {
    emailEnabled: boolean;
    mode: "IMMEDIATE" | "DAILY" | "WEEKLY" | "URGENT_ONLY";
    timezone: string;
    digestTime: string;
    weeklyDay: number;
    disabledCategories: NotificationCategory[];
  };
  preset: {
    source: "existing" | "new";
    presetId: string;
    name: string;
    objective: string;
    format: string;
    aspectRatio: string;
    creationMode: VisualPresetInput["creation_mode"];
  };
  review: { confirmed: boolean; notes: string };
}

export type StepValidationErrors = Record<string, string>;

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function booleanValue(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringValues(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function listText(value: unknown): string {
  return stringValues(value).join("\n");
}

function stepData(onboarding: BusinessOnboarding, step: number): Record<string, unknown> {
  return recordValue(onboarding.step_data[String(step)]);
}

function catalogRows(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(recordValue) : [];
}

export function splitOnboardingList(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\n,]/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
}

export function createOnboardingFormState(
  business: Business,
  onboarding: BusinessOnboarding,
): OnboardingFormState {
  const company = stepData(onboarding, 1);
  const segment = stepData(onboarding, 2);
  const services = catalogRows(stepData(onboarding, 3).services);
  const audiences = catalogRows(stepData(onboarding, 4).audiences);
  const objectives = catalogRows(stepData(onboarding, 5).objectives);
  const differentiators = stepData(onboarding, 6);
  const tone = stepData(onboarding, 7);
  const logos = stepData(onboarding, 8);
  const visual = stepData(onboarding, 9);
  const references = stepData(onboarding, 10);
  const rules = stepData(onboarding, 11);
  const approvers = stepData(onboarding, 12);
  const notifications = stepData(onboarding, 13);
  const preset = stepData(onboarding, 14);
  const review = stepData(onboarding, 15);

  return {
    company: {
      name: stringValue(company.name, business.name),
      brandName: stringValue(company.brand_name, business.name),
      publicName: stringValue(company.public_name, business.name),
      description: stringValue(company.description),
      timezone: stringValue(company.timezone, business.timezone ?? "America/Sao_Paulo"),
    },
    segment: stringValue(segment.segment, business.segment),
    services:
      services.length > 0
        ? services.map((item) => ({
            id: stringValue(item.id) || undefined,
            name: stringValue(item.name),
            description: stringValue(item.description),
            category: stringValue(item.category),
            warnings: listText(item.warnings),
          }))
        : [{ name: "", description: "", category: "", warnings: "" }],
    audiences:
      audiences.length > 0
        ? audiences.map((item) => ({
            id: stringValue(item.id) || undefined,
            name: stringValue(item.name),
            description: stringValue(item.description),
            needs: listText(item.needs),
            objections: listText(item.objections),
            location: stringValue(item.location),
          }))
        : [{ name: "", description: "", needs: "", objections: "", location: "" }],
    objectives:
      objectives.length > 0
        ? objectives.map((item) => ({
            id: stringValue(item.id) || undefined,
            name: stringValue(item.name),
            description: stringValue(item.description),
            indicators: listText(item.planned_indicators),
          }))
        : [{ name: "", description: "", indicators: "" }],
    differentiators: listText(differentiators.differentiators),
    tone: {
      description: stringValue(tone.tone_of_voice),
      preferredWords: listText(tone.preferred_words),
      forbiddenWords: listText(tone.forbidden_words),
    },
    logoIds: stringValues(logos.logo_media_asset_ids),
    visual: {
      primaryColors: listText(visual.primary_colors),
      secondaryColors: listText(visual.secondary_colors),
      fonts: listText(visual.fonts),
    },
    referenceIds: stringValues(references.visual_reference_media_asset_ids),
    rules: {
      allowed: listText(rules.allowed_rules),
      forbidden: listText(rules.forbidden_rules),
      requiredTerms: listText(rules.required_terms),
      legal: listText(rules.legal_rules),
      imageRestrictions: listText(rules.image_restrictions),
    },
    approverIds: stringValues(approvers.membership_ids),
    notifications: {
      emailEnabled: booleanValue(notifications.email_enabled, true),
      mode:
        notifications.mode === "DAILY" ||
        notifications.mode === "WEEKLY" ||
        notifications.mode === "URGENT_ONLY"
          ? notifications.mode
          : "IMMEDIATE",
      timezone: stringValue(notifications.timezone, "America/Sao_Paulo"),
      digestTime: stringValue(notifications.digest_time, "09:00:00").slice(0, 5),
      weeklyDay: numberValue(notifications.weekly_day, 1),
      disabledCategories: stringValues(notifications.disabled_categories).filter(
        (category): category is NotificationCategory =>
          NOTIFICATION_CATEGORIES.some((item) => item.value === category),
      ),
    },
    preset: {
      source: stringValue(preset.preset_id) ? "existing" : "new",
      presetId: stringValue(preset.preset_id),
      name: "Preset inicial",
      objective: "Comunicar com clareza e consistência",
      format: "FEED",
      aspectRatio: "1:1",
      creationMode: "HYBRID",
    },
    review: {
      confirmed: review.confirmed === true,
      notes: stringValue(review.notes),
    },
  };
}

function duplicateNames(items: Array<{ name: string }>): boolean {
  const names = items.map((item) => item.name.trim().toLocaleLowerCase("pt-BR"));
  return new Set(names).size !== names.length;
}

function validTimezone(value: string): boolean {
  try {
    new Intl.DateTimeFormat("pt-BR", { timeZone: value }).format();
    return true;
  } catch {
    return false;
  }
}

export function validateOnboardingStep(
  step: number,
  state: OnboardingFormState,
): StepValidationErrors {
  const errors: StepValidationErrors = {};
  switch (step) {
    case 1:
      if (state.company.name.trim().length < 2) errors.name = "Informe o nome da empresa.";
      if (!state.company.brandName.trim()) errors.brandName = "Informe o nome da marca.";
      if (!validTimezone(state.company.timezone)) {
        errors.timezone = "Informe um fuso horário válido, como America/Sao_Paulo.";
      }
      break;
    case 2:
      if (state.segment.trim().length < 2) errors.segment = "Informe o segmento.";
      break;
    case 3:
      if (state.services.some((item) => !item.name.trim())) {
        errors.services = "Todos os serviços precisam de um nome.";
      } else if (duplicateNames(state.services)) {
        errors.services = "Não repita o mesmo serviço.";
      }
      break;
    case 4:
      if (state.audiences.some((item) => !item.name.trim())) {
        errors.audiences = "Todos os públicos precisam de um nome.";
      } else if (duplicateNames(state.audiences)) {
        errors.audiences = "Não repita o mesmo público.";
      }
      break;
    case 5:
      if (state.objectives.some((item) => !item.name.trim())) {
        errors.objectives = "Todos os objetivos precisam de um nome.";
      } else if (duplicateNames(state.objectives)) {
        errors.objectives = "Não repita o mesmo objetivo.";
      }
      break;
    case 6:
      if (splitOnboardingList(state.differentiators).length === 0) {
        errors.differentiators = "Informe ao menos um diferencial.";
      }
      break;
    case 7:
      if (state.tone.description.trim().length < 2) {
        errors.tone = "Descreva o tom de voz da marca.";
      }
      break;
    case 8:
      if (state.logoIds.length === 0) errors.logos = "Selecione ao menos um logo.";
      break;
    case 9: {
      const colors = splitOnboardingList(state.visual.primaryColors);
      const secondaryColors = splitOnboardingList(state.visual.secondaryColors);
      const colorPattern = /^(#[0-9a-f]{3,8}|[a-z][a-z0-9 ()-]{2,31})$/i;
      if (colors.length === 0) errors.primaryColors = "Informe ao menos uma cor principal.";
      else if (colors.some((color) => !colorPattern.test(color))) {
        errors.primaryColors = "Use hexadecimal (#146B5F) ou um nome de cor.";
      }
      if (secondaryColors.some((color) => !colorPattern.test(color))) {
        errors.secondaryColors = "Use hexadecimal (#DFF4EE) ou um nome de cor.";
      }
      if (splitOnboardingList(state.visual.fonts).length === 0) {
        errors.fonts = "Informe ao menos uma fonte.";
      }
      break;
    }
    case 10:
      if (state.referenceIds.length === 0) {
        errors.references = "Selecione ao menos uma referência visual.";
      }
      break;
    case 11:
      if (splitOnboardingList(state.rules.allowed).length === 0) {
        errors.allowed = "Informe ao menos uma orientação permitida.";
      }
      if (splitOnboardingList(state.rules.forbidden).length === 0) {
        errors.forbidden = "Informe ao menos uma restrição.";
      }
      break;
    case 12:
      if (state.approverIds.length === 0) {
        errors.approvers = "Selecione ao menos uma pessoa responsável pela aprovação.";
      }
      break;
    case 13:
      if (!validTimezone(state.notifications.timezone)) {
        errors.notificationTimezone = "Informe um fuso horário válido.";
      }
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(state.notifications.digestTime)) {
        errors.digestTime = "Informe um horário válido.";
      }
      break;
    case 14:
      if (state.preset.source === "existing" && !state.preset.presetId) {
        errors.preset = "Selecione um preset visual.";
      }
      if (state.preset.source === "new") {
        if (!state.preset.name.trim()) errors.presetName = "Informe um nome para o preset.";
        if (!state.preset.format.trim()) errors.presetFormat = "Informe o formato.";
        if (state.preset.aspectRatio.trim().length < 2) {
          errors.presetAspect = "Informe a proporção, como 1:1.";
        }
      }
      break;
    case 15:
      if (!state.review.confirmed) {
        errors.confirmed = "Confirme a revisão para salvar esta etapa.";
      }
      break;
  }
  return errors;
}

function initialPreset(state: OnboardingFormState): VisualPresetInput {
  const palette = splitOnboardingList(state.visual.primaryColors).concat(
    splitOnboardingList(state.visual.secondaryColors),
  );
  return {
    name: state.preset.name.trim(),
    objective: state.preset.objective.trim(),
    format: state.preset.format.trim(),
    aspect_ratio: state.preset.aspectRatio.trim(),
    creation_mode: state.preset.creationMode,
    color_palette: palette,
    fonts: splitOnboardingList(state.visual.fonts),
    logo_media_asset_id: state.logoIds[0] ?? null,
    logo_position: "canto inferior direito",
    logo_scale_percent: 18,
    safe_margins: { top: 8, right: 8, bottom: 8, left: 8 },
    background_style: "limpo e coerente com a marca",
    photographic_style: "natural e acolhedor",
    realism_level: "alto",
    lighting: "suave e natural",
    composition: "foco claro, espaço seguro para texto e logo",
    max_text_characters: 90,
    text_rules: ["Texto curto e legível"],
    base_prompt: "Aplicar o Brand Kit e manter uma composição clara e consistente.",
    negative_prompt: "Não usar elementos proibidos, marcas de terceiros ou texto ilegível.",
    allowed_elements: [],
    forbidden_elements: splitOnboardingList(state.rules.imageRestrictions),
    visual_signature: "Identidade visual consistente com o Brand Kit.",
    default_cta: "Saiba mais",
  };
}

export function buildOnboardingStepPayload(
  step: number,
  revision: number,
  state: OnboardingFormState,
): OnboardingStepPayload {
  switch (step) {
    case 1:
      return {
        step,
        revision,
        name: state.company.name.trim(),
        brand_name: state.company.brandName.trim(),
        public_name: state.company.publicName.trim(),
        description: state.company.description.trim(),
        timezone: state.company.timezone.trim(),
      };
    case 2:
      return { step, revision, segment: state.segment.trim() };
    case 3:
      return {
        step,
        revision,
        services: state.services.map((item) => ({
          ...(item.id ? { id: item.id } : {}),
          name: item.name.trim(),
          description: item.description.trim(),
          category: item.category.trim(),
          warnings: splitOnboardingList(item.warnings),
        })),
      };
    case 4:
      return {
        step,
        revision,
        audiences: state.audiences.map((item) => ({
          ...(item.id ? { id: item.id } : {}),
          name: item.name.trim(),
          description: item.description.trim(),
          needs: splitOnboardingList(item.needs),
          objections: splitOnboardingList(item.objections),
          location: item.location.trim(),
        })),
      };
    case 5:
      return {
        step,
        revision,
        objectives: state.objectives.map((item) => ({
          ...(item.id ? { id: item.id } : {}),
          name: item.name.trim(),
          description: item.description.trim(),
          planned_indicators: splitOnboardingList(item.indicators),
        })),
      };
    case 6:
      return { step, revision, differentiators: splitOnboardingList(state.differentiators) };
    case 7:
      return {
        step,
        revision,
        tone_of_voice: state.tone.description.trim(),
        preferred_words: splitOnboardingList(state.tone.preferredWords),
        forbidden_words: splitOnboardingList(state.tone.forbiddenWords),
      };
    case 8:
      return { step, revision, logo_media_asset_ids: state.logoIds };
    case 9:
      return {
        step,
        revision,
        primary_colors: splitOnboardingList(state.visual.primaryColors),
        secondary_colors: splitOnboardingList(state.visual.secondaryColors),
        fonts: splitOnboardingList(state.visual.fonts),
      };
    case 10:
      return { step, revision, visual_reference_media_asset_ids: state.referenceIds };
    case 11:
      return {
        step,
        revision,
        allowed_rules: splitOnboardingList(state.rules.allowed),
        forbidden_rules: splitOnboardingList(state.rules.forbidden),
        required_terms: splitOnboardingList(state.rules.requiredTerms),
        legal_rules: splitOnboardingList(state.rules.legal),
        image_restrictions: splitOnboardingList(state.rules.imageRestrictions),
      };
    case 12:
      return { step, revision, membership_ids: state.approverIds };
    case 13:
      return {
        step,
        revision,
        email_enabled: state.notifications.emailEnabled,
        mode: state.notifications.mode,
        timezone: state.notifications.timezone.trim(),
        digest_time: `${state.notifications.digestTime}:00`,
        weekly_day: state.notifications.weeklyDay,
        disabled_categories: state.notifications.disabledCategories,
      };
    case 14:
      return state.preset.source === "existing"
        ? { step, revision, preset_id: state.preset.presetId }
        : { step, revision, preset: initialPreset(state) };
    case 15:
      return { step, revision, confirmed: true, notes: state.review.notes.trim() };
    default:
      throw new Error("Etapa de onboarding desconhecida.");
  }
}
