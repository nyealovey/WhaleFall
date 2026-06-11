import { useQuery } from "@tanstack/react-query";
import { AlertCircle, BarChart3, Database, ExternalLink, HardDrive, Server, Users } from "lucide-react";
import type { ReactNode } from "react";

import {
  fetchAccountStatisticsSnapshot,
  fetchDatabaseStatistics,
  fetchInstanceStatistics,
  type AccountStatisticsSnapshot,
  type DatabaseStatistics,
  type InstanceStatistics
} from "@/api/statistics";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Metric = {
  label: string;
  value: number | string | undefined;
  detail?: string;
  icon: typeof Server;
};

type ListItem = {
  label: string;
  value: number | string;
  detail?: string;
  badge?: string;
};

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatSizeMb(value: number | undefined): string {
  const size = value ?? 0;
  if (size >= 1024) {
    return `${(size / 1024).toFixed(2)} GB`;
  }
  return `${size.toFixed(0)} MB`;
}

function countFromUnknown(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  if (!value || typeof value !== "object") {
    return 0;
  }
  const record = value as Record<string, unknown>;
  for (const key of ["total_accounts", "count", "total", "matched_accounts_count", "value"]) {
    if (typeof record[key] === "number") {
      return record[key];
    }
  }
  return 0;
}

function entriesFromRecord(record: Record<string, unknown> | undefined): ListItem[] {
  return Object.entries(record ?? {})
    .filter(([key]) => !["total", "items"].includes(key))
    .map(([label, value]) => ({ label, value: countFromUnknown(value) }))
    .filter((item) => Number(item.value) > 0)
    .slice(0, 8);
}

