import { describe, expect, it } from "vitest";

import { joinCommaSeparated, splitCommaSeparated } from "@/lib/format";

describe("campos separados por vírgula", () => {
  it("remove espaços e itens vazios", () => {
    expect(splitCommaSeparated("acolhedor,  claro, , profissional ")).toEqual([
      "acolhedor",
      "claro",
      "profissional",
    ]);
  });

  it("apresenta listas de forma editável", () => {
    expect(joinCommaSeparated(["#146B5F", "branco"])).toBe("#146B5F, branco");
  });
});
