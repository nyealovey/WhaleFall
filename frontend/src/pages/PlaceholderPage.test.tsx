import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlaceholderPage } from "./PlaceholderPage";

describe("PlaceholderPage", () => {
  it("shows a stable module shell with a link to the existing page", () => {
    render(
      <PlaceholderPage
        label="实例管理"
        description="React 页面骨架已就绪"
        legacyHref="/instances/"
      />
    );

    expect(screen.getByRole("heading", { name: "实例管理" })).toBeInTheDocument();
    expect(screen.getByText("React 页面骨架已就绪")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "在旧版打开" })).toHaveAttribute("href", "/instances/");
  });
});
