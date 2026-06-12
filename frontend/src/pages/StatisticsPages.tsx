import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CircleCheck,
  Database,
  ExternalLink,
  HardDrive,
  List,
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
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  fetchAccountStatisticsSnapshot,
  fetchDatabaseStatistics,
  fetchInstanceStatistics,
  type AccountStatisticsSnapshot,
  type DatabaseStatistics,
  type InstanceStatistics
} from "@/api/statistics";
import { DataTable } from "@/components/shared/DataTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

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

type VersionRow = {
  dbType: string;
  version: string;
  count: number;
  percent: number;
};

type OwnerRow = {
  type: string;
  label: string;
  total: number;
  active: number;
  deleted: number;
  percent: number;
};

type AdStatusRow = {
  label: string;
  key: string;
  variant: "default" | "secondary" | "destructive" | "outline";
  total: number;
  instance: number;
  ag: number;
};

type CapacityRow = DatabaseStatistics["capacity_rankings"][number];

const chartConfig = {
  value: { label: "数量", color: "var(--chart-1)" },
  count: { label: "数量", color: "var(--chart-2)" }
} satisfies ChartConfig;

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatSizeMb(value: number | undefined): string {
  const size = value ?? 0;
  if (size >= 1024) {
    return `${(size / 1024).toFixed(2)} GB`;
  }
  return `${size.toFixed(0)} MB`;
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

function countFromUnknown(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  return numberField(asRecord(value), ["total_accounts", "account_count", "count", "total", "matched_accounts_count", "value"]);
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

function PercentCell({ value }: { value: number | undefined }) {
  const resolved = value ?? 0;
  return (
    <div className="grid min-w-28 gap-1">
      <Progress aria-label={`占比 ${formatPercent(resolved)}`} value={resolved} />
      <span className="font-mono text-xs text-muted-foreground">{formatPercent(resolved)}</span>
    </div>
  );
}

function LabelCell({ item }: { item: DistributionRow }) {
  return (
    <div className="grid gap-1">
      <div className="flex flex-wrap items-center gap-1.5">
        {item.badge ? <Badge variant={toneForBadge(item.badge)}>{statusLabel(item.badge)}</Badge> : null}
        <span className="font-medium">{item.label}</span>
      </div>
      {item.detail ? <span className="text-xs text-muted-foreground">{item.detail}</span> : null}
      {item.meta?.length ? (
        <div className="flex flex-wrap gap-1">
          {item.meta.map((meta) => (
            <Badge variant={meta.variant ?? "secondary"} key={`${item.label}-${meta.label}`}>
              {meta.label} {meta.value}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}

const distributionColumns: ColumnDef<DistributionRow>[] = [
  {
    accessorKey: "label",
    header: "名称",
    cell: ({ row }) => <LabelCell item={row.original} />
  },
  {
    accessorKey: "value",
    header: "数量",
    cell: ({ row }) => <span className="font-mono text-xs">{typeof row.original.value === "number" ? formatNumber(row.original.value) : row.original.value}</span>
  },
  {
    accessorKey: "percent",
    header: "占比",
    cell: ({ row }) => <PercentCell value={row.original.percent} />
  }
];

function DataPanel<TData, TValue>({
  title,
  description,
  badge,
  icon,
  columns,
  data,
  emptyText,
  searchPlaceholder
}: {
  title: string;
  description?: string;
  badge?: string;
  icon: typeof Server;
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  emptyText: string;
  searchPlaceholder?: string;
}) {
  const Icon = icon;
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Icon aria-hidden size={18} />
            <span>{title}</span>
          </CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {badge ? <Badge variant="outline">{badge}</Badge> : null}
      </CardHeader>
      <CardContent>
        <DataTable columns={columns} data={data} emptyText={emptyText} searchPlaceholder={searchPlaceholder ?? `${title}搜索`} />
      </CardContent>
    </Card>
  );
}

function ChartPanel({
  title,
  description,
  badge,
  icon,
  data,
  type = "bar"
}: {
  title: string;
  description?: string;
  badge?: string;
  icon: typeof Server;
  data: Array<{ label: string; value: number }>;
  type?: "area" | "bar";
}) {
  const Icon = icon;
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Icon aria-hidden size={18} />
            <span>{title}</span>
          </CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {badge ? <Badge variant="outline">{badge}</Badge> : null}
      </CardHeader>
      <CardContent>
        {data.length > 0 ? (
          <ChartContainer config={chartConfig} className="h-[260px] w-full">
            {type === "area" ? (
              <AreaChart accessibilityLayer data={data} margin={{ left: -12, right: 12, top: 12, bottom: 0 }}>
                <defs>
                  <linearGradient id={`${title}-fill`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-value)" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="var(--color-value)" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area dataKey="value" name="数量" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill={`url(#${title}-fill)`} />
              </AreaChart>
            ) : (
              <BarChart accessibilityLayer data={data} margin={{ left: -12, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="value" name="数量" radius={[4, 4, 0, 0]} fill="var(--color-count)" />
              </BarChart>
            )}
          </ChartContainer>
        ) : (
          <p className="text-sm text-muted-foreground">暂无图表数据</p>
        )}
      </CardContent>
    </Card>
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

function recordRows(record: Record<string, unknown>, total: number, options: { labelMap?: Record<string, string>; countKeys?: string[] } = {}): DistributionRow[] {
  return Object.entries(record)
    .filter(([key]) => !["total", "items"].includes(key))
    .map(([key, value]) => {
      const meta = asRecord(value);
      const count = numberField(meta, options.countKeys ?? ["total_accounts", "account_count", "count", "total", "matched_accounts_count", "value"]) || countFromUnknown(value);
      return {
        label: options.labelMap?.[key] ?? key,
        value: count,
        percent: ratio(count, total)
      };
    })
    .filter((row) => Number(row.value) > 0);
}

function InstanceStatisticsContent({ stats }: { stats: InstanceStatistics }) {
  const current = stats.current_instances;
  const dbTypeRows = toDistributionRows(stats.db_type_stats, current, { label: (item) => item.db_type, count: (item) => item.count });
  const portRows = toDistributionRows(stats.port_stats, current, { label: (item) => String(item.port), count: (item) => item.count });
  const versionRows: VersionRow[] = stats.version_stats.map((item) => ({
    dbType: item.db_type,
    version: item.version || "未知版本",
    count: item.count,
    percent: ratio(item.count, current)
  }));
  const backupRows = toDistributionRows(stats.backup_status_stats, current, {
    label: (item) => statusLabel(item.backup_status),
    count: (item) => item.count,
    badge: (item) => item.backup_status
  });
  const versionChartData = versionRows.map((row) => ({ label: `${row.dbType} ${row.version}`, value: row.count }));

  const versionColumns: ColumnDef<VersionRow>[] = [
    { accessorKey: "dbType", header: "类型", cell: ({ row }) => <Badge variant="outline">{row.original.dbType}</Badge> },
    { accessorKey: "version", header: "版本", cell: ({ row }) => <Badge variant="secondary">{row.original.version}</Badge> },
    { accessorKey: "count", header: "数量", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.count)}</span> },
    { accessorKey: "percent", header: "占比", cell: ({ row }) => <PercentCell value={row.original.percent} /> }
  ];

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
      <ChartPanel title="备份状态分布" description="Veeam" badge="Veeam" icon={HardDrive} data={backupRows.map((row) => ({ label: row.label, value: Number(row.value) }))} type="area" />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DataPanel title="数据库类型分布" description={`共 ${formatNumber(stats.db_types_count)} 类`} badge="实时" icon={PieChart} columns={distributionColumns} data={dbTypeRows} emptyText="暂无数据库类型数据" />
        <DataPanel title="端口分布" badge="Top 10" icon={Network} columns={distributionColumns} data={portRows} emptyText="暂无端口数据" />
        <DataPanel title="数据库版本统计" badge="同步数据" icon={Tags} columns={versionColumns} data={versionRows} emptyText="暂无版本数据" />
        <ChartPanel title="版本分布图" description="按类型分组" badge="按类型分组" icon={PieChart} data={versionChartData} />
      </section>
    </>
  );
}

function AccountStatisticsContent({ snapshot }: { snapshot: AccountStatisticsSnapshot }) {
  const { summary } = snapshot;
  const total = summary.total_accounts;
  const ownerRows: OwnerRow[] = Object.entries(summary.owner_type_stats ?? {}).map(([type, value]) => {
    const meta = asRecord(value);
    const count = numberField(meta, ["total", "total_accounts", "count"]);
    return {
      type,
      label: type === "sqlserver_ag" ? "AG 账户" : type === "instance" ? "实例账户" : type,
      total: count,
      active: numberField(meta, ["active", "active_accounts"]),
      deleted: numberField(meta, ["deleted", "deleted_accounts"]),
      percent: numberField(meta, ["percent"]) || ratio(count, total)
    };
  });
  const ownerColumns: ColumnDef<OwnerRow>[] = [
    {
      accessorKey: "label",
      header: "来源",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <Badge variant="outline">{row.original.label}</Badge>
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary">启用 {formatNumber(row.original.active)}</Badge>
            <Badge variant="secondary">删除 {formatNumber(row.original.deleted)}</Badge>
          </div>
        </div>
      )
    },
    { accessorKey: "total", header: "账户数", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.total)}</span> },
    { accessorKey: "percent", header: "占比", cell: ({ row }) => <PercentCell value={row.original.percent} /> }
  ];

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
  const adColumns: ColumnDef<AdStatusRow>[] = [
    { accessorKey: "label", header: "状态", cell: ({ row }) => <Badge variant={row.original.variant}>{row.original.label}</Badge> },
    { accessorKey: "total", header: "合计", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.total)}</span> },
    { accessorKey: "instance", header: "实例账户", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance)}</span> },
    { accessorKey: "ag", header: "AG 账户", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.ag)}</span> }
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
  const classificationRows = recordRows(snapshot.classifications, total, { countKeys: ["account_count", "total_accounts", "count", "total"] });
  const ruleRows: DistributionRow[] = snapshot.rules.rule_stats.slice(0, 8).map((item) => ({
    label: `rule #${item.rule_id}`,
    value: item.matched_accounts_count,
    percent: ratio(item.matched_accounts_count, total)
  }));

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
        <DataPanel title="账户来源分布" description="台账口径" badge="台账口径" icon={BarChart3} columns={ownerColumns} data={ownerRows} emptyText="暂无账户来源数据" />
        <DataPanel title="AD 账户对比" description="活跃账户" badge="活跃账户" icon={UserLock} columns={adColumns} data={adRows} emptyText="暂无 AD 账户数据" />
      </section>
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DataPanel title="数据库类型分布" description="实时" badge="实时" icon={Database} columns={distributionColumns} data={dbTypeRows} emptyText="暂无数据库类型数据" />
        <DataPanel title="账户分类分布" description="当前规则" badge="当前规则" icon={Tags} columns={distributionColumns} data={classificationRows} emptyText="暂无账户分类数据" />
        <DataPanel title="规则命中" description="规则命中统计" badge="当前规则" icon={List} columns={distributionColumns} data={ruleRows} emptyText="暂无规则命中统计" />
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
  const capacityColumns: ColumnDef<CapacityRow>[] = [
    {
      accessorKey: "database_name",
      header: "数据库",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <span className="font-medium">{row.original.database_name}</span>
          <span className="text-xs text-muted-foreground">
            {row.original.instance_name} · {row.original.db_type}
          </span>
        </div>
      )
    },
    { accessorKey: "size_label", header: "大小", cell: ({ row }) => <span className="font-mono text-xs">{row.original.size_label}</span> },
    { accessorKey: "collected_at", header: "采集时间", cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDateTime(row.original.collected_at)}</span> }
  ];

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
            value: formatSizeMb(stats.total_size_mb),
            detail: (
              <MetricPills
                items={[
                  { label: "平均容量", value: formatSizeMb(stats.avg_size_mb), variant: "secondary" },
                  { label: "最大容量", value: formatSizeMb(stats.max_size_mb), variant: "secondary" }
                ]}
              />
            ),
            icon: HardDrive
          }
        ]}
      />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DataPanel title="数据库类型分布" description="活跃数据库" badge="活跃数据库" icon={Database} columns={distributionColumns} data={dbTypeRows} emptyText="暂无数据库类型数据" />
        <DataPanel title="实例数据库分布" description="Top 10" badge="Top 10" icon={Server} columns={distributionColumns} data={instanceRows.slice(0, 10)} emptyText="暂无实例分布数据" />
        <DataPanel title="同步状态分布" description="当前台账" badge="当前台账" icon={RotateCw} columns={distributionColumns} data={syncRows} emptyText="暂无同步状态数据" />
        <DataPanel title="最新容量排行" description="Top 10" badge="Top 10" icon={Trophy} columns={capacityColumns} data={stats.capacity_rankings.slice(0, 10)} emptyText="暂无容量排行数据" />
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
      <CommandBar backHref="/instances/" backLabel="返回实例列表" onRefresh={() => void statsQuery.refetch()} />
      <PageHeader
        eyebrow="Instance statistics"
        title="实例统计"
        description="按实例状态、数据库类型、端口、版本和备份覆盖读取统计数据。"
        legacyHref="/instances/statistics"
      />
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
      <CommandBar backHref="/accounts/ledgers" backLabel="账户列表" onRefresh={() => void statsQuery.refetch()} />
      <PageHeader
        eyebrow="Account statistics"
        title="账户统计"
        description="聚合账户状态、实例范围、数据库类型、分类和规则命中信号。"
        legacyHref="/accounts/statistics"
      />
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
      <CommandBar backHref="/databases/ledgers" backLabel="数据库台账" onRefresh={() => void statsQuery.refetch()} />
      <PageHeader
        eyebrow="Database statistics"
        title="数据库统计"
        description="展示数据库数量、同步状态、实例分布和最新容量排行。"
        legacyHref="/databases/statistics"
      />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <DatabaseStatisticsContent stats={statsQuery.data.stats} /> : null}
      </QueryPage>
    </main>
  );
}
