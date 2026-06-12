import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Activity,
  AlertCircle,
  Boxes,
  ChartColumn,
  Clock,
  Database,
  ExternalLink,
  KeyRound,
  Layers3,
  ListChecks,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Settings,
  Tags,
  Trash2,
  UserCog,
  Zap
} from "lucide-react";
import type { ReactNode } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  fetchAccountClassificationsSnapshot,
  fetchClassificationStatisticsSnapshot,
  fetchClustersSnapshot,
  fetchCredentialsSnapshot,
  fetchPartitionsSnapshot,
  fetchSchedulerSnapshot,
  fetchSettingsSnapshot,
  fetchSyncSessionsSnapshot,
  fetchTagsSnapshot,
  fetchUsersSnapshot,
  type AccountClassificationRuleItem,
  type ClassificationStatisticsSnapshot,
  type ClusterItem,
  type CredentialItem,
  type PartitionItem,
  type SchedulerJobItem,
  type SettingsSnapshot,
  type SyncSessionItem,
  type TagItem,
  type UserItem
} from "@/api/readOnly";
import { DataTable } from "@/components/shared/DataTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof Layers3;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0%";
  }
  return `${Math.round((value / total) * 100)}%`;
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
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

function endpointHost(value: unknown): string {
  const text = asText(value);
  if (text === "-") {
    return text;
  }
  try {
    return new URL(text).host || text;
  } catch {
    return text;
  }
}

function statusVariant(value: string | boolean | undefined | null): "default" | "secondary" | "destructive" | "outline" {
  if (value === true) {
    return "secondary";
  }
  if (value === false || value === null || value === undefined) {
    return "outline";
  }
  const normalized = String(value).toLowerCase();
  if (["failed", "error", "unhealthy", "disabled", "inactive", "cancelled"].includes(normalized)) {
    return "destructive";
  }
  if (["healthy", "completed", "success", "running", "active", "enabled", "state_running"].includes(normalized)) {
    return "secondary";
  }
  return "outline";
}

function statusLabel(value: string | boolean | undefined | null): string {
  if (value === true) {
    return "启用";
  }
  if (value === false) {
    return "停用";
  }
  return asText(value);
}

function roleLabel(role: string | undefined | null): string {
  switch (role) {
    case "admin":
      return "管理员";
    case "user":
      return "普通用户";
    case "viewer":
      return "查看者";
    default:
      return asText(role);
  }
}

function isRunningState(state: string | undefined | null): boolean {
  return state === "STATE_RUNNING" || state === "STATE_EXECUTING" || state === "running";
}

function schedulerStatusLabel(state: string | undefined | null): string {
  switch (state) {
    case "STATE_RUNNING":
    case "STATE_EXECUTING":
      return "运行中";
    case "STATE_PAUSED":
      return "已暂停";
    case "STATE_ERROR":
      return "失败";
    default:
      return asText(state, "未知");
  }
}

function triggerArgsEntries(value: unknown): string[] {
  if (!value) {
    return [];
  }
  if (typeof value === "string") {
    try {
      return triggerArgsEntries(JSON.parse(value) as unknown);
    } catch {
      return [value];
    }
  }
  if (typeof value !== "object") {
    return [String(value)];
  }
  return Object.entries(value as Record<string, unknown>)
    .filter(([key, entry]) => !["__proto__", "prototype", "constructor"].includes(key) && entry !== undefined && entry !== null && entry !== "")
    .map(([key, entry]) => (key === "description" ? String(entry) : `${key}: ${String(entry)}`));
}

function syncRunId(item: SyncSessionItem): string {
  return item.run_id ?? item.session_id;
}

function syncTaskName(item: SyncSessionItem): string {
  return item.task_name ?? item.task_key ?? item.sync_type;
}

function syncSource(item: SyncSessionItem): string {
  return item.trigger_source ?? item.sync_type;
}

function syncCategory(item: SyncSessionItem): string {
  return item.task_category ?? item.sync_category;
}

function syncProgress(item: SyncSessionItem) {
  const total = item.progress_total ?? item.total_instances ?? 0;
  const completed = item.progress_completed ?? item.successful_instances ?? 0;
  const failed = item.progress_failed ?? item.failed_instances ?? 0;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { total, completed, failed, percent };
}

function syncDuration(item: SyncSessionItem): string {
  if (item.status === "running") {
    return "进行中";
  }
  if (!item.started_at || !item.completed_at) {
    return "-";
  }
  const started = Date.parse(item.started_at);
  const completed = Date.parse(item.completed_at);
  if (!Number.isFinite(started) || !Number.isFinite(completed) || completed < started) {
    return "-";
  }
  const seconds = Math.round((completed - started) / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
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

function MetricGrid({ metrics, label }: { metrics: Metric[]; label: string }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label={label}>
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <Card className="min-h-[var(--metric-card-min-height)]" key={metric.label}>
            <CardContent className="grid gap-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Icon aria-hidden size={18} />
                <span>{metric.label}</span>
              </div>
              <strong className="font-mono text-[length:var(--metric-hero-value)] leading-none">
                {typeof metric.value === "number" ? formatNumber(metric.value) : metric.value}
              </strong>
              {metric.detail ? <span className="text-xs text-muted-foreground">{metric.detail}</span> : null}
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="只读页面加载中">
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

function ErrorState({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="grid-cols-[1rem_minmax(0,1fr)] items-center sm:grid-cols-[1rem_minmax(0,1fr)_auto]">
      <AlertCircle aria-hidden size={16} />
      <AlertDescription>{label}加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function QueryFrame<TData>({
  data,
  isLoading,
  isError,
  errorLabel,
  onRetry,
  children
}: {
  data: TData | undefined;
  isLoading: boolean;
  isError: boolean;
  errorLabel: string;
  onRetry: () => void;
  children: (data: TData) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState label={errorLabel} onRetry={onRetry} /> : null}
      {data ? children(data) : null}
    </>
  );
}

function ListPanel({
  title,
  description,
  count,
  actions,
  children
}: {
  title: string;
  description: string;
  count?: number;
  actions?: ReactNode;
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
          <div className="flex flex-wrap items-center justify-end gap-2">
            {typeof count === "number" ? <Badge variant="secondary">共 {formatNumber(count)} 条</Badge> : null}
            {actions}
          </div>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function EmptyRows({ colSpan }: { colSpan: number }) {
  return (
    <TableRow>
      <TableCell className="px-3 py-8 text-center text-sm text-muted-foreground" colSpan={colSpan}>
        暂无数据
      </TableCell>
    </TableRow>
  );
}

function StatusBadge({ value }: { value: string | boolean | undefined | null }) {
  return <Badge variant={statusVariant(value)}>{statusLabel(value)}</Badge>;
}

const credentialColumns: ColumnDef<CredentialItem>[] = [
  {
    accessorKey: "name",
    header: "凭据",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="grid gap-1">
          <span className="font-medium">{item.name}</span>
          <span className="font-mono text-xs text-muted-foreground">{item.username ?? "-"}</span>
        </div>
      );
    }
  },
  {
    accessorKey: "credential_type",
    header: "类型",
    cell: ({ row }) => row.original.credential_type ?? "-"
  },
  {
    accessorKey: "db_type",
    header: "数据库类型",
    cell: ({ row }) => row.original.db_type ?? "-"
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "instance_count",
    header: "绑定实例",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    accessorKey: "created_at_display",
    header: "创建时间",
    cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.created_at_display ?? "-"}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑凭据 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除凭据 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
];

const tagColumns: ColumnDef<TagItem>[] = [
  {
    accessorKey: "display_name",
    header: "标签",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="grid gap-1">
          <span className="font-medium">{item.display_name}</span>
          <span className="font-mono text-xs text-muted-foreground">#{item.name}</span>
        </div>
      );
    }
  },
  {
    accessorKey: "category",
    header: "分类"
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "instance_count",
    header: "关联",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑标签 ${row.original.display_name}`} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除标签 ${row.original.display_name}`} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
];

const userColumns: ColumnDef<UserItem>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">#{row.original.id}</span>
  },
  {
    accessorKey: "username",
    header: "用户",
    cell: ({ row }) => (
      <div className="grid gap-1">
        <span className="font-medium">{row.original.username}</span>
        {row.original.email ? <span className="text-xs text-muted-foreground">{row.original.email}</span> : null}
      </div>
    )
  },
  {
    accessorKey: "role",
    header: "角色",
    cell: ({ row }) => <Badge variant={row.original.role === "admin" ? "default" : "outline"}>{roleLabel(row.original.role)}</Badge>
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "created_at_display",
    header: "创建时间",
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.created_at_display ?? row.original.created_at ?? "-"}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑用户 ${row.original.username}`} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除用户 ${row.original.username}`} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
];

