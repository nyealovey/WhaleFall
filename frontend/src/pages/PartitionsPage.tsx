/* eslint-disable @typescript-eslint/no-unused-vars */
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Activity,
  AlertCircle,
  Boxes,
  ChartColumn,
  Clock,
  Database,
  Eye,
  ExternalLink,
  HardDrive,
  History,
  Layers3,
  ListChecks,
  Pause,
  Pencil,
  Play,
  PlugZap,
  Plus,
  RotateCcw,
  Settings,
  Tags,
  Trash2,
  UserCog,
  Zap
} from "lucide-react";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { CheckboxLine, SelectControl, SwitchField } from "@/components/shared/FormControls";
import { runAction } from "@/utils/action-feedback";
import { formatDateTime, formatStatus } from "@/utils/display";
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  assignTagsToInstances,
  autoClassifyAccounts,
  cancelSyncSession,
  cleanupPartitions,
  createAccountClassification,
  createAccountClassificationRule,
  createAdDomainConfig,
  createPartition,
  createCredential,
  createMySqlCluster,
  createSqlServerAvailabilityGroup,
  createSqlServerCluster,
  createTag,
  createUser,
  createVeeamSource,
  deleteAccountClassification,
  deleteAccountClassificationRule,
  deleteAdDomainConfig,
  deleteCredential,
  deleteSchedulerJob,
  deleteTag,
  deleteUser,
  deleteVeeamSource,
  disableVeeamSource,
  enableVeeamSource,
  pauseSchedulerJob,
  reloadSchedulerJobs,
  removeAllTagsFromInstances,
  removeTagsFromInstances,
  replaceMySqlClusterInstances,
  replaceSqlServerClusterInstances,
  resumeSchedulerJob,
  runSchedulerJob,
  saveAlertSettings,
  saveJumpServerSource,
  saveRiskRules,
  sendAlertTestEmail,
  sendFeishuTest,
  setAdDomainConfigEnabled,
  syncAdDomains,
  syncJumpServer,
  syncMySqlClusterTopology,
  syncSqlServerAgAccounts,
  syncSqlServerAvailabilityGroups,
  syncSqlServerClusterStatus,
  syncVeeam,
  testAdDomainConfig,
  unbindJumpServer,
  updateAccountClassification,
  updateAccountClassificationRule,
  updateAdDomainConfig,
  updateCredential,
  updateMySqlCluster,
  updateSchedulerJob,
  updateSqlServerAvailabilityGroup,
  updateSqlServerCluster,
  updateTag,
  updateUser,
  validateAccountClassificationRuleExpression,
  updateVeeamSource,
  type AccountClassificationRuleWritePayload,
  type AccountClassificationWritePayload,
  type AdDomainConfigPayload,
  type CredentialWritePayload,
  type JumpServerSourcePayload,
  type MySqlClusterPayload,
  type RiskRulePayload,
  type SchedulerJobWritePayload,
  type SqlServerAvailabilityGroupPayload,
  type SqlServerClusterPayload,
  type TagWritePayload,
  type UserWritePayload,
  type VeeamSourcePayload
} from "@/api/actions";
import {
  fetchAccountClassificationsSnapshot,
  fetchAccountClassificationPermissions,
  fetchAccountClassificationRuleDetail,
  fetchAccountScopeOptions,
  fetchClassificationStatisticsSnapshot,
  fetchClusterInstanceOptions,
  fetchClustersSnapshot,
  fetchCredentialsSnapshot,
  fetchMySqlClusterDetail,
  fetchPartitionsSnapshot,
  fetchSchedulerJobDetail,
  fetchSchedulerSnapshot,
  fetchSettingsSnapshot,
  fetchSqlServerAvailabilityGroupDashboard,
  fetchSqlServerClusterDetail,
  fetchTaskRunDetail,
  fetchTaskRunErrorLogs,
  fetchTaskRunsSnapshot,
  fetchTagBulkOptions,
  fetchTagsSnapshot,
  fetchUsersSnapshot,
  type AccountClassificationItem,
  type AccountClassificationRuleItem,
  type AccountScopeOption,
  type ClassificationRuleContributionItem,
  type ClassificationRuleOverviewItem,
  type ClassificationStatisticsFilters,
  type ClassificationStatisticsSnapshot,
  type ClusterDetailRecord,
  type ClusterInstanceOption,
  type ClusterItem,
  type CredentialItem,
  type MySqlClusterDetail,
  type PartitionMetricsFilters,
  type PartitionItem,
  type SchedulerJobDetail,
  type SchedulerJobItem,
  type SettingsSnapshot,
  type SqlServerAvailabilityGroupDashboard,
  type SqlServerClusterDetail,
  type TaskRunChildItem,
  type TaskRunDetail,
  type TaskRunErrorLogs,
  type TaskRunItem,
  type TagBulkOptions,
  type TagItem,
  type TagOptionItem,
  type TaggableInstanceItem,
  type UserItem
} from "@/api/readOnly";
import { DataTable } from "@/components/shared/DataTable";
import { useServerTableState } from "@/components/shared/useServerTableState";
import {
  ActiveField,
  CommandBar,
  DeleteConfirmDialog,
  DetailBlock,
  EmptyRows,
  ErrorState,
  FormField,
  JsonBlock,
  ListPanel,
  MetricGrid,
  PageHeader,
  QueryFrame,
  StatusBadge,
  asNumber,
  asText,
  canManageCatalog,
  endpointHost,
  formatNumber,
  formatPercent,
  isRunningState,
  isEmptyDetailValue,
  roleLabel,
  schedulerJobName,
  schedulerStatusLabel,
  statusLabel,
  statusVariant,
  syncCategory,
  syncDuration,
  syncProgress,
  syncRunId,
  syncSource,
  syncTaskName,
  type AccessUser,
  type Metric
} from "./ConsolePageScaffold";

