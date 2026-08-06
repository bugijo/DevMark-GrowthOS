import { describe, expect, it } from "vitest";

import { aiCostLabel } from "@/lib/ai-cost";

describe("aiCostLabel", () => {
  it("distingue custo positivo e zero confirmados", () => {
    expect(aiCostLabel({ cost_status: "CONFIRMED", cost_usd: "0.00012000" })).toBe(
      "US$ 0,00012 confirmado",
    );
    expect(aiCostLabel({ cost_status: "CONFIRMED", cost_usd: "0.00000000" })).toBe(
      "US$ 0,00 confirmado",
    );
  });

  it("distingue estimativa e ausência", () => {
    expect(aiCostLabel({ cost_status: "ESTIMATED", cost_usd: "0.12" })).toBe(
      "US$ 0,12 estimado",
    );
    expect(aiCostLabel({ cost_status: "UNKNOWN", cost_usd: null })).toBe(
      "Custo não informado pelo provider",
    );
  });
});
