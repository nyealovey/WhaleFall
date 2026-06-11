import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RiskCenterPage } from "./RiskCenterPage";

vi.mock("@/api/riskCenter", () => ({
  fetchRiskCenterSnapshot: vi.fn(async () => ({
    summary: {
      total_instances: 2,
      severity_counts: { high: 1, medium: 1, low: 0, ok: 0 },
      db_type_counts: { mysql: { total: 1, high: 1, medium: 0, low: 0, ok: 0 } },
      top_risks: [{ rule_key: "backup_missing", instance_name: "db-critical", severity: "high", label: "备份缺失" }],
      generated_at: "2026-06-11T10:00:00"
    },
    cards: {
      items: [
        {
          instance_id: 1,
          name: "db-critical",
          db_type: "mysql",
          host: "10.0.0.1",
          port: 3306,
          overall_severity: "high",
          risk_score: 100,
          risk_items: [{ rule_key: "backup_missing", category: "backup", severity: "high", label: "备份缺失", detail: "未发现近期备份" }]
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 12
    }
  }))
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RiskCenterPage />
    </QueryClientProvider>
  );
}

describe("RiskCenterPage", () => {
  it("renders risk summary and cards from the API", async () => {
    renderWithQueryClient();

    await waitFor(() => {
      expect(screen.getAllByText("db-critical").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "风险中心" })).toBeInTheDocument();
    expect(screen.getAllByText("高风险").length).toBeGreaterThan(0);
    expect(screen.getAllByText("备份缺失").length).toBeGreaterThan(0);
    expect(screen.getByText("10.0.0.1:3306")).toBeInTheDocument();
    expect(screen.queryByText("React 页面骨架已就绪")).not.toBeInTheDocument();
  });
});
