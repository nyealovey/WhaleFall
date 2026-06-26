import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Database, HardDrive, Layers3, ListChecks, RefreshCw, ShieldAlert, ShieldCheck, type LucideIcon } from "lucide-react";
import { useState, type FormEvent } from "react";

import { fetchRiskCenterSnapshot, type RiskCenterCard, type RiskCenterFilters, type RiskSeverity } from "@/api/riskCenter";
import { SelectControl } from "@/components/shared/FormControls";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination, PaginationContent, PaginationItem } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { runAction } from "@/utils/action-feedback";
import { cn } from "@/utils/cn";

const SEVERITY_LABELS: Record<string, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
  ok: "健康"
};

const RISK_SEVERITY_OPTIONS = [
  { label: "全部", value: "" },
  { label: "高风险", value: "high" },
  { label: "中风险", value: "medium" },
  { label: "低风险", value: "low" },
  { label: "健康", value: "ok" }
];

const RISK_DB_TYPE_OPTIONS = [
  { label: "全部", value: "" },
  { label: "MySQL", value: "mysql" },
  { label: "PostgreSQL", value: "postgresql" },
  { label: "SQL Server", value: "sqlserver" },
  { label: "Oracle", value: "oracle" }
];

const RISK_STATUS_OPTIONS = [
  { label: "全部", value: "" },
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" }
];

function cleanRiskFilters(filters: RiskCenterFilters): RiskCenterFilters {
  const cleaned: RiskCenterFilters = {};
  const search = filters.search?.trim();
  if (search) {
    cleaned.search = search;
  }
  if (filters.severity) {
    cleaned.severity = filters.severity;
  }
  if (filters.dbType) {
    cleaned.dbType = filters.dbType;
  }
  if (filters.status) {
    cleaned.status = filters.status;
  }
  if (filters.tag) {
    cleaned.tag = filters.tag;
  }
  return cleaned;
}

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function severityLabel(severity: RiskSeverity): string {
  return SEVERITY_LABELS[String(severity)] ?? String(severity || "未知");
}

function severityBadgeVariant(severity: RiskSeverity): "default" | "secondary" | "destructive" | "outline" {
  if (severity === "high") {
    return "destructive";
  }
  if (severity === "medium") {
    return "default";
  }
  if (severity === "ok") {
    return "secondary";
  }
  return "outline";
}

function riskValue(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

function riskSignalVariant(metric: Record<string, unknown> | undefined): "default" | "secondary" | "destructive" | "outline" {
  const tone = riskValue(metric?.tone, "").toLowerCase();
  if (["danger", "error", "high"].includes(tone)) {
    return "destructive";
  }
  if (["success", "ok", "healthy"].includes(tone)) {
    return "secondary";
  }
  if (["warning", "medium"].includes(tone)) {
    return "default";
  }
  return "outline";
}

function RiskSignal({ icon: Icon, label, metric }: { icon: LucideIcon; label: string; metric: Record<string, unknown> | undefined }) {
  const metricLabel = riskValue(metric?.label, "未配置");
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge aria-label={`${label}：${metricLabel}`} className="size-8 justify-center p-0" variant={riskSignalVariant(metric)}>
          <Icon aria-hidden size={15} />
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{label}：{metricLabel}</TooltipContent>
    </Tooltip>
  );
}

