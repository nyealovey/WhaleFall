import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const frontendRoot = resolve(__dirname, "..");

function readSource(path: string) {
  return readFileSync(resolve(frontendRoot, path), "utf8");
}

describe("bundle splitting", () => {
  it("does not keep the temporary RemainingReadOnlyPages migration module", () => {
    expect(existsSync(resolve(frontendRoot, "src/pages/RemainingReadOnlyPages.tsx"))).toBe(false);
    expect(existsSync(resolve(frontendRoot, "src/pages/RemainingReadOnlyPages.test.tsx"))).toBe(false);

    for (const path of [
      "src/pages/CatalogAdminPages.tsx",
      "src/pages/ClassificationPages.tsx",
      "src/pages/ClustersPage.tsx",
      "src/pages/PartitionsPage.tsx",
      "src/pages/SchedulerPage.tsx",
      "src/pages/SettingsPage.tsx",
      "src/pages/SyncSessionsPage.tsx"
    ]) {
      expect(readSource(path)).not.toContain("RemainingReadOnlyPages");
    }
  });

  it("loads migrated route pages through dynamic imports instead of static page imports", () => {
    const appSource = readSource("src/App.tsx");
    const routeModules = [
      "AuditPages",
      "AboutPage",
      "CapacityPages",
      "DashboardPage",
      "ListPages",
      "PlaceholderPage",
      "RiskCenterPage",
      "StatisticsPages",
      "ClustersPage",
      "ClassificationPages",
      "SchedulerPage",
      "SyncSessionsPage",
      "SettingsPage",
      "CatalogAdminPages",
      "PartitionsPage"
    ];

    for (const moduleName of routeModules) {
      expect(appSource).toContain(`import("./pages/${moduleName}")`);
      expect(appSource).not.toContain(`from "./pages/${moduleName}"`);
    }
    expect(appSource).not.toContain('from "./pages/RemainingReadOnlyPages"');
  });

  it("keeps stable third party libraries in dedicated vendor chunks", () => {
    const viteSource = readSource("vite.config.ts");

    expect(viteSource).toContain("react-vendor");
    expect(viteSource).toContain("react-router-dom");
    expect(viteSource).toContain("query-table");
    expect(viteSource).toContain("@tanstack/react-query");
    expect(viteSource).toContain("@tanstack/react-table");
    expect(viteSource).toContain("radix-ui");
    expect(viteSource).toContain("@radix-ui/");
    expect(viteSource).toContain("charts");
  });
});
