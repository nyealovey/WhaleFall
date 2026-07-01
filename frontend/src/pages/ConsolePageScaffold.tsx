import { AlertCircle, Layers3 } from "lucide-react";
import type { ReactNode } from "react";

import { SwitchField } from "@/components/shared/FormControls";
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
import { Skeleton } from "@/components/ui/skeleton";
import { TableCell, TableRow } from "@/components/ui/table";
import type { SessionUser } from "@/types/auth";
import type { SchedulerJobItem, TaskRunItem } from "@/api/readOnly";

export type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof Layers3;
};

export type AccessUser = Pick<SessionUser, "id" | "role">;

export function canManageCatalog(currentUser?: AccessUser | null): boolean {
  return currentUser?.role === undefined || currentUser.role === "admin";
}

export function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

export function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0.0%";
  }
  return `${((value / total) * 100).toFixed(1)}%`;
}

export function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function asText(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

export function isEmptyDetailValue(value: unknown): boolean {
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

export function JsonBlock({ value }: { value: unknown }) {
  if (isEmptyDetailValue(value)) {
    return <span className="text-muted-foreground">-</span>;
  }

  return (
    <pre className="max-h-48 overflow-auto rounded-md border bg-secondary/30 p-3 font-mono text-xs whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function DetailBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-md border bg-secondary/20 p-3">
      <div className="mb-1 text-xs text-muted-foreground">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

export function endpointHost(value: unknown): string {
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

export function statusVariant(value: string | boolean | undefined | null): "default" | "secondary" | "destructive" | "outline" {
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

export function statusLabel(value: string | boolean | undefined | null): string {
  if (value === true) {
    return "启用";
  }
  if (value === false) {
    return "停用";
  }
  return asText(value);
}

export function roleLabel(role: string | undefined | null): string {
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

export function isRunningState(state: string | undefined | null): boolean {
  return state === "STATE_RUNNING" || state === "STATE_EXECUTING" || state === "running";
}

export function schedulerStatusLabel(state: string | undefined | null): string {
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

export function schedulerJobName(job: SchedulerJobItem): string {
  return job.task_name ?? job.name ?? job.id;
}

export function syncRunId(item: TaskRunItem): string {
  return item.run_id;
}

export function syncTaskName(item: TaskRunItem): string {
  return item.task_name || item.task_key;
}

export function syncSource(item: TaskRunItem): string {
  return ({ scheduled: "定时", scheduled_task: "定时", manual: "手动", api: "API" } as Record<string, string>)[item.trigger_source] ?? item.trigger_source;
}

export function syncCategory(item: TaskRunItem): string {
  return ({ account: "账户", capacity: "容量", aggregation: "聚合", classification: "分类", cluster: "群集", notification: "告警", other: "其他" } as Record<string, string>)[item.task_category] ?? item.task_category;
}

export function syncProgress(item: TaskRunItem) {
  const total = item.progress_total ?? 0;
  const completed = item.progress_completed ?? 0;
  const failed = item.progress_failed ?? 0;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { total, completed, failed, percent };
}

export function syncDuration(item: TaskRunItem): string {
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

export function PageHeader({ title }: { eyebrow?: string; title: string; description?: string }) {
  return (
    <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
      <div>
        <h1 className="font-display text-2xl leading-none tracking-normal">{title}</h1>
      </div>
    </section>
  );
}

export function CommandBar({ children }: { children: ReactNode }) {
  return <section className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">{children}</section>;
}

export function MetricGrid({ metrics, label }: { metrics: Metric[]; label: string }) {
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

export function LoadingGrid() {
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

export function ErrorState({ label, onRetry }: { label: string; onRetry: () => void }) {
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

export function QueryFrame<TData>({
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

export function ListPanel({
  title,
  description,
  count,
  actions,
  children
}: {
  title: string;
  description?: string;
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
            {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
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

export function EmptyRows({ colSpan }: { colSpan: number }) {
  return (
    <TableRow>
      <TableCell className="px-3 py-8 text-center text-sm text-muted-foreground" colSpan={colSpan}>
        暂无数据
      </TableCell>
    </TableRow>
  );
}

export function StatusBadge({ value }: { value: string | boolean | undefined | null }) {
  return <Badge variant={statusVariant(value)}>{statusLabel(value)}</Badge>;
}

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function ActiveField({ checked, onCheckedChange }: { checked: boolean; onCheckedChange: (checked: boolean) => void }) {
  return <SwitchField checked={checked} label="状态" onCheckedChange={onCheckedChange} />;
}

export function DeleteConfirmDialog({
  confirmLabel,
  description,
  onConfirm,
  onOpenChange,
  open,
  title
}: {
  confirmLabel: string;
  description: string;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}) {
  return (
    <AlertDialog onOpenChange={onOpenChange} open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>返回</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
