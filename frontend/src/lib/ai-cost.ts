import type { AIGeneration } from "@/types/api";

export function aiCostLabel(
  generation: Pick<AIGeneration, "cost_status" | "cost_usd">,
): string {
  if (generation.cost_status === "UNKNOWN" || generation.cost_usd === null) {
    return "Custo não informado pelo provider";
  }
  const value = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8,
  }).format(Number(generation.cost_usd));
  const kind = generation.cost_status === "CONFIRMED" ? "confirmado" : "estimado";
  return `US$ ${value} ${kind}`;
}
