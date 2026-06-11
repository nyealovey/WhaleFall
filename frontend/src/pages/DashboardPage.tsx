import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, Cpu, Database, HardDrive, Server, Users } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { fetchDashboardSnapshot, type DashboardCharts, type DashboardOverview, type DashboardStatus } from "@/api/dashboard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

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
      <Progress value={bounded} />
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
  const logLevelData = (charts.log_levels ?? []).map((item) => ({
    level: item.level,
    count: item.count
  }));
  const syncTrendData = (charts.sync_trend ?? []).slice(-14).map((item) => ({
    date: item.date,
    label: item.date.slice(5),
    count: item.count
  }));
  const logLevelChartConfig = {
    count: {
      label: "日志数",
      color: "var(--chart-2)"
    }
  } satisfies ChartConfig;
  const syncTrendChartConfig = {
    count: {
      label: "同步数",
      color: "var(--chart-1)"
    }
  } satisfies ChartConfig;

  return (
    <Card>
      <CardHeader>
        <CardTitle>运行信号</CardTitle>
        <CardDescription>日志等级与同步趋势</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-5 max-lg:grid-cols-1">
        <div className="grid gap-2">
          <h2 className="text-sm font-medium">日志等级</h2>
          {logLevelData.length > 0 ? (
            <div aria-label="日志等级折线图" className="min-h-[190px]" role="img">
              <ul className="sr-only" aria-label="日志等级数据">
                {logLevelData.map((item) => (
                  <li key={item.level}>
                    {item.level}: {formatNumber(item.count)}
                  </li>
                ))}
              </ul>
              <ChartContainer config={logLevelChartConfig} className="h-[190px] w-full">
                <LineChart accessibilityLayer data={logLevelData} margin={{ left: -12, right: 10, top: 12, bottom: 0 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="level" tickLine={false} axisLine={false} tickMargin={8} />
                  <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                  <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                  <Line
                    dataKey="count"
                    name="日志数"
                    type="monotone"
                    stroke="var(--color-count)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ChartContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">暂无日志分布</p>
          )}
        </div>
        <div className="grid gap-2">
          <h2 className="text-sm font-medium">同步趋势</h2>
          {syncTrendData.length > 0 ? (
            <div aria-label="同步趋势面积图" className="min-h-[190px]" role="img">
              <ul className="sr-only" aria-label="同步趋势数据">
                {syncTrendData.map((item) => (
                  <li key={item.date}>
                    {item.date}: {formatNumber(item.count)}
                  </li>
                ))}
              </ul>
              <ChartContainer config={syncTrendChartConfig} className="h-[190px] w-full">
                <AreaChart accessibilityLayer data={syncTrendData} margin={{ left: -12, right: 10, top: 12, bottom: 0 }}>
                  <defs>
                    <linearGradient id="syncTrendFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-count)" stopOpacity={0.34} />
                      <stop offset="95%" stopColor="var(--color-count)" stopOpacity={0.04} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                  <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Area
                    dataKey="count"
                    name="同步数"
                    type="monotone"
                    stroke="var(--color-count)"
                    strokeWidth={2}
                    fill="url(#syncTrendFill)"
                  />
                </AreaChart>
              </ChartContainer>
            </div>
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
