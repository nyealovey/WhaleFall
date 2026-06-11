import { describe, expect, it } from "vitest";

import { flattenNavigationItems, navigationGroups } from "./navigation";

describe("console navigation", () => {
  it("defines the full legacy module skeleton for the React console", () => {
    expect(navigationGroups.map((group) => group.label)).toEqual([
      "态势总览",
      "资源管理",
      "账户与权限",
      "容量与审计",
      "自动化",
      "系统管理"
    ]);

    const labels = flattenNavigationItems(navigationGroups).map((item) => item.label);
    expect(labels).toEqual([
      "仪表盘",
      "风险中心",
      "实例管理",
      "群集管理",
      "数据库台账",
      "账户台账",
      "账户分类",
      "分类统计",
      "实例容量",
      "数据库容量",
      "实例统计",
      "账户统计",
      "数据库统计",
      "定时任务",
      "会话中心",
      "日志中心",
      "变更历史",
      "用户管理",
      "系统设置",
      "凭据管理",
      "标签管理",
      "分区管理"
    ]);
  });

  it("keeps every placeholder linked back to the existing Flask page", () => {
    const items = flattenNavigationItems(navigationGroups);

    expect(items.every((item) => item.consolePath.startsWith("/"))).toBe(true);
    expect(items.every((item) => item.legacyHref.startsWith("/"))).toBe(true);
    expect(items.some((item) => item.legacyHref === "/dashboard/")).toBe(true);
    expect(items.some((item) => item.legacyHref === "/instances/")).toBe(true);
  });
});
