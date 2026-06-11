import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;

export type CountRecord = Record<string, number | string | null | undefined>;

export type InstanceStatistics = {
  total_instances: number;
  current_instances: number;
  active_instances: number;
  normal_instances: number;
  disabled_instances: number;
  deleted_instances: number;
  inactive_instances: number;
  audit_enabled_instances: number;
  high_availability_instances: number;
  managed_instances: number;
  unmanaged_instances: number;
  backed_up_instances: number;
  backup_stale_instances: number;
  not_backed_up_instances: number;
  backup_status_stats: Array<{ backup_status: string; count: number }>;
  db_types_count: number;
  db_type_stats: Array<{ db_type: string; count: number }>;
  port_stats: Array<{ port: number; count: number }>;
  version_stats: Array<{ db_type: string; version: string; count: number }>;
};

export type AccountStatisticsSummary = {
  total_accounts: number;
  active_accounts: number;
  locked_accounts: number;
  normal_accounts: number;
  deleted_accounts: number;
  total_instances: number;
  physical_instances: number;
  ag_virtual_instances: number;
  active_instances: number;
  disabled_instances: number;
  normal_instances: number;
  deleted_instances: number;
  owner_type_stats: Record<string, unknown>;
  ad_status_stats: Record<string, unknown>;
};

export type AccountStatisticsRules = {
  rule_stats: Array<{
    rule_id: number;
    matched_accounts_count: number;
  }>;
};

export type AccountStatisticsSnapshot = {
  summary: AccountStatisticsSummary;
  dbTypes: Record<string, unknown>;
  classifications: Record<string, unknown>;
  rules: AccountStatisticsRules;
};

export type DatabaseStatistics = {
  total_databases: number;
  active_databases: number;
  inactive_databases: number;
  deleted_databases: number;
  total_instances: number;
  total_size_mb: number;
  avg_size_mb: number;
  max_size_mb: number;
  db_type_stats: Array<{ db_type: string; count: number }>;
  instance_stats: Array<{ instance_id: number; instance_name: string; db_type: string; count: number }>;
  sync_status_stats: Array<{ value: string; label: string; variant: string; count: number }>;
  capacity_rankings: Array<{
    instance_id: number;
    instance_name: string;
    db_type: string;
    database_name: string;
    size_mb: number;
    size_label: string;
    collected_at?: string | null;
  }>;
};

export type DatabaseStatisticsResponse = {
  stats: DatabaseStatistics;
};

export async function fetchInstanceStatistics(client: ApiReader = apiClient): Promise<InstanceStatistics> {
  return client.get<InstanceStatistics>("/api/v1/instances/statistics");
}

export async function fetchAccountStatisticsSnapshot(
  client: ApiReader = apiClient
): Promise<AccountStatisticsSnapshot> {
  const [summary, dbTypes, classifications, rules] = await Promise.all([
    client.get<AccountStatisticsSummary>("/api/v1/accounts/statistics/summary"),
    client.get<Record<string, unknown>>("/api/v1/accounts/statistics/db-types"),
    client.get<Record<string, unknown>>("/api/v1/accounts/statistics/classifications"),
    client.get<AccountStatisticsRules>("/api/v1/accounts/statistics/rules")
  ]);

  return {
    summary,
    dbTypes,
    classifications,
    rules
  };
}

export async function fetchDatabaseStatistics(client: ApiReader = apiClient): Promise<DatabaseStatisticsResponse> {
  return client.get<DatabaseStatisticsResponse>("/api/v1/databases/statistics");
}
