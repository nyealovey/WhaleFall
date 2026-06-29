import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type PlaceholderPageProps = {
  label: string;
  description: string;
};

export function PlaceholderPage({ label, description }: PlaceholderPageProps) {
  return (
    <main className="grid max-w-[var(--layout-max-width-wide)] gap-[var(--page-spacing-dense)] p-5">
      <section className="flex items-start justify-between gap-4 rounded-lg border bg-card p-4 max-sm:grid">
        <div>
          <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">React module shell</span>
          <h1 className="font-display mt-1 text-2xl leading-none tracking-normal">{label}</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{description}</p>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>页面骨架已接入</CardTitle>
          <CardDescription>该模块已在 React 路由和导航中占位。</CardDescription>
        </CardHeader>
        <CardContent className="border-l-4 border-primary text-sm text-muted-foreground">
          数据表格、筛选和写操作会按模块逐步迁移；当前旧版页面仍是完整功能入口。
        </CardContent>
      </Card>
    </main>
  );
}
