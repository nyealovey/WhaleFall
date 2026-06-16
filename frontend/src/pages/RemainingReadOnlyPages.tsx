import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Activity,
  AlertCircle,
  Boxes,
  ChartColumn,
  Clock,
  Database,
  ExternalLink,
  KeyRound,
  Layers3,
  ListChecks,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Settings,
  Tags,
  Trash2,
  UserCog,
  Zap
} from "lucide-react";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { CheckboxLine, SelectControl, SwitchField } from "@/components/shared/FormControls";
import { runAction } from "@/utils/action-feedback";
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
  type SchedulerJobWritePayload,
  type SqlServerClusterPayload,
  type TagWritePayload,
  type UserWritePayload,
  type VeeamSourcePayload
} from "@/api/actions";
import {
  fetchAccountClassificationsSnapshot,
  fetchAccountClassificationPermissions,
  fetchAccountClassificationRuleDetail,
  fetchClassificationStatisticsSnapshot,
  fetchClustersSnapshot,
  fetchCredentialsSnapshot,
  fetchMySqlClusterDetail,
  fetchPartitionsSnapshot,
  fetchSchedulerSnapshot,
  fetchSettingsSnapshot,
  fetchSqlServerClusterDetail,
  fetchSyncSessionDetail,
  fetchSyncSessionErrorLogs,
  fetchSyncSessionsSnapshot,
  fetchTagBulkOptions,
  fetchTagsSnapshot,
  fetchUsersSnapshot,
  type AccountClassificationItem,
  type AccountClassificationRuleItem,
  type ClassificationStatisticsSnapshot,
  type ClusterDetailRecord,
  type ClusterItem,
  type CredentialItem,
  type MySqlClusterDetail,
  type PartitionItem,
  type SchedulerJobItem,
  type SettingsSnapshot,
  type SqlServerClusterDetail,
  type SyncInstanceRecordItem,
  type SyncSessionDetail,
  type SyncSessionErrorLogs,
  type SyncSessionItem,
  type TagBulkOptions,
  type TagItem,
  type TagOptionItem,
  type TaggableInstanceItem,
  type UserItem
} from "@/api/readOnly";
import { DataTable } from "@/components/shared/DataTable";

type Metric = {
  label: string;
  value: number | string;
  detail?: string;
  icon: typeof Layers3;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0%";
  }
  return `${Math.round((value / total) * 100)}%`;
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

function uniqueTextOptions<TItem>(items: TItem[], getValue: (item: TItem) => string | null | undefined) {
  const values = new Set<string>();
  for (const item of items) {
    const value = getValue(item);
    if (value) {
      values.add(value);
    }
  }
  return [...values].sort((first, second) => first.localeCompare(second, "zh-CN")).map((value) => ({ label: value, value }));
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

function triggerArgsEntries(value: unknown): string[] {
  if (!value) {
    return [];
  }
  if (typeof value === "string") {
    try {
      return triggerArgsEntries(JSON.parse(value) as unknown);
    } catch {
      return [value];
    }
  }
  if (typeof value !== "object") {
    return [String(value)];
  }
  return Object.entries(value as Record<string, unknown>)
    .filter(([key, entry]) => !["__proto__", "prototype", "constructor"].includes(key) && entry !== undefined && entry !== null && entry !== "")
    .map(([key, entry]) => (key === "description" ? String(entry) : `${key}: ${String(entry)}`));
}

function syncRunId(item: SyncSessionItem): string {
  return item.run_id ?? item.session_id;
}

function syncTaskName(item: SyncSessionItem): string {
  return item.task_name ?? item.task_key ?? item.sync_type;
}

function syncSource(item: SyncSessionItem): string {
  return item.trigger_source ?? item.sync_type;
}

function syncCategory(item: SyncSessionItem): string {
  return item.task_category ?? item.sync_category;
}

function syncProgress(item: SyncSessionItem) {
  const total = item.progress_total ?? item.total_instances ?? 0;
  const completed = item.progress_completed ?? item.successful_instances ?? 0;
  const failed = item.progress_failed ?? item.failed_instances ?? 0;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { total, completed, failed, percent };
}

function syncDuration(item: SyncSessionItem): string {
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
  description: string;
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
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
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
  onDelete,
  onEdit
}: {
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
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑凭据 ${row.original.name}`} onClick={() => onEdit(row.original)} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除凭据 ${row.original.name}`} onClick={() => onDelete(row.original)} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
  ];
}

function createTagColumns({
  onDelete,
  onEdit
}: {
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
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑标签 ${row.original.display_name}`} onClick={() => onEdit(row.original)} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除标签 ${row.original.display_name}`} onClick={() => onDelete(row.original)} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
  ];
}

