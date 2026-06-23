import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;

export type PaginatedQuery = {
  page?: number;
  limit?: number;
  search?: string;
};

export type InstanceListQuery = PaginatedQuery & {
  dbType?: string;
  status?: string;
  auditStatus?: string;
  managedStatus?: string;
  backupStatus?: string;
  tags?: string[];
  includeDeleted?: boolean;
};

export type DatabaseLedgerQuery = PaginatedQuery & {
  dbType?: string;
  instanceId?: number;
  tags?: string[];
};

export type AccountLedgerQuery = PaginatedQuery & {
  instanceId?: number;
  tags?: string[];
  classification?: string;
  dbType?: string;
  adStatus?: string;
};

type TagItem = {
  name: string;
  display_name: string;
  color?: string;
};

export type AccountClassificationOption = {
  code: string;
  display_name: string;
};

export type PaginatedList<TItem> = {
  items: TItem[];
  total: number;
  page: number;
  pages?: number;
  limit: number;
};

export type InstanceListItem = {
  id: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  description?: string | null;
  is_active: boolean;
  deleted_at?: string | null;
  status: string;
  audit_status: string;
  backup_status: string;
  backup_last_time?: string | null;
  main_version?: string | null;
  active_db_count: number;
  active_account_count: number;
  last_sync_time?: string | null;
  is_jumpserver_managed: boolean;
  tags: TagItem[];
};

export type CredentialOptionItem = {
  id: number;
  name: string;
  credential_type?: string | null;
  db_type?: string | null;
  is_active?: boolean | null;
};

export type InstanceDetailResponse = {
  instance: InstanceListItem & Record<string, unknown>;
};

export type InstanceConnectionStatus = {
  instance_id: number;
  instance_name: string;
  db_type: string;
  host: string;
  port: number;
  last_connected?: string | null;
  status: string;
  is_active: boolean;
};

export type InstanceAuditInfo = {
  instance_id: number;
  instance_name: string;
  db_type: string;
  config_key?: string;
  supported: boolean;
  available: boolean;
  last_sync_time?: string | null;
  snapshot?: Record<string, unknown>;
  facts?: Record<string, unknown>;
  message?: string | null;
};

export type InstanceBackupRestorePoint = {
  id?: string | null;
  name?: string | null;
  type?: string | null;
  backup_id?: string | null;
  object_id?: string | null;
  restore_point_ids?: string[];
  data_size_bytes?: number | null;
  backup_size_bytes?: number | null;
  compress_ratio?: number | null;
  creation_time?: string | null;
};

export type InstanceBackupInfo = {
  instance_id: number;
  instance_name: string;
  backup_status: string;
  backup_last_time?: string | null;
  matched_machine_name?: string | null;
  match_candidates: string[];
  source_binding_id?: number | null;
  source_name?: string | null;
  source_server_host?: string | null;
  backup_id?: string | null;
  backup_file_id?: string | null;
  job_name?: string | null;
  restore_point_name?: string | null;
  source_record_id?: string | null;
  restore_point_size_bytes?: number | null;
  backup_chain_size_bytes?: number | null;
  restore_point_count?: number | null;
  backup_metrics_coverage?: {
    expected_restore_point_count: number;
    enriched_restore_point_count: number;
    missing_restore_point_count: number;
    partial: boolean;
  };
  restore_point_times?: string[];
  restore_points?: InstanceBackupRestorePoint[];
  last_sync_time?: string | null;
  message?: string | null;
};

export type DatabaseLedgerItem = {
  id: number;
  database_name: string;
  instance: {
    id: number;
    name: string;
    host: string;
    db_type: string;
  };
  db_type: string;
  capacity: {
    size_mb: number;
    size_bytes?: number;
    label: string;
    collected_at?: string | null;
  };
  sync_status: {
    value: string;
    label: string;
    variant: string;
  };
  tags: TagItem[];
};

export type DatabaseTableSizeItem = {
  schema_name?: string | null;
  table_name: string;
  size_mb?: number | string | null;
  data_size_mb?: number | string | null;
  index_size_mb?: number | string | null;
  row_count?: number | string | null;
  collected_at?: string | null;
};

export type DatabaseTableSizesResponse = {
  total: number;
  page: number;
  pages?: number;
  limit: number;
  collected_at?: string | null;
  tables: DatabaseTableSizeItem[];
};

