import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Check, Database, Eraser, Layers3, Minus, Plus, Tags } from "lucide-react";
import { useMemo, useState } from "react";

import { assignTagsToInstances, removeAllTagsFromInstances } from "@/api/actions";
import { fetchTagBulkOptions, type TaggableInstanceItem, type TagOptionItem } from "@/api/readOnly";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/utils/cn";
import { runAction } from "@/utils/action-feedback";

type BatchMode = "assign" | "remove";

function asLabel(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return fallback;
}

function dbTypeLabel(dbType?: string | null): string {
  const normalized = (dbType ?? "").toLowerCase();
  if (normalized === "mysql") {
    return "MySQL";
  }
  if (normalized === "postgresql") {
    return "PostgreSQL";
  }
  if (normalized === "sqlserver") {
    return "SQL Server";
  }
  if (normalized === "oracle") {
    return "Oracle";
  }
  if (normalized === "redis") {
    return "Redis";
  }
  return dbType || "未知类型";
}

function instanceLabel(item: TaggableInstanceItem): string {
  return asLabel(item.name ?? item.instance_name ?? item.id, "未知实例");
}

function instanceMeta(item: TaggableInstanceItem): string {
  const host = asLabel(item.host ?? item.ip_address, "-");
  const port = asLabel(item.port, "");
  const endpoint = port ? `${host}:${port}` : host;
  return `${endpoint} · ${dbTypeLabel(item.db_type)}`;
}

function tagLabel(item: TagOptionItem): string {
  return asLabel(item.display_name ?? item.name ?? item.id, "未知标签");
}

function tagCategory(item: TagOptionItem): string {
  return asLabel(item.category, "未分类");
}

