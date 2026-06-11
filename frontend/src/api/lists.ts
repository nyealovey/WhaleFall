import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;

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

function firstPagePath(path: string): string {
  const params = new URLSearchParams({
    page: "1",
    limit: "20"
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