export type AccountLedgerItem = {
  id: number;
  username: string;
  instance_name: string;
  instance_host: string;
  db_type: string;
  is_locked: boolean;
  is_superuser: boolean;
  is_active: boolean;
  is_deleted: boolean;
  ad_status?: string | null;
  ad_domain?: string | null;
  last_change_time?: string | null;
  availability_reasons: string[];
  tags: TagItem[];
  classifications: Array<{
    display_name: string;
  }>;
  type_specific?: Record<string, unknown>;
};

export type InstanceAgAccountItem = {
  id: number;
  username: string;
  db_type: string;
  availability_group_name?: string | null;
  listener_name?: string | null;
  listener_host?: string | null;
  is_locked: boolean;
  is_superuser: boolean;
  is_active: boolean;
  is_deleted: boolean;
  availability_reasons: string[];
  last_change_time?: string | null;
  last_sync_time?: string | null;
  type_specific?: Record<string, unknown>;
};

export type InstanceAgAccountsResponse = {
  cluster?: {
    id: number;
    name: string;
  } | null;
  items: InstanceAgAccountItem[];
  total: number;
  summary?: {
    total?: number;
    active?: number;
    deleted?: number;
    superuser?: number;
  };
};

export type InstanceDatabaseSizeItem = {
  id?: number | null;
  database_name: string;
  size_mb?: number | string | null;
  data_size_mb?: number | string | null;
  log_size_mb?: number | string | null;
  collected_date?: string | null;
  collected_at?: string | null;
  is_active: boolean;
  deleted_at?: string | null;
  last_seen_date?: string | null;
};

export type InstanceDatabaseSizesResponse = {
  total: number;
  page: number;
  pages?: number;
  limit: number;
  active_count?: number;
  filtered_count?: number;
  total_size_mb?: number | string | null;
  databases: InstanceDatabaseSizeItem[];
};

export type AccountPermissionsResponse = {
  account: {
    id: number;
    username: string;
    instance_name?: string | null;
    db_type?: string | null;
  };
  permissions: {
    db_type?: string | null;
    username?: string | null;
    is_superuser?: boolean;
    last_sync_time?: string | null;
    snapshot?: unknown;
  };
};

export type AccountChangeHistoryResponse = {
  account: {
    id: number;
    username: string;
    db_type?: string | null;
  };
  history: Array<{
    id: number;
    change_type?: string | null;
    change_time?: string | null;
    status?: string | null;
    message?: string | null;
    privilege_diff?: unknown;
    other_diff?: unknown;
    session_id?: string | null;
  }>;
};

function firstPagePath(path: string, limit = DEFAULT_LIST_LIMIT): string {
  const params = new URLSearchParams({
    page: "1",
    limit: String(limit)
  });
  return `${path}?${params.toString()}`;
}

function queryPath(path: string, entries: Array<[string, string | number | boolean | string[] | undefined]>): string {
  const params = new URLSearchParams();
  entries.forEach(([key, value]) => {
    if (value === undefined || value === "") {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, item));
      return;
    }
    params.set(key, String(value));
  });
  return `${path}?${params.toString()}`;
}

export async function fetchInstances(query: InstanceListQuery = {}, client: ApiReader = apiClient): Promise<PaginatedList<InstanceListItem>> {
  return client.get<PaginatedList<InstanceListItem>>(queryPath("/api/v1/instances", [
    ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search], ["db_type", query.dbType],
    ["status", query.status], ["audit_status", query.auditStatus], ["managed_status", query.managedStatus],
    ["backup_status", query.backupStatus], ["tags", query.tags], ["include_deleted", query.includeDeleted || undefined]
  ]));
}

export async function fetchCredentialOptions(client: ApiReader = apiClient): Promise<CredentialOptionItem[]> {
  const response = await client.get<PaginatedList<CredentialOptionItem>>(firstPagePath("/api/v1/credentials"));
  return response.items;
}

export async function fetchTagOptions(client: ApiReader = apiClient): Promise<TagItem[]> {
  const response = await client.get<{ tags: TagItem[] }>("/api/v1/tags/options");
  return response.tags;
}

export async function fetchAccountClassificationOptions(client: ApiReader = apiClient): Promise<AccountClassificationOption[]> {
  const response = await client.get<{ classifications: AccountClassificationOption[] }>("/api/v1/accounts/classifications");
  return response.classifications;
}

export async function fetchDatabaseLedgers(query: DatabaseLedgerQuery = {}, client: ApiReader = apiClient): Promise<PaginatedList<DatabaseLedgerItem>> {
  return client.get<PaginatedList<DatabaseLedgerItem>>(queryPath("/api/v1/databases/ledgers", [
    ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search], ["db_type", query.dbType],
    ["instance_id", query.instanceId], ["tags", query.tags]
  ]));
}

