import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Database, HardDrive, Layers3, ListChecks, RefreshCw, ShieldAlert, ShieldCheck, type LucideIcon } from "lucide-react";

import { fetchRiskCenterSnapshot, type RiskCenterCard, type RiskSeverity } from "@/api/riskCenter";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/utils/cn";

const SEVERITY_LABELS: Record<string, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
  ok: "健康"
};

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
  return (
    <div className="grid gap-2 rounded-md border bg-secondary/40 p-3">
      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Icon aria-hidden size={14} />
          <span>{label}</span>
        </span>
        <Badge variant={riskSignalVariant(metric)}>{riskValue(metric?.label, "未配置")}</Badge>
      </div>
      {metric?.detail ? <p className="text-xs text-muted-foreground">{riskValue(metric.detail)}</p> : null}
    </div>
  );
}

function RiskFilterPanel() {
  const selectClassName =
    "border-input bg-background ring-offset-background focus-visible:ring-ring h-9 rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2";

  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="grid grid-cols-[minmax(16rem,1.2fr)_repeat(4,minmax(8rem,0.7fr))_auto] items-end gap-3 max-2xl:grid-cols-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
          <label className="grid gap-1.5 text-sm font-medium">
            <span>搜索</span>
            <span className="text-xs font-normal text-muted-foreground">实例名 / 主机 / 类型</span>
            <Input placeholder="实例名 / 主机 / 类型" readOnly type="search" />
          </label>
          {["严重度", "数据库类型", "状态", "标签"].map((label) => (
            <label className="grid gap-1.5 text-sm font-medium" key={label}>
              <span>{label}</span>
              <select aria-label={label} className={selectClassName} defaultValue="">
                <option value="">全部</option>
              </select>
            </label>
          ))}
          <div className="flex items-center gap-2">
            <Button type="button">筛选</Button>
            <Button type="button" variant="outline">
              清空
            </Button>
          </div>
        </div>
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
  const primaryRisk = card.risk_items?.[0];
  return (
    <article className="grid gap-3 rounded-lg border bg-card p-4 shadow-xs">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold">{card.name}</h2>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {card.host}:{card.port}
          </p>
        </div>
        <Badge variant={severityBadgeVariant(card.overall_severity)}>{severityLabel(card.overall_severity)}</Badge>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Database aria-hidden size={14} />
        <span>{card.db_type}</span>
        <span className="font-mono">score {formatNumber(card.risk_score)}</span>
      </div>
      {primaryRisk ? (
        <div className="rounded-md bg-secondary/60 p-3 text-sm">
          <div className="font-medium">{primaryRisk.label}</div>
          <p className="mt-1 text-muted-foreground">{primaryRisk.detail}</p>
        </div>
      ) : (
        <p className="rounded-md bg-secondary/60 p-3 text-sm text-muted-foreground">暂无风险详情</p>
      )}
      <section className="grid gap-2" aria-label={`${card.name} 实例核心风险指标`}>
        <h3 className="text-sm font-medium">实例核心风险指标</h3>
        <div className="grid grid-cols-5 gap-2 max-xl:grid-cols-3 max-md:grid-cols-2 max-sm:grid-cols-1">
          <RiskSignal icon={HardDrive} label="备份" metric={card.backup} />
          <RiskSignal icon={ShieldCheck} label="审计" metric={card.audit} />
          <RiskSignal icon={Database} label="托管" metric={card.managed} />
          <RiskSignal icon={Layers3} label="群集" metric={card.cluster} />
          <RiskSignal icon={ListChecks} label="任务" metric={card.tasks} />
        </div>
      </section>
    </article>
  );
}

export function RiskCenterPage() {
  const riskQuery = useQuery({
    queryKey: ["risk-center", "snapshot"],
    queryFn: () => fetchRiskCenterSnapshot()
  });

  const snapshot = riskQuery.data;
  const severityCounts = snapshot?.summary.severity_counts ?? {};
  const topRisks = snapshot?.summary.top_risks ?? [];

  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
        <div>
          <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">Risk signals</span>
          <h1 className="font-display mt-1 text-2xl leading-none tracking-normal">风险中心</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            汇总实例备份、审计、托管、容量和任务信号，优先展示高风险实例。
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button onClick={() => void riskQuery.refetch()} type="button">
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

          <RiskFilterPanel />

          <section className="grid grid-cols-[minmax(0,1.35fr)_minmax(22rem,0.65fr)] gap-2 max-xl:grid-cols-1">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>实例风险墙</CardTitle>
                  <CardDescription>
                    展示前 {formatNumber(snapshot.cards.items.length)} 个候选，共 {formatNumber(snapshot.cards.total)} 个匹配实例。
                  </CardDescription>
                </div>
                <ShieldAlert aria-hidden size={18} />
              </CardHeader>
              <CardContent className="grid gap-4">
                {snapshot.cards.items.length > 0 ? (
                  groupRiskCards(snapshot.cards.items).map(([group, cards]) => (
                    <section className="grid gap-2" key={group}>
                      <div className="flex items-center justify-between rounded-md bg-secondary/50 px-3 py-2">
                        <h3 className="text-sm font-semibold">{group} ({formatNumber(cards.length)})</h3>
                        <Badge variant="outline">{severityLabel(cards[0]?.overall_severity ?? "ok")}</Badge>
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
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>高优先级风险</CardTitle>
                <CardDescription>来自 `/api/v1/risk-center/summary` 的 top_risks。</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                {topRisks.length > 0 ? (
                  topRisks.slice(0, 8).map((risk) => (
                    <div className="rounded-md border bg-secondary/40 p-3 text-sm" key={`${risk.rule_key}-${risk.instance_name}`}>
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{risk.instance_name}</span>
                        <Badge variant={severityBadgeVariant(risk.severity)}>{severityLabel(risk.severity)}</Badge>
                      </div>
                      <p className="mt-1 text-muted-foreground">{risk.label ?? risk.rule_key}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">暂无高优先级风险</p>
                )}
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </main>
  );
}
