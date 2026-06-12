import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  AlertCircle,
  BarChart3,
  Download,
  ExternalLink,
  Eye,
  FileUp,
  PlugZap,
  Plus,
  RefreshCw,
  RotateCcw,
  Trash2
} from "lucide-react";
import type { ReactNode } from "react";

import {
  fetchAccountLedgers,
  fetchDatabaseLedgers,
  fetchInstances,
  type AccountLedgerItem,
  type DatabaseLedgerItem,
  type InstanceListItem,
  type PaginatedList
} from "@/api/lists";
import { DataTable } from "@/components/shared/DataTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type TagItem = {
  name: string;
  display_name: string;
};

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatShortTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "暂无同步记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.replace("T", " ").replace(/\.\d+/, "").replace(/\+\d{2}:\d{2}$/, "");
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function statusVariant(status: string | undefined): "default" | "secondary" | "destructive" | "outline" {
  if (!status) {
    return "outline";
  }
  if (["disabled", "deleted", "failed", "error", "not_backed_up", "locked", "已删除", "已锁定", "未备份"].includes(status)) {
    return "destructive";
  }
  if (["ok", "enabled", "completed", "backed_up", "active", "启用", "已启用", "已托管", "已备份", "正常"].includes(status)) {
    return "secondary";
  }
  return "outline";
}

function dbTypeLabel(value: string | undefined | null): string {
  return value ? value.toUpperCase() : "-";
}

function tagsText(tags: TagItem[]): string {
  return tags.map((tag) => tag.display_name || tag.name).filter(Boolean).join(" ");
}

function uniqueTextOptions<TItem>(items: TItem[], getValue: (item: TItem) => string | null | undefined) {
  const values = new Set<string>();
  for (const item of items) {
    const value = getValue(item);
    if (value) {
      values.add(value);
    }
  }
  return [...values].sort((first, second) => first.localeCompare(second, "zh-CN")).map((value) => ({ label: value, value }));
}

function uniqueTagOptions<TItem>(items: TItem[], getTags: (item: TItem) => TagItem[]) {
  const values = new Map<string, string>();
  for (const item of items) {
    for (const tag of getTags(item)) {
      const value = tag.display_name || tag.name;
      if (value) {
        values.set(value, value);
      }
    }
  }
  return [...values.values()].sort((first, second) => first.localeCompare(second, "zh-CN")).map((value) => ({ label: value, value }));
}

function instanceStatusLabel(item: InstanceListItem): string {
  if (item.deleted_at) {
    return "已删除";
  }
  return item.is_active ? "启用" : "禁用";
}

function auditStatusLabel(item: InstanceListItem): string {
  switch (item.audit_status) {
    case "enabled":
      return "已启用";
    case "configured_disabled":
      return "已配置未启用";
    default:
      return item.db_type?.toLowerCase() === "sqlserver" ? "未配置" : "不支持";
  }
}

function managedStatusLabel(item: InstanceListItem): string {
  return item.is_jumpserver_managed ? "已托管" : "未托管";
}

function backupStatusLabel(item: InstanceListItem): string {
  switch (item.backup_status) {
    case "backed_up":
      return "已备份";
    case "backup_stale":
      return "备份异常";
    default:
      return "未备份";
  }
}

function availabilityLabel(item: AccountLedgerItem): string {
  if (!item.is_locked) {
    return "正常";
  }
  return item.availability_reasons.length > 0 ? `已锁定：${item.availability_reasons.join("；")}` : "已锁定";
}

function deletedLabel(value: boolean): string {
  return value ? "已删除" : "未删除";
}

function superuserLabel(value: boolean): string {
  return value ? "超管用户" : "普通用户";
}

function adStatusLabel(value: string | null | undefined): string {
  switch (value) {
    case "normal":
      return "AD正常";
    case "disabled":
      return "AD已停用";
    case "orphaned":
      return "AD孤账户";
    default:
      return "未匹配AD";
  }
}