function RiskFilterPanel({
  draft,
  onApply,
  onDraftChange,
  onReset
}: {
  draft: RiskCenterFilters;
  onApply: () => void;
  onDraftChange: (draft: RiskCenterFilters) => void;
  onReset: () => void;
}) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  return (
    <Card>
      <CardContent className="grid gap-3">
        <form
          className="grid grid-cols-[minmax(16rem,1.2fr)_repeat(4,minmax(8rem,0.7fr))_auto] items-end gap-3 max-2xl:grid-cols-3 max-lg:grid-cols-2 max-sm:grid-cols-1"
          onSubmit={handleSubmit}
        >
          <label className="grid gap-1.5 text-sm font-medium">
            <span>搜索</span>
            <span className="text-xs font-normal text-muted-foreground">实例名 / 主机 / 类型</span>
            <Input
              onChange={(event) => onDraftChange({ ...draft, search: event.target.value })}
              placeholder="实例名 / 主机 / 类型"
              type="search"
              value={draft.search ?? ""}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>严重度</span>
            <SelectControl
              label="严重度"
              onValueChange={(severity) => onDraftChange({ ...draft, severity })}
              options={RISK_SEVERITY_OPTIONS}
              value={draft.severity ?? ""}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>数据库类型</span>
            <SelectControl
              label="数据库类型"
              onValueChange={(dbType) => onDraftChange({ ...draft, dbType })}
              options={RISK_DB_TYPE_OPTIONS}
              value={draft.dbType ?? ""}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>状态</span>
            <SelectControl
              label="状态"
              onValueChange={(status) => onDraftChange({ ...draft, status })}
              options={RISK_STATUS_OPTIONS}
              value={draft.status ?? ""}
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>标签</span>
            <Input
              aria-label="标签"
              onChange={(event) => onDraftChange({ ...draft, tag: event.target.value })}
              placeholder="标签 code"
              value={draft.tag ?? ""}
            />
          </label>
          <div className="flex items-center gap-2">
            <Button type="submit">应用筛选</Button>
            <Button onClick={onReset} type="button" variant="outline">
              重置
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function groupRiskCards(cards: RiskCenterCard[]): Array<[string, RiskCenterCard[]]> {
  const groups = new Map<string, RiskCenterCard[]>();
  for (const card of cards) {
    const groupName = card.group || card.db_type?.toUpperCase() || "未分组";
    const groupCards = groups.get(groupName) ?? [];
    groupCards.push(card);
    groups.set(groupName, groupCards);
  }
  return [...groups.entries()];
}

function RiskCard({ card }: { card: RiskCenterCard }) {
  const detailHref = card.links?.detail ?? `/instances/${card.instance_id}`;
  return (
    <article className="grid gap-3 rounded-lg border bg-card p-4 shadow-xs">
      <div className="flex items-center justify-between gap-3">
        <a aria-label={`查看 ${card.name} 详情`} className="flex min-w-0 items-center gap-2" href={detailHref}>
          <Badge className="size-8 justify-center p-0" variant="outline">
            <Database aria-hidden size={15} />
          </Badge>
          <strong className="truncate text-base">{card.name}</strong>
        </a>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge aria-label={`风险等级 ${severityLabel(card.overall_severity)}`} className="size-8 justify-center p-0" variant={severityBadgeVariant(card.overall_severity)}>
              <ShieldAlert aria-hidden size={15} />
            </Badge>
          </TooltipTrigger>
          <TooltipContent>风险等级：{severityLabel(card.overall_severity)}</TooltipContent>
        </Tooltip>
      </div>
      <div className="flex flex-wrap gap-2" aria-label={`${card.name} 实例核心风险指标`}>
        <RiskSignal icon={HardDrive} label="备份" metric={card.backup} />
        <RiskSignal icon={ShieldCheck} label="审计" metric={card.audit} />
        <RiskSignal icon={Database} label="托管" metric={card.managed} />
        <RiskSignal icon={Layers3} label="群集" metric={card.cluster} />
        <RiskSignal icon={ListChecks} label="任务" metric={card.tasks} />
      </div>
    </article>
  );
}

export function RiskCenterPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<RiskCenterFilters>({});
  const [draftFilters, setDraftFilters] = useState<RiskCenterFilters>({});
  const riskQuery = useQuery({
    queryKey: ["risk-center", "snapshot", filters, page],
    queryFn: () => fetchRiskCenterSnapshot({ ...filters, limit: 20, page }),
    placeholderData: (previous) => previous
  });

  const snapshot = riskQuery.data;
  const severityCounts = snapshot?.summary.severity_counts ?? {};

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
        <div>
          <h1 className="font-display text-2xl leading-none tracking-normal">风险中心</h1>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button onClick={() => void runAction(riskQuery.refetch(), { success: "风险中心已刷新" })} type="button">
            <RefreshCw aria-hidden size={16} />
            刷新
          </Button>
          <Button variant="outline" asChild>
            <a href="/risk-center/">在旧版打开</a>
          </Button>
        </div>
      </section>

      {riskQuery.isLoading ? (
        <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="风险中心加载中">
          {["high", "medium", "low", "ok"].map((item) => (
            <Card key={item}>
              <CardContent className="grid gap-3">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-12" />
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {riskQuery.isError ? (
        <Alert variant="destructive" className="grid-cols-[1rem_minmax(0,1fr)] items-center sm:grid-cols-[1rem_minmax(0,1fr)_auto]">
          <AlertCircle aria-hidden size={16} />
          <AlertDescription>风险中心数据加载失败</AlertDescription>
          <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
            <Button variant="outline" onClick={() => void riskQuery.refetch()}>
              重新加载
            </Button>
          </div>
        </Alert>
      ) : null}

      <RiskFilterPanel
        draft={draftFilters}
        onApply={() => { setPage(1); setFilters(cleanRiskFilters(draftFilters)); }}
        onDraftChange={setDraftFilters}
        onReset={() => {
          setDraftFilters({});
          setFilters({});
          setPage(1);
        }}
      />

      {snapshot ? (
        <>
          <section className="grid grid-cols-5 gap-2 max-xl:grid-cols-3 max-md:grid-cols-2 max-sm:grid-cols-1" aria-label="风险汇总">
            <Card className="bg-foreground text-background">
              <CardContent>
                <div className="text-sm opacity-70">总实例</div>
                <div className="mt-2 font-mono text-3xl font-semibold">{formatNumber(snapshot.summary.total_instances)}</div>
              </CardContent>
            </Card>
            {(["high", "medium", "low", "ok"] as const).map((severity) => (
              <Card key={severity}>
                <CardContent>
                  <div className="text-sm text-muted-foreground">{severityLabel(severity)}</div>
                  <div className="mt-2 font-mono text-3xl font-semibold">{formatNumber(severityCounts[severity])}</div>
                </CardContent>
              </Card>
            ))}
          </section>

          <TooltipProvider>
          <section className="grid gap-4" aria-label="实例风险墙">
            {snapshot.cards.items.length > 0 ? (
              groupRiskCards(snapshot.cards.items).map(([group, cards]) => (
                <section className="grid gap-2" key={group}>
                  <div className="rounded-md bg-secondary/50 px-3 py-2">
                    <h2 className="text-sm font-semibold">{group} ({formatNumber(cards.length)})</h2>
                  </div>
                  <div className={cn("grid gap-2", cards.length > 1 ? "grid-cols-2 max-lg:grid-cols-1" : "grid-cols-1")}>
                    {cards.map((card) => (
                      <RiskCard card={card} key={card.instance_id} />
                    ))}
                  </div>
                </section>
              ))
            ) : (
              <p className="rounded-md border bg-secondary/40 p-4 text-sm text-muted-foreground">暂无风险实例</p>
            )}
          </section>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
            <span>显示 {(snapshot.cards.page - 1) * snapshot.cards.limit + (snapshot.cards.items.length > 0 ? 1 : 0)}-{Math.min(snapshot.cards.page * snapshot.cards.limit, snapshot.cards.total)}，共 {formatNumber(snapshot.cards.total)} 条</span>
            <Pagination className="w-auto">
              <PaginationContent>
                <PaginationItem><Button disabled={snapshot.cards.page <= 1} onClick={() => setPage((current) => Math.max(current - 1, 1))} size="sm" variant="outline">上一页</Button></PaginationItem>
                <PaginationItem><span className="px-2">第 {snapshot.cards.page} / {Math.max(snapshot.cards.pages, 1)} 页</span></PaginationItem>
                <PaginationItem><Button disabled={snapshot.cards.page >= snapshot.cards.pages} onClick={() => setPage((current) => current + 1)} size="sm" variant="outline">下一页</Button></PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
          </TooltipProvider>
        </>
      ) : null}
    </main>
  );
}
