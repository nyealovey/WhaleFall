import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  AlertCircle,
  BarChart3,
  Check,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileUp,
  Folder,
  HardDrive,
  Layers,
  Pencil,
  PlugZap,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Tag,
  Trash2,
  Users
} from "lucide-react";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useParams } from "react-router-dom";

import {
  batchDeleteInstances,
  batchTestInstanceConnections,
  createInstance,
  deleteInstance,
  importInstancesFromCsv,
  refreshDatabaseTableSizes,
  restoreInstance,
  syncAccounts,
  syncDatabases,
  syncInstanceAccounts,
  syncInstanceAuditInfo,
  syncInstanceBackup,
  syncInstanceCapacity,
  testInstanceConnection,
  updateInstance,
  validateInstanceConnectionParams,
  type InstanceWritePayload
} from "@/api/actions";
import {
  buildAccountLedgersExportPath,
  buildDatabaseLedgersExportPath,
  buildInstancesExportPath,
  fetchAccountClassificationOptions,
  fetchAccountChangeHistory,
  fetchAccountLedgers,
  fetchCredentialOptions,
  fetchAccountPermissions,
  fetchDatabaseLedgers,
  fetchDatabaseTableSizes,
  fetchInstanceAccounts,
  fetchInstanceAgAccounts,
  fetchInstanceAuditInfo,
  fetchInstanceBackupInfo,
  fetchInstanceConnectionStatus,
  fetchInstanceDatabaseSizes,
  fetchInstanceDetail,
  fetchInstances,
  fetchTagOptions,
  type AccountChangeHistoryResponse,
  type AccountLedgerItem,
  type AccountPermissionsResponse,
  type CredentialOptionItem,
  type DatabaseLedgerItem,
  type DatabaseTableSizesResponse,
  type DatabaseTableSizeItem,
  type InstanceAgAccountItem,
  type InstanceAgAccountsResponse,
  type InstanceAuditInfo,
  type InstanceBackupInfo,
  type InstanceBackupRestorePoint,
  type InstanceConnectionStatus,
  type InstanceDatabaseSizeItem,
  type InstanceDatabaseSizesResponse,
  type InstanceListItem,
  type PaginatedList,
  type TagItem
} from "@/api/lists";
import { DataTable } from "@/components/shared/DataTable";
import { useServerTableState } from "@/components/shared/useServerTableState";
import { SelectControl, SwitchField } from "@/components/shared/FormControls";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { runAction } from "@/utils/action-feedback";

const DATABASE_TYPE_FILTER_OPTIONS = [
  { label: "MySQL", value: "mysql" },
  { label: "PostgreSQL", value: "postgresql" },
  { label: "SQL Server", value: "sqlserver" },
  { label: "Oracle", value: "oracle" }
];
const ACTIVE_STATUS_FILTER_OPTIONS = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" }
];
const INSTANCE_AUDIT_FILTER_OPTIONS = [
  { label: "已启用", value: "enabled" },
  { label: "已配置未启用", value: "configured_disabled" },
  { label: "未配置", value: "not_configured" }
];
const INSTANCE_MANAGED_FILTER_OPTIONS = [
  { label: "已托管", value: "managed" },
  { label: "未托管", value: "unmanaged" }
];
const INSTANCE_BACKUP_FILTER_OPTIONS = [
  { label: "24h内备份", value: "backed_up" },
  { label: "备份过期", value: "backup_stale" },
  { label: "未备份", value: "not_backed_up" }
];
const ACCOUNT_AD_STATUS_FILTER_OPTIONS = [
  { label: "正常", value: "normal" },
  { label: "已停用", value: "disabled" },
  { label: "孤账户", value: "orphaned" },
  { label: "未匹配", value: "unknown" }
];

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatShortTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "暂无同步记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.replace("T", " ").replace(/\.\d+/, "").replace(/\+\d{2}:\d{2}$/, "");
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function statusVariant(status: string | undefined): "default" | "secondary" | "destructive" | "outline" {
  if (!status) {
    return "outline";
  }
  if (["disabled", "deleted", "failed", "error", "not_backed_up", "locked", "已删除", "已锁定", "未备份"].includes(status)) {
    return "destructive";
  }
  if (["ok", "enabled", "completed", "backed_up", "active", "启用", "已启用", "已托管", "已备份", "正常"].includes(status)) {
    return "secondary";
  }
  return "outline";
}

function dbTypeLabel(value: string | undefined | null): string {
  return value ? value.toUpperCase() : "-";
}

function tagsText(tags: TagItem[]): string {
  return tags.map((tag) => tag.display_name || tag.name).filter(Boolean).join(" ");
}