export async function fetchAccountLedgers(query: AccountLedgerQuery = {}, client: ApiReader = apiClient): Promise<PaginatedList<AccountLedgerItem>> {
  return client.get<PaginatedList<AccountLedgerItem>>(queryPath("/api/v1/accounts/ledgers", [
    ["page", query.page ?? 1], ["limit", query.limit ?? 20], ["search", query.search], ["instance_id", query.instanceId],
    ["tags", query.tags], ["classification", query.classification], ["db_type", query.dbType], ["ad_status", query.adStatus],
    ["sort", "username"], ["order", "asc"]
  ]));
}

export function buildInstancesExportPath(query: InstanceListQuery): string {
  return queryPath("/api/v1/instances/exports", [["search", query.search], ["db_type", query.dbType]]);
}

export function buildDatabaseLedgersExportPath(query: DatabaseLedgerQuery): string {
  return queryPath("/api/v1/databases/ledgers/exports", [
    ["search", query.search], ["db_type", query.dbType], ["instance_id", query.instanceId], ["tags", query.tags]
  ]);
}

export function buildAccountLedgersExportPath(query: AccountLedgerQuery): string {
  return queryPath("/api/v1/accounts/ledgers/exports", [
    ["search", query.search], ["instance_id", query.instanceId], ["tags", query.tags],
    ["classification", query.classification], ["db_type", query.dbType], ["ad_status", query.adStatus]
  ]);
}

export async function fetchInstanceDetail(instanceId: number, client: ApiReader = apiClient): Promise<InstanceDetailResponse> {
  return client.get<InstanceDetailResponse>(`/api/v1/instances/${instanceId}`);
}

export async function fetchInstanceConnectionStatus(
  instanceId: number,
  client: ApiReader = apiClient
): Promise<InstanceConnectionStatus> {
  return client.get<InstanceConnectionStatus>(`/api/v1/instances/${instanceId}/connection-status`);
}

export async function fetchInstanceAuditInfo(instanceId: number, client: ApiReader = apiClient): Promise<InstanceAuditInfo> {
  return client.get<InstanceAuditInfo>(`/api/v1/instances/${instanceId}/audit-info`);
}

export async function fetchInstanceBackupInfo(instanceId: number, client: ApiReader = apiClient): Promise<InstanceBackupInfo> {
  return client.get<InstanceBackupInfo>(`/api/v1/instances/${instanceId}/backup-info`);
}

export async function fetchInstanceAccounts(
  instanceId: number,
  client: ApiReader = apiClient
): Promise<PaginatedList<AccountLedgerItem>> {
  const params = new URLSearchParams({
    page: "1",
    limit: "200",
    instance_id: String(instanceId),
    sort: "username",
    order: "asc",
    include_roles: "true",
    owner_type: "instance"
  });
  return client.get<PaginatedList<AccountLedgerItem>>(`/api/v1/accounts/ledgers?${params.toString()}`);
}

export async function fetchInstanceAgAccounts(
  instanceId: number,
  client: ApiReader = apiClient
): Promise<InstanceAgAccountsResponse> {
  return client.get<InstanceAgAccountsResponse>(`/api/v1/instances/${instanceId}/ag-accounts`);
}

export async function fetchInstanceDatabaseSizes(
  instanceId: number,
  client: ApiReader = apiClient
): Promise<InstanceDatabaseSizesResponse> {
  const params = new URLSearchParams({
    instance_id: String(instanceId),
    latest_only: "true",
    include_inactive: "true",
    page: "1",
    limit: "100"
  });
  return client.get<InstanceDatabaseSizesResponse>(`/api/v1/databases/sizes?${params.toString()}`);
}

export async function fetchAccountPermissions(accountId: number, client: ApiReader = apiClient): Promise<AccountPermissionsResponse> {
  return client.get<AccountPermissionsResponse>(`/api/v1/accounts/ledgers/${accountId}/permissions`);
}

export async function fetchAccountChangeHistory(accountId: number, client: ApiReader = apiClient): Promise<AccountChangeHistoryResponse> {
  return client.get<AccountChangeHistoryResponse>(`/api/v1/accounts/ledgers/${accountId}/change-history`);
}

export async function fetchDatabaseTableSizes(databaseId: number, client: ApiReader = apiClient): Promise<DatabaseTableSizesResponse> {
  return client.get<DatabaseTableSizesResponse>(firstPagePath(`/api/v1/databases/${databaseId}/tables/sizes`));
}