const syncSessionColumns: ColumnDef<SyncSessionItem>[] = [
  {
    id: "run_id",
    header: "运行ID",
    accessorFn: (item) => syncRunId(item),
    cell: ({ row }) => <span className="font-mono text-xs">{syncRunId(row.original)}</span>
  },
  {
    accessorKey: "status",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.status} />
  },
  {
    id: "progress",
    header: "进度",
    cell: ({ row }) => {
      const progress = syncProgress(row.original);
      return (
        <div className="grid min-w-40 gap-2">
          <Progress aria-label={`${syncRunId(row.original)} 进度`} value={progress.percent} />
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>{progress.percent}%</span>
            <span>
              {formatNumber(progress.completed)}/{formatNumber(progress.total)} · failed {formatNumber(progress.failed)}
            </span>
          </div>
        </div>
      );
    }
  },
  {
    id: "task",
    header: "任务",
    accessorFn: (item) => syncTaskName(item),
    cell: ({ row }) => (
      <div className="grid gap-1">
        <span className="font-medium">{syncTaskName(row.original)}</span>
        <span className="font-mono text-xs text-muted-foreground">{row.original.task_key ?? row.original.sync_type}</span>
      </div>
    )
  },
  {
    id: "trigger_source",
    header: "来源",
    accessorFn: (item) => syncSource(item),
    cell: ({ row }) => <Badge variant="outline">{syncSource(row.original)}</Badge>
  },
  {
    id: "task_category",
    header: "分类",
    accessorFn: (item) => syncCategory(item),
    cell: ({ row }) => <Badge variant="secondary">{syncCategory(row.original)}</Badge>
  },
  {
    accessorKey: "started_at",
    header: "开始时间",
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.started_at ?? "-"}</span>
  },
  {
    id: "duration",
    header: "耗时",
    cell: ({ row }) => <span className="text-xs text-muted-foreground">{syncDuration(row.original)}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => {
      const runId = syncRunId(row.original);
      return (
        <div className="flex items-center gap-1">
          <Button aria-label={`查看详情 ${runId}`} size="icon" type="button" variant="ghost">
            <ExternalLink aria-hidden />
          </Button>
          {row.original.status === "running" ? (
            <Button aria-label={`取消任务 ${runId}`} size="icon" type="button" variant="ghost">
              <Pause aria-hidden />
            </Button>
          ) : null}
        </div>
      );
    }
  }
];

