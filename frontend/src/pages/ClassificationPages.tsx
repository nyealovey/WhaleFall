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
