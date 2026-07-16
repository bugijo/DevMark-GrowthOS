import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

function DialogHarness({ onConfirm = () => undefined }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Arquivar arquivo
      </button>
      <ConfirmationDialog
        open={open}
        title="Arquivar esta imagem?"
        description="Ela deixará de aparecer na biblioteca."
        confirmLabel="Arquivar"
        onClose={() => setOpen(false)}
        onConfirm={() => {
          onConfirm();
          setOpen(false);
        }}
      />
    </>
  );
}

describe("ConfirmationDialog", () => {
  it("recebe foco, fecha com Escape e devolve o foco ao acionador", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);

    const trigger = screen.getByRole("button", { name: "Arquivar arquivo" });
    await user.click(trigger);

    const dialog = screen.getByRole("alertdialog", {
      name: "Arquivar esta imagem?",
      description: "Ela deixará de aparecer na biblioteca.",
    });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("só confirma por uma ação explícita", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<DialogHarness onConfirm={onConfirm} />);

    await user.click(screen.getByRole("button", { name: "Arquivar arquivo" }));
    await user.click(screen.getByRole("button", { name: /^Arquivar$/ }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});
