import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Calculator, Database, ExternalLink, HardDrive, RefreshCw, Server } from "lucide-react";
import type { ReactNode } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { triggerCapacityAggregation } from "@/api/actions";
import {
  fetchCapacityDatabaseSnapshot,
  fetchCapacityInstanceSnapshot,
  type CapacityDatabaseItem,
  type CapacityDatabaseSnapshot,
  type CapacityInstanceItem,
  type CapacityInstanceSnapshot
} from "@/api/capacity";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Metric = {
  label: string;
  value: string | number;
  detail?: string;
  icon: typeof Server;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatSizeMb(value: number | undefined | null): string {
  const size = value ?? 0;
  if (size >= 1024) {
    return `${(size / 1024).toFixed(2)} GB`;
  }
  return `${size.toFixed(0)} MB`;
}

function formatPercent(value: number | undefined | null): string {
  return `${(value ?? 0).toFixed(1)}%`;
}

function trendVariant(value: number | undefined | null): "default" | "secondary" | "destructive" | "outline" {
  const resolved = value ?? 0;
  if (resolved > 0) {
    return "destructive";
  }
  if (resolved < 0) {
    return "secondary";
  }
  return "outline";
}

function TrendIcon({ value }: { value: number | undefined | null }) {
  const resolved = value ?? 0;
  if (resolved > 0) {
    return <ArrowUpRight aria-hidden size={14} />;
  }
  if (resolved < 0) {
    return <ArrowDownRight aria-hidden size={14} />;
  }
  return <ArrowRight aria-hidden size={14} />;
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

function CommandBar({ onAggregate, onRefresh }: { onAggregate: () => void; onRefresh: () => void }) {
  return (
    <section className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
      <Button onClick={onRefresh} type="button" variant="outline">
        <RefreshCw aria-hidden size={16} />
        <span>刷新数据</span>
      </Button>
      <Button onClick={onAggregate} type="button">
        <Calculator aria-hidden size={16} />
        <span>统计当前周期</span>
      </Button>
    </section>
  );
}

const selectClassName =
  "border-input bg-background ring-offset-background focus-visible:ring-ring h-9 rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

function CapacityFilterBar({ includeDatabase }: { includeDatabase?: boolean }) {
  return (
    <section className="grid grid-cols-4 gap-3 rounded-lg border bg-card p-3 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="容量筛选">
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>数据库类型</span>
        <select aria-label="数据库类型" className={selectClassName} defaultValue="all">
          <option value="all">全部类型</option>
          <option value="mysql">MySQL</option>
          <option value="sqlserver">SQL Server</option>
          <option value="oracle">Oracle</option>
        </select>
      </label>
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>实例</span>
        <select aria-label="实例" className={selectClassName} defaultValue="all">
          <option value="all">全部实例</option>
        </select>
      </label>
      {includeDatabase ? (
        <label className="grid gap-1.5 text-sm font-medium text-foreground">
          <span>数据库</span>
          <select aria-label="数据库" className={selectClassName} defaultValue="all">
            <option value="all">全部数据库</option>
          </select>
        </label>
      ) : null}
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>周期</span>
        <select aria-label="周期" className={selectClassName} defaultValue="daily">
          <option value="daily">日</option>
          <option value="weekly">周</option>
          <option value="monthly">月</option>
        </select>
      </label>
    </section>
  );
}

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="容量指标">
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

type CapacityChartPoint = {
  label: string;
  trend: number;
  change: number;
  percent: number;
};

const capacityChartConfig = {
  trend: { label: "容量", color: "var(--chart-1)" },
  change: { label: "变化量", color: "var(--chart-2)" },
  percent: { label: "变化率", color: "var(--chart-3)" }
} satisfies ChartConfig;

function CapacityChartControls() {
  return (
    <div className="flex flex-wrap gap-2">
      {["折线图", "柱状图", "TOP5", "TOP10", "TOP20", "7", "14", "30"].map((label) => (
        <Button disabled key={label} size="sm" variant="outline">
          {label}
        </Button>
      ))}
    </div>
  );
}

function CapacityChartPanel({ title, data, dataKey }: { title: string; data: CapacityChartPoint[]; dataKey: keyof Pick<CapacityChartPoint, "trend" | "change" | "percent"> }) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-lg:grid">
          <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
          <CapacityChartControls />
        </div>
        {data.length > 0 ? (
          <ChartContainer config={capacityChartConfig} className="h-[240px] w-full">
            <AreaChart accessibilityLayer data={data} margin={{ left: -12, right: 12, top: 12, bottom: 0 }}>
              <defs>
                <linearGradient id={`capacity-${dataKey}-fill`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={`var(--color-${dataKey})`} stopOpacity={0.34} />
                  <stop offset="95%" stopColor={`var(--color-${dataKey})`} stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis tickLine={false} axisLine={false} tickMargin={8} width={44} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Area dataKey={dataKey} name={capacityChartConfig[dataKey].label} type="monotone" stroke={`var(--color-${dataKey})`} strokeWidth={2} fill={`url(#capacity-${dataKey}-fill)`} />
            </AreaChart>
          </ChartContainer>
        ) : (
          <p className="text-sm text-muted-foreground">暂无趋势数据</p>
        )}
      </CardContent>
    </Card>
  );
}

function CapacityCharts({ data }: { data: CapacityChartPoint[] }) {
  return (
    <section className="grid gap-2">
      <CapacityChartPanel title="容量统计趋势图" data={data} dataKey="trend" />
      <CapacityChartPanel title="容量变化趋势图" data={data} dataKey="change" />
      <CapacityChartPanel title="容量变化趋势图 (百分比)" data={data} dataKey="percent" />
    </section>
  );
}

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="容量加载中">
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
      <AlertDescription>容量数据加载失败</AlertDescription>
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

function formatRatio(value: number): string {
  return `${value.toFixed(1)}x`;
}

function instanceLargestShare(summary: CapacityInstanceSnapshot["summary"]): string {
  if (summary.total_size_mb <= 0) {
    return "0%";
  }
  return formatPercent((summary.max_size_mb / summary.total_size_mb) * 100);
}

function databaseLargestShare(summary: CapacityDatabaseSnapshot["summary"]): string {
  if (summary.total_size_mb <= 0) {
    return "0%";
  }
  return formatPercent((summary.max_size_mb / summary.total_size_mb) * 100);
}

function instanceChartData(items: CapacityInstanceItem[]): CapacityChartPoint[] {
  return items.map((item) => ({
    label: item.instance.name,
    trend: item.total_size_mb,
    change: item.total_size_change_mb ?? 0,
    percent: item.total_size_change_percent ?? item.growth_rate ?? 0
  }));
}

function databaseChartData(items: CapacityDatabaseItem[]): CapacityChartPoint[] {
  return items.map((item) => ({
    label: item.database_name,
    trend: item.avg_size_mb,
    change: item.size_change_mb ?? 0,
    percent: item.size_change_percent ?? item.growth_rate ?? 0
  }));
}

function InstanceCapacityTable({ items }: { items: CapacityInstanceItem[] }) {
  return (
    <Table className="min-w-[58rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["实例", "周期", "总容量", "数据库数", "变化", "增长率"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell>
              <div className="font-medium">{item.instance.name}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.instance.db_type}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {item.period_start} - {item.period_end}
            </TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.total_size_mb)}</TableCell>
            <TableCell className="font-mono text-xs">{formatNumber(item.database_count)}</TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.total_size_change_mb)}</TableCell>
            <TableCell>
              <Badge variant={trendVariant(item.growth_rate)}>
                <TrendIcon value={item.growth_rate} />
                {formatPercent(item.growth_rate)}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DatabaseCapacityTable({ items }: { items: CapacityDatabaseItem[] }) {
  return (
    <Table className="min-w-[58rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["数据库", "实例", "周期", "平均容量", "变化", "增长率"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell className="font-medium">{item.database_name}</TableCell>
            <TableCell>
              <div>{item.instance.name}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.instance.db_type}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {item.period_start} - {item.period_end}
            </TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.avg_size_mb)}</TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.size_change_mb)}</TableCell>
            <TableCell>
              <Badge variant={trendVariant(item.growth_rate)}>
                <TrendIcon value={item.growth_rate} />
                {formatPercent(item.growth_rate)}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function CapacityInstancesPage() {
  const capacityQuery = useQuery({
    queryKey: ["capacity", "instances", "daily", "last-30-days"],
    queryFn: () => fetchCapacityInstanceSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Instance capacity"
        title="实例容量"
        description="按实例维度查看容量统计、容量变化和容量变化百分比趋势。"
        legacyHref="/capacity/instances"
      />
      <CommandBar
        onAggregate={() => {
          void triggerCapacityAggregation("instance").then(() => capacityQuery.refetch());
        }}
        onRefresh={() => {
          void capacityQuery.refetch();
        }}
      />
      <QueryPage snapshot={capacityQuery.data} isLoading={capacityQuery.isLoading} isError={capacityQuery.isError} onRetry={() => void capacityQuery.refetch()}>
        {(snapshot: CapacityInstanceSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                { label: "在线实例数", value: snapshot.summary.total_instances, detail: `${snapshot.summary.period_type} · ${snapshot.summary.source}`, icon: Server },
                { label: "总容量", value: formatSizeMb(snapshot.summary.total_size_mb), detail: `最大占比 ${instanceLargestShare(snapshot.summary)}`, icon: HardDrive },
                {
                  label: "平均容量",
                  value: formatSizeMb(snapshot.summary.avg_size_mb),
                  detail: `最大/均值 ${formatRatio(snapshot.summary.avg_size_mb > 0 ? snapshot.summary.max_size_mb / snapshot.summary.avg_size_mb : 0)}`,
                  icon: BarChart3
                },
                { label: "最大容量", value: formatSizeMb(snapshot.summary.max_size_mb), icon: Database }
              ]}
            />
            <CapacityFilterBar />
            <CapacityCharts data={instanceChartData(snapshot.list.items)} />
            <ListFrame title="实例容量列表" description={`日粒度 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <InstanceCapacityTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function CapacityDatabasesPage() {
  const capacityQuery = useQuery({
    queryKey: ["capacity", "databases", "daily", "last-30-days"],
    queryFn: () => fetchCapacityDatabaseSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database capacity"
        title="数据库容量"
        description="按数据库维度查看容量统计、容量变化和容量变化百分比趋势。"
        legacyHref="/capacity/databases"
      />
      <CommandBar
        onAggregate={() => {
          void triggerCapacityAggregation("database").then(() => capacityQuery.refetch());
        }}
        onRefresh={() => {
          void capacityQuery.refetch();
        }}
      />
      <QueryPage snapshot={capacityQuery.data} isLoading={capacityQuery.isLoading} isError={capacityQuery.isError} onRetry={() => void capacityQuery.refetch()}>
        {(snapshot: CapacityDatabaseSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                {
                  label: "总数据库数",
                  value: snapshot.summary.total_databases,
                  detail: `实例数 ${formatNumber(snapshot.summary.total_instances)} · 库/实例 ${formatRatio(snapshot.summary.total_instances > 0 ? snapshot.summary.total_databases / snapshot.summary.total_instances : 0)}`,
                  icon: Database
                },
                { label: "总容量", value: formatSizeMb(snapshot.summary.total_size_mb), detail: `增长率 ${formatPercent(snapshot.summary.growth_rate)}`, icon: HardDrive },
                {
                  label: "平均容量",
                  value: formatSizeMb(snapshot.summary.avg_size_mb),
                  detail: `最大/均值 ${formatRatio(snapshot.summary.avg_size_mb > 0 ? snapshot.summary.max_size_mb / snapshot.summary.avg_size_mb : 0)}`,
                  icon: BarChart3
                },
                { label: "最大容量", value: formatSizeMb(snapshot.summary.max_size_mb), detail: `最大占比 ${databaseLargestShare(snapshot.summary)}`, icon: Server }
              ]}
            />
            <CapacityFilterBar includeDatabase />
            <CapacityCharts data={databaseChartData(snapshot.list.items)} />
            <ListFrame title="数据库容量列表" description={`日粒度 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <DatabaseCapacityTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}
