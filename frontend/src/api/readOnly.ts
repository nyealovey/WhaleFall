import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;
const SYNC_SESSIONS_LIST_LIMIT = 100;

export type PaginatedReadOnlyList<TItem> = {
  items: TItem[];
  total: number;
  page: number;
  pages?: number;
  limit?: number;
  stats?: Record<string, number>;
};

export type ClusterItem = {
  id: number;
  name: string;
  domain_name?: string | null;
  description?: string | null;
  is_enabled?: boolean;
  instance_count?: number;
  availability_group_count?: number;
  contained_ag_count?: number;
  last_ag_sync_status?: string | null;
  replication_status?: string | null;
};

export type ClusterDetailRecord = Record<string, unknown> & {
  id?: number;
  name?: string | null;
  host?: string | null;
  role?: string | null;
};

export type SqlServerClusterDetail = {
  cluster: ClusterItem & Record<string, unknown>;
  instances: ClusterDetailRecord[];
  availability_groups: ClusterDetailRecord[];
};

export type MySqlClusterDetail = {
  cluster: ClusterItem & Record<string, unknown>;
  instances: ClusterDetailRecord[];
};

export type ClustersSnapshot = {
  sqlServer: PaginatedReadOnlyList<ClusterItem>;
  mySql: PaginatedReadOnlyList<ClusterItem>;
};

export type AccountClassificationItem = {
  id: number;
  code: string;
  display_name: string;
  description?: string | null;
  risk_level?: number;
  icon_name?: string | null;
  priority?: number;
  is_system?: boolean;
  rules_count?: number;
};

export type AccountClassificationRuleItem = {
  id: number;
  rule_name: string;
  classification_id?: number;
  classification_name?: string | null;
  db_type: string;
  operator?: string;
  rule_expression?: unknown;
  rule_group_id?: string | null;
  rule_version?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  superseded_at?: string | null;
  is_active?: boolean;
  matched_accounts_count?: number;
};

export type AccountClassificationRuleDetail = {
  rule: AccountClassificationRuleItem;
};

export type AccountClassificationPermissions = {
  permissions: Record<string, unknown>;
};

export type AccountClassificationsSnapshot = {
  classifications: AccountClassificationItem[];
  rulesByDbType: Record<string, AccountClassificationRuleItem[]>;
};

export type ClassificationTrendPoint = {
  period_start?: string;
  period_end?: string;
  value?: number;
  value_avg?: number;
  value_sum?: number;
};

export type ClassificationTrendSeries = {
  classification_id: number;
  classification_name: string;
  points: ClassificationTrendPoint[];
};

export type ClassificationStatisticsSnapshot = {
  stats: Record<string, Record<string, unknown>>;
  trends: {
    buckets: Array<Record<string, unknown>>;
    series: ClassificationTrendSeries[];
  };
};

export type SchedulerJobItem = {
  id: string;
  task_id?: string;
  name?: string;
  task_name?: string;
  description?: string;
  next_run_time?: string | null;
  last_run_time?: string | null;
  trigger_type?: string;
  trigger_args?: unknown;
  state?: string;
  is_builtin?: boolean;
  editable_fields?: string[];
  func?: string;
};

export type SchedulerSnapshot = {
  jobs: SchedulerJobItem[];
};

export type SyncSessionItem = {
  id: number;
  session_id: string;
  run_id?: string;
  sync_type: string;
  sync_category: string;
  task_key?: string;
  task_name?: string;
  task_category?: string;
  trigger_source?: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  total_instances?: number;
  successful_instances?: number;
  failed_instances?: number;
  progress_total?: number;
  progress_completed?: number;
  progress_failed?: number;
};

export type SyncInstanceRecordItem = {
  id: number;
  session_id: string;
  instance_id?: number;
  instance_name?: string | null;
  sync_category?: string;
  status?: string;
  started_at?: string | null;
  completed_at?: string | null;
  items_synced?: number;
  items_created?: number;
  items_updated?: number;
  items_deleted?: number;
  error_message?: string | null;
  sync_details?: unknown;
  created_at?: string | null;
};

export type SyncSessionDetailItem = SyncSessionItem & {
  progress_percentage?: number;
  instance_records: SyncInstanceRecordItem[];
};

export type SyncSessionDetail = {
  session: SyncSessionDetailItem;
};

export type SyncSessionErrorLogs = {
  session: SyncSessionItem;
  error_records: SyncInstanceRecordItem[];
  error_count: number;
};

export type UserItem = {
  id: number;
  username: string;
  email?: string | null;
  role: string;
  created_at?: string | null;
  created_at_display?: string | null;
  last_login?: string | null;
  is_active: boolean;
};

export type UsersStats = {
  total: number;
  active: number;
  inactive: number;
  admin: number;
  user: number;
};

