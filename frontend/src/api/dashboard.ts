import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;

export type DashboardCount = {
  total: number;
  active: number;
  inactive?: number;
  deleted?: number;
  physical?: number;
  ag_virtual?: number;
};

export type DashboardAccounts = DashboardCount & {
  normal: number;
  locked: number;
  instance?: Record<string, number>;
  sqlserver_ag?: Record<string, number>;
  ad_status?: Record<string, unknown>;
};

export type DashboardClassificationItem = {
  code: string;
  display_name: string;
  color?: string;
  priority?: number;
  count: number;
};

export type DashboardOverview = {
  users: DashboardCount;
  instances: DashboardCount;
  accounts: DashboardAccounts;
  classified_accounts: {
    total: number;
    auto: number;
    classifications: DashboardClassificationItem[];
  };
  capacity: {
    total_gb: number;
    usage_percent: number;
  };
  databases: {
    total: number;
    active: number;
    inactive: number;
    deleted: number;
  };
};

export type DashboardStatus = {
  system: {
    cpu: number;
    memory: {
      used: number;
      total: number;
      percent: number;
    };
    disk: {
      used: number;
      total: number;
      percent: number;
    };
  };
  services: {
    database: string;
    redis: string;
  };
  uptime: string;
};

export type DashboardCharts = {
  log_trend?: Array<{ date: string; error_count: number; warning_count: number }>;
  log_levels?: Array<{ level: string; count: number }>;
  task_status?: Array<{ status: string; count: number }>;
  sync_trend?: Array<{ date: string; count: number }>;
};

export type DashboardSnapshot = {
  overview: DashboardOverview;
  status: DashboardStatus;
  charts: DashboardCharts;
  activities: unknown[];
};

export async function fetchDashboardSnapshot(client: ApiReader = apiClient): Promise<DashboardSnapshot> {
  const [overview, status, charts, activities] = await Promise.all([
    client.get<DashboardOverview>("/api/v1/dashboard/overview"),
    client.get<DashboardStatus>("/api/v1/dashboard/status"),
    client.get<DashboardCharts>("/api/v1/dashboard/charts?type=all"),
    client.get<unknown[]>("/api/v1/dashboard/activities")
  ]);

  return {
    overview,
    status,
    charts,
    activities
  };
}
