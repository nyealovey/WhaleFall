import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AboutPage } from "./AboutPage";

describe("AboutPage", () => {
  it("renders the legacy footer about page content in React", () => {
    render(<AboutPage />);

    expect(screen.getByRole("heading", { name: "面向 DBA 的数据库资源管理平台" })).toBeInTheDocument();
    expect(screen.getByText("鲸落 WhaleFall")).toBeInTheDocument();
    expect(screen.getByText("项目介绍")).toBeInTheDocument();
    expect(screen.getByText("核心功能")).toBeInTheDocument();
    expect(screen.getByText("技术栈")).toBeInTheDocument();
    expect(screen.getByText("支持的数据库")).toBeInTheDocument();
    expect(screen.getByText("更新日志")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("SQL Server")).toBeInTheDocument();
    expect(screen.getAllByText("版本 1.5.0").length).toBeGreaterThan(0);
  });
});
