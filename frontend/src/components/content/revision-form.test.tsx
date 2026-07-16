import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RevisionForm } from "@/components/content/revision-form";
import type { ContentItem } from "@/types/api";

const content: ContentItem = {
  id: "content-1",
  business_id: "business-1",
  status: "CHANGES_REQUESTED",
  change_request_comment: "Trocar a chamada e deixar o texto mais direto.",
  current_version: {
    id: "version-1",
    version_number: 1,
    title: "Cuidado preventivo",
    caption: "Cuide hoje da saúde do seu pet.",
    channel: "INSTAGRAM",
    format: "FEED",
    objective: "Gerar agendamentos",
    cta: "Agende uma consulta",
  },
};

describe("RevisionForm", () => {
  it("mostra o feedback, preenche a versão e exige uma mudança real", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<RevisionForm content={content} busy={false} onSubmit={onSubmit} />);

    expect(
      screen.getByText("Trocar a chamada e deixar o texto mais direto."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Título/)).toHaveValue("Cuidado preventivo");
    expect(screen.getByLabelText(/Legenda/)).toHaveValue(
      "Cuide hoje da saúde do seu pet.",
    );

    const submit = screen.getByRole("button", {
      name: "Criar rascunho revisado",
    });
    expect(submit).toBeDisabled();

    await user.clear(screen.getByLabelText(/Chamada para ação/));
    await user.type(screen.getByLabelText(/Chamada para ação/), "  Fale conosco  ");
    expect(submit).toBeEnabled();
    await user.click(submit);

    expect(onSubmit).toHaveBeenCalledWith({
      title: "Cuidado preventivo",
      caption: "Cuide hoje da saúde do seu pet.",
      cta: "Fale conosco",
    });
  });

  it("não habilita o envio para alterações feitas somente com espaços", async () => {
    const user = userEvent.setup();
    render(<RevisionForm content={content} busy={false} onSubmit={vi.fn()} />);

    const title = screen.getByLabelText(/Título/);
    await user.clear(title);
    await user.type(title, "  Cuidado preventivo  ");

    expect(
      screen.getByRole("button", { name: "Criar rascunho revisado" }),
    ).toBeDisabled();
  });
});
