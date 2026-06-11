import { Activity, Database, Server, ShieldAlert, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const METRICS = [
  { label: "数据库实例", value: "--", icon: Server },
  { label: "账户总数", value: "--", icon: Users },
  { label: "数据库总数", value: "--", icon: Database },
  { label: "待确认风险", value: "--", icon: ShieldAlert }
];

export function DashboardPage() {
  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
        <div>
          <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">React console</span>
          <h1 className="font-display mt-1 text-2xl leading-none tracking-normal">仪表盘</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            新前端骨架已接入 `/console`，旧站点继续提供完整数据操作能力。
          </p>
        </div>
        <Button variant="outline" asChild>
          <a href="/dashboard/">在旧版打开</a>
        </Button>
      </section>

      <section className="grid grid-cols-4 gap-2 max-xl:grid-cols-2 max-sm:grid-cols-1" aria-label="控制台指标骨架">
        {METRICS.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card className="min-h-[var(--metric-card-min-height)]" key={metric.label}>
              <CardContent className="grid gap-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Icon aria-hidden size={18} />
                  <span>{metric.label}</span>
                </div>
                <strong className="font-mono text-[length:var(--metric-hero-value)] leading-none">{metric.value}</strong>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)] gap-2 max-lg:grid-cols-1">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>迁移状态</CardTitle>
            <Activity aria-hidden size={18} />
          </CardHeader>
          <CardContent className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 font-mono text-sm">
            <span>Session bootstrap</span>
            <Badge variant="outline">Ready</Badge>
            <span>API envelope client</span>
            <Badge variant="outline">Ready</Badge>
            <span>Module routing</span>
            <Badge variant="outline">Ready</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>下一批迁移候选</CardTitle>
            <CardDescription>只读页面优先，写操作延后。</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            建议从只读仪表盘和列表页开始，先迁移读取路径，再迁移写操作与高风险动作。
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
