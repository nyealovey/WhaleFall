import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;

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
  module: string;
  message: string;
  traceback?: string | null;
  context?: Record<string, unknown>;
};

export type HistoryLogStatistics = {
  total_logs: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count: number;
  critical_count: number;
  level_distribution: Record<string, number>;
  top_modules: Array<{ module: string; count: number }>;
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
  privilege_diff?: unknown;
  other_diff?: unknown;
};

export type AccountChangeLogDetail = {
  log: AccountChangeLogDetailItem;
};

function listPath(path: string): string {
  const params = new URLSearchParams({
    page: "1",
    limit: String(DEFAULT_LIST_LIMIT)
  });
  return `${path}?${params.toString()}`;
}

function statisticsPath(path: string): string {
  const params = new URLSearchParams({
    hours: "24"
  });
  return `${path}/statistics?${params.toString()}`;
}

export async function fetchHistoryLogsSnapshot(client: ApiReader = apiClient): Promise<HistoryLogsSnapshot> {
  const [list, statistics] = await Promise.all([
    client.get<PaginatedAuditList<HistoryLogItem>>(listPath("/api/v1/logs")),
    client.get<HistoryLogStatistics>(statisticsPath("/api/v1/logs"))
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
  client: ApiReader = apiClient
): Promise<AccountChangeLogsSnapshot> {
  const [list, statistics] = await Promise.all([
    client.get<PaginatedAuditList<AccountChangeLogItem>>(listPath("/api/v1/account-change-logs")),
    client.get<AccountChangeLogStatistics>(statisticsPath("/api/v1/account-change-logs"))
  ]);

  return {
    list,
    statistics
  };
}

export async function fetchAccountChangeLogDetail(
  logId: number,
  client: ApiReader = apiClient
): Promise<AccountChangeLogDetail> {
  return client.get<AccountChangeLogDetail>(`/api/v1/account-change-logs/${encodeURIComponent(String(logId))}`);
}