function groupBy<TItem>(items: TItem[], getKey: (item: TItem) => string): Array<{ key: string; items: TItem[] }> {
  const groups = new Map<string, TItem[]>();
  for (const item of items) {
    const key = getKey(item);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return Array.from(groups.entries())
    .map(([key, groupItems]) => ({ key, items: groupItems }))
    .sort((left, right) => left.key.localeCompare(right.key, "zh-Hans-CN"));
}

function toggleNumber(values: number[], value: number, checked: boolean): number[] {
  if (checked) {
    return values.includes(value) ? values : [...values, value];
  }
  return values.filter((item) => item !== value);
}

function toggleMany(values: number[], ids: number[], checked: boolean): number[] {
  if (checked) {
    return Array.from(new Set([...values, ...ids]));
  }
  const removeSet = new Set(ids);
  return values.filter((item) => !removeSet.has(item));
}

function groupedSelectionState(selectedIds: number[], itemIds: number[]): boolean | "indeterminate" {
  const selectedCount = itemIds.filter((id) => selectedIds.includes(id)).length;
  if (selectedCount === 0) {
    return false;
  }
  if (selectedCount === itemIds.length) {
    return true;
  }
  return "indeterminate";
}

function selectedItems<TItem extends { id: number }>(items: TItem[], ids: number[]): TItem[] {
  const selected = new Set(ids);
  return items.filter((item) => selected.has(item.id));
}

function InstanceGroupList({
  groups,
  selectedIds,
  onSelectedIdsChange
}: {
  groups: Array<{ key: string; items: TaggableInstanceItem[] }>;
  selectedIds: number[];
  onSelectedIdsChange: (values: number[]) => void;
}) {
  if (groups.length === 0) {
    return <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">暂无实例数据</div>;
  }

  return (
    <div className="grid max-h-[32rem] gap-3 overflow-y-auto pr-1">
      {groups.map((group) => {
        const itemIds = group.items.map((item) => item.id);
        return (
          <section className="rounded-md border bg-card" key={group.key}>
            <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
              <div className="flex items-center gap-2">
                <Layers3 aria-hidden size={16} />
                <Badge variant="outline">{dbTypeLabel(group.key)}</Badge>
                <span className="text-xs text-muted-foreground">{group.items.length} 个</span>
              </div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  aria-label={`选择全部 ${dbTypeLabel(group.key)} 实例`}
                  checked={groupedSelectionState(selectedIds, itemIds)}
                  onCheckedChange={(checked) => onSelectedIdsChange(toggleMany(selectedIds, itemIds, checked === true))}
                />
                全选
              </label>
            </div>
            <div className="grid">
              {group.items.map((item) => {
                const selected = selectedIds.includes(item.id);
                return (
                  <label
                    className={cn(
                      "grid cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0 hover:bg-accent/40",
                      selected ? "bg-primary/5 shadow-[inset_3px_0_0_hsl(var(--primary))]" : ""
                    )}
                    key={item.id}
                  >
                    <Checkbox
                      aria-label={`选择实例 ${instanceLabel(item)}`}
                      checked={selected}
                      onCheckedChange={(checked) => onSelectedIdsChange(toggleNumber(selectedIds, item.id, checked === true))}
                    />
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{instanceLabel(item)}</span>
                      <span className="block truncate text-xs text-muted-foreground">{instanceMeta(item)}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function TagGroupList({
  groups,
  selectedIds,
  onSelectedIdsChange
}: {
  groups: Array<{ key: string; items: TagOptionItem[] }>;
  selectedIds: number[];
  onSelectedIdsChange: (values: number[]) => void;
}) {
  if (groups.length === 0) {
    return <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">暂无标签数据</div>;
  }

  return (
    <div className="grid max-h-[32rem] gap-3 overflow-y-auto pr-1">
      {groups.map((group) => {
        const itemIds = group.items.map((item) => item.id);
        return (
          <section className="rounded-md border bg-card" key={group.key}>
            <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
              <div className="flex items-center gap-2">
                <Layers3 aria-hidden size={16} />
                <Badge variant="outline">{group.key}</Badge>
                <span className="text-xs text-muted-foreground">{group.items.length} 个</span>
              </div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  aria-label={`选择全部 ${group.key} 标签`}
                  checked={groupedSelectionState(selectedIds, itemIds)}
                  onCheckedChange={(checked) => onSelectedIdsChange(toggleMany(selectedIds, itemIds, checked === true))}
                />
                全选
              </label>
            </div>
            <div className="grid">
              {group.items.map((item) => {
                const selected = selectedIds.includes(item.id);
                const active = item.is_active !== false;
                return (
                  <label
                    className={cn(
                      "grid cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0 hover:bg-accent/40",
                      selected ? "bg-primary/5 shadow-[inset_3px_0_0_hsl(var(--primary))]" : ""
                    )}
                    key={item.id}
                  >
                    <Checkbox
                      aria-label={`选择标签 ${tagLabel(item)}`}
                      checked={selected}
                      onCheckedChange={(checked) => onSelectedIdsChange(toggleNumber(selectedIds, item.id, checked === true))}
                    />
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{tagLabel(item)}</span>
                      <span className="block truncate text-xs text-muted-foreground">{item.name ?? "-"}</span>
                    </span>
                    <Badge variant={active ? "default" : "secondary"}>{active ? "启用" : "停用"}</Badge>
                  </label>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function ChipList({ emptyText, items }: { emptyText: string; items: string[] }) {
  if (items.length === 0) {
    return <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">{emptyText}</div>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge className="max-w-full" key={item} variant="outline">
          <span className="truncate">{item}</span>
        </Badge>
      ))}
    </div>
  );
}

export function TagBulkAssignPage() {
  const query = useQuery({
    queryKey: ["read-only", "tags", "bulk-options"],
    queryFn: () => fetchTagBulkOptions()
  });
  const [mode, setMode] = useState<BatchMode>("assign");
  const [selectedInstanceIds, setSelectedInstanceIds] = useState<number[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [executing, setExecuting] = useState(false);

  const instances = useMemo(() => query.data?.instances ?? [], [query.data?.instances]);
  const tags = useMemo(() => query.data?.tags ?? [], [query.data?.tags]);
  const instanceGroups = useMemo(() => groupBy(instances, (item) => item.db_type ?? "unknown"), [instances]);
  const tagGroups = useMemo(() => groupBy(tags, tagCategory), [tags]);
  const chosenInstances = selectedItems(instances, selectedInstanceIds).map(instanceLabel);
  const chosenTags = selectedItems(tags, selectedTagIds).map(tagLabel);
  const canExecute = selectedInstanceIds.length > 0 && (mode === "remove" || selectedTagIds.length > 0);

  function handleModeChange(value: string) {
    const nextMode = value === "remove" ? "remove" : "assign";
    setMode(nextMode);
    if (nextMode === "remove") {
      setSelectedTagIds([]);
    }
  }

  function clearSelections() {
    setSelectedInstanceIds([]);
    setSelectedTagIds([]);
  }

  async function execute() {
    if (!canExecute || executing) {
      return;
    }
    setExecuting(true);
    try {
      const action = mode === "assign"
        ? assignTagsToInstances(selectedInstanceIds, selectedTagIds)
        : removeAllTagsFromInstances(selectedInstanceIds);
      await runAction(action, {
        loading: mode === "assign" ? "正在分配标签" : "正在移除标签",
        success: mode === "assign" ? "标签已分配" : "标签已移除"
      });
      clearSelections();
    } finally {
      setExecuting(false);
    }
  }

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <div className="flex items-center justify-between gap-3">
        <Button asChild variant="outline">
          <a href="/tags">
            <ArrowLeft aria-hidden />
            返回标签管理
          </a>
        </Button>
      </div>

      <div className="grid gap-1">
        <h1 className="text-2xl font-semibold tracking-normal">批量分配标签</h1>
      </div>

      <section className="grid gap-4">
        <Tabs onValueChange={handleModeChange} value={mode}>
          <TabsList>
            <TabsTrigger value="assign">
              <Plus aria-hidden size={16} />
              分配模式
            </TabsTrigger>
            <TabsTrigger value="remove">
              <Minus aria-hidden size={16} />
              移除模式
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {mode === "remove" ? (
          <Alert>
            <AlertTriangle aria-hidden size={16} />
            <AlertDescription>选择要移除标签的实例，系统将移除这些实例上的所有标签。</AlertDescription>
          </Alert>
        ) : null}
      </section>

      {query.isLoading ? (
        <div className="grid grid-cols-3 gap-4 max-xl:grid-cols-1">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      ) : null}

      {query.isError ? (
        <Alert variant="destructive">
          <AlertTriangle aria-hidden size={16} />
          <AlertDescription>批量标签数据加载失败</AlertDescription>
        </Alert>
      ) : null}

      {query.data ? (
        <div className={cn("grid gap-4", mode === "remove" ? "grid-cols-[minmax(0,1fr)_22rem] max-xl:grid-cols-1" : "grid-cols-[minmax(0,0.9fr)_minmax(0,0.9fr)_22rem] max-2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] max-xl:grid-cols-1")}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div>
                <div className="text-xs text-muted-foreground">实例</div>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Database aria-hidden size={18} />
                  选择实例
                </CardTitle>
              </div>
              <Badge variant="secondary">{selectedInstanceIds.length}</Badge>
            </CardHeader>
            <CardContent>
              <InstanceGroupList groups={instanceGroups} selectedIds={selectedInstanceIds} onSelectedIdsChange={setSelectedInstanceIds} />
            </CardContent>
          </Card>

          {mode === "assign" ? (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between gap-3">
                <div>
                  <div className="text-xs text-muted-foreground">标签</div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Tags aria-hidden size={18} />
                    选择标签
                  </CardTitle>
                </div>
                <Badge variant="secondary">{selectedTagIds.length}</Badge>
              </CardHeader>
              <CardContent>
                <TagGroupList groups={tagGroups} selectedIds={selectedTagIds} onSelectedIdsChange={setSelectedTagIds} />
              </CardContent>
            </Card>
          ) : null}

          <Card className={cn("h-fit max-2xl:col-span-2 max-xl:col-span-1", mode === "remove" ? "max-2xl:col-span-1" : "")}>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div>
                <div className="text-xs text-muted-foreground">操作概览</div>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Layers3 aria-hidden size={18} />
                  当前选择
                </CardTitle>
              </div>
              <Badge variant="outline">
                {selectedInstanceIds.length}
                {mode === "assign" ? ` · ${selectedTagIds.length}` : ""}
              </Badge>
            </CardHeader>
            <CardContent className="grid gap-4">
              <section className="grid gap-2 rounded-md border border-dashed p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Database aria-hidden size={16} />
                  已选实例
                </div>
                <ChipList emptyText="尚未选择实例" items={chosenInstances} />
              </section>

              {mode === "assign" ? (
                <section className="grid gap-2 rounded-md border border-dashed p-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Tags aria-hidden size={16} />
                    已选标签
                  </div>
                  <ChipList emptyText="尚未选择标签" items={chosenTags} />
                </section>
              ) : null}

              <div className="grid grid-cols-2 gap-2">
                <Button onClick={clearSelections} type="button" variant="outline">
                  <Eraser aria-hidden />
                  清空选择
                </Button>
                <Button disabled={!canExecute || executing} onClick={() => void execute()} type="button">
                  {mode === "assign" ? <Plus aria-hidden /> : <Minus aria-hidden />}
                  {mode === "assign" ? "分配标签" : "移除标签"}
                </Button>
              </div>

              {executing ? (
                <div className="grid gap-2 rounded-md border p-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 font-medium">
                      <Check aria-hidden size={16} />
                      批量执行
                    </span>
                    <span className="text-muted-foreground">处理中...</span>
                  </div>
                  <Progress value={68} />
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </main>
  );
}