function numberFromInput(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const partitionColumns: ColumnDef<PartitionItem>[] = [
  { accessorKey: "name", header: "分区名称", cell: ({ row }) => <span className="font-medium">{row.original.name ?? row.original.display_name ?? "-"}</span> },
  { accessorKey: "table_type", header: "表类型", cell: ({ row }) => row.original.table_type ?? "-" },
  { accessorKey: "size", header: "大小", cell: ({ row }) => <span className="font-mono text-xs">{row.original.size ?? "-"}</span> },
  { accessorKey: "record_count", header: "记录数", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.record_count)}</span> },
  { id: "partition_month", header: "分区月份", cell: ({ row }) => <span>{partitionMonthLabel(row.original)}</span> },
  { accessorKey: "status", header: "状态", cell: ({ row }) => <span className="text-xs text-muted-foreground">{partitionStatusLabel(row.original.status)}</span> }
];

function partitionMonthLabel(item: PartitionItem): string {
  const match = item.date?.match(/^(\d{4})-(\d{1,2})/);
  return match ? `${match[1]}年${Number(match[2])}月` : (item.display_name ?? item.name);
}

function partitionStatusLabel(value: string | undefined): string {
  return ({ current: "当前分区", past: "历史分区", future: "未来分区", unknown: "未知状态" } as Record<string, string>)[value ?? ""] ?? "未知状态";
}

const PARTITION_PERIOD_OPTIONS: Array<PartitionMetricsFilters & { label: string }> = [
  { label: "日", periodType: "daily", days: 7 },
  { label: "周", periodType: "weekly", days: 7 },
  { label: "月", periodType: "monthly", days: 7 },
  { label: "季", periodType: "quarterly", days: 7 }
];

const PARTITION_PERIOD_COPY: Record<string, { title: string; subtitle: string }> = {
  daily: { title: "日核心指标趋势", subtitle: "最近7天的核心指标统计" },
  weekly: { title: "周核心指标趋势", subtitle: "最近7周的核心指标统计" },
  monthly: { title: "月核心指标趋势", subtitle: "最近7个月的核心指标统计" },
  quarterly: { title: "季度核心指标趋势", subtitle: "最近7个季度的核心指标统计" }
};

const PARTITION_CHART_COLORS = ["#2f80ed", "#ff7aa2", "#4cc9c0", "#f59f00", "#8b5cf6", "#10b981"];

type PartitionChartSeries = {
  key: string;
  label: string;
  color: string;
  data: number[];
  strokeWidth: number;
};

type PartitionChartPoint = {
  label: string;
} & Record<string, number | string>;

function partitionPeriodCopy(periodType: string | undefined): { title: string; subtitle: string } {
  return PARTITION_PERIOD_COPY[periodType ?? ""] ?? PARTITION_PERIOD_COPY.daily;
}

function partitionSeriesColor(dataset: { borderColor?: string }, index: number): string {
  const color = dataset.borderColor?.trim();
  return color && color.toLowerCase() !== "#fff" && color.toLowerCase() !== "#ffffff" ? color : PARTITION_CHART_COLORS[index % PARTITION_CHART_COLORS.length];
}

