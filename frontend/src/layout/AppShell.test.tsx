import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";
import { navigationGroups } from "../navigation";
import type { SessionUser } from "../types/auth";

const user: SessionUser = {
  id: 1,
  username: "admin",
  role: "admin",
  is_active: true
};

describe("AppShell", () => {
  it("renders the complete React console navigation without replacing legacy links", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AppShell navigationGroups={navigationGroups} user={user} onLogout={vi.fn()}>
          <main>Dashboard body</main>
        </AppShell>
      </MemoryRouter>
    );

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByText("鲸落")).toBeInTheDocument();
    expect(screen.getByText("OPS CONSOLE")).toBeInTheDocument();
    expect(screen.getByText("Dashboard body")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /实例管理/ })).toHaveAttribute("href", "/instances");
    expect(screen.getByRole("link", { name: /系统设置/ })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: "修改密码" })).toHaveAttribute("href", "/auth/change-password");
    expect(screen.getByRole("button", { name: "退出" })).toBeInTheDocument();
  });
});
