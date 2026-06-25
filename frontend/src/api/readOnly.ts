import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;

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
  last_status_sync_status?: string | null;
  last_status_sync_at?: string | null;
  last_ag_sync_status?: string | null;
  last_ag_sync_at?: string | null;
  last_topology_sync_status?: string | null;
  last_topology_sync_at?: string | null;
  abnormal_replica_count?: number;
  ag_database_sync_abnormal_count?: number;
  replication_status?: string | null;
};

export type ClusterDetailRecord = Record<string, unknown> & {
  id?: number;
  name?: string | null;
  host?: string | null;
  role?: string | null;
};

export type ClusterInstanceOption = {
  id: number;
  name: string;
  host?: string | null;
  db_type?: string | null;
};

export type AccountScopeOption = {
  value: string;
  label: string;
  db_type?: string | null;
  owner_type?: string | null;
  owner_id?: number | null;
  name?: string | null;
  host?: string | null;
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

export type SqlServerAvailabilityGroupDashboard = {
  summary?: ClusterDetailRecord;
  availability_group?: ClusterDetailRecord;
  replicas: ClusterDetailRecord[];
  databases?: ClusterDetailRecord[];
  database_groups?: Array<ClusterDetailRecord & { databases?: ClusterDetailRecord[] }>;
  kpis?: Record<string, unknown>;
};

export type ClustersSnapshot = {
  sqlServer: PaginatedReadOnlyList<ClusterItem>;
  mySql: PaginatedReadOnlyList<ClusterItem>;
};

export type ServerListQuery = {
  page?: number;
  limit?: number;
  search?: string;
};

export type ClusterListQuery = ServerListQuery & { status?: string };
export type UsersListQuery = ServerListQuery & { role?: string; status?: string };
export type CredentialsListQuery = ServerListQuery & { credentialType?: string; dbType?: string; status?: string };
export type TagsListQuery = ServerListQuery & { category?: string; status?: string };

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
  selectedClassificationTrend?: ClassificationTrendPoint[];
  selectedRuleTrend?: ClassificationTrendPoint[];
  rulesOverview?: ClassificationRulesOverview;
  ruleContributions?: ClassificationRuleContributions;
};

export type ClassificationStatisticsFilters = {
  accountScope?: string;
  classificationId?: number | string;
  dbType?: string;
  periodType?: string;
  periods?: number;
  ruleId?: number | string;
  ruleStatus?: string;
};

export type ClassificationRuleOverviewItem = {
  rule_id: number;
  rule_name: string;
  db_type?: string | null;
  rule_version?: number | null;
  is_active?: boolean;
  latest_value_avg?: number;
  latest_value_sum?: number;
  latest_coverage_days?: number;
  latest_expected_days?: number;
  window_value_sum?: number;
};

export type ClassificationRulesOverview = {
  window_start?: string;
  window_end?: string;
  latest_period_start?: string;
  latest_period_end?: string;
  latest_coverage_days?: number;
  latest_expected_days?: number;
  rules: ClassificationRuleOverviewItem[];
};

export type ClassificationRuleContributionItem = {
  rule_id: number;
  rule_name: string;
  db_type?: string | null;
  rule_version?: number | null;
  is_active?: boolean | null;
  value_avg?: number;
  value_sum?: number;
  coverage_days?: number;
  expected_days?: number;
};

