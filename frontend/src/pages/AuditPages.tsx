import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { AlertCircle, AlertTriangle, Circle, FileText, Minus, Pencil, Plus, ShieldAlert, XCircle } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import {
  fetchAccountChangeLogDetail,
  fetchAccountChangeLogOptions,
  fetchAccountChangeLogsSnapshot,
  fetchHistoryLogDetail,
  fetchHistoryLogModules,
  fetchHistoryLogsSnapshot,
  type AccountChangeLogDetail,
  type AccountChangeLogItem,
  type AccountChangeLogsSnapshot,
  type HistoryLogDetail,
  type HistoryLogItem,
  type HistoryLogsSnapshot
} from "@/api/audit";
import { DataTable } from "@/components/shared/DataTable";
import { useServerTableState } from "@/components/shared/useServerTableState";
import { SelectControl, TruncatedTooltip } from "@/components/shared/FormControls";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { historyLogLevelLabel, historyLogMessageLabel, historyLogModuleLabel } from "@/pages/auditView";

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

function PageHeader({ title }: { title: string }) {
  return (
    <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
      <div>
        <h1 className="font-display text-2xl leading-none tracking-normal">{title}</h1>
      </div>
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

type TimeRangeValue = "1h" | "1d" | "1w" | "1m" | "all";

const timeRangeHours: Record<Exclude<TimeRangeValue, "all">, number> = { "1h": 1, "1d": 24, "1w": 168, "1m": 720 };

function timeWindowLabel(hours: number | undefined): string {
  return hours ? `${hours}h` : "全部";
}

function perHourValue(total: number, hours: number | undefined): string {
  return hours ? formatDecimal(total / hours) : "-";
}

function TimeRangeFilter({ includeAll, onChange, value }: { includeAll?: boolean; onChange: (value: TimeRangeValue) => void; value: TimeRangeValue }) {
  const options = [
    { label: "最近 1 小时", value: "1h" },
    { label: "最近 24 小时", value: "1d" },
    { label: "最近 7 天", value: "1w" },
    { label: "最近 30 天", value: "1m" }
  ];
  if (includeAll) options.unshift({ label: "全部", value: "all" });
  return (
    <label className="grid gap-1.5 text-sm font-medium text-foreground">
      <span>时间范围</span>
      <SelectControl
        label="时间范围"
        onValueChange={(next) => onChange(next as TimeRangeValue)}
        options={options}
        value={value}
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

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : null;
}

function textValue(value: unknown): string | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }
  const text = String(value).trim();
  return text ? text : undefined;
}

function firstText(source: UnknownRecord | null, keys: string[]): string | undefined {
  if (!source) {
    return undefined;
  }
  for (const key of keys) {
    const text = textValue(source[key]);
    if (text) {
      return text;
    }
  }
  return undefined;
}

function accountChangeInstanceInfo(log: AccountChangeLogDetail["log"]): { host?: string; name?: string } {
  const record = asRecord(log);
  const instanceInfo = asRecord(record?.instance_info) ?? asRecord(record?.instance);
  return {
    name: firstText(record, ["instance_name", "instanceName", "display_instance_name", "name"]) ?? firstText(instanceInfo, ["name", "instance_name", "display_name"]),
    host: firstText(record, ["instance_host", "instanceHost", "display_instance_host", "host", "ip", "ip_address"]) ?? firstText(instanceInfo, ["host", "instance_host", "listener_host", "ip", "ip_address"])
  };
}

type PermissionDiffAction = "added" | "changed" | "removed" | "unchanged";
type PermissionDiffEntry = {
  action: PermissionDiffAction;
  text: string;
};

function normalizePermissionAction(value: unknown): PermissionDiffAction {
  const action = textValue(value)?.toLowerCase();
  if (["add", "added", "grant", "granted", "create", "new"].includes(action ?? "")) {
    return "added";
  }
  if (["delete", "deleted", "remove", "removed", "revoke", "revoked"].includes(action ?? "")) {
    return "removed";
  }
  if (["same", "unchanged", "none", "keep", "kept"].includes(action ?? "")) {
    return "unchanged";
  }
  return "changed";
}

function arrayText(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => textValue(item)).filter((item): item is string => Boolean(item));
}

