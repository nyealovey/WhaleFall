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
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

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

function createSyncSessionColumns({
  onCancel,
  onViewDetail
}: {
  onCancel: (sessionId: string) => void;
  onViewDetail: (sessionId: string) => void;
}): ColumnDef<TaskRunItem>[] {
  return [
    {
      id: "run_id",
      header: "运行ID",
      accessorFn: (item) => syncRunId(item),
      cell: ({ row }) => <span className="font-mono text-xs">{syncRunId(row.original)}</span>
    },
    {
      accessorKey: "status",
      header: "状态",
      cell: ({ row }) => <StatusBadge value={row.original.status} />
    },
    {
      id: "progress",
      header: "进度",
      cell: ({ row }) => {
        const progress = syncProgress(row.original);
        return (
          <div className="grid min-w-40 gap-2">
            <Progress aria-label={`${syncRunId(row.original)} 进度`} value={progress.percent} />
            <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>{progress.percent}%</span>
              <span>
                {formatNumber(progress.completed)}/{formatNumber(progress.total)} · failed {formatNumber(progress.failed)}
              </span>
            </div>
          </div>
        );
      }
    },
    {
      id: "task",
      header: "任务",
      accessorFn: (item) => syncTaskName(item),
      cell: ({ row }) => (
        <div className="grid gap-1">
          <span className="font-medium">{syncTaskName(row.original)}</span>
          <span className="font-mono text-xs text-muted-foreground">{row.original.task_key}</span>
        </div>
      )
    },
    {
      id: "trigger_source",
      header: "来源",
      accessorFn: (item) => syncSource(item),
      cell: ({ row }) => <Badge variant="outline">{syncSource(row.original)}</Badge>
    },
    {
      id: "task_category",
      header: "分类",
      accessorFn: (item) => syncCategory(item),
      cell: ({ row }) => <Badge variant="secondary">{syncCategory(row.original)}</Badge>
    },
    {
      accessorKey: "started_at",
      header: "开始时间",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.started_at ?? "-"}</span>
    },
    {
      id: "duration",
      header: "耗时",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{syncDuration(row.original)}</span>
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => {
        const runId = syncRunId(row.original);
        return (
          <div className="flex items-center gap-1">
            <Button aria-label={`查看详情 ${runId}`} onClick={() => onViewDetail(runId)} size="icon" type="button" variant="ghost">
              <ExternalLink aria-hidden />
            </Button>
            {row.original.status === "running" ? (
              <Button aria-label={`取消任务 ${runId}`} onClick={() => onCancel(runId)} size="icon" type="button" variant="ghost">
                <Pause aria-hidden />
              </Button>
            ) : null}
          </div>
        );
      }
    }
  ];
}


function SyncDetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 rounded-md border bg-secondary/30 p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  );
}