function SchedulerJobCard({ job }: { job: SchedulerJobItem }) {
  const name = job.task_name ?? job.name ?? job.id;
  const triggerEntries = triggerArgsEntries(job.trigger_args);

  return (
    <Card className="min-h-[16rem]">
      <CardContent className="grid gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold">{name}</h3>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{job.func ?? job.trigger_type ?? "-"}</p>
          </div>
          <Badge variant={isRunningState(job.state) ? "secondary" : "outline"}>{schedulerStatusLabel(job.state)}</Badge>
        </div>
        <dl className="grid gap-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">下次运行</dt>
            <dd className="font-mono text-xs">{job.next_run_time ?? "未计划"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">上次运行</dt>
            <dd className="font-mono text-xs">{job.last_run_time ?? "从未运行"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">任务 ID</dt>
            <dd className="font-mono text-xs">{job.task_id ?? job.id}</dd>
          </div>
        </dl>
        <div className="grid gap-2">
          <span className="text-sm font-medium">触发器参数</span>
          <div className="flex min-h-8 flex-wrap gap-1">
            {triggerEntries.length > 0 ? triggerEntries.map((entry) => <Badge key={entry} variant="outline">{entry}</Badge>) : <span className="text-sm text-muted-foreground">-</span>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {isRunningState(job.state) ? (
            <Button aria-label={`暂停任务 ${name}`} size="icon" type="button" variant="outline">
              <Pause aria-hidden />
            </Button>
          ) : (
            <Button aria-label={`恢复任务 ${name}`} size="icon" type="button" variant="outline">
              <Play aria-hidden />
            </Button>
          )}
          <Button aria-label={`立即执行 ${name}`} size="icon" type="button" variant="outline">
            <Zap aria-hidden />
          </Button>
          <Button aria-label={`编辑任务 ${name}`} size="icon" type="button" variant="outline">
            <Pencil aria-hidden />
          </Button>
          <Button aria-label={`删除任务 ${name}`} size="icon" type="button" variant="outline">
            <Trash2 aria-hidden />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SchedulerJobSection({ title, jobs }: { title: string; jobs: SchedulerJobItem[] }) {
  return (
    <section className="grid gap-3">
      <div className="flex items-center gap-2">
        <Badge variant={title === "运行中的任务" ? "secondary" : "outline"}>{title}</Badge>
        <span className="text-sm text-muted-foreground">{formatNumber(jobs.length)} 项</span>
      </div>
      {jobs.length > 0 ? (
        <div className="grid grid-cols-3 gap-2 max-2xl:grid-cols-2 max-lg:grid-cols-1">
          {jobs.map((job) => (
            <SchedulerJobCard job={job} key={job.id} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">暂无{title}</CardContent>
        </Card>
      )}
    </section>
  );
}

function clusterDescription(item: ClusterItem, fallback: string): string {
  return item.description || fallback;
}

function clusterEnabledLabel(item: ClusterItem): string {
  return item.is_enabled === false ? "停用" : "启用";
}

function sqlServerAgSummary(item: ClusterItem): string {
  return `${formatNumber(item.availability_group_count)} / contained ${formatNumber(item.contained_ag_count)}`;
}

function sqlServerDatabaseSyncSummary(item: ClusterItem): string {
  const abnormalCount = asNumber((item as Record<string, unknown>).ag_database_sync_abnormal_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return asText(item.last_ag_sync_status, "未同步");
}

function mysqlTopologySummary(item: ClusterItem): string {
  const abnormalCount = asNumber((item as Record<string, unknown>).abnormal_replica_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return asText(item.replication_status, "replication");
}

const sqlServerClusterColumns: ColumnDef<ClusterItem>[] = [
  {
    accessorFn: (item) => `${item.name} ${clusterDescription(item, "SQL Server 群集")}`,
    id: "name",
    header: "群集",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="mt-1 text-xs text-muted-foreground">{clusterDescription(row.original, "SQL Server 群集")}</div>
      </div>
    )
  },
  {
    accessorKey: "domain_name",
    header: "域名",
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.domain_name ?? "-"}</span>
  },
  {
    accessorFn: clusterEnabledLabel,
    id: "is_enabled",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_enabled !== false} />
  },
  {
    accessorKey: "instance_count",
    header: "绑定实例",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    accessorFn: sqlServerAgSummary,
    id: "availability_group_count",
    header: "AG",
    cell: ({ row }) => <span className="font-mono text-xs">{sqlServerAgSummary(row.original)}</span>
  },
  {
    accessorFn: (item) => asText(item.last_ag_sync_status, "未同步"),
    id: "last_ag_sync_status",
    header: "最近 AG 同步",
    cell: ({ row }) => <StatusBadge value={row.original.last_ag_sync_status ?? "未同步"} />
  },
  {
    accessorFn: sqlServerDatabaseSyncSummary,
    id: "ag_database_sync_abnormal_count",
    header: "数据库同步状态",
    cell: ({ row }) => <Badge variant="outline">{sqlServerDatabaseSyncSummary(row.original)}</Badge>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`管理群集 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`AG账户 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <UserCog aria-hidden />
        </Button>
        <Button aria-label={`查看AG状态 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <ChartColumn aria-hidden />
        </Button>
      </div>
    )
  }
];

const mysqlClusterColumns: ColumnDef<ClusterItem>[] = [
  {
    accessorFn: (item) => `${item.name} ${clusterDescription(item, "MySQL replication 群集")}`,
    id: "name",
    header: "群集",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="mt-1 text-xs text-muted-foreground">{clusterDescription(row.original, "MySQL replication 群集")}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => asText((item as Record<string, unknown>).topology_type, "replication"),
    id: "topology_type",
    header: "拓扑"
  },
  {
    accessorFn: clusterEnabledLabel,
    id: "is_enabled",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_enabled !== false} />
  },
  {
    accessorKey: "instance_count",
    header: "绑定实例",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    accessorFn: mysqlTopologySummary,
    id: "abnormal_replica_count",
    header: "主从状态",
    cell: ({ row }) => <Badge variant="outline">{mysqlTopologySummary(row.original)}</Badge>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`管理群集 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`主从状态 ${row.original.name}`} size="icon" type="button" variant="ghost">
          <RotateCcw aria-hidden />
        </Button>
      </div>
    )
  }
];

export function ClustersPage() {
  const query = useQuery({ queryKey: ["read-only", "clusters"], queryFn: () => fetchClustersSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Cluster topology" title="群集管理" description="只读展示 SQL Server AG 与 MySQL 群集首屏拓扑，新增、绑定、同步仍保留在旧版。" legacyHref="/cluster/" />
      <CommandBar>
        <Button disabled>
          <Plus aria-hidden size={16} />
          <span>添加群集</span>
        </Button>
        <Button disabled variant="outline">
          SQL Server
        </Button>
        <Button disabled variant="outline">
          MySQL
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="群集" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <section className="grid grid-cols-2 gap-2 max-xl:grid-cols-1">
            <ListPanel title="SQL Server 群集" description="AG 关系、实例数量、AG 同步和数据库同步状态。" count={snapshot.sqlServer.total}>
              <DataTable
                columns={sqlServerClusterColumns}
                data={snapshot.sqlServer.items}
                filters={[{ columnId: "is_enabled", label: "状态", options: uniqueTextOptions(snapshot.sqlServer.items, clusterEnabledLabel) }]}
                searchPlaceholder="搜索群集名称或描述"
              />
            </ListPanel>
            <ListPanel title="MySQL 群集" description="主从拓扑、绑定实例和复制状态。" count={snapshot.mySql.total}>
              <DataTable
                columns={mysqlClusterColumns}
                data={snapshot.mySql.items}
                filters={[{ columnId: "is_enabled", label: "状态", options: uniqueTextOptions(snapshot.mySql.items, clusterEnabledLabel) }]}
                searchPlaceholder="搜索群集名称或描述"
              />
            </ListPanel>
          </section>
        )}
      </QueryFrame>
    </main>
  );
}

function riskLevelLabel(value: number | undefined): string {
  switch (value) {
    case 1:
      return "1级(最高)";
    case 2:
      return "2级";
    case 3:
      return "3级";
    case 4:
      return "4级(默认)";
    case 5:
      return "5级";
    case 6:
      return "6级(最低)";
    default:
      return "未标记风险";
  }
}

function ruleGroupTitle(dbType: string): string {
  return `${(dbType || "unknown").toUpperCase()} 规则`;
}

function ClassificationList({ items }: { items: Array<{ id: number; code: string; display_name: string; risk_level?: number; is_system?: boolean; rules_count?: number }> }) {
  if (items.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">暂无分类，点击“新建分类”开始配置</p>;
  }
  return (
    <div className="grid gap-2">
      {items.map((item) => (
        <div className="rounded-md border bg-background p-3" key={item.id}>
          <div className="flex items-start justify-between gap-3">
            <div className="grid gap-2">
              <div>
                <div className="font-medium">{item.display_name}</div>
                <div className="font-mono text-xs text-muted-foreground">#{item.code}</div>
              </div>
              <div className="flex flex-wrap gap-1">
                {item.is_system ? <Badge variant="secondary">系统</Badge> : <Badge variant="outline">自定义</Badge>}
                <Badge variant="outline">{riskLevelLabel(item.risk_level)}</Badge>
                <Badge variant="outline">规则 {formatNumber(item.rules_count)}</Badge>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button aria-label={`编辑分类 ${item.display_name}`} size="icon" type="button" variant="ghost">
                <Pencil aria-hidden />
              </Button>
              {!item.is_system ? (
                <Button aria-label={`删除分类 ${item.display_name}`} size="icon" type="button" variant="ghost">
                  <Trash2 aria-hidden />
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function RuleGroups({ rulesByDbType }: { rulesByDbType: Record<string, AccountClassificationRuleItem[]> }) {
  const entries = Object.entries(rulesByDbType).filter(([, rules]) => rules.length > 0);
  if (entries.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">暂无规则，点击“新建规则”开始配置</p>;
  }
  return (
    <div className="grid gap-2">
      {entries.map(([dbType, rules]) => (
        <div className="rounded-md border bg-background p-3" key={dbType}>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{ruleGroupTitle(dbType)}</h3>
            <Badge variant="secondary">{formatNumber(rules.length)}</Badge>
          </div>
          <div className="grid gap-2">
            {rules.map((rule) => (
              <div className="flex items-center justify-between gap-3 rounded-md border p-3 max-sm:grid" key={rule.id}>
                <div className="grid gap-1">
                  <div className="font-medium">{rule.rule_name}</div>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline">{rule.classification_name ?? "未分类"}</Badge>
                    <Badge variant={rule.is_active ? "secondary" : "outline"}>{rule.is_active ? "启用" : "停用"}</Badge>
                    <Badge variant="outline">{formatNumber(rule.matched_accounts_count)}</Badge>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button aria-label={`查看规则 ${rule.rule_name}`} size="icon" type="button" variant="ghost">
                    <ExternalLink aria-hidden />
                  </Button>
                  <Button aria-label={`编辑规则 ${rule.rule_name}`} size="icon" type="button" variant="ghost">
                    <Pencil aria-hidden />
                  </Button>
                  <Button aria-label={`删除规则 ${rule.rule_name}`} size="icon" type="button" variant="ghost">
                    <Trash2 aria-hidden />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AccountClassificationsPage() {
  const query = useQuery({
    queryKey: ["read-only", "account-classifications"],
    queryFn: () => fetchAccountClassificationsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Account taxonomy" title="账户分类" description="只读展示分类、风险等级与规则分布，规则编辑、自动分类仍保留在旧版。" legacyHref="/accounts/classifications/" />
      <CommandBar>
        <Button disabled variant="outline">
          <Zap aria-hidden size={16} />
          <span>自动分类</span>
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="账户分类" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const rules = Object.values(snapshot.rulesByDbType).flat();
          return (
            <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
              <ListPanel
                title="账户分类"
                description="分类展示名、系统标记、风险等级和规则数量。"
                count={snapshot.classifications.length}
                actions={
                  <Button disabled size="sm">
                    <Plus aria-hidden size={16} />
                    <span>新建分类</span>
                  </Button>
                }
              >
                <ClassificationList items={snapshot.classifications} />
              </ListPanel>
              <ListPanel
                title="规则管理"
                description="按数据库类型汇总后的分类规则。"
                count={rules.length}
                actions={
                  <Button disabled size="sm">
                    <Plus aria-hidden size={16} />
                    <span>新建规则</span>
                  </Button>
                }
              >
                <RuleGroups rulesByDbType={snapshot.rulesByDbType} />
              </ListPanel>
            </section>
          );
        }}
      </QueryFrame>
    </main>
  );
}

function buildClassificationChartData(snapshot: ClassificationStatisticsSnapshot): Array<Record<string, string | number>> {
  const firstSeries = snapshot.trends.series[0];
  if (!firstSeries) {
    return [];
  }
  return firstSeries.points.map((point, index) => ({
    label: point.period_start ?? point.period_end ?? String(index + 1),
    value: asNumber(point.value ?? point.value_avg ?? point.value_sum)
  }));
}

function topClassificationStats(stats: ClassificationStatisticsSnapshot["stats"]) {
  return Object.entries(stats)
    .map(([label, value]) => ({
      label,
      value: asNumber(value.total_accounts ?? value.matched_accounts_count ?? value.count ?? value.total)
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

const compactSelectClassName =
  "border-input bg-background ring-offset-background focus-visible:ring-ring h-9 rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

function buildClassificationOptions(snapshot: ClassificationStatisticsSnapshot): Array<{ value: string; label: string }> {
  const options = new Map<string, string>();
  snapshot.trends.series.forEach((series) => {
    options.set(String(series.classification_id), series.classification_name);
  });
  Object.keys(snapshot.stats).forEach((label) => {
    if (![...options.values()].includes(label)) {
      options.set(label, label);
    }
  });
  return [...options.entries()].map(([value, label]) => ({ value, label }));
}

function trendCoverageLabel(snapshot: ClassificationStatisticsSnapshot): string {
  const total = snapshot.trends.buckets.length || snapshot.trends.series[0]?.points.length || 0;
  const covered = snapshot.trends.series[0]?.points.length ?? 0;
  return `覆盖 ${formatNumber(covered)}/${formatNumber(total)} 天`;
}

function ClassificationFilterPanel({ snapshot }: { snapshot: ClassificationStatisticsSnapshot }) {
  const classificationOptions = buildClassificationOptions(snapshot);
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="grid grid-cols-[minmax(12rem,1.3fr)_minmax(8rem,0.7fr)_minmax(8rem,0.7fr)_minmax(12rem,1.3fr)_auto] items-end gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>账户分类</span>
            <select className={compactSelectClassName} defaultValue="">
              <option value="">全部分类</option>
              {classificationOptions.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>统计周期</span>
            <select className={compactSelectClassName} defaultValue="daily">
              <option value="daily">日统计</option>
              <option value="weekly">周统计</option>
              <option value="monthly">月统计</option>
              <option value="quarterly">季统计</option>
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>数据库类型</span>
            <select className={compactSelectClassName} defaultValue="">
              <option value="">全部类型</option>
              <option value="mysql">MySQL</option>
              <option value="postgresql">PostgreSQL</option>
              <option value="sqlserver">SQL Server</option>
              <option value="oracle">Oracle</option>
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>实例/AG</span>
            <select className={compactSelectClassName} defaultValue="" disabled>
              <option value="">所有实例/AG</option>
            </select>
          </label>
          <div className="flex gap-2">
            <Button variant="outline" disabled>
              应用
            </Button>
            <Button variant="ghost" disabled>
              重置
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ClassificationRulesListPanel() {
  return (
    <ListPanel
      title="规则列表"
      description="选择分类后加载规则列表与规则趋势。"
      actions={<Badge variant="outline">最新周期</Badge>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-[minmax(0,1fr)_9rem] gap-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>搜索规则名/备注</span>
            <input className="border-input bg-background h-9 rounded-md border px-3 py-1 text-sm" type="search" readOnly />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>状态</span>
            <select className={compactSelectClassName} defaultValue="active">
              <option value="active">启用</option>
              <option value="archived">已归档</option>
              <option value="all">全部</option>
            </select>
          </label>
        </div>
        <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
          选择分类后加载规则列表与规则趋势
        </div>
      </div>
    </ListPanel>
  );
}

export function ClassificationStatisticsPage() {
  const query = useQuery({
    queryKey: ["read-only", "classification-statistics"],
    queryFn: () => fetchClassificationStatisticsSnapshot()
  });
  const chartConfig = { value: { label: "匹配账户", color: "var(--chart-1)" } } satisfies ChartConfig;

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Classification analytics" title="分类统计" description="只读展示账户分类统计、规则列表入口和最近周期趋势，写操作仍保留在旧版。" legacyHref="/accounts/statistics/classifications" />
      <CommandBar>
        <Button variant="outline" onClick={() => void query.refetch()}>
          <RotateCcw aria-hidden size={16} />
          <span>刷新</span>
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="分类统计" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const chartData = buildClassificationChartData(snapshot);
          const topStats = topClassificationStats(snapshot.stats);
          const coverageLabel = trendCoverageLabel(snapshot);
          return (
            <>
              <ClassificationFilterPanel snapshot={snapshot} />
              <MetricGrid
                label="分类统计指标"
                metrics={[
                  { label: "统计分类", value: Object.keys(snapshot.stats).length, icon: ChartColumn },
                  { label: "趋势序列", value: snapshot.trends.series.length, icon: Activity },
                  { label: "周期数量", value: snapshot.trends.buckets.length || chartData.length, icon: Clock },
                  { label: "Top 命中", value: topStats[0]?.value ?? 0, detail: topStats[0]?.label, icon: Tags }
                ]}
              />
              <section className="grid grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)] gap-2 max-xl:grid-cols-1">
                <ClassificationRulesListPanel />
                <div className="grid gap-2">
                  <Card>
                    <CardHeader className="flex flex-row items-start justify-between gap-3">
                      <div>
                        <CardTitle>分类趋势（去重账号数）</CardTitle>
                        <CardDescription>分类趋势面积图</CardDescription>
                      </div>
                      <Badge variant="outline">{coverageLabel}</Badge>
                    </CardHeader>
                    <CardContent>
                      {snapshot.trends.series[0]?.classification_name ? <div className="mb-2 text-sm font-medium">{snapshot.trends.series[0].classification_name}</div> : null}
                      {chartData.length > 0 ? (
                        <ChartContainer config={chartConfig} className="h-[240px] w-full">
                          <AreaChart accessibilityLayer data={chartData} margin={{ left: -12, right: 12, top: 12, bottom: 0 }}>
                            <defs>
                              <linearGradient id="classificationTrendFill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-value)" stopOpacity={0.34} />
                                <stop offset="95%" stopColor="var(--color-value)" stopOpacity={0.04} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid vertical={false} />
                            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Area dataKey="value" name="匹配账户" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill="url(#classificationTrendFill)" />
                          </AreaChart>
                        </ChartContainer>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂无趋势数据</p>
                      )}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="flex flex-row items-start justify-between gap-3">
                      <div>
                        <CardTitle>规则贡献（当前周期）</CardTitle>
                        <CardDescription>规则之间允许重叠，当前只读首屏默认展示选择分类后的贡献图。</CardDescription>
                      </div>
                      <Badge variant="outline">{coverageLabel}</Badge>
                    </CardHeader>
                    <CardContent className="grid gap-3">
                      <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
                        选择分类后展示规则贡献
                      </div>
                      <p className="text-sm text-muted-foreground">说明：规则之间允许重叠，“各规则之和”不等于分类去重总数。</p>
                    </CardContent>
                  </Card>
                </div>
              </section>
              <ListPanel title="分类排行" description="按当前统计快照展示 Top 分类。" count={topStats.length}>
                <Table>
                  <TableHeader className="text-xs">
                    <TableRow>
                      <TableHead>分类</TableHead>
                      <TableHead>匹配账户</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topStats.length === 0 ? <EmptyRows colSpan={2} /> : null}
                    {topStats.map((item) => (
                      <TableRow key={item.label}>
                        <TableCell className="font-medium">{item.label}</TableCell>
                        <TableCell className="font-mono text-xs">{formatNumber(item.value)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ListPanel>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}

export function SchedulerPage() {
  const query = useQuery({ queryKey: ["read-only", "scheduler"], queryFn: () => fetchSchedulerSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation jobs" title="定时任务" description="只读展示调度任务和运行状态，暂停、恢复、立即执行仍保留在旧版。" legacyHref="/scheduler/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="定时任务" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="定时任务指标"
              metrics={[
                { label: "任务总数", value: snapshot.jobs.length, icon: Clock },
                { label: "运行任务", value: snapshot.jobs.filter((job) => isRunningState(job.state)).length, icon: Activity },
                { label: "内置任务", value: snapshot.jobs.filter((job) => job.is_builtin).length, icon: Settings },
                { label: "可配置", value: snapshot.jobs.filter((job) => job.trigger_type).length, icon: ListChecks }
              ]}
            />
            <ListPanel
              title="任务卡片"
              description="按旧版运行状态分组展示任务名称、运行时间、任务 ID、触发器参数和操作。"
              count={snapshot.jobs.length}
              actions={
                <Button size="sm" type="button" variant="outline">
                  <RotateCcw aria-hidden />
                  重新初始化任务
                </Button>
              }
            >
              <div className="grid gap-6">
                <SchedulerJobSection title="运行中的任务" jobs={snapshot.jobs.filter((job) => isRunningState(job.state))} />
                <SchedulerJobSection title="已暂停的任务" jobs={snapshot.jobs.filter((job) => !isRunningState(job.state))} />
              </div>
            </ListPanel>
          </>
        )}
      </QueryFrame>
    </main>
  );
}

export function SyncSessionsPage() {
  const query = useQuery({ queryKey: ["read-only", "sync-sessions"], queryFn: () => fetchSyncSessionsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation sessions" title="会话中心" description="只读展示同步会话首屏，取消和详情时间线仍保留在旧版。" legacyHref="/history/sessions/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="会话中心" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="会话指标"
              metrics={[
                { label: "会话总数", value: snapshot.total, icon: ListChecks },
                { label: "当前页", value: `${snapshot.page}/${snapshot.pages ?? 1}`, icon: Clock },
                { label: "运行中", value: snapshot.items.filter((item) => item.status === "running").length, icon: Activity },
                { label: "失败实例", value: snapshot.items.reduce((sum, item) => sum + (item.failed_instances ?? 0), 0), icon: AlertCircle }
              ]}
            />
            <ListPanel title="同步会话" description="最近同步会话首屏列表。" count={snapshot.total}>
              <DataTable
                columns={syncSessionColumns}
                data={snapshot.items}
                filters={[
                  { columnId: "trigger_source", label: "来源", options: uniqueTextOptions(snapshot.items, (item) => syncSource(item)) },
                  { columnId: "task_category", label: "分类", options: uniqueTextOptions(snapshot.items, (item) => syncCategory(item)) },
                  { columnId: "status", label: "状态", options: uniqueTextOptions(snapshot.items, (item) => item.status) }
                ]}
                searchPlaceholder="搜索运行 ID、任务或来源"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
    </main>
  );
}

export function UsersPage() {
  const query = useQuery({ queryKey: ["read-only", "users"], queryFn: () => fetchUsersSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Access control" title="用户管理" description="只读展示用户、角色与启用状态，新增、编辑、删除仍保留在旧版。" legacyHref="/users/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="用户管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="用户指标"
              metrics={[
                { label: "用户总数", value: snapshot.stats.total, icon: UserCog },
                { label: "活跃用户", value: snapshot.stats.active, icon: Activity },
                { label: "管理员", value: snapshot.stats.admin, icon: KeyRound },
                { label: "普通用户", value: snapshot.stats.user, icon: UserCog }
              ]}
            />
            <ListPanel
              title="用户列表"
              description={`每页 ${formatNumber(snapshot.list.limit)} 条`}
              count={snapshot.list.total}
              actions={
                <Button size="sm" type="button">
                  <Plus aria-hidden />
                  新建用户
                </Button>
              }
            >
              <DataTable
                columns={userColumns}
                data={snapshot.list.items}
                filters={[
                  {
                    columnId: "role",
                    label: "角色",
                    options: [
                      { label: "管理员", value: "admin" },
                      { label: "普通用户", value: "user" },
                      { label: "查看者", value: "viewer" }
                    ]
                  },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索用户名或邮箱"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
    </main>
  );
}

function SettingsCard({ title, description, status, children }: { title: string; description: string; status?: string | boolean; children: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        {status !== undefined ? <StatusBadge value={status} /> : null}
      </CardHeader>
      <CardContent className="grid gap-2 text-sm">{children}</CardContent>
    </Card>
  );
}

function settingsEnabledCount(snapshot: SettingsSnapshot): number {
  const alertSettings = snapshot.alerts.settings ?? {};
  return [
    snapshot.alerts.smtp_ready,
    alertSettings.global_enabled,
    snapshot.jumpserver.provider_ready,
    snapshot.veeam.provider_ready,
    snapshot.adDomains.configs.some((item) => item.is_enabled === true)
  ].filter(Boolean).length;
}

function ReadonlyField({ label, value }: { label: string; value?: unknown }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      <Input readOnly value={asText(value)} />
    </label>
  );
}

function ToggleRow({ label, checked }: { label: string; checked: unknown }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 text-sm">
      <span>{label}</span>
      <StatusBadge value={checked === true} />
    </div>
  );
}

function SettingsSubsection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3 rounded-md border bg-secondary/20 p-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export function SettingsPage() {
  const query = useQuery({ queryKey: ["read-only", "settings"], queryFn: () => fetchSettingsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="System integrations" title="系统设置" description="只读展示集成源、告警和风险规则配置状态，保存、测试、同步动作仍保留在旧版。" legacyHref="/admin/system-settings" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="系统设置" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const alertSettings = snapshot.alerts.settings ?? {};
          const veeamSources = Array.isArray(snapshot.veeam.sources) ? snapshot.veeam.sources : [];
          const jumpserverBinding = (snapshot.jumpserver.binding as Record<string, unknown> | undefined) ?? {};
          const jumpserverCredentials = Array.isArray(snapshot.jumpserver.api_credentials) ? snapshot.jumpserver.api_credentials : [];
          const veeamCredentials = Array.isArray(snapshot.veeam.veeam_credentials) ? snapshot.veeam.veeam_credentials : [];
          const firstVeeamSource = (veeamSources[0] as Record<string, unknown> | undefined) ?? {};
          const firstAdDomain = snapshot.adDomains.configs[0] ?? {};
          const adControllers = Array.isArray(firstAdDomain.domain_controllers) ? firstAdDomain.domain_controllers.join(", ") : firstAdDomain.domain_controllers;
          return (
            <>
              <MetricGrid
                label="系统设置指标"
                metrics={[
                  { label: "启用配置", value: settingsEnabledCount(snapshot), icon: Settings },
                  { label: "风险规则", value: snapshot.riskRules.length, icon: AlertCircle },
                  { label: "AD 域", value: snapshot.adDomains.configs.length, icon: UserCog },
                  { label: "Veeam 源", value: veeamSources.length, icon: Database }
                ]}
              />
              <section className="grid grid-cols-[16rem_minmax(0,1fr)] gap-2 max-xl:grid-cols-1">
                <Card className="self-start">
                  <CardHeader>
                    <CardTitle>设置模块</CardTitle>
                    <CardDescription>旧版模块导航</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-2">
                    {["告警设置", "风险规则", "JumpServer", "Veeam", "AD 设置"].map((label) => (
                      <Button className="justify-start" key={label} type="button" variant="ghost">
                        {label}
                      </Button>
                    ))}
                  </CardContent>
                </Card>
                <div className="grid gap-2">
                  <SettingsCard title="邮件告警" description="SMTP、飞书投递和告警规则。" status={snapshot.alerts.smtp_ready}>
                    <SettingsSubsection title="发送设置">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="投递通道" value={snapshot.alerts.smtp_ready ? "SMTP" : "未就绪"} />
                        <ReadonlyField label="飞书机器人 URL" value={alertSettings.feishu_webhook_url} />
                        <ReadonlyField label="收件人" value={alertSettings.recipients} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="启用邮件告警" checked={alertSettings.global_enabled} />
                        <ToggleRow label="发送到飞书" checked={alertSettings.feishu_enabled} />
                        <ToggleRow label="共享收件人列表" checked={alertSettings.shared_recipients_enabled} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" type="button">发送测试邮件</Button>
                        <Button size="sm" type="button" variant="outline">发送飞书测试</Button>
                        <Button size="sm" type="button">保存配置</Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="规则设置">
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="容量异常增长" checked={alertSettings.database_capacity_enabled} />
                        <ToggleRow label="账户同步异常" checked={alertSettings.account_sync_failure_enabled} />
                        <ToggleRow label="数据库同步异常" checked={alertSettings.database_sync_failure_enabled} />
                        <ToggleRow label="群集状态" checked={alertSettings.cluster_status_enabled} />
                        <ToggleRow label="高权限账户" checked={alertSettings.privileged_account_enabled} />
                        <ToggleRow label="备份告警" checked={alertSettings.backup_issue_enabled} />
                      </div>
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="风险规则" description="仅影响风险中心展示。" status={snapshot.riskRules.some((rule) => rule.enabled === true)}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm text-muted-foreground">仅影响风险中心展示</span>
                      <Button size="sm" type="button">保存规则</Button>
                    </div>
                    {snapshot.riskRules.length > 0 ? (
                      snapshot.riskRules.map((rule) => (
                        <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(rule.rule_key)}>
                          <span>{asText(rule.rule_key)}</span>
                          <Badge variant={statusVariant(Boolean(rule.enabled))}>{asText(rule.severity, statusLabel(Boolean(rule.enabled)))}</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-muted-foreground">暂无风险规则</p>
                    )}
                  </SettingsCard>

                  <SettingsCard title="JumpServer 数据源设置" description="绑定资产数据源、API 凭据和运行状态。" status={Boolean(snapshot.jumpserver.provider_ready)}>
                    <SettingsSubsection title="绑定配置">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="JumpServer URL" value={endpointHost(jumpserverBinding.base_url)} />
                        <ReadonlyField label="组织 ID" value={jumpserverBinding.org_id} />
                        <ReadonlyField label="SSL 证书验证" value={statusLabel(jumpserverBinding.verify_ssl as boolean | undefined)} />
                      </div>
                      <span className="font-mono text-sm">{endpointHost(jumpserverBinding.base_url)}</span>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" type="button">保存绑定</Button>
                        <Button size="sm" type="button" variant="outline">解绑数据源</Button>
                        <Button size="sm" type="button">同步 JumpServer 资源</Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="API 凭据">
                      <p className="text-sm text-muted-foreground">{jumpserverCredentials.length > 0 ? `${formatNumber(jumpserverCredentials.length)} 条凭据` : "暂无 API 凭据"}</p>
                    </SettingsSubsection>
                    <SettingsSubsection title="运行状态">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="Provider" value={statusLabel(Boolean(snapshot.jumpserver.provider_ready))} />
                        <ReadonlyField label="当前绑定" value={endpointHost(jumpserverBinding.base_url)} />
                        <ReadonlyField label="最近同步" value={snapshot.jumpserver.last_sync_at} />
                      </div>
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="Veeam 数据源设置" description="备份平台数据源配置。" status={Boolean(snapshot.veeam.provider_ready)}>
                    <SettingsSubsection title="新增数据源">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="数据源名称" value={firstVeeamSource.name} />
                        <ReadonlyField label="Veeam 凭据" value={veeamCredentials.length > 0 ? `${formatNumber(veeamCredentials.length)} 条` : "-"} />
                        <ReadonlyField label="Veeam IP" value={firstVeeamSource.server_host} />
                        <ReadonlyField label="端口" value={firstVeeamSource.server_port} />
                        <ReadonlyField label="API 版本" value={firstVeeamSource.api_version} />
                        <ReadonlyField label="域名列表" value={firstVeeamSource.domains} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" type="button">保存数据源</Button>
                        <Button size="sm" type="button" variant="outline">删除数据源</Button>
                        <Badge variant="outline">新增模式</Badge>
                        <Button size="sm" type="button">同步 Veeam 备份</Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="数据源列表">
                      {veeamSources.length > 0 ? (
                        veeamSources.map((source) => {
                          const record = source as Record<string, unknown>;
                          return (
                            <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(record.name ?? record.id)}>
                              <span>{asText(record.name)}</span>
                              <span className="font-mono text-xs text-muted-foreground">{asText(record.server_host)}:{asText(record.server_port)}</span>
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-muted-foreground">暂无 Veeam 数据源</p>
                      )}
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="AD 设置" description="AD 域账户同步配置。" status={snapshot.adDomains.configs.some((item) => item.is_enabled === true)}>
                    <SettingsSubsection title="新增 AD 域">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="域名" value={firstAdDomain.name} />
                        <ReadonlyField label="NetBIOS 名称" value={firstAdDomain.netbios_name} />
                        <ReadonlyField label="LDAP 端口" value={firstAdDomain.ldap_port} />
                        <ReadonlyField label="域控地址" value={adControllers} />
                        <ReadonlyField label="Base DN" value={firstAdDomain.base_dn} />
                        <ReadonlyField label="LDAP 凭据" value={firstAdDomain.credential_id} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="使用 SSL" checked={firstAdDomain.use_ssl ?? firstAdDomain.ldap_port === 636} />
                        <ToggleRow label="证书验证" checked={firstAdDomain.verify_ssl} />
                        <ToggleRow label="启用同步" checked={firstAdDomain.is_enabled} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" type="button">保存 AD 域</Button>
                        <Button size="sm" type="button" variant="outline">删除配置</Button>
                        <Button size="sm" type="button">AD 域账户同步</Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="AD 域列表">
                      {snapshot.adDomains.configs.length > 0 ? (
                        snapshot.adDomains.configs.map((config) => (
                          <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(config.id ?? config.name)}>
                            <span>{asText(config.name)}</span>
                            <StatusBadge value={config.is_enabled === true} />
                          </div>
                        ))
                      ) : (
                        <p className="text-muted-foreground">暂无 AD 域配置</p>
                      )}
                    </SettingsSubsection>
                  </SettingsCard>
                </div>
              </section>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}

export function CredentialsPage() {
  const query = useQuery({ queryKey: ["read-only", "credentials"], queryFn: () => fetchCredentialsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Credential vault" title="凭据管理" description="只读展示凭据类型、数据库类型和引用数量，新增、编辑、测试连接仍保留在旧版。" legacyHref="/credentials/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="凭据管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="凭据指标"
              metrics={[
                { label: "凭据总数", value: snapshot.total, icon: KeyRound },
                { label: "启用凭据", value: snapshot.items.filter((item) => item.is_active !== false).length, icon: Activity },
                { label: "数据库凭据", value: snapshot.items.filter((item) => item.credential_type === "database").length, icon: Database },
                { label: "引用实例", value: snapshot.items.reduce((sum, item) => sum + (item.instance_count ?? 0), 0), icon: Layers3 }
              ]}
            />
            <ListPanel
              title="凭据列表"
              description={`每页 ${formatNumber(snapshot.limit)} 条`}
              count={snapshot.total}
              actions={
                <Button size="sm" type="button">
                  <Plus aria-hidden />
                  新建凭据
                </Button>
              }
            >
              <DataTable
                columns={credentialColumns}
                data={snapshot.items}
                filters={[
                  { columnId: "credential_type", label: "凭据类型", options: uniqueTextOptions(snapshot.items, (item) => item.credential_type) },
                  { columnId: "db_type", label: "数据库类型", options: uniqueTextOptions(snapshot.items, (item) => item.db_type) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索凭据、账号或数据库类型"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
    </main>
  );
}

export function TagsPage() {
  const query = useQuery({ queryKey: ["read-only", "tags"], queryFn: () => fetchTagsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Resource tags" title="标签管理" description="只读展示标签、分类和实例引用数量，新增、删除、批量绑定仍保留在旧版。" legacyHref="/tags/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="标签管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="标签指标"
              metrics={[
                { label: "全部标签", value: snapshot.list.stats.total, icon: Tags },
                { label: "启用率", value: formatPercent(snapshot.list.stats.active, snapshot.list.stats.total), detail: `${formatNumber(snapshot.list.stats.active)} 个启用`, icon: Activity },
                { label: "停用率", value: formatPercent(snapshot.list.stats.inactive, snapshot.list.stats.total), detail: `${formatNumber(snapshot.list.stats.inactive)} 个停用`, icon: AlertCircle },
                { label: "标签分类", value: snapshot.list.stats.category_count, detail: `${snapshot.categories.length} 个分类`, icon: Boxes }
              ]}
            />
            <ListPanel
              title="标签列表"
              description={`分类: ${snapshot.categories.join(", ") || "-"}`}
              count={snapshot.list.total}
              actions={
                <>
                  <Button size="sm" type="button">
                    <Plus aria-hidden />
                    新建标签
                  </Button>
                  <Button size="sm" type="button" variant="outline">
                    批量分配
                  </Button>
                </>
              }
            >
              <DataTable
                columns={tagColumns}
                data={snapshot.list.items}
                filters={[
                  { columnId: "category", label: "分类", options: uniqueTextOptions(snapshot.list.items, (item) => item.category) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索标签、编码或分类"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
    </main>
  );
}

function PartitionsTable({ items }: { items: PartitionItem[] }) {
  return (
    <Table className="min-w-[52rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["分区", "表", "类型", "大小", "记录", "状态"].map((label) => (
            <TableHead key={label}>{label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow key={item.name}>
            <TableCell className="font-medium">{item.display_name ?? item.name}</TableCell>
            <TableCell>{item.table ?? "-"}</TableCell>
            <TableCell>{item.table_type ?? "-"}</TableCell>
            <TableCell className="font-mono text-xs">{item.size ?? "-"}</TableCell>
            <TableCell className="font-mono text-xs">{formatNumber(item.record_count)}</TableCell>
            <TableCell>
              <span className="text-xs text-muted-foreground">{item.status ? `分区 ${statusLabel(item.status)}` : "-"}</span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function PartitionsPage() {
  const query = useQuery({ queryKey: ["read-only", "partitions"], queryFn: () => fetchPartitionsSnapshot() });
  const chartConfig = { value: { label: "分区指标", color: "var(--chart-2)" } } satisfies ChartConfig;

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Storage partitions" title="分区管理" description="只读展示分区健康状态、核心指标和分区列表，创建和清理动作仍保留在旧版。" legacyHref="/partition/" />
      <CommandBar>
        <Button type="button">
          <Plus aria-hidden />
          创建分区
        </Button>
        <Button type="button" variant="outline">
          <Trash2 aria-hidden />
          清理旧分区
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="分区管理" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const status = snapshot.status.data;
          const metricValues = snapshot.coreMetrics.datasets[0]?.data ?? [];
          const chartData = snapshot.coreMetrics.labels.map((label, index) => ({ label, value: metricValues[index] ?? 0 }));
          return (
            <>
              <MetricGrid
                label="分区指标"
                metrics={[
                  { label: "分区总数", value: status.total_partitions ?? snapshot.list.total, icon: Boxes },
                  { label: "总大小", value: status.total_size ?? "-", icon: Database },
                  { label: "总记录数", value: status.total_records ?? 0, icon: ListChecks },
                  { label: "健康状态", value: statusLabel(status.status), detail: "数据库连接", icon: Activity }
                ]}
              />
              <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
                <Card>
                  <CardHeader className="flex flex-row items-start justify-between gap-3">
                    <div>
                      <CardTitle>核心指标趋势</CardTitle>
                      <CardDescription>最近7天的核心指标统计</CardDescription>
                    </div>
                    <StatusBadge value={status.status} />
                  </CardHeader>
                  <CardContent className="grid gap-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                      <span>数据库连接</span>
                      <span>{snapshot.status.timestamp ?? "-"}</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {["日", "周", "月", "季"].map((period, index) => (
                        <Button key={period} size="sm" type="button" variant={index === 0 ? "default" : "outline"}>
                          {period}
                        </Button>
                      ))}
                    </div>
                    {chartData.length > 0 ? (
                      <ChartContainer config={chartConfig} className="h-[220px] w-full">
                        <AreaChart accessibilityLayer data={chartData} margin={{ left: -12, right: 12, top: 12, bottom: 0 }}>
                          <CartesianGrid vertical={false} />
                          <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                          <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                          <ChartTooltip content={<ChartTooltipContent />} />
                          <Area dataKey="value" name="分区指标" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill="var(--color-value)" fillOpacity={0.16} />
                        </AreaChart>
                      </ChartContainer>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无核心指标</p>
                    )}
                  </CardContent>
                </Card>
                <ListPanel title="分区列表" description={`每页 ${formatNumber(snapshot.list.limit)} 条`} count={snapshot.list.total}>
                  <PartitionsTable items={snapshot.list.items} />
                </ListPanel>
              </section>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}