function createUserColumns({
  onDelete,
  onEdit
}: {
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
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Button aria-label={`编辑用户 ${row.original.username}`} onClick={() => onEdit(row.original)} size="icon" type="button" variant="ghost">
          <Pencil aria-hidden />
        </Button>
        <Button aria-label={`删除用户 ${row.original.username}`} onClick={() => onDelete(row.original)} size="icon" type="button" variant="ghost">
          <Trash2 aria-hidden />
        </Button>
      </div>
    )
  }
  ];
}

function createSyncSessionColumns({
  onCancel,
  onViewDetail
}: {
  onCancel: (sessionId: string) => void;
  onViewDetail: (sessionId: string) => void;
}): ColumnDef<SyncSessionItem>[] {
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
          <span className="font-mono text-xs text-muted-foreground">{row.original.task_key ?? row.original.sync_type}</span>
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

function SchedulerJobCard({ job, onEdit }: { job: SchedulerJobItem; onEdit: (job: SchedulerJobItem) => void }) {
  const name = job.task_name ?? job.name ?? job.id;
  const triggerEntries = triggerArgsEntries(job.trigger_args);

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
            <dd className="font-mono text-xs">{job.next_run_time ?? "未计划"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">上次运行</dt>
            <dd className="font-mono text-xs">{job.last_run_time ?? "从未运行"}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">任务 ID</dt>
            <dd className="font-mono text-xs">{job.task_id ?? job.id}</dd>
          </div>
        </dl>
        <div className="grid gap-2">
          <span className="text-sm font-medium">触发器参数</span>
          <div className="flex min-h-8 flex-wrap gap-1">
            {triggerEntries.length > 0 ? triggerEntries.map((entry) => <Badge key={entry} variant="outline">{entry}</Badge>) : <span className="text-sm text-muted-foreground">-</span>}
          </div>
        </div>
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
          <Button aria-label={`编辑任务 ${name}`} onClick={() => onEdit(job)} size="icon" type="button" variant="outline">
            <Pencil aria-hidden />
          </Button>
          <Button aria-label={`删除任务 ${name}`} size="icon" type="button" variant="outline">
            <Trash2 aria-hidden />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SchedulerJobSection({
  jobs,
  onEdit,
  title
}: {
  jobs: SchedulerJobItem[];
  onEdit: (job: SchedulerJobItem) => void;
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
            <SchedulerJobCard job={job} key={job.id} onEdit={onEdit} />
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
  const abnormalCount = asNumber((item as Record<string, unknown>).ag_database_sync_abnormal_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return asText(item.last_ag_sync_status, "未同步");
}

function mysqlTopologySummary(item: ClusterItem): string {
  const abnormalCount = asNumber((item as Record<string, unknown>).abnormal_replica_count);
  if (abnormalCount > 0) {
    return `异常 ${formatNumber(abnormalCount)}`;
  }
  return asText(item.replication_status, "replication");
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
          <DialogDescription>维护群集基础信息。实例绑定和 AG 成员配置保留为后续独立表单迁移。</DialogDescription>
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

function SqlServerAvailabilityGroupsTable({ records }: { records: ClusterDetailRecord[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>AG</TableHead>
          <TableHead>监听器</TableHead>
          <TableHead>状态</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.length > 0 ? (
          records.map((record, index) => (
            <TableRow key={`${clusterRecordField(record, ["id", "name"], String(index))}-${index}`}>
              <TableCell className="font-medium">{clusterRecordField(record, ["name", "availability_group_name"])}</TableCell>
              <TableCell className="font-mono text-xs">
                {clusterRecordField(record, ["listener_name", "listener_host", "listener_dns_name"])}
              </TableCell>
              <TableCell>
                <StatusBadge value={clusterRecordField(record, ["sync_status", "health_status", "is_enabled"])} />
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
  onDetail,
  onEdit,
  onSyncAccounts
}: {
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
      cell: ({ row }) => <StatusBadge value={row.original.last_ag_sync_status ?? "未同步"} />
    },
    {
      accessorFn: sqlServerDatabaseSyncSummary,
      id: "ag_database_sync_abnormal_count",
      header: "数据库同步状态",
      cell: ({ row }) => <Badge variant="outline">{sqlServerDatabaseSyncSummary(row.original)}</Badge>
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
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
  onDetail,
  onEdit
}: {
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
      cell: ({ row }) => <Badge variant="outline">{mysqlTopologySummary(row.original)}</Badge>
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
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
  const query = useQuery({ queryKey: ["read-only", "clusters"], queryFn: () => fetchClustersSnapshot() });
  const [creatingCluster, setCreatingCluster] = useState<ClusterMode | null>(null);
  const [editingCluster, setEditingCluster] = useState<{ mode: ClusterMode; item: ClusterItem } | null>(null);
  const [viewingCluster, setViewingCluster] = useState<{ mode: ClusterMode; item: ClusterItem } | null>(null);
  const sqlServerClusterColumns = useMemo(
    () =>
      createSqlServerClusterColumns({
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
                  filters={[{ columnId: "is_enabled", label: "状态", options: uniqueTextOptions(snapshot.sqlServer.items, clusterEnabledLabel) }]}
                  searchPlaceholder="搜索群集名称或描述"
                />
              </ListPanel>
            </TabsContent>
            <TabsContent className="mt-0 grid gap-3" value="mysql">
              <ListPanel title="MySQL 群集" description="主从拓扑、绑定实例和复制状态。" count={snapshot.mySql.total}>
                <DataTable
                  columns={mysqlClusterColumns}
                  data={snapshot.mySql.items}
                  filters={[{ columnId: "is_enabled", label: "状态", options: uniqueTextOptions(snapshot.mySql.items, clusterEnabledLabel) }]}
                  searchPlaceholder="搜索群集名称或描述"
                />
              </ListPanel>
            </TabsContent>
          </Tabs>
        )}
      </QueryFrame>
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
  items,
  onDelete,
  onEdit
}: {
  items: AccountClassificationItem[];
  onDelete: (classificationId: number) => void;
  onEdit: (item: AccountClassificationItem) => void;
}) {
  if (items.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">暂无分类，点击“新建分类”开始配置</p>;
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
            <div className="flex items-center gap-1">
              <Button aria-label={`编辑分类 ${item.display_name}`} onClick={() => onEdit(item)} size="icon" type="button" variant="ghost">
                <Pencil aria-hidden />
              </Button>
              {!item.is_system ? (
                <Button aria-label={`删除分类 ${item.display_name}`} onClick={() => onDelete(item.id)} size="icon" type="button" variant="ghost">
                  <Trash2 aria-hidden />
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function RuleGroups({
  rulesByDbType,
  onDeleteRule,
  onEditRule,
  onViewRule
}: {
  rulesByDbType: Record<string, AccountClassificationRuleItem[]>;
  onDeleteRule: (ruleId: number) => void;
  onEditRule: (rule: AccountClassificationRuleItem) => void;
  onViewRule: (rule: AccountClassificationRuleItem) => void;
}) {
  const entries = Object.entries(rulesByDbType).filter(([, rules]) => rules.length > 0);
  if (entries.length === 0) {
    return <p className="rounded-md border p-4 text-sm text-muted-foreground">暂无规则，点击“新建规则”开始配置</p>;
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
                  <Button aria-label={`编辑规则 ${rule.rule_name}`} onClick={() => onEditRule(rule)} size="icon" type="button" variant="ghost">
                    <Pencil aria-hidden />
                  </Button>
                  <Button aria-label={`删除规则 ${rule.rule_name}`} onClick={() => onDeleteRule(rule.id)} size="icon" type="button" variant="ghost">
                    <Trash2 aria-hidden />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AccountClassificationsPage() {
  const query = useQuery({
    queryKey: ["read-only", "account-classifications"],
    queryFn: () => fetchAccountClassificationsSnapshot()
  });
  const [creatingClassification, setCreatingClassification] = useState(false);
  const [editingClassification, setEditingClassification] = useState<AccountClassificationItem | null>(null);
  const [creatingRule, setCreatingRule] = useState(false);
  const [editingRule, setEditingRule] = useState<AccountClassificationRuleItem | null>(null);
  const [viewingRule, setViewingRule] = useState<AccountClassificationRuleItem | null>(null);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Account taxonomy" title="账户分类" description="展示分类、风险等级与规则分布，新增和编辑仍保留在旧版。" legacyHref="/accounts/classifications/" />
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
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="账户分类" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const rules = Object.values(snapshot.rulesByDbType).flat();
          return (
            <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
              <ListPanel
                title="账户分类"
                description="分类展示名、系统标记、风险等级和规则数量。"
                count={snapshot.classifications.length}
                actions={
                  <Button onClick={() => setCreatingClassification(true)} size="sm" type="button">
                    <Plus aria-hidden size={16} />
                    <span>新建分类</span>
                  </Button>
                }
              >
                <ClassificationList
                  items={snapshot.classifications}
                  onEdit={setEditingClassification}
                  onDelete={(classificationId) => {
                    void runAction(deleteAccountClassification(classificationId), { success: "账户分类已删除" }).then(() => query.refetch());
                  }}
                />
              </ListPanel>
              <ListPanel
                title="规则管理"
                description="按数据库类型汇总后的分类规则。"
                count={rules.length}
                actions={
                  <Button onClick={() => setCreatingRule(true)} size="sm" type="button">
                    <Plus aria-hidden size={16} />
                    <span>新建规则</span>
                  </Button>
                }
              >
                <RuleGroups
                  onDeleteRule={(ruleId) => {
                    void runAction(deleteAccountClassificationRule(ruleId), { success: "分类规则已删除" }).then(() => query.refetch());
                  }}
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
          {creatingClassification ? (
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
          {editingClassification ? (
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
          {creatingRule ? (
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
          {editingRule ? (
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
        </>
      ) : null}
    </main>
  );
}

function buildClassificationChartData(snapshot: ClassificationStatisticsSnapshot): Array<Record<string, string | number>> {
  const firstSeries = snapshot.trends.series[0];
  if (!firstSeries) {
    return [];
  }
  return firstSeries.points.map((point, index) => ({
    label: point.period_start ?? point.period_end ?? String(index + 1),
    value: asNumber(point.value ?? point.value_avg ?? point.value_sum)
  }));
}

function topClassificationStats(stats: ClassificationStatisticsSnapshot["stats"]) {
  return Object.entries(stats)
    .map(([label, value]) => ({
      label,
      value: asNumber(value.total_accounts ?? value.matched_accounts_count ?? value.count ?? value.total)
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

function buildClassificationOptions(snapshot: ClassificationStatisticsSnapshot): Array<{ value: string; label: string }> {
  const options = new Map<string, string>();
  snapshot.trends.series.forEach((series) => {
    options.set(String(series.classification_id), series.classification_name);
  });
  Object.keys(snapshot.stats).forEach((label) => {
    if (![...options.values()].includes(label)) {
      options.set(label, label);
    }
  });
  return [...options.entries()].map(([value, label]) => ({ value, label }));
}

function trendCoverageLabel(snapshot: ClassificationStatisticsSnapshot): string {
  const total = snapshot.trends.buckets.length || snapshot.trends.series[0]?.points.length || 0;
  const covered = snapshot.trends.series[0]?.points.length ?? 0;
  return `覆盖 ${formatNumber(covered)}/${formatNumber(total)} 天`;
}

function ClassificationFilterPanel({ snapshot }: { snapshot: ClassificationStatisticsSnapshot }) {
  const classificationOptions = buildClassificationOptions(snapshot);
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="grid grid-cols-[minmax(12rem,1.3fr)_minmax(8rem,0.7fr)_minmax(8rem,0.7fr)_minmax(12rem,1.3fr)_auto] items-end gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>账户分类</span>
            <SelectControl label="账户分类" defaultValue="" options={[{ label: "全部分类", value: "" }, ...classificationOptions]} />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>统计周期</span>
            <SelectControl
              label="统计周期"
              defaultValue="daily"
              options={[
                { label: "日统计", value: "daily" },
                { label: "周统计", value: "weekly" },
                { label: "月统计", value: "monthly" },
                { label: "季统计", value: "quarterly" }
              ]}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>数据库类型</span>
            <SelectControl
              label="数据库类型"
              defaultValue=""
              options={[
                { label: "全部类型", value: "" },
                { label: "MySQL", value: "mysql" },
                { label: "PostgreSQL", value: "postgresql" },
                { label: "SQL Server", value: "sqlserver" },
                { label: "Oracle", value: "oracle" }
              ]}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>实例/AG</span>
            <SelectControl label="实例/AG" defaultValue="" disabled options={[{ label: "所有实例/AG", value: "" }]} />
          </label>
          <div className="flex gap-2">
            <Button variant="outline" disabled>
              应用
            </Button>
            <Button variant="ghost" disabled>
              重置
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ClassificationRulesListPanel() {
  return (
    <ListPanel
      title="规则列表"
      description="选择分类后加载规则列表与规则趋势。"
      actions={<Badge variant="outline">最新周期</Badge>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-[minmax(0,1fr)_9rem] gap-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>搜索规则名/备注</span>
            <input className="border-input bg-background h-9 rounded-md border px-3 py-1 text-sm" type="search" readOnly />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>状态</span>
            <SelectControl
              label="状态"
              defaultValue="active"
              options={[
                { label: "启用", value: "active" },
                { label: "已归档", value: "archived" },
                { label: "全部", value: "all" }
              ]}
            />
          </label>
        </div>
        <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
          选择分类后加载规则列表与规则趋势
        </div>
      </div>
    </ListPanel>
  );
}

export function ClassificationStatisticsPage() {
  const query = useQuery({
    queryKey: ["read-only", "classification-statistics"],
    queryFn: () => fetchClassificationStatisticsSnapshot()
  });
  const chartConfig = { value: { label: "匹配账户", color: "var(--chart-1)" } } satisfies ChartConfig;

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Classification analytics" title="分类统计" description="只读展示账户分类统计、规则列表入口和最近周期趋势，写操作仍保留在旧版。" legacyHref="/accounts/statistics/classifications" />
      <CommandBar>
        <Button variant="outline" onClick={() => void query.refetch()}>
          <RotateCcw aria-hidden size={16} />
          <span>刷新</span>
        </Button>
      </CommandBar>
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="分类统计" onRetry={() => void query.refetch()}>
        {(snapshot) => {
          const chartData = buildClassificationChartData(snapshot);
          const topStats = topClassificationStats(snapshot.stats);
          const coverageLabel = trendCoverageLabel(snapshot);
          return (
            <>
              <ClassificationFilterPanel snapshot={snapshot} />
              <MetricGrid
                label="分类统计指标"
                metrics={[
                  { label: "统计分类", value: Object.keys(snapshot.stats).length, icon: ChartColumn },
                  { label: "趋势序列", value: snapshot.trends.series.length, icon: Activity },
                  { label: "周期数量", value: snapshot.trends.buckets.length || chartData.length, icon: Clock },
                  { label: "Top 命中", value: topStats[0]?.value ?? 0, detail: topStats[0]?.label, icon: Tags }
                ]}
              />
              <section className="grid grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)] gap-2 max-xl:grid-cols-1">
                <ClassificationRulesListPanel />
                <div className="grid gap-2">
                  <Card>
                    <CardHeader className="flex flex-row items-start justify-between gap-3">
                      <div>
                        <CardTitle>分类趋势（去重账号数）</CardTitle>
                        <CardDescription>分类趋势面积图</CardDescription>
                      </div>
                      <Badge variant="outline">{coverageLabel}</Badge>
                    </CardHeader>
                    <CardContent>
                      {snapshot.trends.series[0]?.classification_name ? <div className="mb-2 text-sm font-medium">{snapshot.trends.series[0].classification_name}</div> : null}
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
                        <CardDescription>规则之间允许重叠，当前只读首屏默认展示选择分类后的贡献图。</CardDescription>
                      </div>
                      <Badge variant="outline">{coverageLabel}</Badge>
                    </CardHeader>
                    <CardContent className="grid gap-3">
                      <div className="grid min-h-36 place-items-center rounded-md border border-dashed bg-secondary/30 p-4 text-center text-sm text-muted-foreground">
                        选择分类后展示规则贡献
                      </div>
                      <p className="text-sm text-muted-foreground">说明：规则之间允许重叠，“各规则之和”不等于分类去重总数。</p>
                    </CardContent>
                  </Card>
                </div>
              </section>
              <ListPanel title="分类排行" description="按当前统计快照展示 Top 分类。" count={topStats.length}>
                <Table>
                  <TableHeader className="text-xs">
                    <TableRow>
                      <TableHead>分类</TableHead>
                      <TableHead>匹配账户</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topStats.length === 0 ? <EmptyRows colSpan={2} /> : null}
                    {topStats.map((item) => (
                      <TableRow key={item.label}>
                        <TableCell className="font-medium">{item.label}</TableCell>
                        <TableCell className="font-mono text-xs">{formatNumber(item.value)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ListPanel>
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

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation jobs" title="定时任务" description="只读展示调度任务和运行状态，暂停、恢复、立即执行仍保留在旧版。" legacyHref="/scheduler/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="定时任务" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="定时任务指标"
              metrics={[
                { label: "任务总数", value: snapshot.jobs.length, icon: Clock },
                { label: "运行任务", value: snapshot.jobs.filter((job) => isRunningState(job.state)).length, icon: Activity },
                { label: "内置任务", value: snapshot.jobs.filter((job) => job.is_builtin).length, icon: Settings },
                { label: "可配置", value: snapshot.jobs.filter((job) => job.trigger_type).length, icon: ListChecks }
              ]}
            />
            <ListPanel
              title="任务卡片"
              description="按旧版运行状态分组展示任务名称、运行时间、任务 ID、触发器参数和操作。"
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
                <SchedulerJobSection title="运行中的任务" jobs={snapshot.jobs.filter((job) => isRunningState(job.state))} onEdit={setEditingJob} />
                <SchedulerJobSection title="已暂停的任务" jobs={snapshot.jobs.filter((job) => !isRunningState(job.state))} onEdit={setEditingJob} />
              </div>
            </ListPanel>
          </>
        )}
      </QueryFrame>
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
  records: SyncInstanceRecordItem[];
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
                    <span className="font-medium">{record.instance_name ?? "-"}</span>
                    <span className="font-mono text-xs text-muted-foreground">{record.instance_id ? `#${record.instance_id}` : record.session_id}</span>
                  </div>
                </TableCell>
                <TableCell>{record.sync_category ?? "-"}</TableCell>
                <TableCell>
                  <StatusBadge value={record.status} />
                </TableCell>
                <TableCell className="font-mono text-xs">{formatNumber(record.items_synced)}</TableCell>
                <TableCell className="font-mono text-xs">
                  +{formatNumber(record.items_created)} / ~{formatNumber(record.items_updated)} / -{formatNumber(record.items_deleted)}
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
  const detailQuery = useQuery<SyncSessionDetail>({
    enabled: open && sessionId !== null,
    queryKey: ["read-only", "sync-session-detail", sessionId],
    queryFn: () => {
      if (sessionId === null) {
        throw new Error("Missing sync session id");
      }
      return fetchSyncSessionDetail(sessionId);
    }
  });
  const errorsQuery = useQuery<SyncSessionErrorLogs>({
    enabled: open && sessionId !== null,
    queryKey: ["read-only", "sync-session-error-logs", sessionId],
    queryFn: () => {
      if (sessionId === null) {
        throw new Error("Missing sync session id");
      }
      return fetchSyncSessionErrorLogs(sessionId);
    }
  });
  const session = detailQuery.data?.session;
  const progress = session ? syncProgress(session) : null;
  const progressPercent = session?.progress_percentage ?? progress?.percent ?? 0;
  const errorRecords = errorsQuery.data?.error_records ?? [];

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
                  <span className="font-mono text-xs text-muted-foreground">{session.task_key ?? session.sync_type}</span>
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
            <SyncSessionRecordTable emptyLabel="暂无实例执行记录" records={session.instance_records} title="实例执行记录" />
            <SyncSessionRecordTable emptyLabel="暂无错误日志" records={errorRecords} title="错误日志" />
            <section className="grid gap-2">
              <h3 className="text-sm font-semibold">同步详情</h3>
              <JsonBlock value={session.instance_records.map((record) => ({ instance_name: record.instance_name, sync_details: record.sync_details }))} />
            </section>
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
  const query = useQuery({ queryKey: ["read-only", "sync-sessions"], queryFn: () => fetchSyncSessionsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Automation sessions" title="会话中心" description="展示同步会话、实例执行详情、错误日志，并支持取消运行中会话。" legacyHref="/history/sessions/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="会话中心" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="会话指标"
              metrics={[
                { label: "会话总数", value: snapshot.total, icon: ListChecks },
                { label: "当前页", value: `${snapshot.page}/${snapshot.pages ?? 1}`, icon: Clock },
                { label: "运行中", value: snapshot.items.filter((item) => item.status === "running").length, icon: Activity },
                { label: "失败实例", value: snapshot.items.reduce((sum, item) => sum + (item.failed_instances ?? 0), 0), icon: AlertCircle }
              ]}
            />
            <ListPanel title="同步会话" description="最近同步会话首屏列表。" count={snapshot.total}>
              <DataTable
                columns={columns}
                data={snapshot.items}
                filters={[
                  { columnId: "trigger_source", label: "来源", options: uniqueTextOptions(snapshot.items, (item) => syncSource(item)) },
                  { columnId: "task_category", label: "分类", options: uniqueTextOptions(snapshot.items, (item) => syncCategory(item)) },
                  { columnId: "status", label: "状态", options: uniqueTextOptions(snapshot.items, (item) => item.status) }
                ]}
                searchPlaceholder="搜索运行 ID、任务或来源"
              />
            </ListPanel>
          </>
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

export function UsersPage() {
  const query = useQuery({ queryKey: ["read-only", "users"], queryFn: () => fetchUsersSnapshot() });
  const [creatingUser, setCreatingUser] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [deletingUser, setDeletingUser] = useState<UserItem | null>(null);
  const columns = useMemo(
    () =>
      createUserColumns({
        onDelete: setDeletingUser,
        onEdit: setEditingUser
      }),
    []
  );

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Access control" title="用户管理" description="展示用户、角色与启用状态，并支持新增、编辑、删除。" legacyHref="/users/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="用户管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="用户指标"
              metrics={[
                { label: "用户总数", value: snapshot.stats.total, icon: UserCog },
                { label: "活跃用户", value: snapshot.stats.active, icon: Activity },
                { label: "管理员", value: snapshot.stats.admin, icon: KeyRound },
                { label: "普通用户", value: snapshot.stats.user, icon: UserCog }
              ]}
            />
            <ListPanel
              title="用户列表"
              description={`每页 ${formatNumber(snapshot.list.limit)} 条`}
              count={snapshot.list.total}
              actions={
                <Button onClick={() => setCreatingUser(true)} size="sm" type="button">
                  <Plus aria-hidden />
                  新建用户
                </Button>
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  {
                    columnId: "role",
                    label: "角色",
                    options: [
                      { label: "管理员", value: "admin" },
                      { label: "普通用户", value: "user" },
                      { label: "查看者", value: "viewer" }
                    ]
                  },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索用户名或邮箱"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
      {creatingUser ? (
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
      {editingUser ? (
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
        open={deletingUser !== null}
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

function ToggleRow({ label, checked }: { label: string; checked: unknown }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 text-sm">
      <span>{label}</span>
      <StatusBadge value={checked === true} />
    </div>
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

export function SettingsPage() {
  const query = useQuery({ queryKey: ["read-only", "settings"], queryFn: () => fetchSettingsSnapshot() });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="System integrations" title="系统设置" description="只读展示集成源、告警和风险规则配置状态，保存、测试、同步动作仍保留在旧版。" legacyHref="/admin/system-settings" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="系统设置" onRetry={() => void query.refetch()}>
        {(snapshot) => {
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

export function CredentialsPage() {
  const query = useQuery({ queryKey: ["read-only", "credentials"], queryFn: () => fetchCredentialsSnapshot() });
  const [creatingCredential, setCreatingCredential] = useState(false);
  const [editingCredential, setEditingCredential] = useState<CredentialItem | null>(null);
  const [deletingCredential, setDeletingCredential] = useState<CredentialItem | null>(null);
  const columns = useMemo(
    () =>
      createCredentialColumns({
        onDelete: setDeletingCredential,
        onEdit: setEditingCredential
      }),
    []
  );

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Credential vault" title="凭据管理" description="展示凭据类型、数据库类型和引用数量，并支持新增、编辑、删除。" legacyHref="/credentials/" />
      <QueryFrame data={query.data} isLoading={query.isLoading} isError={query.isError} errorLabel="凭据管理" onRetry={() => void query.refetch()}>
        {(snapshot) => (
          <>
            <MetricGrid
              label="凭据指标"
              metrics={[
                { label: "凭据总数", value: snapshot.total, icon: KeyRound },
                { label: "启用凭据", value: snapshot.items.filter((item) => item.is_active !== false).length, icon: Activity },
                { label: "数据库凭据", value: snapshot.items.filter((item) => item.credential_type === "database").length, icon: Database },
                { label: "引用实例", value: snapshot.items.reduce((sum, item) => sum + (item.instance_count ?? 0), 0), icon: Layers3 }
              ]}
            />
            <ListPanel
              title="凭据列表"
              description={`每页 ${formatNumber(snapshot.limit)} 条`}
              count={snapshot.total}
              actions={
                <Button onClick={() => setCreatingCredential(true)} size="sm" type="button">
                  <Plus aria-hidden />
                  新建凭据
                </Button>
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.items}
                filters={[
                  { columnId: "credential_type", label: "凭据类型", options: uniqueTextOptions(snapshot.items, (item) => item.credential_type) },
                  { columnId: "db_type", label: "数据库类型", options: uniqueTextOptions(snapshot.items, (item) => item.db_type) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索凭据、账号或数据库类型"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
      {creatingCredential ? (
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
      {editingCredential ? (
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
        open={deletingCredential !== null}
        title={`确认删除凭据 ${deletingCredential?.name ?? ""}`}
      />
    </main>
  );
}

export function TagsPage() {
  const query = useQuery({ queryKey: ["read-only", "tags"], queryFn: () => fetchTagsSnapshot() });
  const [creatingTag, setCreatingTag] = useState(false);
  const [editingTag, setEditingTag] = useState<TagItem | null>(null);
  const [deletingTag, setDeletingTag] = useState<TagItem | null>(null);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const columns = useMemo(
    () =>
      createTagColumns({
        onDelete: setDeletingTag,
        onEdit: setEditingTag
      }),
    []
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
                { label: "全部标签", value: snapshot.list.stats.total, icon: Tags },
                { label: "启用率", value: formatPercent(snapshot.list.stats.active, snapshot.list.stats.total), detail: `${formatNumber(snapshot.list.stats.active)} 个启用`, icon: Activity },
                { label: "停用率", value: formatPercent(snapshot.list.stats.inactive, snapshot.list.stats.total), detail: `${formatNumber(snapshot.list.stats.inactive)} 个停用`, icon: AlertCircle },
                { label: "标签分类", value: snapshot.list.stats.category_count, detail: `${snapshot.categories.length} 个分类`, icon: Boxes }
              ]}
            />
            <ListPanel
              title="标签列表"
              description={`分类: ${snapshot.categories.join(", ") || "-"}`}
              count={snapshot.list.total}
              actions={
                <>
                  <Button onClick={() => setCreatingTag(true)} size="sm" type="button">
                    <Plus aria-hidden />
                    新建标签
                  </Button>
                  <Button onClick={() => setBulkDialogOpen(true)} size="sm" type="button" variant="outline">
                    批量分配
                  </Button>
                </>
              }
            >
              <DataTable
                columns={columns}
                data={snapshot.list.items}
                filters={[
                  { columnId: "category", label: "分类", options: uniqueTextOptions(snapshot.list.items, (item) => item.category) },
                  {
                    columnId: "is_active",
                    label: "状态",
                    options: [
                      { label: "启用", value: "true" },
                      { label: "停用", value: "false" }
                    ]
                  }
                ]}
                searchPlaceholder="搜索标签、编码或分类"
              />
            </ListPanel>
          </>
        )}
      </QueryFrame>
      {creatingTag ? (
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
      {editingTag ? (
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
      {bulkDialogOpen ? (
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
        open={deletingTag !== null}
        title={`确认删除标签 ${deletingTag?.display_name ?? ""}`}
      />
    </main>
  );
}

function PartitionsTable({ items }: { items: PartitionItem[] }) {
  return (
    <Table className="min-w-[52rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["分区", "表", "类型", "大小", "记录", "状态"].map((label) => (
            <TableHead key={label}>{label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow key={item.name}>
            <TableCell className="font-medium">{item.display_name ?? item.name}</TableCell>
            <TableCell>{item.table ?? "-"}</TableCell>
            <TableCell>{item.table_type ?? "-"}</TableCell>
            <TableCell className="font-mono text-xs">{item.size ?? "-"}</TableCell>
            <TableCell className="font-mono text-xs">{formatNumber(item.record_count)}</TableCell>
            <TableCell>
              <span className="text-xs text-muted-foreground">{item.status ? `分区 ${statusLabel(item.status)}` : "-"}</span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function PartitionsPage() {
  const query = useQuery({ queryKey: ["read-only", "partitions"], queryFn: () => fetchPartitionsSnapshot() });
  const chartConfig = { value: { label: "分区指标", color: "var(--chart-2)" } } satisfies ChartConfig;
  const [partitionDate, setPartitionDate] = useState("");
  const [retentionMonths, setRetentionMonths] = useState("12");

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader eyebrow="Storage partitions" title="分区管理" description="只读展示分区健康状态、核心指标和分区列表，创建和清理动作仍保留在旧版。" legacyHref="/partition/" />
      <CommandBar>
        <FormField label="分区日期">
          <Input className="w-44" onChange={(event) => setPartitionDate(event.target.value)} type="date" value={partitionDate} />
        </FormField>
        <FormField label="保留月份">
          <Input className="w-28" min={1} onChange={(event) => setRetentionMonths(event.target.value)} type="number" value={retentionMonths} />
        </FormField>
        <Button
          onClick={() => {
            void runAction(createPartition(partitionDate || undefined), { success: "分区创建已触发" }).then(() => query.refetch());
          }}
          type="button"
        >
          <Plus aria-hidden />
          创建分区
        </Button>
        <Button
          onClick={() => {
            void runAction(cleanupPartitions(numberFromInput(retentionMonths, 12)), { success: "旧分区清理已触发" }).then(() => query.refetch());
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
          const metricValues = snapshot.coreMetrics.datasets[0]?.data ?? [];
          const chartData = snapshot.coreMetrics.labels.map((label, index) => ({ label, value: metricValues[index] ?? 0 }));
          return (
            <>
              <MetricGrid
                label="分区指标"
                metrics={[
                  { label: "分区总数", value: status.total_partitions ?? snapshot.list.total, icon: Boxes },
                  { label: "总大小", value: status.total_size ?? "-", icon: Database },
                  { label: "总记录数", value: status.total_records ?? 0, icon: ListChecks },
                  { label: "健康状态", value: statusLabel(status.status), detail: "数据库连接", icon: Activity }
                ]}
              />
              <section className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-2 max-xl:grid-cols-1">
                <Card>
                  <CardHeader className="flex flex-row items-start justify-between gap-3">
                    <div>
                      <CardTitle>核心指标趋势</CardTitle>
                      <CardDescription>最近7天的核心指标统计</CardDescription>
                    </div>
                    <StatusBadge value={status.status} />
                  </CardHeader>
                  <CardContent className="grid gap-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                      <span>数据库连接</span>
                      <span>{snapshot.status.timestamp ?? "-"}</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {["日", "周", "月", "季"].map((period, index) => (
                        <Button key={period} size="sm" type="button" variant={index === 0 ? "default" : "outline"}>
                          {period}
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
                <ListPanel title="分区列表" description={`每页 ${formatNumber(snapshot.list.limit)} 条`} count={snapshot.list.total}>
                  <PartitionsTable items={snapshot.list.items} />
                </ListPanel>
              </section>
            </>
          );
        }}
      </QueryFrame>
    </main>
  );
}
