import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;

export type CapacityDateRange = {
  startDate: string;
  endDate: string;
};

export type CapacityFilters = {
  databaseName?: string;
  dbTypes?: string[];
  instanceIds?: number[];
  periodType?: string;
  range?: CapacityDateRange;
};

export type CapacityList<TItem> = {
  items: TItem[];
  total: number;
  page: number;
  pages: number;
  limit: number;
  has_prev?: boolean;
  has_next?: boolean;
};

export type CapacityInstanceRef = {
  id: number;
  name: string;
  db_type: string;
};

export type CapacityInstanceOption = {
  asset_url?: string | null;
  db_type: string;
  display_name?: string | null;
  id: number;
  name: string;
};

export type CapacityDatabaseOption = {
  database_name: string;
  deleted_at?: string | null;
  first_seen_date?: string | null;
  id: number;
  is_active?: boolean | null;
  last_seen_date?: string | null;
};

export type CapacityInstanceItem = {
  id: number;
  instance_id: number;
  period_type: string;
  period_start: string;
  period_end: string;
  total_size_mb: number;
  avg_size_mb: number;
  max_size_mb: number;
  min_size_mb: number;
  data_count: number;
  database_count: number;
  avg_database_count?: number | null;
  max_database_count?: number | null;
  min_database_count?: number | null;
  total_size_change_mb?: number | null;
  total_size_change_percent?: number | null;
  database_count_change?: number | null;
  database_count_change_percent?: number | null;
  growth_rate?: number | null;
  trend_direction?: string | null;
  instance: CapacityInstanceRef;
};

export type CapacityInstanceSummary = {
  total_instances: number;
  total_size_mb: number;
  avg_size_mb: number;
  max_size_mb: number;
  period_type: string;
  source: string;
};

export type CapacityDatabaseItem = {
  id: number;
  instance_id: number;
  database_name: string;
  period_type: string;
  period_start: string;
  period_end: string;
  avg_size_mb: number;
  max_size_mb: number;
  min_size_mb: number;
  data_count: number;
  avg_data_size_mb?: number | null;
  max_data_size_mb?: number | null;
  min_data_size_mb?: number | null;
  avg_log_size_mb?: number | null;
  max_log_size_mb?: number | null;
  min_log_size_mb?: number | null;
  size_change_mb?: number | null;
  size_change_percent?: number | null;
  data_size_change_mb?: number | null;
  data_size_change_percent?: number | null;
  log_size_change_mb?: number | null;
  log_size_change_percent?: number | null;
  growth_rate?: number | null;
  instance: CapacityInstanceRef;
};

export type CapacityDatabaseSummary = {
  total_databases: number;
  total_instances: number;
  total_size_mb: number;
  avg_size_mb: number;
  max_size_mb: number;
  growth_rate: number;
};

type SummaryEnvelope<TSummary> = {
  summary: TSummary;
};

export type CapacityInstanceSnapshot = {
  list: CapacityList<CapacityInstanceItem>;
  summary: CapacityInstanceSummary;
  charts: {
    trend: CapacityList<CapacityInstanceItem>;
    change: CapacityList<CapacityInstanceItem>;
    percent: CapacityList<CapacityInstanceItem>;
  };
};

export type CapacityDatabaseSnapshot = {
  list: CapacityList<CapacityDatabaseItem>;
  summary: CapacityDatabaseSummary;
  charts: {
    trend: CapacityList<CapacityDatabaseItem>;
    change: CapacityList<CapacityDatabaseItem>;
    percent: CapacityList<CapacityDatabaseItem>;
  };
};

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function getDefaultCapacityRange(): CapacityDateRange {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - 30);
  return {
    startDate: formatDate(start),
    endDate: formatDate(end)
  };
}

function appendCapacityFilters(params: URLSearchParams, filters: CapacityFilters): void {
  filters.instanceIds?.forEach((instanceId) => {
    params.append("instance_id", String(instanceId));
  });
  filters.dbTypes?.forEach((dbType) => {
    if (dbType) {
      params.append("db_type", dbType);
    }
  });
  if (filters.databaseName) {
    params.set("database_name", filters.databaseName);
  }
}