function buildPartitionChart(
  labels: string[],
  datasets: Array<{ label?: string; data?: number[]; borderColor?: string; borderWidth?: number }>
): { chartData: PartitionChartPoint[]; chartConfig: ChartConfig; series: PartitionChartSeries[] } {
  const series = datasets
    .filter((dataset) => Array.isArray(dataset.data))
    .map((dataset, index) => ({
      key: `metric${index}`,
      label: dataset.label?.trim() || `指标 ${index + 1}`,
      color: partitionSeriesColor(dataset, index),
      data: dataset.data ?? [],
      strokeWidth: dataset.borderWidth ?? 3
    }));
  const chartConfig = Object.fromEntries(series.map((item) => [item.key, { label: item.label, color: item.color }])) satisfies ChartConfig;
  const chartData = labels.map((label, index) => {
    const point: PartitionChartPoint = { label };
    series.forEach((item) => {
      const value = Number(item.data[index] ?? 0);
      point[item.key] = Number.isFinite(value) ? value : 0;
    });
    return point;
  });
  return { chartData, chartConfig, series };
}

const PARTITION_YEAR_OPTIONS = Array.from({ length: 3 }, (_, index) => {
  const year = new Date().getFullYear() + index;
  return { label: `${year}年`, value: String(year) };
});

const PARTITION_MONTH_OPTIONS = Array.from({ length: 12 }, (_, index) => ({
  label: `${index + 1}月`,
  value: String(index + 1)
}));

