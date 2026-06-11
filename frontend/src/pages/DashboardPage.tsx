import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, Cpu, Database, HardDrive, Server, Users } from "lucide-react";

import { fetchDashboardSnapshot, type DashboardCharts, type DashboardOverview, type DashboardStatus } from "@/api/dashboard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

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

function MetricCards({ overview }: { overview: DashboardOverview }) {
  const metrics = [
    {
      label: "数据库实例",
      value: formatNumber(overview.instances.total),
      detail: `活跃 ${formatNumber(overview.instances.active)} · 物理 ${formatNumber(overview.instances.physical)}`,
      icon: Server
    },
    {
      label: "账户总数",
      value: formatNumber(overview.accounts.total),
      detail: `正常 ${formatNumber(overview.accounts.normal)} · 锁定 ${formatNumber(overview.accounts.locked)}`,
      icon: Users
    },
    {
      label: "数据库总数",
      value: formatNumber(overview.databases.total),
      detail: `正常 ${formatNumber(overview.databases.active)} · 受限 ${formatNumber(overview.databases.inactive)}`,
      icon: Database
    },
    {
      label: "实例容量",
      value: formatCapacity(overview.capacity.total_gb),
      detail: `当前利用率 ${formatNumber(overview.capacity.usage_percent)}%`,
      icon: HardDrive
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
              <span className="text-xs text-muted-foreground">{metric.detail}</span>
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
      <div className="h-2 overflow-hidden rounded-sm bg-secondary">
        <div className="h-full rounded-sm bg-primary" style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}

function SystemStatus({ status }: { status: DashboardStatus }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>运行状态</CardTitle>
          <CardDescription>系统资源与依赖服务</CardDescription>
        </div>
        <Cpu aria-hidden size={18} />
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-3">
          <UsageBar label="CPU" value={status.system.cpu} />
          <UsageBar label="Memory" value={status.system.memory.percent} />
          <UsageBar label="Disk" value={status.system.disk.percent} />
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-md border bg-secondary/40 p-3">
            <span className="text-muted-foreground">Database</span>
            <div className="mt-2">
              <Badge variant={serviceTone(status.services.database)}>{status.services.database}</Badge>
            </div>
          </div>
          <div className="rounded-md border bg-secondary/40 p-3">
            <span className="text-muted-foreground">Redis</span>
            <div className="mt-2">
              <Badge variant={serviceTone(status.services.redis)}>{status.services.redis}</Badge>
            </div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">Uptime: {status.uptime}</p>
      </CardContent>
    </Card>
  );
}

function ChartLists({ charts }: { charts: DashboardCharts }) {
  const maxLogCount = Math.max(...(charts.log_levels ?? []).map((item) => item.count), 1);
  const maxSyncCount = Math.max(...(charts.sync_trend ?? []).map((item) => item.count), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>运行信号</CardTitle>
        <CardDescription>日志等级与同步趋势</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-5 max-lg:grid-cols-1">
        <div className="grid gap-2">
          <h2 className="text-sm font-medium">日志等级</h2>
          {(charts.log_levels ?? []).length > 0 ? (
            charts.log_levels?.map((item) => (
              <div className="grid gap-1" key={item.level}>
                <div className="flex items-center justify-between text-xs">
                  <span>{item.level}</span>
                  <span className="font-mono">{formatNumber(item.count)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-sm bg-secondary">
                  <div className="h-full rounded-sm bg-foreground/70" style={{ width: `${(item.count / maxLogCount) * 100}%` }} />
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">暂无日志分布</p>
          )}
        </div>
        <div className="grid gap-2">
          <h2 className="text-sm font-medium">同步趋势</h2>
          {(charts.sync_trend ?? []).length > 0 ? (
            charts.sync_trend?.slice(-7).map((item) => (
              <div className="grid grid-cols-[5.5rem_minmax(0,1fr)_3rem] items-center gap-2 text-xs" key={item.date}>
                <span className="text-muted-foreground">{item.date.slice(5)}</span>
                <div className="h-2 overflow-hidden rounded-sm bg-secondary">
                  <div className="h-full rounded-sm bg-primary" style={{ width: `${(item.count / maxSyncCount) * 100}%` }} />
                </div>
                <span className="text-right font-mono">{formatNumber(item.count)}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">暂无同步趋势</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ClassificationPanel({ overview }: { overview: DashboardOverview }) {
  const classifications = overview.classified_accounts.classifications ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>账户分类</CardTitle>
        <CardDescription>
          已分类 {formatNumber(overview.classified_accounts.total)} · 自动分类 {formatNumber(overview.classified_accounts.auto)}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {classifications.length > 0 ? (
          classifications.slice(0, 6).map((item) => (
            <div className="flex items-center justify-between rounded-md border bg-secondary/40 px-3 py-2 text-sm" key={item.code}>
              <span>{item.display_name}</span>
              <span className="font-mono">{formatNumber(item.count)}</span>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">暂无分类分布</p>
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
          <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">React console</span>
          <h1 className="font-display mt-1 text-2xl leading-none tracking-normal">仪表盘</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            读取 `/api/v1/dashboard/**` 汇总系统资源、账号分类、运行状态和同步信号。
          </p>
        </div>
        <Button variant="outline" asChild>
          <a href="/dashboard/">在旧版打开</a>
        </Button>
      </section>

      {dashboardQuery.isLoading ? (
        <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="控制台指标加载中">
          {["实例", "账户", "数据库", "容量"].map((label) => (
            <Card className="min-h-[var(--metric-card-min-height)]" key={label}>
              <CardContent className="grid gap-3">
                <div className="h-4 w-24 rounded-sm bg-secondary" />
                <div className="h-8 w-20 rounded-sm bg-secondary" />
                <div className="h-3 w-32 rounded-sm bg-secondary" />
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {dashboardQuery.isError ? (
        <Card>
          <CardContent className="flex items-center justify-between gap-4 text-sm max-sm:grid">
            <span className="flex items-center gap-2 text-destructive">
              <AlertCircle aria-hidden size={16} />
              仪表盘数据加载失败
            </span>
            <Button variant="outline" onClick={() => void dashboardQuery.refetch()}>
              重新加载
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {snapshot ? (
        <>
          <MetricCards overview={snapshot.overview} />
          <section className="grid grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)] gap-2 max-lg:grid-cols-1">
            <ChartLists charts={snapshot.charts} />
            <SystemStatus status={snapshot.status} />
          </section>
          <section className="grid grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] gap-2 max-lg:grid-cols-1">
            <ClassificationPanel overview={snapshot.overview} />
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>活动流</CardTitle>
                  <CardDescription>当前 API 已接入，暂无活动数据时保持空态。</CardDescription>
                </div>
                <Activity aria-hidden size={18} />
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {snapshot.activities.length > 0 ? `${formatNumber(snapshot.activities.length)} 条活动` : "暂无近期活动"}
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </main>
  );
}
