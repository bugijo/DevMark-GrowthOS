import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ContentVersionComparisonPanel } from "@/components/content/version-comparison";
import { api } from "@/lib/api";
import type { ContentVersionComparison, ContentVersionHistory } from "@/types/api";

const summary = (id: string, version: number) => ({
  id,
  version_number: version,
  created_at: `2026-07-0${version}T12:00:00Z`,
  author: { name: version === 1 ? "Ana" : "Bruno" },
  is_current: version === 2,
  is_approved: version === 1,
  decisions: version === 1 ? [{ status: "APPROVED", component: "TEXT", comment: "Texto claro.", decided_at: "2026-07-03T12:00:00Z", decided_by: { name: "Cliente" } }] : [],
});

const history: ContentVersionHistory = {
  content_id: "content-1",
  business_id: "business-1",
  current_version_id: "version-2",
  versions: [summary("version-1", 1), summary("version-2", 2)],
};

const comparison: ContentVersionComparison = {
  content_id: "content-1",
  business_id: "business-1",
  base: {
    ...summary("version-1", 1),
    text: { title: "Antes", caption: "Legenda antiga", objective: "Educar", audience: "Tutores", cta: "Leia", script: "" },
    visual: { channel: "INSTAGRAM", format: "FEED", visual_prompt: "Imagem clara", preset: {}, media_asset_ids: ["media-1"] },
  },
  target: {
    ...summary("version-2", 2),
    text: { title: "Depois", caption: "Legenda nova", objective: "Educar", audience: "Tutores", cta: "Agende", script: "" },
    visual: { channel: "INSTAGRAM", format: "FEED", visual_prompt: "Imagem acolhedora", preset: {}, media_asset_ids: ["media-2"] },
  },
  changed_fields: ["text.title", "text.caption", "text.cta", "visual.visual_prompt", "visual.media_asset_ids"],
};

describe("ContentVersionComparisonPanel", () => {
  it("expõe antes/depois, decisões e controles acessíveis de imagem", async () => {
    vi.spyOn(api.contents, "history").mockResolvedValue(history);
    vi.spyOn(api.contents, "compare").mockResolvedValue(comparison);
    vi.spyOn(api.media, "signedUrl").mockImplementation(async (id) => ({ url: `https://storage.local/${id}`, expires_at: "2026-07-04T12:00:00Z" }));
    const user = userEvent.setup();
    render(<ContentVersionComparisonPanel contentId="content-1" />);

    await user.click(screen.getByRole("button", { name: "Comparar versões" }));
    expect(await screen.findByText(/5 campo\(s\) alterado\(s\)/)).toBeVisible();
    expect(screen.getByText("Texto claro.", { exact: false })).toBeVisible();
    expect(screen.getByText("Legenda antiga")).toBeVisible();
    expect(screen.getByText("Legenda nova")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "Visualização das imagens" })).toHaveValue("side-by-side");
    expect(screen.getByRole("slider", { name: "Zoom das imagens" })).toHaveValue("100");
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(2));

    await user.selectOptions(screen.getByRole("combobox", { name: "Visualização das imagens" }), "target");
    expect(screen.getAllByRole("img")).toHaveLength(1);
    expect(screen.getByRole("img")).toHaveAttribute("src", "https://storage.local/media-2");
  });
});
