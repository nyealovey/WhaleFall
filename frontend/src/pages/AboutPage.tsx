import { Activity, Clock, Code2, Database, History, Info, LineChart, Server, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const featureGroups = [
  { title: "数据库管理", icon: Database, tone: "outline" as const, bullets: ["多数据库实例管理", "连接状态测试", "实例标签分类"] },
  { title: "账户管理", icon: Users, tone: "secondary" as const, bullets: ["账户权限扫描", "智能分类管理", "权限规则配置", "账户状态监控"] },
  { title: "任务调度", icon: Clock, tone: "outline" as const, bullets: ["定时数据同步", "容量同步"] },
  { title: "监控与聚合", icon: LineChart, tone: "destructive" as const, bullets: ["统一日志与审计中心", "聚合服务周期统计", "同步会话追踪"] }
];

const stackGroups = [
  {
    title: "后端技术",
    entries: ["Python 3.11+", "Flask 3.1.2+", "SQLAlchemy 2.0.43+", "APScheduler 3.11.0+", "Redis 6.4.0+", "Gunicorn 23.0.0+", "Gevent 25.9.1+"]
  },
  {
    title: "前端技术",
    entries: ["Bootstrap 5", "Grid.js", "Chart.js", "Umbrella JS", "Font Awesome", "Jinja2 模板引擎"]
  }
];

const dbSupports = [
  { name: "PostgreSQL", version: "11.x ~ 16.x" },
  { name: "MySQL", version: "5.7 ~ 9.0" },
  { name: "SQL Server", version: "2017 ~ 2022" },
  { name: "Oracle", version: "12c ~ 21c" }
];

const versionTimeline = [
  { version: "1.5.0", date: "2026-01-28", summary: "核心升级：新增账户分类统计（分类/规则维度聚合与趋势查看），补齐统计 API 与页面联动。", tag: "账户分类统计" },
  { version: "1.4.0", date: "2026-01-09", summary: "核心升级：建立 /api/v1 OpenAPI 标准 API（Swagger UI + OpenAPI JSON）；Scheduler 触发器配置收敛为 cron。", tag: "OpenAPI API" },
  { version: "1.3.6", date: "2025-12-30", summary: "核心升级：GRID 组件化，补充标准化文档；全局版本号与可见页面同步更新至 v1.3.6。", tag: "GRID 组件化" },
  { version: "1.3.5", date: "2025-12-24", summary: "按版本升级指南同步全局版本号至 v1.3.5，清单文件与可见页面版本信息同步更新。", tag: "版本同步" },
  { version: "1.3.4", date: "2025-12-16", summary: "修复 Pyright 类型问题，补齐注解以确保静态检查零告警；全局版本号与可见页面同步更新。", tag: "类型修复" },
  { version: "1.3.3", date: "2025-12-15", summary: "RUFF 全面修复，清理告警并补齐类型与日志规范；版本号与可见页面同步更新。", tag: "质量提升" },
  { version: "1.3.2", date: "2025-12-05", summary: "统一实例/凭据/标签模态布局，移除标签颜色/排序并引入基础设施域、组织角色域、外部域三类父分类，版本号与脚本同步更新。", tag: "UI 统一" },
  { version: "1.3.1", date: "2025-12-01", summary: "全面修复 CRUD 流程：批量选择、CSV 导入、实例编辑入口等体验一致，清理残留命名与模板问题。", tag: "CRUD 稳定" },
  { version: "1.3.0", date: "2025-12-01", summary: "统一 UI 视觉体系、完成命名规范重构，并为核心接口补齐 Google 风格注释。", tag: "视觉治理" },
  { version: "1.2.3", date: "2025-11-26", summary: "注释/Docstring 全面补齐，版本号统一至 v1.2.3，关于页与部署文档同步更新。", tag: "文档同步" }
];

function SectionHeading({ icon: Icon, label, meta }: { icon: typeof Info; label: string; meta: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <Badge className="gap-2" variant="outline">
        <Icon aria-hidden size={15} />
        {label}
      </Badge>
      <Badge variant="secondary">{meta}</Badge>
    </div>
  );
}

export function AboutPage() {
  const latestRelease = versionTimeline[0];

  return (
    <main className="mx-auto grid max-w-[var(--layout-max-width-wide)] gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_minmax(28rem,0.9fr)]">
      <section className="grid content-start gap-4">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
            <img className="rounded-md" src="/static/img/logo.webp" alt="鲸落" width="72" height="72" />
            <Badge variant="outline">鲸落 WhaleFall</Badge>
            <h1 className="font-display text-3xl font-semibold">面向 DBA 的数据库资源管理平台</h1>
            <Badge className="gap-2" variant="secondary">
              <Activity aria-hidden size={15} />
              Kurtis.Jin
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeading icon={Info} label="项目介绍" meta={`版本 ${latestRelease.version}`} />
            <CardDescription className="text-base leading-7 text-foreground">
              鲸落聚焦实例、账户、容量与任务调度等日常运维场景，为 DBA 提供统一入口。系统内置实例与账户台账、权限治理、容量体检、调度编排等能力，借助结构化日志与可视化看板帮助团队快速识别风险、分配任务并跟踪执行效果。
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeading icon={Server} label="核心功能" meta="组件复用" />
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {featureGroups.map((feature) => {
              const Icon = feature.icon;
              return (
                <section className="rounded-md border bg-background/50 p-4" key={feature.title}>
                  <Badge className="mb-3 gap-2" variant={feature.tone}>
                    <Icon aria-hidden size={15} />
                    {feature.title}
                  </Badge>
                  <ul className="grid gap-2 text-sm text-muted-foreground">
                    {feature.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeading icon={Code2} label="技术栈" meta="持续升级" />
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {stackGroups.map((stack) => (
              <section className="rounded-md border bg-background/50 p-4" key={stack.title}>
                <Badge className="mb-3" variant="outline">{stack.title}</Badge>
                <ul className="grid gap-2 text-sm text-muted-foreground">
                  {stack.entries.map((entry) => (
                    <li className="font-mono" key={entry}>{entry}</li>
                  ))}
                </ul>
              </section>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeading icon={Database} label="支持的数据库" meta="全覆盖" />
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {dbSupports.map((db) => (
              <section className="grid place-items-center gap-3 rounded-md border bg-background/50 p-4 text-center" key={db.name}>
                <Database aria-hidden className="text-primary" size={28} />
                <CardTitle className="text-base">{db.name}</CardTitle>
                <Badge variant="secondary">{db.version}</Badge>
              </section>
            ))}
          </CardContent>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader>
            <SectionHeading icon={History} label="更新日志" meta="依时间排序" />
          </CardHeader>
          <CardContent className="grid gap-3">
            {versionTimeline.map((item) => (
              <article className="rounded-md border bg-background/50 p-4" key={item.version}>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-2">
                    <Badge>版本 {item.version}</Badge>
                    <Badge variant="outline">{item.tag}</Badge>
                  </div>
                  <Badge className="gap-2" variant="secondary">
                    <Clock aria-hidden size={14} />
                    {item.date}
                  </Badge>
                </div>
                <p className="mb-0 text-sm leading-6 text-muted-foreground">{item.summary}</p>
              </article>
            ))}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
