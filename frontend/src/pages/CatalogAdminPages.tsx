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
  EyeOff,
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
  type TagItem,
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
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const title = item ? `编辑凭据 ${item.name}` : "新建凭据";
  const isDatabaseCredential = credentialType === "database";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: CredentialWritePayload = {
      name: name.trim(),
      credential_type: credentialType,
      db_type: isDatabaseCredential ? dbType || null : null,
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
                  { label: "数据库", value: "database" },
                  { label: "API", value: "api" },
                  { label: "Veeam", value: "veeam" },
                  { label: "LDAP", value: "ldap" },
                  { label: "SSH", value: "ssh" }
                ]}
                value={credentialType}
              />
            </FormField>
            {isDatabaseCredential ? (
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
            ) : null}
            <FormField label="用户名">
              <Input onChange={(event) => setUsername(event.target.value)} required value={username} />
            </FormField>
            <FormField label="密码">
              <div className="relative">
                <Input
                  className="pr-10"
                  onChange={(event) => setPassword(event.target.value)}
                  required={!item}
                  type={passwordVisible ? "text" : "password"}
                  value={password}
                />
                <Button
                  aria-label={passwordVisible ? "隐藏密码" : "显示密码"}
                  className="absolute top-1/2 right-1 size-7 -translate-y-1/2"
                  onClick={() => setPasswordVisible((current) => !current)}
                  size="icon"
                  type="button"
                  variant="ghost"
                >
                  {passwordVisible ? <EyeOff aria-hidden size={16} /> : <Eye aria-hidden size={16} />}
                </Button>
              </div>
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
  categoryOptions,
  item,
  onOpenChange,
  onSaved,
  open
}: {
  categoryOptions: string[];
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
  const effectiveCategoryOptions = useMemo(
    () =>
      Array.from(new Set([item?.category ?? "", ...categoryOptions].map((value) => value.trim()).filter(Boolean))).sort((left, right) =>
        left.localeCompare(right, "zh-Hans-CN")
      ),
    [categoryOptions, item?.category]
  );

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
              <SelectControl
                disabled={effectiveCategoryOptions.length === 0}
                label="分类"
                onValueChange={setCategory}
                options={effectiveCategoryOptions.map((option) => ({ label: option, value: option }))}
                placeholder="请选择分类"
                value={category}
              />
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
      <PageHeader eyebrow="Access control" title="用户管理" description="展示用户、角色与启用状态，并支持新增、编辑、删除。" />
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
                onResetFilters={tableState.reset}
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
      <PageHeader eyebrow="Credential vault" title="凭据管理" description="展示凭据类型、数据库类型和引用数量，并支持新增、编辑、删除。" />
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
                onResetFilters={tableState.reset}
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
  const canManage = canManageCatalog(currentUser);
  const categoryOptions = query.data?.categories ?? [];
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
      <PageHeader eyebrow="Resource tags" title="标签管理" description="展示标签、分类和实例引用数量，并支持新增、编辑、删除。" />
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
                    <Button asChild size="sm" variant="outline">
                      <a href="/tags/bulk/assign">批量分配</a>
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
                onResetFilters={tableState.reset}
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
          categoryOptions={categoryOptions}
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
          categoryOptions={categoryOptions}
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