function classificationText(item: AccountLedgerItem): string {
  return item.classifications.map((classification) => classification.display_name).filter(Boolean).join(" ");
}

function PageHeader({
  eyebrow,
  title,
  description,
  legacyHref
}: {
  eyebrow: string;
  title: string;
  description: string;
  legacyHref: string;
}) {
  return (
    <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
      <div>
        <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">{eyebrow}</span>
        <h1 className="font-display mt-1 text-2xl leading-none tracking-normal">{title}</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{description}</p>
      </div>
      <Button variant="outline" asChild>
        <a href={legacyHref}>
          <ExternalLink aria-hidden size={16} />
          <span>在旧版打开</span>
        </a>
      </Button>
    </section>
  );
}

function CommandBar({ children }: { children: ReactNode }) {
  return <section className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">{children}</section>;
}

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="列表加载中">
      {["a", "b", "c", "d"].map((key) => (
        <Card className="min-h-[var(--metric-card-min-height)]" key={key}>
          <CardContent className="grid gap-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="grid-cols-[1rem_minmax(0,1fr)] items-center sm:grid-cols-[1rem_minmax(0,1fr)_auto]">
      <AlertCircle aria-hidden size={16} />
      <AlertDescription>列表数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function TagList({ tags }: { tags: TagItem[] }) {
  if (tags.length === 0) {
    return <span className="text-muted-foreground">无标签</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {tags.slice(0, 6).map((tag) => (
        <Badge variant="outline" key={tag.name}>
          {tag.display_name || tag.name}
        </Badge>
      ))}
    </div>
  );
}

function BadgeText({ value, variantValue }: { value: string; variantValue?: string }) {
  return <Badge variant={statusVariant(variantValue ?? value)}>{value}</Badge>;
}

function ListFrame({
  title,
  description,
  total,
  children
}: {
  title: string;
  description: string;
  total: number;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-sm:grid">
          <div>
            <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
          <Badge variant="secondary">共 {formatNumber(total)} 条</Badge>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function QueryPage<TItem>({
  result,
  isLoading,
  isError,
  onRetry,
  children
}: {
  result: PaginatedList<TItem> | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  children: (result: PaginatedList<TItem>) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {result ? children(result) : null}
    </>
  );
}

const instanceColumns: ColumnDef<InstanceListItem>[] = [
  {
    accessorKey: "name",
    header: "名称",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="mt-1 text-xs text-muted-foreground">ID {row.original.id}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => `${item.host}:${item.port}`,
    id: "host",
    header: "主机/IP",
    cell: ({ row }) => (
      <div className="font-mono text-xs">
        {row.original.host}:{row.original.port}
      </div>
    )
  },
  {
    accessorFn: instanceStatusLabel,
    id: "status",
    header: "状态",
    cell: ({ row }) => <BadgeText value={instanceStatusLabel(row.original)} />
  },
  {
    accessorFn: auditStatusLabel,
    id: "audit_status",
    header: "审计",
    cell: ({ row }) => <BadgeText value={auditStatusLabel(row.original)} variantValue={row.original.audit_status} />
  },
  {
    accessorFn: managedStatusLabel,
    id: "managed_status",
    header: "已托管",
    cell: ({ row }) => <BadgeText value={managedStatusLabel(row.original)} />
  },
  {
    accessorFn: backupStatusLabel,
    id: "backup_status",
    header: "备份",
    cell: ({ row }) => <BadgeText value={backupStatusLabel(row.original)} variantValue={row.original.backup_status} />
  },
  {
    accessorFn: (item) => `${item.active_db_count}/${item.active_account_count}`,
    id: "active_counts",
    header: "活跃",
    cell: ({ row }) => (
      <div className="grid gap-1 text-xs text-muted-foreground">
        <span>数据库 {formatNumber(row.original.active_db_count)}</span>
        <span>账户 {formatNumber(row.original.active_account_count)}</span>
      </div>
    )
  },
  {
    accessorFn: (item) => `${item.main_version ?? "未检测"} ${formatShortTimestamp(item.last_sync_time)}`,
    id: "version_sync",
    header: "版本 / 同步",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.main_version || "未检测"}</div>
        <div className="mt-1 text-xs text-muted-foreground">{formatShortTimestamp(row.original.last_sync_time)}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex gap-2">
        <Button aria-label={`查看详情 ${row.original.id}`} size="sm" variant="outline">
          <Eye aria-hidden size={14} />
          <span>详情</span>
        </Button>
        <Button aria-label={`测试连接 ${row.original.id}`} size="sm" variant="outline">
          <PlugZap aria-hidden size={14} />
          <span>测试</span>
        </Button>
      </div>
    )
  }
];

const databaseLedgerColumns: ColumnDef<DatabaseLedgerItem>[] = [
  {
    accessorFn: (item) => `${item.database_name} ${item.instance.name} ${item.instance.host}`,
    id: "database_name",
    header: "数据库/实例",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.database_name}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {row.original.instance.name} · {row.original.instance.host}
        </div>
      </div>
    )
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => item.capacity.label || "未采集",
    id: "capacity",
    header: "数据库大小",
    cell: ({ row }) => (
      <div>
        <div className="font-mono text-xs font-medium">{row.original.capacity.label || "未采集"}</div>
        <div className="mt-1 text-xs text-muted-foreground">{formatShortTimestamp(row.original.capacity.collected_at)}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <Button aria-label={`查看容量趋势 ${row.original.id}`} size="sm" variant="outline">
        <ExternalLink aria-hidden size={14} />
        <span>趋势</span>
      </Button>
    )
  }
];

const accountLedgerColumns: ColumnDef<AccountLedgerItem>[] = [
  {
    accessorFn: (item) => `${item.username} ${item.instance_name} ${item.instance_host}`,
    id: "username",
    header: "账户/实例",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.username}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {row.original.instance_name} · {row.original.instance_host}
        </div>
      </div>
    )
  },
  {
    accessorFn: availabilityLabel,
    id: "is_locked",
    header: "是否可用",
    cell: ({ row }) => <BadgeText value={availabilityLabel(row.original)} variantValue={row.original.is_locked ? "locked" : "正常"} />
  },
  {
    accessorFn: (item) => deletedLabel(item.is_deleted),
    id: "is_deleted",
    header: "是否删除",
    cell: ({ row }) => <BadgeText value={deletedLabel(row.original.is_deleted)} variantValue={row.original.is_deleted ? "deleted" : undefined} />
  },
  {
    accessorFn: (item) => superuserLabel(item.is_superuser),
    id: "is_superuser",
    header: "是否超管",
    cell: ({ row }) => <Badge variant={row.original.is_superuser ? "outline" : "secondary"}>{superuserLabel(row.original.is_superuser)}</Badge>
  },
  {
    accessorFn: (item) => adStatusLabel(item.ad_status),
    id: "ad_status",
    header: "AD状态",
    cell: ({ row }) => <Badge variant="outline">{adStatusLabel(row.original.ad_status)}</Badge>
  },
  {
    accessorFn: classificationText,
    id: "classifications",
    header: "分类",
    cell: ({ row }) => {
      const labels = row.original.classifications.map((classification) => classification.display_name).filter(Boolean);
      return labels.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {labels.map((label) => (
            <Badge variant="outline" key={label}>
              {label}
            </Badge>
          ))}
        </div>
      ) : (
        <span className="text-muted-foreground">未分类</span>
      );
    }
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <Button aria-label={`查看权限 ${row.original.id}`} size="sm" variant="outline">
        <Eye aria-hidden size={14} />
        <span>权限</span>
      </Button>
    )
  }
];

