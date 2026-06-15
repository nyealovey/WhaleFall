export type LegacyParitySection = {
  title: string;
  fields: string[];
};

export type LegacyParityPage = {
  consolePath: string;
  legacyPath: string;
  title: string;
  sections: LegacyParitySection[];
  filters: string[];
  actions: string[];
  apiPaths: string[];
};

export const legacyParityPages: LegacyParityPage[] = [
  {
    consolePath: "/dashboard",
    legacyPath: "/dashboard/",
    title: "仪表盘",
    sections: [
      { title: "资源指标", fields: ["实例", "账户", "数据库", "容量"] },
      { title: "运行信号", fields: ["日志等级", "同步趋势", "活动记录", "系统状态"] }
    ],
    filters: ["刷新"],
    actions: ["刷新", "查看旧版"],
    apiPaths: ["/api/v1/dashboard/overview", "/api/v1/dashboard/status", "/api/v1/dashboard/charts", "/api/v1/dashboard/activities"]
  },
  {
    consolePath: "/risk-center",
    legacyPath: "/risk-center/",
    title: "风险中心",
    sections: [
      { title: "风险汇总", fields: ["实例总数", "风险总数", "高风险", "风险分类"] },
      { title: "风险卡片", fields: ["实例", "规则", "分类", "严重级别", "详情"] }
    ],
    filters: ["严重级别", "分类", "搜索"],
    actions: ["刷新", "查看详情"],
    apiPaths: ["/api/v1/risk-center/summary", "/api/v1/risk-center/cards", "/api/v1/risk-center/rules"]
  },
  {
    consolePath: "/instances",
    legacyPath: "/instances/",
    title: "实例管理",
    sections: [{ title: "实例列表", fields: ["实例", "地址", "数据库类型", "状态", "标签", "连接状态", "操作"] }],
    filters: ["搜索", "数据库类型", "状态", "标签"],
    actions: ["新建实例", "编辑实例", "测试连接", "同步账户", "同步容量", "删除实例", "导入模板", "批量创建", "导出"],
    apiPaths: ["/api/v1/instances", "/api/v1/instances/options", "/api/v1/instances/actions/batch-create", "/api/v1/instances/exports"]
  },
  {
    consolePath: "/clusters",
    legacyPath: "/cluster/",
    title: "群集管理",
    sections: [
      { title: "SQL Server 群集列表", fields: ["群集", "状态", "绑定实例", "AG", "最近 AG 同步", "数据库同步状态", "操作"] },
      { title: "AG 配置", fields: ["AG 名称", "侦听器", "连接端点", "账户凭据", "Contained", "采集", "同步状态", "数据库状态"] },
      { title: "AG 状态面板", fields: ["AG 状态", "群集状态", "群集类型", "主副本", "数据库数", "异常数据库", "受影响副本", "副本状态", "数据库状态"] },
      { title: "AG 账户面板", fields: ["AG 总数", "Contained AG", "已配置凭据", "启用 AG", "账户", "实例", "可用性", "超级用户", "AD 状态", "分类", "标签", "最近变更"] },
      { title: "MySQL 群集列表", fields: ["群集", "拓扑", "状态", "绑定实例", "主从状态", "操作"] },
      { title: "MySQL 主从状态面板", fields: ["实例", "角色", "上游", "IO 线程", "SQL 线程", "延迟", "IO 状态", "日志位置", "GTID", "只读", "错误"] }
    ],
    filters: ["搜索", "状态"],
    actions: ["新建群集", "管理群集", "同步 AG", "同步 SQL Server 状态", "同步 AG 账户", "同步 MySQL 主从状态", "绑定实例"],
    apiPaths: ["/api/v1/sqlserver-clusters", "/api/v1/mysql-clusters", "/api/v1/accounts/ledgers"]
  },
  {
    consolePath: "/database-ledgers",
    legacyPath: "/databases/ledgers",
    title: "数据库台账",
    sections: [{ title: "数据库列表", fields: ["数据库", "实例", "类型", "状态", "容量", "表空间", "同步时间", "操作"] }],
    filters: ["搜索", "数据库类型", "状态", "标签"],
    actions: ["同步数据库", "导出", "查看表空间"],
    apiPaths: ["/api/v1/databases/ledgers", "/api/v1/databases/ledgers/exports", "/api/v1/databases/sizes"]
  },
  {
    consolePath: "/account-ledgers",
    legacyPath: "/accounts/ledgers",
    title: "账户台账",
    sections: [{ title: "账户列表", fields: ["账户", "实例/AG", "类型", "状态", "锁定", "高权限", "分类", "标签", "最近变更", "操作"] }],
    filters: ["搜索", "数据库类型", "账户状态", "分类", "标签"],
    actions: ["查看权限", "查看变更历史", "导出"],
    apiPaths: ["/api/v1/accounts/ledgers", "/api/v1/accounts/ledgers/exports"]
  },
  {
    consolePath: "/account-classifications",
    legacyPath: "/accounts/classifications/",
    title: "账户分类",
    sections: [
      { title: "账户分类", fields: ["图标", "分类名称", "系统标记", "风险等级", "Code", "操作"] },
      { title: "规则管理", fields: ["数据库类型分组", "规则名称", "账户分类", "命中账户数", "权限配置", "操作"] },
      { title: "规则详情", fields: ["匹配逻辑", "账户分类", "数据库类型", "权限配置"] }
    ],
    filters: ["规则搜索", "数据库类型"],
    actions: ["自动分类", "新建分类", "编辑分类", "删除分类", "新建规则", "查看规则", "编辑规则", "删除规则", "验证表达式"],
    apiPaths: ["/api/v1/accounts/classifications", "/api/v1/accounts/classifications/rules", "/api/v1/accounts/classifications/permissions"]
  },
  {
    consolePath: "/classification-statistics",
    legacyPath: "/accounts/statistics/classifications",
    title: "分类统计",
    sections: [
      { title: "规则列表", fields: ["规则名", "备注", "状态", "最新周期", "规则命中"] },
      { title: "分类趋势（去重账号数）", fields: ["周期", "去重账号数", "覆盖天数"] },
      { title: "规则贡献（当前周期）", fields: ["规则", "贡献账号数", "覆盖天数"] }
    ],
    filters: ["账户分类", "统计周期", "数据库类型", "实例/AG", "规则状态", "规则搜索"],
    actions: ["刷新", "应用", "重置", "选择规则"],
    apiPaths: ["/api/v1/accounts/statistics/classifications", "/api/v1/accounts/statistics/classifications/trend", "/api/v1/accounts/statistics/rules/trend", "/api/v1/accounts/statistics/rules/contributions", "/api/v1/accounts/statistics/rules/overview"]
  },
  {
    consolePath: "/capacity/instances",
    legacyPath: "/capacity/instances",
    title: "实例容量",
    sections: [{ title: "容量列表", fields: ["实例", "数据库类型", "容量", "增长", "周期", "采集时间"] }],
    filters: ["周期", "开始日期", "结束日期", "搜索"],
    actions: ["刷新"],
    apiPaths: ["/api/v1/capacity/instances", "/api/v1/capacity/instances/summary"]
  },
  {
    consolePath: "/capacity/databases",
    legacyPath: "/capacity/databases",
    title: "数据库容量",
    sections: [{ title: "容量列表", fields: ["数据库", "实例", "容量", "增长", "周期", "采集时间"] }],
    filters: ["周期", "开始日期", "结束日期", "搜索"],
    actions: ["刷新"],
    apiPaths: ["/api/v1/capacity/databases", "/api/v1/capacity/databases/summary"]
  },
  {
    consolePath: "/instance-statistics",
    legacyPath: "/instances/statistics",
    title: "实例统计",
    sections: [{ title: "统计图表", fields: ["实例总数", "类型分布", "状态分布", "版本分布", "业务维度"] }],
    filters: ["刷新"],
    actions: ["刷新"],
    apiPaths: ["/api/v1/instances/statistics"]
  },
  {
    consolePath: "/account-statistics",
    legacyPath: "/accounts/statistics",
    title: "账户统计",
    sections: [{ title: "账户统计", fields: ["账户总数", "启用账户", "锁定账户", "实例范围", "账户来源", "分类", "规则命中"] }],
    filters: ["刷新"],
    actions: ["刷新"],
    apiPaths: ["/api/v1/accounts/statistics/summary", "/api/v1/accounts/statistics/db-types", "/api/v1/accounts/statistics/classifications", "/api/v1/accounts/statistics/rules"]
  },
  {
    consolePath: "/database-statistics",
    legacyPath: "/databases/statistics",
    title: "数据库统计",
    sections: [{ title: "数据库统计", fields: ["数据库总数", "状态分布", "类型分布", "容量排行", "同步状态"] }],
    filters: ["刷新"],
    actions: ["刷新"],
    apiPaths: ["/api/v1/databases/statistics"]
  },
  {
    consolePath: "/scheduler",
    legacyPath: "/scheduler/",
    title: "定时任务",
    sections: [{ title: "任务卡片", fields: ["任务名称", "状态", "下次运行", "上次运行", "任务 ID", "触发器参数", "操作"] }],
    filters: ["全部任务", "运行中", "已暂停"],
    actions: ["新增任务", "重载任务", "暂停任务", "恢复任务", "立即执行", "编辑任务", "删除任务"],
    apiPaths: ["/api/v1/scheduler/jobs", "/api/v1/scheduler/jobs/actions/reload"]
  },
  {
    consolePath: "/sync-sessions",
    legacyPath: "/history/sessions/",
    title: "会话中心",
    sections: [{ title: "同步会话列表", fields: ["运行ID", "状态", "进度", "任务", "来源", "分类", "开始时间", "耗时", "操作"] }],
    filters: ["来源", "分类", "状态"],
    actions: ["查看详情", "取消任务"],
    apiPaths: ["/api/v1/sync-sessions", "/api/v1/sync-sessions/{session_id}", "/api/v1/sync-sessions/{session_id}/error-logs"]
  },
  {
    consolePath: "/logs",
    legacyPath: "/history/logs/",
    title: "日志中心",
    sections: [{ title: "日志列表", fields: ["时间", "级别", "模块", "消息", "请求ID", "用户", "操作"] }],
    filters: ["级别", "模块", "时间范围", "搜索"],
    actions: ["查看详情"],
    apiPaths: ["/api/v1/logs", "/api/v1/logs/statistics", "/api/v1/logs/modules", "/api/v1/logs/{log_id}"]
  },
  {
    consolePath: "/account-change-logs",
    legacyPath: "/history/account-change-logs/",
    title: "变更历史",
    sections: [{ title: "变更列表", fields: ["时间", "账户", "实例", "变更类型", "摘要", "操作人", "操作"] }],
    filters: ["时间范围", "变更类型", "搜索"],
    actions: ["查看详情"],
    apiPaths: ["/api/v1/account-change-logs", "/api/v1/account-change-logs/statistics", "/api/v1/account-change-logs/{log_id}"]
  },
  {
    consolePath: "/users",
    legacyPath: "/users/",
    title: "用户管理",
    sections: [{ title: "用户列表", fields: ["ID", "用户", "角色", "状态", "创建时间", "操作"] }],
    filters: ["搜索", "角色", "状态"],
    actions: ["新建用户", "编辑用户", "删除用户"],
    apiPaths: ["/api/v1/users", "/api/v1/users/{user_id}", "/api/v1/users/stats"]
  },
  {
    consolePath: "/settings",
    legacyPath: "/admin/system-settings",
    title: "系统设置",
    sections: [
      { title: "邮件告警", fields: ["SMTP", "发件人", "告警开关", "测试邮件", "飞书测试"] },
      { title: "风险规则", fields: ["规则键", "严重级别", "启用状态"] },
      { title: "JumpServer", fields: ["Provider", "地址", "凭据", "同步状态"] },
      { title: "Veeam", fields: ["数据源", "主机", "凭据", "启用状态"] },
      { title: "AD 域配置", fields: ["域名", "凭据", "启用状态", "测试连接"] }
    ],
    filters: ["设置分区"],
    actions: ["保存", "测试邮件", "飞书测试", "同步 JumpServer", "同步 Veeam", "测试 AD", "同步 AD"],
    apiPaths: ["/api/v1/alerts/email-settings", "/api/v1/risk-center/rules", "/api/v1/integrations/jumpserver/source", "/api/v1/integrations/veeam/sources", "/api/v1/ad-domain-configs"]
  },
  {
    consolePath: "/credentials",
    legacyPath: "/credentials/",
    title: "凭据管理",
    sections: [{ title: "凭据列表", fields: ["凭据", "类型", "数据库类型", "状态", "绑定实例", "创建时间", "操作"] }],
    filters: ["搜索", "凭据类型", "数据库类型", "状态"],
    actions: ["新建凭据", "编辑凭据", "删除凭据"],
    apiPaths: ["/api/v1/credentials", "/api/v1/credentials/{credential_id}"]
  },
  {
    consolePath: "/tags",
    legacyPath: "/tags/",
    title: "标签管理",
    sections: [
      { title: "标签统计", fields: ["全部标签", "启用率", "停用率", "标签分类"] },
      { title: "标签列表", fields: ["标签", "分类", "状态", "关联", "操作"] }
    ],
    filters: ["搜索", "标签分类", "状态"],
    actions: ["新建标签", "编辑标签", "删除标签", "批量分配"],
    apiPaths: ["/api/v1/tags", "/api/v1/tags/categories", "/api/v1/tags/{tag_id}"]
  },
  {
    consolePath: "/partitions",
    legacyPath: "/partition/",
    title: "分区管理",
    sections: [
      { title: "分区统计", fields: ["分区总数", "总大小", "总记录数", "健康状态"] },
      { title: "分区列表", fields: ["分区", "表", "类型", "大小", "记录", "状态"] },
      { title: "核心指标", fields: ["周期", "指标曲线", "时间范围"] }
    ],
    filters: ["搜索", "表类型", "状态"],
    actions: ["创建分区", "清理旧分区", "刷新", "切换指标周期"],
    apiPaths: ["/api/v1/partitions/info", "/api/v1/partitions", "/api/v1/partitions/actions/cleanup", "/api/v1/partitions/core-metrics"]
  },
  {
    consolePath: "/instances/:instanceId",
    legacyPath: "/instances/<instance_id>",
    title: "实例详情",
    sections: [
      { title: "基本信息", fields: ["实例名称", "数据库类型", "主机地址", "端口", "实例 ID", "数据库版本", "标签", "实例描述"] },
      { title: "快速操作", fields: ["测试连接", "同步账户", "同步容量", "同步审计", "同步备份", "编辑实例", "移入回收站"] },
      { title: "数据标签页", fields: ["账户", "AG 账户", "容量", "审计", "备份"] }
    ],
    filters: ["账户筛选", "容量筛选", "审计筛选"],
    actions: ["测试连接", "同步账户", "同步容量", "同步审计", "同步备份", "查看权限", "查看变更历史", "编辑实例", "删除实例"],
    apiPaths: ["/api/v1/instances/{instance_id}", "/api/v1/instances/{instance_id}/actions/sync-accounts", "/api/v1/instances/{instance_id}/actions/sync-capacity", "/api/v1/instances/{instance_id}/audit-info", "/api/v1/instances/{instance_id}/backup-info"]
  },
  {
    consolePath: "/tags/bulk/assign",
    legacyPath: "/tags/bulk/assign",
    title: "标签批量分配",
    sections: [
      { title: "选择实例", fields: ["实例", "数据库类型", "已选数量"] },
      { title: "选择标签", fields: ["标签", "分类", "已选数量"] },
      { title: "当前选择", fields: ["已选实例", "已选标签", "执行进度"] }
    ],
    filters: ["分配模式", "移除模式", "实例搜索", "标签搜索"],
    actions: ["分配模式", "移除模式", "清空选择", "执行操作"],
    apiPaths: ["/api/v1/tags/bulk/instances", "/api/v1/tags/bulk/tags", "/api/v1/tags/bulk/actions/assign", "/api/v1/tags/bulk/actions/remove-all"]
  },
  {
    consolePath: "/sync-sessions/:sessionId",
    legacyPath: "/history/sessions/<session_id>",
    title: "会话详情",
    sections: [{ title: "会话详情", fields: ["运行ID", "状态", "进度", "任务", "详情", "错误日志"] }],
    filters: ["错误日志"],
    actions: ["取消任务", "返回列表"],
    apiPaths: ["/api/v1/sync-sessions/{session_id}", "/api/v1/sync-sessions/{session_id}/error-logs", "/api/v1/sync-sessions/{session_id}/actions/cancel"]
  },
  {
    consolePath: "/logs/:logId",
    legacyPath: "/history/logs/<log_id>",
    title: "日志详情",
    sections: [{ title: "日志详情", fields: ["时间", "级别", "模块", "消息", "上下文", "异常堆栈"] }],
    filters: ["无"],
    actions: ["返回列表"],
    apiPaths: ["/api/v1/logs/{log_id}"]
  }
];

export function parityByConsolePath(consolePath: string): LegacyParityPage | undefined {
  return legacyParityPages.find((page) => page.consolePath === consolePath);
}
