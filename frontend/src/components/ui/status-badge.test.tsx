import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/ui/status-badge";

describe("StatusBadge", () => {
  it("traduz o estado técnico para português", () => {
    render(<StatusBadge status="CLIENT_REVIEW" />);
    expect(screen.getByText("Aguardando cliente")).toBeInTheDocument();
  });
});