export function InstancesPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "instances", 1, 20],
    queryFn: () => fetchInstances()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Resource inventory"
        title="实例管理"
        description="管理数据库实例，包括增删改查和连接测试。"
        legacyHref="/instances/"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/instances/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>实例统计</span>
          </a>
        </Button>
        <Button disabled>
          <Plus aria-hidden size={16} />
          <span>添加实例</span>
        </Button>
        <Button disabled variant="outline">
          <Trash2 aria-hidden size={16} />
          <span>移入回收站</span>
        </Button>
        <Button disabled variant="outline">
          <PlugZap aria-hidden size={16} />
          <span>批量测试连接</span>
        </Button>
        <Button disabled variant="outline">
          <FileUp aria-hidden size={16} />
          <span>批量导入</span>
        </Button>
        <label className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
          <input aria-label="显示已删除" className="accent-primary" type="checkbox" />
          <span>显示已删除</span>
        </label>
        <Button variant="outline" asChild>
          <a href="/api/v1/instances/exports">
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="实例列表" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
            <DataTable
              columns={instanceColumns}
              data={result.items}
              filters={[
                { columnId: "db_type", label: "类型", options: uniqueTextOptions(result.items, (item) => dbTypeLabel(item.db_type)) },
                { columnId: "status", label: "状态", options: uniqueTextOptions(result.items, instanceStatusLabel) },
                { columnId: "audit_status", label: "审计", options: uniqueTextOptions(result.items, auditStatusLabel) },
                { columnId: "managed_status", label: "托管", options: uniqueTextOptions(result.items, managedStatusLabel) },
                { columnId: "backup_status", label: "备份", options: uniqueTextOptions(result.items, backupStatusLabel) },
                { columnId: "tags", label: "标签", options: uniqueTagOptions(result.items, (item) => item.tags) }
              ]}
              searchPlaceholder="搜索实例 / 主机"
            />
          </ListFrame>
        )}
      </QueryPage>
    </main>
  );
}

