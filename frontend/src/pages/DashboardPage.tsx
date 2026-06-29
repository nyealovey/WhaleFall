import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Cpu, Database, HardDrive, RefreshCw, Server, ShieldAlert, Users } from "lucide-react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  fetchDashboardSnapshot,
  type DashboardCharts,
  type DashboardOverview,
  type DashboardRiskSummary,
  type DashboardStatus
} from "@/api/dashboard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { runAction } from "@/utils/action-feedback";

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatCapacity(value: number | undefined): string {
  if (!value) {
    return "0 GB";
  }
  if (value >= 1024) {
    return `${(value / 1024).toFixed(1)} TB`;
  }
  return `${value.toFixed(1)} GB`;
}

function serviceTone(status: string): "default" | "secondary" | "destructive" | "outline" {
  return status === "healthy" || status === "connected" ? "secondary" : "destructive";
}

function serviceLabel(status: string): string {
  return status === "healthy" || status === "connected" ? "正常" : "异常";
}

function StatChips({ items }: { items: Array<{ label: string; value: number | undefined; variant?: "default" | "secondary" | "destructive" | "outline" }> }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Badge className="gap-1 font-normal" key={item.label} variant={item.variant ?? "outline"}>
          <span className="font-mono">{formatNumber(item.value)}</span>
          <span>{item.label}</span>
        </Badge>
      ))}
    </div>
  );
}

function MetricCards({ overview }: { overview: DashboardOverview }) {
  const metrics = [
    {
      label: "数据库实例",
      value: formatNumber(overview.instances.total),
      icon: Server,
      chips: [
        { label: "在线", value: overview.instances.active, variant: "secondary" as const },
        { label: "物理", value: overview.instances.physical },
        { label: "AG", value: overview.instances.ag_virtual },
        { label: "停用", value: overview.instances.inactive },
        { label: "删除", value: overview.instances.deleted, variant: "destructive" as const }
      ]
    },
    {
      label: "账户总数",
      value: formatNumber(overview.accounts.total),
      icon: Users,
      chips: [
        { label: "正常", value: overview.accounts.normal, variant: "secondary" as const },
        { label: "锁定", value: overview.accounts.locked },
        { label: "删除", value: overview.accounts.deleted, variant: "destructive" as const },
        { label: "实例", value: overview.accounts.instance?.total },
        { label: "AG", value: overview.accounts.sqlserver_ag?.total }
      ]
    },
    {
      label: "总容量",
      value: formatCapacity(overview.capacity.total_gb),
      icon: HardDrive,
      chips: []
    },
    {
      label: "数据库总数",
      value: formatNumber(overview.databases.total),
      icon: Database,
      chips: [
        { label: "正常", value: overview.databases.active, variant: "secondary" as const },
        { label: "受限", value: overview.databases.inactive },
        { label: "删除", value: overview.databases.deleted, variant: "destructive" as const }
      ]
    }
  ];

  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="控制台指标">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <Card className="min-h-[var(--metric-card-min-height)]" key={metric.label}>
            <CardContent className="grid gap-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Icon aria-hidden size={18} />
                <span>{metric.label}</span>
              </div>
              <strong className="font-mono text-[length:var(--metric-hero-value)] leading-none">{metric.value}</strong>
              {metric.chips.length > 0 ? <StatChips items={metric.chips} /> : null}
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}

function UsageBar({ label, value }: { label: string; value: number }) {
  const bounded = Math.max(0, Math.min(value, 100));
  return (
    <div className="grid gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{bounded.toFixed(1)}%</span>
      </div>
      <Progress value={bounded} />
    </div>
  );
}

function SystemStatus({ status }: { status: DashboardStatus }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>系统状态</CardTitle>
          <CardDescription>系统资源与依赖服务</CardDescription>
        </div>
        <Cpu aria-hidden size={18} />
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-3">
          <UsageBar label="CPU 使用率" value={status.system.cpu} />
          <UsageBar label="内存使用率" value={status.system.memory.percent} />
          <UsageBar label="磁盘使用率" value={status.system.disk.percent} />
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-md border bg-secondary/40 p-3">
            <strong className="text-muted-foreground">数据库:</strong>
            <div className="mt-2">
              <Badge variant={serviceTone(status.services.database)}>{serviceLabel(status.services.database)}</Badge>
            </div>
          </div>
          <div className="rounded-md border bg-secondary/40 p-3">
            <strong className="text-muted-foreground">Redis:</strong>
            <div className="mt-2">
              <Badge variant={serviceTone(status.services.redis)}>{serviceLabel(status.services.redis)}</Badge>
            </div>
          </div>
        </div>
        <p className="flex flex-wrap gap-1 text-xs text-muted-foreground">
          <span>系统运行时间</span>
          <span>{status.uptime}</span>
        </p>
      </CardContent>
    </Card>
  );
}

