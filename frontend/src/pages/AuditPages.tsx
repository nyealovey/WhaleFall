import { useQuery } from "@tanstack/react-query";
import { AlertCircle, AlertTriangle, CheckCircle2, ExternalLink, FileText, ShieldAlert, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import {
  fetchAccountChangeLogsSnapshot,
  fetchHistoryLogsSnapshot,
  type AccountChangeLogItem,
  type AccountChangeLogsSnapshot,
  type HistoryLogItem,
  type HistoryLogsSnapshot
} from "@/api/audit";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof FileText;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number | undefined | null): string {
  return `${(value ?? 0).toFixed(1)}%`;
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

function ListFrame({ title, description, total, children }: { title: string; description: string; total: number; children: ReactNode }) {
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

function EmptyRows({ colSpan }: { colSpan: number }) {
  return (
    <TableRow>
      <TableCell className="px-3 py-8 text-center text-sm text-muted-foreground" colSpan={colSpan}>
        暂无数据
      </TableCell>
    </TableRow>
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

function HistoryLogsTable({ items }: { items: HistoryLogItem[] }) {
  return (
    <Table className="min-w-[62rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["时间", "等级", "模块", "消息", "上下文"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={5} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell className="font-mono text-xs">{item.timestamp_display || item.timestamp}</TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.level)}>{item.level}</Badge>
            </TableCell>
            <TableCell>{item.module}</TableCell>
            <TableCell>
              <div className="max-w-xl truncate font-medium">{item.message}</div>
              {item.traceback ? <div className="mt-1 text-xs text-destructive">traceback available</div> : null}
            </TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {item.context ? Object.keys(item.context).slice(0, 3).join(", ") : "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function AccountChangeLogsTable({ items }: { items: AccountChangeLogItem[] }) {
  return (
    <Table className="min-w-[64rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["时间", "账户", "实例", "类型", "状态", "摘要", "差异"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={7} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell className="font-mono text-xs">{item.change_time}</TableCell>
            <TableCell>
              <div className="font-medium">{item.username}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.db_type}</div>
            </TableCell>
            <TableCell>
              <div>{item.instance_name || "-"}</div>
              <div className="mt-1 font-mono text-xs text-muted-foreground">{item.instance_host || "-"}</div>
            </TableCell>
            <TableCell>{item.change_type}</TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
            </TableCell>
            <TableCell>
              <div className="max-w-xl truncate">{item.message || "-"}</div>
              {item.session_id ? <div className="mt-1 font-mono text-xs text-muted-foreground">{item.session_id}</div> : null}
            </TableCell>
            <TableCell className="font-mono text-xs">
              P {formatNumber(item.privilege_diff_count)} · O {formatNumber(item.other_diff_count)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function HistoryLogsPage() {
  const logsQuery = useQuery({
    queryKey: ["audit", "history-logs", 1, 20, 24],
    queryFn: () => fetchHistoryLogsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="System audit"
        title="日志中心"
        description="查看最近 24 小时系统日志统计和首屏日志列表；详情检索仍保留在旧版。"
        legacyHref="/history/logs/"
      />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: HistoryLogsSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                { label: "日志总数", value: snapshot.statistics.total_logs, icon: FileText },
                { label: "错误", value: snapshot.statistics.error_count, detail: `错误率 ${formatPercent(snapshot.statistics.error_rate)}`, icon: XCircle },
                { label: "告警", value: snapshot.statistics.warning_count, icon: AlertTriangle },
                { label: "Top 模块", value: snapshot.statistics.top_modules[0]?.module ?? "-", detail: `${formatNumber(snapshot.statistics.top_modules[0]?.count)} 条`, icon: ShieldAlert }
              ]}
            />
            <ListFrame title="日志列表" description={`最近 24 小时 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <HistoryLogsTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function AccountChangeLogsPage() {
  const logsQuery = useQuery({
    queryKey: ["audit", "account-change-logs", 1, 20, 24],
    queryFn: () => fetchAccountChangeLogsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Account audit"
        title="变更历史"
        description="查看最近 24 小时账户变更统计和首屏变更日志；详情仍保留在旧版。"
        legacyHref="/history/account-change-logs/"
      />
      <QueryPage snapshot={logsQuery.data} isLoading={logsQuery.isLoading} isError={logsQuery.isError} onRetry={() => void logsQuery.refetch()}>
        {(snapshot: AccountChangeLogsSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                { label: "变更总数", value: snapshot.statistics.total_changes, icon: FileText },
                { label: "成功", value: snapshot.statistics.success_count, icon: CheckCircle2 },
                { label: "失败", value: snapshot.statistics.failed_count, icon: XCircle },
                { label: "影响账户", value: snapshot.statistics.affected_accounts, icon: ShieldAlert }
              ]}
            />
            <ListFrame title="账户变更列表" description={`最近 24 小时 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <AccountChangeLogsTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}