export type UsersSnapshot = {
  list: PaginatedReadOnlyList<UserItem>;
  stats: UsersStats;
};

export type SettingsSnapshot = {
  alerts: {
    smtp_ready?: boolean;
    from_address?: string | null;
    from_name?: string | null;
    settings?: Record<string, unknown>;
  };
  riskRules: Array<Record<string, unknown>>;
  jumpserver: Record<string, unknown>;
  veeam: Record<string, unknown>;
  adDomains: {
    configs: Array<Record<string, unknown>>;
  };
};

export type CredentialItem = {
  id: number;
  name: string;
  credential_type?: string;
  db_type?: string | null;
  username?: string;
  description?: string | null;
  is_active?: boolean;
  instance_count?: number;
  created_at_display?: string | null;
};

export type TagItem = {
  id: number;
  name: string;
  display_name: string;
  category: string;
  is_active?: boolean;
  instance_count?: number;
};

export type TagsSnapshot = {
  list: PaginatedReadOnlyList<TagItem> & {
    stats: {
      total: number;
      active: number;
      inactive: number;
      category_count: number;
    };
  };
  categories: string[];
};

export type TaggableInstanceItem = {
  id: number;
  name?: string | null;
  instance_name?: string | null;
  db_type?: string | null;
  host?: string | null;
  ip_address?: string | null;
  tags?: unknown;
};

export type TagOptionItem = {
  id: number;
  name?: string | null;
  display_name?: string | null;
  category?: string | null;
  is_active?: boolean;
};

export type TagBulkOptions = {
  instances: TaggableInstanceItem[];
  tags: TagOptionItem[];
  categoryNames: string[];
};

export type PartitionItem = {
  name: string;
  table?: string;
  table_type?: string;
  display_name?: string;
  size?: string;
  record_count?: number;
  date?: string;
  status?: string;
};

export type PartitionsSnapshot = {
  status: {
    data: {
      status?: string;
      total_partitions?: number;
      total_size?: string;
      total_records?: number;
      missing_partitions?: string[];
    };
    timestamp?: string;
  };
  list: PaginatedReadOnlyList<PartitionItem>;
  coreMetrics: {
    labels: string[];
    datasets: Array<{ label?: string; data?: number[] }>;
    dataPointCount: number;
    timeRange: string;
    yAxisLabel: string;
    chartTitle: string;
    periodType: string;
  };
};

function pagePath(path: string, limit = DEFAULT_LIST_LIMIT): string {
  return `${path}?page=1&limit=${limit}`;
}

export async function fetchClustersSnapshot(client: ApiReader = apiClient): Promise<ClustersSnapshot> {
  const [sqlServer, mySql] = await Promise.all([
    client.get<PaginatedReadOnlyList<ClusterItem>>(pagePath("/api/v1/sqlserver-clusters")),
    client.get<PaginatedReadOnlyList<ClusterItem>>(pagePath("/api/v1/mysql-clusters"))
  ]);

  return { sqlServer, mySql };
}

export function fetchSqlServerClusterDetail(clusterId: number, client: ApiReader = apiClient): Promise<SqlServerClusterDetail> {
  return client.get<SqlServerClusterDetail>(`/api/v1/sqlserver-clusters/${clusterId}`);
}

export function fetchMySqlClusterDetail(clusterId: number, client: ApiReader = apiClient): Promise<MySqlClusterDetail> {
  return client.get<MySqlClusterDetail>(`/api/v1/mysql-clusters/${clusterId}`);
}

export async function fetchAccountClassificationsSnapshot(
  client: ApiReader = apiClient
): Promise<AccountClassificationsSnapshot> {
  const [classificationsResponse, rulesResponse] = await Promise.all([
    client.get<{ classifications: AccountClassificationItem[] }>("/api/v1/accounts/classifications"),
    client.get<{ rules_by_db_type: Record<string, AccountClassificationRuleItem[]> }>("/api/v1/accounts/classifications/rules")
  ]);

  return {
    classifications: classificationsResponse.classifications,
    rulesByDbType: rulesResponse.rules_by_db_type
  };
}

export function fetchAccountClassificationRuleDetail(
  ruleId: number,
  client: ApiReader = apiClient
): Promise<AccountClassificationRuleDetail> {
  return client.get<AccountClassificationRuleDetail>(`/api/v1/accounts/classifications/rules/${ruleId}`);
}

export function fetchAccountClassificationPermissions(
  dbType: string,
  client: ApiReader = apiClient
): Promise<AccountClassificationPermissions> {
  return client.get<AccountClassificationPermissions>(`/api/v1/accounts/classifications/permissions/${encodeURIComponent(dbType)}`);
}

