import { describe, expect, it } from "vitest";

import {
  hasMeaningfulRevisionChange,
  normalizeRevisionInput,
} from "@/lib/content-revision";

const original = {
  title: "Cuidado preventivo",
  caption: "Cuide hoje da saúde do seu pet.",
  cta: "Agende uma consulta",
};

describe("revisão de conteúdo", () => {
  it("ignora mudanças compostas somente por espaços", () => {
    expect(
      hasMeaningfulRevisionChange(original, {
        title: `  ${original.title}  `,
        caption: `${original.caption} `,
        cta: ` ${original.cta}`,
      }),
    ).toBe(false);
  });

  it("detecta uma alteração real e normaliza o payload", () => {
    const candidate = {
      ...original,
      caption: "  Nova legenda aprovada internamente.  ",
    };

    expect(hasMeaningfulRevisionChange(original, candidate)).toBe(true);
    expect(normalizeRevisionInput(candidate).caption).toBe(
      "Nova legenda aprovada internamente.",
    );
  });
});
