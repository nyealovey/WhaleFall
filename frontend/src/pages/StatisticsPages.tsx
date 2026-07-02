import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CircleCheck,
  Database,
  HardDrive,
  Network,
  PieChart,
  RefreshCw,
  RotateCw,
  Server,
  ShieldCheck,
  Tags,
  Trophy,
  UserCheck,
  UserLock,
  Users
} from "lucide-react";
import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart as RechartsPieChart, XAxis, YAxis } from "recharts";

import {
  fetchAccountStatisticsSnapshot,
  fetchDatabaseStatistics,
  fetchInstanceStatistics,
  type AccountStatisticsSnapshot,
  type DatabaseStatistics,
  type InstanceStatistics
} from "@/api/statistics";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { runAction } from "@/utils/action-feedback";

import { formatStatisticsSizeMb } from "./statisticsView";

type Metric = {
  label: string;
  value: number | string | undefined;
  detail?: ReactNode;
  icon: typeof Server;
};

type DistributionRow = {
  label: string;
  value: number | string;
  percent?: number;
  detail?: string;
  badge?: string;
  meta?: Array<{ label: string; value: number | string; variant?: "default" | "secondary" | "destructive" | "outline" }>;
};

type AdStatusRow = {
  label: string;
  key: string;
  variant: "default" | "secondary" | "destructive" | "outline";
  total: number;
  instance: number;
  ag: number;
};

const chartConfig = {
  value: { label: "数量", color: "var(--chart-1)" },
  instance: { label: "实例账户", color: "var(--chart-1)" },
  ag: { label: "AG 账户", color: "var(--chart-2)" }
} satisfies ChartConfig;

const chartColors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--primary)"];

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function ratio(numerator: number | undefined, denominator: number | undefined): number {
  const total = denominator ?? 0;
  if (total <= 0) {
    return 0;
  }
  return ((numerator ?? 0) / total) * 100;
}

function perUnit(numerator: number | undefined, denominator: number | undefined): string {
  const total = denominator ?? 0;
  if (total <= 0) {
    return "0.0";
  }
  return ((numerator ?? 0) / total).toFixed(1);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function numberField(record: Record<string, unknown>, keys: string[]): number {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return 0;
}

function toneForBadge(value: string): "default" | "secondary" | "destructive" | "outline" {
  return ["error", "failed", "not_backed_up", "backup_stale", "high", "disabled", "orphaned"].includes(value) ? "destructive" : "secondary";
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    backed_up: "已备份",
    backup_stale: "备份过期",
    not_backed_up: "未备份",
    completed: "已更新"
  };
  return labels[value] ?? value;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "未采集";
  }
  return value.split("+")[0]?.replace("T", " ") ?? value;
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

function CommandBar({
  backHref,
  backLabel,
  refreshLabel,
  onRefresh
}: {
  backHref: string;
  backLabel: string;
  refreshLabel?: string;
  onRefresh: () => void;
}) {
  return (
    <section className="flex items-center justify-between gap-2 rounded-lg border bg-card p-3 max-sm:grid" aria-label="页面命令">
      <Button variant="outline" asChild>
        <a href={backHref}>
          <ArrowLeft aria-hidden size={16} />
          <span>{backLabel}</span>
        </a>
      </Button>
      <Button variant="outline" onClick={onRefresh}>
        <RefreshCw aria-hidden size={16} />
        <span>{refreshLabel ?? "刷新统计"}</span>
      </Button>
    </section>
  );
}

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="统计指标">
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
              {metric.detail ? <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">{metric.detail}</div> : null}
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}

function MetricPills({ items }: { items: Array<{ label: string; value?: number | string; variant?: "default" | "secondary" | "destructive" | "outline" }> }) {
  return (
    <>
      {items.map((item) => (
        <Badge key={item.label} variant={item.variant ?? "secondary"}>
          {item.value !== undefined ? <span>{item.value}</span> : null}
          <span>{item.label}</span>
        </Badge>
      ))}
    </>
  );
}

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="统计指标加载中">
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
      <AlertDescription>统计数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function QueryPage({
  children,
  isLoading,
  isError,
  onRetry
}: {
  children: ReactNode;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {children}
    </>
  );
}

