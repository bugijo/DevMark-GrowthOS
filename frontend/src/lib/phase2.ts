import type {
  Approval,
  ApprovalComponent,
  PeriodReport,
  VisualPresetInput,
} from "@/types/api";

export function splitLines(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function localDateTimeToIso(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toISOString();
}

export function monthBounds(now = new Date()): { startsOn: string; endsOn: string } {
  const year = now.getFullYear();
  const month = now.getMonth();
  const format = (value: Date) => {
    const yyyy = value.getFullYear();
    const mm = String(value.getMonth() + 1).padStart(2, "0");
    const dd = String(value.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  };
  return {
    startsOn: format(new Date(year, month, 1)),
    endsOn: format(new Date(year, month + 1, 0)),
  };
}

export function approvalFor(
  approvals: Approval[] | undefined,
  component: ApprovalComponent,
): Approval | undefined {
  return approvals?.find((approval) => approval.component === component);
}

export function manualPublicationKey(contentId: string, publishedAt: string): string {
  const compactDate = publishedAt.replace(/\D/g, "").slice(0, 14) || "sem-data";
  return `manual:${contentId}:${compactDate}`;
}

export function visualPresetMissingFields(preset: VisualPresetInput): string[] {
  const missing: string[] = [];
  const textFields: Array<[keyof VisualPresetInput, string]> = [
    ["objective", "objetivo"],
    ["background_style", "estilo de fundo"],
    ["photographic_style", "estilo fotográfico"],
    ["lighting", "iluminação"],
    ["composition", "composição"],
    ["base_prompt", "prompt-base"],
    ["negative_prompt", "prompt negativo"],
    ["visual_signature", "assinatura visual"],
    ["default_cta", "CTA padrão"],
  ];
  textFields.forEach(([field, label]) => {
    if (!String(preset[field] ?? "").trim()) missing.push(label);
  });
  const listFields: Array<[keyof VisualPresetInput, string]> = [
    ["color_palette", "paleta"],
    ["fonts", "fontes"],
    ["text_rules", "regras de texto"],
    ["allowed_elements", "elementos permitidos"],
    ["forbidden_elements", "elementos proibidos"],
  ];
  listFields.forEach(([field, label]) => {
    if (!Array.isArray(preset[field]) || preset[field].length === 0) missing.push(label);
  });
  if (!preset.logo_media_asset_id) missing.push("logo");
  if (!preset.logo_position.trim()) missing.push("posição do logo");
  if (!preset.logo_scale_percent) missing.push("escala do logo");
  if (
    ["top", "right", "bottom", "left"].some(
      (side) => typeof preset.safe_margins[side] !== "number",
    )
  ) {
    missing.push("margens seguras");
  }
  return missing;
}

function csvCell(value: string | number): string {
  const normalized = String(value).replaceAll('"', '""');
  return `"${normalized}"`;
}

export function periodReportCsv(report: PeriodReport): string {
  const rows: Array<[string, string | number]> = [
    ["Empresa", report.business_id],
    ["Início", report.starts_on],
    ["Fim", report.ends_on],
    ["Conteúdos", report.content_total],
    ["Versões", report.content_versions_total],
    ["Revisões", report.revisions_total],
    ["Publicações manuais", report.manual_publications_total],
    ["Estratégias", report.strategies_total],
    ["Estratégias aprovadas", report.approved_strategies_total],
    ["Pautas no calendário", report.calendar_entries_total],
  ];
  Object.entries(report.content_by_status).forEach(([status, total]) => {
    rows.push([`Conteúdo · ${status}`, total]);
  });
  Object.entries(report.publications_by_channel).forEach(([channel, total]) => {
    rows.push([`Publicação · ${channel}`, total]);
  });
  Object.entries(report.approvals_by_component).forEach(([component, statuses]) => {
    Object.entries(statuses).forEach(([status, total]) => {
      rows.push([`Aprovação · ${component} · ${status}`, total]);
    });
  });
  report.unavailable_metrics.forEach((metric) => {
    rows.push([`Métrica indisponível · ${metric}`, "sem integração"]);
  });
  return ["Indicador,Valor", ...rows.map(([label, value]) => `${csvCell(label)},${csvCell(value)}`)]
    .join("\n")
    .concat("\n");
}
