import { describe, expect, it } from "vitest";

import { legacyParityPages, parityByConsolePath } from "./legacyParity";

describe("legacyParityPages", () => {
  it("tracks every console navigation page plus known legacy drill-down pages", () => {
    expect(legacyParityPages).toHaveLength(26);
    expect(parityByConsolePath("/clusters")?.sections.map((section) => section.title)).toEqual(
      expect.arrayContaining(["SQL Server 群集列表", "AG 配置", "AG 状态面板", "AG 账户面板", "MySQL 群集列表", "MySQL 主从状态面板"])
    );
    expect(parityByConsolePath("/tags/bulk/assign")?.actions).toEqual(
      expect.arrayContaining(["分配模式", "移除模式", "清空选择", "执行操作"])
    );
  });

  it("keeps field parity explicit for pages that were previously simplified", () => {
    const requiredPaths = [
      "/clusters",
      "/account-classifications",
      "/classification-statistics",
      "/scheduler",
      "/sync-sessions",
      "/users",
      "/settings",
      "/credentials",
      "/tags",
      "/partitions"
    ];

    for (const path of requiredPaths) {
      const page = parityByConsolePath(path);
      expect(page, path).toBeDefined();
      expect(page?.sections.length, path).toBeGreaterThan(0);
      expect(page?.filters.length, path).toBeGreaterThan(0);
      expect(page?.actions.length, path).toBeGreaterThan(0);
      expect(page?.apiPaths.length, path).toBeGreaterThan(0);
    }
  });

  it("documents the old-page fields that React pages must render", () => {
    expect(parityByConsolePath("/sync-sessions")?.sections[0]?.fields).toEqual([
      "运行ID",
      "状态",
      "进度",
      "任务",
      "来源",
      "分类",
      "开始时间",
      "耗时",
      "操作"
    ]);

    expect(parityByConsolePath("/credentials")?.sections[0]?.fields).toEqual([
      "凭据",
      "类型",
      "数据库类型",
      "状态",
      "绑定实例",
      "创建时间",
      "操作"
    ]);
  });
});
