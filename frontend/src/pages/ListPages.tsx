import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Database, ExternalLink, KeyRound, Server, ShieldCheck, Tags, Users } from "lucide-react";
import type { ReactNode } from "react";

import {
  fetchAccountLedgers,
  fetchDatabaseLedgers,
  fetchInstances,
  type AccountLedgerItem,
  type DatabaseLedgerItem,
  type InstanceListItem,
  type PaginatedList
} from "@/api/lists";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Metric = {
  label: string;
  value: number | string;
  icon: typeof Server;
};

function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function statusVariant(status: string | undefined): "default" | "secondary" | "destructive" | "outline" {
  if (!status) {
    return "outline";
  }
  if (["disabled", "deleted", "failed", "error", "not_backed_up", "locked"].includes(status)) {
    return "destructive";
  }
  if (["ok", "enabled", "completed", "backed_up", "active"].includes(status)) {
    return "secondary";
  }
  return "outline";
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
    <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="列表指标">
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
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
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

function TagList({ tags }: { tags: Array<{ name: string; display_name: string }> }) {
  if (tags.length === 0) {
    return <span className="text-muted-foreground">-</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {tags.slice(0, 3).map((tag) => (
        <Badge variant="outline" key={tag.name}>
          {tag.display_name}
        </Badge>
      ))}
    </div>
  );
}

function ListFrame({
  title,
  description,
  total,
  children
}: {
  title: string;
  description: string;
  total: number;
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

function InstanceTable({ items }: { items: InstanceListItem[] }) {
  return (
    <Table className="min-w-[58rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["实例", "地址", "状态", "审计", "备份", "资源", "标签"].map((label) => (
            <TableHead key={label}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.length === 0 ? <EmptyRows colSpan={7} /> : null}
        {items.map((item) => (
          <TableRow className="align-top" key={item.id}>
            <TableCell>
              <div className="font-medium">{item.name}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.db_type}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {item.host}:{item.port}
            </TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.status)}>{item.is_active ? item.status : "disabled"}</Badge>
            </TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.audit_status)}>{item.audit_status}</Badge>
            </TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.backup_status)}>{item.backup_status}</Badge>
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              DB {formatNumber(item.active_db_count)} · Account {formatNumber(item.active_account_count)}
            </TableCell>
            <TableCell>
              <TagList tags={item.tags} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DatabaseLedgerTable({ items }: { items: DatabaseLedgerItem[] }) {
  return (
    <Table className="min-w-[54rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["数据库", "实例", "类型", "容量", "同步", "标签"].map((label) => (
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
              <div className="mt-1 font-mono text-xs text-muted-foreground">{item.instance.host}</div>
            </TableCell>
            <TableCell>{item.db_type}</TableCell>
            <TableCell className="font-mono text-xs">{item.capacity.label}</TableCell>
            <TableCell>
              <Badge variant={statusVariant(item.sync_status.value)}>{item.sync_status.label}</Badge>
            </TableCell>
            <TableCell>
              <TagList tags={item.tags} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function AccountLedgerTable({ items }: { items: AccountLedgerItem[] }) {
  return (
    <Table className="min-w-[60rem]">
      <TableHeader className="text-xs">
        <TableRow>
          {["账户", "实例", "类型", "状态", "分类", "标签"].map((label) => (
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
              <div className="font-medium">{item.username}</div>
              <div className="mt-1 text-xs text-muted-foreground">{item.is_superuser ? "superuser" : "standard"}</div>
            </TableCell>
            <TableCell>
              <div>{item.instance_name}</div>
              <div className="mt-1 font-mono text-xs text-muted-foreground">{item.instance_host}</div>
            </TableCell>
            <TableCell>{item.db_type}</TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                <Badge variant={statusVariant(item.is_active ? "active" : "disabled")}>
                  {item.is_active ? "active" : "disabled"}
                </Badge>
                {item.is_locked ? <Badge variant="destructive">locked</Badge> : null}
                {item.is_deleted ? <Badge variant="outline">deleted</Badge> : null}
              </div>
            </TableCell>
            <TableCell>
              <TagList tags={item.classifications.map((classification) => ({ name: classification.display_name, display_name: classification.display_name }))} />
            </TableCell>
            <TableCell>
              <TagList tags={item.tags} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function InstancesPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "instances", 1, 20],
    queryFn: () => fetchInstances()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Resource inventory"
        title="实例管理"
        description="集中查看实例状态、审计、备份、数据库数量和账户数量。"
        legacyHref="/instances/"
      />
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <>
            <MetricGrid
              metrics={[
                { label: "实例总数", value: result.total, icon: Server },
                { label: "当前页", value: `${result.page}/${result.pages ?? 1}`, icon: Tags },
                { label: "启用实例", value: result.items.filter((item) => item.is_active).length, icon: ShieldCheck },
                { label: "托管实例", value: result.items.filter((item) => item.is_jumpserver_managed).length, icon: Database }
              ]}
            />
            <ListFrame title="实例列表" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
              <InstanceTable items={result.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function DatabaseLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "database-ledgers", 1, 20],
    queryFn: () => fetchDatabaseLedgers()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Database ledger"
        title="数据库台账"
        description="查看数据库所属实例、同步状态、容量和标签。"
        legacyHref="/databases/ledgers"
      />
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <>
            <MetricGrid
              metrics={[
                { label: "数据库总数", value: result.total, icon: Database },
                { label: "当前页", value: `${result.page}/-`, icon: Tags },
                { label: "已更新", value: result.items.filter((item) => item.sync_status.value === "completed").length, icon: ShieldCheck },
                { label: "实例覆盖", value: new Set(result.items.map((item) => item.instance.id)).size, icon: Server }
              ]}
            />
            <ListFrame title="数据库列表" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
              <DatabaseLedgerTable items={result.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}

export function AccountLedgersPage() {
  const listQuery = useQuery({
    queryKey: ["lists", "account-ledgers", 1, 20],
    queryFn: () => fetchAccountLedgers()
  });

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <PageHeader
        eyebrow="Account ledger"
        title="账户台账"
        description="查看账户状态、所属实例、分类和标签。"
        legacyHref="/accounts/ledgers"
      />
      <QueryPage result={listQuery.data} isLoading={listQuery.isLoading} isError={listQuery.isError} onRetry={() => void listQuery.refetch()}>
        {(result) => (
          <>
            <MetricGrid
              metrics={[
                { label: "账户总数", value: result.total, icon: Users },
                { label: "当前页", value: `${result.page}/${result.pages ?? 1}`, icon: Tags },
                { label: "锁定账户", value: result.items.filter((item) => item.is_locked).length, icon: KeyRound },
                { label: "高权限", value: result.items.filter((item) => item.is_superuser).length, icon: ShieldCheck }
              ]}
            />
            <ListFrame title="账户列表" description={`每页 ${formatNumber(result.limit)} 条`} total={result.total}>
              <AccountLedgerTable items={result.items} />
            </ListFrame>
          </>
        )}
      </QueryPage>
    </main>
  );
}