function permissionEntryText(value: unknown): string {
  const record = asRecord(value);
  if (!record) {
    return textValue(value) ?? "-";
  }

  const direct = firstText(record, ["privilege", "permission", "name", "label", "field"]);
  const object = firstText(record, ["object", "target", "scope"]);
  const permissions = arrayText(record.permissions ?? record.permission_values ?? record.values);
  const before = textValue(record.before ?? record.old ?? record.from);
  const after = textValue(record.after ?? record.new ?? record.to);

  if (object && permissions.length > 0) {
    return `${object} · ${permissions.join(", ")}`;
  }
  if (direct && permissions.length > 0) {
    return `${direct} · ${permissions.join(", ")}`;
  }
  if (direct && (before || after)) {
    return `${direct}: ${before ?? "-"} -> ${after ?? "-"}`;
  }
  return object ?? direct ?? textValue(JSON.stringify(value)) ?? "-";
}

function collectPermissionDiffEntries(value: unknown): PermissionDiffEntry[] {
  if (Array.isArray(value)) {
    return value.map((item) => {
      const record = asRecord(item);
      return {
        action: normalizePermissionAction(record?.action ?? record?.type ?? record?.operation),
        text: permissionEntryText(item)
      };
    });
  }

  const record = asRecord(value);
  if (!record) {
    return [];
  }

  const groupedKeys: Array<[PermissionDiffAction, string[]]> = [
    ["added", ["added", "add", "granted", "grant"]],
    ["removed", ["removed", "remove", "revoked", "revoke"]],
    ["changed", ["changed", "modified", "updated", "altered"]],
    ["unchanged", ["unchanged", "same", "kept"]]
  ];
  const entries: PermissionDiffEntry[] = [];
  groupedKeys.forEach(([action, keys]) => {
    keys.forEach((key) => {
      const groupValue = record[key];
      if (Array.isArray(groupValue)) {
        groupValue.forEach((item) => entries.push({ action, text: permissionEntryText(item) }));
      }
    });
  });
  return entries;
}

