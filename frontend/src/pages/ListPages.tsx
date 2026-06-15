import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  AlertCircle,
  BarChart3,
  Download,
  ExternalLink,
  Eye,
  FileUp,
  Pencil,
  PlugZap,
  Plus,
  RefreshCw,
  RotateCcw,
  Trash2
} from "lucide-react";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import {
  batchTestInstanceConnections,
  createInstance,
  deleteInstance,
  refreshDatabaseTableSizes,
  restoreInstance,
  syncAccounts,
  syncDatabases,
  testInstanceConnection,
  updateInstance,
  type InstanceWritePayload
} from "@/api/actions";
import {
  fetchAccountChangeHistory,
  fetchAccountLedgers,
  fetchAccountPermissions,
  fetchDatabaseLedgers,
  fetchDatabaseTableSizes,
  fetchInstanceDetail,
  fetchInstances,
  type AccountChangeHistoryResponse,
  type AccountLedgerItem,
  type AccountPermissionsResponse,
  type DatabaseLedgerItem,
  type DatabaseTableSizesResponse,
  type DatabaseTableSizeItem,
  type InstanceDetailResponse,
  type InstanceListItem,
  type PaginatedList
} from "@/api/lists";
import { DataTable } from "@/components/shared/DataTable";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

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

function asText(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">-</span>;
  }
  return (
    <pre className="max-h-56 overflow-auto rounded-md border bg-secondary/30 p-3 font-mono text-xs whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 rounded-md border bg-secondary/30 p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  );
}

