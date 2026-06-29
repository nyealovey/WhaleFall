import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlaceholderPage } from "./PlaceholderPage";

describe("PlaceholderPage", () => {
  it("shows a stable module shell without a per-page legacy link", () => {
    render(<PlaceholderPage label="实例管理" description="React 页面骨架已就绪" />);

    expect(screen.getByRole("heading", { name: "实例管理" })).toBeInTheDocument();
    expect(screen.getByText("React 页面骨架已就绪")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "在旧版打开" })).not.toBeInTheDocument();
  });
});