function PermissionDiffPanel({ value }: { value: unknown }) {
  const entries = collectPermissionDiffEntries(value).filter((entry) => entry.text && entry.text !== "-");
  if (entries.length === 0) {
    return <JsonBlock value={value} />;
  }

  const groups: Array<{
    action: PermissionDiffAction;
    className: string;
    icon: typeof Plus;
    label: string;
  }> = [
    { action: "added", label: "新增权限", icon: Plus, className: "wf-badge-success" },
    { action: "removed", label: "移除权限", icon: Minus, className: "wf-badge-danger" },
    { action: "changed", label: "调整权限", icon: Pencil, className: "wf-badge-warning" },
    { action: "unchanged", label: "未变化", icon: Circle, className: "wf-badge-muted" }
  ];

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {groups.map((group) => {
        const groupEntries = entries.filter((entry) => entry.action === group.action);
        if (groupEntries.length === 0) {
          return null;
        }
        const Icon = group.icon;
        return (
          <section className={`rounded-md border p-3 ${group.className}`} key={group.action}>
            <div className="mb-2 flex items-center justify-between gap-2 text-sm font-semibold">
              <span className="inline-flex items-center gap-1.5">
                <Icon aria-hidden size={15} />
                {group.label}
              </span>
              <Badge variant="outline" className="bg-background/70">
                {groupEntries.length} 项
              </Badge>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {groupEntries.map((entry, index) => (
                <Badge className="max-w-full whitespace-normal break-all bg-background/75 text-current" key={`${group.action}-${entry.text}-${index}`} variant="outline">
                  {entry.text}
                </Badge>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function writeClipboard(text: string) {
  void navigator.clipboard?.writeText(text);
}

function historyLogDetailPayload(log: HistoryLogItem): string {
  return JSON.stringify(
    {
      id: log.id,
      timestamp: log.timestamp_display || log.timestamp,
      level: log.level,
      module: log.module,
      message: log.message,
      traceback: log.traceback,
      context: log.context
    },
    null,
    2
  );
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
  const [showContext, setShowContext] = useState(true);
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
          <DialogDescription>系统日志消息、堆栈和上下文。</DialogDescription>
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
            <div className="flex flex-wrap gap-2">
              <Button size="sm" type="button" variant="outline" onClick={() => writeClipboard(historyLogMessageLabel(log))}>
                复制消息
              </Button>
              <Button size="sm" type="button" variant="outline" onClick={() => writeClipboard(historyLogDetailPayload(log))}>
                复制 JSON
              </Button>
              <Button size="sm" type="button" variant="outline" onClick={() => writeClipboard(String(log.traceback ?? ""))}>
                复制堆栈
              </Button>
              <Button size="sm" type="button" variant="outline" onClick={() => setShowContext((current) => !current)}>
                展开上下文
              </Button>
              <Button size="sm" type="button" variant="outline" onClick={() => writeClipboard(historyLogDetailPayload(log))}>
                复制详情
              </Button>
            </div>
            <dl className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
              <DetailField label="时间">
                <DetailText value={log.timestamp_display || log.timestamp} />
              </DetailField>
              <DetailField label="级别">
                <Badge variant={statusVariant(log.level)}>{historyLogLevelLabel(log)}</Badge>
              </DetailField>
              <DetailField label="模块">
                <Badge variant="outline">{historyLogModuleLabel(log)}</Badge>
              </DetailField>
              <DetailField label="日志 ID">
                <span className="font-mono">#{log.id}</span>
              </DetailField>
            </dl>
            <DetailField label="消息">
              <DetailText value={historyLogMessageLabel(log)} />
            </DetailField>
            <DetailField label="堆栈">
              {log.traceback ? (
                <pre className="max-h-64 overflow-auto rounded-md border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{log.traceback}</pre>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </DetailField>
            {showContext ? (
              <DetailField label="上下文">
                <JsonBlock value={log.context} />
              </DetailField>
            ) : null}
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
  const instanceInfo = log ? accountChangeInstanceInfo(log) : {};

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
                  <DetailText value={instanceInfo.name} />
                  <span className="font-mono text-xs text-muted-foreground">{instanceInfo.host || "-"}</span>
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
              <PermissionDiffPanel value={log.privilege_diff} />
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
      cell: ({ row }) => <Badge variant={statusVariant(row.original.level)}>{historyLogLevelLabel(row.original)}</Badge>
    },
    {
      accessorKey: "module",
      header: "模块",
      cell: ({ row }) => <Badge variant="outline">{historyLogModuleLabel(row.original)}</Badge>
    },
    {
      accessorKey: "message",
      header: "消息",
      cell: ({ row }) => {
        const message = historyLogMessageLabel(row.original);
        return (
          <TruncatedTooltip className="max-w-xl font-medium" content={message}>
            {message}
          </TruncatedTooltip>
        );
      }
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
  const table = useServerTableState({ initialFilters: { level: "", module: "", timeRange: "1d" } });
  const columns = useMemo(() => createHistoryLogColumns(setSelectedHistoryLogId), [setSelectedHistoryLogId]);
  const hours = timeRangeHours[table.filters.timeRange as Exclude<TimeRangeValue, "all">];
  const windowLabel = timeWindowLabel(hours);
  const logsQuery = useQuery({
    queryKey: ["audit", "history-logs", table.page, table.pageSize, table.search, table.filters, hours],
    queryFn: () => fetchHistoryLogsSnapshot({ page: table.page, limit: table.pageSize, search: table.search, level: table.filters.level, module: table.filters.module, hours }),
    placeholderData: (previous) => previous
  });
  const modulesQuery = useQuery({ queryKey: ["audit", "history-log-modules"], queryFn: () => fetchHistoryLogModules() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader title="日志中心" />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: HistoryLogsSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                {
                  label: "总日志数",
                  value: snapshot.statistics.total_logs,
                  detail: `Top 模块 ${snapshot.statistics.top_modules[0]?.module_label ?? snapshot.statistics.top_modules[0]?.module ?? "-"} · ${formatNumber(snapshot.statistics.top_modules[0]?.count)} 条 · ${windowLabel}`,
                  icon: FileText
                },
                {
                  label: "错误日志",
                  value: snapshot.statistics.error_count,
                  detail: `错误率 ${formatPercent(snapshot.statistics.error_rate)} · 严重 ${formatNumber(snapshot.statistics.critical_count)} · ${perHourValue(snapshot.statistics.error_count, hours)}/小时`,
                  icon: XCircle
                },
                {
                  label: "警告日志",
                  value: snapshot.statistics.warning_count,
                  detail: `占比 ${formatPercent(snapshot.statistics.total_logs > 0 ? (snapshot.statistics.warning_count / snapshot.statistics.total_logs) * 100 : 0)} · ${perHourValue(snapshot.statistics.warning_count, hours)}/小时`,
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
                  { columnId: "level", label: "级别", options: ["ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"].map((value) => ({ label: value, value })), value: table.filters.level, onValueChange: (value) => table.setFilter("level", value) },
                  { columnId: "module", label: "模块", options: modulesQuery.data ?? [], value: table.filters.module, onValueChange: (value) => table.setFilter("module", value) }
                ]}
                onSearchChange={table.setSearchInput}
                onResetFilters={table.reset}
                pagination={{ page: table.page, pageSize: table.pageSize, pages: snapshot.list.pages, total: snapshot.list.total, onPageChange: table.setPage, onPageSizeChange: table.setPageSize }}
                searchPlaceholder="输入搜索关键词"
                searchValue={table.searchInput}
                toolbarExtras={<TimeRangeFilter onChange={(value) => table.setFilter("timeRange", value)} value={table.filters.timeRange as TimeRangeValue} />}
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
  const table = useServerTableState({ initialFilters: { instanceId: "", dbType: "", changeType: "", timeRange: "all" } });
  const columns = useMemo(() => createAccountChangeLogColumns(setSelectedAccountChangeLogId), [setSelectedAccountChangeLogId]);
  const hours = table.filters.timeRange === "all" ? undefined : timeRangeHours[table.filters.timeRange as Exclude<TimeRangeValue, "all">];
  const logsQuery = useQuery({
    queryKey: ["audit", "account-change-logs", table.page, table.pageSize, table.search, table.filters, hours],
    queryFn: () => fetchAccountChangeLogsSnapshot({ page: table.page, limit: table.pageSize, search: table.search, instanceId: table.filters.instanceId ? Number(table.filters.instanceId) : undefined, dbType: table.filters.dbType, changeType: table.filters.changeType, hours }),
    placeholderData: (previous) => previous
  });
  const optionsQuery = useQuery({ queryKey: ["audit", "account-change-options"], queryFn: () => fetchAccountChangeLogOptions() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader title="变更历史" />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: AccountChangeLogsSnapshot) => (
          <ListFrame title="账户变更列表" total={snapshot.list.total}>
            <DataTable
              columns={columns}
              data={snapshot.list.items}
              filters={[
                { columnId: "instance_name", label: "实例", options: optionsQuery.data ?? [], value: table.filters.instanceId, onValueChange: (value) => table.setFilter("instanceId", value) },
                { columnId: "db_type", label: "数据库类型", options: ["mysql", "postgresql", "sqlserver", "oracle"].map((value) => ({ label: value.toUpperCase(), value })), value: table.filters.dbType, onValueChange: (value) => table.setFilter("dbType", value) },
                { columnId: "change_type", label: "变更类型", options: [{ label: "新增", value: "add" }, { label: "权限变更", value: "modify_privilege" }, { label: "属性变更", value: "modify_other" }, { label: "删除", value: "delete" }], value: table.filters.changeType, onValueChange: (value) => table.setFilter("changeType", value) }
              ]}
              onSearchChange={table.setSearchInput}
              onResetFilters={table.reset}
              pagination={{ page: table.page, pageSize: table.pageSize, pages: snapshot.list.pages, total: snapshot.list.total, onPageChange: table.setPage, onPageSizeChange: table.setPageSize }}
              searchPlaceholder="搜索账号 / 实例"
              searchValue={table.searchInput}
              toolbarExtras={<TimeRangeFilter includeAll onChange={(value) => table.setFilter("timeRange", value)} value={table.filters.timeRange as TimeRangeValue} />}
            />
          </ListFrame>
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
