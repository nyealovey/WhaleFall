# 数据库容量同步过滤规则重构文档

## 1. 背景与目标

- 账户同步已经使用 `account_filters.yaml` + `AccountSyncFilterManager` 构建了一套可配置、可扩展、可审计的过滤体系，能够在同步前剔除系统账号、临时账号等冗余数据。
- 数据库容量同步仍然依赖散落在代码中的硬编码条件，不同数据库类型（MySQL、PostgreSQL、SQL Server、Oracle）缺乏统一的过滤入口，也无法按环境差异快速调整规则。
- 本次重构目标是在容量同步流程中复用账户同步的核心理念，提供一套**集中配置、多维过滤、可观测**的数据库过滤能力，并支持后续定制化拓展（例如分环境开关、灰度发布）。

## 2. 现状复盘：账户过滤体系的关键能力

| 能力 | 说明 | 对数据库过滤的启发 |
| --- | --- | --- |
| 配置驱动 | `account_filters.yaml` 提供按数据库类型划分的默认规则 | 新增 `database_filters.yaml`，遵循相同的版本字段、描述字段以及 per-dbtype 节点，便于统一加载。 |
| 过滤管理器 | `AccountSyncFilterManager` 封装加载、缓存、验证、匹配逻辑 | 设计 `DatabaseSyncFilterManager`，保持 API 风格一致（如 `should_exclude`, `list_effective_rules`）。 |
| 可组合条件 | 支持显式包含/排除、前缀匹配、正则表达式 | 规则只针对数据库名称及其命名模式。 |
| 查询构建器 | `SafeQueryBuilder` 提供链式构建安全 SQL 条件 | 需要扩展以生成数据库过滤相关的 WHERE 子句，避免手写字符串。 |
| 诊断能力 | 同步日志记录命中规则、统计被过滤数量 | 容量同步应当输出数据库级过滤日志，便于排查误删；同时暴露指标供监控。 |

## 3. 设计原则

1. **配置优先**：所有默认过滤逻辑放在配置文件，不在代码里硬编码；运行时从配置派生规则。
2. **最小惊讶**：过滤规则的优先级和账户过滤保持一致（`include_only` > 明确排除 > 模式匹配）。
3. **易于审计**：日志中包含被排除对象、命中规则类型、配置来源；提供调试 CLI/接口用于预览过滤结果。
4. **安全可靠**：所有动态条件走参数化查询；对 YAML 做 结构校验，防止配置格式错误导致同步失败。
5. **可扩展**：预留环境维度（例如 `defaults`、`production`、`test` 覆盖）。

## 4. 配置文件设计

### 4.1 文件位置
`app/config/database_filters.yaml`

### 4.2 建议结构

```yaml
version: "1.0"
description: "数据库容量同步过滤规则"

database_filters:
  mysql:
    description: "MySQL 默认过滤"
    exclude_databases:
      - information_schema
      - performance_schema
      - mysql
      - sys
    exclude_patterns:
      - "tmp_%"
      - "temp_%"
      - "#sql%"
    
  postgresql:
    description: "PostgreSQL 默认过滤"
    exclude_databases:
      - template0
      - template1
      - postgres
    exclude_patterns:
      - "pg_%"

  sqlserver:
    description: "SQL Server 默认过滤"
    exclude_databases:
      - master
      - model
      - msdb
      - tempdb
    exclude_patterns:
      - "ReportServer%"

  oracle:
    description: "Oracle 默认过滤"
    exclude_patterns:
      - "SYS%"
      - "SYSTEM%"
```

> 说明：
> - 示例中的系统库列表可按需扩展。

## 5. 核心组件改造

### 5.1 DatabaseSyncFilterManager（新）

| 功能 | 说明 |
| --- | --- |
| 加载 & 校验配置 | 读取 YAML，校验必填字段、类型、重复项；提供简单的缓存。 |
| 过滤判定 | 提供 `should_exclude_database(instance, database_name)` 方法，返回命中规则及原因。 |
| 生成查询片段 | 暴露 `build_database_conditions(builder)`，将规则注入 `SafeQueryBuilder`。 |
| 统计 & 日志 | 记录过滤命中数、最近一次命中规则；支持导出 Prometheus 指标或写入结构化日志。 |

