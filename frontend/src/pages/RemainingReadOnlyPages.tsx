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
import type { SessionUser } from "@/types/auth";
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

type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof Layers3;
};

type AccessUser = Pick<SessionUser, "id" | "role">;

function canManageCatalog(currentUser?: AccessUser | null): boolean {
  return currentUser?.role === undefined || currentUser.role === "admin";
}

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0.0%";
  }
  return `${((value / total) * 100).toFixed(1)}%`;
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function asText(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

function isEmptyDetailValue(value: unknown): boolean {
  if (value === null || value === undefined || value === "") {
    return true;
  }
  if (Array.isArray(value)) {
    return value.length === 0;
  }
  if (typeof value === "object") {
    return Object.keys(value).length === 0;
  }
  return false;
}

function JsonBlock({ value }: { value: unknown }) {
  if (isEmptyDetailValue(value)) {
    return <span className="text-muted-foreground">-</span>;
  }

  return (
    <pre className="max-h-48 overflow-auto rounded-md border bg-secondary/30 p-3 font-mono text-xs whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function DetailBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-md border bg-secondary/20 p-3">
      <div className="mb-1 text-xs text-muted-foreground">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function endpointHost(value: unknown): string {
  const text = asText(value);
  if (text === "-") {
    return text;
  }
  try {
    return new URL(text).host || text;
  } catch {
    return text;
  }
}

function statusVariant(value: string | boolean | undefined | null): "default" | "secondary" | "destructive" | "outline" {
  if (value === true) {
    return "secondary";
  }
  if (value === false || value === null || value === undefined) {
    return "outline";
  }
  const normalized = String(value).toLowerCase();
  if (["failed", "error", "unhealthy", "disabled", "inactive", "cancelled"].includes(normalized)) {
    return "destructive";
  }
  if (["healthy", "completed", "success", "running", "active", "enabled", "state_running"].includes(normalized)) {
    return "secondary";
  }
  return "outline";
}

function statusLabel(value: string | boolean | undefined | null): string {
  if (value === true) {
    return "启用";
  }
  if (value === false) {
    return "停用";
  }
  return asText(value);
}

function roleLabel(role: string | undefined | null): string {
  switch (role) {
    case "admin":
      return "管理员";
    case "user":
      return "普通用户";
    case "viewer":
      return "查看者";
    default:
      return asText(role);
  }
}

function isRunningState(state: string | undefined | null): boolean {
  return state === "STATE_RUNNING" || state === "STATE_EXECUTING" || state === "running";
}

function schedulerStatusLabel(state: string | undefined | null): string {
  switch (state) {
    case "STATE_RUNNING":
    case "STATE_EXECUTING":
      return "运行中";
    case "STATE_PAUSED":
      return "已暂停";
    case "STATE_ERROR":
      return "失败";
    default:
      return asText(state, "未知");
  }
}

function schedulerJobName(job: SchedulerJobItem): string {
  return job.task_name ?? job.name ?? job.id;
}

function syncRunId(item: TaskRunItem): string {
  return item.run_id;
}

function syncTaskName(item: TaskRunItem): string {
  return item.task_name || item.task_key;
}

function syncSource(item: TaskRunItem): string {
  return ({ scheduled: "定时", scheduled_task: "定时", manual: "手动", api: "API" } as Record<string, string>)[item.trigger_source] ?? item.trigger_source;
}

function syncCategory(item: TaskRunItem): string {
  return ({ account: "账户", capacity: "容量", aggregation: "聚合", classification: "分类", cluster: "群集", alert: "告警", other: "其他" } as Record<string, string>)[item.task_category] ?? item.task_category;
}

function syncProgress(item: TaskRunItem) {
  const total = item.progress_total ?? 0;
  const completed = item.progress_completed ?? 0;
  const failed = item.progress_failed ?? 0;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { total, completed, failed, percent };
}

function syncDuration(item: TaskRunItem): string {
  if (item.status === "running") {
    return "进行中";
  }
  if (!item.started_at || !item.completed_at) {
    return "-";
  }
  const started = Date.parse(item.started_at);
  const completed = Date.parse(item.completed_at);
  if (!Number.isFinite(started) || !Number.isFinite(completed) || completed < started) {
    return "-";
  }
  const seconds = Math.round((completed - started) / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function PageHeader({
  title,
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
        <h1 className="font-display text-2xl leading-none tracking-normal">{title}</h1>
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

function CommandBar({ children }: { children: ReactNode }) {
  return <section className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">{children}</section>;
}

function MetricGrid({ metrics, label }: { metrics: Metric[]; label: string }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label={label}>
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

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="只读页面加载中">
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

function ErrorState({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="grid-cols-[1rem_minmax(0,1fr)] items-center sm:grid-cols-[1rem_minmax(0,1fr)_auto]">
      <AlertCircle aria-hidden size={16} />
      <AlertDescription>{label}加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function QueryFrame<TData>({
  data,
  isLoading,
  isError,
  errorLabel,
  onRetry,
  children
}: {
  data: TData | undefined;
  isLoading: boolean;
  isError: boolean;
  errorLabel: string;
  onRetry: () => void;
  children: (data: TData) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState label={errorLabel} onRetry={onRetry} /> : null}
      {data ? children(data) : null}
    </>
  );
}

function ListPanel({
  title,
  description,
  count,
  actions,
  children
}: {
  title: string;
  description?: string;
  count?: number;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-sm:grid">
          <div>
            <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
            {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {typeof count === "number" ? <Badge variant="secondary">共 {formatNumber(count)} 条</Badge> : null}
            {actions}
          </div>
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

function StatusBadge({ value }: { value: string | boolean | undefined | null }) {
  return <Badge variant={statusVariant(value)}>{statusLabel(value)}</Badge>;
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  );
}

function ActiveField({ checked, onCheckedChange }: { checked: boolean; onCheckedChange: (checked: boolean) => void }) {
  return <SwitchField checked={checked} label="状态" onCheckedChange={onCheckedChange} />;
}

function DeleteConfirmDialog({
  confirmLabel,
  description,
  onConfirm,
  onOpenChange,
  open,
  title
}: {
  confirmLabel: string;
  description: string;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}) {
  return (
    <AlertDialog onOpenChange={onOpenChange} open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>返回</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

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
  const detail = (query.data ?? item) as SchedulerJobDetail | null;

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
            <DetailBlock label="状态"><StatusBadge value={detail.state} /></DetailBlock>
            <DetailBlock label="执行函数"><span className="font-mono">{asText(detail.func)}</span></DetailBlock>
            <DetailBlock label="触发器"><span className="font-mono">{asText(detail.trigger ?? detail.trigger_type)}</span></DetailBlock>
            <DetailBlock label="下次运行"><span className="font-mono">{asText(detail.next_run_time, "未计划")}</span></DetailBlock>
            <DetailBlock label="上次运行"><span className="font-mono">{asText(detail.last_run_time, "从未运行")}</span></DetailBlock>
            <DetailBlock label="最大实例数"><span className="font-mono">{asText(detail.max_instances)}</span></DetailBlock>
            <DetailBlock label="错过执行宽限"><span className="font-mono">{asText(detail.misfire_grace_time)}</span></DetailBlock>
            <DetailBlock label="触发参数"><JsonBlock value={detail.trigger_args} /></DetailBlock>
            <DetailBlock label="位置参数"><JsonBlock value={detail.args} /></DetailBlock>
            <DetailBlock label="关键字参数"><JsonBlock value={detail.kwargs} /></DetailBlock>
            <DetailBlock label="合并执行"><StatusBadge value={detail.coalesce ?? null} /></DetailBlock>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function UserFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: UserItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [username, setUsername] = useState(item?.username ?? "");
  const [role, setRole] = useState(item?.role ?? "user");
  const [password, setPassword] = useState("");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const title = item ? `编辑用户 ${item.username}` : "新建用户";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: UserWritePayload = {
      username: username.trim(),
      role,
      is_active: isActive
    };
    if (item) {
      if (password.trim()) {
        payload.password = password;
      }
      void runAction(updateUser(item.id, payload), { success: "用户已更新" }).then(onSaved);
      return;
    }
    void runAction(createUser({ ...payload, password }), { success: "用户已创建" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护登录账号、角色和启用状态。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="用户名">
              <Input onChange={(event) => setUsername(event.target.value)} required value={username} />
            </FormField>
            <FormField label="角色">
              <SelectControl
                label="角色"
                onValueChange={setRole}
                options={[
                  { label: "管理员", value: "admin" },
                  { label: "普通用户", value: "user" },
                  { label: "查看者", value: "viewer" }
                ]}
                value={role}
              />
            </FormField>
            <FormField label={item ? "新密码" : "初始密码"}>
              <Input onChange={(event) => setPassword(event.target.value)} required={!item} type="password" value={password} />
            </FormField>
            <ActiveField checked={isActive} onCheckedChange={setIsActive} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存用户</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CredentialFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: CredentialItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [credentialType, setCredentialType] = useState(item?.credential_type ?? "database");
  const [dbType, setDbType] = useState(item?.db_type ?? "mysql");
  const [username, setUsername] = useState(item?.username ?? "");
  const [password, setPassword] = useState("");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const title = item ? `编辑凭据 ${item.name}` : "新建凭据";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: CredentialWritePayload = {
      name: name.trim(),
      credential_type: credentialType,
      db_type: dbType || null,
      username: username.trim(),
      description: description.trim() || null,
      is_active: isActive
    };
    if (item) {
      if (password.trim()) {
        payload.password = password;
      }
      void runAction(updateCredential(item.id, payload), { success: "凭据已更新" }).then(onSaved);
      return;
    }
    void runAction(createCredential({ ...payload, password }), { success: "凭据已创建" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护数据库、平台等连接凭据。密码为空时编辑不会覆盖旧密码。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="凭据名称">
              <Input onChange={(event) => setName(event.target.value)} required value={name} />
            </FormField>
            <FormField label="凭据类型">
              <SelectControl
                label="凭据类型"
                onValueChange={setCredentialType}
                options={[
                  { label: "database", value: "database" },
                  { label: "ssh", value: "ssh" },
                  { label: "api", value: "api" },
                  { label: "ldap", value: "ldap" }
                ]}
                value={credentialType}
              />
            </FormField>
            <FormField label="数据库类型">
              <SelectControl
                label="数据库类型"
                onValueChange={setDbType}
                options={[
                  { label: "mysql", value: "mysql" },
                  { label: "postgresql", value: "postgresql" },
                  { label: "sqlserver", value: "sqlserver" },
                  { label: "oracle", value: "oracle" },
                  { label: "无", value: "" }
                ]}
                value={dbType}
              />
            </FormField>
            <FormField label="用户名">
              <Input onChange={(event) => setUsername(event.target.value)} required value={username} />
            </FormField>
            <FormField label="密码">
              <Input onChange={(event) => setPassword(event.target.value)} required={!item} type="password" value={password} />
            </FormField>
            <ActiveField checked={isActive} onCheckedChange={setIsActive} />
          </div>
          <FormField label="描述">
            <Textarea onChange={(event) => setDescription(event.target.value)} value={description} />
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存凭据</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function TagFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: TagItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [displayName, setDisplayName] = useState(item?.display_name ?? "");
  const [category, setCategory] = useState(item?.category ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const title = item ? `编辑标签 ${item.display_name}` : "新建标签";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: TagWritePayload = {
      name: name.trim(),
      display_name: displayName.trim(),
      category: category.trim(),
      is_active: isActive
    };
    if (item) {
      void runAction(updateTag(item.id, payload), { success: "标签已更新" }).then(onSaved);
      return;
    }
    void runAction(createTag(payload), { success: "标签已创建" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护标签编码、展示名称、分类和启用状态。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="标签编码">
              <Input onChange={(event) => setName(event.target.value)} required value={name} />
            </FormField>
            <FormField label="展示名称">
              <Input onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
            </FormField>
            <FormField label="分类">
              <Input onChange={(event) => setCategory(event.target.value)} required value={category} />
            </FormField>
            <ActiveField checked={isActive} onCheckedChange={setIsActive} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存标签</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function numberFromInput(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function ClassificationFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: AccountClassificationItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [code, setCode] = useState(item?.code ?? "");
  const [displayName, setDisplayName] = useState(item?.display_name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [riskLevel, setRiskLevel] = useState(String(item?.risk_level ?? 4));
  const [iconName, setIconName] = useState(item?.icon_name ?? "");
  const [priority, setPriority] = useState(String(item?.priority ?? 0));
  const title = item ? `编辑分类 ${item.display_name}` : "新建分类";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: AccountClassificationWritePayload = {
      code: code.trim() || undefined,
      display_name: displayName.trim(),
      description: description.trim() || null,
      risk_level: numberFromInput(riskLevel, 4),
      icon_name: iconName.trim() || null,
      priority: numberFromInput(priority, 0)
    };
    if (item) {
      void runAction(updateAccountClassification(item.id, payload), { success: "账户分类已更新" }).then(onSaved);
      return;
    }
    void runAction(createAccountClassification(payload), { success: "账户分类已创建" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护分类编码、展示名称、风险等级和优先级。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="分类编码">
              <Input onChange={(event) => setCode(event.target.value)} required={!item} value={code} />
            </FormField>
            <FormField label="展示名称">
              <Input onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
            </FormField>
            <FormField label="风险等级">
              <Input max={6} min={1} onChange={(event) => setRiskLevel(event.target.value)} type="number" value={riskLevel} />
            </FormField>
            <FormField label="优先级">
              <Input max={100} min={0} onChange={(event) => setPriority(event.target.value)} type="number" value={priority} />
            </FormField>
            <FormField label="图标">
              <Input onChange={(event) => setIconName(event.target.value)} value={iconName} />
            </FormField>
          </div>
          <FormField label="描述">
            <Textarea onChange={(event) => setDescription(event.target.value)} value={description} />
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存分类</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function formatRuleExpression(value: unknown): string {
  if (isEmptyDetailValue(value)) {
    return "{}";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function parseRuleExpression(value: string): unknown {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return trimmed;
  }
}

function RuleFormDialog({
  classifications,
  item,
  onOpenChange,
  onSaved,
  open
}: {
  classifications: AccountClassificationItem[];
  item: AccountClassificationRuleItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const defaultClassificationId = item?.classification_id ?? classifications[0]?.id ?? 0;
  const [ruleName, setRuleName] = useState(item?.rule_name ?? "");
  const [classificationId, setClassificationId] = useState(String(defaultClassificationId));
  const [dbType, setDbType] = useState(item?.db_type ?? "mysql");
  const [operator, setOperator] = useState(item?.operator ?? "any");
  const [ruleExpression, setRuleExpression] = useState(formatRuleExpression(item?.rule_expression));
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const title = item ? `编辑规则 ${item.rule_name}` : "新建规则";

  function handleValidateExpression() {
    const parsedExpression = parseRuleExpression(ruleExpression);
    void runAction(validateAccountClassificationRuleExpression(parsedExpression), { success: "规则表达式校验通过" }).then((result) => {
      const validated = (result as { rule_expression?: unknown }).rule_expression ?? parsedExpression;
      setRuleExpression(formatRuleExpression(validated));
      setValidationMessage("规则表达式校验通过");
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: AccountClassificationRuleWritePayload = {
      rule_name: ruleName.trim(),
      classification_id: numberFromInput(classificationId, defaultClassificationId),
      db_type: dbType,
      operator,
      rule_expression: parseRuleExpression(ruleExpression),
      is_active: isActive
    };
    if (item) {
      void runAction(updateAccountClassificationRule(item.id, payload), { success: "分类规则已更新" }).then(onSaved);
      return;
    }
    void runAction(createAccountClassificationRule(payload), { success: "分类规则已创建" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),44rem)]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护分类规则的数据库类型、匹配逻辑和 DSL 表达式。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="规则名称">
              <Input onChange={(event) => setRuleName(event.target.value)} required value={ruleName} />
            </FormField>
            <FormField label="账户分类">
              <SelectControl
                label="账户分类"
                onValueChange={setClassificationId}
                options={classifications.map((classification) => ({ label: classification.display_name, value: String(classification.id) }))}
                value={classificationId}
              />
            </FormField>
            <FormField label="数据库类型">
              <SelectControl
                label="数据库类型"
                onValueChange={setDbType}
                options={[
                  { label: "mysql", value: "mysql" },
                  { label: "postgresql", value: "postgresql" },
                  { label: "sqlserver", value: "sqlserver" },
                  { label: "oracle", value: "oracle" }
                ]}
                value={dbType}
              />
            </FormField>
            <FormField label="匹配逻辑">
              <SelectControl
                label="匹配逻辑"
                onValueChange={setOperator}
                options={[
                  { label: "any", value: "any" },
                  { label: "all", value: "all" }
                ]}
                value={operator}
              />
            </FormField>
            <ActiveField checked={isActive} onCheckedChange={setIsActive} />
          </div>
          <FormField label="规则表达式">
            <Textarea className="min-h-32 font-mono text-xs" onChange={(event) => setRuleExpression(event.target.value)} value={ruleExpression} />
          </FormField>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button type="button" variant="outline" onClick={handleValidateExpression}>
              <ListChecks aria-hidden size={16} />
              <span>校验表达式</span>
            </Button>
            {validationMessage ? <span className="text-sm text-muted-foreground">{validationMessage}</span> : null}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存规则</Button>
          </DialogFooter>
        </form>
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
  const [cronExpression, setCronExpression] = useState(item ? cronExpressionFromJob(item) : "* * * * *");
  const title = item ? `编辑任务 ${item.task_name ?? item.name ?? item.id}` : "编辑任务";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!item) {
      return;
    }
    const payload: SchedulerJobWritePayload = {
      trigger_type: "cron",
      cron_expression: cronExpression.trim()
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
          <FormField label="Cron 表达式">
            <Input className="font-mono" onChange={(event) => setCronExpression(event.target.value)} required value={cronExpression} />
          </FormField>
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

function taggableInstanceLabel(item: TaggableInstanceItem): string {
  return asText(item.name ?? item.instance_name ?? item.id);
}

function tagOptionLabel(item: TagOptionItem): string {
  return asText(item.display_name ?? item.name ?? item.id);
}

function toggleNumberSelection(values: number[], value: number, checked: boolean): number[] {
  if (checked) {
    return values.includes(value) ? values : [...values, value];
  }
  return values.filter((item) => item !== value);
}

function TagBulkDialog({
  onOpenChange,
  onSaved,
  open
}: {
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [operation, setOperation] = useState<"assign" | "remove" | "remove_all">("assign");
  const [selectedInstanceIds, setSelectedInstanceIds] = useState<number[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const query = useQuery<TagBulkOptions>({
    enabled: open,
    queryKey: ["read-only", "tags", "bulk-options"],
    queryFn: () => fetchTagBulkOptions()
  });
  const actionLabel =
    operation === "assign" ? "执行批量分配" : operation === "remove" ? "执行批量移除" : "执行批量移除全部";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const action =
      operation === "assign"
        ? assignTagsToInstances(selectedInstanceIds, selectedTagIds)
        : operation === "remove"
          ? removeTagsFromInstances(selectedInstanceIds, selectedTagIds)
          : removeAllTagsFromInstances(selectedInstanceIds);
    void runAction(action, { success: actionLabel }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader>
          <DialogTitle>批量分配标签</DialogTitle>
          <DialogDescription>选择实例和标签后执行批量分配或移除。</DialogDescription>
        </DialogHeader>
        {query.isLoading ? (
          <div className="grid gap-3">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : null}
        {query.isError ? (
          <Alert variant="destructive">
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>标签批量选项加载失败</AlertDescription>
          </Alert>
        ) : null}
        {query.data ? (
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <FormField label="操作">
              <SelectControl
                label="操作"
                onValueChange={(value) => setOperation(value as "assign" | "remove" | "remove_all")}
                options={[
                  { label: "批量分配", value: "assign" },
                  { label: "批量移除指定标签", value: "remove" },
                  { label: "批量移除全部标签", value: "remove_all" }
                ]}
                value={operation}
              />
            </FormField>
            <div className="grid grid-cols-2 gap-3 max-lg:grid-cols-1">
              <section className="grid gap-2 rounded-md border p-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold">实例</h3>
                  <Badge variant="secondary">{formatNumber(query.data.instances.length)}</Badge>
                </div>
                <div className="grid max-h-64 gap-2 overflow-auto">
                  {query.data.instances.map((instance) => (
                    <CheckboxLine
                      checked={selectedInstanceIds.includes(instance.id)}
                      key={instance.id}
                      label={`实例 ${taggableInstanceLabel(instance)}`}
                      onCheckedChange={(checked) => setSelectedInstanceIds((current) => toggleNumberSelection(current, instance.id, checked))}
                    >
                      <span>
                        <span className="sr-only">实例 </span>
                        {taggableInstanceLabel(instance)}
                      </span>
                    </CheckboxLine>
                  ))}
                </div>
              </section>
              <section className="grid gap-2 rounded-md border p-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold">标签</h3>
                  <Badge variant="secondary">{formatNumber(query.data.tags.length)}</Badge>
                </div>
                <div className="grid max-h-64 gap-2 overflow-auto">
                  {query.data.tags.map((tag) => (
                    <CheckboxLine
                      checked={selectedTagIds.includes(tag.id)}
                      disabled={operation === "remove_all"}
                      key={tag.id}
                      label={`标签 ${tagOptionLabel(tag)}`}
                      onCheckedChange={(checked) => setSelectedTagIds((current) => toggleNumberSelection(current, tag.id, checked))}
                    >
                      <span>
                        <span className="sr-only">标签 </span>
                        {tagOptionLabel(tag)}
                      </span>
                    </CheckboxLine>
                  ))}
                </div>
              </section>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button type="submit" disabled={selectedInstanceIds.length === 0 || (operation !== "remove_all" && selectedTagIds.length === 0)}>
                {actionLabel}
              </Button>
            </DialogFooter>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function createCredentialColumns({
  canManage,
  onDelete,
  onEdit
}: {
  canManage: boolean;
  onDelete: (item: CredentialItem) => void;
  onEdit: (item: CredentialItem) => void;
}): ColumnDef<CredentialItem>[] {
  return [
  {
    accessorKey: "name",
    header: "凭据",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="grid gap-1">
          <span className="font-medium">{item.name}</span>
          <span className="font-mono text-xs text-muted-foreground">{item.username ?? "-"}</span>
        </div>
      );
    }
  },
  {
    accessorKey: "credential_type",
    header: "类型",
    cell: ({ row }) => row.original.credential_type ?? "-"
  },
  {
    accessorKey: "db_type",
    header: "数据库类型",
    cell: ({ row }) => row.original.db_type ?? "-"
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "instance_count",
    header: "绑定实例",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    accessorKey: "created_at_display",
    header: "创建时间",
    cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.created_at_display ?? "-"}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="flex items-center gap-1">
          {canManage ? (
            <>
              <Button aria-label={`编辑凭据 ${item.name}`} onClick={() => onEdit(item)} size="icon" type="button" variant="ghost">
                <Pencil aria-hidden />
              </Button>
              <Button aria-label={`删除凭据 ${item.name}`} onClick={() => onDelete(item)} size="icon" type="button" variant="ghost">
                <Trash2 aria-hidden />
              </Button>
            </>
          ) : (
            <Badge variant="outline">只读</Badge>
          )}
        </div>
      );
    }
  }
  ];
}

function createTagColumns({
  canManage,
  onDelete,
  onEdit
}: {
  canManage: boolean;
  onDelete: (item: TagItem) => void;
  onEdit: (item: TagItem) => void;
}): ColumnDef<TagItem>[] {
  return [
  {
    accessorKey: "display_name",
    header: "标签",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="grid gap-1">
          <span className="font-medium">{item.display_name}</span>
          <span className="font-mono text-xs text-muted-foreground">#{item.name}</span>
        </div>
      );
    }
  },
  {
    accessorKey: "category",
    header: "分类"
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "instance_count",
    header: "关联",
    cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="flex items-center gap-1">
          {canManage ? (
            <>
              <Button aria-label={`编辑标签 ${item.display_name}`} onClick={() => onEdit(item)} size="icon" type="button" variant="ghost">
                <Pencil aria-hidden />
              </Button>
              <Button aria-label={`删除标签 ${item.display_name}`} onClick={() => onDelete(item)} size="icon" type="button" variant="ghost">
                <Trash2 aria-hidden />
              </Button>
            </>
          ) : (
            <Badge variant="outline">只读</Badge>
          )}
        </div>
      );
    }
  }
  ];
}

function createUserColumns({
  canManage,
  currentUserId,
  onDelete,
  onEdit
}: {
  canManage: boolean;
  currentUserId?: number | null;
  onDelete: (item: UserItem) => void;
  onEdit: (item: UserItem) => void;
}): ColumnDef<UserItem>[] {
  return [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">#{row.original.id}</span>
  },
  {
    accessorKey: "username",
    header: "用户",
    cell: ({ row }) => (
      <div className="grid gap-1">
        <span className="font-medium">{row.original.username}</span>
        {row.original.email ? <span className="text-xs text-muted-foreground">{row.original.email}</span> : null}
      </div>
    )
  },
  {
    accessorKey: "role",
    header: "角色",
    cell: ({ row }) => <Badge variant={row.original.role === "admin" ? "default" : "outline"}>{roleLabel(row.original.role)}</Badge>
  },
  {
    accessorKey: "is_active",
    header: "状态",
    cell: ({ row }) => <StatusBadge value={row.original.is_active} />,
    filterFn: (row, columnId, filterValue) => String(row.getValue(columnId)) === filterValue
  },
  {
    accessorKey: "created_at_display",
    header: "创建时间",
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.created_at_display ?? row.original.created_at ?? "-"}</span>
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => {
      const item = row.original;
      const isCurrentUser = currentUserId !== undefined && currentUserId !== null && item.id === currentUserId;
      return (
        <div className="flex items-center gap-1">
          {canManage ? (
            <>
              <Button aria-label={`编辑用户 ${item.username}`} onClick={() => onEdit(item)} size="icon" type="button" variant="ghost">
                <Pencil aria-hidden />
              </Button>
              {isCurrentUser ? (
                <Button aria-label="不能删除当前登录用户" disabled size="icon" type="button" variant="ghost">
                  <Trash2 aria-hidden />
                </Button>
              ) : (
                <Button aria-label={`删除用户 ${item.username}`} onClick={() => onDelete(item)} size="icon" type="button" variant="ghost">
                  <Trash2 aria-hidden />
                </Button>
              )}
            </>
          ) : (
            <Badge variant="outline">只读</Badge>
          )}
        </div>
      );
    }
  }
  ];
}

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

function SchedulerJobCard({
  job,
  onDelete,
  onEdit,
  onView
}: {
  job: SchedulerJobItem;
  onDelete: (job: SchedulerJobItem) => void;
  onEdit: (job: SchedulerJobItem) => void;
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
                void runAction(pauseSchedulerJob(job.id), { success: "任务已暂停" });
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
                void runAction(resumeSchedulerJob(job.id), { success: "任务已恢复" });
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
          <Button aria-label={`删除任务 ${name}`} onClick={() => onDelete(job)} size="icon" type="button" variant="outline">
            <Trash2 aria-hidden />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SchedulerJobSection({
  jobs,
  onDelete,
  onEdit,
  onView,
  title
}: {
  jobs: SchedulerJobItem[];
  onDelete: (job: SchedulerJobItem) => void;
  onEdit: (job: SchedulerJobItem) => void;
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
            <SchedulerJobCard job={job} key={job.id} onDelete={onDelete} onEdit={onEdit} onView={onView} />
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

function clusterDescription(item: ClusterItem, fallback: string): string {
  return item.description || fallback;
}

function clusterEnabledLabel(item: ClusterItem): string {
  return item.is_enabled === false ? "停用" : "启用";
}

function sqlServerAgSummary(item: ClusterItem): string {
  return `${formatNumber(item.availability_group_count)} / contained ${formatNumber(item.contained_ag_count)}`;
}

function sqlServerDatabaseSyncSummary(item: ClusterItem): string {
  const abnormalCount = asNumber(item.ag_database_sync_abnormal_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return item.last_status_sync_status ? formatStatus(item.last_status_sync_status) : "未同步";
}

function mysqlTopologySummary(item: ClusterItem): string {
  const abnormalCount = asNumber(item.abnormal_replica_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return item.last_topology_sync_status ? formatStatus(item.last_topology_sync_status) : "未同步";
}

type ClusterMode = "sqlserver" | "mysql";

function clusterModeLabel(mode: ClusterMode): string {
  return mode === "sqlserver" ? "SQL Server" : "MySQL";
}

function clusterRecordField(record: ClusterDetailRecord, keys: string[], fallback = "-"): string {
  for (const key of keys) {
    const value = record[key];
    if (!isEmptyDetailValue(value)) {
      return asText(value);
    }
  }
  return fallback;
}

function clusterRecordId(record: ClusterDetailRecord | ClusterInstanceOption | ClusterItem): number | null {
  const value = record.id;
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function optionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function nullableText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function ClusterFormDialog({
  item,
  mode,
  onOpenChange,
  onSaved,
  open
}: {
  item: ClusterItem | null;
  mode: ClusterMode;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [domainName, setDomainName] = useState(item?.domain_name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isEnabled, setIsEnabled] = useState(item?.is_enabled ?? true);
  const label = clusterModeLabel(mode);
  const title = item ? `编辑 ${label} 群集 ${item.name}` : `新建 ${label} 群集`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "sqlserver") {
      const payload: SqlServerClusterPayload = {
        name: name.trim(),
        domain_name: domainName.trim(),
        description: description.trim() || null,
        is_enabled: isEnabled
      };
      const request = item ? updateSqlServerCluster(item.id, payload) : createSqlServerCluster(payload);
      void runAction(request, { success: "SQL Server 群集已保存" }).then(onSaved);
      return;
    }

    const payload: MySqlClusterPayload = {
      name: name.trim(),
      description: description.trim() || null,
      is_enabled: isEnabled
    };
    const request = item ? updateMySqlCluster(item.id, payload) : createMySqlCluster(payload);
    void runAction(request, { success: "MySQL 群集已保存" }).then(onSaved);
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护群集基础信息；实例绑定和 AG 配置通过群集列表操作进入。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="群集名称">
              <Input onChange={(event) => setName(event.target.value)} required value={name} />
            </FormField>
            {mode === "sqlserver" ? (
              <FormField label="群集域名">
                <Input onChange={(event) => setDomainName(event.target.value)} required value={domainName} />
              </FormField>
            ) : null}
            <ActiveField checked={isEnabled} onCheckedChange={setIsEnabled} />
          </div>
          <FormField label="描述">
            <Textarea onChange={(event) => setDescription(event.target.value)} value={description} />
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit">保存群集</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ClusterInstancesTable({ records }: { records: ClusterDetailRecord[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>实例</TableHead>
          <TableHead>主机</TableHead>
          <TableHead>角色/状态</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.length > 0 ? (
          records.map((record, index) => (
            <TableRow key={`${clusterRecordField(record, ["id", "name"], String(index))}-${index}`}>
              <TableCell className="font-medium">{clusterRecordField(record, ["name", "instance_name", "display_name"])}</TableCell>
              <TableCell className="font-mono text-xs">{clusterRecordField(record, ["host", "ip_address", "endpoint", "server_host"])}</TableCell>
              <TableCell>
                <Badge variant="outline">{clusterRecordField(record, ["role", "status", "sync_status"])}</Badge>
              </TableCell>
            </TableRow>
          ))
        ) : (
          <EmptyRows colSpan={3} />
        )}
      </TableBody>
    </Table>
  );
}

function ClusterInstanceBindingPanel({
  item,
  mode,
  onClose,
  onSaved
}: {
  item: ClusterItem;
  mode: ClusterMode;
  onClose: () => void;
  onSaved: () => void;
}) {
  const label = clusterModeLabel(mode);
  const detailQuery = useQuery({
    enabled: true,
    queryKey: ["read-only", "clusters", mode, item.id, "binding"],
    queryFn: () => (mode === "sqlserver" ? fetchSqlServerClusterDetail(item.id) : fetchMySqlClusterDetail(item.id))
  });
  const optionsQuery = useQuery({
    enabled: true,
    queryKey: ["read-only", "clusters", mode, "instance-options"],
    queryFn: () => fetchClusterInstanceOptions(mode)
  });
  const boundIds = useMemo(
    () =>
      (detailQuery.data?.instances ?? [])
        .map((record) => clusterRecordId(record))
        .filter((id): id is number => id !== null),
    [detailQuery.data]
  );
  const [selectedIdsOverride, setSelectedIdsOverride] = useState<number[] | null>(null);
  const selectedIds = selectedIdsOverride ?? boundIds;

  function toggleInstance(instanceId: number, checked: boolean) {
    setSelectedIdsOverride((current) => {
      const baseIds = current ?? boundIds;
      if (checked) {
        return Array.from(new Set([...baseIds, instanceId])).sort((left, right) => left - right);
      }
      return baseIds.filter((id) => id !== instanceId);
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const request =
      mode === "sqlserver" ? replaceSqlServerClusterInstances(item.id, selectedIds) : replaceMySqlClusterInstances(item.id, selectedIds);
    void runAction(request, { success: `${label} 实例绑定已保存` }).then(() => {
      onSaved();
      onClose();
      void detailQuery.refetch();
    });
  }

  const isLoading = detailQuery.isLoading || optionsQuery.isLoading;
  const isError = detailQuery.isError || optionsQuery.isError;
  const options = optionsQuery.data ?? [];
  const title = `编辑 ${label} 实例绑定 ${item.name}`;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护群集成员绑定，保存后替换当前绑定实例列表。</DialogDescription>
        </DialogHeader>
        {isLoading ? <Skeleton className="h-32 w-full" /> : null}
        {isError ? (
          <ErrorState
            label={`${label} 实例绑定`}
            onRetry={() => {
              void detailQuery.refetch();
              void optionsQuery.refetch();
            }}
          />
        ) : null}
        {!isLoading && !isError ? (
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
              {options.length > 0 ? (
                options.map((option) => {
                  const optionId = clusterRecordId(option);
                  if (optionId === null) {
                    return null;
                  }
                  return (
                    <CheckboxLine
                      checked={selectedIds.includes(optionId)}
                      key={optionId}
                      label={`绑定 ${option.name}`}
                      onCheckedChange={(checked) => toggleInstance(optionId, checked)}
                    >
                      <span className="grid gap-0.5">
                        <span className="font-medium">{option.name}</span>
                        <span className="font-mono text-xs text-muted-foreground">{option.host ?? "-"}</span>
                      </span>
                    </CheckboxLine>
                  );
                })
              ) : (
                <div className="rounded-md border px-3 py-8 text-center text-sm text-muted-foreground">暂无可绑定实例</div>
              )}
            </div>
            <DialogFooter>
              <Button onClick={onClose} type="button" variant="outline">
                取消
              </Button>
              <Button type="submit">保存绑定</Button>
            </DialogFooter>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function sqlServerAgName(record: ClusterDetailRecord): string {
  return clusterRecordField(record, ["name", "availability_group_name"], "AG");
}

function SqlServerAvailabilityGroupsTable({
  onDashboard,
  onEdit,
  records
}: {
  onDashboard?: (record: ClusterDetailRecord) => void;
  onEdit?: (record: ClusterDetailRecord) => void;
  records: ClusterDetailRecord[];
}) {
  const hasActions = Boolean(onDashboard || onEdit);
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>AG</TableHead>
          <TableHead>监听器</TableHead>
          <TableHead>状态</TableHead>
          {hasActions ? <TableHead>操作</TableHead> : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.length > 0 ? (
          records.map((record, index) => (
            <TableRow key={`${clusterRecordField(record, ["id", "name"], String(index))}-${index}`}>
              <TableCell className="font-medium">{sqlServerAgName(record)}</TableCell>
              <TableCell className="font-mono text-xs">
                {clusterRecordField(record, ["listener_name", "listener_host", "listener_dns_name"])}
              </TableCell>
              <TableCell>
                <StatusBadge value={clusterRecordField(record, ["sync_status", "health_status", "is_enabled"])} />
              </TableCell>
              {hasActions ? (
                <TableCell>
                  <div className="flex items-center gap-1">
                    {onEdit ? (
                      <Button aria-label={`编辑AG ${sqlServerAgName(record)}`} onClick={() => onEdit(record)} size="icon" type="button" variant="ghost">
                        <Pencil aria-hidden />
                      </Button>
                    ) : null}
                    {onDashboard ? (
                      <Button
                        aria-label={`查看AG看板 ${sqlServerAgName(record)}`}
                        onClick={() => onDashboard(record)}
                        size="icon"
                        type="button"
                        variant="ghost"
                      >
                        <ChartColumn aria-hidden />
                      </Button>
                    ) : null}
                  </div>
                </TableCell>
              ) : null}
            </TableRow>
          ))
        ) : (
          <EmptyRows colSpan={hasActions ? 4 : 3} />
        )}
      </TableBody>
    </Table>
  );
}

function ClusterDetailRecordsTable({
  columns,
  records
}: {
  columns: Array<{ keys: string[]; label: string }>;
  records: ClusterDetailRecord[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.label}>{column.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.length > 0 ? (
          records.map((record, index) => (
            <TableRow key={`${clusterRecordField(record, ["id", "name", "replica_server_name", "database_name"], String(index))}-${index}`}>
              {columns.map((column) => (
                <TableCell className="font-mono text-xs" key={column.label}>
                  {clusterRecordField(record, column.keys)}
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : (
          <EmptyRows colSpan={columns.length} />
        )}
      </TableBody>
    </Table>
  );
}

function SqlServerAgInlineForm({
  clusterId,
  onCancel,
  onSaved,
  target
}: {
  clusterId: number;
  onCancel: () => void;
  onSaved: () => void;
  target: ClusterDetailRecord | "new";
}) {
  const editingRecord = target === "new" ? null : target;
  const [name, setName] = useState(() => (editingRecord ? clusterRecordField(editingRecord, ["name", "availability_group_name"], "") : ""));
  const [listenerName, setListenerName] = useState(() => (editingRecord ? clusterRecordField(editingRecord, ["listener_name"], "") : ""));
  const [listenerHost, setListenerHost] = useState(() =>
    editingRecord ? clusterRecordField(editingRecord, ["listener_host", "listener_dns_name"], "") : ""
  );
  const [listenerPort, setListenerPort] = useState(() => (editingRecord ? String(numericValue(editingRecord.listener_port, 1433)) : "1433"));
  const [connectionDatabase, setConnectionDatabase] = useState(() =>
    editingRecord ? clusterRecordField(editingRecord, ["connection_database"], "master") : "master"
  );
  const [accountCredentialId, setAccountCredentialId] = useState(() =>
    editingRecord ? clusterRecordField(editingRecord, ["account_credential_id"], "") : ""
  );
  const [containedEnabled, setContainedEnabled] = useState(() => (editingRecord ? booleanValue(editingRecord.contained_enabled, false) : false));
  const [isEnabled, setIsEnabled] = useState(() => (editingRecord ? booleanValue(editingRecord.is_enabled, true) : true));

  function buildPayload(): SqlServerAvailabilityGroupPayload {
    return {
      name: name.trim(),
      listener_name: nullableText(listenerName),
      listener_host: nullableText(listenerHost),
      listener_port: optionalNumber(listenerPort) ?? 1433,
      connection_database: nullableText(connectionDatabase),
      account_credential_id: optionalNumber(accountCredentialId),
      contained_enabled: containedEnabled,
      is_enabled: isEnabled
    };
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildPayload();
    const agId = editingRecord ? clusterRecordId(editingRecord) : null;
    const request = editingRecord && agId !== null
      ? updateSqlServerAvailabilityGroup(clusterId, agId, payload)
      : createSqlServerAvailabilityGroup(clusterId, payload);
    void runAction(request, { success: "SQL Server AG 配置已保存" }).then(onSaved);
  }

  const title = editingRecord ? `编辑 SQL Server AG 配置 ${sqlServerAgName(editingRecord)}` : "新建 SQL Server AG 配置";

  return (
    <section className="grid gap-3 rounded-md border bg-secondary/20 p-3">
      <h3 className="font-display text-base font-semibold">{title}</h3>
      <form className="grid gap-4" onSubmit={handleSubmit}>
        <div className="grid grid-cols-3 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
          <FormField label="AG 名称">
            <Input onChange={(event) => setName(event.target.value)} required value={name} />
          </FormField>
          <FormField label="监听器名称">
            <Input onChange={(event) => setListenerName(event.target.value)} value={listenerName} />
          </FormField>
          <FormField label="监听器地址">
            <Input onChange={(event) => setListenerHost(event.target.value)} value={listenerHost} />
          </FormField>
          <FormField label="监听器端口">
            <Input inputMode="numeric" onChange={(event) => setListenerPort(event.target.value)} value={listenerPort} />
          </FormField>
          <FormField label="连接数据库">
            <Input onChange={(event) => setConnectionDatabase(event.target.value)} value={connectionDatabase} />
          </FormField>
          <FormField label="账户凭据ID">
            <Input inputMode="numeric" onChange={(event) => setAccountCredentialId(event.target.value)} value={accountCredentialId} />
          </FormField>
        </div>
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <SwitchField checked={containedEnabled} label="Contained 账户采集" onCheckedChange={setContainedEnabled} />
          <ActiveField checked={isEnabled} onCheckedChange={setIsEnabled} />
        </div>
        <div className="flex items-center justify-end gap-2">
          <Button onClick={onCancel} type="button" variant="outline">
            取消
          </Button>
          <Button type="submit">保存AG配置</Button>
        </div>
      </form>
    </section>
  );
}

function SqlServerAgDashboardInline({
  clusterId,
  item,
  onClose
}: {
  clusterId: number;
  item: ClusterDetailRecord;
  onClose: () => void;
}) {
  const agId = clusterRecordId(item);
  const query = useQuery({
    enabled: agId !== null,
    queryKey: ["read-only", "clusters", "sqlserver-ag-dashboard", clusterId, agId],
    queryFn: () => fetchSqlServerAvailabilityGroupDashboard(clusterId, agId ?? 0)
  });
  const title = `SQL Server AG 看板 ${sqlServerAgName(item)}`;

  return (
    <section className="grid gap-3 rounded-md border bg-secondary/20 p-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-base font-semibold">{title}</h3>
        <Button onClick={onClose} size="sm" type="button" variant="outline">
          收起看板
        </Button>
      </div>
      {query.isLoading ? <Skeleton className="h-32 w-full" /> : null}
      {query.isError ? <ErrorState label={title} onRetry={() => void query.refetch()} /> : null}
      {query.data ? <SqlServerAgDashboardContent dashboard={query.data} /> : null}
    </section>
  );
}

function SqlServerAgDashboardContent({ dashboard }: { dashboard: SqlServerAvailabilityGroupDashboard }) {
  return (
    <div className="grid gap-3">
      <section className="grid grid-cols-3 gap-2 max-lg:grid-cols-1">
        <DetailBlock label="AG">{clusterRecordField(dashboard.availability_group, ["name", "availability_group_name"])}</DetailBlock>
        <DetailBlock label="监听器">{clusterRecordField(dashboard.availability_group, ["listener_name", "listener_host"])}</DetailBlock>
        <DetailBlock label="状态">
          <StatusBadge value={clusterRecordField(dashboard.availability_group, ["health_status", "sync_status", "is_enabled"])} />
        </DetailBlock>
      </section>
      <ListPanel title="副本状态" description="AG 看板中的副本角色与同步健康。" count={dashboard.replicas.length}>
        <ClusterDetailRecordsTable
          columns={[
            { label: "副本", keys: ["replica_server_name", "server_name", "name"] },
            { label: "角色", keys: ["role_desc", "role"] },
            { label: "同步健康", keys: ["synchronization_health_desc", "health_status"] }
          ]}
          records={dashboard.replicas}
        />
      </ListPanel>
      <ListPanel title="数据库状态" description="AG 看板中的数据库同步状态。" count={dashboard.databases.length}>
        <ClusterDetailRecordsTable
          columns={[
            { label: "数据库", keys: ["database_name", "name"] },
            { label: "同步状态", keys: ["synchronization_state_desc", "sync_status"] },
            { label: "同步健康", keys: ["synchronization_health_desc", "health_status"] }
          ]}
          records={dashboard.databases}
        />
      </ListPanel>
    </div>
  );
}

function SqlServerAgConfigurationPanel({
  item,
  onClose,
  onSaved
}: {
  item: ClusterItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const query = useQuery({
    enabled: true,
    queryKey: ["read-only", "clusters", "sqlserver", item.id, "ag-config"],
    queryFn: () => fetchSqlServerClusterDetail(item.id)
  });
  const [formTarget, setFormTarget] = useState<ClusterDetailRecord | "new" | null>(null);
  const [dashboardTarget, setDashboardTarget] = useState<ClusterDetailRecord | null>(null);

  function handleSaved() {
    setFormTarget(null);
    onSaved();
    void query.refetch();
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-6xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>SQL Server AG 配置 {item.name}</DialogTitle>
          <DialogDescription>维护可用性组监听器、连接数据库和账户采集配置。</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="flex justify-end">
          <Button onClick={() => setFormTarget("new")} size="sm" type="button">
            <Plus aria-hidden />
            新建AG配置
          </Button>
          </div>
          {query.isLoading ? <Skeleton className="h-32 w-full" /> : null}
          {query.isError ? <ErrorState label="SQL Server AG 配置" onRetry={() => void query.refetch()} /> : null}
          {query.data ? (
            <>
              <ListPanel title="可用性组配置" description="旧版 SQL Server 群集中的 AG 配置列表。" count={query.data.availability_groups.length}>
                <SqlServerAvailabilityGroupsTable
                  onDashboard={(record) => setDashboardTarget(record)}
                  onEdit={(record) => setFormTarget(record)}
                  records={query.data.availability_groups}
                />
              </ListPanel>
              {formTarget ? (
                <SqlServerAgInlineForm
                  clusterId={item.id}
                  key={formTarget === "new" ? "new" : `edit-${clusterRecordId(formTarget) ?? sqlServerAgName(formTarget)}`}
                  onCancel={() => setFormTarget(null)}
                  onSaved={handleSaved}
                  target={formTarget}
                />
              ) : null}
              {dashboardTarget ? (
                <SqlServerAgDashboardInline clusterId={item.id} item={dashboardTarget} onClose={() => setDashboardTarget(null)} />
              ) : null}
            </>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SqlServerClusterDetailContent({ detail }: { detail: SqlServerClusterDetail }) {
  return (
    <div className="grid gap-4">
      <section className="grid grid-cols-3 gap-2 max-sm:grid-cols-1">
        <DetailBlock label="群集">{detail.cluster.name}</DetailBlock>
        <DetailBlock label="域名">{detail.cluster.domain_name ?? "-"}</DetailBlock>
        <DetailBlock label="状态">
          <StatusBadge value={detail.cluster.is_enabled !== false} />
        </DetailBlock>
      </section>
      <ListPanel title="绑定实例" description="旧版群集详情中的实例成员。" count={detail.instances.length}>
        <ClusterInstancesTable records={detail.instances} />
      </ListPanel>
      <ListPanel title="可用性组" description="SQL Server AG 监听器与同步状态。" count={detail.availability_groups.length}>
        <SqlServerAvailabilityGroupsTable records={detail.availability_groups} />
      </ListPanel>
    </div>
  );
}

function MySqlClusterDetailContent({ detail }: { detail: MySqlClusterDetail }) {
  return (
    <div className="grid gap-4">
      <section className="grid grid-cols-3 gap-2 max-sm:grid-cols-1">
        <DetailBlock label="群集">{detail.cluster.name}</DetailBlock>
        <DetailBlock label="描述">{clusterDescription(detail.cluster, "MySQL replication 群集")}</DetailBlock>
        <DetailBlock label="状态">
          <StatusBadge value={detail.cluster.is_enabled !== false} />
        </DetailBlock>
      </section>
      <ListPanel title="主从实例" description="旧版主从状态页中的实例拓扑。" count={detail.instances.length}>
        <ClusterInstancesTable records={detail.instances} />
      </ListPanel>
    </div>
  );
}

function SqlServerClusterDetailDialog({
  item,
  onOpenChange,
  open
}: {
  item: ClusterItem;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const query = useQuery({
    queryKey: ["read-only", "clusters", "sqlserver", item.id],
    queryFn: () => fetchSqlServerClusterDetail(item.id),
    enabled: open
  });

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),64rem)]">
        <DialogHeader>
          <DialogTitle>SQL Server 群集详情 {item.name}</DialogTitle>
          <DialogDescription>查看绑定实例、可用性组，并执行 AG 信息、群集状态和 AG 账户同步。</DialogDescription>
        </DialogHeader>
        {query.isLoading ? <Skeleton className="h-48 w-full" /> : null}
        {query.isError ? <ErrorState label="SQL Server 群集详情" onRetry={() => void query.refetch()} /> : null}
        {query.data ? <SqlServerClusterDetailContent detail={query.data} /> : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            关闭详情
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void runAction(syncSqlServerAvailabilityGroups(item.id, "master"), { success: "AG 信息同步已触发" }).then(() => void query.refetch());
            }}
          >
            同步AG信息
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void runAction(syncSqlServerClusterStatus(item.id), { success: "群集状态同步已触发" }).then(() => void query.refetch());
            }}
          >
            同步群集状态
          </Button>
          <Button
            type="button"
            onClick={() => {
              void runAction(syncSqlServerAgAccounts(item.id), { success: "AG 账户同步已触发" }).then(() => void query.refetch());
            }}
          >
            同步AG账户
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MySqlClusterDetailDialog({
  item,
  onOpenChange,
  open
}: {
  item: ClusterItem;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const query = useQuery({
    queryKey: ["read-only", "clusters", "mysql", item.id],
    queryFn: () => fetchMySqlClusterDetail(item.id),
    enabled: open
  });

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),58rem)]">
        <DialogHeader>
          <DialogTitle>MySQL 群集详情 {item.name}</DialogTitle>
          <DialogDescription>查看主从拓扑实例，并执行主从拓扑同步。</DialogDescription>
        </DialogHeader>
        {query.isLoading ? <Skeleton className="h-40 w-full" /> : null}
        {query.isError ? <ErrorState label="MySQL 群集详情" onRetry={() => void query.refetch()} /> : null}
        {query.data ? <MySqlClusterDetailContent detail={query.data} /> : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            关闭详情
          </Button>
          <Button
            type="button"
            onClick={() => {
              void runAction(syncMySqlClusterTopology(item.id), { success: "MySQL 拓扑同步已触发" }).then(() => void query.refetch());
            }}
          >
            同步主从拓扑
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function createSqlServerClusterColumns({
  onAgConfig,
  onBind,
  onDetail,
  onEdit,
  onSyncAccounts
}: {
  onAgConfig: (item: ClusterItem) => void;
  onBind: (item: ClusterItem) => void;
  onDetail: (item: ClusterItem) => void;
  onEdit: (item: ClusterItem) => void;
  onSyncAccounts: (item: ClusterItem) => void;
}): ColumnDef<ClusterItem>[] {
  return [
    {
      accessorFn: (item) => `${item.name} ${clusterDescription(item, "SQL Server 群集")}`,
      id: "name",
      header: "群集",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="mt-1 text-xs text-muted-foreground">{clusterDescription(row.original, "SQL Server 群集")}</div>
        </div>
      )
    },
    {
      accessorKey: "domain_name",
      header: "域名",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.domain_name ?? "-"}</span>
    },
    {
      accessorFn: clusterEnabledLabel,
      id: "is_enabled",
      header: "状态",
      cell: ({ row }) => <StatusBadge value={row.original.is_enabled !== false} />
    },
    {
      accessorKey: "instance_count",
      header: "绑定实例",
      cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
    },
    {
      accessorFn: sqlServerAgSummary,
      id: "availability_group_count",
      header: "AG",
      cell: ({ row }) => <span className="font-mono text-xs">{sqlServerAgSummary(row.original)}</span>
    },
    {
      accessorFn: (item) => asText(item.last_ag_sync_status, "未同步"),
      id: "last_ag_sync_status",
      header: "最近 AG 同步",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <StatusBadge value={formatStatus(row.original.last_ag_sync_status ?? "unknown")} />
          <span className="font-mono text-xs text-muted-foreground">{formatDateTime(row.original.last_ag_sync_at)}</span>
        </div>
      )
    },
    {
      accessorFn: sqlServerDatabaseSyncSummary,
      id: "ag_database_sync_abnormal_count",
      header: "数据库同步状态",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <Badge variant="outline">{sqlServerDatabaseSyncSummary(row.original)}</Badge>
          <span className="font-mono text-xs text-muted-foreground">{formatDateTime(row.original.last_status_sync_at)}</span>
        </div>
      )
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button aria-label={`绑定实例 ${row.original.name}`} onClick={() => onBind(row.original)} size="icon" type="button" variant="ghost">
            <Boxes aria-hidden />
          </Button>
          <Button aria-label={`AG配置 ${row.original.name}`} onClick={() => onAgConfig(row.original)} size="icon" type="button" variant="ghost">
            <Settings aria-hidden />
          </Button>
          <Button aria-label={`管理群集 ${row.original.name}`} onClick={() => onEdit(row.original)} size="icon" type="button" variant="ghost">
            <Pencil aria-hidden />
          </Button>
          <Button
            aria-label={`AG账户 ${row.original.name}`}
            onClick={() => onSyncAccounts(row.original)}
            size="icon"
            type="button"
            variant="ghost"
          >
            <UserCog aria-hidden />
          </Button>
          <Button aria-label={`查看AG状态 ${row.original.name}`} onClick={() => onDetail(row.original)} size="icon" type="button" variant="ghost">
            <ChartColumn aria-hidden />
          </Button>
        </div>
      )
    }
  ];
}

function createMySqlClusterColumns({
  onBind,
  onDetail,
  onEdit
}: {
  onBind: (item: ClusterItem) => void;
  onDetail: (item: ClusterItem) => void;
  onEdit: (item: ClusterItem) => void;
}): ColumnDef<ClusterItem>[] {
  return [
    {
      accessorFn: (item) => `${item.name} ${clusterDescription(item, "MySQL replication 群集")}`,
      id: "name",
      header: "群集",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="mt-1 text-xs text-muted-foreground">{clusterDescription(row.original, "MySQL replication 群集")}</div>
        </div>
      )
    },
    {
      accessorFn: (item) => asText((item as Record<string, unknown>).topology_type, "replication"),
      id: "topology_type",
      header: "拓扑"
    },
    {
      accessorFn: clusterEnabledLabel,
      id: "is_enabled",
      header: "状态",
      cell: ({ row }) => <StatusBadge value={row.original.is_enabled !== false} />
    },
    {
      accessorKey: "instance_count",
      header: "绑定实例",
      cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.instance_count)}</span>
    },
    {
      accessorFn: mysqlTopologySummary,
      id: "abnormal_replica_count",
      header: "主从状态",
      cell: ({ row }) => (
        <div className="grid gap-1">
          <Badge variant="outline">{mysqlTopologySummary(row.original)}</Badge>
          <span className="font-mono text-xs text-muted-foreground">{formatDateTime(row.original.last_topology_sync_at)}</span>
        </div>
      )
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button aria-label={`绑定实例 ${row.original.name}`} onClick={() => onBind(row.original)} size="icon" type="button" variant="ghost">
            <Boxes aria-hidden />
          </Button>
          <Button aria-label={`管理群集 ${row.original.name}`} onClick={() => onEdit(row.original)} size="icon" type="button" variant="ghost">
            <Pencil aria-hidden />
          </Button>
          <Button aria-label={`主从状态 ${row.original.name}`} onClick={() => onDetail(row.original)} size="icon" type="button" variant="ghost">
            <RotateCcw aria-hidden />
          </Button>
        </div>
      )
    }
  ];
}

export function ClustersPage() {
  const sqlServerTable = useServerTableState({ initialFilters: { status: "" } });
  const mySqlTable = useServerTableState({ initialFilters: { status: "" } });
  const clusterQuery = {
    sqlServer: { page: sqlServerTable.page, limit: sqlServerTable.pageSize, search: sqlServerTable.search, status: sqlServerTable.filters.status },
    mySql: { page: mySqlTable.page, limit: mySqlTable.pageSize, search: mySqlTable.search, status: mySqlTable.filters.status }
  };
  const query = useQuery({
    queryKey: ["read-only", "clusters", clusterQuery],
    queryFn: () => fetchClustersSnapshot(clusterQuery),
    placeholderData: (previous) => previous
  });
  const [creatingCluster, setCreatingCluster] = useState<ClusterMode | null>(null);
  const [editingCluster, setEditingCluster] = useState<{ mode: ClusterMode; item: ClusterItem } | null>(null);
  const [viewingCluster, setViewingCluster] = useState<{ mode: ClusterMode; item: ClusterItem } | null>(null);
  const [maintainingCluster, setMaintainingCluster] = useState<{
    mode: ClusterMode;
    item: ClusterItem;
    panel: "instances" | "sqlserver-ag";
  } | null>(null);
  const sqlServerClusterColumns = useMemo(
    () =>
      createSqlServerClusterColumns({
        onAgConfig: (item) => setMaintainingCluster({ mode: "sqlserver", item, panel: "sqlserver-ag" }),
        onBind: (item) => setMaintainingCluster({ mode: "sqlserver", item, panel: "instances" }),
        onDetail: (item) => setViewingCluster({ mode: "sqlserver", item }),
        onEdit: (item) => setEditingCluster({ mode: "sqlserver", item }),
        onSyncAccounts: (item) => {
          void runAction(syncSqlServerAgAccounts(item.id), { success: "AG 账户同步已触发" }).then(() => void query.refetch());
        }
      }),
    [query]
  );
  const mysqlClusterColumns = useMemo(
    () =>
      createMySqlClusterColumns({
        onBind: (item) => setMaintainingCluster({ mode: "mysql", item, panel: "instances" }),
        onDetail: (item) => setViewingCluster({ mode: "mysql", item }),
        onEdit: (item) => setEditingCluster({ mode: "mysql", item })
      }),
    []
  );

  function handleClusterSaved() {
    setCreatingCluster(null);
    setEditingCluster(null);
    void query.refetch();
  }

  function refreshClusters() {
    void query.refetch();
  }

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Cluster topology"
        title="群集管理"
        description="展示 SQL Server AG 与 MySQL 群集拓扑，并支持群集基础信息维护、详情查看和同步操作。"
        legacyHref="/cluster/"
      />
      <CommandBar>
        <span className="text-sm font-medium text-muted-foreground">添加群集</span>
        <Button aria-label="添加 SQL Server 群集" onClick={() => setCreatingCluster("sqlserver")} type="button">
          <Plus aria-hidden size={16} />
          <span>添加</span>
          <span>SQL Server</span>
          <span>群集</span>
        </Button>
        <Button aria-label="添加 MySQL 群集" onClick={() => setCreatingCluster("mysql")} type="button" variant="outline">
          <Plus aria-hidden size={16} />
          <span>添加</span>
          <span>MySQL</span>
          <span>群集</span>
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="群集" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <Tabs className="grid gap-3" defaultValue="sqlserver">
            <TabsList className="grid h-auto w-full grid-cols-2 p-1">
              <TabsTrigger className="gap-2" value="sqlserver">
                <Layers3 aria-hidden size={16} />
                <span>SQL Server</span>
              </TabsTrigger>
              <TabsTrigger className="gap-2" value="mysql">
                <Database aria-hidden size={16} />
                <span>MySQL</span>
              </TabsTrigger>
            </TabsList>
            <TabsContent className="mt-0 grid gap-3" value="sqlserver">
              <ListPanel title="SQL Server 群集" description="AG 关系、实例数量、AG 同步和数据库同步状态。" count={snapshot.sqlServer.total}>
                <DataTable
                  columns={sqlServerClusterColumns}
                  data={snapshot.sqlServer.items}
                  filters={[{ columnId: "is_enabled", label: "状态", options: [{ label: "启用", value: "active" }, { label: "停用", value: "inactive" }], value: sqlServerTable.filters.status, onValueChange: (value) => sqlServerTable.setFilter("status", value) }]}
                  onSearchChange={sqlServerTable.setSearchInput}
                  pagination={{ page: snapshot.sqlServer.page, pageSize: sqlServerTable.pageSize, pages: snapshot.sqlServer.pages ?? 1, total: snapshot.sqlServer.total, onPageChange: sqlServerTable.setPage, onPageSizeChange: sqlServerTable.setPageSize }}
                  searchPlaceholder="搜索群集名称或描述"
                  searchValue={sqlServerTable.searchInput}
                />
              </ListPanel>
            </TabsContent>
            <TabsContent className="mt-0 grid gap-3" value="mysql">
              <ListPanel title="MySQL 群集" description="主从拓扑、绑定实例和复制状态。" count={snapshot.mySql.total}>
                <DataTable
                  columns={mysqlClusterColumns}
                  data={snapshot.mySql.items}
                  filters={[{ columnId: "is_enabled", label: "状态", options: [{ label: "启用", value: "active" }, { label: "停用", value: "inactive" }], value: mySqlTable.filters.status, onValueChange: (value) => mySqlTable.setFilter("status", value) }]}
                  onSearchChange={mySqlTable.setSearchInput}
                  pagination={{ page: snapshot.mySql.page, pageSize: mySqlTable.pageSize, pages: snapshot.mySql.pages ?? 1, total: snapshot.mySql.total, onPageChange: mySqlTable.setPage, onPageSizeChange: mySqlTable.setPageSize }}
                  searchPlaceholder="搜索群集名称或描述"
                  searchValue={mySqlTable.searchInput}
                />
              </ListPanel>
            </TabsContent>
          </Tabs>
        )}
      </QueryFrame>
      {maintainingCluster?.panel === "instances" ? (
        <ClusterInstanceBindingPanel
          item={maintainingCluster.item}
          mode={maintainingCluster.mode}
          onClose={() => setMaintainingCluster(null)}
          onSaved={refreshClusters}
        />
      ) : null}
      {maintainingCluster?.mode === "sqlserver" && maintainingCluster.panel === "sqlserver-ag" ? (
        <SqlServerAgConfigurationPanel
          item={maintainingCluster.item}
          onClose={() => setMaintainingCluster(null)}
          onSaved={refreshClusters}
        />
      ) : null}
      {creatingCluster ? (
        <ClusterFormDialog
          item={null}
          mode={creatingCluster}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingCluster(null);
            }
          }}
          onSaved={handleClusterSaved}
          open
        />
      ) : null}
      {editingCluster ? (
        <ClusterFormDialog
          item={editingCluster.item}
          mode={editingCluster.mode}
          onOpenChange={(open) => {
            if (!open) {
              setEditingCluster(null);
            }
          }}
          onSaved={handleClusterSaved}
          open
        />
      ) : null}
      {viewingCluster?.mode === "sqlserver" ? (
        <SqlServerClusterDetailDialog
          item={viewingCluster.item}
          onOpenChange={(open) => {
            if (!open) {
              setViewingCluster(null);
            }
          }}
          open
        />
      ) : null}
      {viewingCluster?.mode === "mysql" ? (
        <MySqlClusterDetailDialog
          item={viewingCluster.item}
          onOpenChange={(open) => {
            if (!open) {
              setViewingCluster(null);
            }
          }}
          open
        />
      ) : null}
    </main>
  );
}

function riskLevelLabel(value: number | undefined): string {
  switch (value) {
    case 1:
      return "1级(最高)";
    case 2:
      return "2级";
    case 3:
      return "3级";
    case 4:
      return "4级(默认)";
    case 5:
      return "5级";
    case 6:
      return "6级(最低)";
    default:
      return "未标记风险";
  }
}

function ruleGroupTitle(dbType: string): string {
  return `${(dbType || "unknown").toUpperCase()} 规则`;
}

function flattenPermissionValues(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((entry) => flattenPermissionValues(entry));
  }
  if (value && typeof value === "object") {
    return Object.values(value as Record<string, unknown>).flatMap((entry) => flattenPermissionValues(entry));
  }
  if (typeof value === "string" && value.trim()) {
    return [value];
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return [String(value)];
  }
  return [];
}

function ruleExpressionFunction(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const fn = (value as Record<string, unknown>).fn;
  return typeof fn === "string" && fn.trim() ? fn : null;
}

function RuleDetailDialog({
  item,
  onOpenChange,
  open
}: {
  item: AccountClassificationRuleItem;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const detailQuery = useQuery({
    queryKey: ["read-only", "account-classification-rule", item.id],
    queryFn: () => fetchAccountClassificationRuleDetail(item.id),
    enabled: open
  });
  const permissionsQuery = useQuery({
    queryKey: ["read-only", "account-classification-permissions", item.db_type],
    queryFn: () => fetchAccountClassificationPermissions(item.db_type),
    enabled: open
  });
  const rule = detailQuery.data?.rule ?? item;
  const permissionValues = [...new Set(flattenPermissionValues(permissionsQuery.data?.permissions))];
  const expressionFunction = ruleExpressionFunction(rule.rule_expression);

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),46rem)]">
        <DialogHeader>
          <DialogTitle>规则详情 {item.rule_name}</DialogTitle>
          <DialogDescription>展示规则版本、表达式和当前数据库类型的权限元数据。</DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap gap-1">
          <Badge variant="secondary">规则详情</Badge>
          <Badge variant="outline">{rule.db_type}</Badge>
          <Badge variant={rule.is_active ? "secondary" : "outline"}>{rule.is_active ? "启用" : "停用"}</Badge>
          {rule.rule_version ? <Badge variant="outline">版本 {rule.rule_version}</Badge> : null}
          {expressionFunction ? <Badge variant="outline">{expressionFunction}</Badge> : null}
        </div>
        {detailQuery.isLoading ? <Skeleton className="h-20 w-full" /> : null}
        <div className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
          <DetailBlock label="规则名称">{rule.rule_name}</DetailBlock>
          <DetailBlock label="账户分类">{asText(rule.classification_name, "未分类")}</DetailBlock>
          <DetailBlock label="数据库类型">{rule.db_type}</DetailBlock>
          <DetailBlock label="规则组">{asText(rule.rule_group_id)}</DetailBlock>
          <DetailBlock label="创建时间">{asText(rule.created_at)}</DetailBlock>
          <DetailBlock label="更新时间">{asText(rule.updated_at)}</DetailBlock>
        </div>
        <section className="grid gap-2">
          <h3 className="text-sm font-semibold">规则表达式</h3>
          <JsonBlock value={rule.rule_expression} />
        </section>
        <section className="grid gap-2">
          <h3 className="text-sm font-semibold">权限选项</h3>
          {permissionsQuery.isLoading ? <Skeleton className="h-10 w-full" /> : null}
          {permissionValues.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {permissionValues.map((value) => (
                <Badge key={value} variant="outline">
                  {value}
                </Badge>
              ))}
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">暂无权限元数据</span>
          )}
        </section>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ClassificationList({
  canManage,
  items,
  onDelete,
  onEdit
}: {
  canManage: boolean;
  items: AccountClassificationItem[];
  onDelete: (item: AccountClassificationItem) => void;
  onEdit: (item: AccountClassificationItem) => void;
}) {
  if (items.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">{canManage ? "暂无分类，点击“新建分类”开始配置" : "暂无分类"}</p>;
  }
  return (
    <div className="grid gap-2">
      {items.map((item) => (
        <div className="rounded-md border bg-background p-3" key={item.id}>
          <div className="flex items-start justify-between gap-3">
            <div className="grid gap-2">
              <div>
                <div className="font-medium">{item.display_name}</div>
                <div className="font-mono text-xs text-muted-foreground">#{item.code}</div>
              </div>
              <div className="flex flex-wrap gap-1">
                {item.is_system ? <Badge variant="secondary">系统</Badge> : <Badge variant="outline">自定义</Badge>}
                <Badge variant="outline">{riskLevelLabel(item.risk_level)}</Badge>
                <Badge variant="outline">规则 {formatNumber(item.rules_count)}</Badge>
              </div>
            </div>
            {canManage ? (
              <div className="flex items-center gap-1">
                <Button aria-label={`编辑分类 ${item.display_name}`} onClick={() => onEdit(item)} size="icon" type="button" variant="ghost">
                  <Pencil aria-hidden />
                </Button>
                {!item.is_system ? (
                  <Button aria-label={`删除分类 ${item.display_name}`} onClick={() => onDelete(item)} size="icon" type="button" variant="ghost">
                    <Trash2 aria-hidden />
                  </Button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function RuleGroups({
  canManage,
  rulesByDbType,
  onDeleteRule,
  onEditRule,
  onViewRule
}: {
  canManage: boolean;
  rulesByDbType: Record<string, AccountClassificationRuleItem[]>;
  onDeleteRule: (rule: AccountClassificationRuleItem) => void;
  onEditRule: (rule: AccountClassificationRuleItem) => void;
  onViewRule: (rule: AccountClassificationRuleItem) => void;
}) {
  const entries = Object.entries(rulesByDbType).filter(([, rules]) => rules.length > 0);
  if (entries.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">{canManage ? "暂无规则，点击“新建规则”开始配置" : "暂无规则"}</p>;
  }
  return (
    <div className="grid gap-2">
      {entries.map(([dbType, rules]) => (
        <div className="rounded-md border bg-background p-3" key={dbType}>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{ruleGroupTitle(dbType)}</h3>
            <Badge variant="secondary">{formatNumber(rules.length)}</Badge>
          </div>
          <div className="grid gap-2">
            {rules.map((rule) => (
              <div className="flex items-center justify-between gap-3 rounded-md border p-3 max-sm:grid" key={rule.id}>
                <div className="grid gap-1">
                  <div className="font-medium">{rule.rule_name}</div>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline">{rule.classification_name ?? "未分类"}</Badge>
                    <Badge variant={rule.is_active ? "secondary" : "outline"}>{rule.is_active ? "启用" : "停用"}</Badge>
                    <Badge variant="outline">{formatNumber(rule.matched_accounts_count)}</Badge>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button aria-label={`查看规则 ${rule.rule_name}`} onClick={() => onViewRule(rule)} size="icon" type="button" variant="ghost">
                    <ExternalLink aria-hidden />
                  </Button>
                  {canManage ? (
                    <>
                      <Button aria-label={`编辑规则 ${rule.rule_name}`} onClick={() => onEditRule(rule)} size="icon" type="button" variant="ghost">
                        <Pencil aria-hidden />
                      </Button>
                      <Button aria-label={`删除规则 ${rule.rule_name}`} onClick={() => onDeleteRule(rule)} size="icon" type="button" variant="ghost">
                        <Trash2 aria-hidden />
                      </Button>
                    </>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AccountClassificationsPage({ currentUser }: { currentUser?: AccessUser | null } = {}) {
  const query = useQuery({
    queryKey: ["read-only", "account-classifications"],
    queryFn: () => fetchAccountClassificationsSnapshot()
  });
  const [creatingClassification, setCreatingClassification] = useState(false);
  const [editingClassification, setEditingClassification] = useState<AccountClassificationItem | null>(null);
  const [deletingClassification, setDeletingClassification] = useState<AccountClassificationItem | null>(null);
  const [creatingRule, setCreatingRule] = useState(false);
  const [editingRule, setEditingRule] = useState<AccountClassificationRuleItem | null>(null);
  const [viewingRule, setViewingRule] = useState<AccountClassificationRuleItem | null>(null);
  const [deletingRule, setDeletingRule] = useState<AccountClassificationRuleItem | null>(null);
  const canManage = canManageCatalog(currentUser);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Account taxonomy" title="账户分类" description="展示分类、风险等级与规则分布，新增和编辑仍保留在旧版。" legacyHref="/accounts/classifications/" />
      {canManage ? (
        <CommandBar>
          <Button
            onClick={() => {
              void runAction(autoClassifyAccounts(), { success: "自动分类已触发" }).then(() => query.refetch());
            }}
            type="button"
            variant="outline"
          >
            <Zap aria-hidden size={16} />
            <span>自动分类</span>
          </Button>
        </CommandBar>
      ) : null}
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="账户分类" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          return (
            <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
              <ListPanel
                title="账户分类"
                actions={
                  canManage ? (
                    <Button onClick={() => setCreatingClassification(true)} size="sm" type="button">
                      <Plus aria-hidden size={16} />
                      <span>新建分类</span>
                    </Button>
                  ) : null
                }
              >
                <ClassificationList
                  canManage={canManage}
                  items={snapshot.classifications}
                  onEdit={setEditingClassification}
                  onDelete={setDeletingClassification}
                />
              </ListPanel>
              <ListPanel
                title="规则管理"
                actions={
                  canManage ? (
                    <Button onClick={() => setCreatingRule(true)} size="sm" type="button">
                      <Plus aria-hidden size={16} />
                      <span>新建规则</span>
                    </Button>
                  ) : null
                }
              >
                <RuleGroups
                  canManage={canManage}
                  onDeleteRule={setDeletingRule}
                  onEditRule={setEditingRule}
                  onViewRule={setViewingRule}
                  rulesByDbType={snapshot.rulesByDbType}
                />
              </ListPanel>
            </section>
          );
        }}
      </QueryFrame>
      {query.data ? (
        <>
          {canManage && creatingClassification ? (
            <ClassificationFormDialog
              item={null}
              onOpenChange={(open) => {
                if (!open) {
                  setCreatingClassification(false);
                }
              }}
              onSaved={() => {
                setCreatingClassification(false);
                void query.refetch();
              }}
              open={creatingClassification}
            />
          ) : null}
          {canManage && editingClassification ? (
            <ClassificationFormDialog
              item={editingClassification}
              onOpenChange={(open) => {
                if (!open) {
                  setEditingClassification(null);
                }
              }}
              onSaved={() => {
                setEditingClassification(null);
                void query.refetch();
              }}
              open={editingClassification !== null}
            />
          ) : null}
          {canManage && creatingRule ? (
            <RuleFormDialog
              classifications={query.data.classifications}
              item={null}
              onOpenChange={(open) => {
                if (!open) {
                  setCreatingRule(false);
                }
              }}
              onSaved={() => {
                setCreatingRule(false);
                void query.refetch();
              }}
              open={creatingRule}
            />
          ) : null}
          {canManage && editingRule ? (
            <RuleFormDialog
              classifications={query.data.classifications}
              item={editingRule}
              onOpenChange={(open) => {
                if (!open) {
                  setEditingRule(null);
                }
              }}
              onSaved={() => {
                setEditingRule(null);
                void query.refetch();
              }}
              open={editingRule !== null}
            />
          ) : null}
          {viewingRule ? (
            <RuleDetailDialog
              item={viewingRule}
              onOpenChange={(open) => {
                if (!open) {
                  setViewingRule(null);
                }
              }}
              open={viewingRule !== null}
            />
          ) : null}
          <DeleteConfirmDialog
            confirmLabel="确认删除分类"
            description="删除分类后，该分类下的规则和账户归类关系会按后端规则处理。"
            onConfirm={() => {
              const classification = deletingClassification;
              setDeletingClassification(null);
              if (classification) {
                void runAction(deleteAccountClassification(classification.id), { success: "账户分类已删除" }).then(() => query.refetch());
              }
            }}
            onOpenChange={(open) => {
              if (!open) {
                setDeletingClassification(null);
              }
            }}
            open={canManage && deletingClassification !== null}
            title={`确认删除分类 ${deletingClassification?.display_name ?? ""}`}
          />
          <DeleteConfirmDialog
            confirmLabel="确认删除规则"
            description="删除规则后，后续自动分类不再使用该规则。"
            onConfirm={() => {
              const rule = deletingRule;
              setDeletingRule(null);
              if (rule) {
                void runAction(deleteAccountClassificationRule(rule.id), { success: "分类规则已删除" }).then(() => query.refetch());
              }
            }}
            onOpenChange={(open) => {
              if (!open) {
                setDeletingRule(null);
              }
            }}
            open={canManage && deletingRule !== null}
            title={`确认删除规则 ${deletingRule?.rule_name ?? ""}`}
          />
        </>
      ) : null}
    </main>
  );
}

type ClassificationFiltersState = {
  accountScope: string;
  classificationId: string;
  dbType: string;
  periodType: string;
  periods: string;
  ruleId: string;
  ruleStatus: string;
};

const DEFAULT_CLASSIFICATION_FILTERS: ClassificationFiltersState = {
  accountScope: "",
  classificationId: "",
  dbType: "",
  periodType: "daily",
  periods: "7",
  ruleId: "",
  ruleStatus: "active"
};

function buildTrendChartData(points: ClassificationStatisticsSnapshot["trends"]["series"][number]["points"]): Array<Record<string, string | number>> {
  return points.map((point, index) => ({
    label: point.period_start ?? point.period_end ?? String(index + 1),
    value: asNumber(point.value ?? point.value_avg ?? point.value_sum)
  }));
}

function selectedTrendPoints(
  snapshot: ClassificationStatisticsSnapshot,
  filters: ClassificationFiltersState
): ClassificationStatisticsSnapshot["trends"]["series"][number]["points"] {
  if (filters.ruleId && snapshot.selectedRuleTrend) {
    return snapshot.selectedRuleTrend;
  }
  if (filters.classificationId && snapshot.selectedClassificationTrend) {
    return snapshot.selectedClassificationTrend;
  }
  return snapshot.trends.series[0]?.points ?? [];
}

function selectedTrendName(snapshot: ClassificationStatisticsSnapshot, filters: ClassificationFiltersState): string | null {
  if (filters.ruleId) {
    return snapshot.rulesOverview?.rules.find((rule) => String(rule.rule_id) === filters.ruleId)?.rule_name ?? `规则 #${filters.ruleId}`;
  }
  if (filters.classificationId) {
    return snapshot.trends.series.find((series) => String(series.classification_id) === filters.classificationId)?.classification_name ?? `分类 #${filters.classificationId}`;
  }
  return snapshot.trends.series[0]?.classification_name ?? null;
}

function buildClassificationOptions(snapshot: ClassificationStatisticsSnapshot): Array<{ value: string; label: string }> {
  return snapshot.trends.series.map((series) => ({
    value: String(series.classification_id),
    label: series.classification_name
  }));
}

function trendCoverageLabel(snapshot: ClassificationStatisticsSnapshot, points: ClassificationStatisticsSnapshot["trends"]["series"][number]["points"]): string {
  const total = snapshot.trends.buckets.length || points.length;
  const covered = points.length;
  return `覆盖 ${formatNumber(covered)}/${formatNumber(total)} 天`;
}

function toClassificationApiFilters(filters: ClassificationFiltersState): ClassificationStatisticsFilters {
  return {
    accountScope: filters.accountScope || undefined,
    classificationId: filters.classificationId || undefined,
    dbType: filters.dbType || undefined,
    periodType: filters.periodType || undefined,
    periods: Number(filters.periods || 7),
    ruleId: filters.ruleId || undefined,
    ruleStatus: filters.ruleStatus || undefined
  };
}

function buildRuleContributionChartData(items: ClassificationRuleContributionItem[]): Array<Record<string, string | number>> {
  return items.map((item) => ({
    label: item.rule_name,
    value: asNumber(item.value_sum ?? item.value_avg)
  }));
}

function ClassificationFilterPanel({
  accountScopeOptions,
  draft,
  onApply,
  onDraftChange,
  onReset,
  snapshot
}: {
  accountScopeOptions: AccountScopeOption[];
  draft: ClassificationFiltersState;
  onApply: () => void;
  onDraftChange: (draft: ClassificationFiltersState) => void;
  onReset: () => void;
  snapshot: ClassificationStatisticsSnapshot;
}) {
  const classificationOptions = buildClassificationOptions(snapshot);
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  return (
    <Card>
      <CardContent className="grid gap-3">
        <form
          className="grid grid-cols-[minmax(12rem,1.3fr)_minmax(8rem,0.7fr)_minmax(8rem,0.7fr)_minmax(8rem,0.7fr)_auto] items-end gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1"
          onSubmit={handleSubmit}
        >
          <label className="grid gap-1.5 text-sm font-medium">
            <span>账户分类</span>
            <SelectControl
              label="账户分类"
              onValueChange={(classificationId) => onDraftChange({ ...draft, classificationId, ruleId: "" })}
              options={[{ label: "全部分类", value: "" }, ...classificationOptions]}
              value={draft.classificationId}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>统计周期</span>
            <SelectControl
              label="统计周期"
              onValueChange={(periodType) => onDraftChange({ ...draft, periodType, ruleId: "" })}
              options={[
                { label: "日统计", value: "daily" },
                { label: "周统计", value: "weekly" },
                { label: "月统计", value: "monthly" },
                { label: "季统计", value: "quarterly" },
                { label: "年统计（即将支持）", value: "yearly", disabled: true }
              ]}
              value={draft.periodType}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>数据库类型</span>
            <SelectControl
              label="数据库类型"
              onValueChange={(dbType) => onDraftChange({ ...draft, accountScope: "", dbType, ruleId: "" })}
              options={[
                { label: "全部类型", value: "" },
                { label: "MySQL", value: "mysql" },
                { label: "PostgreSQL", value: "postgresql" },
                { label: "SQL Server", value: "sqlserver" },
                { label: "Oracle", value: "oracle" }
              ]}
              value={draft.dbType}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>实例/AG</span>
            <SelectControl
              disabled={!draft.dbType}
              label="实例/AG"
              onValueChange={(accountScope) => onDraftChange({ ...draft, accountScope, ruleId: "" })}
              options={[{ label: "所有实例/AG", value: "" }, ...accountScopeOptions.map((option) => ({ label: option.label, value: option.value }))]}
              value={draft.accountScope}
            />
          </label>
          <div className="flex gap-2">
            <Button variant="outline" type="submit">
              应用
            </Button>
            <Button onClick={onReset} type="button" variant="ghost">
              重置
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function ClassificationRulesListPanel({
  filters,
  onRuleSelect,
  onRuleStatusChange,
  onSearchChange,
  rules,
  search
}: {
  filters: ClassificationFiltersState;
  onRuleSelect: (ruleId: string) => void;
  onRuleStatusChange: (status: string) => void;
  onSearchChange: (search: string) => void;
  rules: ClassificationRuleOverviewItem[];
  search: string;
}) {
  const visibleRules = rules.filter((rule) => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) {
      return true;
    }
    return [rule.rule_name, rule.db_type, String(rule.rule_id)].some((value) => String(value ?? "").toLowerCase().includes(keyword));
  });

  return (
    <ListPanel
      title="规则列表"
      actions={<Badge variant="outline">最新周期</Badge>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-[minmax(0,1fr)_9rem] gap-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>搜索规则名/备注</span>
            <Input onChange={(event) => onSearchChange(event.target.value)} type="search" value={search} />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>状态</span>
            <SelectControl
              label="状态"
              onValueChange={onRuleStatusChange}
              options={[
                { label: "启用", value: "active" },
                { label: "已归档", value: "archived" },
                { label: "全部", value: "all" }
              ]}
              value={filters.ruleStatus}
            />
          </label>
        </div>
        {filters.classificationId ? (
          <Table>
            <TableHeader className="text-xs">
              <TableRow>
                <TableHead>规则</TableHead>
                <TableHead>数据库</TableHead>
                <TableHead>当前周期命中</TableHead>
                <TableHead>覆盖</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleRules.length === 0 ? <EmptyRows colSpan={6} /> : null}
              {visibleRules.map((rule) => (
                <TableRow data-state={filters.ruleId === String(rule.rule_id) ? "selected" : undefined} key={rule.rule_id}>
                  <TableCell className="font-medium">{rule.rule_name}</TableCell>
                  <TableCell>{rule.db_type ?? "-"}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {formatNumber(asNumber(rule.latest_value_sum ?? rule.latest_value_avg))}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {formatNumber(rule.latest_coverage_days)}/{formatNumber(rule.latest_expected_days)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={rule.is_active} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => onRuleSelect(String(rule.rule_id))}>
                      查看趋势
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
            选择分类后加载规则列表与规则趋势
          </div>
        )}
      </div>
    </ListPanel>
  );
}

export function ClassificationStatisticsPage() {
  const [filters, setFilters] = useState<ClassificationFiltersState>(DEFAULT_CLASSIFICATION_FILTERS);
  const [draftFilters, setDraftFilters] = useState<ClassificationFiltersState>(DEFAULT_CLASSIFICATION_FILTERS);
  const [ruleSearch, setRuleSearch] = useState("");
  const query = useQuery({
    queryKey: ["read-only", "classification-statistics", filters],
    queryFn: () => fetchClassificationStatisticsSnapshot(toClassificationApiFilters(filters))
  });
  const accountScopeQuery = useQuery({
    enabled: Boolean(draftFilters.dbType),
    queryKey: ["read-only", "classification-account-scopes", draftFilters.dbType],
    queryFn: () => fetchAccountScopeOptions(draftFilters.dbType)
  });
  const chartConfig = { value: { label: "匹配账户", color: "var(--chart-1)" } } satisfies ChartConfig;
  const contributionChartConfig = { value: { label: "规则贡献", color: "var(--chart-2)" } } satisfies ChartConfig;

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Classification analytics" title="分类统计" description="只读展示账户分类统计、规则列表入口和最近周期趋势，写操作仍保留在旧版。" legacyHref="/accounts/statistics/classifications" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="分类统计" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const trendPoints = selectedTrendPoints(snapshot, filters);
          const chartData = buildTrendChartData(trendPoints);
          const coverageLabel = trendCoverageLabel(snapshot, trendPoints);
          const trendName = selectedTrendName(snapshot, filters);
          const rules = snapshot.rulesOverview?.rules ?? [];
          const contributionItems = snapshot.ruleContributions?.contributions ?? [];
          const contributionData = buildRuleContributionChartData(contributionItems);
          return (
            <>
              <ClassificationFilterPanel
                accountScopeOptions={accountScopeQuery.data ?? []}
                draft={draftFilters}
                onApply={() => {
                  setFilters({ ...draftFilters, ruleId: "" });
                  setRuleSearch("");
                }}
                onDraftChange={setDraftFilters}
                onReset={() => {
                  setDraftFilters(DEFAULT_CLASSIFICATION_FILTERS);
                  setFilters(DEFAULT_CLASSIFICATION_FILTERS);
                  setRuleSearch("");
                }}
                snapshot={snapshot}
              />
              <section className="grid grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)] gap-2 max-xl:grid-cols-1">
                <ClassificationRulesListPanel
                  filters={filters}
                  onRuleSelect={(ruleId) => {
                    setFilters({ ...filters, ruleId });
                    setDraftFilters({ ...draftFilters, ruleId });
                  }}
                  onRuleStatusChange={(ruleStatus) => {
                    setFilters({ ...filters, ruleId: "", ruleStatus });
                    setDraftFilters({ ...draftFilters, ruleId: "", ruleStatus });
                  }}
                  onSearchChange={setRuleSearch}
                  rules={rules}
                  search={ruleSearch}
                />
                <div className="grid gap-2">
                  <Card>
                    <CardHeader className="flex flex-row items-start justify-between gap-3">
                      <div>
                        <CardTitle>{filters.ruleId ? "规则趋势（命中账号数）" : "分类趋势（去重账号数）"}</CardTitle>
                      </div>
                      <Badge variant="outline">{coverageLabel}</Badge>
                    </CardHeader>
                    <CardContent>
                      {trendName ? <div className="mb-2 text-sm font-medium">{trendName}</div> : null}
                      {chartData.length > 0 ? (
                        <ChartContainer config={chartConfig} className="h-[240px] w-full">
                          <AreaChart accessibilityLayer data={chartData} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                            <defs>
                              <linearGradient id="classificationTrendFill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-value)" stopOpacity={0.34} />
                                <stop offset="95%" stopColor="var(--color-value)" stopOpacity={0.04} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid vertical={false} />
                            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Area dataKey="value" name="匹配账户" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill="url(#classificationTrendFill)" />
                          </AreaChart>
                        </ChartContainer>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂无趋势数据</p>
                      )}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="flex flex-row items-start justify-between gap-3">
                      <div>
                        <CardTitle>规则贡献（当前周期）</CardTitle>
                      </div>
                      <Badge variant="outline">
                        覆盖 {formatNumber(snapshot.ruleContributions?.coverage_days)}/{formatNumber(snapshot.ruleContributions?.expected_days)}
                      </Badge>
                    </CardHeader>
                    <CardContent className="grid gap-3">
                      {contributionData.length > 0 ? (
                        <ChartContainer config={contributionChartConfig} className="h-[220px] w-full">
                          <BarChart accessibilityLayer data={contributionData} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                            <CartesianGrid vertical={false} />
                            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Bar dataKey="value" name="规则贡献" fill="var(--color-value)" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ChartContainer>
                      ) : (
                        <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
                          选择分类后展示规则贡献
                        </div>
                      )}
                      {contributionItems.length > 0 ? (
                        <div className="grid gap-2">
                          {contributionItems.slice(0, 5).map((item) => (
                            <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/30 px-3 py-2 text-sm" key={item.rule_id}>
                              <span className="truncate">{item.rule_name}</span>
                              <span className="font-mono">贡献 {formatNumber(asNumber(item.value_sum ?? item.value_avg))}</span>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      <p className="text-sm text-muted-foreground">说明：规则之间允许重叠，“各规则之和”不等于分类去重总数。</p>
                    </CardContent>
                  </Card>
                </div>
              </section>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}

export function SchedulerPage() {
  const query = useQuery({ queryKey: ["read-only", "scheduler"], queryFn: () => fetchSchedulerSnapshot() });
  const [editingJob, setEditingJob] = useState<SchedulerJobItem | null>(null);
  const [viewingJob, setViewingJob] = useState<SchedulerJobItem | null>(null);
  const [deletingJob, setDeletingJob] = useState<SchedulerJobItem | null>(null);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation jobs" title="定时任务" description="只读展示调度任务和运行状态，暂停、恢复、立即执行仍保留在旧版。" legacyHref="/scheduler/" />
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
                  onDelete={setDeletingJob}
                  onEdit={setEditingJob}
                  onView={setViewingJob}
                />
                <SchedulerJobSection
                  title="已暂停的任务"
                  jobs={snapshot.jobs.filter((job) => !isRunningState(job.state))}
                  onDelete={setDeletingJob}
                  onEdit={setEditingJob}
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
      <DeleteConfirmDialog
        confirmLabel="确认删除任务"
        description="删除任务后将从调度器移除，后续需要重新初始化或重新配置。"
        onConfirm={() => {
          const job = deletingJob;
          setDeletingJob(null);
          if (job) {
            void runAction(deleteSchedulerJob(job.id), { success: "任务已删除" }).then(() => query.refetch());
          }
        }}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingJob(null);
          }
        }}
        open={deletingJob !== null}
        title={`确认删除任务 ${deletingJob ? schedulerJobName(deletingJob) : ""}`}
      />
    </main>
  );
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
      <PageHeader eyebrow="Automation sessions" title="会话中心" description="展示同步会话、实例执行详情、错误日志，并支持取消运行中会话。" legacyHref="/history/sessions/" />
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

export function UsersPage({ currentUser }: { currentUser?: AccessUser | null } = {}) {
  const tableState = useServerTableState({ initialFilters: { role: "", status: "" } });
  const listQuery = { page: tableState.page, limit: tableState.pageSize, search: tableState.search, role: tableState.filters.role, status: tableState.filters.status };
  const query = useQuery({ queryKey: ["read-only", "users", listQuery], queryFn: () => fetchUsersSnapshot(listQuery), placeholderData: (previous) => previous });
  const [creatingUser, setCreatingUser] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [deletingUser, setDeletingUser] = useState<UserItem | null>(null);
  const canManage = canManageCatalog(currentUser);
  const currentUserId = currentUser?.id ?? null;
  const columns = useMemo(
    () =>
      createUserColumns({
        canManage,
        currentUserId,
        onDelete: setDeletingUser,
        onEdit: setEditingUser
      }),
    [canManage, currentUserId]
  );

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Access control" title="用户管理" description="展示用户、角色与启用状态，并支持新增、编辑、删除。" legacyHref="/users/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="用户管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <ListPanel
              title="用户列表"
              count={snapshot.list.total}
              actions={
                canManage ? (
                  <Button onClick={() => setCreatingUser(true)} size="sm" type="button">
                  <Plus aria-hidden />
                  新建用户
                  </Button>
                ) : (
                  <Badge variant="outline">只读</Badge>
                )
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  {
                    columnId: "role",
                    label: "角色",
                    value: tableState.filters.role,
                    onValueChange: (value) => tableState.setFilter("role", value),
                    options: [
                      { label: "管理员", value: "admin" },
                      { label: "普通用户", value: "user" },
                      { label: "查看者", value: "viewer" }
                    ]
                  },
                  {
                    columnId: "is_active",
                    label: "状态",
                    value: tableState.filters.status,
                    onValueChange: (value) => tableState.setFilter("status", value),
                    options: [
                      { label: "启用", value: "active" },
                      { label: "停用", value: "inactive" }
                    ]
                  }
                ]}
                onSearchChange={tableState.setSearchInput}
                pagination={{ page: snapshot.list.page, pageSize: tableState.pageSize, pages: snapshot.list.pages ?? 1, total: snapshot.list.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
                searchPlaceholder="搜索用户名或邮箱"
                searchValue={tableState.searchInput}
              />
          </ListPanel>
        )}
      </QueryFrame>
      {canManage && creatingUser ? (
        <UserFormDialog
          item={null}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingUser(false);
            }
          }}
          onSaved={() => {
            setCreatingUser(false);
            void query.refetch();
          }}
          open={creatingUser}
        />
      ) : null}
      {canManage && editingUser ? (
        <UserFormDialog
          item={editingUser}
          onOpenChange={(open) => {
            if (!open) {
              setEditingUser(null);
            }
          }}
          onSaved={() => {
            setEditingUser(null);
            void query.refetch();
          }}
          open={editingUser !== null}
        />
      ) : null}
      <DeleteConfirmDialog
        confirmLabel="确认删除用户"
        description="删除用户后，该账号将不能继续登录。"
        onConfirm={() => {
          if (!deletingUser) {
            return;
          }
          const userId = deletingUser.id;
          setDeletingUser(null);
          void runAction(deleteUser(userId), { success: "用户已删除" }).then(() => query.refetch());
        }}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingUser(null);
          }
        }}
        open={canManage && deletingUser !== null}
        title={`确认删除用户 ${deletingUser?.username ?? ""}`}
      />
    </main>
  );
}

function SettingsCard({ title, description, status, children }: { title: string; description: string; status?: string | boolean; children: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        {status !== undefined ? <StatusBadge value={status} /> : null}
      </CardHeader>
      <CardContent className="grid gap-2 text-sm">{children}</CardContent>
    </Card>
  );
}

function settingsEnabledCount(snapshot: SettingsSnapshot): number {
  const alertSettings = snapshot.alerts.settings ?? {};
  return [
    snapshot.alerts.smtp_ready,
    alertSettings.global_enabled,
    snapshot.jumpserver.provider_ready,
    snapshot.veeam.provider_ready,
    snapshot.adDomains.configs.some((item) => item.is_enabled === true)
  ].filter(Boolean).length;
}

function ReadonlyField({ label, value }: { label: string; value?: unknown }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      <Input readOnly value={asText(value)} />
    </label>
  );
}

function SettingsSubsection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3 rounded-md border bg-secondary/20 p-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function textList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => asText(item, "")).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(/[,;\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function settingsRecipients(alerts: SettingsSnapshot["alerts"]): string[] {
  const settings = alerts.settings ?? {};
  return textList(settings.recipients);
}

function riskRulePayload(rules: SettingsSnapshot["riskRules"]) {
  return rules
    .map((rule) => ({
      rule_key: asText(rule.rule_key, ""),
      enabled: rule.enabled === true,
      severity: asText(rule.severity, "medium")
    }))
    .filter((rule) => rule.rule_key);
}

function numericId(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function numericValue(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function booleanValue(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function firstRecordId(items: unknown[]): number {
  for (const item of items) {
    if (item && typeof item === "object") {
      const id = numericId((item as Record<string, unknown>).id);
      if (id !== null) {
        return id;
      }
    }
  }
  return 0;
}

function jumpServerSourcePayload(binding: Record<string, unknown>, credentials: unknown[]): JumpServerSourcePayload | null {
  const credentialId = numericValue(binding.credential_id, firstRecordId(credentials));
  const baseUrl = asText(binding.base_url, "");
  if (credentialId <= 0 || !baseUrl) {
    return null;
  }
  return {
    credential_id: credentialId,
    base_url: baseUrl,
    org_id: asText(binding.org_id, "") || null,
    verify_ssl: booleanValue(binding.verify_ssl, true)
  };
}

function veeamSourcePayload(source: Record<string, unknown>, credentials: unknown[]): VeeamSourcePayload | null {
  const credentialId = numericValue(source.credential_id, firstRecordId(credentials));
  const serverHost = asText(source.server_host, "");
  if (credentialId <= 0 || !serverHost) {
    return null;
  }
  return {
    name: asText(source.name, "") || null,
    credential_id: credentialId,
    server_host: serverHost,
    server_port: numericValue(source.server_port, 9419),
    api_version: asText(source.api_version, "v1"),
    verify_ssl: booleanValue(source.verify_ssl, true),
    match_domains: textList(source.match_domains ?? source.domains)
  };
}

function adDomainPayload(config: Record<string, unknown>): AdDomainConfigPayload | null {
  const credentialId = numericValue(config.credential_id, 0);
  const name = asText(config.name, "");
  const netbiosName = asText(config.netbios_name, "");
  const baseDn = asText(config.base_dn, "");
  const controllers = textList(config.domain_controllers);
  if (credentialId <= 0 || !name || !netbiosName || !baseDn || controllers.length === 0) {
    return null;
  }
  return {
    name,
    netbios_name: netbiosName,
    domain_controllers: controllers,
    ldap_port: numericValue(config.ldap_port, 636),
    use_ssl: booleanValue(config.use_ssl, numericValue(config.ldap_port, 636) === 636),
    verify_ssl: booleanValue(config.verify_ssl, true),
    base_dn: baseDn,
    credential_id: credentialId,
    is_enabled: booleanValue(config.is_enabled, true),
    description: asText(config.description, "") || null
  };
}

type AlertSettingsFormState = {
  account_sync_failure_enabled: boolean;
  backup_issue_enabled: boolean;
  cluster_status_enabled: boolean;
  clear_feishu_webhook_url: boolean;
  database_capacity_absolute_gb_threshold: string;
  database_capacity_enabled: boolean;
  database_capacity_percent_threshold: string;
  database_sync_failure_enabled: boolean;
  feishu_enabled: boolean;
  feishu_webhook_url: string;
  global_enabled: boolean;
  privileged_account_enabled: boolean;
  recipients: string;
  shared_recipients_enabled: boolean;
};

type JumpServerFormState = {
  baseUrl: string;
  credentialId: string;
  orgId: string;
  verifySsl: boolean;
};

type VeeamFormState = {
  apiVersion: string;
  credentialId: string;
  domains: string;
  name: string;
  serverHost: string;
  serverPort: string;
  verifySsl: boolean;
};

type AdDomainFormState = {
  baseDn: string;
  credentialId: string;
  description: string;
  domainControllers: string;
  isEnabled: boolean;
  ldapPort: string;
  name: string;
  netbiosName: string;
  useSsl: boolean;
  verifySsl: string;
};

function recordList(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object") : [];
}

function settingsSnapshotKey(snapshot: SettingsSnapshot): string {
  return JSON.stringify([
    snapshot.alerts.settings,
    snapshot.riskRules,
    snapshot.jumpserver.binding,
    snapshot.veeam.sources,
    snapshot.adDomains.configs
  ]);
}

function credentialOptions(items: Array<Record<string, unknown>>, currentId: string, placeholder: string) {
  const options = items.map((item) => ({
    label: asText(item.description, "") ? `${asText(item.name, "未命名凭据")} · ${asText(item.description)}` : asText(item.name, "未命名凭据"),
    value: String(numericValue(item.id, 0))
  }));
  if (currentId && !options.some((option) => option.value === currentId)) {
    options.unshift({ label: `凭据 #${currentId}`, value: currentId });
  }
  return [{ label: placeholder, value: "" }, ...options.filter((option) => option.value !== "0")];
}

function alertSettingsFormState(settings: Record<string, unknown>): AlertSettingsFormState {
  return {
    account_sync_failure_enabled: booleanValue(settings.account_sync_failure_enabled, false),
    backup_issue_enabled: booleanValue(settings.backup_issue_enabled, false),
    cluster_status_enabled: booleanValue(settings.cluster_status_enabled, false),
    clear_feishu_webhook_url: false,
    database_capacity_absolute_gb_threshold: String(numericValue(settings.database_capacity_absolute_gb_threshold, 20)),
    database_capacity_enabled: booleanValue(settings.database_capacity_enabled, false),
    database_capacity_percent_threshold: String(numericValue(settings.database_capacity_percent_threshold, 30)),
    database_sync_failure_enabled: booleanValue(settings.database_sync_failure_enabled, false),
    feishu_enabled: booleanValue(settings.feishu_enabled, false),
    feishu_webhook_url: "",
    global_enabled: booleanValue(settings.global_enabled, false),
    privileged_account_enabled: booleanValue(settings.privileged_account_enabled, false),
    recipients: textList(settings.recipients).join("\n"),
    shared_recipients_enabled: booleanValue(settings.shared_recipients_enabled, false)
  };
}

function alertSettingsPayload(form: AlertSettingsFormState): Record<string, unknown> {
  return {
    account_sync_failure_enabled: form.account_sync_failure_enabled,
    backup_issue_enabled: form.backup_issue_enabled,
    cluster_status_enabled: form.cluster_status_enabled,
    clear_feishu_webhook_url: form.clear_feishu_webhook_url,
    database_capacity_enabled: form.database_capacity_enabled,
    database_capacity_percent_threshold: numericValue(form.database_capacity_percent_threshold, 30),
    database_capacity_absolute_gb_threshold: numericValue(form.database_capacity_absolute_gb_threshold, 20),
    database_sync_failure_enabled: form.database_sync_failure_enabled,
    feishu_enabled: form.feishu_enabled,
    feishu_webhook_url: form.feishu_webhook_url.trim(),
    global_enabled: form.global_enabled,
    privileged_account_enabled: form.privileged_account_enabled,
    recipients: textList(form.recipients),
    shared_recipients_enabled: form.shared_recipients_enabled
  };
}

function jumpServerFormState(binding: Record<string, unknown>): JumpServerFormState {
  return {
    baseUrl: asText(binding.base_url, ""),
    credentialId: String(numericValue(binding.credential_id, numericValue((binding.credential as Record<string, unknown> | undefined)?.id, 0)) || ""),
    orgId: asText(binding.org_id, ""),
    verifySsl: booleanValue(binding.verify_ssl, true)
  };
}

function jumpServerPayloadFromForm(form: JumpServerFormState): JumpServerSourcePayload | null {
  const credentialId = numericValue(form.credentialId, 0);
  const baseUrl = form.baseUrl.trim();
  if (credentialId <= 0 || !baseUrl) {
    return null;
  }
  return {
    credential_id: credentialId,
    base_url: baseUrl,
    org_id: form.orgId.trim() || null,
    verify_ssl: form.verifySsl
  };
}

function veeamFormState(source: Record<string, unknown> | null, snapshot: SettingsSnapshot): VeeamFormState {
  return {
    apiVersion: asText(source?.api_version, asText(snapshot.veeam.default_api_version, "1.2-rev0")),
    credentialId: String(numericValue(source?.credential_id, numericValue((source?.credential as Record<string, unknown> | undefined)?.id, 0)) || ""),
    domains: textList(source?.match_domains ?? source?.domains ?? snapshot.veeam.default_match_domains).join("\n"),
    name: asText(source?.name, ""),
    serverHost: asText(source?.server_host, ""),
    serverPort: String(numericValue(source?.server_port, numericValue(snapshot.veeam.default_port, 9419))),
    verifySsl: booleanValue(source?.verify_ssl, booleanValue(snapshot.veeam.default_verify_ssl, true))
  };
}

function veeamPayloadFromForm(form: VeeamFormState): VeeamSourcePayload | null {
  const credentialId = numericValue(form.credentialId, 0);
  const serverHost = form.serverHost.trim();
  if (credentialId <= 0 || !serverHost) {
    return null;
  }
  return {
    name: form.name.trim() || null,
    credential_id: credentialId,
    server_host: serverHost,
    server_port: numericValue(form.serverPort, 9419),
    api_version: form.apiVersion.trim() || "1.2-rev0",
    verify_ssl: form.verifySsl,
    match_domains: textList(form.domains)
  };
}

function adDomainFormState(config: Record<string, unknown> | null): AdDomainFormState {
  const ldapPort = numericValue(config?.ldap_port, 636);
  return {
    baseDn: asText(config?.base_dn, ""),
    credentialId: String(numericValue(config?.credential_id, numericValue((config?.credential as Record<string, unknown> | undefined)?.id, 0)) || ""),
    description: asText(config?.description, ""),
    domainControllers: textList(config?.domain_controllers).join("\n"),
    isEnabled: booleanValue(config?.is_enabled, true),
    ldapPort: String(ldapPort),
    name: asText(config?.name, ""),
    netbiosName: asText(config?.netbios_name, ""),
    useSsl: booleanValue(config?.use_ssl, ldapPort === 636),
    verifySsl: config?.verify_ssl === false ? "false" : config?.verify_ssl === true ? "true" : ""
  };
}

function adDomainPayloadFromForm(form: AdDomainFormState): AdDomainConfigPayload | null {
  const credentialId = numericValue(form.credentialId, 0);
  const name = form.name.trim();
  const netbiosName = form.netbiosName.trim();
  const baseDn = form.baseDn.trim();
  const controllers = textList(form.domainControllers);
  if (credentialId <= 0 || !name || !netbiosName || !baseDn || controllers.length === 0) {
    return null;
  }
  return {
    name,
    netbios_name: netbiosName,
    domain_controllers: controllers,
    ldap_port: numericValue(form.ldapPort, 636),
    use_ssl: form.useSsl,
    verify_ssl: form.verifySsl === "" ? null : form.verifySsl === "true",
    base_dn: baseDn,
    credential_id: credentialId,
    is_enabled: form.isEnabled,
    description: form.description.trim() || null
  };
}

function ToggleRow({ label, checked }: { label: string; checked: unknown }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 text-sm">
      <span>{label}</span>
      <StatusBadge value={checked === true} />
    </div>
  );
}

function maskWebhookUrl(value: unknown): string {
  const text = asText(value, "");
  if (!text) {
    return "未配置";
  }
  try {
    const url = new URL(text);
    const suffix = url.hostname.split(".").slice(-1)[0] || url.hostname;
    return `${url.protocol}//***.${suffix}`;
  } catch {
    return "***";
  }
}

function recordName(value: unknown, fallback = "-"): string {
  return value && typeof value === "object" ? asText((value as Record<string, unknown>).name, fallback) : fallback;
}

function adSyncMetricsText(metrics: unknown): string {
  if (!metrics || typeof metrics !== "object") {
    return "未执行同步";
  }
  const record = metrics as Record<string, unknown>;
  return [
    `AD对象 ${asText(record.ad_principals_total, "0")}`,
    `SQL账户 ${asText(record.total, "0")}`,
    `正常 ${asText(record.normal, "0")}`,
    `停用 ${asText(record.disabled, "0")}`,
    `孤账户 ${asText(record.orphaned, "0")}`,
    `更新 ${asText(record.updated, "0")}`
  ].join(" · ");
}

const severityOptions = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" }
];

type SettingsModule = "alerts" | "risk" | "jumpserver" | "veeam" | "ad";

const settingsModules: Array<{ label: string; value: SettingsModule }> = [
  { label: "告警设置", value: "alerts" },
  { label: "风险规则", value: "risk" },
  { label: "JumpServer", value: "jumpserver" },
  { label: "Veeam", value: "veeam" },
  { label: "AD 设置", value: "ad" }
];

function SettingsEditor({ onRefresh, snapshot }: { onRefresh: () => void; snapshot: SettingsSnapshot }) {
  const alertSettings = snapshot.alerts.settings ?? {};
  const veeamSources = recordList(snapshot.veeam.sources);
  const jumpserverBinding = (snapshot.jumpserver.binding as Record<string, unknown> | undefined) ?? {};
  const jumpserverCredentials = recordList(snapshot.jumpserver.api_credentials);
  const veeamCredentials = recordList(snapshot.veeam.veeam_credentials);
  const adCredentials = recordList((snapshot.adDomains as Record<string, unknown>).credentials);
  const adDomainConfigs = recordList(snapshot.adDomains.configs);
  const [alertForm, setAlertForm] = useState(() => alertSettingsFormState(alertSettings));
  const [riskRules, setRiskRules] = useState<RiskRulePayload[]>(() => riskRulePayload(recordList(snapshot.riskRules)));
  const [jumpServerForm, setJumpServerForm] = useState(() => jumpServerFormState(jumpserverBinding));
  const [selectedVeeamSourceId, setSelectedVeeamSourceId] = useState<number | null>(() => numericId(veeamSources[0]?.id));
  const [veeamForm, setVeeamForm] = useState(() => veeamFormState(veeamSources[0] ?? null, snapshot));
  const [selectedAdDomainId, setSelectedAdDomainId] = useState<number | null>(null);
  const [adDomainForm, setAdDomainForm] = useState(() => adDomainFormState(null));
  const selectedVeeamSource = selectedVeeamSourceId === null ? null : veeamSources.find((source) => numericId(source.id) === selectedVeeamSourceId) ?? null;
  const selectedAdDomain = selectedAdDomainId === null ? null : adDomainConfigs.find((config) => numericId(config.id) === selectedAdDomainId) ?? null;
  const jumpServerPayload = jumpServerPayloadFromForm(jumpServerForm);
  const veeamPayload = veeamPayloadFromForm(veeamForm);
  const adPayload = adDomainPayloadFromForm(adDomainForm);
  const [activeModule, setActiveModule] = useState<SettingsModule>("alerts");

  function editVeeamSource(source: Record<string, unknown>) {
    setSelectedVeeamSourceId(numericId(source.id));
    setVeeamForm(veeamFormState(source, snapshot));
  }

  function resetVeeamForm() {
    setSelectedVeeamSourceId(null);
    setVeeamForm(veeamFormState(null, snapshot));
  }

  function editAdDomain(config: Record<string, unknown>) {
    setSelectedAdDomainId(numericId(config.id));
    setAdDomainForm(adDomainFormState(config));
  }

  function resetAdDomainForm() {
    setSelectedAdDomainId(null);
    setAdDomainForm(adDomainFormState(null));
  }

  return (
    <>
      <Tabs className="grid grid-cols-[16rem_minmax(0,1fr)] gap-2 max-xl:grid-cols-1" value={activeModule} onValueChange={(value) => setActiveModule(value as SettingsModule)}>
        <Card className="self-start">
          <CardHeader>
            <CardTitle>设置模块</CardTitle>
          </CardHeader>
          <CardContent>
            <TabsList className="grid h-auto w-full gap-2 bg-transparent p-0">
              {settingsModules.map((module) => (
                <TabsTrigger className="justify-start" key={module.value} value={module.value}>
                  {module.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </CardContent>
        </Card>
        <div className="grid gap-2">
          {activeModule === "alerts" ? (
          <SettingsCard title="邮件告警" description="SMTP、飞书投递和告警规则。" status={snapshot.alerts.smtp_ready}>
            <SettingsSubsection title="发送设置">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <ReadonlyField label="投递通道" value={snapshot.alerts.smtp_ready ? "SMTP" : "未就绪"} />
                <ReadonlyField label="当前飞书 Webhook" value={maskWebhookUrl(alertSettings.feishu_webhook_url)} />
                <FormField label="飞书机器人 URL">
                  <Input placeholder="输入新 Webhook 后替换已保存地址" value={alertForm.feishu_webhook_url} onChange={(event) => setAlertForm((form) => ({ ...form, feishu_webhook_url: event.target.value }))} />
                </FormField>
                <FormField label="收件人">
                  <Textarea value={alertForm.recipients} onChange={(event) => setAlertForm((form) => ({ ...form, recipients: event.target.value }))} />
                </FormField>
                <FormField label="容量增长百分比阈值">
                  <Input min={1} type="number" value={alertForm.database_capacity_percent_threshold} onChange={(event) => setAlertForm((form) => ({ ...form, database_capacity_percent_threshold: event.target.value }))} />
                </FormField>
                <FormField label="容量增长绝对阈值">
                  <Input min={1} type="number" value={alertForm.database_capacity_absolute_gb_threshold} onChange={(event) => setAlertForm((form) => ({ ...form, database_capacity_absolute_gb_threshold: event.target.value }))} />
                </FormField>
              </div>
              <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <SwitchField checked={alertForm.global_enabled} label="启用邮件告警" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, global_enabled: checked }))} />
                <SwitchField checked={alertForm.feishu_enabled} label="发送到飞书" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, feishu_enabled: checked }))} />
                <SwitchField checked={alertForm.shared_recipients_enabled} label="共享收件人列表" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, shared_recipients_enabled: checked }))} />
                <CheckboxLine checked={alertForm.clear_feishu_webhook_url} label="清空飞书 Webhook" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, clear_feishu_webhook_url: checked }))}>
                  清空飞书 Webhook
                </CheckboxLine>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void runAction(sendAlertTestEmail(textList(alertForm.recipients)), { success: "测试邮件已发送" })} size="sm" type="button">
                  发送测试邮件
                </Button>
                <Button onClick={() => void runAction(sendFeishuTest(alertForm.feishu_webhook_url.trim()), { success: "飞书测试已发送" })} size="sm" type="button" variant="outline">
                  发送飞书测试
                </Button>
                <Button onClick={() => void runAction(saveAlertSettings(alertSettingsPayload(alertForm)), { success: "告警设置已保存" }).then(onRefresh)} size="sm" type="button">
                  保存配置
                </Button>
              </div>
            </SettingsSubsection>
            <SettingsSubsection title="规则设置">
              <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                {[
                  ["database_capacity_enabled", "容量异常增长"],
                  ["account_sync_failure_enabled", "账户同步异常"],
                  ["database_sync_failure_enabled", "数据库同步异常"],
                  ["cluster_status_enabled", "群集状态"],
                  ["privileged_account_enabled", "高权限账户"],
                  ["backup_issue_enabled", "备份告警"]
                ].map(([key, label]) => (
                  <SwitchField
                    checked={Boolean(alertForm[key as keyof AlertSettingsFormState])}
                    key={key}
                    label={label}
                    onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, [key]: checked }))}
                  />
                ))}
              </div>
            </SettingsSubsection>
          </SettingsCard>
          ) : null}

          {activeModule === "risk" ? (
          <SettingsCard title="风险规则" description="仅影响风险中心展示。" status={riskRules.some((rule) => rule.enabled)}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm text-muted-foreground">仅影响风险中心展示</span>
              <Button onClick={() => void runAction(saveRiskRules(riskRules), { success: "风险规则已保存" }).then(onRefresh)} size="sm" type="button">
                保存规则
              </Button>
            </div>
            {riskRules.length > 0 ? (
              riskRules.map((rule, index) => {
                const sourceRule = recordList(snapshot.riskRules).find((item) => asText(item.rule_key, "") === rule.rule_key) ?? {};
                return (
                <div className="grid grid-cols-[minmax(0,1fr)_18rem_8rem] items-center gap-3 rounded-md border bg-secondary/40 px-3 py-2 max-lg:grid-cols-1" key={rule.rule_key}>
                  <div className="grid gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{asText(sourceRule.category, "未分类")}</Badge>
                      <span className="font-medium">{asText(sourceRule.display_name ?? sourceRule.name, rule.rule_key)}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">{asText(sourceRule.description, rule.rule_key)}</div>
                  </div>
                  <div className="grid gap-1">
                    <span className="text-xs font-medium text-muted-foreground">严重级别</span>
                    <RadioGroup
                      className="grid grid-cols-3 gap-2"
                      onValueChange={(severity) => setRiskRules((items) => items.map((item, itemIndex) => (itemIndex === index ? { ...item, severity } : item)))}
                      value={rule.severity}
                    >
                      {severityOptions.map((option) => (
                        <label className="flex items-center gap-2 rounded-md border bg-background px-2 py-1.5 text-sm" key={option.value}>
                          <RadioGroupItem value={option.value} />
                          <span>{option.label}</span>
                        </label>
                      ))}
                    </RadioGroup>
                  </div>
                  <SwitchField
                    checked={rule.enabled}
                    label="启用规则"
                    onCheckedChange={(enabled) => setRiskRules((items) => items.map((item, itemIndex) => (itemIndex === index ? { ...item, enabled } : item)))}
                  />
                </div>
                );
              })
            ) : (
              <p className="text-muted-foreground">暂无风险规则</p>
            )}
          </SettingsCard>
          ) : null}

          {activeModule === "jumpserver" ? (
          <SettingsCard title="JumpServer 数据源设置" description="绑定资产数据源、API 凭据和运行状态。" status={Boolean(snapshot.jumpserver.provider_ready)}>
            <SettingsSubsection title="绑定配置">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <FormField label="API 凭据">
                  <SelectControl
                    label="API 凭据"
                    onValueChange={(credentialId) => setJumpServerForm((form) => ({ ...form, credentialId }))}
                    options={credentialOptions(jumpserverCredentials, jumpServerForm.credentialId, "请选择 API 凭据")}
                    value={jumpServerForm.credentialId}
                  />
                </FormField>
                <FormField label="JumpServer URL">
                  <Input value={jumpServerForm.baseUrl} onChange={(event) => setJumpServerForm((form) => ({ ...form, baseUrl: event.target.value }))} />
                </FormField>
                <FormField label="组织 ID">
                  <Input value={jumpServerForm.orgId} onChange={(event) => setJumpServerForm((form) => ({ ...form, orgId: event.target.value }))} />
                </FormField>
                <ReadonlyField label="当前 API 凭据" value={recordName(jumpserverBinding.credential, jumpServerForm.credentialId ? `凭据 #${jumpServerForm.credentialId}` : "-")} />
              </div>
              <SwitchField checked={jumpServerForm.verifySsl} label="SSL 证书验证" onCheckedChange={(checked) => setJumpServerForm((form) => ({ ...form, verifySsl: checked }))} />
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={jumpServerPayload === null}
                  onClick={() => {
                    if (jumpServerPayload !== null) {
                      void runAction(saveJumpServerSource(jumpServerPayload), { success: "JumpServer 数据源已保存" }).then(onRefresh);
                    }
                  }}
                  size="sm"
                  type="button"
                >
                  保存绑定
                </Button>
                <Button onClick={() => void runAction(unbindJumpServer(), { success: "JumpServer 已解绑" }).then(onRefresh)} size="sm" type="button" variant="outline">
                  解绑数据源
                </Button>
                <Button onClick={() => void runAction(syncJumpServer(), { success: "JumpServer 同步已触发" }).then(onRefresh)} size="sm" type="button">
                  同步 JumpServer 资源
                </Button>
              </div>
            </SettingsSubsection>
            <SettingsSubsection title="运行状态">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <ReadonlyField label="Provider" value={statusLabel(Boolean(snapshot.jumpserver.provider_ready))} />
                <ReadonlyField label="当前绑定" value={endpointHost(jumpServerForm.baseUrl)} />
                <ReadonlyField label="最近同步状态" value={asText(jumpserverBinding.last_sync_status ?? snapshot.jumpserver.last_sync_status)} />
                <ReadonlyField label="最近同步" value={asText(jumpserverBinding.last_sync_at ?? snapshot.jumpserver.last_sync_at)} />
              </div>
              <span className="font-mono text-sm">{endpointHost(jumpServerForm.baseUrl)}</span>
            </SettingsSubsection>
          </SettingsCard>
          ) : null}

          {activeModule === "veeam" ? (
          <SettingsCard title="Veeam 数据源设置" description="备份平台数据源配置。" status={Boolean(snapshot.veeam.provider_ready)}>
            <SettingsSubsection title="新增数据源">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <FormField label="数据源名称">
                  <Input value={veeamForm.name} onChange={(event) => setVeeamForm((form) => ({ ...form, name: event.target.value }))} />
                </FormField>
                <FormField label="Veeam 凭据">
                  <SelectControl
                    label="Veeam 凭据"
                    onValueChange={(credentialId) => setVeeamForm((form) => ({ ...form, credentialId }))}
                    options={credentialOptions(veeamCredentials, veeamForm.credentialId, "请选择 Veeam 凭据")}
                    value={veeamForm.credentialId}
                  />
                </FormField>
                <ReadonlyField label="当前 Veeam 凭据" value={recordName(selectedVeeamSource?.credential, veeamForm.credentialId ? `凭据 #${veeamForm.credentialId}` : "-")} />
                <FormField label="Veeam IP">
                  <Input value={veeamForm.serverHost} onChange={(event) => setVeeamForm((form) => ({ ...form, serverHost: event.target.value }))} />
                </FormField>
                <FormField label="端口">
                  <Input min={1} type="number" value={veeamForm.serverPort} onChange={(event) => setVeeamForm((form) => ({ ...form, serverPort: event.target.value }))} />
                </FormField>
                <FormField label="API 版本">
                  <Input value={veeamForm.apiVersion} onChange={(event) => setVeeamForm((form) => ({ ...form, apiVersion: event.target.value }))} />
                </FormField>
                <FormField label="域名列表">
                  <Textarea value={veeamForm.domains} onChange={(event) => setVeeamForm((form) => ({ ...form, domains: event.target.value }))} />
                </FormField>
                <ReadonlyField label="启用状态" value={statusLabel(selectedVeeamSource?.is_active !== false)} />
                <ReadonlyField label="最近同步" value={selectedVeeamSource?.last_sync_at} />
                <ReadonlyField label="最近同步状态" value={selectedVeeamSource?.last_sync_status} />
              </div>
              <SwitchField checked={veeamForm.verifySsl} label="SSL 证书验证" onCheckedChange={(checked) => setVeeamForm((form) => ({ ...form, verifySsl: checked }))} />
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={veeamPayload === null}
                  onClick={() => {
                    if (veeamPayload === null) {
                      return;
                    }
                    const request = selectedVeeamSourceId === null ? createVeeamSource(veeamPayload) : updateVeeamSource(selectedVeeamSourceId, veeamPayload);
                    void runAction(request, { success: selectedVeeamSourceId === null ? "Veeam 数据源已创建" : "Veeam 数据源已更新" }).then(onRefresh);
                  }}
                  size="sm"
                  type="button"
                >
                  保存数据源
                </Button>
                {selectedVeeamSourceId !== null ? (
                  <Button
                    onClick={() => {
                      const action = selectedVeeamSource?.is_active === false ? enableVeeamSource : disableVeeamSource;
                      void runAction(action(selectedVeeamSourceId), { success: selectedVeeamSource?.is_active === false ? "Veeam 数据源已启用" : "Veeam 数据源已停用" }).then(onRefresh);
                    }}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    {selectedVeeamSource?.is_active === false ? "启用数据源" : "停用数据源"}
                  </Button>
                ) : null}
                <Button disabled={selectedVeeamSourceId === null} onClick={() => selectedVeeamSourceId !== null && void runAction(deleteVeeamSource(selectedVeeamSourceId), { success: "Veeam 数据源已删除" }).then(onRefresh)} size="sm" type="button" variant="outline">
                  删除数据源
                </Button>
                <Button onClick={resetVeeamForm} size="sm" type="button" variant="outline">
                  新增模式
                </Button>
                <Button onClick={() => void runAction(syncVeeam(), { success: "Veeam 同步已触发" }).then(onRefresh)} size="sm" type="button">
                  同步 Veeam 备份
                </Button>
              </div>
            </SettingsSubsection>
            <SettingsSubsection title="Provider 汇总">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <ReadonlyField label="Provider" value={statusLabel(Boolean(snapshot.veeam.provider_ready))} />
                <ReadonlyField label="数据源数量" value={veeamSources.length} />
                <ReadonlyField label="凭据数量" value={veeamCredentials.length} />
              </div>
            </SettingsSubsection>
            <SettingsSubsection title="数据源列表">
              {veeamSources.length > 0 ? (
                veeamSources.map((source) => (
                  <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 max-sm:grid" key={asText(source.id ?? source.name)}>
                    <div>
                      <div className="font-medium">{asText(source.name)}</div>
                      <div className="font-mono text-xs text-muted-foreground">
                        {asText(source.server_host)}:{asText(source.server_port)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {recordName(source.credential)} · {statusLabel(source.is_active !== false)} · {asText(source.last_sync_status)}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Button onClick={() => editVeeamSource(source)} size="sm" type="button" variant="outline">
                        编辑数据源 {asText(source.name)}
                      </Button>
                      <Button
                        onClick={() => {
                          const sourceId = numericId(source.id);
                          if (sourceId !== null) {
                            const action = source.is_active === false ? enableVeeamSource : disableVeeamSource;
                            void runAction(action(sourceId), { success: source.is_active === false ? "Veeam 数据源已启用" : "Veeam 数据源已停用" }).then(onRefresh);
                          }
                        }}
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        {source.is_active === false ? "启用" : "停用"}
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">暂无 Veeam 数据源</p>
              )}
            </SettingsSubsection>
          </SettingsCard>
          ) : null}

          {activeModule === "ad" ? (
          <SettingsCard title="AD 设置" description="AD 域账户同步配置。" status={adDomainConfigs.some((item) => item.is_enabled === true)}>
            <SettingsSubsection title="新增 AD 域">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <FormField label="域名">
                  <Input value={adDomainForm.name} onChange={(event) => setAdDomainForm((form) => ({ ...form, name: event.target.value }))} />
                </FormField>
                <FormField label="NetBIOS 名称">
                  <Input value={adDomainForm.netbiosName} onChange={(event) => setAdDomainForm((form) => ({ ...form, netbiosName: event.target.value }))} />
                </FormField>
                <FormField label="LDAP 端口">
                  <Input min={1} type="number" value={adDomainForm.ldapPort} onChange={(event) => setAdDomainForm((form) => ({ ...form, ldapPort: event.target.value }))} />
                </FormField>
                <FormField label="域控地址">
                  <Textarea value={adDomainForm.domainControllers} onChange={(event) => setAdDomainForm((form) => ({ ...form, domainControllers: event.target.value }))} />
                </FormField>
                <FormField label="Base DN">
                  <Input value={adDomainForm.baseDn} onChange={(event) => setAdDomainForm((form) => ({ ...form, baseDn: event.target.value }))} />
                </FormField>
                <FormField label="LDAP 凭据">
                  <SelectControl
                    label="LDAP 凭据"
                    onValueChange={(credentialId) => setAdDomainForm((form) => ({ ...form, credentialId }))}
                    options={credentialOptions(adCredentials, adDomainForm.credentialId, "请选择 LDAP 凭据")}
                    value={adDomainForm.credentialId}
                  />
                </FormField>
              </div>
              <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <SwitchField checked={adDomainForm.useSsl} label="使用 SSL" onCheckedChange={(checked) => setAdDomainForm((form) => ({ ...form, useSsl: checked }))} />
                <FormField label="证书验证">
                  <SelectControl
                    label="证书验证"
                    onValueChange={(verifySsl) => setAdDomainForm((form) => ({ ...form, verifySsl }))}
                    options={[
                      { label: "继承默认", value: "" },
                      { label: "启用", value: "true" },
                      { label: "关闭", value: "false" }
                    ]}
                    value={adDomainForm.verifySsl}
                  />
                </FormField>
                <SwitchField checked={adDomainForm.isEnabled} label="启用同步" onCheckedChange={(checked) => setAdDomainForm((form) => ({ ...form, isEnabled: checked }))} />
              </div>
              <FormField label="描述">
                <Textarea value={adDomainForm.description} onChange={(event) => setAdDomainForm((form) => ({ ...form, description: event.target.value }))} />
              </FormField>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={adPayload === null}
                  onClick={() => {
                    if (adPayload === null) {
                      return;
                    }
                    const request = selectedAdDomainId === null ? createAdDomainConfig(adPayload) : updateAdDomainConfig(selectedAdDomainId, adPayload);
                    void runAction(request, { success: selectedAdDomainId === null ? "AD 域已创建" : "AD 域已更新" }).then(onRefresh);
                  }}
                  size="sm"
                  type="button"
                >
                  保存 AD 域
                </Button>
                {selectedAdDomainId !== null ? (
                  <>
                    <Button
                      onClick={() => void runAction(setAdDomainConfigEnabled(selectedAdDomainId, selectedAdDomain?.is_enabled !== true), { success: selectedAdDomain?.is_enabled === true ? "AD 域已停用" : "AD 域已启用" }).then(onRefresh)}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      {selectedAdDomain?.is_enabled === true ? "停用 AD 域" : "启用 AD 域"}
                    </Button>
                    <Button onClick={() => void runAction(testAdDomainConfig(selectedAdDomainId), { success: "AD 连接测试已完成" })} size="sm" type="button" variant="outline">
                      测试 AD 连接
                    </Button>
                  </>
                ) : null}
                <Button disabled={selectedAdDomainId === null} onClick={() => selectedAdDomainId !== null && void runAction(deleteAdDomainConfig(selectedAdDomainId), { success: "AD 域配置已删除" }).then(onRefresh)} size="sm" type="button" variant="outline">
                  删除配置
                </Button>
                <Button onClick={resetAdDomainForm} size="sm" type="button" variant="outline">
                  新增模式
                </Button>
                <Button onClick={() => void runAction(syncAdDomains(), { success: "AD 域账户同步已触发" }).then(onRefresh)} size="sm" type="button">
                  AD 域账户同步
                </Button>
              </div>
            </SettingsSubsection>
            <SettingsSubsection title="AD 域列表">
              {adDomainConfigs.length > 0 ? (
                adDomainConfigs.map((config) => (
                  <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 max-sm:grid" key={asText(config.id ?? config.name)}>
                    <div>
                  <div className="font-medium">{asText(config.name)}</div>
                  <div className="font-mono text-xs text-muted-foreground">{asText(config.netbios_name)}</div>
                  <div className="text-xs text-muted-foreground">
                    域控 {textList(config.domain_controllers).join(", ") || "-"} · 凭据 {recordName(config.credential, numericValue(config.credential_id, 0) > 0 ? `凭据 #${numericValue(config.credential_id, 0)}` : "-")}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    同步状态 {asText(config.last_sync_status, "未执行")} · {asText(config.last_sync_at)}
                  </div>
                  <div className="text-xs text-muted-foreground">{adSyncMetricsText(config.last_sync_metrics)}</div>
                </div>
                    <div className="flex flex-wrap items-center gap-1">
                      <StatusBadge value={config.is_enabled === true} />
                      <Button onClick={() => editAdDomain(config)} size="sm" type="button" variant="outline">
                        编辑AD域 {asText(config.name)}
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">暂无 AD 域配置</p>
              )}
            </SettingsSubsection>
          </SettingsCard>
          ) : null}
        </div>
      </Tabs>
    </>
  );
}

export function SettingsPage() {
  const query = useQuery({ queryKey: ["read-only", "settings"], queryFn: () => fetchSettingsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="System integrations" title="系统设置" description="迁移旧版系统设置模块，保留告警、风险规则、JumpServer、Veeam 和 AD 配置能力。" legacyHref="/admin/system-settings" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="系统设置" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const editorKey = settingsSnapshotKey(snapshot);
          if (editorKey) {
            return <SettingsEditor key={editorKey} snapshot={snapshot} onRefresh={() => void query.refetch()} />;
          }
          const alertSettings = snapshot.alerts.settings ?? {};
          const veeamSources = Array.isArray(snapshot.veeam.sources) ? snapshot.veeam.sources : [];
          const jumpserverBinding = (snapshot.jumpserver.binding as Record<string, unknown> | undefined) ?? {};
          const jumpserverCredentials = Array.isArray(snapshot.jumpserver.api_credentials) ? snapshot.jumpserver.api_credentials : [];
          const veeamCredentials = Array.isArray(snapshot.veeam.veeam_credentials) ? snapshot.veeam.veeam_credentials : [];
          const firstVeeamSource = (veeamSources[0] as Record<string, unknown> | undefined) ?? {};
          const firstAdDomain = snapshot.adDomains.configs[0] ?? {};
          const adControllers = Array.isArray(firstAdDomain.domain_controllers) ? firstAdDomain.domain_controllers.join(", ") : firstAdDomain.domain_controllers;
          const jumpServerPayload = jumpServerSourcePayload(jumpserverBinding, jumpserverCredentials);
          const firstVeeamSourceId = numericId(firstVeeamSource.id);
          const firstVeeamPayload = veeamSourcePayload(firstVeeamSource, veeamCredentials);
          const firstAdDomainId = numericId(firstAdDomain.id);
          const firstAdDomainPayload = adDomainPayload(firstAdDomain);
          return (
            <>
              <MetricGrid
                label="系统设置指标"
                metrics={[
                  { label: "启用配置", value: settingsEnabledCount(snapshot), icon: Settings },
                  { label: "风险规则", value: snapshot.riskRules.length, icon: AlertCircle },
                  { label: "AD 域", value: snapshot.adDomains.configs.length, icon: UserCog },
                  { label: "Veeam 源", value: veeamSources.length, icon: Database }
                ]}
              />
              <section className="grid grid-cols-[16rem_minmax(0,1fr)] gap-2 max-xl:grid-cols-1">
                <Card className="self-start">
                  <CardHeader>
                    <CardTitle>设置模块</CardTitle>
                    <CardDescription>旧版模块导航</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-2">
                    {["告警设置", "风险规则", "JumpServer", "Veeam", "AD 设置"].map((label) => (
                      <Button className="justify-start" key={label} type="button" variant="ghost">
                        {label}
                      </Button>
                    ))}
                  </CardContent>
                </Card>
                <div className="grid gap-2">
                  <SettingsCard title="邮件告警" description="SMTP、飞书投递和告警规则。" status={snapshot.alerts.smtp_ready}>
                    <SettingsSubsection title="发送设置">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="投递通道" value={snapshot.alerts.smtp_ready ? "SMTP" : "未就绪"} />
                        <ReadonlyField label="飞书机器人 URL" value={alertSettings.feishu_webhook_url} />
                        <ReadonlyField label="收件人" value={alertSettings.recipients} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="启用邮件告警" checked={alertSettings.global_enabled} />
                        <ToggleRow label="发送到飞书" checked={alertSettings.feishu_enabled} />
                        <ToggleRow label="共享收件人列表" checked={alertSettings.shared_recipients_enabled} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={() => {
                            void runAction(sendAlertTestEmail(settingsRecipients(snapshot.alerts)), { success: "测试邮件已发送" });
                          }}
                          size="sm"
                          type="button"
                        >
                          发送测试邮件
                        </Button>
                        <Button
                          onClick={() => {
                            void runAction(sendFeishuTest(asText(alertSettings.feishu_webhook_url, "")), { success: "飞书测试已发送" });
                          }}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          发送飞书测试
                        </Button>
                        <Button
                          onClick={() => {
                            void runAction(saveAlertSettings(alertSettings), { success: "告警设置已保存" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          保存配置
                        </Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="规则设置">
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="容量异常增长" checked={alertSettings.database_capacity_enabled} />
                        <ToggleRow label="账户同步异常" checked={alertSettings.account_sync_failure_enabled} />
                        <ToggleRow label="数据库同步异常" checked={alertSettings.database_sync_failure_enabled} />
                        <ToggleRow label="群集状态" checked={alertSettings.cluster_status_enabled} />
                        <ToggleRow label="高权限账户" checked={alertSettings.privileged_account_enabled} />
                        <ToggleRow label="备份告警" checked={alertSettings.backup_issue_enabled} />
                      </div>
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="风险规则" description="仅影响风险中心展示。" status={snapshot.riskRules.some((rule) => rule.enabled === true)}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm text-muted-foreground">仅影响风险中心展示</span>
                      <Button
                        onClick={() => {
                          void runAction(saveRiskRules(riskRulePayload(snapshot.riskRules)), { success: "风险规则已保存" }).then(() => query.refetch());
                        }}
                        size="sm"
                        type="button"
                      >
                        保存规则
                      </Button>
                    </div>
                    {snapshot.riskRules.length > 0 ? (
                      snapshot.riskRules.map((rule) => (
                        <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(rule.rule_key)}>
                          <span>{asText(rule.rule_key)}</span>
                          <Badge variant={statusVariant(Boolean(rule.enabled))}>{asText(rule.severity, statusLabel(Boolean(rule.enabled)))}</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-muted-foreground">暂无风险规则</p>
                    )}
                  </SettingsCard>

                  <SettingsCard title="JumpServer 数据源设置" description="绑定资产数据源、API 凭据和运行状态。" status={Boolean(snapshot.jumpserver.provider_ready)}>
                    <SettingsSubsection title="绑定配置">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="JumpServer URL" value={endpointHost(jumpserverBinding.base_url)} />
                        <ReadonlyField label="组织 ID" value={jumpserverBinding.org_id} />
                        <ReadonlyField label="SSL 证书验证" value={statusLabel(jumpserverBinding.verify_ssl as boolean | undefined)} />
                      </div>
                      <span className="font-mono text-sm">{endpointHost(jumpserverBinding.base_url)}</span>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          disabled={jumpServerPayload === null}
                          onClick={() => {
                            if (jumpServerPayload !== null) {
                              void runAction(saveJumpServerSource(jumpServerPayload), { success: "JumpServer 数据源已保存" }).then(() => query.refetch());
                            }
                          }}
                          size="sm"
                          type="button"
                        >
                          保存绑定
                        </Button>
                        <Button
                          onClick={() => {
                            void runAction(unbindJumpServer(), { success: "JumpServer 已解绑" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          解绑数据源
                        </Button>
                        <Button
                          onClick={() => {
                            void runAction(syncJumpServer(), { success: "JumpServer 同步已触发" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          同步 JumpServer 资源
                        </Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="API 凭据">
                      <p className="text-sm text-muted-foreground">{jumpserverCredentials.length > 0 ? `${formatNumber(jumpserverCredentials.length)} 条凭据` : "暂无 API 凭据"}</p>
                    </SettingsSubsection>
                    <SettingsSubsection title="运行状态">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="Provider" value={statusLabel(Boolean(snapshot.jumpserver.provider_ready))} />
                        <ReadonlyField label="当前绑定" value={endpointHost(jumpserverBinding.base_url)} />
                        <ReadonlyField label="最近同步" value={snapshot.jumpserver.last_sync_at} />
                      </div>
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="Veeam 数据源设置" description="备份平台数据源配置。" status={Boolean(snapshot.veeam.provider_ready)}>
                    <SettingsSubsection title="新增数据源">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="数据源名称" value={firstVeeamSource.name} />
                        <ReadonlyField label="Veeam 凭据" value={veeamCredentials.length > 0 ? `${formatNumber(veeamCredentials.length)} 条` : "-"} />
                        <ReadonlyField label="Veeam IP" value={firstVeeamSource.server_host} />
                        <ReadonlyField label="端口" value={firstVeeamSource.server_port} />
                        <ReadonlyField label="API 版本" value={firstVeeamSource.api_version} />
                        <ReadonlyField label="域名列表" value={firstVeeamSource.domains} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          disabled={firstVeeamPayload === null}
                          onClick={() => {
                            if (firstVeeamPayload === null) {
                              return;
                            }
                            if (firstVeeamSourceId !== null) {
                              void runAction(updateVeeamSource(firstVeeamSourceId, firstVeeamPayload), { success: "Veeam 数据源已更新" }).then(() => query.refetch());
                              return;
                            }
                            void runAction(createVeeamSource(firstVeeamPayload), { success: "Veeam 数据源已创建" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          保存数据源
                        </Button>
                        {firstVeeamSourceId !== null ? (
                          <Button
                            onClick={() => {
                              const action = firstVeeamSource.is_active === false ? enableVeeamSource : disableVeeamSource;
                              void runAction(action(firstVeeamSourceId), { success: firstVeeamSource.is_active === false ? "Veeam 数据源已启用" : "Veeam 数据源已停用" }).then(() => query.refetch());
                            }}
                            size="sm"
                            type="button"
                            variant="outline"
                          >
                            {firstVeeamSource.is_active === false ? "启用数据源" : "停用数据源"}
                          </Button>
                        ) : null}
                        <Button
                          onClick={() => {
                            if (firstVeeamSourceId !== null) {
                              void runAction(deleteVeeamSource(firstVeeamSourceId), { success: "Veeam 数据源已删除" }).then(() => query.refetch());
                            }
                          }}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          删除数据源
                        </Button>
                        <Badge variant="outline">新增模式</Badge>
                        <Button
                          onClick={() => {
                            void runAction(syncVeeam(), { success: "Veeam 同步已触发" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          同步 Veeam 备份
                        </Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="数据源列表">
                      {veeamSources.length > 0 ? (
                        veeamSources.map((source) => {
                          const record = source as Record<string, unknown>;
                          return (
                            <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(record.name ?? record.id)}>
                              <span>{asText(record.name)}</span>
                              <span className="font-mono text-xs text-muted-foreground">{asText(record.server_host)}:{asText(record.server_port)}</span>
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-muted-foreground">暂无 Veeam 数据源</p>
                      )}
                    </SettingsSubsection>
                  </SettingsCard>

                  <SettingsCard title="AD 设置" description="AD 域账户同步配置。" status={snapshot.adDomains.configs.some((item) => item.is_enabled === true)}>
                    <SettingsSubsection title="新增 AD 域">
                      <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ReadonlyField label="域名" value={firstAdDomain.name} />
                        <ReadonlyField label="NetBIOS 名称" value={firstAdDomain.netbios_name} />
                        <ReadonlyField label="LDAP 端口" value={firstAdDomain.ldap_port} />
                        <ReadonlyField label="域控地址" value={adControllers} />
                        <ReadonlyField label="Base DN" value={firstAdDomain.base_dn} />
                        <ReadonlyField label="LDAP 凭据" value={firstAdDomain.credential_id} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="使用 SSL" checked={firstAdDomain.use_ssl ?? firstAdDomain.ldap_port === 636} />
                        <ToggleRow label="证书验证" checked={firstAdDomain.verify_ssl} />
                        <ToggleRow label="启用同步" checked={firstAdDomain.is_enabled} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          disabled={firstAdDomainPayload === null}
                          onClick={() => {
                            if (firstAdDomainPayload === null) {
                              return;
                            }
                            if (firstAdDomainId !== null) {
                              void runAction(updateAdDomainConfig(firstAdDomainId, firstAdDomainPayload), { success: "AD 域已更新" }).then(() => query.refetch());
                              return;
                            }
                            void runAction(createAdDomainConfig(firstAdDomainPayload), { success: "AD 域已创建" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          保存 AD 域
                        </Button>
                        {firstAdDomainId !== null ? (
                          <>
                            <Button
                              onClick={() => {
                                void runAction(setAdDomainConfigEnabled(firstAdDomainId, firstAdDomain.is_enabled !== true), { success: firstAdDomain.is_enabled === true ? "AD 域已停用" : "AD 域已启用" }).then(() => query.refetch());
                              }}
                              size="sm"
                              type="button"
                              variant="outline"
                            >
                              {firstAdDomain.is_enabled === true ? "停用 AD 域" : "启用 AD 域"}
                            </Button>
                            <Button
                              onClick={() => {
                                void runAction(testAdDomainConfig(firstAdDomainId), { success: "AD 连接测试已完成" });
                              }}
                              size="sm"
                              type="button"
                              variant="outline"
                            >
                              测试 AD 连接
                            </Button>
                          </>
                        ) : null}
                        <Button
                          onClick={() => {
                            if (firstAdDomainId !== null) {
                              void runAction(deleteAdDomainConfig(firstAdDomainId), { success: "AD 域配置已删除" }).then(() => query.refetch());
                            }
                          }}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          删除配置
                        </Button>
                        <Button
                          onClick={() => {
                            void runAction(syncAdDomains(), { success: "AD 域账户同步已触发" }).then(() => query.refetch());
                          }}
                          size="sm"
                          type="button"
                        >
                          AD 域账户同步
                        </Button>
                      </div>
                    </SettingsSubsection>
                    <SettingsSubsection title="AD 域列表">
                      {snapshot.adDomains.configs.length > 0 ? (
                        snapshot.adDomains.configs.map((config) => (
                          <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2" key={asText(config.id ?? config.name)}>
                            <span>{asText(config.name)}</span>
                            <StatusBadge value={config.is_enabled === true} />
                          </div>
                        ))
                      ) : (
                        <p className="text-muted-foreground">暂无 AD 域配置</p>
                      )}
                    </SettingsSubsection>
                  </SettingsCard>
                </div>
              </section>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}

export function CredentialsPage({ currentUser }: { currentUser?: AccessUser | null } = {}) {
  const tableState = useServerTableState({ initialFilters: { credentialType: "", dbType: "", status: "" } });
  const listQuery = { page: tableState.page, limit: tableState.pageSize, search: tableState.search, credentialType: tableState.filters.credentialType, dbType: tableState.filters.dbType, status: tableState.filters.status };
  const query = useQuery({ queryKey: ["read-only", "credentials", listQuery], queryFn: () => fetchCredentialsSnapshot(listQuery), placeholderData: (previous) => previous });
  const [creatingCredential, setCreatingCredential] = useState(false);
  const [editingCredential, setEditingCredential] = useState<CredentialItem | null>(null);
  const [deletingCredential, setDeletingCredential] = useState<CredentialItem | null>(null);
  const canManage = canManageCatalog(currentUser);
  const columns = useMemo(
    () =>
      createCredentialColumns({
        canManage,
        onDelete: setDeletingCredential,
        onEdit: setEditingCredential
      }),
    [canManage]
  );

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Credential vault" title="凭据管理" description="展示凭据类型、数据库类型和引用数量，并支持新增、编辑、删除。" legacyHref="/credentials/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="凭据管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <ListPanel
              title="凭据列表"
              count={snapshot.total}
              actions={
                canManage ? (
                  <Button onClick={() => setCreatingCredential(true)} size="sm" type="button">
                    <Plus aria-hidden />
                    添加凭据
                  </Button>
                ) : (
                  <Badge variant="outline">只读</Badge>
                )
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.items}
                filters={[
                  { columnId: "credential_type", label: "凭据类型", options: [{ label: "数据库凭据", value: "database" }, { label: "API 凭据", value: "api" }, { label: "Veeam 凭据", value: "veeam" }, { label: "LDAP 凭据", value: "ldap" }, { label: "SSH 凭据", value: "ssh" }], value: tableState.filters.credentialType, onValueChange: (value) => tableState.setFilter("credentialType", value) },
                  { columnId: "db_type", label: "数据库类型", options: [{ label: "MySQL", value: "mysql" }, { label: "PostgreSQL", value: "postgresql" }, { label: "SQL Server", value: "sqlserver" }, { label: "Oracle", value: "oracle" }], value: tableState.filters.dbType, onValueChange: (value) => tableState.setFilter("dbType", value) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    value: tableState.filters.status,
                    onValueChange: (value) => tableState.setFilter("status", value),
                    options: [
                      { label: "启用", value: "active" },
                      { label: "停用", value: "inactive" }
                    ]
                  }
                ]}
                onSearchChange={tableState.setSearchInput}
                pagination={{ page: snapshot.page, pageSize: tableState.pageSize, pages: snapshot.pages ?? 1, total: snapshot.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
                searchPlaceholder="搜索凭据、账号或数据库类型"
                searchValue={tableState.searchInput}
              />
          </ListPanel>
        )}
      </QueryFrame>
      {canManage && creatingCredential ? (
        <CredentialFormDialog
          item={null}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingCredential(false);
            }
          }}
          onSaved={() => {
            setCreatingCredential(false);
            void query.refetch();
          }}
          open={creatingCredential}
        />
      ) : null}
      {canManage && editingCredential ? (
        <CredentialFormDialog
          item={editingCredential}
          onOpenChange={(open) => {
            if (!open) {
              setEditingCredential(null);
            }
          }}
          onSaved={() => {
            setEditingCredential(null);
            void query.refetch();
          }}
          open={editingCredential !== null}
        />
      ) : null}
      <DeleteConfirmDialog
        confirmLabel="确认删除凭据"
        description="删除凭据会影响后续使用该凭据的实例配置，请先确认引用关系。"
        onConfirm={() => {
          if (!deletingCredential) {
            return;
          }
          const credentialId = deletingCredential.id;
          setDeletingCredential(null);
          void runAction(deleteCredential(credentialId), { success: "凭据已删除" }).then(() => query.refetch());
        }}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingCredential(null);
          }
        }}
        open={canManage && deletingCredential !== null}
        title={`确认删除凭据 ${deletingCredential?.name ?? ""}`}
      />
    </main>
  );
}

export function TagsPage({ currentUser }: { currentUser?: AccessUser | null } = {}) {
  const tableState = useServerTableState({ initialFilters: { category: "", status: "" } });
  const listQuery = { page: tableState.page, limit: tableState.pageSize, search: tableState.search, category: tableState.filters.category, status: tableState.filters.status };
  const query = useQuery({ queryKey: ["read-only", "tags", listQuery], queryFn: () => fetchTagsSnapshot(listQuery), placeholderData: (previous) => previous });
  const [creatingTag, setCreatingTag] = useState(false);
  const [editingTag, setEditingTag] = useState<TagItem | null>(null);
  const [deletingTag, setDeletingTag] = useState<TagItem | null>(null);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const canManage = canManageCatalog(currentUser);
  const columns = useMemo(
    () =>
      createTagColumns({
        canManage,
        onDelete: setDeletingTag,
        onEdit: setEditingTag
      }),
    [canManage]
  );

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Resource tags" title="标签管理" description="展示标签、分类和实例引用数量，并支持新增、编辑、删除。" legacyHref="/tags/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="标签管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="标签指标"
              metrics={[
                {
                  label: "全部标签",
                  value: snapshot.list.stats.total,
                  detail: `均值/分类 ${formatNumber(snapshot.list.stats.category_count > 0 ? snapshot.list.stats.total / snapshot.list.stats.category_count : 0)}`,
                  icon: Tags
                },
                { label: "启用率", value: formatPercent(snapshot.list.stats.active, snapshot.list.stats.total), detail: `启用 ${formatNumber(snapshot.list.stats.active)}`, icon: Activity },
                { label: "停用率", value: formatPercent(snapshot.list.stats.inactive, snapshot.list.stats.total), detail: `停用 ${formatNumber(snapshot.list.stats.inactive)}`, icon: AlertCircle },
                {
                  label: "标签分类",
                  value: snapshot.list.stats.category_count,
                  detail: `启用/分类 ${formatNumber(snapshot.list.stats.category_count > 0 ? snapshot.list.stats.active / snapshot.list.stats.category_count : 0)}`,
                  icon: Boxes
                }
              ]}
            />
            <ListPanel
              title="标签列表"
              count={snapshot.list.total}
              actions={
                canManage ? (
                  <>
                    <Button onClick={() => setCreatingTag(true)} size="sm" type="button">
                      <Plus aria-hidden />
                      添加标签
                    </Button>
                    <Button onClick={() => setBulkDialogOpen(true)} size="sm" type="button" variant="outline">
                      批量分配
                    </Button>
                  </>
                ) : (
                  <Badge variant="outline">只读</Badge>
                )
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  { columnId: "category", label: "分类", options: snapshot.categories.map((category) => ({ label: category, value: category })), value: tableState.filters.category, onValueChange: (value) => tableState.setFilter("category", value) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    value: tableState.filters.status,
                    onValueChange: (value) => tableState.setFilter("status", value),
                    options: [
                      { label: "启用", value: "active" },
                      { label: "停用", value: "inactive" }
                    ]
                  }
                ]}
                onSearchChange={tableState.setSearchInput}
                pagination={{ page: snapshot.list.page, pageSize: tableState.pageSize, pages: snapshot.list.pages ?? 1, total: snapshot.list.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
                searchPlaceholder="搜索标签、编码或分类"
                searchValue={tableState.searchInput}
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
      {canManage && creatingTag ? (
        <TagFormDialog
          item={null}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingTag(false);
            }
          }}
          onSaved={() => {
            setCreatingTag(false);
            void query.refetch();
          }}
          open={creatingTag}
        />
      ) : null}
      {canManage && editingTag ? (
        <TagFormDialog
          item={editingTag}
          onOpenChange={(open) => {
            if (!open) {
              setEditingTag(null);
            }
          }}
          onSaved={() => {
            setEditingTag(null);
            void query.refetch();
          }}
          open={editingTag !== null}
        />
      ) : null}
      {canManage && bulkDialogOpen ? (
        <TagBulkDialog
          onOpenChange={setBulkDialogOpen}
          onSaved={() => {
            setBulkDialogOpen(false);
            void query.refetch();
          }}
          open={bulkDialogOpen}
        />
      ) : null}
      <DeleteConfirmDialog
        confirmLabel="确认删除标签"
        description="删除标签会解除与实例等资源的关联。"
        onConfirm={() => {
          if (!deletingTag) {
            return;
          }
          const tagId = deletingTag.id;
          setDeletingTag(null);
          void runAction(deleteTag(tagId), { success: "标签已删除" }).then(() => query.refetch());
        }}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingTag(null);
          }
        }}
        open={canManage && deletingTag !== null}
        title={`确认删除标签 ${deletingTag?.display_name ?? ""}`}
      />
    </main>
  );
}

const partitionColumns: ColumnDef<PartitionItem>[] = [
  { accessorKey: "display_name", header: "分区", cell: ({ row }) => <span className="font-medium">{partitionMonthLabel(row.original)}</span> },
  { accessorKey: "table", header: "表", cell: ({ row }) => row.original.table ?? "-" },
  { accessorKey: "table_type", header: "类型", cell: ({ row }) => row.original.table_type ?? "-" },
  { accessorKey: "size", header: "大小", cell: ({ row }) => <span className="font-mono text-xs">{row.original.size ?? "-"}</span> },
  { accessorKey: "record_count", header: "记录", cell: ({ row }) => <span className="font-mono text-xs">{formatNumber(row.original.record_count)}</span> },
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
  { label: "周", periodType: "weekly", days: 28 },
  { label: "月", periodType: "monthly", days: 90 },
  { label: "季", periodType: "quarterly", days: 365 }
];

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
  const chartConfig = { value: { label: "分区指标", color: "var(--chart-2)" } } satisfies ChartConfig;
  const [partitionYear, setPartitionYear] = useState("");
  const [partitionMonth, setPartitionMonth] = useState("");
  const [retentionMonths, setRetentionMonths] = useState("12");
  const [createOpen, setCreateOpen] = useState(false);
  const [cleanupOpen, setCleanupOpen] = useState(false);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Storage partitions" title="分区管理" description="展示分区健康状态、核心指标和分区列表，并支持创建分区与清理旧分区。" legacyHref="/partition/" />
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
          const metricValues = snapshot.coreMetrics.datasets[0]?.data ?? [];
          const chartData = snapshot.coreMetrics.labels.map((label, index) => ({ label, value: metricValues[index] ?? 0 }));
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
              <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
                <Card>
                  <CardHeader>
                    <div>
                      <CardTitle>核心指标趋势</CardTitle>
                      <CardDescription>最近7天的核心指标统计</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="grid gap-3">
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
                    {chartData.length > 0 ? (
                      <ChartContainer config={chartConfig} className="h-[220px] w-full">
                        <AreaChart accessibilityLayer data={chartData} margin={{ left: 8, right: 12, top: 12, bottom: 0 }}>
                          <CartesianGrid vertical={false} />
                          <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                          <YAxis tickLine={false} axisLine={false} tickMargin={8} width={60} />
                          <ChartTooltip content={<ChartTooltipContent />} />
                          <Area dataKey="value" name="分区指标" type="monotone" stroke="var(--color-value)" strokeWidth={2} fill="var(--color-value)" fillOpacity={0.16} />
                        </AreaChart>
                      </ChartContainer>
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
