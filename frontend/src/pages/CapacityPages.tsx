import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Database, ExternalLink, HardDrive, Server } from "lucide-react";
import type { ReactNode } from "react";

import {
  fetchCapacityDatabaseSnapshot,
  fetchCapacityInstanceSnapshot,
  type CapacityDatabaseItem,
  type CapacityDatabaseSnapshot,
  type CapacityInstanceItem,
  type CapacityInstanceSnapshot
} from "@/api/capacity";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Metric = {
  label: string;
  value: string | number;
  detail?: string;
  icon: typeof Server;
};

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatSizeMb(value: number | undefined | null): string {
  const size = value ?? 0;
  if (size >= 1024) {
    return `${(size / 1024).toFixed(2)} GB`;
  }
  return `${size.toFixed(0)} MB`;
}

function formatPercent(value: number | undefined | null): string {
  return `${(value ?? 0).toFixed(1)}%`;
}

function trendVariant(value: number | undefined | null): "default" | "secondary" | "destructive" | "outline" {
  const resolved = value ?? 0;
  if (resolved > 0) {
    return "destructive";
  }
  if (resolved < 0) {
    return "secondary";
  }
  return "outline";
}

function TrendIcon({ value }: { value: number | undefined | null }) {
  const resolved = value ?? 0;
  if (resolved > 0) {
    return <ArrowUpRight aria-hidden size={14} />;
  }
  if (resolved < 0) {
    return <ArrowDownRight aria-hidden size={14} />;
  }
  return <ArrowRight aria-hidden size={14} />;
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
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="容量指标">
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
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="容量加载中">
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
      <AlertDescription>容量数据加载失败</AlertDescription>
      <div className="col-start-2 mt-2 sm:col-start-3 sm:row-span-2 sm:mt-0">
        <Button variant="outline" onClick={onRetry}>
          重新加载
        </Button>
      </div>
    </Alert>
  );
}

function ListFrame({ title, description, total, children }: { title: string; description: string; total: number; children: ReactNode }) {
  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex items-start justify-between gap-3 max-sm:grid">
          <div>
            <h2 className="font-display text-lg leading-none font-semibold tracking-normal">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
          <Badge variant="secondary">共 {formatNumber(total)} 条</Badge>
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

function QueryPage<TSnapshot>({
  snapshot,
  isLoading,
  isError,
  onRetry,
  children
}: {
  snapshot: TSnapshot | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  children: (snapshot: TSnapshot) => ReactNode;
}) {
  return (
    <>
      {isLoading ? <LoadingGrid /> : null}
      {isError ? <ErrorState onRetry={onRetry} /> : null}
      {snapshot ? children(snapshot) : null}
    </>
  );
}

function InstanceCapacityTable({ items }: { items: CapacityInstanceItem[] }) {
  return (
    <Table className="min-w-[58rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["实例", "周期", "总容量", "数据库数", "变化", "增长率"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell>
              <div className="font-medium">{item.instance.name}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.instance.db_type}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {item.period_start} - {item.period_end}
            </TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.total_size_mb)}</TableCell>
            <TableCell className="font-mono text-xs">{formatNumber(item.database_count)}</TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.total_size_change_mb)}</TableCell>
            <TableCell>
              <Badge variant={trendVariant(item.growth_rate)}>
                <TrendIcon value={item.growth_rate} />
                {formatPercent(item.growth_rate)}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DatabaseCapacityTable({ items }: { items: CapacityDatabaseItem[] }) {
  return (
    <Table className="min-w-[58rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["数据库", "实例", "周期", "平均容量", "变化", "增长率"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={6} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell className="font-medium">{item.database_name}</TableCell>
            <TableCell>
              <div>{item.instance.name}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.instance.db_type}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {item.period_start} - {item.period_end}
            </TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.avg_size_mb)}</TableCell>
            <TableCell className="font-mono text-xs">{formatSizeMb(item.size_change_mb)}</TableCell>
            <TableCell>
              <Badge variant={trendVariant(item.growth_rate)}>
                <TrendIcon value={item.growth_rate} />
                {formatPercent(item.growth_rate)}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function CapacityInstancesPage() {
  const capacityQuery = useQuery({
    queryKey: ["capacity", "instances", "daily", "last-30-days"],
    queryFn: () => fetchCapacityInstanceSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Instance capacity"
        title="实例容量"
        description="按最近 30 天日粒度读取实例容量聚合，展示容量变化和数据库数量。"
        legacyHref="/capacity/instances"
      />
      <QueryPage snapshot={capacityQuery.data} isLoading={capacityQuery.isLoading} isError={capacityQuery.isError} onRetry={() => void capacityQuery.refetch()}>
        {(snapshot: CapacityInstanceSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                { label: "实例总数", value: snapshot.summary.total_instances, icon: Server },
                { label: "总容量", value: formatSizeMb(snapshot.summary.total_size_mb), detail: `平均 ${formatSizeMb(snapshot.summary.avg_size_mb)}`, icon: HardDrive },
                { label: "最大实例", value: formatSizeMb(snapshot.summary.max_size_mb), icon: BarChart3 },
                { label: "当前页", value: `${snapshot.list.page}/${snapshot.list.pages}`, icon: Database }
              ]}
            />
            <ListFrame title="实例容量列表" description={`日粒度 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <InstanceCapacityTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function CapacityDatabasesPage() {
  const capacityQuery = useQuery({
    queryKey: ["capacity", "databases", "daily", "last-30-days"],
    queryFn: () => fetchCapacityDatabaseSnapshot()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database capacity"
        title="数据库容量"
        description="按最近 30 天日粒度读取数据库容量聚合，展示容量排行和增长趋势。"
        legacyHref="/capacity/databases"
      />
      <QueryPage snapshot={capacityQuery.data} isLoading={capacityQuery.isLoading} isError={capacityQuery.isError} onRetry={() => void capacityQuery.refetch()}>
        {(snapshot: CapacityDatabaseSnapshot) => (
          <>
            <MetricGrid
              metrics={[
                { label: "数据库总数", value: snapshot.summary.total_databases, icon: Database },
                { label: "实例覆盖", value: snapshot.summary.total_instances, icon: Server },
                { label: "总容量", value: formatSizeMb(snapshot.summary.total_size_mb), detail: `平均 ${formatSizeMb(snapshot.summary.avg_size_mb)}`, icon: HardDrive },
                { label: "增长率", value: formatPercent(snapshot.summary.growth_rate), icon: BarChart3 }
              ]}
            />
            <ListFrame title="数据库容量列表" description={`日粒度 · 每页 ${formatNumber(snapshot.list.limit)} 条`} total={snapshot.list.total}>
              <DatabaseCapacityTable items={snapshot.list.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}