export function DatabaseLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "database-ledgers", 1, 20],
    queryFn: () => fetchDatabaseLedgers()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database ledger"
        title="数据库台账"
        description="查看数据库所属实例、容量采集时间和标签。"
        legacyHref="/databases/ledgers"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/databases/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>数据库统计</span>
          </a>
        </Button>
        <Button disabled>
          <RefreshCw aria-hidden size={16} />
          <span>同步所有数据库</span>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/v1/databases/ledgers/exports">
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="数据库台账" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
            <DataTable
              columns={databaseLedgerColumns}
              data={result.items}
              filters={[
                { columnId: "db_type", label: "类型", options: uniqueTextOptions(result.items, (item) => dbTypeLabel(item.db_type)) },
                { columnId: "tags", label: "标签", options: uniqueTagOptions(result.items, (item) => item.tags) }
              ]}
              searchPlaceholder="搜索数据库 / 实例"
            />
          </ListFrame>
        )}
      </QueryPage>
    </main>
  );
}

export function AccountLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "account-ledgers", 1, 20],
    queryFn: () => fetchAccountLedgers()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Account ledger"
        title="账户台账"
        description="查看账户所属实例、可用性、删除状态、超管标识、AD 状态、分类和标签。"
        legacyHref="/accounts/ledgers"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/accounts/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>账户统计</span>
          </a>
        </Button>
        <Button disabled>
          <RotateCcw aria-hidden size={16} />
          <span>同步所有账户</span>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/v1/accounts/ledgers/exports">
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="账户台账" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
            <DataTable
              columns={accountLedgerColumns}
              data={result.items}
              filters={[
                { columnId: "classifications", label: "分类", options: uniqueTextOptions(result.items, classificationText) },
                { columnId: "ad_status", label: "AD状态", options: uniqueTextOptions(result.items, (item) => adStatusLabel(item.ad_status)) },
                { columnId: "tags", label: "标签", options: uniqueTagOptions(result.items, (item) => item.tags) }
              ]}
              searchPlaceholder="搜索账户 / 实例"
            />
          </ListFrame>
        )}
      </QueryPage>
    </main>
  );
}