const formSelectClassName =
  "border-input bg-background ring-offset-background focus-visible:ring-ring h-9 rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  );
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseTagNames(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function InstanceFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: InstanceListItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [dbType, setDbType] = useState(item?.db_type ?? "mysql");
  const [host, setHost] = useState(item?.host ?? "");
  const [port, setPort] = useState(String(item?.port ?? 3306));
  const [databaseName, setDatabaseName] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [tagNames, setTagNames] = useState(item?.tags.map((tag) => tag.name).join(", ") ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const title = item ? `编辑实例 ${item.name}` : "新建实例";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: InstanceWritePayload = {
      name: name.trim(),
      db_type: dbType,
      host: host.trim(),
      port: Number(port),
      database_name: databaseName.trim() || null,
      credential_id: parseOptionalNumber(credentialId),
      description: description.trim() || null,
      tag_names: parseTagNames(tagNames),
      is_active: isActive
    };
    const request = item ? updateInstance(item.id, payload) : createInstance(payload);
    void request.then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护实例基础连接信息。连接测试仍可在列表操作中执行。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="实例名称">
              <Input onChange={(event) => setName(event.target.value)} required value={name} />
            </FormField>
            <FormField label="数据库类型">
              <select className={formSelectClassName} onChange={(event) => setDbType(event.target.value)} required value={dbType}>
                <option value="mysql">mysql</option>
                <option value="postgresql">postgresql</option>
                <option value="sqlserver">sqlserver</option>
                <option value="oracle">oracle</option>
              </select>
            </FormField>
            <FormField label="主机/IP">
              <Input onChange={(event) => setHost(event.target.value)} required value={host} />
            </FormField>
            <FormField label="端口">
              <Input min={1} onChange={(event) => setPort(event.target.value)} required type="number" value={port} />
            </FormField>
            <FormField label="默认数据库">
              <Input onChange={(event) => setDatabaseName(event.target.value)} value={databaseName} />
            </FormField>
            <FormField label="凭据ID">
              <Input min={1} onChange={(event) => setCredentialId(event.target.value)} type="number" value={credentialId} />
            </FormField>
            <FormField label="标签代码">
              <Input onChange={(event) => setTagNames(event.target.value)} placeholder="prod, core" value={tagNames} />
            </FormField>
            <label className="flex items-center justify-between gap-3 rounded-md border bg-secondary/30 px-3 py-2 text-sm font-medium">
              <span>状态</span>
              <span className="flex items-center gap-2">
                <input
                  aria-label="启用"
                  checked={isActive}
                  className="size-4 accent-primary"
                  onChange={(event) => setIsActive(event.target.checked)}
                  type="checkbox"
                />
                <span className="text-muted-foreground">启用</span>
              </span>
            </label>
          </div>
          <FormField label="描述">
            <Textarea onChange={(event) => setDescription(event.target.value)} value={description} />
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存实例</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
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

function InstanceDetailDialog({ item, onOpenChange }: { item: InstanceListItem; onOpenChange: (open: boolean) => void }) {
  const query = useQuery({
    queryKey: ["lists", "instances", "detail", item.id],
    queryFn: () => fetchInstanceDetail(item.id)
  });
  const instance: InstanceDetailResponse["instance"] = query.data?.instance ?? item;

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>实例详情 {instance.name}</DialogTitle>
          <DialogDescription>来自 `/api/v1/instances/{instance.id}` 的实例详情。</DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <DetailField label="实例名称">{instance.name}</DetailField>
          <DetailField label="数据库类型">{dbTypeLabel(instance.db_type)}</DetailField>
          <DetailField label="主机/IP">{instance.host}:{instance.port}</DetailField>
          <DetailField label="状态">{instanceStatusLabel(instance)}</DetailField>
          <DetailField label="描述">{asText(instance.description)}</DetailField>
          <DetailField label="最后同步">{formatShortTimestamp(instance.last_sync_time)}</DetailField>
        </dl>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DatabaseTableSizesDialog({
  item,
  onOpenChange,
  onRefresh
}: {
  item: DatabaseLedgerItem;
  onOpenChange: (open: boolean) => void;
  onRefresh: () => void;
}) {
  const query = useQuery({
    queryKey: ["lists", "database-ledgers", item.id, "table-sizes"],
    queryFn: () => fetchDatabaseTableSizes(item.id)
  });
  const data: DatabaseTableSizesResponse | undefined = query.data;

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent className="w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader>
          <DialogTitle>数据库表容量 {item.database_name}</DialogTitle>
          <DialogDescription>
            {item.instance.name} · {formatShortTimestamp(data?.collected_at ?? item.capacity.collected_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Schema</TableHead>
                <TableHead>表名</TableHead>
                <TableHead>总大小</TableHead>
                <TableHead>数据</TableHead>
                <TableHead>索引</TableHead>
                <TableHead>行数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.tables.length === 0 ? (
                <TableRow>
                  <TableCell className="py-8 text-center text-sm text-muted-foreground" colSpan={6}>
                    暂无表容量数据
                  </TableCell>
                </TableRow>
              ) : null}
              {(data?.tables ?? []).map((table: DatabaseTableSizeItem) => (
                <TableRow key={`${table.schema_name ?? "-"}-${table.table_name}`}>
                  <TableCell>{table.schema_name ?? "-"}</TableCell>
                  <TableCell className="font-medium">{table.table_name}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.data_size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.index_size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.row_count)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <DialogFooter>
          <Button onClick={onRefresh} type="button">
            刷新表容量 {item.database_name}
          </Button>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountPermissionsDialog({ item, onOpenChange }: { item: AccountLedgerItem; onOpenChange: (open: boolean) => void }) {
  const query = useQuery({
    queryKey: ["lists", "account-ledgers", item.id, "permissions"],
    queryFn: () => fetchAccountPermissions(item.id)
  });
  const data: AccountPermissionsResponse | undefined = query.data;
  const snapshot = data?.permissions.snapshot as { roles?: unknown } | undefined;
  const roles = Array.isArray(snapshot?.roles) ? snapshot.roles.map((role) => asText(role)).filter((role) => role !== "-") : [];

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>权限详情 {data?.account.username ?? item.username}</DialogTitle>
          <DialogDescription>
            {item.instance_name} · {dbTypeLabel(data?.permissions.db_type ?? item.db_type)}
          </DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <DetailField label="账户">{data?.account.username ?? item.username}</DetailField>
          <DetailField label="是否超管">{data?.permissions.is_superuser ? "是" : "否"}</DetailField>
          <DetailField label="最后同步">{formatShortTimestamp(data?.permissions.last_sync_time)}</DetailField>
          <DetailField label="角色">
            {roles.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {roles.map((role) => (
                  <Badge key={role} variant="outline">
                    {role}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </DetailField>
        </dl>
        <JsonBlock value={data?.permissions.snapshot} />
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountChangeHistoryDialog({ item, onOpenChange }: { item: AccountLedgerItem; onOpenChange: (open: boolean) => void }) {
  const query = useQuery({
    queryKey: ["lists", "account-ledgers", item.id, "change-history"],
    queryFn: () => fetchAccountChangeHistory(item.id)
  });
  const data: AccountChangeHistoryResponse | undefined = query.data;

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent className="w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader>
          <DialogTitle>变更历史 {data?.account.username ?? item.username}</DialogTitle>
          <DialogDescription>账户权限与状态变更记录。</DialogDescription>
        </DialogHeader>
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>摘要</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.history ?? []).map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono text-xs">{formatShortTimestamp(record.change_time)}</TableCell>
                  <TableCell>{asText(record.change_type)}</TableCell>
                  <TableCell>
                    <BadgeText value={asText(record.status)} />
                  </TableCell>
                  <TableCell>{asText(record.message)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function createInstanceColumns({
  onDelete,
  onEdit,
  onRestore,
  onView
}: {
  onDelete: (item: InstanceListItem) => void;
  onEdit: (item: InstanceListItem) => void;
  onRestore: (item: InstanceListItem) => void;
  onView: (item: InstanceListItem) => void;
}): ColumnDef<InstanceListItem>[] {
  return [
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
      <div className="flex flex-wrap gap-2">
        <Button aria-label={`查看详情 ${row.original.id}`} onClick={() => onView(row.original)} size="sm" type="button" variant="outline">
          <Eye aria-hidden size={14} />
          <span>详情</span>
        </Button>
        <Button aria-label={`编辑实例 ${row.original.id}`} onClick={() => onEdit(row.original)} size="sm" type="button" variant="outline">
          <Pencil aria-hidden size={14} />
          <span>编辑</span>
        </Button>
        <Button
          aria-label={`测试连接 ${row.original.id}`}
          onClick={() => {
            void testInstanceConnection(row.original.id);
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          <PlugZap aria-hidden size={14} />
          <span>测试</span>
        </Button>
        {row.original.deleted_at ? (
          <Button aria-label={`恢复实例 ${row.original.id}`} onClick={() => onRestore(row.original)} size="sm" type="button" variant="outline">
            <RotateCcw aria-hidden size={14} />
            <span>恢复</span>
          </Button>
        ) : (
          <Button aria-label={`删除实例 ${row.original.id}`} onClick={() => onDelete(row.original)} size="sm" type="button" variant="outline">
            <Trash2 aria-hidden size={14} />
            <span>删除</span>
          </Button>
        )}
      </div>
    )
  }
  ];
}

function createDatabaseLedgerColumns({
  onViewTables
}: {
  onViewTables: (item: DatabaseLedgerItem) => void;
}): ColumnDef<DatabaseLedgerItem>[] {
  return [
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
      <Button aria-label={`查看容量趋势 ${row.original.id}`} onClick={() => onViewTables(row.original)} size="sm" type="button" variant="outline">
        <ExternalLink aria-hidden size={14} />
        <span>趋势</span>
      </Button>
    )
  }
  ];
}

function createAccountLedgerColumns({
  onViewHistory,
  onViewPermissions
}: {
  onViewHistory: (item: AccountLedgerItem) => void;
  onViewPermissions: (item: AccountLedgerItem) => void;
}): ColumnDef<AccountLedgerItem>[] {
  return [
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
      <div className="flex flex-wrap gap-2">
        <Button aria-label={`查看权限 ${row.original.id}`} onClick={() => onViewPermissions(row.original)} size="sm" type="button" variant="outline">
          <Eye aria-hidden size={14} />
          <span>权限</span>
        </Button>
        <Button aria-label={`查看变更历史 ${row.original.id}`} onClick={() => onViewHistory(row.original)} size="sm" type="button" variant="outline">
          <ExternalLink aria-hidden size={14} />
          <span>变更</span>
        </Button>
      </div>
    )
  }
  ];
}

export function InstancesPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "instances", 1, 20],
    queryFn: () => fetchInstances()
  });
  const [selectedInstance, setSelectedInstance] = useState<InstanceListItem | null>(null);
  const [creatingInstance, setCreatingInstance] = useState(false);
  const [editingInstance, setEditingInstance] = useState<InstanceListItem | null>(null);
  const [deletingInstance, setDeletingInstance] = useState<InstanceListItem | null>(null);
  function handleInstanceSaved() {
    setCreatingInstance(false);
    setEditingInstance(null);
    void listQuery.refetch();
  }
  const columns = useMemo(
    () =>
      createInstanceColumns({
        onDelete: setDeletingInstance,
        onEdit: setEditingInstance,
        onRestore: (item) => {
          void restoreInstance(item.id).then(() => listQuery.refetch());
        },
        onView: setSelectedInstance
      }),
    [listQuery]
  );
  const visibleInstanceIds = listQuery.data?.items.map((item) => item.id) ?? [];

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
        <Button onClick={() => setCreatingInstance(true)} type="button">
          <Plus aria-hidden size={16} />
          <span>添加实例</span>
        </Button>
        <Button disabled variant="outline">
          <Trash2 aria-hidden size={16} />
          <span>移入回收站</span>
        </Button>
        <Button
          disabled={visibleInstanceIds.length === 0}
          onClick={() => {
            void batchTestInstanceConnections(visibleInstanceIds).then(() => listQuery.refetch());
          }}
          type="button"
          variant="outline"
        >
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
              columns={columns}
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
      {selectedInstance ? (
        <InstanceDetailDialog
          item={selectedInstance}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedInstance(null);
            }
          }}
        />
      ) : null}
      {creatingInstance ? (
        <InstanceFormDialog
          item={null}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingInstance(false);
            }
          }}
          onSaved={handleInstanceSaved}
          open
        />
      ) : null}
      {editingInstance ? (
        <InstanceFormDialog
          item={editingInstance}
          onOpenChange={(open) => {
            if (!open) {
              setEditingInstance(null);
            }
          }}
          onSaved={handleInstanceSaved}
          open
        />
      ) : null}
      <AlertDialog
        open={deletingInstance !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingInstance(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认移入回收站 {deletingInstance?.name ?? ""}</AlertDialogTitle>
            <AlertDialogDescription>实例会被软删除并从默认列表中隐藏，可在包含已删除记录后恢复。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!deletingInstance) {
                  return;
                }
                const instanceId = deletingInstance.id;
                setDeletingInstance(null);
                void deleteInstance(instanceId).then(() => listQuery.refetch());
              }}
            >
              确认移入回收站
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}