function listPath(basePath: string, filters: CapacityFilters, options?: { getAll?: boolean }): string {
  const range = filters.range ?? getDefaultCapacityRange();
  const params = new URLSearchParams();
  params.set("period_type", filters.periodType || "daily");
  params.set("page", "1");
  params.set("limit", String(DEFAULT_LIST_LIMIT));
  params.set("start_date", range.startDate);
  params.set("end_date", range.endDate);
  appendCapacityFilters(params, filters);
  if (options?.getAll) {
    params.set("get_all", "true");
  }
  return `${basePath}?${params.toString()}`;
}

function summaryPath(basePath: string, filters: CapacityFilters): string {
  const range = filters.range ?? getDefaultCapacityRange();
  const params = new URLSearchParams();
  params.set("period_type", filters.periodType || "daily");
  params.set("start_date", range.startDate);
  params.set("end_date", range.endDate);
  appendCapacityFilters(params, filters);
  return `${basePath}/summary?${params.toString()}`;
}

export async function fetchCapacityInstanceSnapshot(
  filters: CapacityFilters = {},
  client: ApiReader = apiClient
): Promise<CapacityInstanceSnapshot> {
  const [list, summaryEnvelope, trend, change, percent] = await Promise.all([
    client.get<CapacityList<CapacityInstanceItem>>(listPath("/api/v1/capacity/instances", filters)),
    client.get<SummaryEnvelope<CapacityInstanceSummary>>(summaryPath("/api/v1/capacity/instances", filters)),
    client.get<CapacityList<CapacityInstanceItem>>(listPath("/api/v1/capacity/instances", filters, { getAll: true })),
    client.get<CapacityList<CapacityInstanceItem>>(listPath("/api/v1/capacity/instances", filters, { getAll: true })),
    client.get<CapacityList<CapacityInstanceItem>>(listPath("/api/v1/capacity/instances", filters, { getAll: true }))
  ]);

  return {
    list,
    summary: summaryEnvelope.summary,
    charts: { trend, change, percent }
  };
}

export async function fetchCapacityDatabaseSnapshot(
  filters: CapacityFilters = {},
  client: ApiReader = apiClient
): Promise<CapacityDatabaseSnapshot> {
  const [list, summaryEnvelope, trend, change, percent] = await Promise.all([
    client.get<CapacityList<CapacityDatabaseItem>>(listPath("/api/v1/capacity/databases", filters)),
    client.get<SummaryEnvelope<CapacityDatabaseSummary>>(summaryPath("/api/v1/capacity/databases", filters)),
    client.get<CapacityList<CapacityDatabaseItem>>(listPath("/api/v1/capacity/databases", filters, { getAll: true })),
    client.get<CapacityList<CapacityDatabaseItem>>(listPath("/api/v1/capacity/databases", filters, { getAll: true })),
    client.get<CapacityList<CapacityDatabaseItem>>(listPath("/api/v1/capacity/databases", filters, { getAll: true }))
  ]);

  return {
    list,
    summary: summaryEnvelope.summary,
    charts: { trend, change, percent }
  };
}

export async function fetchCapacityInstanceOptions(
  dbTypes: string[] | string,
  client: ApiReader = apiClient
): Promise<CapacityInstanceOption[]> {
  const selectedDbTypes = (Array.isArray(dbTypes) ? dbTypes : [dbTypes]).filter(Boolean);
  if (selectedDbTypes.length === 0) {
    return [];
  }
  const responses = await Promise.all(
    selectedDbTypes.map((dbType) =>
      client.get<{ instances?: CapacityInstanceOption[] }>(`/api/v1/instances/options?db_type=${encodeURIComponent(dbType)}`)
    )
  );
  const optionsById = new Map<number, CapacityInstanceOption>();
  for (const response of responses) {
    for (const item of response.instances ?? []) {
      optionsById.set(item.id, item);
    }
  }
  return [...optionsById.values()];
}

export async function fetchCapacityDatabaseOptions(
  instanceId: number | string,
  client: ApiReader = apiClient
): Promise<CapacityDatabaseOption[]> {
  const resolvedInstanceId = String(instanceId || "").trim();
  if (!resolvedInstanceId) {
    return [];
  }
  const response = await client.get<{ databases?: CapacityDatabaseOption[] }>(
    `/api/v1/databases/options?instance_id=${encodeURIComponent(resolvedInstanceId)}&page=1&limit=200`
  );
  return response.databases ?? [];
}
