import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field, Input, Select } from "@/components/ui/form-controls";

describe("Field", () => {
  it("associa label, ajuda e erro ao controle com estado inválido", () => {
    render(
      <>
        <span id="ajuda-externa">Use seu endereço profissional.</span>
        <Field
          label="E-mail"
          hint="Não compartilharemos este endereço."
          error="Informe um e-mail válido."
          required
        >
          <Input type="email" aria-describedby="ajuda-externa" />
        </Field>
      </>,
    );

    const input = screen.getByRole("textbox", { name: "E-mail" });
    const describedBy = input.getAttribute("aria-describedby")?.split(" ") ?? [];
    const error = screen.getByText("Informe um e-mail válido.");
    const hint = screen.getByText("Não compartilharemos este endereço.");

    expect(input).toHaveAttribute("id", expect.stringMatching(/^field-/));
    expect(input).toBeRequired();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-errormessage", error.id);
    expect(describedBy).toEqual(
      expect.arrayContaining(["ajuda-externa", hint.id, error.id]),
    );
    expect(error).toHaveAttribute("role", "alert");
  });

  it("preserva um id explícito sem marcar um campo válido como inválido", () => {
    render(
      <Field id="segmento" label="Segmento">
        <Select defaultValue="clinica">
          <option value="clinica">Clínica veterinária</option>
        </Select>
      </Field>,
    );

    const select = screen.getByLabelText("Segmento");
    expect(select).toHaveAttribute("id", "segmento");
    expect(select).not.toHaveAttribute("aria-invalid");
    expect(select).not.toHaveAttribute("aria-describedby");
  });
});
