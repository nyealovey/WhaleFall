import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCapacityDatabaseSnapshot, fetchCapacityInstanceSnapshot } from "@/api/capacity";
import { runAction } from "@/utils/action-feedback";

import { CapacityDatabasesPage, CapacityInstancesPage } from "./CapacityPages";

const actionMocks = vi.hoisted(() => ({
  triggerCapacityAggregation: vi.fn(async () => ({ run_id: "capacity-run" }))
}));

vi.mock("@/api/actions", () => actionMocks);

vi.mock("@/utils/action-feedback", () => ({
  runAction: vi.fn((promise: Promise<unknown>) => promise)
}));

vi.mock("@/api/capacity", () => ({
  getDefaultCapacityRange: vi.fn(() => ({ startDate: "2026-05-17", endDate: "2026-06-16" })),
  fetchCapacityInstanceOptions: vi.fn(async (dbTypes: string[] | string) => {
    const selectedTypes = Array.isArray(dbTypes) ? dbTypes : [dbTypes];
    const options = [
      { id: 10, name: "mysql-capacity", display_name: "mysql-capacity", db_type: "mysql" },
      { id: 20, name: "sqlserver-capacity", display_name: "sqlserver-capacity", db_type: "sqlserver" }
    ];
    return options.filter((item) => selectedTypes.includes(item.db_type));
  }),
  fetchCapacityDatabaseOptions: vi.fn(async () => [
    { id: 100, database_name: "app_db", is_active: true }
  ]),
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
    },
    charts: {
      trend: {
        items: [
          {
            id: 11,
            instance_id: 10,
            period_start: "2026-06-09",
            total_size_mb: 1024,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          },
          {
            id: 12,
            instance_id: 10,
            period_start: "2026-06-10",
            total_size_mb: 2048,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 2,
        page: 1,
        pages: 1,
        limit: 200
      },
      change: {
        items: [
          {
            id: 13,
            instance_id: 10,
            period_start: "2026-06-10",
            total_size_change_mb: 128,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 1,
        page: 1,
        pages: 1,
        limit: 200
      },
      percent: {
        items: [
          {
            id: 14,
            instance_id: 10,
            period_start: "2026-06-10",
            total_size_change_percent: 6.7,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 1,
        page: 1,
        pages: 1,
        limit: 200
      }
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
    },
    charts: {
      trend: {
        items: [
          {
            id: 21,
            database_name: "app_db",
            period_start: "2026-06-09",
            avg_size_mb: 1024,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          },
          {
            id: 22,
            database_name: "app_db",
            period_start: "2026-06-10",
            avg_size_mb: 2048,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 2,
        page: 1,
        pages: 1,
        limit: 200
      },
      change: {
        items: [
          {
            id: 23,
            database_name: "app_db",
            period_start: "2026-06-10",
            size_change_mb: 64,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 1,
        page: 1,
        pages: 1,
        limit: 200
      },
      percent: {
        items: [
          {
            id: 24,
            database_name: "app_db",
            period_start: "2026-06-10",
            size_change_percent: 3.2,
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          }
        ],
        total: 1,
        page: 1,
        pages: 1,
        limit: 200
      }
    }
  }))
}));

function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

async function chooseSelectOption(label: string, optionName: string) {
  fireEvent.click(screen.getByRole("combobox", { name: label }));
  fireEvent.click(await screen.findByRole("option", { name: optionName }));
}

async function chooseMultiOptions(label: string, optionNames: string[]) {
  fireEvent.click(screen.getByRole("button", { name: new RegExp(label) }));
  const dialog = await screen.findByRole("dialog", { name: `选择${label}` });
  for (const optionName of optionNames) {
    fireEvent.click(await within(dialog).findByLabelText(`选择 ${optionName}`));
  }
  fireEvent.click(within(dialog).getByRole("button", { name: "完成" }));
}

describe("CapacityPages", () => {
  beforeEach(() => {
    vi.mocked(runAction).mockClear();
  });

  it("renders instance capacity data from the API", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);

    await waitFor(() => {
      expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "实例容量" })).toBeInTheDocument();
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.queryByText("实例容量列表")).not.toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders instance capacity with legacy controls, metrics, and chart panels", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);

    await waitFor(() => {
      expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0);
    });

    for (const text of ["刷新数据", "统计当前周期", "数据库类型", "实例", "周期", "在线实例数", "总容量", "平均容量", "最大容量"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    for (const text of ["容量统计趋势图", "容量变化趋势图", "容量变化趋势图 (百分比)", "折线图", "柱状图", "TOP5", "TOP10", "TOP20", "7", "14", "30"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByRole("button", { name: "折线图" })[0]).toBeEnabled();
    expect(screen.getAllByRole("button", { name: "柱状图" })[0]).toBeEnabled();
    expect(screen.getAllByText("2026-06-10").length).toBeGreaterThan(0);
    expect(screen.queryByText("Instance capacity")).not.toBeInTheDocument();
    expect(screen.queryByText("按实例维度查看容量统计、容量变化和容量变化百分比趋势。")).not.toBeInTheDocument();
    expect(screen.queryByText("开始日期")).not.toBeInTheDocument();
    expect(screen.queryByText("结束日期")).not.toBeInTheDocument();
    expect(screen.queryByText(/日粒度 · 每页/)).not.toBeInTheDocument();
  });

  it("renders database capacity data from the API", async () => {
    renderWithQueryClient(<CapacityDatabasesPage />);

    await waitFor(() => {
      expect(screen.getAllByText("app_db").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "数据库容量" })).toBeInTheDocument();
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.queryByText("数据库容量列表")).not.toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders database capacity with legacy controls, metrics, and chart panels", async () => {
    renderWithQueryClient(<CapacityDatabasesPage />);

    await waitFor(() => {
      expect(screen.getAllByText("app_db").length).toBeGreaterThan(0);
    });

    for (const text of ["刷新数据", "统计当前周期", "数据库类型", "实例", "数据库", "周期", "总数据库数", "总容量", "平均容量", "最大容量"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    for (const text of ["容量统计趋势图", "容量变化趋势图", "容量变化趋势图 (百分比)", "折线图", "柱状图", "TOP5", "TOP10", "TOP20", "7", "14", "30"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByRole("button", { name: "折线图" })[0]).toBeEnabled();
    expect(screen.getAllByRole("button", { name: "柱状图" })[0]).toBeEnabled();
    expect(screen.getAllByText("2026-06-10").length).toBeGreaterThan(0);
    expect(screen.queryByText("Database capacity")).not.toBeInTheDocument();
    expect(screen.queryByText("按数据库维度查看容量统计、容量变化和容量变化百分比趋势。")).not.toBeInTheDocument();
    expect(screen.queryByText("开始日期")).not.toBeInTheDocument();
    expect(screen.queryByText("结束日期")).not.toBeInTheDocument();
    expect(screen.queryByText(/日粒度 · 每页/)).not.toBeInTheDocument();
  });

  it("triggers current-period aggregation from capacity pages", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByRole("button", { name: "统计当前周期" }));
    await waitFor(() => {
      expect(actionMocks.triggerCapacityAggregation).toHaveBeenCalledWith("instance");
    });

    cleanup();
    renderWithQueryClient(<CapacityDatabasesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("app_db").length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByRole("button", { name: "统计当前周期" }));
    await waitFor(() => {
      expect(actionMocks.triggerCapacityAggregation).toHaveBeenCalledWith("database");
    });
  });

  it("refreshes capacity pages through unified action feedback", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);
    await screen.findByRole("heading", { name: "实例容量" });
    await waitFor(() => expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0));
    vi.mocked(fetchCapacityInstanceSnapshot).mockClear();
    fireEvent.click(screen.getByRole("button", { name: "刷新数据" }));
    await waitFor(() => expect(fetchCapacityInstanceSnapshot).toHaveBeenCalledTimes(1));
    expect(runAction).toHaveBeenCalledWith(expect.any(Promise), { success: "实例容量数据已刷新" });

    cleanup();
    vi.mocked(runAction).mockClear();
    renderWithQueryClient(<CapacityDatabasesPage />);
    await screen.findByRole("heading", { name: "数据库容量" });
    await waitFor(() => expect(screen.getAllByText("app_db").length).toBeGreaterThan(0));
    vi.mocked(fetchCapacityDatabaseSnapshot).mockClear();
    fireEvent.click(screen.getByRole("button", { name: "刷新数据" }));
    await waitFor(() => expect(fetchCapacityDatabaseSnapshot).toHaveBeenCalledTimes(1));
    expect(runAction).toHaveBeenCalledWith(expect.any(Promise), { success: "数据库容量数据已刷新" });
  });

  it("applies instance and database capacity filters to API requests", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);
    await screen.findByRole("heading", { name: "实例容量" });
    await waitFor(() => expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0));
    vi.mocked(fetchCapacityInstanceSnapshot).mockClear();

    await chooseMultiOptions("数据库类型", ["MySQL"]);
    await chooseMultiOptions("实例", ["mysql-capacity"]);
    await chooseSelectOption("周期", "周");
    fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

    await waitFor(() => {
      expect(fetchCapacityInstanceSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({
          dbTypes: ["mysql"],
          instanceIds: [10],
          periodType: "weekly"
        })
      );
    });

    cleanup();
    renderWithQueryClient(<CapacityDatabasesPage />);
    await screen.findByRole("heading", { name: "数据库容量" });
    await waitFor(() => expect(screen.getAllByText("app_db").length).toBeGreaterThan(0));
    vi.mocked(fetchCapacityDatabaseSnapshot).mockClear();

    await chooseMultiOptions("数据库类型", ["MySQL"]);
    await chooseMultiOptions("实例", ["mysql-capacity"]);
    await chooseSelectOption("数据库", "app_db");
    await chooseSelectOption("周期", "月");
    fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

    await waitFor(() => {
      expect(fetchCapacityDatabaseSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({
          databaseName: "app_db",
          dbTypes: ["mysql"],
          instanceIds: [10],
          periodType: "monthly"
        })
      );
    });
  });

  it("keeps capacity filter options fixed and linked by selected database type", async () => {
    vi.mocked(fetchCapacityInstanceSnapshot).mockResolvedValueOnce({
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
            instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
          },
          {
            id: 2,
            instance_id: 20,
            period_type: "daily",
            period_start: "2026-06-10",
            period_end: "2026-06-10",
            total_size_mb: 1024,
            avg_size_mb: 1024,
            max_size_mb: 1024,
            min_size_mb: 1024,
            data_count: 1,
            database_count: 6,
            instance: { id: 20, name: "sqlserver-capacity", db_type: "sqlserver" }
          }
        ],
        total: 2,
        page: 1,
        pages: 1,
        limit: 20
      },
      charts: {
        trend: {
          items: [
            {
              id: 11,
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
              instance: { id: 10, name: "mysql-capacity", db_type: "mysql" }
            },
            {
              id: 12,
              instance_id: 20,
              period_type: "daily",
              period_start: "2026-06-10",
              period_end: "2026-06-10",
              total_size_mb: 1024,
              avg_size_mb: 1024,
              max_size_mb: 1024,
              min_size_mb: 1024,
              data_count: 1,
              database_count: 6,
              instance: { id: 20, name: "sqlserver-capacity", db_type: "sqlserver" }
            }
          ],
          total: 2,
          page: 1,
          pages: 1,
          limit: 200
        },
        change: { items: [], total: 0, page: 1, pages: 1, limit: 200 },
        percent: { items: [], total: 0, page: 1, pages: 1, limit: 200 }
      }
    });

    renderWithQueryClient(<CapacityInstancesPage />);
    await screen.findByRole("heading", { name: "实例容量" });
    await waitFor(() => expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0));

    fireEvent.click(screen.getByRole("button", { name: /数据库类型/ }));
    const dbTypeDialog = await screen.findByRole("dialog", { name: "选择数据库类型" });
    expect(within(dbTypeDialog).getByLabelText("选择 Oracle")).toBeInTheDocument();
    fireEvent.click(within(dbTypeDialog).getByLabelText("选择 MySQL"));
    fireEvent.click(within(dbTypeDialog).getByRole("button", { name: "完成" }));

    fireEvent.click(screen.getByRole("button", { name: /实例/ }));
    const instanceDialog = await screen.findByRole("dialog", { name: "选择实例" });
    expect(await within(instanceDialog).findByLabelText("选择 mysql-capacity")).toBeInTheDocument();
    expect(within(instanceDialog).queryByLabelText("选择 sqlserver-capacity")).not.toBeInTheDocument();
  });

  it("supports legacy multi-select capacity filters", async () => {
    renderWithQueryClient(<CapacityInstancesPage />);
    await screen.findByRole("heading", { name: "实例容量" });
    await waitFor(() => expect(screen.getAllByText("mysql-capacity").length).toBeGreaterThan(0));
    vi.mocked(fetchCapacityInstanceSnapshot).mockClear();

    await chooseMultiOptions("数据库类型", ["MySQL", "SQL Server"]);
    await chooseMultiOptions("实例", ["mysql-capacity", "sqlserver-capacity"]);
    fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

    await waitFor(() => {
      expect(fetchCapacityInstanceSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({
          dbTypes: ["mysql", "sqlserver"],
          instanceIds: [10, 20]
        })
      );
    });
  });
});
