import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;
const DEFAULT_LIST_LIMIT = 200;

type TagItem = {
  name: string;
  display_name: string;
  color?: string;
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

export async function fetchInstances(client: ApiReader = apiClient): Promise<PaginatedList<InstanceListItem>> {
  return client.get<PaginatedList<InstanceListItem>>(firstPagePath("/api/v1/instances"));
}

export async function fetchDatabaseLedgers(client: ApiReader = apiClient): Promise<PaginatedList<DatabaseLedgerItem>> {
  return client.get<PaginatedList<DatabaseLedgerItem>>(firstPagePath("/api/v1/databases/ledgers"));
}

export async function fetchAccountLedgers(client: ApiReader = apiClient): Promise<PaginatedList<AccountLedgerItem>> {
  return client.get<PaginatedList<AccountLedgerItem>>(firstPagePath("/api/v1/accounts/ledgers"));
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
