import { useQuery } from "@tanstack/react-query";
import { AlertCircle, BarChart3, Calculator, Database, HardDrive, RefreshCw, Server } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { triggerCapacityAggregation } from "@/api/actions";
import {
  fetchCapacityDatabaseOptions,
  fetchCapacityDatabaseSnapshot,
  fetchCapacityInstanceOptions,
  fetchCapacityInstanceSnapshot,
  getDefaultCapacityRange,
  type CapacityDatabaseOption,
  type CapacityDatabaseItem,
  type CapacityDatabaseSnapshot,
  type CapacityFilters,
  type CapacityInstanceItem,
  type CapacityInstanceOption,
  type CapacityInstanceSnapshot
} from "@/api/capacity";
import { MultiSelectDialogControl, SelectControl } from "@/components/shared/FormControls";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { runAction } from "@/utils/action-feedback";
import { formatCapacityMb as formatSizeMb } from "@/utils/display";

type Metric = {
  label: string;
  value: string | number;
  detail?: string;
  icon: typeof Server;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number | undefined | null): string {
  return `${(value ?? 0).toFixed(1)}%`;
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

type CapacityFilterState = {
  databaseName: string;
  dbTypes: string[];
  endDate: string;
  instanceIds: string[];
  periodType: string;
  startDate: string;
};

const CAPACITY_DB_TYPE_OPTIONS = [
  { label: "MySQL", value: "mysql" },
  { label: "PostgreSQL", value: "postgresql" },
  { label: "SQL Server", value: "sqlserver" },
  { label: "Oracle", value: "oracle" }
];

function defaultCapacityFilterState(): CapacityFilterState {
  const range = getDefaultCapacityRange();
  return {
    databaseName: "",
    dbTypes: [],
    endDate: range.endDate,
    instanceIds: [],
    periodType: "daily",
    startDate: range.startDate
  };
}

function toCapacityFilters(filters: CapacityFilterState): CapacityFilters {
  return {
    databaseName: filters.databaseName || undefined,
    dbTypes: filters.dbTypes.length > 0 ? filters.dbTypes : undefined,
    instanceIds: filters.instanceIds.length > 0 ? filters.instanceIds.map(Number) : undefined,
    periodType: filters.periodType,
    range: { startDate: filters.startDate, endDate: filters.endDate }
  };
}

function CapacityFilterBar({
  databaseOptions = [],
  dbTypeOptions,
  draft,
  includeDatabase,
  instanceOptions,
  onApply,
  onDraftChange,
  onReset
}: {
  databaseOptions?: Array<{ label: string; value: string }>;
  dbTypeOptions: Array<{ label: string; value: string }>;
  draft: CapacityFilterState;
  includeDatabase?: boolean;
  instanceOptions: Array<{ label: string; value: string }>;
  onApply: () => void;
  onDraftChange: (draft: CapacityFilterState) => void;
  onReset: () => void;
}) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  return (
    <form
      aria-label="容量筛选"
      className="grid grid-cols-5 gap-3 rounded-lg border bg-card p-3 max-xl:grid-cols-2 max-sm:grid-cols-1"
      onSubmit={handleSubmit}
    >
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>数据库类型</span>
        <MultiSelectDialogControl
          label="数据库类型"
          onValueChange={(dbTypes) => onDraftChange({ ...draft, databaseName: "", dbTypes, instanceIds: [] })}
          options={dbTypeOptions}
          value={draft.dbTypes}
        />
      </label>
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>实例</span>
        <MultiSelectDialogControl
          disabled={draft.dbTypes.length === 0}
          label="实例"
          onValueChange={(instanceIds) => onDraftChange({ ...draft, databaseName: instanceIds.length === 1 ? draft.databaseName : "", instanceIds })}
          options={instanceOptions}
          value={draft.instanceIds}
        />
      </label>
      {includeDatabase ? (
        <label className="grid gap-1.5 text-sm font-medium text-foreground">
          <span>数据库</span>
          <SelectControl
            disabled={draft.instanceIds.length !== 1}
            label="数据库"
            onValueChange={(databaseName) => onDraftChange({ ...draft, databaseName })}
            options={[{ label: "全部数据库", value: "" }, ...databaseOptions]}
            value={draft.databaseName}
          />
        </label>
      ) : null}
      <label className="grid gap-1.5 text-sm font-medium text-foreground">
        <span>周期</span>
        <SelectControl
          label="周期"
          onValueChange={(periodType) => onDraftChange({ ...draft, periodType })}
          options={[
            { label: "日", value: "daily" },
            { label: "周", value: "weekly" },
            { label: "月", value: "monthly" }
          ]}
          value={draft.periodType}
        />
      </label>
      <div className="flex items-end gap-2">
        <Button type="submit">应用筛选</Button>
        <Button onClick={onReset} type="button" variant="outline">
          重置
        </Button>
      </div>
    </form>
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

type CapacityChartValue = Record<string, number | string> & {
  label: string;
};

type CapacityChartSeries = {
  key: string;
  label: string;
  color: string;
};

type CapacityChartType = "line" | "bar";
type CapacityChartUnit = "size" | "change" | "percent";

const chartPalette = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

function chartButtonVariant(active: boolean): "default" | "outline" {
  return active ? "default" : "outline";
}

function CapacityChartControls({
  chartType,
  onChartTypeChange,
  onPeriodsChange,
  onTopNChange,
  periods,
  topN
}: {
  chartType: CapacityChartType;
  onChartTypeChange: (value: CapacityChartType) => void;
  onPeriodsChange: (value: number) => void;
  onTopNChange: (value: number) => void;
  periods: number;
  topN: number;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button onClick={() => onChartTypeChange("line")} size="sm" type="button" variant={chartButtonVariant(chartType === "line")}>
        折线图
      </Button>
      <Button onClick={() => onChartTypeChange("bar")} size="sm" type="button" variant={chartButtonVariant(chartType === "bar")}>
        柱状图
      </Button>
      {[5, 10, 20].map((value) => (
        <Button onClick={() => onTopNChange(value)} key={value} size="sm" type="button" variant={chartButtonVariant(topN === value)}>
          TOP{value}
        </Button>
      ))}
      {[7, 14, 30].map((value) => (
        <Button onClick={() => onPeriodsChange(value)} key={value} size="sm" type="button" variant={chartButtonVariant(periods === value)}>
          {value}
        </Button>
      ))}
    </div>
  );
}

function chartDateLabel(value: string | undefined): string {
  return value?.slice(0, 10) || "-";
}

function chartNumber(value: number | null | undefined, unit: CapacityChartUnit): number {
  const resolved = value ?? 0;
  if (unit === "size" || unit === "change") {
    return Number((resolved / 1024).toFixed(2));
  }
  return Number(resolved.toFixed(2));
}

function buildCapacityChartData<TItem>({
  getDate,
  getSeriesName,
  getValue,
  items,
  periods,
  topN,
  unit
}: {
  getDate: (item: TItem) => string | undefined;
  getSeriesName: (item: TItem) => string;
  getValue: (item: TItem) => number | null | undefined;
  items: TItem[];
  periods: number;
  topN: number;
  unit: CapacityChartUnit;
}): { data: CapacityChartValue[]; series: CapacityChartSeries[] } {
  const labels = [...new Set(items.map((item) => chartDateLabel(getDate(item))))].sort().slice(-periods);
  const labelSet = new Set(labels);
  const scopedItems = items.filter((item) => labelSet.has(chartDateLabel(getDate(item))));
  const seriesMax = new Map<string, number>();

  for (const item of scopedItems) {
    const name = getSeriesName(item);
    const value = Math.abs(getValue(item) ?? 0);
    seriesMax.set(name, Math.max(seriesMax.get(name) ?? 0, value));
  }

  const seriesNames = [...seriesMax.entries()]
    .sort((first, second) => second[1] - first[1])
    .slice(0, topN)
    .map(([name]) => name);
  const series = seriesNames.map((name, index) => ({
    key: `series_${index}`,
    label: name,
    color: chartPalette[index % chartPalette.length] ?? "var(--chart-1)"
  }));
  const seriesKeyByName = new Map(series.map((item) => [item.label, item.key]));
  const dataByDate = new Map<string, CapacityChartValue>(labels.map((label) => [label, { label }]));

  for (const item of scopedItems) {
    const name = getSeriesName(item);
    const key = seriesKeyByName.get(name);
    if (!key) {
      continue;
    }
    const label = chartDateLabel(getDate(item));
    const row = dataByDate.get(label);
    if (!row) {
      continue;
    }
    row[key] = chartNumber(getValue(item), unit);
  }

  return { data: [...dataByDate.values()], series };
}

function instanceChartBuilder(items: CapacityInstanceItem[], unit: CapacityChartUnit, topN: number, periods: number) {
  return buildCapacityChartData({
    getDate: (item) => item.period_start || item.period_end,
    getSeriesName: (item) => item.instance.name,
    getValue: (item) => {
      if (unit === "change") {
        return item.total_size_change_mb;
      }
      if (unit === "percent") {
        return item.total_size_change_percent ?? item.growth_rate;
      }
      return item.total_size_mb;
    },
    items,
    periods,
    topN,
    unit
  });
}

function databaseChartBuilder(items: CapacityDatabaseItem[], unit: CapacityChartUnit, topN: number, periods: number) {
  return buildCapacityChartData({
    getDate: (item) => item.period_start || item.period_end,
    getSeriesName: (item) => item.database_name,
    getValue: (item) => {
      if (unit === "change") {
        return item.size_change_mb;
      }
      if (unit === "percent") {
        return item.size_change_percent ?? item.growth_rate;
      }
      return item.avg_size_mb;
    },
    items,
    periods,
    topN,
    unit
  });
}

function CapacityChartPanel({
  buildData,
  title
}: {
  buildData: (topN: number, periods: number) => { data: CapacityChartValue[]; series: CapacityChartSeries[] };
  title: string;
}) {
  const [chartType, setChartType] = useState<CapacityChartType>("line");
  const [topN, setTopN] = useState(5);
  const [periods, setPeriods] = useState(7);
  const { data, series } = buildData(topN, periods);
  const config = Object.fromEntries(series.map((item) => [item.key, { label: item.label, color: item.color }])) satisfies ChartConfig;

  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-lg:grid">
          <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
          <CapacityChartControls chartType={chartType} onChartTypeChange={setChartType} onPeriodsChange={setPeriods} onTopNChange={setTopN} periods={periods} topN={topN} />
        </div>
        {data.length > 0 && series.length > 0 ? (
          <ChartContainer config={config} className="h-[280px] w-full">
            {chartType === "bar" ? (
              <BarChart accessibilityLayer data={data} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} width={64} />
                <ChartTooltip content={<ChartTooltipContent />} />
                {series.map((item) => (
                  <Bar dataKey={item.key} fill={`var(--color-${item.key})`} key={item.key} name={item.label} radius={[3, 3, 0, 0]} />
                ))}
              </BarChart>
            ) : (
              <LineChart accessibilityLayer data={data} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} width={64} />
                <ChartTooltip content={<ChartTooltipContent />} />
                {series.map((item) => (
                  <Line dataKey={item.key} dot={false} key={item.key} name={item.label} stroke={`var(--color-${item.key})`} strokeWidth={2} type="monotone" />
                ))}
              </LineChart>
            )}
          </ChartContainer>
        ) : (
          <p className="text-sm text-muted-foreground">暂无趋势数据</p>
        )}
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground" aria-label={`${title}图例`}>
          {series.map((item) => (
            <span className="inline-flex items-center gap-1.5" key={item.key}>
              <span className="size-2 rounded-[2px]" style={{ backgroundColor: item.color }} />
              <span>{item.label}</span>
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function CapacityCharts({
  databaseChangeItems,
  databasePercentItems,
  databaseTrendItems,
  instanceChangeItems,
  instancePercentItems,
  instanceTrendItems,
  scope
}: {
  databaseChangeItems?: CapacityDatabaseItem[];
  databasePercentItems?: CapacityDatabaseItem[];
  databaseTrendItems?: CapacityDatabaseItem[];
  instanceChangeItems?: CapacityInstanceItem[];
  instancePercentItems?: CapacityInstanceItem[];
  instanceTrendItems?: CapacityInstanceItem[];
  scope: "database" | "instance";
}) {
  const build = (unit: CapacityChartUnit) => {
    const databaseItems = unit === "change" ? databaseChangeItems : unit === "percent" ? databasePercentItems : databaseTrendItems;
    const instanceItems = unit === "change" ? instanceChangeItems : unit === "percent" ? instancePercentItems : instanceTrendItems;
    return (topN: number, periods: number) =>
      scope === "database"
        ? databaseChartBuilder(databaseItems ?? [], unit, topN, periods)
        : instanceChartBuilder(instanceItems ?? [], unit, topN, periods);
  };

  return (
    <section className="grid gap-2">
      <CapacityChartPanel title="容量统计趋势图" buildData={build("size")} />
      <CapacityChartPanel title="容量变化趋势图" buildData={build("change")} />
      <CapacityChartPanel title="容量变化趋势图 (百分比)" buildData={build("percent")} />
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

function capacityInstanceOptions(items: CapacityInstanceOption[]): Array<{ label: string; value: string }> {
  return items.map((item) => ({ label: item.display_name || item.name, value: String(item.id) }));
}

function capacityDatabaseOptions(items: CapacityDatabaseOption[]): Array<{ label: string; value: string }> {
  return items.map((item) => ({ label: item.database_name, value: item.database_name }));
}

export function CapacityInstancesPage() {
  const [filters, setFilters] = useState<CapacityFilterState>(() => defaultCapacityFilterState());
  const [draftFilters, setDraftFilters] = useState<CapacityFilterState>(() => defaultCapacityFilterState());
  const capacityQuery = useQuery({
    queryKey: ["capacity", "instances", filters],
    queryFn: () => fetchCapacityInstanceSnapshot(toCapacityFilters(filters))
  });
  const instanceOptionsQuery = useQuery({
    enabled: draftFilters.dbTypes.length > 0,
    queryKey: ["capacity", "instance-options", draftFilters.dbTypes],
    queryFn: () => fetchCapacityInstanceOptions(draftFilters.dbTypes),
    staleTime: 60_000
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader title="实例容量" />
      <CommandBar
        onAggregate={() => {
          void runAction(triggerCapacityAggregation("instance"), { success: "实例容量统计已触发" }).then(() => capacityQuery.refetch());
        }}
        onRefresh={() => {
          void runAction(capacityQuery.refetch(), { success: "实例容量数据已刷新" });
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
            <CapacityFilterBar
              dbTypeOptions={CAPACITY_DB_TYPE_OPTIONS}
              draft={draftFilters}
              instanceOptions={capacityInstanceOptions(instanceOptionsQuery.data ?? [])}
              onApply={() => setFilters(draftFilters)}
              onDraftChange={setDraftFilters}
              onReset={() => {
                const nextFilters = defaultCapacityFilterState();
                setDraftFilters(nextFilters);
                setFilters(nextFilters);
              }}
            />
            <CapacityCharts
              instanceChangeItems={snapshot.charts.change.items}
              instancePercentItems={snapshot.charts.percent.items}
              instanceTrendItems={snapshot.charts.trend.items}
              scope="instance"
            />
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function CapacityDatabasesPage() {
  const [filters, setFilters] = useState<CapacityFilterState>(() => defaultCapacityFilterState());
  const [draftFilters, setDraftFilters] = useState<CapacityFilterState>(() => defaultCapacityFilterState());
  const capacityQuery = useQuery({
    queryKey: ["capacity", "databases", filters],
    queryFn: () => fetchCapacityDatabaseSnapshot(toCapacityFilters(filters))
  });
  const instanceOptionsQuery = useQuery({
    enabled: draftFilters.dbTypes.length > 0,
    queryKey: ["capacity", "instance-options", draftFilters.dbTypes],
    queryFn: () => fetchCapacityInstanceOptions(draftFilters.dbTypes),
    staleTime: 60_000
  });
  const databaseOptionsQuery = useQuery({
    enabled: draftFilters.instanceIds.length === 1,
    queryKey: ["capacity", "database-options", draftFilters.instanceIds[0]],
    queryFn: () => fetchCapacityDatabaseOptions(draftFilters.instanceIds[0] ?? ""),
    staleTime: 60_000
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader title="数据库容量" />
      <CommandBar
        onAggregate={() => {
          void runAction(triggerCapacityAggregation("database"), { success: "数据库容量统计已触发" }).then(() => capacityQuery.refetch());
        }}
        onRefresh={() => {
          void runAction(capacityQuery.refetch(), { success: "数据库容量数据已刷新" });
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
            <CapacityFilterBar
              databaseOptions={capacityDatabaseOptions(databaseOptionsQuery.data ?? [])}
              dbTypeOptions={CAPACITY_DB_TYPE_OPTIONS}
              draft={draftFilters}
              includeDatabase
              instanceOptions={capacityInstanceOptions(instanceOptionsQuery.data ?? [])}
              onApply={() => setFilters(draftFilters)}
              onDraftChange={setDraftFilters}
              onReset={() => {
                const nextFilters = defaultCapacityFilterState();
                setDraftFilters(nextFilters);
                setFilters(nextFilters);
              }}
            />
            <CapacityCharts
              databaseChangeItems={snapshot.charts.change.items}
              databasePercentItems={snapshot.charts.percent.items}
              databaseTrendItems={snapshot.charts.trend.items}
              scope="database"
            />
          </>
        )}
      </QueryPage>
    </main>
  );
}
