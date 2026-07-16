import { describe, expect, it } from "vitest";

import {
  approvalFor,
  formatBytes,
  manualPublicationKey,
  monthBounds,
  periodReportCsv,
  splitLines,
  visualPresetMissingFields,
} from "@/lib/phase2";
import type { PeriodReport } from "@/types/api";

describe("helpers operacionais da Fase 2", () => {
  it("normaliza listas e tamanhos sem perder informação", () => {
    expect(splitLines(" prevenção, educação\nacolhimento ")).toEqual([
      "prevenção",
      "educação",
      "acolhimento",
    ]);
    expect(formatBytes(1536)).toBe("1.5 KB");
  });

  it("localiza a decisão do componente e cria chave manual estável", () => {
    const approval = {
      id: "approval-image",
      content_item_id: "content",
      content_version_id: "version",
      stage: "CLIENT" as const,
      component: "IMAGE" as const,
      status: "PENDING" as const,
      requested_by_user_id: "user",
      decided_by_user_id: null,
      decision_comment: null,
      decided_at: null,
    };
    expect(approvalFor([approval], "IMAGE")?.id).toBe("approval-image");
    expect(manualPublicationKey("content", "2026-08-05T15:30")).toBe(
      "manual:content:202608051530",
    );
  });

  it("calcula o período mensal incluindo anos bissextos", () => {
    expect(monthBounds(new Date(2024, 1, 15))).toEqual({
      startsOn: "2024-02-01",
      endsOn: "2024-02-29",
    });
  });

  it("exporta somente os agregados autorizados do relatório", () => {
    const report: PeriodReport = {
      organization_id: "org",
      business_id: "business",
      starts_on: "2026-08-01",
      ends_on: "2026-08-31",
      content_total: 3,
      content_by_status: { APPROVED: 2, PUBLISHED: 1 },
      content_versions_total: 4,
      revisions_total: 1,
      approvals_by_component: { TEXT: { APPROVED: 2 } },
      manual_publications_total: 1,
      publications_by_channel: { INSTAGRAM: 1 },
      strategies_total: 1,
      approved_strategies_total: 1,
      calendar_entries_total: 5,
      unavailable_metrics: ["impressões"],
    };
    const csv = periodReportCsv(report);
    expect(csv).toContain('"Conteúdos","3"');
    expect(csv).toContain('"Aprovação · TEXT · APPROVED","2"');
    expect(csv).not.toContain("organization_id");
    expect(csv).toContain('"Métrica indisponível · impressões","sem integração"');
  });

  it("informa os campos ausentes de um preset sem impedir o rascunho", () => {
    const missing = visualPresetMissingFields({
      name: "Preset",
      objective: "",
      format: "FEED",
      aspect_ratio: "1:1",
      creation_mode: "HYBRID",
      color_palette: [],
      fonts: [],
      logo_media_asset_id: null,
      logo_position: "",
      logo_scale_percent: null,
      safe_margins: {},
      background_style: "",
      photographic_style: "",
      realism_level: "alto",
      lighting: "",
      composition: "",
      max_text_characters: 90,
      text_rules: [],
      base_prompt: "",
      negative_prompt: "",
      allowed_elements: [],
      forbidden_elements: [],
      visual_signature: "",
      default_cta: "",
    });
    expect(missing).toContain("margens seguras");
    expect(missing).toContain("logo");
    expect(missing).toContain("prompt-base");
  });
});
