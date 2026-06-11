import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { CapacityDatabasesPage, CapacityInstancesPage } from "./CapacityPages";

vi.mock("@/api/capacity", () => ({
  fetchCapacityInstanceSnapshot: vi.fn(async () => ({
    summary: {
      total_instances: 2,
      total_size_mb: 3072,
      avg_size_mb: 1536,
      max_size_mb: 2048,
      period_type: "daily",
      source: "capacity_aggregation"
    },
    list: {
      items: [
        {
          id: 1,
          instance_id: 10,
          period_type: "daily",
          period_start: "2026-06-10",
          period_end: "2026-06-10",
          total_size_mb: 2048,
          avg_size_mb: 2048,
          max_size_mb: 2048,
          min_size_mb: 2048,
          data_count: 1,
          database_count: 12,
          total_size_change_mb: 128,
          total_size_change_percent: 6.7,
          growth_rate: 6.7,
          trend_direction: "up",
          instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 20,
      has_prev: false,
      has_next: false
    }
  })),
  fetchCapacityDatabaseSnapshot: vi.fn(async () => ({
    summary: {
      total_databases: 3,
      total_instances: 1,
      total_size_mb: 4096,
      avg_size_mb: 1365.3,
      max_size_mb: 2048,
      growth_rate: 3.2
    },
    list: {
      items: [
        {
          id: 2,
          instance_id: 10,
          database_name: "app_db",
          period_type: "daily",
          period_start: "2026-06-10",
          period_end: "2026-06-10",
          avg_size_mb: 2048,
          max_size_mb: 2048,
          min_size_mb: 2048,
          data_count: 1,
          size_change_mb: 64,
          size_change_percent: 3.2,
          growth_rate: 3.2,
          instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 20
    }
  }))
}));

function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

describe("CapacityPages", () => {
  it("renders instance capacity data from the API", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);

    await waitFor(() => {
      expect(screen.getByText("mysql-capacity")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "实例容量" })).toBeInTheDocument();
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders database capacity data from the API", async () => {
    renderWithQueryClient(<CapacityDatabasesPage />);

    await waitFor(() => {
      expect(screen.getByText("app_db")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "数据库容量" })).toBeInTheDocument();
    expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });
});
