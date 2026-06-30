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
import { Switch } from "@/components/ui/switch";
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
    recipients: textList(settings.recipients).join("\n")
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
    recipients: textList(form.recipients)
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

function feishuWebhookDisplay(settings: Record<string, unknown>): string {
  const masked = asText(settings.feishu_webhook_url_masked, "");
  if (settings.feishu_webhook_url_configured === true && masked) {
    return `已配置：${masked}`;
  }
  if (settings.feishu_webhook_url_configured === true) {
    return "已配置";
  }
  const raw = asText(settings.feishu_webhook_url, "");
  if (raw) {
    return `已配置：${maskWebhookUrl(raw)}`;
  }
  return "未配置";
}

function feishuWebhookConfigured(settings: Record<string, unknown>): boolean {
  return settings.feishu_webhook_url_configured === true || Boolean(asText(settings.feishu_webhook_url_masked, "")) || Boolean(asText(settings.feishu_webhook_url, ""));
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
  { label: "Alerts", value: "alerts" },
  { label: "Risk Rules", value: "risk" },
  { label: "JumpServer", value: "jumpserver" },
  { label: "Veeam", value: "veeam" },
  { label: "Active Directory", value: "ad" }
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
              <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                <ReadonlyField label="投递通道" value={snapshot.alerts.smtp_ready ? "SMTP" : "未就绪"} />
                <FormField label="收件人">
                  <Textarea value={alertForm.recipients} onChange={(event) => setAlertForm((form) => ({ ...form, recipients: event.target.value }))} />
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
                <SwitchField checked={alertForm.global_enabled} label="启用邮件告警" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, global_enabled: checked }))} />
                <Button onClick={() => void runAction(sendAlertTestEmail(textList(alertForm.recipients)), { success: "测试邮件已发送" })} size="sm" type="button" variant="outline">
                  发送测试邮件
                </Button>
              </div>
            </SettingsSubsection>

            <SettingsSubsection title="飞书数据源">
              <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                <ReadonlyField label="当前飞书 Webhook" value={feishuWebhookDisplay(alertSettings)} />
                <FormField label="飞书机器人 URL">
                  <Input placeholder={feishuWebhookConfigured(alertSettings) ? "已配置，留空表示不修改" : "请输入飞书机器人 URL"} type="password" value={alertForm.feishu_webhook_url} onChange={(event) => setAlertForm((form) => ({ ...form, feishu_webhook_url: event.target.value }))} />
                </FormField>
                <SwitchField checked={alertForm.feishu_enabled} label="发送到飞书" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, feishu_enabled: checked }))} />
                <CheckboxLine checked={alertForm.clear_feishu_webhook_url} label="清空飞书 Webhook" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, clear_feishu_webhook_url: checked, feishu_webhook_url: checked ? "" : form.feishu_webhook_url }))}>
                  清空飞书 Webhook
                </CheckboxLine>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void runAction(sendFeishuTest(alertForm.feishu_webhook_url.trim()), { success: "飞书测试已发送" })} size="sm" type="button" variant="outline">
                  发送飞书测试
                </Button>
                <Button onClick={() => void runAction(saveAlertSettings(alertSettingsPayload(alertForm)), { success: "告警设置已保存" }).then(onRefresh)} size="sm" type="button">
                  保存配置
                </Button>
              </div>
            </SettingsSubsection>

            <SettingsSubsection title="飞书数据源列表">
              <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/40 px-3 py-2 max-sm:grid">
                <div>
                  <div className="font-medium">飞书机器人</div>
                  <div className="font-mono text-xs text-muted-foreground">{feishuWebhookDisplay(alertSettings)}</div>
                  <div className="text-xs text-muted-foreground">
                    {alertForm.feishu_enabled ? "已启用" : "未启用"} · {feishuWebhookConfigured(alertSettings) ? "Webhook 已配置" : "Webhook 未配置"}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={alertForm.feishu_enabled && feishuWebhookConfigured(alertSettings)} />
                  <Button onClick={() => setActiveModule("alerts")} size="sm" type="button" variant="outline">
                    编辑飞书数据源
                  </Button>
                </div>
              </div>
            </SettingsSubsection>

            <SettingsSubsection title="规则设置">
              <section aria-label="容量异常增长规则" className="grid gap-3 rounded-md border bg-background p-3">
                <SwitchField checked={alertForm.database_capacity_enabled} label="容量异常增长" onCheckedChange={(checked) => setAlertForm((form) => ({ ...form, database_capacity_enabled: checked }))} />
                <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                  <FormField label="容量增长百分比阈值">
                    <Input min={1} type="number" value={alertForm.database_capacity_percent_threshold} onChange={(event) => setAlertForm((form) => ({ ...form, database_capacity_percent_threshold: event.target.value }))} />
                  </FormField>
                  <FormField label="容量增长绝对阈值">
                    <Input min={1} type="number" value={alertForm.database_capacity_absolute_gb_threshold} onChange={(event) => setAlertForm((form) => ({ ...form, database_capacity_absolute_gb_threshold: event.target.value }))} />
                  </FormField>
                </div>
              </section>
              <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                {[
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
                  <div className="flex justify-end">
                    <Switch
                      aria-label={`启用风险规则 ${asText(sourceRule.display_name ?? sourceRule.name, rule.rule_key)}`}
                      checked={rule.enabled}
                      onCheckedChange={(enabled) => setRiskRules((items) => items.map((item, itemIndex) => (itemIndex === index ? { ...item, enabled } : item)))}
                    />
                  </div>
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
                      <Button onClick={() => numericId(config.id) !== null && void runAction(testAdDomainConfig(numericId(config.id) as number), { success: "AD 连接测试已完成" })} size="sm" type="button" variant="outline">
                        <span>测试 AD 连接</span>
                        <span className="sr-only"> {asText(config.name)}</span>
                      </Button>
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
      <PageHeader eyebrow="System integrations" title="系统设置" description="迁移旧版系统设置模块，保留告警、风险规则、JumpServer、Veeam 和 AD 配置能力。" />
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
                    {["Alerts", "Risk Rules", "JumpServer", "Veeam", "Active Directory"].map((label) => (
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
                        <ReadonlyField label="飞书机器人 URL" value={feishuWebhookDisplay(alertSettings)} />
                        <ReadonlyField label="收件人" value={alertSettings.recipients} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
                        <ToggleRow label="启用邮件告警" checked={alertSettings.global_enabled} />
                        <ToggleRow label="发送到飞书" checked={alertSettings.feishu_enabled} />
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