### 5.2 SafeQueryBuilder 扩展

- 新增 `add_database_filters(filters: Iterable[str])` 等方法，复用现有参数化模式。
- 调整 QueryBuilder 使其支持组合 AND/OR 条件，并保证跨数据库语法兼容（尤其是 SQL Server 与 Oracle）。

### 5.3 容量同步流程集成

| 阶段 | 集成要点 |
| --- | --- |
| 数据库发现 (`DatabaseInventoryManager`) | 在拉取实例数据库列表时应用过滤，避免在后续阶段处理无关项。 |
| 容量采集 (`DatabaseSizeCollectorService`) | 在统计前应用过滤结果，跳过已被排除的数据库并记日志。 |
| 结果汇总 (`CapacityPersistence`) | 确保过滤器返回的“跳过”信息写入日志，以便平台 UI 显示。 |

## 6. 新增功能：数据库级过滤能力

1. **按数据库名称过滤**：支持精确名称 & 模式匹配；顺序与账户过滤保持一致，先处理 `include_only` 白名单，再执行排除列表与正则。
2. **调试预览**：提供 CLI `flask database-filters preview --instance gf-imsdb-01l`（后续实现），打印当前实例的过滤命中情况。该工具将帮助验证配置，防止误排除业务库。

## 7. 实施步骤

### 阶段 A：基础设施
1. 定义 `database_filters.yaml` 初版，梳理默认排除项。
2. 新建 `DatabaseSyncFilterManager`，实现配置加载与缓存接口。
3. 扩展 `SafeQueryBuilder` 支持数据库级过滤表达式。
4. 提供配置 Schema 校验（使用 `pydantic` / `marshmallow`）。

### 阶段 B：服务改造
1. 在 `DatabaseInventoryManager`、`DatabaseSizeCollectorService` 中注入过滤器。
2. 调整 `CapacityPersistence`，记录过滤统计，并暴露到结构化日志。
3. 更新 `collect_database_sizes` 任务，增加过滤命中指标。

### 阶段 C：测试与验证
1. 单元测试：覆盖配置加载、 include/exclude 优先级。
2. 集成测试：使用 SQLite / dummy 驱动模拟多库场景，验证过滤后的采集结果。
3. 回归测试：确保账号过滤模块不受影响；确认数据库过滤开启后容量统计与 UI 显示一致。

### 阶段 D：上线与推广
1. 预发布环境灰度，观察过滤命中日志与容量指标。
2. 线上启用后观察 24 小时，确认无业务库被误排除。
3. 编写运维手册，指导如何调整 `database_filters.yaml` 和如何使用调试工具。

## 8. 监控与日志

- **日志字段**：`filter_scope`（database）、`filter_rule`（命中规则 ID）、`source`（配置文件路径）、`action`（skipped/allowed）。
- **指标**：每实例每日被过滤数据库数、命中 `include_only` 的数量。
- **审计**：保留最近一次配置加载时间和版本号（`version` 字段），在 UI/接口上可见。

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 配置过度排除业务库 | 容量统计缺失 | 默认仅排除系统库；上线前通过预览命令确认；支持快速回滚至禁用过滤。 |
| 不同数据库语法差异 | 过滤条件失效 | QueryBuilder 层封装数据库特定语句；单元测试覆盖多数据库方言。 |
| 配置热更新失败 | 旧配置持续生效 | 提供版本号对比与拉取失败报警；必要时允许手工 reload。 |

## 10. 成功标准

1. 过滤模块上线后，系统库和临时库不再出现在容量报表中。
2. 同步耗时与资源使用不超过当前基线的 105%。
3. 运维人员可在 5 分钟内通过配置调整过滤规则并验证结果。
4. 过滤命中率与日志统计可在监控面板中查看。
5. 新增功能对账户同步模块无回归影响（CI 单测通过）。

## 11. 后续规划

- **环境覆盖**：支持按实例标签/环境维度套用不同过滤配置。
- **可视化配置**：在前端提供规则 CRUD，集成 YAML 模板导出/导入。
- **智能推荐**：基于容量统计自动推荐过滤候选库（例如长期 0 MB 的库）。
- **自动化校验**：在部署 pipeline 中增加配置 lint，确保上线前校验通过。

---

*本文档将随着实施进展持续更新和完善。*