function ChartLists({ charts }: { charts: DashboardCharts }) {
  const logTrendData = (charts.log_trend ?? []).map((item) => ({
    date: item.date,
    label: item.date.slice(5),
    error_count: item.error_count,
    warning_count: item.warning_count
  }));
  const logTrendChartConfig = {
    error_count: {
      label: "错误日志",
      color: "var(--chart-3)"
    },
    warning_count: {
      label: "告警日志",
      color: "var(--chart-4)"
    }
  } satisfies ChartConfig;

  return (
    <Card>
      <CardHeader>
        <CardTitle>错误和告警日志趋势（最近7天）</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium">日志趋势</h2>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="destructive">错误日志</Badge>
              <Badge variant="outline">告警日志</Badge>
            </div>
          </div>
          {logTrendData.length > 0 ? (
            <div aria-label="错误和告警日志趋势图" className="min-h-[220px]" role="img">
              <ul className="sr-only" aria-label="错误和告警日志趋势数据">
                {logTrendData.map((item) => (
                  <li key={item.date}>
                    {item.date}: 错误日志 {formatNumber(item.error_count)}, 告警日志 {formatNumber(item.warning_count)}
                  </li>
                ))}
              </ul>
              <ChartContainer config={logTrendChartConfig} className="h-[220px] w-full">
                <LineChart accessibilityLayer data={logTrendData} margin={{ left: 8, right: 10, top: 12, bottom: 0 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                  <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line
                    dataKey="error_count"
                    name="错误日志"
                    type="monotone"
                    stroke="var(--color-error_count)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                  <Line
                    dataKey="warning_count"
                    name="告警日志"
                    type="monotone"
                    stroke="var(--color-warning_count)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ChartContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">暂无错误和告警日志趋势</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function RiskAlertBoard({ summary }: { summary: DashboardRiskSummary | undefined }) {
  const topRisks = summary?.top_risks ?? [];
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>风险告警</CardTitle>
          <CardDescription>当前风险事件 · {formatNumber(topRisks.length)} 项</CardDescription>
        </div>
        <ShieldAlert aria-hidden size={18} />
      </CardHeader>
      <CardContent className="grid gap-2">
        {topRisks.length > 0 ? (
          topRisks.map((risk, index) => (
            <a
              className="grid gap-1 rounded-md border bg-secondary/40 p-3 text-sm transition-colors hover:bg-secondary"
              href={risk.target_url ?? "#"}
              key={`${risk.instance_name ?? "risk"}-${risk.rule_key ?? index}`}
            >
              <div className="flex items-center justify-between gap-2">
                <strong>{[risk.instance_name, risk.label].filter(Boolean).join(" · ") || "风险事件"}</strong>
                <Badge variant={risk.severity === "high" ? "destructive" : "outline"}>{risk.group ?? risk.db_type?.toUpperCase() ?? "风险"}</Badge>
              </div>
              {risk.detail ? <span className="text-muted-foreground">{risk.detail}</span> : null}
            </a>
          ))
        ) : (
          <div className="rounded-md border bg-secondary/40 p-4 text-sm text-muted-foreground">
            <strong className="text-foreground">当前没有启用的风险命中</strong>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "snapshot"],
    queryFn: () => fetchDashboardSnapshot()
  });

  const snapshot = dashboardQuery.data;

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
        <div>
          <h1 className="font-display text-2xl leading-none tracking-normal">仪表盘</h1>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button onClick={() => void runAction(dashboardQuery.refetch(), { success: "仪表盘已刷新" })} type="button">
            <RefreshCw aria-hidden size={16} />
            刷新数据
          </Button>
        </div>
      </section>

      {dashboardQuery.isLoading ? (
        <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="控制台指标加载中">
          {["实例", "账户", "数据库", "容量"].map((label) => (
            <Card className="min-h-[var(--metric-card-min-height)]" key={label}>
              <CardContent className="grid gap-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {dashboardQuery.isError ? (
        <Alert variant="destructive" className="grid-cols-[1rem_minmax(0,1fr)] items-center sm:grid-cols-[1rem_minmax(0,1fr)_auto]">
          <AlertCircle aria-hidden size={16} />
          <AlertDescription>仪表盘数据加载失败</AlertDescription>
          <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
            <Button variant="outline" onClick={() => void dashboardQuery.refetch()}>
              重新加载
            </Button>
          </div>
        </Alert>
      ) : null}

      {snapshot ? (
        <>
          <MetricCards overview={snapshot.overview} />
          <RiskAlertBoard summary={snapshot.riskSummary} />
          <section className="grid grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)] gap-2 max-lg:grid-cols-1">
            <ChartLists charts={snapshot.charts} />
            <SystemStatus status={snapshot.status} />
          </section>
        </>
      ) : null}
    </main>
  );
}
