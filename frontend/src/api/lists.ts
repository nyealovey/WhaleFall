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

function firstPagePath(path: string): string {
  const params = new URLSearchParams({
    page: "1",
    limit: String(DEFAULT_LIST_LIMIT)
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

export async function fetchAccountPermissions(accountId: number, client: ApiReader = apiClient): Promise<AccountPermissionsResponse> {
  return client.get<AccountPermissionsResponse>(`/api/v1/accounts/ledgers/${accountId}/permissions`);
}

export async function fetchAccountChangeHistory(accountId: number, client: ApiReader = apiClient): Promise<AccountChangeHistoryResponse> {
  return client.get<AccountChangeHistoryResponse>(`/api/v1/accounts/ledgers/${accountId}/change-history`);
}

export async function fetchDatabaseTableSizes(databaseId: number, client: ApiReader = apiClient): Promise<DatabaseTableSizesResponse> {
  return client.get<DatabaseTableSizesResponse>(firstPagePath(`/api/v1/databases/${databaseId}/tables/sizes`));
}
