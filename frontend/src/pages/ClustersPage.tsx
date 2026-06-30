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
  fetchAccountLedgers,
  type AccountLedgerItem,
} from "@/api/lists";
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

function numericValue(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function booleanValue(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
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
  onClose?: () => void;
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
        {onClose ? (
          <Button onClick={onClose} size="sm" type="button" variant="outline">
            收起看板
          </Button>
        ) : null}
      </div>
      {query.isLoading ? <Skeleton className="h-32 w-full" /> : null}
      {query.isError ? <ErrorState label={title} onRetry={() => void query.refetch()} /> : null}
      {query.data ? <SqlServerAgDashboardContent dashboard={query.data} /> : null}
    </section>
  );
}

function SqlServerAgDashboardContent({ dashboard }: { dashboard: SqlServerAvailabilityGroupDashboard }) {
  const summary = dashboard.summary ?? dashboard.availability_group ?? {};
  const databaseGroups = dashboard.database_groups ?? [];
  const flatDatabases = dashboard.databases ?? databaseGroups.flatMap((group) => group.databases ?? []);
  const listener = [clusterRecordField(summary, ["listener_name"], ""), clusterRecordField(summary, ["listener_host"], "")]
    .filter(Boolean)
    .join(" / ");

  return (
    <div className="grid gap-3">
      <section className="grid grid-cols-3 gap-2 max-lg:grid-cols-1">
        <DetailBlock label="AG">{clusterRecordField(summary, ["ag_name", "name", "availability_group_name"])}</DetailBlock>
        <DetailBlock label="监听器">{listener || clusterRecordField(summary, ["listener_name", "listener_host"])}</DetailBlock>
        <DetailBlock label="状态">
          <StatusBadge value={clusterRecordField(summary, ["status", "health_status", "sync_status", "is_enabled"])} />
        </DetailBlock>
      </section>
      <ListPanel title="副本状态" description="AG 看板中的副本角色与同步健康。" count={dashboard.replicas.length}>
        <ClusterDetailRecordsTable
          columns={[
            { label: "副本", keys: ["replica_server_name", "server_name", "name"] },
            { label: "角色", keys: ["role_desc", "role"] },
            { label: "可用模式", keys: ["availability_mode_desc"] },
            { label: "故障转移", keys: ["failover_mode_desc"] },
            { label: "连接状态", keys: ["connected_state_desc"] },
            { label: "同步健康", keys: ["synchronization_health_desc", "health_status"] },
            { label: "问题", keys: ["error_summary"] }
          ]}
          records={dashboard.replicas}
        />
      </ListPanel>
      <ListPanel title="数据库状态" description="AG 看板中的数据库同步状态。" count={flatDatabases.length}>
        {databaseGroups.length > 0 ? (
          <div className="grid gap-3">
            {databaseGroups.map((group, index) => (
              <section className="grid gap-2" key={`${clusterRecordField(group, ["replica_server_name", "name"], String(index))}-${index}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{clusterRecordField(group, ["replica_server_name", "name"])}</span>
                  <StatusBadge value={clusterRecordField(group, ["status", "health_status"])} />
                </div>
                <ClusterDetailRecordsTable
                  columns={[
                    { label: "数据库", keys: ["database_name", "name"] },
                    { label: "同步状态", keys: ["synchronization_state_desc", "sync_status"] },
                    { label: "健康", keys: ["synchronization_health_desc", "health_status"] },
                    { label: "故障转移就绪", keys: ["failover_ready"] },
                    { label: "发送队列", keys: ["log_send_queue_size"] },
                    { label: "Redo 队列", keys: ["redo_queue_size"] },
                    { label: "问题", keys: ["error_summary"] }
                  ]}
                  records={group.databases ?? []}
                />
              </section>
            ))}
          </div>
        ) : (
          <ClusterDetailRecordsTable
            columns={[
              { label: "数据库", keys: ["database_name", "name"] },
              { label: "同步状态", keys: ["synchronization_state_desc", "sync_status"] },
              { label: "健康", keys: ["synchronization_health_desc", "health_status"] }
            ]}
            records={flatDatabases}
          />
        )}
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

function agRecordKey(record: ClusterDetailRecord, index = 0): string {
  return String(clusterRecordId(record) ?? clusterRecordField(record, ["name", "availability_group_name"], `ag-${index}`));
}

function agAccountAvailabilityLabel(item: AccountLedgerItem): string {
  if (item.is_deleted || item.is_active === false) {
    return "已删除";
  }
  if (item.is_locked) {
    return "不可用";
  }
  return "可用";
}

function agAccountAdStatusLabel(value: string | null | undefined): string {
  switch (value) {
    case "normal":
      return "AD正常";
    case "disabled":
      return "AD已停用";
    case "orphaned":
      return "AD孤账户";
    default:
      return "未匹配AD";
  }
}

function agAccountTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.replace("T", " ").replace(/\.\d+/, "").replace(/\+\d{2}:\d{2}$/, "");
  }
  const parts = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).formatToParts(date);
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${byType.year}-${byType.month}-${byType.day} ${byType.hour}:${byType.minute}:${byType.second}`;
}

function agAccountNames(items: Array<{ display_name?: string | null; name?: string | null }>): string {
  return items.map((item) => item.display_name || item.name).filter(Boolean).join(" / ") || "-";
}

function AgAccountLedgerRows({ items }: { items: AccountLedgerItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">暂无 AG 账户，请先同步 AG 账户</p>;
  }
  return (
    <div className="grid gap-2">
      {items.map((account) => (
        <div key={account.id} className="grid grid-cols-[minmax(12rem,1.4fr)_auto_minmax(16rem,1.6fr)] items-center gap-3 rounded-md border bg-background p-3 max-lg:grid-cols-1">
          <div className="grid gap-1">
            <strong>{account.username}</strong>
            <small className="text-muted-foreground">{[account.instance_name, account.instance_host].filter(Boolean).join(" · ") || "-"}</small>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-emerald-50 text-emerald-700" variant="outline">
              {agAccountAvailabilityLabel(account)}
            </Badge>
            <Badge className={account.is_superuser ? "bg-emerald-50 text-emerald-700" : ""} variant="outline">
              {account.is_superuser ? "是" : "否"}
            </Badge>
            <Badge variant="secondary">{agAccountAdStatusLabel(account.ad_status)}</Badge>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span>分类 {agAccountNames(account.classifications)}</span>
            <span>标签 {agAccountNames(account.tags)}</span>
            <span>最近变更 {agAccountTimestamp(account.last_change_time)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SqlServerClusterDetailContent({ clusterId, detail }: { clusterId: number; detail: SqlServerClusterDetail }) {
  const availabilityGroups = detail.availability_groups;
  const [selectedAgKey, setSelectedAgKey] = useState(() => (availabilityGroups[0] ? agRecordKey(availabilityGroups[0]) : ""));
  const selectedAg = availabilityGroups.find((record, index) => agRecordKey(record, index) === selectedAgKey) ?? availabilityGroups[0];

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
      {selectedAg ? (
        <section className="grid gap-3">
          <Tabs className="grid gap-3" value={selectedAgKey} onValueChange={setSelectedAgKey}>
            <TabsList className="h-auto w-full justify-start overflow-x-auto p-1">
              {availabilityGroups.map((record, index) => (
                <TabsTrigger key={agRecordKey(record, index)} value={agRecordKey(record, index)}>
                  {sqlServerAgName(record)}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <SqlServerAgDashboardInline clusterId={clusterId} item={selectedAg} />
        </section>
      ) : null}
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
        {query.data ? <SqlServerClusterDetailContent clusterId={item.id} detail={query.data} /> : null}
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

function SqlServerAgAccountsDialog({
  item,
  onOpenChange,
  onSynced,
  open
}: {
  item: ClusterItem;
  onOpenChange: (open: boolean) => void;
  onSynced: () => void;
  open: boolean;
}) {
  const query = useQuery({
    queryKey: ["read-only", "clusters", "sqlserver", item.id, "ag-accounts"],
    queryFn: () => fetchSqlServerClusterDetail(item.id),
    enabled: open
  });
  const availabilityGroups = query.data?.availability_groups ?? [];
  const [selectedAgKey, setSelectedAgKey] = useState("");
  const activeKey = selectedAgKey || (availabilityGroups[0] ? agRecordKey(availabilityGroups[0]) : "empty");
  const selectedAg = availabilityGroups.find((record, index) => agRecordKey(record, index) === activeKey) ?? availabilityGroups[0];
  const selectedAgId = selectedAg ? clusterRecordId(selectedAg) : null;
  const accountsQuery = useQuery({
    queryKey: ["lists", "accounts", "sqlserver-ag", selectedAgId],
    queryFn: () =>
      fetchAccountLedgers({
        page: 1,
        limit: 100,
        ownerType: "sqlserver_ag",
        ownerId: selectedAgId ?? undefined,
        includeRoles: true
      }),
    enabled: open && selectedAgId !== null,
    placeholderData: (previous) => previous
  });
  const containedCount = availabilityGroups.filter((record) => Boolean(record.contained_enabled)).length;
  const credentialedCount = availabilityGroups.filter((record) => !isEmptyDetailValue(record.account_credential_id)).length;
  const enabledCount = availabilityGroups.filter((record) => record.is_enabled === true).length;

  function handleSync() {
    void runAction(syncSqlServerAgAccounts(item.id), { success: "AG 账户同步已触发" }).then(() => {
      onSynced();
      void query.refetch();
      void accountsQuery.refetch();
    });
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="w-[min(calc(100vw-2rem),60rem)]">
        <DialogHeader>
          <DialogTitle>AG 账户 {item.name}</DialogTitle>
          <DialogDescription>查看 SQL Server contained AG 账户采集概览，并触发 AG 账户同步。</DialogDescription>
        </DialogHeader>
        {query.isLoading ? <Skeleton className="h-48 w-full" /> : null}
        {query.isError ? <ErrorState label="AG 账户" onRetry={() => void query.refetch()} /> : null}
        {query.data ? (
          <div className="grid gap-4">
            <section className="grid grid-cols-4 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
              <DetailBlock label="AG 总数">{formatNumber(availabilityGroups.length)}</DetailBlock>
              <DetailBlock label="Contained">{formatNumber(containedCount)}</DetailBlock>
              <DetailBlock label="已配凭据">{formatNumber(credentialedCount)}</DetailBlock>
              <DetailBlock label="启用采集">{formatNumber(enabledCount)}</DetailBlock>
            </section>
            <Tabs className="grid gap-3" value={activeKey} onValueChange={setSelectedAgKey}>
              <TabsList className="h-auto w-full justify-start overflow-x-auto p-1">
                {availabilityGroups.length > 0 ? (
                  availabilityGroups.map((record, index) => (
                    <TabsTrigger key={agRecordKey(record, index)} value={agRecordKey(record, index)}>
                      {sqlServerAgName(record)}
                    </TabsTrigger>
                  ))
                ) : (
                  <TabsTrigger value="empty">暂无 AG</TabsTrigger>
                )}
              </TabsList>
            </Tabs>
            <section className="grid gap-2 rounded-md border bg-secondary/20 p-3">
              <div className="grid gap-1">
                <h3 className="font-display text-base font-semibold">{selectedAg ? sqlServerAgName(selectedAg) : "暂无 AG"}</h3>
                <p className="text-sm text-muted-foreground">
                  {selectedAg
                    ? [sqlServerAgName(selectedAg), clusterRecordField(selectedAg, ["listener_name", "listener_host"], ""), clusterRecordField(selectedAg, ["connection_endpoint"], "")]
                        .filter(Boolean)
                        .join(" · ")
                    : "-"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {selectedAg && !isEmptyDetailValue(selectedAg.last_sync_at)
                    ? `最近同步 ${formatDateTime(asText(selectedAg.last_sync_at))}`
                    : "未同步"}
                </p>
              </div>
              <ListPanel title="账户列表" count={accountsQuery.data?.total ?? 0}>
                {accountsQuery.isLoading ? <p className="text-sm text-muted-foreground">账户列表加载中...</p> : null}
                {accountsQuery.isError ? <ErrorState label="AG 账户列表" onRetry={() => void accountsQuery.refetch()} /> : null}
                {accountsQuery.data ? <AgAccountLedgerRows items={accountsQuery.data.items} /> : null}
              </ListPanel>
            </section>
          </div>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
          <Button type="button" onClick={handleSync}>
            同步 AG 账户
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function createSqlServerClusterColumns({
  onAgConfig,
  onAgAccounts,
  onBind,
  onDetail,
  onEdit
}: {
  onAgConfig: (item: ClusterItem) => void;
  onAgAccounts: (item: ClusterItem) => void;
  onBind: (item: ClusterItem) => void;
  onDetail: (item: ClusterItem) => void;
  onEdit: (item: ClusterItem) => void;
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
            onClick={() => onAgAccounts(row.original)}
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
  const [viewingAgAccountsCluster, setViewingAgAccountsCluster] = useState<ClusterItem | null>(null);
  const [maintainingCluster, setMaintainingCluster] = useState<{
    mode: ClusterMode;
    item: ClusterItem;
    panel: "instances" | "sqlserver-ag";
  } | null>(null);
  const sqlServerClusterColumns = useMemo(
    () =>
      createSqlServerClusterColumns({
        onAgConfig: (item) => setMaintainingCluster({ mode: "sqlserver", item, panel: "sqlserver-ag" }),
        onAgAccounts: setViewingAgAccountsCluster,
        onBind: (item) => setMaintainingCluster({ mode: "sqlserver", item, panel: "instances" }),
        onDetail: (item) => setViewingCluster({ mode: "sqlserver", item }),
        onEdit: (item) => setEditingCluster({ mode: "sqlserver", item })
      }),
    []
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
                  onResetFilters={sqlServerTable.reset}
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
                  onResetFilters={mySqlTable.reset}
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
      {viewingAgAccountsCluster ? (
        <SqlServerAgAccountsDialog
          item={viewingAgAccountsCluster}
          onOpenChange={(open) => {
            if (!open) {
              setViewingAgAccountsCluster(null);
            }
          }}
          onSynced={refreshClusters}
          open
        />
      ) : null}
    </main>
  );
}