export function DatabaseLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "database-ledgers", 1, 20],
    queryFn: () => fetchDatabaseLedgers()
  });
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseLedgerItem | null>(null);
  const columns = useMemo(
    () =>
      createDatabaseLedgerColumns({
        onViewTables: setSelectedDatabase
      }),
    []
  );

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
        <Button
          onClick={() => {
            void syncDatabases().then(() => listQuery.refetch());
          }}
          type="button"
        >
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
              columns={columns}
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
      {selectedDatabase ? (
        <DatabaseTableSizesDialog
          item={selectedDatabase}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedDatabase(null);
            }
          }}
          onRefresh={() => {
            void refreshDatabaseTableSizes(selectedDatabase.id).then(() => listQuery.refetch());
          }}
        />
      ) : null}
    </main>
  );
}

export function AccountLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "account-ledgers", 1, 20],
    queryFn: () => fetchAccountLedgers()
  });
  const [permissionsAccount, setPermissionsAccount] = useState<AccountLedgerItem | null>(null);
  const [historyAccount, setHistoryAccount] = useState<AccountLedgerItem | null>(null);
  const columns = useMemo(
    () =>
      createAccountLedgerColumns({
        onViewHistory: setHistoryAccount,
        onViewPermissions: setPermissionsAccount
      }),
    []
  );

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
        <Button
          onClick={() => {
            void syncAccounts().then(() => listQuery.refetch());
          }}
          type="button"
        >
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
              columns={columns}
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
      {permissionsAccount ? (
        <AccountPermissionsDialog
          item={permissionsAccount}
          onOpenChange={(open) => {
            if (!open) {
              setPermissionsAccount(null);
            }
          }}
        />
      ) : null}
      {historyAccount ? (
        <AccountChangeHistoryDialog
          item={historyAccount}
          onOpenChange={(open) => {
            if (!open) {
              setHistoryAccount(null);
            }
          }}
        />
      ) : null}
    </main>
  );
}
