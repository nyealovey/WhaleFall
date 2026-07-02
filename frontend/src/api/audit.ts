import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 20;

export type AuditPaginationQuery = {
  limit?: number;
  page?: number;
  search?: string;
};

export type HistoryLogsQuery = AuditPaginationQuery & {
  hours?: number;
  level?: string;
  module?: string;
};

export type AccountChangeLogsQuery = AuditPaginationQuery & {
  changeType?: string;
  dbType?: string;
  hours?: number;
  instanceId?: number;
};

export type FilterOption = { label: string; value: string };

export type PaginatedAuditList<TItem> = {
  items: TItem[];
  total: number;
  page: number;
  pages: number;
  limit: number;
};

export type HistoryLogItem = {
  id: number;
  timestamp: string;
  timestamp_display: string;
  level: string;
  level_label: string;
  module: string;
  module_label: string;
  message: string;
  message_label: string;
  traceback?: string | null;
  context?: Record<string, unknown>;
};

export type HistoryLogTopModule = {
  count: number;
  module: string;
  module_label: string;
};

export type HistoryLogStatistics = {
  total_logs: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count: number;
  critical_count: number;
  level_distribution: Record<string, number>;
  top_modules: HistoryLogTopModule[];
  error_rate: number;
};

export type HistoryLogsSnapshot = {
  list: PaginatedAuditList<HistoryLogItem>;
  statistics: HistoryLogStatistics;
};

export type HistoryLogDetail = {
  log: HistoryLogItem;
};

export type AccountChangeLogItem = {
  id: number;
  account_id?: number | null;
  instance_id: number;
  instance_name?: string | null;
  instance_host?: string | null;
  db_type: string;
  username: string;
  change_type: string;
  status: string;
  message?: string | null;
  change_time: string;
  session_id?: string | null;
  privilege_diff_count: number;
  other_diff_count: number;
};

export type AccountChangeLogStatistics = {
  total_changes: number;
  success_count: number;
  failed_count: number;
  affected_accounts: number;
};

export type AccountChangeLogsSnapshot = {
  list: PaginatedAuditList<AccountChangeLogItem>;
  statistics: AccountChangeLogStatistics;
};

export type AccountChangeLogDetailItem = AccountChangeLogItem & {
  instance_info?: unknown;
  privilege_diff?: unknown;
  other_diff?: unknown;
};

export type AccountChangeLogDetail = {
  log: AccountChangeLogDetailItem;
};

function queryPath(path: string, entries: Array<[string, string | number | undefined]>): string {
  const params = new URLSearchParams();
  entries.forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

function historyLogsPath(query: HistoryLogsQuery): string {
  return queryPath("/api/v1/logs", [
    ["page", query.page ?? 1], ["limit", query.limit ?? DEFAULT_LIST_LIMIT], ["search", query.search],
    ["level", query.level], ["module", query.module], ["hours", query.hours]
  ]);
}

function accountChangeLogsPath(query: AccountChangeLogsQuery): string {
  return queryPath("/api/v1/account-change-logs", [
    ["page", query.page ?? 1], ["limit", query.limit ?? DEFAULT_LIST_LIMIT], ["search", query.search],
    ["instance_id", query.instanceId], ["db_type", query.dbType], ["change_type", query.changeType], ["hours", query.hours]
  ]);
}

function statisticsPath(path: string, hours?: number): string {
  return queryPath(`${path}/statistics`, [["hours", hours]]);
}

export async function fetchHistoryLogsSnapshot(query: HistoryLogsQuery = {}, client: ApiReader = apiClient): Promise<HistoryLogsSnapshot> {
  const [list, statistics] = await Promise.all([
    client.get<PaginatedAuditList<HistoryLogItem>>(historyLogsPath(query)),
    client.get<HistoryLogStatistics>(statisticsPath("/api/v1/logs", query.hours ?? 24))
  ]);

  return {
    list,
    statistics
  };
}

export async function fetchHistoryLogDetail(logId: number, client: ApiReader = apiClient): Promise<HistoryLogDetail> {
  return client.get<HistoryLogDetail>(`/api/v1/logs/${encodeURIComponent(String(logId))}`);
}

export async function fetchAccountChangeLogsSnapshot(
  query: AccountChangeLogsQuery = {},
  client: ApiReader = apiClient
): Promise<AccountChangeLogsSnapshot> {
  const [list, statistics] = await Promise.all([
    client.get<PaginatedAuditList<AccountChangeLogItem>>(accountChangeLogsPath(query)),
    client.get<AccountChangeLogStatistics>(statisticsPath("/api/v1/account-change-logs", query.hours))
  ]);

  return {
    list,
    statistics
  };
}

export async function fetchHistoryLogModules(client: ApiReader = apiClient): Promise<FilterOption[]> {
  const response = await client.get<{ modules: string[]; module_options?: FilterOption[] }>("/api/v1/logs/modules");
  return response.module_options ?? response.modules.map((module) => ({ label: module, value: module }));
}

export async function fetchAccountChangeLogOptions(client: ApiReader = apiClient): Promise<FilterOption[]> {
  const response = await client.get<{ instances: FilterOption[] }>("/api/v1/instances/options");
  return response.instances;
}

export async function fetchAccountChangeLogDetail(
  logId: number,
  client: ApiReader = apiClient
): Promise<AccountChangeLogDetail> {
  return client.get<AccountChangeLogDetail>(`/api/v1/account-change-logs/${encodeURIComponent(String(logId))}`);
}
