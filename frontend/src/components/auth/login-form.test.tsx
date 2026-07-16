import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/login-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: null,
    checkingSession: false,
    loading: false,
    signIn: vi.fn(),
  }),
}));

describe("LoginForm", () => {
  it("mantém um único título principal visível em qualquer viewport", () => {
    render(<LoginForm />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { level: 1, name: "Entre na sua conta" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", {
        name: "Marketing organizado, com controle humano.",
      }),
    ).not.toBeInTheDocument();
  });
});