export type ClassificationRuleContributions = {
  period_start?: string;
  period_end?: string;
  coverage_days?: number;
  expected_days?: number;
  contributions: ClassificationRuleContributionItem[];
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

export type SchedulerJobDetail = SchedulerJobItem & {
  trigger?: string;
  args?: unknown;
  kwargs?: unknown;
  misfire_grace_time?: number | null;
  max_instances?: number | null;
  coalesce?: boolean | null;
};

export type TaskRunItem = {
  id: number;
  run_id: string;
  task_key: string;
  task_name: string;
  task_category: string;
  trigger_source: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  progress_total: number;
  progress_completed: number;
  progress_failed: number;
  error_message?: string | null;
};

export type TaskRunChildItem = {
  id: number;
  run_id: string;
  item_type: string;
  item_key: string;
  item_name?: string | null;
  instance_id?: number;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  metrics_json?: Record<string, unknown> | null;
  details_json?: Record<string, unknown> | null;
};

export type TaskRunDetail = {
  run: TaskRunItem;
  items: TaskRunChildItem[];
};

export type TaskRunErrorLogs = {
  run: TaskRunItem;
  items: TaskRunChildItem[];
  error_count: number;
};

export type TaskRunsQuery = {
  limit?: number;
  page?: number;
  status?: string;
  taskCategory?: string;
  taskKey?: string;
  triggerSource?: string;
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
    credentials?: Array<Record<string, unknown>>;
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
  size_bytes?: number;
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
      partitions?: PartitionItem[];
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

export type PartitionMetricsFilters = {
  days?: number;
  periodType?: string;
  page?: number;
  limit?: number;
  search?: string;
  tableType?: string;
  status?: string;
};

function pagePath(path: string, limit = DEFAULT_LIST_LIMIT): string {
  return `${path}?page=1&limit=${limit}`;
}

function queryPath(path: string, entries: Array<[string, string | number | undefined | null]>): string {
  const params = new URLSearchParams();
  entries.forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export async function fetchClustersSnapshot(
  query: { sqlServer?: ClusterListQuery; mySql?: ClusterListQuery } = {},
  client: ApiReader = apiClient
): Promise<ClustersSnapshot> {
  const sqlServerQuery = query.sqlServer ?? {};
  const mySqlQuery = query.mySql ?? {};
  const [sqlServer, mySql] = await Promise.all([
    client.get<PaginatedReadOnlyList<ClusterItem>>(queryPath("/api/v1/sqlserver-clusters", [
      ["page", sqlServerQuery.page ?? 1], ["limit", sqlServerQuery.limit ?? 20], ["search", sqlServerQuery.search], ["status", sqlServerQuery.status]
    ])),
    client.get<PaginatedReadOnlyList<ClusterItem>>(queryPath("/api/v1/mysql-clusters", [
      ["page", mySqlQuery.page ?? 1], ["limit", mySqlQuery.limit ?? 20], ["search", mySqlQuery.search], ["status", mySqlQuery.status]
    ]))
  ]);

  return { sqlServer, mySql };
}

export async function fetchClusterInstanceOptions(dbType: "sqlserver" | "mysql", client: ApiReader = apiClient): Promise<ClusterInstanceOption[]> {
  const response = await client.get<PaginatedReadOnlyList<ClusterInstanceOption>>(`${pagePath("/api/v1/instances")}&db_type=${dbType}`);
  return response.items;
}

export function fetchSqlServerClusterDetail(clusterId: number, client: ApiReader = apiClient): Promise<SqlServerClusterDetail> {
  return client.get<SqlServerClusterDetail>(`/api/v1/sqlserver-clusters/${clusterId}`);
}

export function fetchMySqlClusterDetail(clusterId: number, client: ApiReader = apiClient): Promise<MySqlClusterDetail> {
  return client.get<MySqlClusterDetail>(`/api/v1/mysql-clusters/${clusterId}`);
}

export function fetchSqlServerAvailabilityGroupDashboard(
  clusterId: number,
  availabilityGroupId: number,
  client: ApiReader = apiClient
): Promise<SqlServerAvailabilityGroupDashboard> {
  return client.get<SqlServerAvailabilityGroupDashboard>(
    `/api/v1/sqlserver-clusters/${clusterId}/availability-groups/${availabilityGroupId}/dashboard`
  );
}

export async function fetchAccountClassificationsSnapshot(
  client: ApiReader = apiClient
): Promise<AccountClassificationsSnapshot> {
  const [classificationsResponse, rulesResponse] = await Promise.all([
    client.get<{ classifications: AccountClassificationItem[] }>("/api/v1/accounts/classifications"),
    client.get<{ rules_by_db_type: Record<string, AccountClassificationRuleItem[]> }>("/api/v1/accounts/classifications/rules")
  ]);

  const rules = Object.values(rulesResponse.rules_by_db_type).flat();
  const ruleIds = rules.map((rule) => rule.id);
  const statisticsResponse = ruleIds.length > 0
    ? await client.get<{ rule_stats: Array<{ rule_id: number; matched_accounts_count: number }> }>(
        `/api/v1/accounts/statistics/rules?rule_ids=${ruleIds.join(",")}`
      )
    : { rule_stats: [] };
  const counts = new Map(statisticsResponse.rule_stats.map((item) => [item.rule_id, item.matched_accounts_count]));
  const rulesByDbType = Object.fromEntries(
    Object.entries(rulesResponse.rules_by_db_type).map(([dbType, items]) => [
      dbType,
      items.map((item) => ({ ...item, matched_accounts_count: counts.get(item.id) ?? 0 }))
    ])
  );

  return {
    classifications: classificationsResponse.classifications,
    rulesByDbType
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

export async function fetchAccountScopeOptions(dbType: string, client: ApiReader = apiClient): Promise<AccountScopeOption[]> {
  const response = await client.get<{ account_scopes?: AccountScopeOption[] }>(
    `/api/v1/instances/account-scope-options?db_type=${encodeURIComponent(dbType)}`
  );
  return response.account_scopes ?? [];
}

export async function fetchClassificationStatisticsSnapshot(
  filters: ClassificationStatisticsFilters = {},
  client: ApiReader = apiClient
): Promise<ClassificationStatisticsSnapshot> {
  const periodType = filters.periodType || "daily";
  const periods = filters.periods ?? 7;
  const classificationId = filters.classificationId || undefined;
  const ruleId = filters.ruleId || undefined;
  const commonTrendEntries: Array<[string, string | number | undefined | null]> = [
    ["period_type", periodType],
    ["periods", periods],
    ["db_type", filters.dbType],
    ["account_scope", filters.accountScope]
  ];

  const statsRequest = client.get<Record<string, Record<string, unknown>>>("/api/v1/accounts/statistics/classifications");
  const trendsRequest = client.get<ClassificationStatisticsSnapshot["trends"]>(
    queryPath("/api/v1/accounts/statistics/classifications/trends", commonTrendEntries)
  );
  const selectedClassificationTrendRequest = classificationId
    ? client.get<{ trend: ClassificationTrendPoint[] }>(
        queryPath("/api/v1/accounts/statistics/classifications/trend", [
          ["classification_id", classificationId],
          ...commonTrendEntries
        ])
      )
    : Promise.resolve(undefined);
  const rulesOverviewRequest = classificationId
    ? client.get<ClassificationRulesOverview>(
        queryPath("/api/v1/accounts/statistics/rules/overview", [
          ["classification_id", classificationId],
          ...commonTrendEntries,
          ["status", filters.ruleStatus || "active"]
        ])
      )
    : Promise.resolve(undefined);
  const ruleContributionsRequest = classificationId
    ? client.get<ClassificationRuleContributions>(
        queryPath("/api/v1/accounts/statistics/rules/contributions", [
          ["classification_id", classificationId],
          ["period_type", periodType],
          ["db_type", filters.dbType],
          ["account_scope", filters.accountScope],
          ["limit", 10]
        ])
      )
    : Promise.resolve(undefined);
  const selectedRuleTrendRequest = ruleId
    ? client.get<{ trend: ClassificationTrendPoint[] }>(
        queryPath("/api/v1/accounts/statistics/rules/trend", [["rule_id", ruleId], ...commonTrendEntries])
      )
    : Promise.resolve(undefined);

  const [stats, trends, selectedClassificationTrend, rulesOverview, ruleContributions, selectedRuleTrend] =
    await Promise.all([
      statsRequest,
      trendsRequest,
      selectedClassificationTrendRequest,
      rulesOverviewRequest,
      ruleContributionsRequest,
      selectedRuleTrendRequest
    ]);

  return {
    stats,
    trends,
    selectedClassificationTrend: selectedClassificationTrend?.trend,
    rulesOverview,
    ruleContributions,
    selectedRuleTrend: selectedRuleTrend?.trend
  };
}

export async function fetchSchedulerSnapshot(client: ApiReader = apiClient): Promise<SchedulerSnapshot> {
  const jobs = await client.get<SchedulerJobItem[]>("/api/v1/scheduler/jobs");
  return { jobs };
}

export function fetchSchedulerJobDetail(jobId: string, client: ApiReader = apiClient): Promise<SchedulerJobDetail> {
  return client.get<SchedulerJobDetail>(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}`);
}

export async function fetchTaskRunsSnapshot(
  query: TaskRunsQuery = {},
  client: ApiReader = apiClient
): Promise<PaginatedReadOnlyList<TaskRunItem>> {
  return client.get<PaginatedReadOnlyList<TaskRunItem>>(queryPath("/api/v1/task-runs", [
    ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["task_key", query.taskKey],
    ["task_category", query.taskCategory], ["trigger_source", query.triggerSource], ["status", query.status],
    ["sort", "started_at"], ["order", "desc"]
  ]));
}

export async function fetchTaskRunDetail(
  runId: string,
  client: ApiReader = apiClient
): Promise<TaskRunDetail> {
  return client.get<TaskRunDetail>(`/api/v1/task-runs/${encodeURIComponent(runId)}`);
}

export async function fetchTaskRunErrorLogs(
  runId: string,
  client: ApiReader = apiClient
): Promise<TaskRunErrorLogs> {
  return client.get<TaskRunErrorLogs>(`/api/v1/task-runs/${encodeURIComponent(runId)}/error-logs`);
}

export async function fetchUsersSnapshot(query: UsersListQuery = {}, client: ApiReader = apiClient): Promise<UsersSnapshot> {
  const [list, stats] = await Promise.all([
    client.get<PaginatedReadOnlyList<UserItem>>(queryPath("/api/v1/users", [
      ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search], ["role", query.role], ["status", query.status]
    ])),
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
  const [alerts, riskRules, jumpserver, veeam, adDomains, adCredentials] = await Promise.all([
    client.get<SettingsSnapshot["alerts"]>("/api/v1/alerts/email-settings"),
    client.get<unknown>("/api/v1/risk-center/rules"),
    client.get<SettingsSnapshot["jumpserver"]>("/api/v1/integrations/jumpserver/source"),
    client.get<SettingsSnapshot["veeam"]>("/api/v1/integrations/veeam/sources"),
    client.get<SettingsSnapshot["adDomains"]>("/api/v1/ad-domain-configs"),
    client.get<PaginatedReadOnlyList<CredentialItem>>("/api/v1/credentials?page=1&limit=200&credential_type=ldap&status=active")
  ]);

  return { alerts, riskRules: normalizeRiskRules(riskRules), jumpserver, veeam, adDomains: { ...adDomains, credentials: adCredentials.items } };
}

export async function fetchCredentialsSnapshot(
  query: CredentialsListQuery = {},
  client: ApiReader = apiClient
): Promise<PaginatedReadOnlyList<CredentialItem>> {
  return client.get<PaginatedReadOnlyList<CredentialItem>>(queryPath("/api/v1/credentials", [
    ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search],
    ["credential_type", query.credentialType], ["db_type", query.dbType], ["status", query.status]
  ]));
}

export async function fetchTagsSnapshot(query: TagsListQuery = {}, client: ApiReader = apiClient): Promise<TagsSnapshot> {
  const [list, categoriesResponse] = await Promise.all([
    client.get<TagsSnapshot["list"]>(queryPath("/api/v1/tags", [
      ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search],
      ["category", query.category], ["status", query.status]
    ])),
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

export async function fetchPartitionsSnapshot(
  filters: PartitionMetricsFilters = {},
  client: ApiReader = apiClient
): Promise<PartitionsSnapshot> {
  const periodType = filters.periodType || "daily";
  const days = filters.days ?? 7;
  const [status, list, coreMetrics] = await Promise.all([
    client.get<PartitionsSnapshot["status"]>("/api/v1/partitions/status"),
    client.get<PaginatedReadOnlyList<PartitionItem>>(queryPath("/api/v1/partitions", [
      ["page", filters.page ?? 1], ["limit", filters.limit ?? 20], ["search", filters.search],
      ["table_type", filters.tableType], ["status", filters.status]
    ])),
    client.get<PartitionsSnapshot["coreMetrics"]>(
      `/api/v1/partitions/core-metrics?period_type=${encodeURIComponent(periodType)}&days=${days}`
    )
  ]);

  return { status, list, coreMetrics };
}
