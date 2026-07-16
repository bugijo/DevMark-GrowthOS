import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ContentCard } from "@/components/content/content-card";
import type { ContentItem } from "@/types/api";

const content: ContentItem = {
  id: "content-1",
  business_id: "business-1",
  status: "CLIENT_REVIEW",
  current_version: {
    id: "version-1",
    version_number: 2,
    title: "Prevenção responsável",
    caption: "Conteúdo fictício para aprovação.",
    channel: "INSTAGRAM",
    format: "FEED",
    objective: "Educar",
    audience: "Tutores",
    cta: "Converse com a equipe",
    media_asset_ids: ["media-1"],
  },
  approvals: [
    {
      id: "approval-text",
      content_item_id: "content-1",
      content_version_id: "version-1",
      stage: "CLIENT",
      component: "TEXT",
      status: "APPROVED",
      requested_by_user_id: "agency-user",
      decided_by_user_id: "client-user",
      decision_comment: "Texto aprovado com clareza.",
      decided_at: "2026-07-15T18:00:00Z",
    },
  ],
};

describe("ContentCard", () => {
  it("libera a prévia privada antes da decisão visual e preserva o histórico", async () => {
    const user = userEvent.setup();
    const onRevealMedia = vi.fn();
    const { rerender } = render(
      <ContentCard content={content} onRevealMedia={onRevealMedia} />,
    );

    await user.click(screen.getByRole("button", { name: "Abrir imagem para revisar" }));
    expect(onRevealMedia).toHaveBeenCalledOnce();
    expect(screen.getByText("Texto aprovado com clareza.")).toBeInTheDocument();

    rerender(
      <ContentCard
        content={content}
        mediaPreviewUrl="http://storage.local/signed-preview"
        onRevealMedia={onRevealMedia}
      />,
    );
    expect(screen.getByRole("img", { name: /Imagem em aprovação/ })).toHaveAttribute(
      "src",
      "http://storage.local/signed-preview",
    );
  });
});