function SyncSessionRecordTable({
  emptyLabel,
  records,
  title
}: {
  emptyLabel: string;
  records: TaskRunChildItem[];
  title: string;
}) {
  return (
    <section className="grid gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Badge variant="secondary">{formatNumber(records.length)} 条</Badge>
      </div>
      <div className="overflow-hidden rounded-md border">
        <Table>
          <TableHeader className="text-xs">
            <TableRow>
              <TableHead>实例</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>同步项</TableHead>
              <TableHead>变更</TableHead>
              <TableHead>错误</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.length === 0 ? (
              <TableRow>
                <TableCell className="px-3 py-8 text-center text-sm text-muted-foreground" colSpan={6}>
                  {emptyLabel}
                </TableCell>
              </TableRow>
            ) : null}
            {records.map((record) => (
              <TableRow key={record.id}>
                <TableCell>
                  <div className="grid gap-1">
                    <span className="font-medium">{record.item_name ?? record.item_key}</span>
                    <span className="font-mono text-xs text-muted-foreground">{record.instance_id ? `#${record.instance_id}` : record.item_type}</span>
                  </div>
                </TableCell>
                <TableCell>{record.item_type ?? "-"}</TableCell>
                <TableCell>
                  <StatusBadge value={record.status} />
                </TableCell>
                <TableCell className="font-mono text-xs">{formatNumber(Number(record.metrics_json?.items_synced ?? 0))}</TableCell>
                <TableCell className="font-mono text-xs">
                  +{formatNumber(Number(record.metrics_json?.items_created ?? 0))} / ~{formatNumber(Number(record.metrics_json?.items_updated ?? 0))} / -{formatNumber(Number(record.metrics_json?.items_deleted ?? 0))}
                </TableCell>
                <TableCell className="max-w-[18rem] break-words text-sm text-muted-foreground">{record.error_message || "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}

function SyncSessionDetailDialog({
  onOpenChange,
  open,
  sessionId
}: {
  onOpenChange: (open: boolean) => void;
  open: boolean;
  sessionId: string | null;
}) {
  const detailQuery = useQuery<TaskRunDetail>({
    enabled: open && sessionId !== null,
    queryKey: ["read-only", "sync-session-detail", sessionId],
    queryFn: () => {
      if (sessionId === null) {
        throw new Error("Missing sync session id");
      }
      return fetchTaskRunDetail(sessionId);
    }
  });
  const errorsQuery = useQuery<TaskRunErrorLogs>({
    enabled: open && sessionId !== null,
    queryKey: ["read-only", "sync-session-error-logs", sessionId],
    queryFn: () => {
      if (sessionId === null) {
        throw new Error("Missing sync session id");
      }
      return fetchTaskRunErrorLogs(sessionId);
    }
  });
  const session = detailQuery.data?.run;
  const progress = session ? syncProgress(session) : null;
  const progressPercent = progress?.percent ?? 0;
  const errorRecords = errorsQuery.data?.items ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(calc(100vw-2rem),64rem)]">
        <DialogHeader>
          <DialogTitle>会话详情 {sessionId ?? ""}</DialogTitle>
          <DialogDescription>同步会话摘要、实例执行记录和错误日志。</DialogDescription>
        </DialogHeader>
        {detailQuery.isLoading || errorsQuery.isLoading ? (
          <div className="grid gap-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : null}
        {detailQuery.isError || errorsQuery.isError ? (
          <Alert variant="destructive">
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>会话详情加载失败</AlertDescription>
          </Alert>
        ) : null}
        {session ? (
          <div className="grid gap-4">
            <dl className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1">
              <SyncDetailField label="运行 ID">
                <span className="font-mono text-xs">{syncRunId(session)}</span>
              </SyncDetailField>
              <SyncDetailField label="状态">
                <StatusBadge value={session.status} />
              </SyncDetailField>
              <SyncDetailField label="任务">
                <div className="grid gap-1">
                  <span>{syncTaskName(session)}</span>
                  <span className="font-mono text-xs text-muted-foreground">{session.task_key}</span>
                </div>
              </SyncDetailField>
              <SyncDetailField label="来源/分类">
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline">{syncSource(session)}</Badge>
                  <Badge variant="secondary">{syncCategory(session)}</Badge>
                </div>
              </SyncDetailField>
              <SyncDetailField label="开始时间">
                <span className="font-mono text-xs">{session.started_at ?? "-"}</span>
              </SyncDetailField>
              <SyncDetailField label="完成时间">
                <span className="font-mono text-xs">{session.completed_at ?? "-"}</span>
              </SyncDetailField>
              <SyncDetailField label="耗时">
                <span>{syncDuration(session)}</span>
              </SyncDetailField>
              <SyncDetailField label="错误日志">
                <span className="font-mono">{formatNumber(errorsQuery.data?.error_count)}</span>
              </SyncDetailField>
            </dl>
            <div className="grid gap-2 rounded-md border bg-secondary/20 p-3">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="font-medium">执行进度</span>
                <span className="font-mono text-xs text-muted-foreground">
                  {formatNumber(progress?.completed)}/{formatNumber(progress?.total)} · failed {formatNumber(progress?.failed)}
                </span>
              </div>
              <Progress value={progressPercent} />
            </div>
            <SyncSessionRecordTable emptyLabel="暂无实例执行记录" records={detailQuery.data?.items ?? []} title="实例执行记录" />
            <SyncSessionRecordTable emptyLabel="暂无错误日志" records={errorRecords} title="错误日志" />
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export function SyncSessionsPage() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [cancelSessionId, setCancelSessionId] = useState<string | null>(null);
  const columns = useMemo(
    () => createSyncSessionColumns({ onCancel: setCancelSessionId, onViewDetail: setSelectedSessionId }),
    [setCancelSessionId, setSelectedSessionId]
  );
  const table = useServerTableState({ initialFilters: { triggerSource: "", taskCategory: "", status: "" } });
  const query = useQuery({
    queryKey: ["read-only", "task-runs", table.page, table.pageSize, table.search, table.filters],
    queryFn: () => fetchTaskRunsSnapshot({ page: table.page, limit: table.pageSize, taskKey: table.search, triggerSource: table.filters.triggerSource, taskCategory: table.filters.taskCategory, status: table.filters.status }),
    placeholderData: (previous) => previous
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation sessions" title="会话中心" description="展示同步会话、实例执行详情、错误日志，并支持取消运行中会话。" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="会话中心" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <ListPanel title="同步会话" count={snapshot.total}>
              <DataTable
                columns={columns}
                data={snapshot.items}
                filters={[
                  { columnId: "trigger_source", label: "来源", options: [{ label: "定时", value: "scheduled" }, { label: "手动", value: "manual" }, { label: "API", value: "api" }], value: table.filters.triggerSource, onValueChange: (value) => table.setFilter("triggerSource", value) },
                  { columnId: "task_category", label: "分类", options: [{ label: "账户", value: "account" }, { label: "容量", value: "capacity" }, { label: "聚合", value: "aggregation" }, { label: "分类", value: "classification" }, { label: "群集", value: "cluster" }, { label: "告警", value: "alert" }, { label: "其他", value: "other" }], value: table.filters.taskCategory, onValueChange: (value) => table.setFilter("taskCategory", value) },
                  { columnId: "status", label: "状态", options: [{ label: "运行中", value: "running" }, { label: "已完成", value: "completed" }, { label: "部分完成", value: "partial" }, { label: "失败", value: "failed" }, { label: "已取消", value: "cancelled" }], value: table.filters.status, onValueChange: (value) => table.setFilter("status", value) }
                ]}
                onSearchChange={table.setSearchInput}
                onResetFilters={table.reset}
                pagination={{ page: table.page, pageSize: table.pageSize, pages: snapshot.pages ?? 1, total: snapshot.total, onPageChange: table.setPage, onPageSizeChange: table.setPageSize }}
                searchPlaceholder="搜索运行 ID、任务或来源"
                searchValue={table.searchInput}
              />
          </ListPanel>
        )}
      </QueryFrame>
      <SyncSessionDetailDialog
        onOpenChange={(open) => {
          if (!open) {
            setSelectedSessionId(null);
          }
        }}
        open={selectedSessionId !== null}
        sessionId={selectedSessionId}
      />
      <AlertDialog
        open={cancelSessionId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCancelSessionId(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认取消会话 {cancelSessionId ?? ""}</AlertDialogTitle>
            <AlertDialogDescription>取消后，仍在执行的同步任务会被中止。已完成的实例记录不会回滚。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!cancelSessionId) {
                  return;
                }
                const targetSessionId = cancelSessionId;
                setCancelSessionId(null);
                void runAction(cancelSyncSession(targetSessionId), { success: "会话已取消" }).then(() => query.refetch());
              }}
            >
              确认取消会话
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