function selectedTagValues(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function tagDisplayName(tag: TagItem): string {
  return tag.display_name || tag.name;
}

function tagCategoryName(tag: TagItem): string {
  return tag.category?.trim() || "未分类";
}

function summarizeSelectedTags(options: TagItem[], selectedValues: string[]): string {
  if (selectedValues.length === 0) {
    return "选择标签";
  }
  const optionMap = new Map(options.map((option) => [option.name, tagDisplayName(option)]));
  if (selectedValues.length <= 2) {
    return selectedValues.map((value) => optionMap.get(value) || value).join(" / ");
  }
  return `已选 ${selectedValues.length} 个标签`;
}

function TagSelectorFilter({
  disabled = false,
  onChange,
  options,
  selectedValues
}: {
  disabled?: boolean;
  onChange: (values: string[]) => void;
  options: TagItem[];
  selectedValues: string[];
}) {
  const [open, setOpen] = useState(false);
  const [draftValues, setDraftValues] = useState<string[]>(selectedValues);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const selectedSet = new Set(draftValues);
  const categories = useMemo(() => {
    return Array.from(new Set(options.map(tagCategoryName))).sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));
  }, [options]);
  const filteredOptions = options.filter((tag) => {
    const keyword = search.trim().toLowerCase();
    const matchesCategory = !category || tagCategoryName(tag) === category;
    const matchesSearch = !keyword
      || tagDisplayName(tag).toLowerCase().includes(keyword)
      || tag.name.toLowerCase().includes(keyword)
      || tagCategoryName(tag).toLowerCase().includes(keyword);
    return matchesCategory && matchesSearch;
  });
  const selectedTags = draftValues
    .map((value) => options.find((tag) => tag.name === value))
    .filter((tag): tag is TagItem => Boolean(tag));
  const activeCount = options.filter((tag) => tag.is_active !== false).length;
  const summary = summarizeSelectedTags(options, selectedValues);

  function toggleTag(value: string) {
    setDraftValues((current) => {
      if (current.includes(value)) {
        return current.filter((item) => item !== value);
      }
      return [...current, value];
    });
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setDraftValues(selectedValues);
      setSearch("");
      setCategory("");
    }
  }

  function applyValues(values: string[]) {
    onChange(values);
    handleOpenChange(false);
  }

  return (
    <div className="grid gap-1.5 text-sm font-medium text-foreground">
      <span>标签筛选</span>
      <Button
        aria-label={`标签筛选 ${summary}`}
        className="justify-start"
        disabled={disabled}
        onClick={() => handleOpenChange(true)}
        type="button"
        variant={selectedValues.length > 0 ? "default" : "outline"}
      >
        <Tag aria-hidden size={16} />
        <span>{summary}</span>
      </Button>
      <Dialog onOpenChange={handleOpenChange} open={open}>
        <DialogContent className="w-[min(calc(100vw-2rem),72rem)]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Tag aria-hidden size={18} />
              选择标签
            </DialogTitle>
            <DialogDescription>按分类或搜索筛选标签，并在右侧确认当前筛选条件。</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-[minmax(16rem,1fr)_repeat(4,minmax(5.5rem,7rem))] gap-3 max-lg:grid-cols-2">
              <label className="relative grid gap-1.5 text-sm font-medium text-foreground max-lg:col-span-2">
                <span className="sr-only">搜索标签</span>
                <Search aria-hidden className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                <Input
                  aria-label="搜索标签"
                  className="pl-9"
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="搜索标签名称 / 代码 / 分类"
                  type="search"
                  value={search}
                />
              </label>
              {[
                ["总数", options.length],
                ["筛选后", filteredOptions.length],
                ["已启用", activeCount],
                ["已选择", draftValues.length]
              ].map(([label, value]) => (
                <div className="rounded-md border bg-card px-3 py-2" key={label}>
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="font-mono text-xl font-semibold">{value}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-[13rem_minmax(0,1fr)_18rem] gap-4 max-xl:grid-cols-[12rem_minmax(0,1fr)] max-lg:grid-cols-1">
              <section className="rounded-md border bg-card p-3">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <Layers aria-hidden size={16} />
                  分类导航
                </div>
                <div className="grid gap-2">
                  <Button
                    className="justify-start"
                    onClick={() => setCategory("")}
                    type="button"
                    variant={category === "" ? "default" : "outline"}
                  >
                    <Layers aria-hidden size={16} />
                    全部
                  </Button>
                  {categories.map((item) => (
                    <Button
                      className="justify-start"
                      key={item}
                      onClick={() => setCategory(item)}
                      type="button"
                      variant={category === item ? "default" : "outline"}
                    >
                      <Layers aria-hidden size={16} />
                      {item}
                    </Button>
                  ))}
                </div>
              </section>
              <section className="rounded-md border bg-card p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Tag aria-hidden size={16} />
                    可选标签
                  </div>
                  <Badge variant="outline">按分类或搜索筛选</Badge>
                </div>
                <div className="grid max-h-[26rem] gap-2 overflow-y-auto pr-1">
                  {filteredOptions.length > 0 ? filteredOptions.map((tag) => {
                    const selected = selectedSet.has(tag.name);
                    const inactive = tag.is_active === false;
                    return (
                      <button
                        aria-label={`${selected ? "取消选择标签" : "选择标签"} ${tagDisplayName(tag)}`}
                        className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 rounded-md border bg-background px-3 py-2 text-left text-sm transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={inactive && !selected}
                        key={tag.name}
                        onClick={() => toggleTag(tag.name)}
                        type="button"
                      >
                        <span className="min-w-0 font-medium">{tagDisplayName(tag)}</span>
                        <Badge variant="outline">
                          <Folder aria-hidden size={13} />
                          {tagCategoryName(tag)}
                        </Badge>
                        <span className="grid size-8 place-items-center rounded-md bg-muted text-muted-foreground">
                          {selected ? <Check aria-hidden size={16} /> : <Plus aria-hidden size={16} />}
                        </span>
                      </button>
                    );
                  }) : (
                    <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">暂无匹配标签</div>
                  )}
                </div>
              </section>
              <section className="rounded-md border bg-card p-3 max-xl:col-span-2 max-lg:col-span-1">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Check aria-hidden size={16} />
                    已选择
                  </div>
                  <Badge variant="secondary">{draftValues.length} 项</Badge>
                </div>
                <p className="mb-3 text-sm text-muted-foreground">确认后写回当前页面的标签筛选条件。</p>
                {selectedTags.length > 0 ? (
                  <div className="grid max-h-[20rem] gap-2 overflow-y-auto pr-1">
                    {selectedTags.map((tag) => (
                      <div className="flex items-center justify-between gap-2 rounded-md border bg-background px-3 py-2" key={tag.name}>
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{tagDisplayName(tag)}</div>
                          <div className="truncate text-xs text-muted-foreground">{tagCategoryName(tag)}</div>
                        </div>
                        <Button aria-label={`移除标签 ${tagDisplayName(tag)}`} onClick={() => toggleTag(tag.name)} size="icon" type="button" variant="ghost">
                          ×
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid h-[14rem] place-items-center rounded-md border border-dashed text-sm text-muted-foreground">暂无选择的标签</div>
                )}
              </section>
            </div>
          </div>
          <DialogFooter className="items-center justify-between gap-2 sm:justify-between">
            <Button onClick={() => applyValues([])} type="button" variant="ghost">
              <RotateCcw aria-hidden size={16} />
              重置
            </Button>
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button onClick={() => handleOpenChange(false)} type="button" variant="outline">
                取消
              </Button>
              <Button onClick={() => applyValues(draftValues)} type="button">
                <Check aria-hidden size={16} />
                应用
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function instanceStatusLabel(item: InstanceListItem): string {
  if (item.deleted_at) {
    return "已删除";
  }
  return item.is_active ? "启用" : "禁用";
}

function auditStatusLabel(item: InstanceListItem): string {
  switch (item.audit_status) {
    case "enabled":
      return "已启用";
    case "configured_disabled":
      return "已配置未启用";
    default:
      return item.db_type?.toLowerCase() === "sqlserver" ? "未配置" : "不支持";
  }
}

function managedStatusLabel(item: InstanceListItem): string {
  return item.is_jumpserver_managed ? "已托管" : "未托管";
}

function backupStatusLabel(item: InstanceListItem): string {
  return backupStatusValueLabel(item.backup_status);
}

function backupStatusValueLabel(status: string | null | undefined): string {
  switch (status) {
    case "backed_up":
      return "已备份";
    case "backup_stale":
      return "备份异常";
    default:
      return "未备份";
  }
}

function accountAvailabilityText(isLocked: boolean, reasons: string[] = []): string {
  if (!isLocked) {
    return "正常";
  }
  return reasons.length > 0 ? `已锁定：${reasons.join("；")}` : "已锁定";
}

function availabilityLabel(item: AccountLedgerItem): string {
  return accountAvailabilityText(item.is_locked, item.availability_reasons);
}

function deletedLabel(value: boolean): string {
  return value ? "已删除" : "未删除";
}

function superuserLabel(value: boolean): string {
  return value ? "超管用户" : "普通用户";
}

function adStatusLabel(value: string | null | undefined): string {
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

function connectionStatusLabel(value: string | null | undefined): string {
  switch ((value ?? "").toLowerCase()) {
    case "ok":
    case "success":
    case "healthy":
    case "connected":
      return "连接正常";
    case "poor":
    case "warning":
    case "degraded":
      return "连接较差";
    case "failed":
    case "error":
    case "unreachable":
      return "连接失败";
    case "unknown":
    case "":
      return "未检测";
    default:
      return String(value);
  }
}

function classificationText(item: AccountLedgerItem): string {
  return item.classifications.map((classification) => classification.display_name).filter(Boolean).join(" ");
}

function PageHeader({
  title,
  legacyHref
}: {
  eyebrow?: string;
  title: string;
  description?: string;
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

function LoadingGrid() {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="列表加载中">
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
      <AlertDescription>列表数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function TagList({ tags }: { tags: TagItem[] }) {
  if (tags.length === 0) {
    return <span className="text-muted-foreground">无标签</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {tags.slice(0, 6).map((tag) => (
        <Badge variant="outline" key={tag.name}>
          {tag.display_name || tag.name}
        </Badge>
      ))}
    </div>
  );
}

function BadgeText({ value, variantValue }: { value: string; variantValue?: string }) {
  return <Badge variant={statusVariant(variantValue ?? value)}>{value}</Badge>;
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

function asNumber(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let size = Number(value);
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
}

function formatMegabytes(value: unknown, fallback = "无数据"): string {
  const mb = Number(value);
  if (!Number.isFinite(mb) || mb <= 0) {
    return fallback;
  }
  return formatBytes(mb * 1024 * 1024);
}

function recordsFromUnknown(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object") : [];
}

function snapshotRecords(snapshot: Record<string, unknown> | undefined, key: string): Array<Record<string, unknown>> {
  return recordsFromUnknown(snapshot?.[key]);
}

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">-</span>;
  }
  return (
    <pre className="max-h-56 overflow-auto rounded-md border bg-secondary/30 p-3 font-mono text-xs whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 rounded-md border bg-secondary/30 p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  );
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseTagNames(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function credentialOptionLabel(item: CredentialOptionItem): string {
  const dbType = item.db_type ? ` · ${item.db_type}` : "";
  const inactive = item.is_active === false ? " · 停用" : "";
  return `${item.name}${dbType}${inactive}`;
}

function matchesInstanceCredential(item: CredentialOptionItem, dbType: string): boolean {
  return item.credential_type === undefined || item.credential_type === null || item.credential_type === "database"
    ? !item.db_type || item.db_type === dbType
    : false;
}

function InstanceFormDialog({
  item,
  onOpenChange,
  onSaved,
  open
}: {
  item: InstanceListItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  open: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [dbType, setDbType] = useState(item?.db_type ?? "mysql");
  const [host, setHost] = useState(item?.host ?? "");
  const [port, setPort] = useState(String(item?.port ?? 3306));
  const [databaseName, setDatabaseName] = useState("");
  const [credentialId, setCredentialId] = useState(String((item as Record<string, unknown> | null)?.credential_id ?? ""));
  const [tagNames, setTagNames] = useState(item?.tags.map((tag) => tag.name).join(", ") ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const credentialOptionsQuery = useQuery({
    queryKey: ["list", "instance-form-credentials"],
    queryFn: () => fetchCredentialOptions()
  });
  const title = item ? `编辑实例 ${item.name}` : "新建实例";
  const credentialOptions = (credentialOptionsQuery.data ?? []).filter((credential) => matchesInstanceCredential(credential, dbType));

  function buildPayload(): InstanceWritePayload {
    return {
      name: name.trim(),
      db_type: dbType,
      host: host.trim(),
      port: Number(port),
      database_name: databaseName.trim() || null,
      credential_id: parseOptionalNumber(credentialId),
      description: description.trim() || null,
      tag_names: parseTagNames(tagNames),
      is_active: isActive
    };
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildPayload();
    const request = item ? updateInstance(item.id, payload) : createInstance(payload);
    void runAction(request, { success: item ? "实例已更新" : "实例已创建" }).then(onSaved);
  }

  function handleValidateConnectionParams() {
    void runAction(validateInstanceConnectionParams(buildPayload()), { success: "连接参数校验已通过" });
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>维护实例基础连接信息。连接测试仍可在列表操作中执行。</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <FormField label="实例名称">
              <Input onChange={(event) => setName(event.target.value)} required value={name} />
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
            <FormField label="主机/IP">
              <Input onChange={(event) => setHost(event.target.value)} required value={host} />
            </FormField>
            <FormField label="端口">
              <Input min={1} onChange={(event) => setPort(event.target.value)} required type="number" value={port} />
            </FormField>
            <FormField label="默认数据库">
              <Input onChange={(event) => setDatabaseName(event.target.value)} value={databaseName} />
            </FormField>
            <FormField label="凭据">
              <SelectControl
                disabled={credentialOptionsQuery.isLoading}
                label="凭据"
                onValueChange={setCredentialId}
                options={[
                  { label: "请选择凭据", value: "" },
                  ...credentialOptions.map((credential) => ({
                    label: credentialOptionLabel(credential),
                    value: String(credential.id),
                    disabled: credential.is_active === false
                  }))
                ]}
                value={credentialId}
              />
            </FormField>
            <FormField label="标签代码">
              <Input onChange={(event) => setTagNames(event.target.value)} placeholder="prod, core" value={tagNames} />
            </FormField>
            <SwitchField checked={isActive} label="状态" onCheckedChange={setIsActive} />
          </div>
          <FormField label="描述">
            <Textarea onChange={(event) => setDescription(event.target.value)} value={description} />
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="button" variant="outline" onClick={handleValidateConnectionParams}>
              <PlugZap aria-hidden size={16} />
              校验连接参数
            </Button>
            <Button type="submit">保存实例</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ListFrame({
  title,
  description,
  total,
  children
}: {
  title: string;
  description?: string;
  total: number;
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
          <Badge variant="secondary">共 {formatNumber(total)} 条</Badge>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function QueryPage<TItem>({
  result,
  isLoading,
  isError,
  onRetry,
  children
}: {
  result: PaginatedList<TItem> | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  children: (result: PaginatedList<TItem>) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {result ? children(result) : null}
    </>
  );
}

function InstanceImportDialog({
  onImported,
  onOpenChange,
  open
}: {
  onImported: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      return;
    }
    void runAction(importInstancesFromCsv(file), { success: "实例导入已提交" }).then(() => {
      setFile(null);
      onImported();
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>批量导入实例</DialogTitle>
            <DialogDescription>上传 CSV 文件批量创建实例。模板字段以 v1 导入模板为准。</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Button asChild variant="outline">
              <a href="/api/v1/instances/imports/template">
                <Download aria-hidden size={16} />
                <span>下载导入模板</span>
              </a>
            </Button>
            <label className="grid gap-1.5 text-sm font-medium text-foreground">
              <span>CSV 文件</span>
              <Input
                accept=".csv,text/csv"
                aria-label="CSV 文件"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                }}
                type="file"
              />
            </label>
            {file ? <p className="text-sm text-muted-foreground">已选择 {file.name}</p> : null}
          </div>
          <DialogFooter>
            <Button disabled={!file} type="submit">
              上传并创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type DatabaseTableSizesTarget = {
  id: number;
  database_name: string;
  instance?: { name?: string | null };
  capacity?: { collected_at?: string | null };
  collected_at?: string | null;
};

function DatabaseTableSizesDialog({
  item,
  onOpenChange,
  onRefresh
}: {
  item: DatabaseTableSizesTarget;
  onOpenChange: (open: boolean) => void;
  onRefresh: () => void;
}) {
  const query = useQuery({
    queryKey: ["lists", "database-ledgers", item.id, "table-sizes"],
    queryFn: () => fetchDatabaseTableSizes(item.id)
  });
  const data: DatabaseTableSizesResponse | undefined = query.data;

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent className="w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader>
          <DialogTitle>数据库表容量 {item.database_name}</DialogTitle>
          <DialogDescription>
            {item.instance?.name ?? "当前实例"} · {formatShortTimestamp(data?.collected_at ?? item.capacity?.collected_at ?? item.collected_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Schema</TableHead>
                <TableHead>表名</TableHead>
                <TableHead>总大小</TableHead>
                <TableHead>数据</TableHead>
                <TableHead>索引</TableHead>
                <TableHead>行数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.tables.length === 0 ? (
                <TableRow>
                  <TableCell className="py-8 text-center text-sm text-muted-foreground" colSpan={6}>
                    暂无表容量数据
                  </TableCell>
                </TableRow>
              ) : null}
              {(data?.tables ?? []).map((table: DatabaseTableSizeItem) => (
                <TableRow key={`${table.schema_name ?? "-"}-${table.table_name}`}>
                  <TableCell>{table.schema_name ?? "-"}</TableCell>
                  <TableCell className="font-medium">{table.table_name}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.data_size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.index_size_mb)}</TableCell>
                  <TableCell className="font-mono text-xs">{asText(table.row_count)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <DialogFooter>
          <Button onClick={onRefresh} type="button">
            刷新表容量 {item.database_name}
          </Button>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountPermissionsDialog({ item, onOpenChange }: { item: AccountLedgerItem; onOpenChange: (open: boolean) => void }) {
  const query = useQuery({
    queryKey: ["lists", "account-ledgers", item.id, "permissions"],
    queryFn: () => fetchAccountPermissions(item.id)
  });
  const data: AccountPermissionsResponse | undefined = query.data;
  const snapshot = data?.permissions.snapshot as { roles?: unknown } | undefined;
  const roles = Array.isArray(snapshot?.roles) ? snapshot.roles.map((role) => asText(role)).filter((role) => role !== "-") : [];

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>权限详情 {data?.account.username ?? item.username}</DialogTitle>
          <DialogDescription>
            {item.instance_name} · {dbTypeLabel(data?.permissions.db_type ?? item.db_type)}
          </DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <DetailField label="账户">{data?.account.username ?? item.username}</DetailField>
          <DetailField label="是否超管">{data?.permissions.is_superuser ? "是" : "否"}</DetailField>
          <DetailField label="最后同步">{formatShortTimestamp(data?.permissions.last_sync_time)}</DetailField>
          <DetailField label="角色">
            {roles.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {roles.map((role) => (
                  <Badge key={role} variant="outline">
                    {role}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </DetailField>
        </dl>
        <JsonBlock value={data?.permissions.snapshot} />
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountChangeHistoryDialog({ item, onOpenChange }: { item: AccountLedgerItem; onOpenChange: (open: boolean) => void }) {
  const query = useQuery({
    queryKey: ["lists", "account-ledgers", item.id, "change-history"],
    queryFn: () => fetchAccountChangeHistory(item.id)
  });
  const data: AccountChangeHistoryResponse | undefined = query.data;

  return (
    <Dialog onOpenChange={onOpenChange} open>
      <DialogContent className="w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader>
          <DialogTitle>变更历史 {data?.account.username ?? item.username}</DialogTitle>
          <DialogDescription>账户权限与状态变更记录。</DialogDescription>
        </DialogHeader>
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>摘要</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.history ?? []).map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono text-xs">{formatShortTimestamp(record.change_time)}</TableCell>
                  <TableCell>{asText(record.change_type)}</TableCell>
                  <TableCell>
                    <BadgeText value={asText(record.status)} />
                  </TableCell>
                  <TableCell>{asText(record.message)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
            关闭详情
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function InstanceConnectionStatusCard({
  data,
  isLoading,
  isError,
  onRetry
}: {
  data?: InstanceConnectionStatus;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>连接状态</CardTitle>
        <CardDescription>来自实例连接状态接口的最近连接信号。</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {isLoading ? <Skeleton className="h-24 w-full" /> : null}
        {isError ? <ErrorState onRetry={onRetry} /> : null}
        {data ? (
          <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            <DetailField label="当前状态">
              <BadgeText value={connectionStatusLabel(data.status)} variantValue={asText(data.status)} />
            </DetailField>
            <DetailField label="启用状态">{data.is_active ? "启用" : "停用"}</DetailField>
            <DetailField label="主机/IP">
              {data.host}:{data.port}
            </DetailField>
            <DetailField label="最近连接">{formatShortTimestamp(data.last_connected)}</DetailField>
          </dl>
        ) : null}
      </CardContent>
    </Card>
  );
}

function InstanceAuditInfoPanel({
  data,
  isLoading,
  isError,
  onRetry
}: {
  data?: InstanceAuditInfo;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  const facts = data?.facts ?? {};
  const serverAudits = snapshotRecords(data?.snapshot, "server_audits");
  const serverSpecs = snapshotRecords(data?.snapshot, "audit_specifications");
  const databaseSpecs = snapshotRecords(data?.snapshot, "database_audit_specifications");
  const specs = [...serverSpecs, ...databaseSpecs];

  return (
    <section className="grid gap-4">
      <div className="grid gap-1">
        <h3 className="font-display text-base font-semibold leading-none tracking-normal">审计信息</h3>
        <p className="text-sm text-muted-foreground">审计目标、审计规范和覆盖数据库概览。</p>
      </div>
        {isLoading ? <Skeleton className="h-28 w-full" /> : null}
        {isError ? <ErrorState onRetry={onRetry} /> : null}
        {data && !data.supported ? (
          <Alert>
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>{data.message ?? "当前实例暂不支持审计采集。"}</AlertDescription>
          </Alert>
        ) : null}
        {data && data.supported && !data.available ? (
          <Alert>
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>{data.message ?? "尚未采集审计信息。"}</AlertDescription>
          </Alert>
        ) : null}
        {data ? (
          <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            <DetailField label="审计目标数">{formatNumber(asNumber(facts.audit_count))}</DetailField>
            <DetailField label="已启用审计">{formatNumber(asNumber(facts.enabled_audit_count))}</DetailField>
            <DetailField label="规范总数">{formatNumber(asNumber(facts.specification_count))}</DetailField>
            <DetailField label="覆盖数据库数">{formatNumber(asNumber(facts.covered_database_count))}</DetailField>
          </dl>
        ) : null}
        {serverAudits.length > 0 ? (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold">审计目标</h3>
            <div className="overflow-hidden rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>目标</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {serverAudits.map((item, index) => (
                    <TableRow key={`${asText(item.name)}-${index}`}>
                      <TableCell className="font-medium">{asText(item.name)}</TableCell>
                      <TableCell>
                        <BadgeText value={item.is_state_enabled ? "启用" : "停用"} />
                      </TableCell>
                      <TableCell>{asText(item.audit_file_path ?? item.queue_delay ?? item.type_desc)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
        {specs.length > 0 ? (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold">审计规范</h3>
            <div className="overflow-hidden rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>数据库</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {specs.map((item, index) => (
                    <TableRow key={`${asText(item.name)}-${index}`}>
                      <TableCell className="font-medium">{asText(item.name)}</TableCell>
                      <TableCell>{asText(item.database_name)}</TableCell>
                      <TableCell>
                        <BadgeText value={item.is_state_enabled ? "启用" : "停用"} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
    </section>
  );
}

function InstanceBackupInfoPanel({
  data,
  isLoading,
  isError,
  onRetry
}: {
  data?: InstanceBackupInfo;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  const restorePoints: InstanceBackupRestorePoint[] = data?.restore_points ?? [];
  const coverage = data?.backup_metrics_coverage;
  const coverageText = coverage ? `${formatNumber(coverage.enriched_restore_point_count)} / ${formatNumber(coverage.expected_restore_point_count)}` : "-";
  const sourceText = [data?.source_name, data?.source_server_host].map((value) => asText(value, "")).filter(Boolean).join(" / ") || "-";

  return (
    <section className="grid gap-4">
      <div className="grid gap-1">
        <h3 className="font-display text-base font-semibold leading-none tracking-normal">备份信息</h3>
        <p className="text-sm text-muted-foreground">Veeam 匹配结果、最近备份时间和恢复点明细。</p>
      </div>
        {isLoading ? <Skeleton className="h-28 w-full" /> : null}
        {isError ? <ErrorState onRetry={onRetry} /> : null}
        {data && restorePoints.length === 0 ? (
          <Alert>
            <AlertCircle aria-hidden size={16} />
            <AlertDescription>{data.message ?? "尚未采集到匹配该实例的备份记录。"}</AlertDescription>
          </Alert>
        ) : null}
        {data ? (
          <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            <DetailField label="备份状态">
              <BadgeText value={backupStatusValueLabel(data.backup_status)} variantValue={data.backup_status} />
            </DetailField>
            <DetailField label="最近备份时间">{formatShortTimestamp(data.backup_last_time)}</DetailField>
            <DetailField label="备份链完整大小">{formatBytes(data.backup_chain_size_bytes)}</DetailField>
            <DetailField label="恢复点数量">{formatNumber(data.restore_point_count ?? restorePoints.length)}</DetailField>
            <DetailField label="Backup ID">{asText(data.backup_id)}</DetailField>
            <DetailField label="覆盖数量">{coverageText}</DetailField>
            <DetailField label="平台">{sourceText}</DetailField>
            <DetailField label="源记录">{asText(data.source_record_id ?? data.backup_file_id)}</DetailField>
          </dl>
        ) : null}
        {data ? (
          <dl className="grid grid-cols-3 gap-3 max-lg:grid-cols-1">
            <DetailField label="匹配机器">{asText(data.matched_machine_name)}</DetailField>
            <DetailField label="备份任务">{asText(data.job_name)}</DetailField>
            <DetailField label="最近同步">{formatShortTimestamp(data.last_sync_time)}</DetailField>
          </dl>
        ) : null}
        {restorePoints.length > 0 ? (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold">恢复点明细</h3>
            <div className="overflow-hidden rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>恢复点</TableHead>
                    <TableHead>Backup ID</TableHead>
                    <TableHead>备份方式</TableHead>
                    <TableHead>数据大小</TableHead>
                    <TableHead>备份大小</TableHead>
                    <TableHead>压缩率</TableHead>
                    <TableHead>创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {restorePoints.map((item, index) => (
                    <TableRow key={`${item.id ?? item.name ?? "restore-point"}-${index}`}>
                      <TableCell className="font-medium">{asText(item.name ?? item.id)}</TableCell>
                      <TableCell className="font-mono text-xs">{asText(item.backup_id)}</TableCell>
                      <TableCell>{asText(item.type)}</TableCell>
                      <TableCell className="font-mono text-xs">{formatBytes(item.data_size_bytes)}</TableCell>
                      <TableCell className="font-mono text-xs">{formatBytes(item.backup_size_bytes ?? item.data_size_bytes)}</TableCell>
                      <TableCell className="font-mono text-xs">{item.compress_ratio === null || item.compress_ratio === undefined ? "-" : `${item.compress_ratio}%`}</TableCell>
                      <TableCell className="font-mono text-xs">{formatShortTimestamp(item.creation_time)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
    </section>
  );
}

function typeSpecificText(item: AccountLedgerItem, key: string): string {
  return asText(item.type_specific?.[key]);
}

function buildAgListenerLabel(item: InstanceAgAccountItem): string {
  const parts = [item.listener_name, item.listener_host].map((value) => asText(value, "")).filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "-";
}

function createInstanceAccountsColumns({
  onShowHistory,
  onShowPermissions
}: {
  onShowHistory: (item: AccountLedgerItem) => void;
  onShowPermissions: (item: AccountLedgerItem) => void;
}): ColumnDef<AccountLedgerItem>[] {
  return [
    {
      accessorKey: "id",
      header: "ID",
      cell: ({ row }) => <Badge variant="outline">{row.original.id}</Badge>
    },
    {
      accessorFn: (item) => `${item.username} ${typeSpecificText(item, "host")}`,
      id: "username",
      header: "账户",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.username}</div>
          {typeSpecificText(row.original, "host") !== "-" ? (
            <div className="mt-1 text-xs text-muted-foreground">@{typeSpecificText(row.original, "host")}</div>
          ) : null}
        </div>
      )
    },
    {
      accessorFn: (item) => typeSpecificText(item, "plugin"),
      id: "plugin",
      header: "插件",
      cell: ({ row }) => <span className="font-mono text-xs">{typeSpecificText(row.original, "plugin")}</span>
    },
    {
      accessorFn: (item) => typeSpecificText(item, "account_kind"),
      id: "account_kind",
      header: "类型",
      cell: ({ row }) => <Badge variant="outline">{typeSpecificText(row.original, "account_kind")}</Badge>
    },
    {
      accessorFn: availabilityLabel,
      id: "is_locked",
      header: "是否可用",
      cell: ({ row }) => <BadgeText value={availabilityLabel(row.original)} variantValue={row.original.is_locked ? "locked" : "正常"} />
    },
    {
      accessorFn: (item) => deletedLabel(item.is_deleted),
      id: "is_deleted",
      header: "是否删除",
      cell: ({ row }) => <BadgeText value={deletedLabel(row.original.is_deleted)} variantValue={row.original.is_deleted ? "deleted" : undefined} />
    },
    {
      accessorFn: (item) => superuserLabel(item.is_superuser),
      id: "is_superuser",
      header: "是否超管",
      cell: ({ row }) => <Badge variant={row.original.is_superuser ? "outline" : "secondary"}>{superuserLabel(row.original.is_superuser)}</Badge>
    },
    {
      accessorFn: (item) => formatShortTimestamp(item.last_change_time),
      id: "last_change_time",
      header: "最后变更",
      cell: ({ row }) => <span className="font-mono text-xs">{formatShortTimestamp(row.original.last_change_time)}</span>
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-2">
          <Button aria-label={`查看权限 ${row.original.username}`} onClick={() => onShowPermissions(row.original)} size="sm" type="button" variant="outline">
            查看权限
          </Button>
          <Button aria-label={`变更历史 ${row.original.username}`} onClick={() => onShowHistory(row.original)} size="sm" type="button" variant="outline">
            变更历史
          </Button>
        </div>
      )
    }
  ];
}

function createInstanceAgAccountsColumns(): ColumnDef<InstanceAgAccountItem>[] {
  return [
    {
      accessorKey: "id",
      header: "ID",
      cell: ({ row }) => <Badge variant="outline">{row.original.id}</Badge>
    },
    {
      accessorFn: (item) => asText(item.availability_group_name),
      id: "availability_group_name",
      header: "AG",
      cell: ({ row }) => <span className="font-medium">{asText(row.original.availability_group_name)}</span>
    },
    {
      accessorFn: buildAgListenerLabel,
      id: "listener",
      header: "监听器",
      cell: ({ row }) => <span className="font-mono text-xs">{buildAgListenerLabel(row.original)}</span>
    },
    {
      accessorKey: "username",
      header: "账户",
      cell: ({ row }) => <span className="font-medium">{row.original.username}</span>
    },
    {
      accessorFn: (item) => accountAvailabilityText(item.is_locked, item.availability_reasons),
      id: "is_locked",
      header: "是否可用",
      cell: ({ row }) => (
        <BadgeText
          value={accountAvailabilityText(row.original.is_locked, row.original.availability_reasons)}
          variantValue={row.original.is_locked ? "locked" : "正常"}
        />
      )
    },
    {
      accessorFn: (item) => deletedLabel(item.is_deleted),
      id: "is_deleted",
      header: "是否删除",
      cell: ({ row }) => <BadgeText value={deletedLabel(row.original.is_deleted)} variantValue={row.original.is_deleted ? "deleted" : undefined} />
    },
    {
      accessorFn: (item) => superuserLabel(item.is_superuser),
      id: "is_superuser",
      header: "是否超管",
      cell: ({ row }) => <Badge variant={row.original.is_superuser ? "outline" : "secondary"}>{superuserLabel(row.original.is_superuser)}</Badge>
    },
    {
      accessorFn: (item) => formatShortTimestamp(item.last_change_time ?? item.last_sync_time),
      id: "last_change_time",
      header: "最后变更",
      cell: ({ row }) => <span className="font-mono text-xs">{formatShortTimestamp(row.original.last_change_time ?? row.original.last_sync_time)}</span>
    }
  ];
}

function createInstanceDatabaseSizeColumns({ onShowTableSizes }: { onShowTableSizes: (item: InstanceDatabaseSizeItem) => void }): ColumnDef<InstanceDatabaseSizeItem>[] {
  return [
    {
      accessorFn: (item) => item.database_name,
      id: "database_name",
      header: "数据库名称",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Database aria-hidden className={row.original.is_active ? "text-primary" : "text-muted-foreground"} size={16} />
          <span className={row.original.is_active ? "font-medium" : "font-medium text-muted-foreground"}>{row.original.database_name}</span>
        </div>
      )
    },
    {
      accessorFn: (item) => formatMegabytes(item.size_mb),
      id: "size_mb",
      header: "总大小",
      cell: ({ row }) => <span className="font-mono text-xs">{formatMegabytes(row.original.size_mb)}</span>
    },
    {
      accessorFn: (item) => `${formatMegabytes(item.data_size_mb, "-")} / ${formatMegabytes(item.log_size_mb, "-")}`,
      id: "data_log_size",
      header: "数据 / 日志",
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {formatMegabytes(row.original.data_size_mb, "-")} / {formatMegabytes(row.original.log_size_mb, "-")}
        </span>
      )
    },
    {
      accessorFn: (item) => (item.is_active ? "在线" : "已删除"),
      id: "is_active",
      header: "状态",
      cell: ({ row }) => <BadgeText value={row.original.is_active ? "在线" : "已删除"} variantValue={row.original.is_active ? "正常" : "deleted"} />
    },
    {
      accessorFn: (item) => formatShortTimestamp(item.collected_at),
      id: "collected_at",
      header: "采集时间",
      cell: ({ row }) => <span className="font-mono text-xs">{formatShortTimestamp(row.original.collected_at)}</span>
    },
    {
      accessorFn: (item) => `${asText(item.last_seen_date)} ${asText(item.deleted_at)}`,
      id: "inactive_meta",
      header: "最近出现 / 隐藏时间",
      cell: ({ row }) => (
        <div className="grid gap-1 text-xs text-muted-foreground">
          <span>最后出现：{asText(row.original.last_seen_date)}</span>
          <span>隐藏时间：{formatShortTimestamp(row.original.deleted_at)}</span>
        </div>
      )
    },
    {
      id: "actions",
      header: "操作",
      cell: ({ row }) => (
        <Button
          aria-label={`表容量 ${row.original.database_name}`}
          disabled={typeof row.original.id !== "number"}
          onClick={() => {
            if (typeof row.original.id === "number") {
              onShowTableSizes(row.original);
            }
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          表容量
        </Button>
      )
    }
  ];
}

function DataTabState({ isError, isLoading, onRetry }: { isError: boolean; isLoading: boolean; onRetry: () => void }) {
  if (isLoading) {
    return <Skeleton className="h-28 w-full" />;
  }
  if (isError) {
    return <ErrorState onRetry={onRetry} />;
  }
  return null;
}

function InstanceDataTabsCard({
  accountsData,
  accountsError,
  accountsLoading,
  agAccountsData,
  agAccountsError,
  agAccountsLoading,
  auditData,
  auditError,
  auditLoading,
  backupData,
  backupError,
  backupLoading,
  databaseSizesData,
  databaseSizesError,
  databaseSizesLoading,
  onRetryAccounts,
  onRetryAgAccounts,
  onRetryAudit,
  onRetryBackup,
  onRetryDatabaseSizes,
  showAgAccounts
}: {
  accountsData?: PaginatedList<AccountLedgerItem>;
  accountsError: boolean;
  accountsLoading: boolean;
  agAccountsData?: InstanceAgAccountsResponse;
  agAccountsError: boolean;
  agAccountsLoading: boolean;
  auditData?: InstanceAuditInfo;
  auditError: boolean;
  auditLoading: boolean;
  backupData?: InstanceBackupInfo;
  backupError: boolean;
  backupLoading: boolean;
  databaseSizesData?: InstanceDatabaseSizesResponse;
  databaseSizesError: boolean;
  databaseSizesLoading: boolean;
  onRetryAccounts: () => void;
  onRetryAgAccounts: () => void;
  onRetryAudit: () => void;
  onRetryBackup: () => void;
  onRetryDatabaseSizes: () => void;
  showAgAccounts: boolean;
}) {
  const [permissionsAccount, setPermissionsAccount] = useState<AccountLedgerItem | null>(null);
  const [historyAccount, setHistoryAccount] = useState<AccountLedgerItem | null>(null);
  const [tableSizeDatabase, setTableSizeDatabase] = useState<InstanceDatabaseSizeItem | null>(null);
  const accountColumns = useMemo(
    () => createInstanceAccountsColumns({ onShowHistory: setHistoryAccount, onShowPermissions: setPermissionsAccount }),
    []
  );
  const agAccountColumns = useMemo(() => createInstanceAgAccountsColumns(), []);
  const databaseSizeColumns = useMemo(() => createInstanceDatabaseSizeColumns({ onShowTableSizes: setTableSizeDatabase }), []);
  const databases = databaseSizesData?.databases ?? [];
  const tableSizeTarget =
    tableSizeDatabase && typeof tableSizeDatabase.id === "number"
      ? {
          ...tableSizeDatabase,
          id: tableSizeDatabase.id
        }
      : null;
  const accounts = accountsData?.items ?? [];
  const activeAccounts = accounts.filter((item) => item.is_active && !item.is_deleted).length;
  const superuserAccounts = accounts.filter((item) => item.is_superuser).length;
  const deletedAccounts = accounts.filter((item) => item.is_deleted).length;
  const agAccounts = agAccountsData?.items ?? [];
  const activeAgAccounts = agAccounts.filter((item) => item.is_active && !item.is_deleted).length;
  const activeDatabases = databaseSizesData?.active_count ?? databases.filter((item) => item.is_active).length;
  const deletedDatabases = Math.max((databaseSizesData?.total ?? databases.length) - activeDatabases, 0);
  const tabsListClass = showAgAccounts
    ? "grid h-auto w-full grid-cols-5 max-xl:grid-cols-3 max-md:grid-cols-2"
    : "grid h-auto w-full grid-cols-4 max-xl:grid-cols-2";

  return (
    <Card>
      <CardContent className="grid gap-4">
        <Tabs defaultValue="accounts">
          <TabsList className={tabsListClass}>
            <TabsTrigger value="accounts">
              <Users aria-hidden size={16} />
              <span>账户信息</span>
            </TabsTrigger>
            {showAgAccounts ? (
              <TabsTrigger value="ag-accounts">
                <Layers aria-hidden size={16} />
                <span>账户信息（AG）</span>
              </TabsTrigger>
            ) : null}
            <TabsTrigger value="capacity">
              <Database aria-hidden size={16} />
              <span>容量信息</span>
            </TabsTrigger>
            <TabsTrigger value="audit">
              <ShieldCheck aria-hidden size={16} />
              <span>审计信息</span>
            </TabsTrigger>
            <TabsTrigger value="backup">
              <HardDrive aria-hidden size={16} />
              <span>备份信息</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent className="grid gap-4" value="accounts">
            <DataTabState isLoading={accountsLoading} isError={accountsError} onRetry={onRetryAccounts} />
            {accountsData ? (
              <>
                <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
                  <DetailField label="账户总数">{formatNumber(accountsData.total)}</DetailField>
                  <DetailField label="活跃账户">{formatNumber(activeAccounts)}</DetailField>
                  <DetailField label="超管账户">{formatNumber(superuserAccounts)}</DetailField>
                  <DetailField label="已删除账户">{formatNumber(deletedAccounts)}</DetailField>
                </dl>
                <DataTable
                  columns={accountColumns}
                  data={accountsData.items}
                  emptyText="暂无账户信息"
                  filters={[
                    { columnId: "is_locked", label: "是否可用", options: [{ label: "正常", value: "正常" }, { label: "已锁定", value: "已锁定" }] },
                    { columnId: "is_deleted", label: "是否删除", options: [{ label: "未删除", value: "未删除" }, { label: "已删除", value: "已删除" }] },
                    { columnId: "is_superuser", label: "是否超管", options: [{ label: "超管用户", value: "超管用户" }, { label: "普通用户", value: "普通用户" }] }
                  ]}
                  searchPlaceholder="搜索账户、插件、类型"
                />
              </>
            ) : null}
          </TabsContent>

          {showAgAccounts ? (
            <TabsContent className="grid gap-4" value="ag-accounts">
              <DataTabState isLoading={agAccountsLoading} isError={agAccountsError} onRetry={onRetryAgAccounts} />
              {agAccountsData ? (
                <>
                  <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
                    <DetailField label="AG账户总数">{formatNumber(agAccountsData.total)}</DetailField>
                    <DetailField label="AG活跃账户">{formatNumber(activeAgAccounts)}</DetailField>
                    <DetailField label="AG超管账户">{formatNumber(agAccounts.filter((item) => item.is_superuser).length)}</DetailField>
                    <DetailField label="AG已删除账户">{formatNumber(agAccounts.filter((item) => item.is_deleted).length)}</DetailField>
                  </dl>
                  <DataTable
                    columns={agAccountColumns}
                    data={agAccountsData.items}
                    emptyText="暂无 AG 账户信息"
                    filters={[
                      { columnId: "is_locked", label: "是否可用", options: [{ label: "正常", value: "正常" }, { label: "已锁定", value: "已锁定" }] },
                      { columnId: "is_deleted", label: "是否删除", options: [{ label: "未删除", value: "未删除" }, { label: "已删除", value: "已删除" }] },
                      { columnId: "is_superuser", label: "是否超管", options: [{ label: "超管用户", value: "超管用户" }, { label: "普通用户", value: "普通用户" }] }
                    ]}
                    searchPlaceholder="搜索 AG、监听器、账户"
                  />
                </>
              ) : null}
            </TabsContent>
          ) : null}

          <TabsContent className="grid gap-4" value="capacity">
            <DataTabState isLoading={databaseSizesLoading} isError={databaseSizesError} onRetry={onRetryDatabaseSizes} />
            {databaseSizesData ? (
              <>
                <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
                  <DetailField label="数据库总数">{formatNumber(databaseSizesData.total)}</DetailField>
                  <DetailField label="当前数据库">{formatNumber(activeDatabases)}</DetailField>
                  <DetailField label="删除数据库">{formatNumber(deletedDatabases)}</DetailField>
                  <DetailField label="容量总量">{formatMegabytes(databaseSizesData.total_size_mb, "-")}</DetailField>
                </dl>
                <DataTable
                  columns={databaseSizeColumns}
                  data={databases}
                  emptyText="暂无数据库容量信息"
                  filters={[{ columnId: "is_active", label: "状态", options: [{ label: "在线", value: "在线" }, { label: "已删除", value: "已删除" }] }]}
                  searchPlaceholder="搜索数据库名称、状态"
                />
              </>
            ) : null}
          </TabsContent>
          <TabsContent className="grid gap-4" value="audit">
            <InstanceAuditInfoPanel data={auditData} isLoading={auditLoading} isError={auditError} onRetry={onRetryAudit} />
          </TabsContent>
          <TabsContent className="grid gap-4" value="backup">
            <InstanceBackupInfoPanel data={backupData} isLoading={backupLoading} isError={backupError} onRetry={onRetryBackup} />
          </TabsContent>
        </Tabs>
      </CardContent>
      {permissionsAccount ? <AccountPermissionsDialog item={permissionsAccount} onOpenChange={() => setPermissionsAccount(null)} /> : null}
      {historyAccount ? <AccountChangeHistoryDialog item={historyAccount} onOpenChange={() => setHistoryAccount(null)} /> : null}
      {tableSizeTarget ? (
        <DatabaseTableSizesDialog
          item={tableSizeTarget}
          onOpenChange={() => setTableSizeDatabase(null)}
          onRefresh={() => {
            void runAction(refreshDatabaseTableSizes(tableSizeTarget.id), { success: "表容量已刷新" }).then(() => onRetryDatabaseSizes());
          }}
        />
      ) : null}
    </Card>
  );
}

function createInstanceColumns({
  onDelete,
  onEdit,
  onRestore,
  onSelectedChange,
  selectedIds
}: {
  onDelete: (item: InstanceListItem) => void;
  onEdit: (item: InstanceListItem) => void;
  onRestore: (item: InstanceListItem) => void;
  onSelectedChange: (id: number, selected: boolean) => void;
  selectedIds: Set<number>;
}): ColumnDef<InstanceListItem>[] {
  return [
  {
    id: "select",
    header: "选择",
    cell: ({ row }) => (
      <Checkbox
        aria-label={`选择实例 ${row.original.name}`}
        checked={selectedIds.has(row.original.id)}
        onCheckedChange={(checked) => onSelectedChange(row.original.id, checked === true)}
      />
    )
  },
  {
    accessorKey: "name",
    header: "名称",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="mt-1 text-xs text-muted-foreground">ID {row.original.id}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => `${item.host}:${item.port}`,
    id: "host",
    header: "主机/IP",
    cell: ({ row }) => (
      <div className="font-mono text-xs">
        {row.original.host}:{row.original.port}
      </div>
    )
  },
  {
    accessorFn: instanceStatusLabel,
    id: "status",
    header: "状态",
    cell: ({ row }) => <BadgeText value={instanceStatusLabel(row.original)} />
  },
  {
    accessorFn: auditStatusLabel,
    id: "audit_status",
    header: "审计",
    cell: ({ row }) => <BadgeText value={auditStatusLabel(row.original)} variantValue={row.original.audit_status} />
  },
  {
    accessorFn: managedStatusLabel,
    id: "managed_status",
    header: "已托管",
    cell: ({ row }) => <BadgeText value={managedStatusLabel(row.original)} />
  },
  {
    accessorFn: backupStatusLabel,
    id: "backup_status",
    header: "备份",
    cell: ({ row }) => <BadgeText value={backupStatusLabel(row.original)} variantValue={row.original.backup_status} />
  },
  {
    accessorFn: (item) => `${item.active_db_count}/${item.active_account_count}`,
    id: "active_counts",
    header: "活跃",
    cell: ({ row }) => (
      <div className="grid gap-1 text-xs text-muted-foreground">
        <span>数据库 {formatNumber(row.original.active_db_count)}</span>
        <span>账户 {formatNumber(row.original.active_account_count)}</span>
      </div>
    )
  },
  {
    accessorFn: (item) => `${item.main_version ?? "未检测"} ${formatShortTimestamp(item.last_sync_time)}`,
    id: "version_sync",
    header: "版本 / 同步",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.main_version || "未检测"}</div>
        <div className="mt-1 text-xs text-muted-foreground">{formatShortTimestamp(row.original.last_sync_time)}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-2">
        <Button asChild size="sm" variant="outline">
          <a aria-label={`查看详情 ${row.original.id}`} href={`/console/instances/${row.original.id}`}>
            <Eye aria-hidden size={14} />
            <span>详情</span>
          </a>
        </Button>
        <Button aria-label={`编辑实例 ${row.original.id}`} onClick={() => onEdit(row.original)} size="sm" type="button" variant="outline">
          <Pencil aria-hidden size={14} />
          <span>编辑</span>
        </Button>
        <Button
          aria-label={`测试连接 ${row.original.id}`}
          onClick={() => {
            void runAction(testInstanceConnection(row.original.id), { success: "连接测试已完成" });
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          <PlugZap aria-hidden size={14} />
          <span>测试</span>
        </Button>
        {row.original.deleted_at ? (
          <Button aria-label={`恢复实例 ${row.original.id}`} onClick={() => onRestore(row.original)} size="sm" type="button" variant="outline">
            <RotateCcw aria-hidden size={14} />
            <span>恢复</span>
          </Button>
        ) : (
          <Button aria-label={`删除实例 ${row.original.id}`} onClick={() => onDelete(row.original)} size="sm" type="button" variant="outline">
            <Trash2 aria-hidden size={14} />
            <span>删除</span>
          </Button>
        )}
      </div>
    )
  }
  ];
}

function createDatabaseLedgerColumns({
  onViewTables
}: {
  onViewTables: (item: DatabaseLedgerItem) => void;
}): ColumnDef<DatabaseLedgerItem>[] {
  return [
  {
    accessorFn: (item) => `${item.database_name} ${item.instance.name} ${item.instance.host}`,
    id: "database_name",
    header: "数据库/实例",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.database_name}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {row.original.instance.name} · {row.original.instance.host}
        </div>
      </div>
    )
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => item.capacity.label || "未采集",
    id: "capacity",
    header: "数据库大小",
    cell: ({ row }) => (
      <div>
        <div className="font-mono text-xs font-medium">{row.original.capacity.label || "未采集"}</div>
        <div className="mt-1 text-xs text-muted-foreground">{formatShortTimestamp(row.original.capacity.collected_at)}</div>
      </div>
    )
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <Button aria-label={`查看容量趋势 ${row.original.id}`} onClick={() => onViewTables(row.original)} size="sm" type="button" variant="outline">
        <ExternalLink aria-hidden size={14} />
        <span>趋势</span>
      </Button>
    )
  }
  ];
}

function createAccountLedgerColumns({
  onViewHistory,
  onViewPermissions
}: {
  onViewHistory: (item: AccountLedgerItem) => void;
  onViewPermissions: (item: AccountLedgerItem) => void;
}): ColumnDef<AccountLedgerItem>[] {
  return [
  {
    accessorFn: (item) => `${item.username} ${item.instance_name} ${item.instance_host}`,
    id: "username",
    header: "账户/实例",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.username}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {row.original.instance_name} · {row.original.instance_host}
        </div>
      </div>
    )
  },
  {
    accessorFn: availabilityLabel,
    id: "is_locked",
    header: "是否可用",
    cell: ({ row }) => <BadgeText value={availabilityLabel(row.original)} variantValue={row.original.is_locked ? "locked" : "正常"} />
  },
  {
    accessorFn: (item) => deletedLabel(item.is_deleted),
    id: "is_deleted",
    header: "是否删除",
    cell: ({ row }) => <BadgeText value={deletedLabel(row.original.is_deleted)} variantValue={row.original.is_deleted ? "deleted" : undefined} />
  },
  {
    accessorFn: (item) => superuserLabel(item.is_superuser),
    id: "is_superuser",
    header: "是否超管",
    cell: ({ row }) => <Badge variant={row.original.is_superuser ? "outline" : "secondary"}>{superuserLabel(row.original.is_superuser)}</Badge>
  },
  {
    accessorFn: (item) => adStatusLabel(item.ad_status),
    id: "ad_status",
    header: "AD状态",
    cell: ({ row }) => <Badge variant="outline">{adStatusLabel(row.original.ad_status)}</Badge>
  },
  {
    accessorFn: classificationText,
    id: "classifications",
    header: "分类",
    cell: ({ row }) => {
      const labels = row.original.classifications.map((classification) => classification.display_name).filter(Boolean);
      return labels.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {labels.map((label) => (
            <Badge variant="outline" key={label}>
              {label}
            </Badge>
          ))}
        </div>
      ) : (
        <span className="text-muted-foreground">未分类</span>
      );
    }
  },
  {
    accessorFn: (item) => dbTypeLabel(item.db_type),
    id: "db_type",
    header: "类型",
    cell: ({ getValue }) => <Badge variant="outline">{String(getValue())}</Badge>
  },
  {
    accessorFn: (item) => tagsText(item.tags),
    id: "tags",
    header: "标签",
    cell: ({ row }) => <TagList tags={row.original.tags} />
  },
  {
    id: "actions",
    header: "操作",
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-2">
        <Button aria-label={`查看权限 ${row.original.id}`} onClick={() => onViewPermissions(row.original)} size="sm" type="button" variant="outline">
          <Eye aria-hidden size={14} />
          <span>权限</span>
        </Button>
        <Button aria-label={`查看变更历史 ${row.original.id}`} onClick={() => onViewHistory(row.original)} size="sm" type="button" variant="outline">
          <ExternalLink aria-hidden size={14} />
          <span>变更</span>
        </Button>
      </div>
    )
  }
  ];
}

function resolveInstanceRouteId(instanceId?: number): number {
  if (typeof instanceId === "number" && Number.isFinite(instanceId)) {
    return instanceId;
  }
  return 0;
}

export function InstanceDetailPage({ instanceId }: { instanceId?: number }) {
  const params = useParams();
  const routeId = resolveInstanceRouteId(instanceId ?? Number(params.instanceId));
  const [editingInstance, setEditingInstance] = useState<InstanceListItem | null>(null);
  const [deletingInstance, setDeletingInstance] = useState<InstanceListItem | null>(null);
  const detailQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", "detail-page", routeId],
    queryFn: () => fetchInstanceDetail(routeId)
  });
  const connectionQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", "connection-status", routeId],
    queryFn: () => fetchInstanceConnectionStatus(routeId)
  });
  const auditQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", "audit-info", routeId],
    queryFn: () => fetchInstanceAuditInfo(routeId)
  });
  const backupQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", "backup-info", routeId],
    queryFn: () => fetchInstanceBackupInfo(routeId)
  });
  const instance = detailQuery.data?.instance;
  const isSqlServer = String(instance?.db_type ?? "").toLowerCase() === "sqlserver";
  const accountsQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", routeId, "accounts"],
    queryFn: () => fetchInstanceAccounts(routeId)
  });
  const agAccountsQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", routeId, "ag-accounts"],
    queryFn: () => fetchInstanceAgAccounts(routeId)
  });
  const databaseSizesQuery = useQuery({
    enabled: routeId > 0,
    queryKey: ["lists", "instances", routeId, "database-sizes"],
    queryFn: () => fetchInstanceDatabaseSizes(routeId)
  });
  function handleInstanceDetailSaved() {
    setEditingInstance(null);
    void detailQuery.refetch();
  }

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Instance detail"
        title={instance ? `实例详情 ${instance.name}` : "实例详情"}
        description="查看实例基础连接信息、状态和同步信号。"
        legacyHref={routeId > 0 ? `/instances/${routeId}` : "/instances/"}
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/console/instances">
            <ExternalLink aria-hidden size={16} />
            <span>返回实例列表</span>
          </a>
        </Button>
        <Button disabled={!instance} onClick={() => setEditingInstance(instance ?? null)} type="button" variant="outline">
          <Pencil aria-hidden size={16} />
          <span>编辑实例</span>
        </Button>
        <Button disabled={!instance || Boolean(instance.deleted_at)} onClick={() => setDeletingInstance(instance ?? null)} type="button" variant="outline">
          <Trash2 aria-hidden size={16} />
          <span>移入回收站</span>
        </Button>
        <Button
          disabled={!instance}
          onClick={() => {
            void runAction(testInstanceConnection(routeId), { success: "连接测试已完成" }).then(() => void connectionQuery.refetch());
          }}
          type="button"
          variant="outline"
        >
          <PlugZap aria-hidden size={16} />
          <span>测试连接</span>
        </Button>
        <Button
          disabled={!instance}
          onClick={() => {
            void runAction(syncInstanceAccounts(routeId), { success: "账户同步已触发" }).then(() => {
              void detailQuery.refetch();
              void accountsQuery.refetch();
              void agAccountsQuery.refetch();
            });
          }}
          type="button"
          variant="outline"
        >
          <RefreshCw aria-hidden size={16} />
          <span>同步账户</span>
        </Button>
        <Button
          disabled={!instance}
          onClick={() => {
            void runAction(syncInstanceCapacity(routeId), { success: "容量同步已触发" }).then(() => {
              void detailQuery.refetch();
              void databaseSizesQuery.refetch();
            });
          }}
          type="button"
          variant="outline"
        >
          <BarChart3 aria-hidden size={16} />
          <span>同步容量</span>
        </Button>
        {isSqlServer ? (
          <Button
            disabled={!instance}
            onClick={() => {
              void runAction(syncInstanceAuditInfo(routeId), { success: "审计同步已触发" }).then(() => void auditQuery.refetch());
            }}
            type="button"
            variant="outline"
          >
            <ShieldCheck aria-hidden size={16} />
            <span>同步审计</span>
          </Button>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Button disabled type="button" variant="outline">
                  <ShieldCheck aria-hidden size={16} />
                  <span>同步审计</span>
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>当前仅支持 SQL Server 审计信息采集</TooltipContent>
          </Tooltip>
        )}
        <Button
          disabled={!instance}
          onClick={() => {
            void runAction(syncInstanceBackup(routeId), { success: "备份同步已触发" }).then(() => void backupQuery.refetch());
          }}
          type="button"
          variant="outline"
        >
          <HardDrive aria-hidden size={16} />
          <span>同步备份</span>
        </Button>
      </CommandBar>
      {detailQuery.isLoading ? <LoadingGrid /> : null}
      {detailQuery.isError ? <ErrorState onRetry={() => void detailQuery.refetch()} /> : null}
      {instance ? (
        <Card>
          <CardContent className="grid gap-4">
            <div>
              <h2 className="font-display text-xl leading-none font-semibold tracking-normal">{instance.name}</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {instance.host}:{instance.port}
              </p>
            </div>
            <dl className="grid grid-cols-3 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
              <DetailField label="实例ID">{instance.id}</DetailField>
              <DetailField label="实例名称">{instance.name}</DetailField>
              <DetailField label="数据库类型">{dbTypeLabel(instance.db_type)}</DetailField>
              <DetailField label="主机/IP">{instance.host}:{instance.port}</DetailField>
              <DetailField label="数据库版本">{asText((instance as Record<string, unknown>).main_version ?? (instance as Record<string, unknown>).version)}</DetailField>
              <DetailField label="状态">{instanceStatusLabel(instance)}</DetailField>
              <DetailField label="描述">{asText(instance.description)}</DetailField>
              <DetailField label="标签"><TagList tags={instance.tags} /></DetailField>
              <DetailField label="最后同步">{formatShortTimestamp(instance.last_sync_time)}</DetailField>
            </dl>
          </CardContent>
        </Card>
      ) : null}
      <InstanceConnectionStatusCard
        data={connectionQuery.data}
        isLoading={connectionQuery.isLoading}
        isError={connectionQuery.isError}
        onRetry={() => void connectionQuery.refetch()}
      />
      <InstanceDataTabsCard
        accountsData={accountsQuery.data}
        accountsError={accountsQuery.isError}
        accountsLoading={accountsQuery.isLoading}
        agAccountsData={agAccountsQuery.data}
        agAccountsError={agAccountsQuery.isError}
        agAccountsLoading={agAccountsQuery.isLoading}
        auditData={auditQuery.data}
        auditError={auditQuery.isError}
        auditLoading={auditQuery.isLoading}
        backupData={backupQuery.data}
        backupError={backupQuery.isError}
        backupLoading={backupQuery.isLoading}
        databaseSizesData={databaseSizesQuery.data}
        databaseSizesError={databaseSizesQuery.isError}
        databaseSizesLoading={databaseSizesQuery.isLoading}
        onRetryAccounts={() => void accountsQuery.refetch()}
        onRetryAgAccounts={() => void agAccountsQuery.refetch()}
        onRetryAudit={() => void auditQuery.refetch()}
        onRetryBackup={() => void backupQuery.refetch()}
        onRetryDatabaseSizes={() => void databaseSizesQuery.refetch()}
        showAgAccounts={isSqlServer}
      />
      {editingInstance ? (
        <InstanceFormDialog
          item={editingInstance}
          onOpenChange={(open) => {
            if (!open) {
              setEditingInstance(null);
            }
          }}
          onSaved={handleInstanceDetailSaved}
          open
        />
      ) : null}
      <AlertDialog
        open={deletingInstance !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingInstance(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认移入回收站 {deletingInstance?.name ?? ""}</AlertDialogTitle>
            <AlertDialogDescription>实例会被软删除并从默认列表中隐藏，可在包含已删除记录后恢复。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!deletingInstance) {
                  return;
                }
                const targetId = deletingInstance.id;
                setDeletingInstance(null);
                void runAction(deleteInstance(targetId), { success: "实例已移入回收站" }).then(() => void detailQuery.refetch());
              }}
            >
              确认移入回收站
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}

export function InstancesPage() {
  const tableState = useServerTableState({
    initialFilters: { auditStatus: "", backupStatus: "", dbType: "", includeDeleted: "", managedStatus: "", status: "", tag: "" }
  });
  const listParams = {
    page: tableState.page,
    limit: tableState.pageSize,
    search: tableState.search,
    dbType: tableState.filters.dbType,
    status: tableState.filters.status,
    auditStatus: tableState.filters.auditStatus,
    managedStatus: tableState.filters.managedStatus,
    backupStatus: tableState.filters.backupStatus,
    tags: selectedTagValues(tableState.filters.tag),
    includeDeleted: tableState.filters.includeDeleted === "true"
  };
  const listQuery = useQuery({
    queryKey: ["lists", "instances", listParams],
    queryFn: () => fetchInstances(listParams),
    placeholderData: (previous) => previous
  });
  const tagOptionsQuery = useQuery({ queryKey: ["lists", "tag-options"], queryFn: () => fetchTagOptions(), staleTime: 60_000 });
  const selectedTags = selectedTagValues(tableState.filters.tag);
  const [creatingInstance, setCreatingInstance] = useState(false);
  const [editingInstance, setEditingInstance] = useState<InstanceListItem | null>(null);
  const [deletingInstance, setDeletingInstance] = useState<InstanceListItem | null>(null);
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [selectedInstanceIds, setSelectedInstanceIds] = useState<Set<number>>(() => new Set());
  function clearInstanceSelection() {
    setSelectedInstanceIds(new Set());
  }
  function setInstanceFilter(key: keyof typeof tableState.filters, value: string) {
    clearInstanceSelection();
    tableState.setFilter(key, value);
  }
  function handleInstanceSaved() {
    setCreatingInstance(false);
    setEditingInstance(null);
    void listQuery.refetch();
  }
  const columns = createInstanceColumns({
        onDelete: setDeletingInstance,
        onEdit: setEditingInstance,
        onRestore: (item) => {
          void runAction(restoreInstance(item.id), { success: "实例已恢复" }).then(() => listQuery.refetch());
        },
        onSelectedChange: (id, selected) => setSelectedInstanceIds((current) => {
          const next = new Set(current);
          if (selected) next.add(id);
          else next.delete(id);
          return next;
        }),
        selectedIds: selectedInstanceIds
      });
  const selectedItems = listQuery.data?.items.filter((item) => selectedInstanceIds.has(item.id)) ?? [];
  const selectedIds = selectedItems.map((item) => item.id);
  const deletableInstanceIds = selectedItems.filter((item) => !item.deleted_at).map((item) => item.id);

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Resource inventory"
        title="实例管理"
        description="管理数据库实例，包括增删改查和连接测试。"
        legacyHref="/instances/"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/instances/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>实例统计</span>
          </a>
        </Button>
        <Button onClick={() => setCreatingInstance(true)} type="button">
          <Plus aria-hidden size={16} />
          <span>添加实例</span>
        </Button>
        <Button
          disabled={deletableInstanceIds.length === 0}
          onClick={() => {
            setBatchDeleteOpen(true);
          }}
          type="button"
          variant="outline"
        >
          <Trash2 aria-hidden size={16} />
          <span>移入回收站</span>
        </Button>
        <Button
          disabled={selectedIds.length === 0}
          onClick={() => {
            void runAction(batchTestInstanceConnections(selectedIds), { success: "批量连接测试已完成" }).then(() => listQuery.refetch());
          }}
          type="button"
          variant="outline"
        >
          <PlugZap aria-hidden size={16} />
          <span>批量测试连接</span>
        </Button>
        <Button
          onClick={() => {
            setImportOpen(true);
          }}
          type="button"
          variant="outline"
        >
          <FileUp aria-hidden size={16} />
          <span>批量导入</span>
        </Button>
        <div className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
          <Checkbox
            aria-label="显示已删除"
            checked={tableState.filters.includeDeleted === "true"}
            onCheckedChange={(checked) => setInstanceFilter("includeDeleted", checked === true ? "true" : "")}
          />
          <span>显示已删除</span>
        </div>
        <Button variant="outline" asChild>
          <a href={buildInstancesExportPath(listParams)}>
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="实例列表" total={result.total}>
            <DataTable
              columns={columns}
              data={result.items}
              filters={[
                { columnId: "db_type", label: "类型", options: DATABASE_TYPE_FILTER_OPTIONS, value: tableState.filters.dbType, onValueChange: (value) => setInstanceFilter("dbType", value) },
                { columnId: "status", label: "状态", options: ACTIVE_STATUS_FILTER_OPTIONS, value: tableState.filters.status, onValueChange: (value) => setInstanceFilter("status", value) },
                { columnId: "audit_status", label: "审计", options: INSTANCE_AUDIT_FILTER_OPTIONS, value: tableState.filters.auditStatus, onValueChange: (value) => setInstanceFilter("auditStatus", value) },
                { columnId: "managed_status", label: "托管", options: INSTANCE_MANAGED_FILTER_OPTIONS, value: tableState.filters.managedStatus, onValueChange: (value) => setInstanceFilter("managedStatus", value) },
                { columnId: "backup_status", label: "备份", options: INSTANCE_BACKUP_FILTER_OPTIONS, value: tableState.filters.backupStatus, onValueChange: (value) => setInstanceFilter("backupStatus", value) }
              ]}
              onSearchChange={(value) => { clearInstanceSelection(); tableState.setSearchInput(value); }}
              onResetFilters={() => {
                clearInstanceSelection();
                tableState.reset();
              }}
              pagination={{
                page: result.page,
                pageSize: tableState.pageSize,
                pages: result.pages ?? 1,
                total: result.total,
                onPageChange: (page) => { clearInstanceSelection(); tableState.setPage(page); },
                onPageSizeChange: (pageSize) => { clearInstanceSelection(); tableState.setPageSize(pageSize); }
              }}
              searchPlaceholder="搜索实例 / 主机"
              searchValue={tableState.searchInput}
              toolbarExtras={
                <TagSelectorFilter
                  disabled={tagOptionsQuery.isLoading}
                  onChange={(values) => setInstanceFilter("tag", values.join(","))}
                  options={tagOptionsQuery.data ?? []}
                  selectedValues={selectedTags}
                />
              }
            />
          </ListFrame>
        )}
      </QueryPage>
      {creatingInstance ? (
        <InstanceFormDialog
          item={null}
          onOpenChange={(open) => {
            if (!open) {
              setCreatingInstance(false);
            }
          }}
          onSaved={handleInstanceSaved}
          open
        />
      ) : null}
      {editingInstance ? (
        <InstanceFormDialog
          item={editingInstance}
          onOpenChange={(open) => {
            if (!open) {
              setEditingInstance(null);
            }
          }}
          onSaved={handleInstanceSaved}
          open
        />
      ) : null}
      <InstanceImportDialog
        onImported={() => {
          setImportOpen(false);
          void listQuery.refetch();
        }}
        onOpenChange={setImportOpen}
        open={importOpen}
      />
      <AlertDialog open={batchDeleteOpen} onOpenChange={setBatchDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认批量移入回收站</AlertDialogTitle>
            <AlertDialogDescription>
              将选中的 {formatNumber(deletableInstanceIds.length)} 个未删除实例移入回收站。此操作不会物理删除实例，可在包含已删除记录后恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setBatchDeleteOpen(false);
                void runAction(batchDeleteInstances(deletableInstanceIds, "soft"), { success: "实例已移入回收站" }).then(() => listQuery.refetch());
              }}
            >
              确认批量移入回收站
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog
        open={deletingInstance !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingInstance(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认移入回收站 {deletingInstance?.name ?? ""}</AlertDialogTitle>
            <AlertDialogDescription>实例会被软删除并从默认列表中隐藏，可在包含已删除记录后恢复。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!deletingInstance) {
                  return;
                }
                const instanceId = deletingInstance.id;
                setDeletingInstance(null);
                void runAction(deleteInstance(instanceId), { success: "实例已移入回收站" }).then(() => listQuery.refetch());
              }}
            >
              确认移入回收站
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}

export function DatabaseLedgersPage() {
  const tableState = useServerTableState({ initialFilters: { dbType: "", tag: "" } });
  const selectedTags = selectedTagValues(tableState.filters.tag);
  const listParams = {
    page: tableState.page,
    limit: tableState.pageSize,
    search: tableState.search,
    dbType: tableState.filters.dbType,
    tags: selectedTags
  };
  const listQuery = useQuery({
    queryKey: ["lists", "database-ledgers", listParams],
    queryFn: () => fetchDatabaseLedgers(listParams),
    placeholderData: (previous) => previous
  });
  const tagOptionsQuery = useQuery({ queryKey: ["lists", "tag-options"], queryFn: () => fetchTagOptions(), staleTime: 60_000 });
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseLedgerItem | null>(null);
  const columns = createDatabaseLedgerColumns({
        onViewTables: setSelectedDatabase
      });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database ledger"
        title="数据库台账"
        description="查看数据库所属实例、容量采集时间和标签。"
        legacyHref="/databases/ledgers"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/databases/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>数据库统计</span>
          </a>
        </Button>
        <Button
          onClick={() => {
            void runAction(syncDatabases(), { success: "数据库同步已触发" }).then(() => listQuery.refetch());
          }}
          type="button"
        >
          <RefreshCw aria-hidden size={16} />
          <span>同步所有数据库</span>
        </Button>
        <Button variant="outline" asChild>
          <a href={buildDatabaseLedgersExportPath(listParams)}>
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="数据库台账" total={result.total}>
            <DataTable
              columns={columns}
              data={result.items}
              filters={[
                { columnId: "db_type", label: "类型", options: DATABASE_TYPE_FILTER_OPTIONS, value: tableState.filters.dbType, onValueChange: (value) => tableState.setFilter("dbType", value) }
              ]}
              onSearchChange={tableState.setSearchInput}
              onResetFilters={tableState.reset}
              pagination={{ page: result.page, pageSize: tableState.pageSize, pages: result.pages ?? 1, total: result.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
              searchPlaceholder="搜索数据库 / 实例"
              searchValue={tableState.searchInput}
              toolbarExtras={
                <TagSelectorFilter
                  disabled={tagOptionsQuery.isLoading}
                  onChange={(values) => tableState.setFilter("tag", values.join(","))}
                  options={tagOptionsQuery.data ?? []}
                  selectedValues={selectedTags}
                />
              }
            />
          </ListFrame>
        )}
      </QueryPage>
      {selectedDatabase ? (
        <DatabaseTableSizesDialog
          item={selectedDatabase}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedDatabase(null);
            }
          }}
          onRefresh={() => {
            void runAction(refreshDatabaseTableSizes(selectedDatabase.id), { success: "表容量已刷新" }).then(() => listQuery.refetch());
          }}
        />
      ) : null}
    </main>
  );
}

export function AccountLedgersPage() {
  const tableState = useServerTableState({ initialFilters: { adStatus: "", classification: "", dbType: "", tag: "" } });
  const selectedTags = selectedTagValues(tableState.filters.tag);
  const listParams = {
    page: tableState.page,
    limit: tableState.pageSize,
    search: tableState.search,
    classification: tableState.filters.classification,
    dbType: tableState.filters.dbType,
    adStatus: tableState.filters.adStatus,
    tags: selectedTags
  };
  const listQuery = useQuery({
    queryKey: ["lists", "account-ledgers", listParams],
    queryFn: () => fetchAccountLedgers(listParams),
    placeholderData: (previous) => previous
  });
  const tagOptionsQuery = useQuery({ queryKey: ["lists", "tag-options"], queryFn: () => fetchTagOptions(), staleTime: 60_000 });
  const classificationOptionsQuery = useQuery({ queryKey: ["lists", "classification-options"], queryFn: () => fetchAccountClassificationOptions(), staleTime: 60_000 });
  const [permissionsAccount, setPermissionsAccount] = useState<AccountLedgerItem | null>(null);
  const [historyAccount, setHistoryAccount] = useState<AccountLedgerItem | null>(null);
  const columns = createAccountLedgerColumns({
        onViewHistory: setHistoryAccount,
        onViewPermissions: setPermissionsAccount
      });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Account ledger"
        title="账户台账"
        description="查看账户所属实例、可用性、删除状态、超管标识、AD 状态、分类和标签。"
        legacyHref="/accounts/ledgers"
      />
      <CommandBar>
        <Button variant="outline" asChild>
          <a href="/accounts/statistics">
            <BarChart3 aria-hidden size={16} />
            <span>账户统计</span>
          </a>
        </Button>
        <Button
          onClick={() => {
            void runAction(syncAccounts(), { success: "账户同步已触发" }).then(() => listQuery.refetch());
          }}
          type="button"
        >
          <RotateCcw aria-hidden size={16} />
          <span>同步所有账户</span>
        </Button>
        <Button variant="outline" asChild>
          <a href={buildAccountLedgersExportPath(listParams)}>
            <Download aria-hidden size={16} />
            <span>导出CSV</span>
          </a>
        </Button>
      </CommandBar>
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <ListFrame title="账户台账" total={result.total}>
            <DataTable
              columns={columns}
              data={result.items}
              filters={[
                { columnId: "db_type", label: "类型", options: DATABASE_TYPE_FILTER_OPTIONS, value: tableState.filters.dbType, onValueChange: (value) => tableState.setFilter("dbType", value) },
                { columnId: "classifications", label: "分类", options: (classificationOptionsQuery.data ?? []).map((item) => ({ label: item.display_name, value: item.code })), value: tableState.filters.classification, onValueChange: (value) => tableState.setFilter("classification", value) },
                { columnId: "ad_status", label: "AD状态", options: ACCOUNT_AD_STATUS_FILTER_OPTIONS, value: tableState.filters.adStatus, onValueChange: (value) => tableState.setFilter("adStatus", value) }
              ]}
              onSearchChange={tableState.setSearchInput}
              onResetFilters={tableState.reset}
              pagination={{ page: result.page, pageSize: tableState.pageSize, pages: result.pages ?? 1, total: result.total, onPageChange: tableState.setPage, onPageSizeChange: tableState.setPageSize }}
              searchPlaceholder="搜索账户 / 实例"
              searchValue={tableState.searchInput}
              toolbarExtras={
                <TagSelectorFilter
                  disabled={tagOptionsQuery.isLoading}
                  onChange={(values) => tableState.setFilter("tag", values.join(","))}
                  options={tagOptionsQuery.data ?? []}
                  selectedValues={selectedTags}
                />
              }
            />
          </ListFrame>
        )}
      </QueryPage>
      {permissionsAccount ? (
        <AccountPermissionsDialog
          item={permissionsAccount}
          onOpenChange={(open) => {
            if (!open) {
              setPermissionsAccount(null);
            }
          }}
        />
      ) : null}
      {historyAccount ? (
        <AccountChangeHistoryDialog
          item={historyAccount}
          onOpenChange={(open) => {
            if (!open) {
              setHistoryAccount(null);
            }
          }}
        />
      ) : null}
    </main>
  );
}
