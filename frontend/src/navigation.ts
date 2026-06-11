import {
  Activity,
  Boxes,
  ChartColumn,
  ChartLine,
  ChartPie,
  Clock,
  Database,
  FileText,
  Gauge,
  HardDrive,
  HeartPulse,
  KeyRound,
  Layers3,
  ListChecks,
  Server,
  Settings,
  ShieldAlert,
  Tags,
  UserCog,
  Users
} from "lucide-react";
import type { ComponentType } from "react";

export type NavigationItem = {
  label: string;
  description: string;
  consolePath: string;
  legacyHref: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  adminOnly?: boolean;
};

export type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

export const navigationGroups: NavigationGroup[] = [
  {
    label: "态势总览",
    items: [
      {
        label: "仪表盘",
        description: "关键资源、风险和系统状态的 React 首屏骨架。",
        consolePath: "/dashboard",
        legacyHref: "/dashboard/",
        icon: Gauge
      },
      {
        label: "风险中心",
        description: "集中查看规则风险和高优先级处置入口。",
        consolePath: "/risk-center",
        legacyHref: "/risk-center/",
        icon: HeartPulse
      }
    ]
  },
  {
    label: "资源管理",
    items: [
      {
        label: "实例管理",
        description: "数据库实例列表、连接、同步和详情入口。",
        consolePath: "/instances",
        legacyHref: "/instances/",
        icon: Server
      },
      {
        label: "群集管理",
        description: "SQL Server AG 与 MySQL 拓扑管理入口。",
        consolePath: "/clusters",
        legacyHref: "/cluster/",
        icon: Layers3
      },
      {
        label: "数据库台账",
        description: "数据库清单、标签、容量和导出入口。",
        consolePath: "/database-ledgers",
        legacyHref: "/databases/ledgers",
        icon: Database
      }
    ]
  },
  {
    label: "账户与权限",
    items: [
      {
        label: "账户台账",
        description: "实例账户、AG 账户、权限详情和变更历史。",
        consolePath: "/account-ledgers",
        legacyHref: "/accounts/ledgers",
        icon: Users
      },
      {
        label: "账户分类",
        description: "分类、规则、授权范围和自动分类入口。",
        consolePath: "/account-classifications",
        legacyHref: "/accounts/classifications/",
        icon: Tags
      },
      {
        label: "分类统计",
        description: "账户分类趋势、贡献和规则命中分析。",
        consolePath: "/classification-statistics",
        legacyHref: "/accounts/statistics/classifications",
        icon: ChartColumn
      }
    ]
  },
  {
    label: "容量与审计",
    items: [
      {
        label: "实例容量",
        description: "实例容量趋势和聚合数据入口。",
        consolePath: "/capacity/instances",
        legacyHref: "/capacity/instances",
        icon: ChartPie
      },
      {
        label: "数据库容量",
        description: "数据库容量趋势、表空间和刷新入口。",
        consolePath: "/capacity/databases",
        legacyHref: "/capacity/databases",
        icon: ChartLine
      },
      {
        label: "实例统计",
        description: "按类型、状态、版本和业务维度统计实例。",
        consolePath: "/instance-statistics",
        legacyHref: "/instances/statistics",
        icon: HardDrive
      },
      {
        label: "账户统计",
        description: "账户状态、类型和分类统计。",
        consolePath: "/account-statistics",
        legacyHref: "/accounts/statistics",
        icon: Activity
      },
      {
        label: "数据库统计",
        description: "数据库状态、容量分布和类型统计。",
        consolePath: "/database-statistics",
        legacyHref: "/databases/statistics",
        icon: Database
      }
    ]
  },
  {
    label: "自动化",
    items: [
      {
        label: "定时任务",
        description: "调度任务、任务状态和手动执行入口。",
        consolePath: "/scheduler",
        legacyHref: "/scheduler/",
        icon: Clock
      },
      {
        label: "会话中心",
        description: "同步会话、任务运行状态和取消入口。",
        consolePath: "/sync-sessions",
        legacyHref: "/history/sessions/",
        icon: ListChecks
      },
      {
        label: "日志中心",
        description: "统一日志检索、详情和错误分析入口。",
        consolePath: "/logs",
        legacyHref: "/history/logs/",
        icon: FileText,
        adminOnly: true
      },
      {
        label: "变更历史",
        description: "账户变更日志与审计追踪入口。",
        consolePath: "/account-change-logs",
        legacyHref: "/history/account-change-logs/",
        icon: ShieldAlert
      }
    ]
  },
  {
    label: "系统管理",
    items: [
      {
        label: "用户管理",
        description: "用户、角色和只读权限视图。",
        consolePath: "/users",
        legacyHref: "/users/",
        icon: UserCog
      },
      {
        label: "系统设置",
        description: "集成源、告警规则和风险规则设置。",
        consolePath: "/settings",
        legacyHref: "/admin/system-settings",
        icon: Settings,
        adminOnly: true
      },
      {
        label: "凭据管理",
        description: "数据库连接凭据和密钥管理入口。",
        consolePath: "/credentials",
        legacyHref: "/credentials/",
        icon: KeyRound
      },
      {
        label: "标签管理",
        description: "标签维护、批量绑定和资源归类入口。",
        consolePath: "/tags",
        legacyHref: "/tags/",
        icon: Tags
      },
      {
        label: "分区管理",
        description: "容量时序分区、清理和健康状态入口。",
        consolePath: "/partitions",
        legacyHref: "/partition/",
        icon: Boxes,
        adminOnly: true
      }
    ]
  }
];

export function flattenNavigationItems(groups: NavigationGroup[]): NavigationItem[] {
  return groups.flatMap((group) => group.items);
}

export function filterNavigationForRole(groups: NavigationGroup[], role: string): NavigationGroup[] {
  const isAdmin = role === "admin";
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => isAdmin || !item.adminOnly)
    }))
    .filter((group) => group.items.length > 0);
}
