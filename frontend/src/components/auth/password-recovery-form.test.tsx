import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  GENERIC_RECOVERY_MESSAGE,
  PasswordRecoveryForm,
} from "@/components/auth/password-recovery-form";
import { api } from "@/lib/api";

describe("PasswordRecoveryForm", () => {
  it("mostra a mesma resposta genérica mesmo quando a API rejeita", async () => {
    vi.spyOn(api.auth, "requestPasswordRecovery").mockRejectedValue(
      new Error("detalhe que não pode enumerar a conta"),
    );
    const user = userEvent.setup();
    render(<PasswordRecoveryForm />);

    await user.type(screen.getByLabelText(/^E-mail/), "unknown@example.com");
    await user.click(screen.getByRole("button", { name: "Enviar orientações" }));

    expect(await screen.findByText(GENERIC_RECOVERY_MESSAGE)).toBeVisible();
    expect(screen.queryByText(/detalhe que não pode enumerar/i)).not.toBeInTheDocument();
  });
});