type ChartRow = DistributionRow & {
  value: number;
  fill: string;
};

function numericValue(value: number | string | undefined): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function toChartRows(rows: DistributionRow[]): ChartRow[] {
  return rows.map((row, index) => ({
    ...row,
    value: numericValue(row.value),
    fill: chartColors[index % chartColors.length] ?? "var(--chart-1)"
  }));
}

function topRows(rows: DistributionRow[], limit = 10): DistributionRow[] {
  return [...rows].sort((left, right) => numericValue(right.value) - numericValue(left.value)).slice(0, limit);
}

function ChartSummaryList({
  rows,
  valueFormatter = formatNumber
}: {
  rows: ChartRow[];
  valueFormatter?: (value: number) => string;
}) {
  return (
    <div className="grid gap-2">
      {rows.map((row) => (
        <div className="grid gap-1 rounded-md border bg-muted/20 px-3 py-2" key={`${row.label}-${row.badge ?? ""}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="size-2.5 rounded-[3px]" style={{ backgroundColor: row.fill }} />
                {row.badge ? <Badge variant={toneForBadge(row.badge)}>{statusLabel(row.badge)}</Badge> : null}
                <span className="truncate font-medium">{row.label}</span>
              </div>
              {row.detail ? <p className="mt-1 text-xs text-muted-foreground">{row.detail}</p> : null}
            </div>
            <div className="shrink-0 text-right">
              <div className="font-mono text-sm font-semibold">{valueFormatter(row.value)}</div>
              {row.percent !== undefined ? <div className="font-mono text-xs text-muted-foreground">{formatPercent(row.percent)}</div> : null}
            </div>
          </div>
          {row.meta?.length ? (
            <div className="flex flex-wrap gap-1">
              {row.meta.map((meta) => (
                <Badge variant={meta.variant ?? "secondary"} key={`${row.label}-${meta.label}`}>
                  {meta.label} {meta.value}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function StatPanel({
  title,
  badge,
  icon,
  children
}: {
  title: string;
  badge?: string;
  icon: typeof Server;
  children: ReactNode;
}) {
  const Icon = icon;
  return (
    <Card className="min-h-[360px]">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Icon aria-hidden size={18} />
            <span>{title}</span>
          </CardTitle>
        </div>
        {badge ? <Badge variant="outline">{badge}</Badge> : null}
      </CardHeader>
      <CardContent>
        {children}
      </CardContent>
    </Card>
  );
}

function DistributionChartPanel({
  title,
  badge,
  icon,
  rows,
  type,
  valueLabel = "数量",
  valueFormatter = formatNumber
}: {
  title: string;
  badge?: string;
  icon: typeof Server;
  rows: DistributionRow[];
  type: "donut" | "bar" | "horizontalBar";
  valueLabel?: string;
  valueFormatter?: (value: number) => string;
}) {
  const data = toChartRows(rows);
  const hasData = data.length > 0;
  return (
    <StatPanel title={title} badge={badge} icon={icon}>
      <div className="grid gap-4">
        {hasData ? (
          <ChartContainer config={chartConfig} className={type === "horizontalBar" ? "h-[300px] w-full" : "h-[260px] w-full"}>
            {type === "donut" ? (
              <RechartsPieChart accessibilityLayer margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                <Pie data={data} dataKey="value" nameKey="label" innerRadius="58%" outerRadius="82%" paddingAngle={2}>
                  {data.map((entry) => (
                    <Cell key={entry.label} fill={entry.fill} />
                  ))}
                </Pie>
              </RechartsPieChart>
            ) : type === "horizontalBar" ? (
              <BarChart accessibilityLayer data={data} layout="vertical" margin={{ left: 8, right: 18, top: 8, bottom: 8 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis dataKey="label" type="category" tickLine={false} axisLine={false} tickMargin={8} width={128} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="value" name={valueLabel} radius={[0, 4, 4, 0]}>
                  {data.map((entry) => (
                    <Cell key={entry.label} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            ) : (
              <BarChart accessibilityLayer data={data} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="value" name={valueLabel} radius={[4, 4, 0, 0]}>
                  {data.map((entry) => (
                    <Cell key={entry.label} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            )}
          </ChartContainer>
        ) : (
          <p className="text-sm text-muted-foreground">暂无图表数据</p>
        )}
        {hasData ? <ChartSummaryList rows={data} valueFormatter={valueFormatter} /> : null}
      </div>
    </StatPanel>
  );
}

function StackedStatusChartPanel({
  title,
  badge,
  icon,
  rows
}: {
  title: string;
  badge?: string;
  icon: typeof Server;
  rows: AdStatusRow[];
}) {
  const data = rows.map((row) => ({ label: row.label, total: row.total, instance: row.instance, ag: row.ag }));
  return (
    <StatPanel title={title} badge={badge} icon={icon}>
      <div className="grid gap-4">
        <ChartContainer config={chartConfig} className="h-[260px] w-full">
          <BarChart accessibilityLayer data={data} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="instance" stackId="accounts" name="实例账户" radius={[4, 4, 0, 0]} fill="var(--color-instance)" />
            <Bar dataKey="ag" stackId="accounts" name="AG 账户" radius={[4, 4, 0, 0]} fill="var(--color-ag)" />
          </BarChart>
        </ChartContainer>
        <div className="grid gap-2">
          {rows.map((row) => (
            <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/20 px-3 py-2" key={row.key}>
              <Badge variant={row.variant}>{row.label}</Badge>
              <div className="flex flex-wrap justify-end gap-1 text-xs">
                <Badge variant="secondary">合计 {formatNumber(row.total)}</Badge>
                <Badge variant="secondary">实例 {formatNumber(row.instance)}</Badge>
                <Badge variant="secondary">AG {formatNumber(row.ag)}</Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </StatPanel>
  );
}

function toDistributionRows<TItem>(
  items: TItem[],
  total: number,
  options: {
    label: (item: TItem) => string;
    count: (item: TItem) => number;
    detail?: (item: TItem) => string | undefined;
    badge?: (item: TItem) => string | undefined;
  }
): DistributionRow[] {
  return items.map((item) => {
    const value = options.count(item);
    return {
      label: options.label(item),
      value,
      percent: ratio(value, total),
      detail: options.detail?.(item),
      badge: options.badge?.(item)
    };
  });
}

function InstanceStatisticsContent({ stats }: { stats: InstanceStatistics }) {
  const current = stats.current_instances;
  const dbTypeRows = toDistributionRows(stats.db_type_stats, current, { label: (item) => item.db_type, count: (item) => item.count });
  const portRows = toDistributionRows(stats.port_stats, current, { label: (item) => String(item.port), count: (item) => item.count });
  const versionRows: DistributionRow[] = stats.version_stats.map((item) => ({
    label: item.version || "未知版本",
    value: item.count,
    percent: ratio(item.count, current),
    detail: item.db_type
  }));
  const backupRows = toDistributionRows(stats.backup_status_stats, current, {
    label: (item) => statusLabel(item.backup_status),
    count: (item) => item.count,
    badge: (item) => item.backup_status
  });

  return (
    <>
      <MetricGrid
        metrics={[
          {
            label: "实例总数",
            value: stats.total_instances,
            detail: (
              <MetricPills
                items={[
                  { label: "在线", value: stats.active_instances, variant: "default" },
                  { label: "停用", value: stats.inactive_instances, variant: "secondary" },
                  { label: "删除", value: stats.deleted_instances, variant: "destructive" }
                ]}
              />
            ),
            icon: Server
          },
          {
            label: "审计信息",
            value: stats.audit_enabled_instances,
            detail: <MetricPills items={[{ label: "已开通率", value: formatPercent(ratio(stats.audit_enabled_instances, stats.active_instances)), variant: "secondary" }]} />,
            icon: ShieldCheck
          },
          {
            label: "托管统计",
            value: stats.managed_instances,
            detail: (
              <MetricPills
                items={[
                  { label: "托管覆盖率", value: formatPercent(ratio(stats.managed_instances, current)), variant: "secondary" },
                  { label: "未托管", value: stats.unmanaged_instances, variant: "secondary" }
                ]}
              />
            ),
            icon: BarChart3
          },
          {
            label: "备份统计",
            value: stats.backed_up_instances,
            detail: (
              <MetricPills
                items={[
                  { label: "有效备份率", value: formatPercent(ratio(stats.backed_up_instances, current)), variant: "secondary" },
                  { label: "过期", value: stats.backup_stale_instances, variant: "secondary" },
                  { label: "未备份", value: stats.not_backed_up_instances, variant: "destructive" }
                ]}
              />
            ),
            icon: HardDrive
          }
        ]}
      />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DistributionChartPanel title="数据库类型分布" badge={`${formatNumber(stats.db_types_count)} 类`} icon={PieChart} rows={dbTypeRows} type="donut" />
        <DistributionChartPanel title="备份状态分布" badge="Veeam" icon={HardDrive} rows={backupRows} type="bar" />
      </section>
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DistributionChartPanel title="端口分布" badge="Top 10" icon={Network} rows={topRows(portRows)} type="horizontalBar" />
        <DistributionChartPanel title="数据库版本统计" badge="Top 10" icon={Tags} rows={topRows(versionRows)} type="horizontalBar" />
      </section>
    </>
  );
}

function AccountStatisticsContent({ snapshot }: { snapshot: AccountStatisticsSnapshot }) {
  const { summary } = snapshot;
  const total = summary.total_accounts;
  const ownerRows: DistributionRow[] = Object.entries(summary.owner_type_stats ?? {}).map(([type, value]) => {
    const meta = asRecord(value);
    const count = numberField(meta, ["total", "total_accounts", "count"]);
    return {
      label: type === "sqlserver_ag" ? "AG 账户" : type === "instance" ? "实例账户" : type,
      value: count,
      percent: numberField(meta, ["percent"]) || ratio(count, total),
      meta: [
        { label: "启用", value: numberField(meta, ["active", "active_accounts"]), variant: "default" as const },
        { label: "删除", value: numberField(meta, ["deleted", "deleted_accounts"]), variant: "secondary" as const }
      ]
    };
  });

  const adStatus = asRecord(summary.ad_status_stats);
  const adTotal = asRecord(adStatus.total);
  const adByOwner = asRecord(adStatus.by_owner_type);
  const adInstance = asRecord(adByOwner.instance);
  const adAg = asRecord(adByOwner.sqlserver_ag);
  const adRows: AdStatusRow[] = [
    { key: "normal", label: "正常", variant: "default", total: numberField(adTotal, ["normal"]), instance: numberField(adInstance, ["normal"]), ag: numberField(adAg, ["normal"]) },
    { key: "disabled", label: "AD 已停用", variant: "secondary", total: numberField(adTotal, ["disabled"]), instance: numberField(adInstance, ["disabled"]), ag: numberField(adAg, ["disabled"]) },
    { key: "orphaned", label: "AD 孤账户", variant: "destructive", total: numberField(adTotal, ["orphaned"]), instance: numberField(adInstance, ["orphaned"]), ag: numberField(adAg, ["orphaned"]) },
    { key: "unmatched", label: "未匹配", variant: "outline", total: numberField(adTotal, ["unmatched"]), instance: numberField(adInstance, ["unmatched"]), ag: numberField(adAg, ["unmatched"]) }
  ];

  const dbTypeRows = Object.entries(snapshot.dbTypes ?? {}).map(([dbType, value]) => {
    const meta = asRecord(value);
    const count = numberField(meta, ["total", "total_accounts", "count"]);
    return {
      label: dbType,
      value: count,
      percent: ratio(count, total),
      meta: [
        { label: "正常", value: numberField(meta, ["normal", "normal_accounts"]), variant: "default" as const },
        { label: "受限", value: numberField(meta, ["locked", "locked_accounts"]), variant: "secondary" as const },
        { label: "删除", value: numberField(meta, ["deleted", "deleted_accounts"]), variant: "secondary" as const }
      ]
    };
  });
  const classificationSource = asRecord(snapshot.classifications);
  const classificationRows: DistributionRow[] = [
    ["super", "超高风险"],
    ["highly", "高风险"],
    ["sensitive", "敏感"],
    ["medium", "中风险"],
    ["low", "低风险"],
    ["public", "公开"]
  ].map(([code, label]) => {
    const count = numberField(asRecord(classificationSource[code]), ["account_count", "total_accounts", "count", "total"]);
    return { label, value: count, percent: ratio(count, total) };
  });
  return (
    <>
      <MetricGrid
        metrics={[
          {
            label: "总账户数",
            value: summary.total_accounts,
            detail: (
              <MetricPills
                items={[
                  { label: "正常账户", value: summary.normal_accounts, variant: "default" },
                  { label: "受限账户", value: summary.locked_accounts, variant: "secondary" },
                  { label: "已删除账户", value: summary.deleted_accounts, variant: "destructive" }
                ]}
              />
            ),
            icon: Users
          },
          {
            label: "正常账户",
            value: summary.normal_accounts,
            detail: <MetricPills items={[{ label: "正常/实例", value: perUnit(summary.normal_accounts, summary.total_instances), variant: "secondary" }]} />,
            icon: UserCheck
          },
          {
            label: "受限账户",
            value: summary.locked_accounts,
            detail: <MetricPills items={[{ label: "受限/实例", value: perUnit(summary.locked_accounts, summary.total_instances), variant: "secondary" }]} />,
            icon: UserLock
          },
          {
            label: "统计实例",
            value: summary.total_instances,
            detail: (
              <MetricPills
                items={[
                  { label: "账户/实例", value: perUnit(summary.total_accounts, summary.total_instances), variant: "secondary" },
                  { label: "物理实例", value: summary.physical_instances, variant: "secondary" },
                  { label: "AG虚拟实例", value: summary.ag_virtual_instances, variant: "secondary" }
                ]}
              />
            ),
            icon: Server
          }
        ]}
      />
      <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
        <DistributionChartPanel title="账户来源分布" badge="台账口径" icon={BarChart3} rows={ownerRows} type="donut" />
        <StackedStatusChartPanel title="AD 账户对比" badge="活跃账户" icon={UserLock} rows={adRows} />
      </section>
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DistributionChartPanel title="数据库类型分布" badge="实时" icon={Database} rows={dbTypeRows} type="donut" />
        <DistributionChartPanel title="账户分类分布" badge="当前规则" icon={Tags} rows={classificationRows} type="horizontalBar" />
      </section>
    </>
  );
}

function DatabaseStatisticsContent({ stats }: { stats: DatabaseStatistics }) {
  const active = stats.active_databases;
  const dbTypeRows = toDistributionRows(stats.db_type_stats, active, { label: (item) => item.db_type, count: (item) => item.count });
  const instanceRows = toDistributionRows(stats.instance_stats, active, {
    label: (item) => item.instance_name,
    count: (item) => item.count,
    detail: (item) => item.db_type
  });
  const syncRows = toDistributionRows(stats.sync_status_stats, active, {
    label: (item) => item.label,
    count: (item) => item.count,
    badge: (item) => item.value
  });
  const capacityRows: DistributionRow[] = stats.capacity_rankings.map((item) => ({
    label: item.database_name,
    value: item.size_mb,
    percent: ratio(item.size_mb, stats.total_size_mb),
    detail: `${item.instance_name} · ${item.db_type} · ${formatDateTime(item.collected_at)}`
  }));

  return (
    <>
      <MetricGrid
        metrics={[
          {
            label: "数据库总数",
            value: stats.total_databases,
            detail: (
              <MetricPills
                items={[
                  { label: "正常数据库", value: stats.active_databases, variant: "default" },
                  { label: "受限数据库", value: stats.inactive_databases, variant: "secondary" },
                  { label: "已删除数据库", value: stats.deleted_databases, variant: "destructive" }
                ]}
              />
            ),
            icon: Database
          },
          {
            label: "正常数据库",
            value: stats.active_databases,
            detail: <MetricPills items={[{ label: "正常率", value: formatPercent(ratio(stats.active_databases, stats.total_databases)), variant: "secondary" }]} />,
            icon: CircleCheck
          },
          {
            label: "覆盖实例",
            value: stats.total_instances,
            detail: <MetricPills items={[{ label: "库/实例", value: perUnit(stats.active_databases, stats.total_instances), variant: "secondary" }]} />,
            icon: Server
          },
          {
            label: "总容量",
            value: formatStatisticsSizeMb(stats.total_size_mb),
            detail: (
              <MetricPills
                items={[
                  { label: "平均容量", value: formatStatisticsSizeMb(stats.avg_size_mb), variant: "secondary" },
                  { label: "最大容量", value: formatStatisticsSizeMb(stats.max_size_mb), variant: "secondary" }
                ]}
              />
            ),
            icon: HardDrive
          }
        ]}
      />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DistributionChartPanel title="数据库类型分布" badge="活跃数据库" icon={Database} rows={dbTypeRows} type="donut" />
        <DistributionChartPanel title="最新容量排行" badge="Top 10" icon={Trophy} rows={topRows(capacityRows)} type="horizontalBar" valueLabel="容量 MB" valueFormatter={formatStatisticsSizeMb} />
      </section>
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DistributionChartPanel title="实例数据库分布" badge="Top 10" icon={Server} rows={topRows(instanceRows)} type="horizontalBar" />
        <DistributionChartPanel title="同步状态分布" badge="当前台账" icon={RotateCw} rows={syncRows} type="bar" />
      </section>
    </>
  );
}

export function InstanceStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "instances"],
    queryFn: () => fetchInstanceStatistics()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <CommandBar backHref="/instances/" backLabel="返回实例列表" onRefresh={() => void runAction(statsQuery.refetch(), { success: "实例统计已刷新" })} />
      <PageHeader title="实例统计" />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <InstanceStatisticsContent stats={statsQuery.data} /> : null}
      </QueryPage>
    </main>
  );
}

export function AccountStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "accounts"],
    queryFn: () => fetchAccountStatisticsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <CommandBar backHref="/accounts/ledgers" backLabel="账户列表" onRefresh={() => void runAction(statsQuery.refetch(), { success: "账户统计已刷新" })} />
      <PageHeader title="账户统计" />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <AccountStatisticsContent snapshot={statsQuery.data} /> : null}
      </QueryPage>
    </main>
  );
}

export function DatabaseStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "databases"],
    queryFn: () => fetchDatabaseStatistics()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <CommandBar backHref="/databases/ledgers" backLabel="数据库台账" onRefresh={() => void runAction(statsQuery.refetch(), { success: "数据库统计已刷新" })} />
      <PageHeader title="数据库统计" />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <DatabaseStatisticsContent stats={statsQuery.data.stats} /> : null}
      </QueryPage>
    </main>
  );
}
