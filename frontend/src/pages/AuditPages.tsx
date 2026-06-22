import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { AlertCircle, AlertTriangle, CheckCircle2, ExternalLink, FileText, ShieldAlert, XCircle } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import {
  fetchAccountChangeLogDetail,
  fetchAccountChangeLogsSnapshot,
  fetchHistoryLogDetail,
  fetchHistoryLogsSnapshot,
  type AccountChangeLogDetail,
  type AccountChangeLogItem,
  type AccountChangeLogsSnapshot,
  type HistoryLogDetail,
  type HistoryLogItem,
  type HistoryLogsSnapshot
} from "@/api/audit";
import { DataTable } from "@/components/shared/DataTable";
import { SelectControl, TruncatedTooltip } from "@/components/shared/FormControls";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";

type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof FileText;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatDecimal(value: number | undefined | null): string {
  return (value ?? 0).toFixed(1).replace(/\.0$/, "");
}

function formatPercent(value: number | undefined | null): string {
  return `${formatDecimal(value)}%`;
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

function statusVariant(value: string | undefined): "default" | "secondary" | "destructive" | "outline" {
  const normalized = value?.toLowerCase() ?? "";
  if (["error", "critical", "failed", "fail"].includes(normalized)) {
    return "destructive";
  }
  if (["warning", "warn"].includes(normalized)) {
    return "outline";
  }
  if (["success", "info", "ok"].includes(normalized)) {
    return "secondary";
  }
  return "outline";
}

function PageHeader({
  title,
  legacyHref
}: {
  title: string;
  legacyHref: string;
}) {
  return (
    <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
      <div>
        <h1 className="font-display text-2xl leading-none tracking-normal">{title}</h1>
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

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="审计指标">
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
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="审计加载中">
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
      <AlertDescription>审计数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function ListFrame({ title, total, children }: { title: string; total: number; children: ReactNode }) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-sm:grid">
          <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
          <Badge variant="secondary">共 {formatNumber(total)} 条</Badge>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function QueryPage<TSnapshot>({
  snapshot,
  isLoading,
  isError,
  onRetry,
  children
}: {
  snapshot: TSnapshot | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  children: (snapshot: TSnapshot) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {snapshot ? children(snapshot) : null}
    </>
  );
}

function TimeRangeFilter() {
  return (
    <label className="grid gap-1.5 text-sm font-medium text-foreground">
      <span>时间范围</span>
      <SelectControl
        label="时间范围"
        defaultValue="1d"
        options={[
          { label: "最近 1 小时", value: "1h" },
          { label: "最近 24 小时", value: "1d" },
          { label: "最近 7 天", value: "1w" },
          { label: "最近 30 天", value: "1m" },
          { label: "全部", value: "all" }
        ]}
      />
    </label>
  );
}

function isEmptyDetailValue(value: unknown): boolean {
  if (value === null || value === undefined || value === "") {
    return true;
  }
  if (Array.isArray(value)) {
    return value.length === 0;
  }
  if (typeof value === "object") {
    return Object.keys(value).length === 0;
  }
  return false;
}

function JsonBlock({ value }: { value: unknown }) {
  if (isEmptyDetailValue(value)) {
    return <span className="text-muted-foreground">-</span>;
  }

  return (
    <pre className="max-h-64 overflow-auto rounded-md border bg-secondary/30 p-3 font-mono text-xs whitespace-pre-wrap">
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

function DetailText({ value }: { value: unknown }) {
  if (isEmptyDetailValue(value)) {
    return <span className="text-muted-foreground">-</span>;
  }
  return <span>{String(value)}</span>;
}

function DetailLoading() {
  return (
    <div className="grid gap-3">
      <Skeleton className="h-6 w-40" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

function HistoryLogDetailDialog({
  logId,
  onOpenChange,
  open
}: {
  logId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const detailQuery = useQuery<HistoryLogDetail>({
    enabled: open && logId !== null,
    queryKey: ["audit", "history-log-detail", logId],
    queryFn: () => {
      if (logId === null) {
        throw new Error("Missing log id");
      }
      return fetchHistoryLogDetail(logId);
    }
  });
  const log = detailQuery.data?.log;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>日志详情 #{logId ?? ""}</DialogTitle>
          <DialogDescription>系统日志原始消息、堆栈和上下文。</DialogDescription>
        </DialogHeader>
        {detailQuery.isLoading ? <DetailLoading /> : null}
        {detailQuery.isError ? (
          <Alert variant="destructive">
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>日志详情加载失败</AlertDescription>
          </Alert>
        ) : null}
        {log ? (
          <div className="grid gap-4">
            <dl className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
              <DetailField label="时间">
                <DetailText value={log.timestamp_display || log.timestamp} />
              </DetailField>
              <DetailField label="级别">
                <Badge variant={statusVariant(log.level)}>{log.level}</Badge>
              </DetailField>
              <DetailField label="模块">
                <Badge variant="outline">{log.module}</Badge>
              </DetailField>
              <DetailField label="日志 ID">
                <span className="font-mono">#{log.id}</span>
              </DetailField>
            </dl>
            <DetailField label="消息">
              <DetailText value={log.message} />
            </DetailField>
            <DetailField label="堆栈">
              {log.traceback ? (
                <pre className="max-h-64 overflow-auto rounded-md border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{log.traceback}</pre>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </DetailField>
            <DetailField label="上下文">
              <JsonBlock value={log.context} />
            </DetailField>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function AccountChangeLogDetailDialog({
  logId,
  onOpenChange,
  open
}: {
  logId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const detailQuery = useQuery<AccountChangeLogDetail>({
    enabled: open && logId !== null,
    queryKey: ["audit", "account-change-log-detail", logId],
    queryFn: () => {
      if (logId === null) {
        throw new Error("Missing account change log id");
      }
      return fetchAccountChangeLogDetail(logId);
    }
  });
  const log = detailQuery.data?.log;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>变更详情 #{logId ?? ""}</DialogTitle>
          <DialogDescription>账户变更摘要、实例信息和差异明细。</DialogDescription>
        </DialogHeader>
        {detailQuery.isLoading ? <DetailLoading /> : null}
        {detailQuery.isError ? (
          <Alert variant="destructive">
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>变更详情加载失败</AlertDescription>
          </Alert>
        ) : null}
        {log ? (
          <div className="grid gap-4">
            <dl className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
              <DetailField label="账号">
                <DetailText value={log.username} />
              </DetailField>
              <DetailField label="实例">
                <div className="grid gap-1">
                  <DetailText value={log.instance_name} />
                  <span className="font-mono text-xs text-muted-foreground">{log.instance_host || "-"}</span>
                </div>
              </DetailField>
              <DetailField label="数据库类型">
                <Badge variant="outline">{log.db_type ? log.db_type.toUpperCase() : "-"}</Badge>
              </DetailField>
              <DetailField label="变更类型">
                <Badge variant="secondary">{log.change_type}</Badge>
              </DetailField>
              <DetailField label="状态">
                <Badge variant={statusVariant(log.status)}>{log.status}</Badge>
              </DetailField>
              <DetailField label="会话 ID">
                <span className="font-mono text-xs">{log.session_id || "-"}</span>
              </DetailField>
            </dl>
            <DetailField label="摘要">
              <DetailText value={log.message} />
            </DetailField>
            <DetailField label="权限差异">
              <JsonBlock value={log.privilege_diff} />
            </DetailField>
            <DetailField label="其他差异">
              <JsonBlock value={log.other_diff} />
            </DetailField>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function createHistoryLogColumns(onViewDetail: (logId: number) => void): ColumnDef<HistoryLogItem>[] {
  return [
    {
      accessorKey: "timestamp_display",
      header: "时间",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.timestamp_display || row.original.timestamp}</span>
    },
    {
      accessorKey: "level",
      header: "级别",
      cell: ({ row }) => <Badge variant={statusVariant(row.original.level)}>{row.original.level}</Badge>
    },
    {
      accessorKey: "module",
      header: "模块",
      cell: ({ row }) => <Badge variant="outline">{row.original.module}</Badge>
    },
    {
      accessorKey: "message",
      header: "消息",
      cell: ({ row }) => (
        <TruncatedTooltip className="max-w-xl font-medium" content={row.original.message}>
          {row.original.message}
        </TruncatedTooltip>
      )
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <Button aria-label={`查看详情 ${row.original.id}`} onClick={() => onViewDetail(row.original.id)} size="sm" type="button" variant="outline">
          查看详情
        </Button>
      )
    }
  ];
}

function createAccountChangeLogColumns(onViewDetail: (logId: number) => void): ColumnDef<AccountChangeLogItem>[] {
  return [
    {
      accessorKey: "change_time",
      header: "时间",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.change_time}</span>
    },
    {
      accessorKey: "db_type",
      header: "数据库类型",
      cell: ({ row }) => <Badge variant="outline">{row.original.db_type.toUpperCase()}</Badge>
    },
    {
      accessorKey: "instance_name",
      header: "实例",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <span className="font-medium">{row.original.instance_name || "-"}</span>
          <span className="font-mono text-xs text-muted-foreground">{row.original.instance_host || "-"}</span>
        </div>
      )
    },
    {
      accessorKey: "username",
      header: "账号",
      cell: ({ row }) => <span className="font-medium">{row.original.username}</span>
    },
    {
      accessorKey: "change_type",
      header: "类型",
      cell: ({ row }) => <Badge variant="secondary">{row.original.change_type}</Badge>
    },
    {
      accessorKey: "message",
      header: "摘要",
      cell: ({ row }) => (
        <TruncatedTooltip className="max-w-xl" content={row.original.message ?? ""}>
          {row.original.message || "-"}
        </TruncatedTooltip>
      )
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <Button aria-label={`查看详情 ${row.original.id}`} onClick={() => onViewDetail(row.original.id)} size="sm" type="button" variant="outline">
          查看详情
        </Button>
      )
    }
  ];
}

export function HistoryLogsPage() {
  const [selectedHistoryLogId, setSelectedHistoryLogId] = useState<number | null>(null);
  const columns = useMemo(() => createHistoryLogColumns(setSelectedHistoryLogId), [setSelectedHistoryLogId]);
  const logsQuery = useQuery({
    queryKey: ["audit", "history-logs", 1, 200, 24],
    queryFn: () => fetchHistoryLogsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        title="日志中心"
        legacyHref="/history/logs/"
      />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: HistoryLogsSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                {
                  label: "总日志数",
                  value: snapshot.statistics.total_logs,
                  detail: `Top 模块 ${snapshot.statistics.top_modules[0]?.module ?? "-"} · ${formatNumber(snapshot.statistics.top_modules[0]?.count)} 条 · 24h`,
                  icon: FileText
                },
                {
                  label: "错误日志",
                  value: snapshot.statistics.error_count,
                  detail: `错误率 ${formatPercent(snapshot.statistics.error_rate)} · 严重 ${formatNumber(snapshot.statistics.critical_count)} · ${formatDecimal(snapshot.statistics.error_count / 24)}/小时`,
                  icon: XCircle
                },
                {
                  label: "警告日志",
                  value: snapshot.statistics.warning_count,
                  detail: `占比 ${formatPercent(snapshot.statistics.total_logs > 0 ? (snapshot.statistics.warning_count / snapshot.statistics.total_logs) * 100 : 0)} · ${formatDecimal(snapshot.statistics.warning_count / 24)}/小时`,
                  icon: AlertTriangle
                },
                { label: "信息日志", value: snapshot.statistics.info_count, detail: `调试 ${formatNumber(snapshot.statistics.debug_count)}`, icon: ShieldAlert }
              ]}
            />
            <ListFrame title="日志列表" total={snapshot.list.total}>
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  { columnId: "level", label: "级别", options: uniqueTextOptions(snapshot.list.items, (item) => item.level) },
                  { columnId: "module", label: "模块", options: uniqueTextOptions(snapshot.list.items, (item) => item.module) }
                ]}
                searchPlaceholder="输入搜索关键词"
                toolbarExtras={<TimeRangeFilter />}
              />
            </ListFrame>
          </>
        )}
      </QueryPage>
      <HistoryLogDetailDialog
        logId={selectedHistoryLogId}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedHistoryLogId(null);
          }
        }}
        open={selectedHistoryLogId !== null}
      />
    </main>
  );
}

export function AccountChangeLogsPage() {
  const [selectedAccountChangeLogId, setSelectedAccountChangeLogId] = useState<number | null>(null);
  const columns = useMemo(() => createAccountChangeLogColumns(setSelectedAccountChangeLogId), [setSelectedAccountChangeLogId]);
  const logsQuery = useQuery({
    queryKey: ["audit", "account-change-logs", 1, 200, 24],
    queryFn: () => fetchAccountChangeLogsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        title="变更历史"
        legacyHref="/history/account-change-logs/"
      />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: AccountChangeLogsSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                {
                  label: "变更总数",
                  value: snapshot.statistics.total_changes,
                  detail: `人均变更 ${formatDecimal(snapshot.statistics.affected_accounts > 0 ? snapshot.statistics.total_changes / snapshot.statistics.affected_accounts : 0)} · 24h`,
                  icon: FileText
                },
                {
                  label: "成功率",
                  value: formatPercent(snapshot.statistics.total_changes > 0 ? (snapshot.statistics.success_count / snapshot.statistics.total_changes) * 100 : 0),
                  detail: `成功/账号 ${formatDecimal(snapshot.statistics.affected_accounts > 0 ? snapshot.statistics.success_count / snapshot.statistics.affected_accounts : 0)}`,
                  icon: CheckCircle2
                },
                {
                  label: "失败变更",
                  value: snapshot.statistics.failed_count,
                  detail: `失败率 ${formatPercent(snapshot.statistics.total_changes > 0 ? (snapshot.statistics.failed_count / snapshot.statistics.total_changes) * 100 : 0)} · 失败/账号 ${formatDecimal(snapshot.statistics.affected_accounts > 0 ? snapshot.statistics.failed_count / snapshot.statistics.affected_accounts : 0)}`,
                  icon: XCircle
                },
                {
                  label: "影响账号数",
                  value: snapshot.statistics.affected_accounts,
                  detail: `变更/小时 ${formatDecimal(snapshot.statistics.total_changes / 24)}`,
                  icon: ShieldAlert
                }
              ]}
            />
            <ListFrame title="账户变更列表" total={snapshot.list.total}>
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  { columnId: "instance_name", label: "实例", options: uniqueTextOptions(snapshot.list.items, (item) => item.instance_name) },
                  { columnId: "db_type", label: "数据库类型", options: uniqueTextOptions(snapshot.list.items, (item) => item.db_type) },
                  { columnId: "change_type", label: "变更类型", options: uniqueTextOptions(snapshot.list.items, (item) => item.change_type) }
                ]}
                searchPlaceholder="搜索账号 / 实例"
                toolbarExtras={<TimeRangeFilter />}
              />
            </ListFrame>
          </>
        )}
      </QueryPage>
      <AccountChangeLogDetailDialog
        logId={selectedAccountChangeLogId}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedAccountChangeLogId(null);
          }
        }}
        open={selectedAccountChangeLogId !== null}
      />
    </main>
  );
}