export function PartitionsPage() {
  const [metricFilters, setMetricFilters] = useState<PartitionMetricsFilters>(PARTITION_PERIOD_OPTIONS[0]);
  const tableState = useServerTableState({ initialFilters: { status: "", tableType: "" } });
  const partitionQuery = {
    ...metricFilters,
    page: tableState.page,
    limit: tableState.pageSize,
    search: tableState.search,
    status: tableState.filters.status,
    tableType: tableState.filters.tableType
  };
  const query = useQuery({ queryKey: ["read-only", "partitions", partitionQuery], queryFn: () => fetchPartitionsSnapshot(partitionQuery), placeholderData: (previous) => previous });
  const [partitionYear, setPartitionYear] = useState("");
  const [partitionMonth, setPartitionMonth] = useState("");
  const [retentionMonths, setRetentionMonths] = useState("12");
  const [createOpen, setCreateOpen] = useState(false);
  const [cleanupOpen, setCleanupOpen] = useState(false);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Storage partitions" title="分区管理" description="展示分区健康状态、核心指标和分区列表，并支持创建分区与清理旧分区。" />
      <CommandBar>
        <Button
          onClick={() => {
            setCreateOpen(true);
          }}
          type="button"
        >
          <Plus aria-hidden />
          创建分区
        </Button>
        <Button
          onClick={() => {
            setCleanupOpen(true);
          }}
          type="button"
          variant="outline"
        >
          <Trash2 aria-hidden />
          清理旧分区
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="分区管理" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const status = snapshot.status.data;
          const partitions = status.partitions ?? [];
          const historyCount = partitions.filter((item) => item.status === "past").length;
          const currentPartitions = partitions.filter((item) => item.status === "current");
          const futureCount = partitions.filter((item) => item.status === "future").length;
          const currentPartition = currentPartitions[0];
          const averageRecords = (status.total_partitions ?? 0) > 0 ? Math.round((status.total_records ?? 0) / (status.total_partitions ?? 1)) : 0;
          const chartCopy = partitionPeriodCopy(snapshot.coreMetrics.periodType || metricFilters.periodType);
          const { chartData, chartConfig, series } = buildPartitionChart(snapshot.coreMetrics.labels, snapshot.coreMetrics.datasets);
          return (
            <>
              <MetricGrid
                label="分区指标"
                metrics={[
                  { label: "分区总数", value: status.total_partitions ?? snapshot.list.total, icon: Boxes },
                  { label: "历史分区", value: historyCount, icon: History },
                  { label: "当前分区", value: currentPartitions.length, icon: Activity },
                  { label: "未来分区", value: futureCount, icon: Clock },
                  { label: "总大小", value: status.total_size ?? "-", icon: Database },
                  { label: "总记录数", value: status.total_records ?? 0, icon: ListChecks },
                  { label: "当前分区大小", value: currentPartition?.size ?? "-", icon: HardDrive },
                  { label: "平均记录数", value: averageRecords, icon: ChartColumn },
                  { label: "当前记录数", value: currentPartition?.record_count ?? 0, icon: ListChecks },
                  { label: "数据库连接", value: status.status === "healthy" ? "正常" : "异常", icon: PlugZap }
                ]}
              />
              <section className="grid gap-2">
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3 max-sm:grid">
                      <div>
                        <CardTitle>{chartCopy.title}</CardTitle>
                        <CardDescription>{chartCopy.subtitle}</CardDescription>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {PARTITION_PERIOD_OPTIONS.map((option) => (
                          <Button
                            key={option.periodType}
                            onClick={() => setMetricFilters({ days: option.days, periodType: option.periodType })}
                            size="sm"
                            type="button"
                            variant={metricFilters.periodType === option.periodType ? "default" : "outline"}
                          >
                            {option.label}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="grid gap-3">
                    {chartData.length > 0 && series.length > 0 ? (
                      <>
                        <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm font-semibold text-muted-foreground">
                          {series.map((item) => (
                            <span className="inline-flex items-center gap-2" key={item.key}>
                              <span className="size-2.5 rounded-full" style={{ backgroundColor: `var(--color-${item.key})` }} />
                              {item.label}
                            </span>
                          ))}
                        </div>
                        <ChartContainer config={chartConfig} className="h-[340px] w-full">
                          <LineChart accessibilityLayer data={chartData} margin={{ left: 12, right: 16, top: 12, bottom: 8 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                            <YAxis
                              tickLine={false}
                              axisLine={false}
                              tickMargin={8}
                              width={72}
                              label={{ value: snapshot.coreMetrics.yAxisLabel || "数量", angle: -90, position: "insideLeft", offset: -2 }}
                            />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            {series.map((item) => (
                              <Line
                                activeDot={{ r: 5 }}
                                connectNulls
                                dataKey={item.key}
                                dot={{ r: 3, strokeWidth: 2 }}
                                key={item.key}
                                name={item.label}
                                stroke={`var(--color-${item.key})`}
                                strokeWidth={item.strokeWidth}
                                type="monotone"
                              />
                            ))}
                          </LineChart>
                        </ChartContainer>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无核心指标</p>
                    )}
                  </CardContent>
                </Card>
                <ListPanel title="分区列表" count={snapshot.list.total}>
                  <DataTable
                    columns={partitionColumns}
                    data={snapshot.list.items}
                    filters={[
                      { columnId: "table_type", label: "类型", options: [{ label: "统计", value: "stats" }, { label: "聚合", value: "aggregations" }, { label: "实例统计", value: "instance_stats" }, { label: "实例聚合", value: "instance_aggregations" }], value: tableState.filters.tableType, onValueChange: (value) => tableState.setFilter("tableType", value) },
                      { columnId: "status", label: "状态", options: [{ label: "当前", value: "current" }, { label: "历史", value: "past" }, { label: "未来", value: "future" }, { label: "未知", value: "unknown" }], value: tableState.filters.status, onValueChange: (value) => tableState.setFilter("status", value) }
                    ]}
                    onSearchChange={tableState.setSearchInput}
                    onResetFilters={tableState.reset}
                    pagination={{ page: snapshot.list.page, pageSize: tableState.pageSize, pages: snapshot.list.pages ?? 1, total: snapshot.list.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
                    searchPlaceholder="搜索分区或数据表"
                    searchValue={tableState.searchInput}
                  />
                </ListPanel>
              </section>
            </>
          );
        }}
      </QueryFrame>
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="w-[min(calc(100vw-2rem),36rem)]">
          <DialogHeader>
            <DialogTitle>创建分区</DialogTitle>
            <DialogDescription>选择年月后创建对应的月度分区。</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="年份">
              <SelectControl label="年份" onValueChange={setPartitionYear} options={PARTITION_YEAR_OPTIONS} value={partitionYear} />
            </FormField>
            <FormField label="月份">
              <SelectControl label="月份" onValueChange={setPartitionMonth} options={PARTITION_MONTH_OPTIONS} value={partitionMonth} />
            </FormField>
          </div>
          <DialogFooter>
            <Button onClick={() => setCreateOpen(false)} type="button" variant="outline">
              取消
            </Button>
            <Button
              disabled={!partitionYear || !partitionMonth}
              onClick={() => {
                const date = `${partitionYear}-${partitionMonth.padStart(2, "0")}-01`;
                setCreateOpen(false);
                void runAction(createPartition(date), { success: "分区创建已触发" }).then(() => query.refetch());
              }}
              type="button"
            >
              创建分区
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <AlertDialog open={cleanupOpen} onOpenChange={setCleanupOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>清理旧分区</AlertDialogTitle>
            <AlertDialogDescription>
              超过保留月数的分区将被永久删除，包含历史数据、索引与统计。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <FormField label="保留月数">
            <Input max={60} min={1} onChange={(event) => setRetentionMonths(event.target.value)} type="number" value={retentionMonths} />
          </FormField>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                const months = numberFromInput(retentionMonths, 12);
                setCleanupOpen(false);
                void runAction(cleanupPartitions(months), { success: "旧分区清理已触发" }).then(() => query.refetch());
              }}
            >
              开始清理
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
