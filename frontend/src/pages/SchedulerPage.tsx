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
  DetailBlock,
  EmptyRows,
  ErrorState,
  FormField,
  ListPanel,
  MetricGrid,
  PageHeader,
  QueryFrame,
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

function SchedulerJobDetailDialog({
  item,
  onOpenChange,
  open
}: {
  item: SchedulerJobItem | null;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const query = useQuery({
    enabled: open && Boolean(item),
    queryKey: ["read-only", "scheduler-job-detail", item?.id],
    queryFn: () => fetchSchedulerJobDetail(item?.id ?? "")
  });
  const detail = item
    ? ({
        ...item,
        ...(query.data ?? {}),
        next_run_time: query.data?.next_run_time ?? item.next_run_time,
        last_run_time: query.data?.last_run_time ?? item.last_run_time,
        state: query.data?.state ?? item.state
      } as SchedulerJobDetail)
    : null;

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),52rem)]">
        <DialogHeader>
          <DialogTitle>任务详情 {item ? schedulerJobName(item) : ""}</DialogTitle>
          <DialogDescription>展示调度任务的触发器、执行函数和运行参数。</DialogDescription>
        </DialogHeader>
        {query.isLoading ? (
          <div className="grid gap-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : null}
        {query.isError ? <Alert variant="destructive"><AlertCircle aria-hidden size={16} /><AlertDescription>任务详情加载失败</AlertDescription></Alert> : null}
        {detail ? (
          <div className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
            <DetailBlock label="任务 ID"><span className="font-mono">{detail.task_id ?? detail.id}</span></DetailBlock>
            <DetailBlock label="执行函数"><span className="font-mono">{asText(detail.func)}</span></DetailBlock>
            <DetailBlock label="触发器"><span className="font-mono">{asText(detail.trigger ?? detail.trigger_type)}</span></DetailBlock>
            <DetailBlock label="下次运行"><span className="font-mono">{detail.next_run_time ? formatDateTime(detail.next_run_time) : "未计划"}</span></DetailBlock>
            <DetailBlock label="上次运行"><span className="font-mono">{detail.last_run_time ? formatDateTime(detail.last_run_time) : "从未运行"}</span></DetailBlock>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}


function cronExpressionFromJob(job: SchedulerJobItem): string {
  const args = job.trigger_args;
  if (typeof args === "string") {
    return args;
  }
  if (!args || typeof args !== "object") {
    return "* * * * *";
  }
  const record = args as Record<string, unknown>;
  if (typeof record.cron_expression === "string") {
    return record.cron_expression;
  }
  const minute = asText(record.minute, "*");
  const hour = asText(record.hour, "*");
  const day = asText(record.day, "*");
  const month = asText(record.month, "*");
  const dayOfWeek = asText(record.day_of_week, "*");
  return `${minute} ${hour} ${day} ${month} ${dayOfWeek}`;
}

type SchedulerCronParts = {
  second: string;
  minute: string;
  hour: string;
  day: string;
  month: string;
  dayOfWeek: string;
  year: string;
};

function cronPartsFromJob(job: SchedulerJobItem): SchedulerCronParts {
  const defaults: SchedulerCronParts = {
    second: "0",
    minute: "*",
    hour: "*",
    day: "*",
    month: "*",
    dayOfWeek: "*",
    year: "*"
  };
  const args = job.trigger_args;
  if (args && typeof args === "object") {
    const record = args as Record<string, unknown>;
    return {
      second: asText(record.second, defaults.second),
      minute: asText(record.minute, defaults.minute),
      hour: asText(record.hour, defaults.hour),
      day: asText(record.day, defaults.day),
      month: asText(record.month, defaults.month),
      dayOfWeek: asText(record.day_of_week ?? record.dayOfWeek, defaults.dayOfWeek),
      year: asText(record.year, defaults.year)
    };
  }
  const parts = cronExpressionFromJob(job).split(/\s+/).filter(Boolean);
  if (parts.length >= 5) {
    return {
      ...defaults,
      minute: parts[0] ?? defaults.minute,
      hour: parts[1] ?? defaults.hour,
      day: parts[2] ?? defaults.day,
      month: parts[3] ?? defaults.month,
      dayOfWeek: parts[4] ?? defaults.dayOfWeek
    };
  }
  return defaults;
}

function cronExpressionFromParts(parts: SchedulerCronParts): string {
  return [parts.minute, parts.hour, parts.day, parts.month, parts.dayOfWeek].map((part) => part.trim() || "*").join(" ");
}

function SchedulerJobFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: SchedulerJobItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [cronParts, setCronParts] = useState<SchedulerCronParts>(() => (item ? cronPartsFromJob(item) : cronPartsFromJob({ id: "new" })));
  const title = item ? `编辑任务 ${item.task_name ?? item.name ?? item.id}` : "编辑任务";

  function setCronPart(key: keyof SchedulerCronParts, value: string) {
    setCronParts((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!item) {
      return;
    }
    const payload: SchedulerJobWritePayload = {
      trigger_type: "cron",
      cron_expression: cronExpressionFromParts(cronParts)
    };
    void runAction(updateSchedulerJob(item.id, payload), { success: "调度任务已更新" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>更新内置任务 cron 触发器。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="任务名称">
              <Input readOnly value={item?.task_name ?? item?.name ?? item?.id ?? ""} />
            </FormField>
            <FormField label="执行函数">
              <Input className="font-mono" readOnly value={item?.func ?? "-"} />
            </FormField>
            <FormField label="秒">
              <Input className="font-mono" onChange={(event) => setCronPart("second", event.target.value)} value={cronParts.second} />
            </FormField>
            <FormField label="分钟">
              <Input className="font-mono" onChange={(event) => setCronPart("minute", event.target.value)} required value={cronParts.minute} />
            </FormField>
            <FormField label="小时">
              <Input className="font-mono" onChange={(event) => setCronPart("hour", event.target.value)} required value={cronParts.hour} />
            </FormField>
            <FormField label="日">
              <Input className="font-mono" onChange={(event) => setCronPart("day", event.target.value)} required value={cronParts.day} />
            </FormField>
            <FormField label="月份">
              <Input className="font-mono" onChange={(event) => setCronPart("month", event.target.value)} required value={cronParts.month} />
            </FormField>
            <FormField label="星期">
              <Input className="font-mono" onChange={(event) => setCronPart("dayOfWeek", event.target.value)} required value={cronParts.dayOfWeek} />
            </FormField>
            <FormField label="年份">
              <Input className="font-mono" onChange={(event) => setCronPart("year", event.target.value)} value={cronParts.year} />
            </FormField>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存任务</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}


function SchedulerJobCard({
  job,
  onEdit,
  onJobChanged,
  onView
}: {
  job: SchedulerJobItem;
  onEdit: (job: SchedulerJobItem) => void;
  onJobChanged: () => void;
  onView: (job: SchedulerJobItem) => void;
}) {
  const name = schedulerJobName(job);

  return (
    <Card className="min-h-[16rem]">
      <CardContent className="grid gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold">{name}</h3>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{job.func ?? job.trigger_type ?? "-"}</p>
          </div>
          <Badge variant={isRunningState(job.state) ? "secondary" : "outline"}>{schedulerStatusLabel(job.state)}</Badge>
        </div>
        <dl className="grid gap-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">下次运行</dt>
            <dd className="font-mono text-xs">{job.next_run_time ? formatDateTime(job.next_run_time) : "未计划"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">上次运行</dt>
            <dd className="font-mono text-xs">{job.last_run_time ? formatDateTime(job.last_run_time) : "从未运行"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">任务 ID</dt>
            <dd className="font-mono text-xs">{job.task_id ?? job.id}</dd>
          </div>
        </dl>
        <div className="flex flex-wrap items-center gap-1">
          {isRunningState(job.state) ? (
            <Button
              aria-label={`暂停任务 ${name}`}
              onClick={() => {
                void runAction(pauseSchedulerJob(job.id), { success: "任务已暂停" }).then(onJobChanged);
              }}
              size="icon"
              type="button"
              variant="outline"
            >
              <Pause aria-hidden />
            </Button>
          ) : (
            <Button
              aria-label={`恢复任务 ${name}`}
              onClick={() => {
                void runAction(resumeSchedulerJob(job.id), { success: "任务已恢复" }).then(onJobChanged);
              }}
              size="icon"
              type="button"
              variant="outline"
            >
              <Play aria-hidden />
            </Button>
          )}
          <Button
            aria-label={`立即执行 ${name}`}
            onClick={() => {
              void runAction(runSchedulerJob(job.id), { success: "任务已触发" });
            }}
            size="icon"
            type="button"
            variant="outline"
          >
            <Zap aria-hidden />
          </Button>
          <Button aria-label={`查看任务 ${name}`} onClick={() => onView(job)} size="icon" type="button" variant="outline">
            <Eye aria-hidden />
          </Button>
          <Button aria-label={`编辑任务 ${name}`} onClick={() => onEdit(job)} size="icon" type="button" variant="outline">
            <Pencil aria-hidden />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SchedulerJobSection({
  jobs,
  onEdit,
  onJobChanged,
  onView,
  title
}: {
  jobs: SchedulerJobItem[];
  onEdit: (job: SchedulerJobItem) => void;
  onJobChanged: () => void;
  onView: (job: SchedulerJobItem) => void;
  title: string;
}) {
  return (
    <section className="grid gap-3">
      <div className="flex items-center gap-2">
        <Badge variant={title === "运行中的任务" ? "secondary" : "outline"}>{title}</Badge>
        <span className="text-sm text-muted-foreground">{formatNumber(jobs.length)} 项</span>
      </div>
      {jobs.length > 0 ? (
        <div className="grid grid-cols-3 gap-2 max-2xl:grid-cols-2 max-lg:grid-cols-1">
          {jobs.map((job) => (
            <SchedulerJobCard job={job} key={job.id} onEdit={onEdit} onJobChanged={onJobChanged} onView={onView} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">暂无{title}</CardContent>
        </Card>
      )}
    </section>
  );
}


export function SchedulerPage() {
  const query = useQuery({ queryKey: ["read-only", "scheduler"], queryFn: () => fetchSchedulerSnapshot() });
  const [editingJob, setEditingJob] = useState<SchedulerJobItem | null>(null);
  const [viewingJob, setViewingJob] = useState<SchedulerJobItem | null>(null);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation jobs" title="定时任务" description="只读展示调度任务和运行状态，暂停、恢复、立即执行仍保留在旧版。" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="定时任务" onRetry={() => void query.refetch()}>
        {(snapshot) => (
            <ListPanel
              title="任务卡片"
              description="按旧版运行状态分组展示任务名称、运行时间、任务 ID 和操作。"
              count={snapshot.jobs.length}
              actions={
                <Button
                  onClick={() => {
                    void runAction(reloadSchedulerJobs(), { success: "调度器已重新初始化" }).then(() => query.refetch());
                  }}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <RotateCcw aria-hidden />
                  重新初始化任务
                </Button>
              }
            >
              <div className="grid gap-6">
                <SchedulerJobSection
                  title="运行中的任务"
                  jobs={snapshot.jobs.filter((job) => isRunningState(job.state))}
                  onEdit={setEditingJob}
                  onJobChanged={() => void query.refetch()}
                  onView={setViewingJob}
                />
                <SchedulerJobSection
                  title="已暂停的任务"
                  jobs={snapshot.jobs.filter((job) => !isRunningState(job.state))}
                  onEdit={setEditingJob}
                  onJobChanged={() => void query.refetch()}
                  onView={setViewingJob}
                />
              </div>
            </ListPanel>
        )}
      </QueryFrame>
      <SchedulerJobDetailDialog
        item={viewingJob}
        onOpenChange={(open) => {
          if (!open) {
            setViewingJob(null);
          }
        }}
        open={viewingJob !== null}
      />
      {editingJob ? (
        <SchedulerJobFormDialog
          item={editingJob}
          onOpenChange={(open) => {
            if (!open) {
              setEditingJob(null);
            }
          }}
          onSaved={() => {
            setEditingJob(null);
            void query.refetch();
          }}
          open={editingJob !== null}
        />
      ) : null}
    </main>
  );
}