export async function fetchClassificationStatisticsSnapshot(
  client: ApiReader = apiClient
): Promise<ClassificationStatisticsSnapshot> {
  const [stats, trends] = await Promise.all([
    client.get<Record<string, Record<string, unknown>>>("/api/v1/accounts/statistics/classifications"),
    client.get<ClassificationStatisticsSnapshot["trends"]>(
      "/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7"
    )
  ]);

  return { stats, trends };
}

export async function fetchSchedulerSnapshot(client: ApiReader = apiClient): Promise<SchedulerSnapshot> {
  const jobs = await client.get<SchedulerJobItem[]>("/api/v1/scheduler/jobs");
  return { jobs };
}

export async function fetchSyncSessionsSnapshot(
  client: ApiReader = apiClient
): Promise<PaginatedReadOnlyList<SyncSessionItem>> {
  return client.get<PaginatedReadOnlyList<SyncSessionItem>>(pagePath("/api/v1/sync-sessions", SYNC_SESSIONS_LIST_LIMIT));
}

export async function fetchSyncSessionDetail(
  sessionId: string,
  client: ApiReader = apiClient
): Promise<SyncSessionDetail> {
  return client.get<SyncSessionDetail>(`/api/v1/sync-sessions/${encodeURIComponent(sessionId)}`);
}

export async function fetchSyncSessionErrorLogs(
  sessionId: string,
  client: ApiReader = apiClient
): Promise<SyncSessionErrorLogs> {
  return client.get<SyncSessionErrorLogs>(`/api/v1/sync-sessions/${encodeURIComponent(sessionId)}/error-logs`);
}

export async function fetchUsersSnapshot(client: ApiReader = apiClient): Promise<UsersSnapshot> {
  const [list, stats] = await Promise.all([
    client.get<PaginatedReadOnlyList<UserItem>>(pagePath("/api/v1/users")),
    client.get<UsersStats>("/api/v1/users/stats")
  ]);

  return { list, stats };
}

function normalizeRiskRules(payload: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(payload)) {
    return payload.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object");
  }
  if (payload !== null && typeof payload === "object") {
    const rules = (payload as { rules?: unknown }).rules;
    if (Array.isArray(rules)) {
      return rules.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object");
    }
  }
  return [];
}

export async function fetchSettingsSnapshot(client: ApiReader = apiClient): Promise<SettingsSnapshot> {
  const [alerts, riskRules, jumpserver, veeam, adDomains] = await Promise.all([
    client.get<SettingsSnapshot["alerts"]>("/api/v1/alerts/email-settings"),
    client.get<unknown>("/api/v1/risk-center/rules"),
    client.get<SettingsSnapshot["jumpserver"]>("/api/v1/integrations/jumpserver/source"),
    client.get<SettingsSnapshot["veeam"]>("/api/v1/integrations/veeam/sources"),
    client.get<SettingsSnapshot["adDomains"]>("/api/v1/ad-domain-configs")
  ]);

  return { alerts, riskRules: normalizeRiskRules(riskRules), jumpserver, veeam, adDomains };
}

export async function fetchCredentialsSnapshot(
  client: ApiReader = apiClient
): Promise<PaginatedReadOnlyList<CredentialItem>> {
  return client.get<PaginatedReadOnlyList<CredentialItem>>(pagePath("/api/v1/credentials"));
}

export async function fetchTagsSnapshot(client: ApiReader = apiClient): Promise<TagsSnapshot> {
  const [list, categoriesResponse] = await Promise.all([
    client.get<TagsSnapshot["list"]>(pagePath("/api/v1/tags")),
    client.get<{ categories: string[] }>("/api/v1/tags/categories")
  ]);

  return {
    list,
    categories: categoriesResponse.categories
  };
}

export async function fetchTagBulkOptions(client: ApiReader = apiClient): Promise<TagBulkOptions> {
  const [instancesResponse, tagsResponse] = await Promise.all([
    client.get<{ instances: TaggableInstanceItem[] }>("/api/v1/tags/bulk/instances"),
    client.get<{ tags: TagOptionItem[]; category_names?: string[] }>("/api/v1/tags/bulk/tags")
  ]);

  return {
    instances: instancesResponse.instances,
    tags: tagsResponse.tags,
    categoryNames: tagsResponse.category_names ?? []
  };
}

export async function fetchPartitionsSnapshot(client: ApiReader = apiClient): Promise<PartitionsSnapshot> {
  const [status, list, coreMetrics] = await Promise.all([
    client.get<PartitionsSnapshot["status"]>("/api/v1/partitions/status"),
    client.get<PaginatedReadOnlyList<PartitionItem>>(pagePath("/api/v1/partitions")),
    client.get<PartitionsSnapshot["coreMetrics"]>("/api/v1/partitions/core-metrics?period_type=daily&days=7")
  ]);

  return { status, list, coreMetrics };
}