function toneForBadge(value: string): "default" | "secondary" | "destructive" | "outline" {
  return ["error", "failed", "not_backed_up", "backup_stale", "high"].includes(value) ? "destructive" : "secondary";
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

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="统计指标">
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
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="统计指标加载中">
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
      <AlertDescription>统计数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function DataList({ title, description, items, emptyText }: { title: string; description?: string; items: ListItem[]; emptyText: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="grid gap-2">
        {items.length > 0 ? (
          items.map((item) => (
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md border bg-secondary/40 px-3 py-2 text-sm" key={`${title}-${item.label}`}>
              <div className="min-w-0">
                <div className="truncate font-medium">{item.label}</div>
                {item.detail ? <div className="mt-1 truncate text-xs text-muted-foreground">{item.detail}</div> : null}
              </div>
              <div className="flex items-center gap-2">
                {item.badge ? <Badge variant={toneForBadge(item.badge)}>{item.badge}</Badge> : null}
                <span className="font-mono">{typeof item.value === "number" ? formatNumber(item.value) : item.value}</span>
              </div>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        )}
      </CardContent>
    </Card>
  );
}

function QueryPage({
  children,
  isLoading,
  isError,
  onRetry
}: {
  children: ReactNode;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {children}
    </>
  );
}

function InstanceStatisticsContent({ stats }: { stats: InstanceStatistics }) {
  return (
    <>
      <MetricGrid
        metrics={[
          { label: "实例总数", value: stats.total_instances, detail: `当前 ${formatNumber(stats.current_instances)}`, icon: Server },
          { label: "启用实例", value: stats.active_instances, detail: `停用 ${formatNumber(stats.disabled_instances)}`, icon: BarChart3 },
          { label: "审计启用", value: stats.audit_enabled_instances, detail: `高可用 ${formatNumber(stats.high_availability_instances)}`, icon: HardDrive },
          { label: "备份覆盖", value: stats.backed_up_instances, detail: `过期 ${formatNumber(stats.backup_stale_instances)}`, icon: Database }
        ]}
      />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DataList
          title="数据库类型"
          description={`共 ${formatNumber(stats.db_types_count)} 类`}
          emptyText="暂无数据库类型统计"
          items={stats.db_type_stats.map((item) => ({ label: item.db_type, value: item.count }))}
        />
        <DataList
          title="端口分布"
          emptyText="暂无端口统计"
          items={stats.port_stats.map((item) => ({ label: String(item.port), value: item.count }))}
        />
        <DataList
          title="版本分布"
          emptyText="暂无版本统计"
          items={stats.version_stats.map((item) => ({
            label: item.version || "unknown",
            value: item.count,
            detail: item.db_type
          }))}
        />
        <DataList
          title="备份状态"
          emptyText="暂无备份状态统计"
          items={stats.backup_status_stats.map((item) => ({
            label: item.backup_status,
            value: item.count,
            badge: item.backup_status
          }))}
        />
      </section>
    </>
  );
}

function AccountStatisticsContent({ snapshot }: { snapshot: AccountStatisticsSnapshot }) {
  const { summary } = snapshot;
  return (
    <>
      <MetricGrid
        metrics={[
          { label: "账户总数", value: summary.total_accounts, detail: `正常 ${formatNumber(summary.normal_accounts)}`, icon: Users },
          { label: "启用账户", value: summary.active_accounts, detail: `锁定 ${formatNumber(summary.locked_accounts)}`, icon: BarChart3 },
          { label: "实例范围", value: summary.total_instances, detail: `物理 ${formatNumber(summary.physical_instances)} · AG ${formatNumber(summary.ag_virtual_instances)}`, icon: Server },
          { label: "停用实例", value: summary.disabled_instances, detail: `删除 ${formatNumber(summary.deleted_instances)}`, icon: Database }
        ]}
      />
      <section className="grid grid-cols-2 gap-2 max-lg:grid-cols-1">
        <DataList title="数据库类型" emptyText="暂无数据库类型账户统计" items={entriesFromRecord(snapshot.dbTypes)} />
        <DataList title="账户分类" emptyText="暂无账户分类统计" items={entriesFromRecord(snapshot.classifications)} />
        <DataList title="账户来源" emptyText="暂无账户来源统计" items={entriesFromRecord(summary.owner_type_stats)} />
        <DataList
          title="规则命中"
          emptyText="暂无规则命中统计"
          items={snapshot.rules.rule_stats.slice(0, 8).map((item) => ({
            label: `rule #${item.rule_id}`,
            value: item.matched_accounts_count
          }))}
        />
      </section>
    </>
  );
}

function DatabaseStatisticsContent({ stats }: { stats: DatabaseStatistics }) {
  return (
    <>
      <MetricGrid
        metrics={[
          { label: "数据库总数", value: stats.total_databases, detail: `活跃 ${formatNumber(stats.active_databases)}`, icon: Database },
          { label: "涉及实例", value: stats.total_instances, detail: `停用库 ${formatNumber(stats.inactive_databases)}`, icon: Server },
          { label: "总容量", value: formatSizeMb(stats.total_size_mb), detail: `平均 ${formatSizeMb(stats.avg_size_mb)}`, icon: HardDrive },
          { label: "最大库", value: formatSizeMb(stats.max_size_mb), detail: `删除 ${formatNumber(stats.deleted_databases)}`, icon: BarChart3 }
        ]}
      />
      <section className="grid grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] gap-2 max-lg:grid-cols-1">
        <div className="grid gap-2">
          <DataList
            title="数据库类型"
            emptyText="暂无数据库类型统计"
            items={stats.db_type_stats.map((item) => ({ label: item.db_type, value: item.count }))}
          />
          <DataList
            title="同步状态"
            emptyText="暂无同步状态统计"
            items={stats.sync_status_stats.map((item) => ({
              label: item.label,
              value: item.count,
              badge: item.value
            }))}
          />
        </div>
        <div className="grid gap-2">
          <DataList
            title="实例分布"
            emptyText="暂无实例分布统计"
            items={stats.instance_stats.slice(0, 8).map((item) => ({
              label: item.instance_name,
              value: item.count,
              detail: item.db_type
            }))}
          />
          <DataList
            title="容量排行"
            emptyText="暂无容量排行"
            items={stats.capacity_rankings.slice(0, 8).map((item) => ({
              label: item.database_name,
              value: item.size_label,
              detail: `${item.instance_name} · ${item.db_type}`
            }))}
          />
        </div>
      </section>
    </>
  );
}

export function InstanceStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "instances"],
    queryFn: () => fetchInstanceStatistics()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Instance statistics"
        title="实例统计"
        description="按实例状态、数据库类型、端口、版本和备份覆盖读取统计数据。"
        legacyHref="/instances/statistics"
      />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <InstanceStatisticsContent stats={statsQuery.data} /> : null}
      </QueryPage>
    </main>
  );
}

export function AccountStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "accounts"],
    queryFn: () => fetchAccountStatisticsSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Account statistics"
        title="账户统计"
        description="聚合账户状态、实例范围、数据库类型、分类和规则命中信号。"
        legacyHref="/accounts/statistics"
      />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <AccountStatisticsContent snapshot={statsQuery.data} /> : null}
      </QueryPage>
    </main>
  );
}

export function DatabaseStatisticsPage() {
  const statsQuery = useQuery({
    queryKey: ["statistics", "databases"],
    queryFn: () => fetchDatabaseStatistics()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database statistics"
        title="数据库统计"
        description="展示数据库数量、同步状态、实例分布和最新容量排行。"
        legacyHref="/databases/statistics"
      />
      <QueryPage isLoading={statsQuery.isLoading} isError={statsQuery.isError} onRetry={() => void statsQuery.refetch()}>
        {statsQuery.data ? <DatabaseStatisticsContent stats={statsQuery.data.stats} /> : null}
      </QueryPage>
    </main>
  );
}
