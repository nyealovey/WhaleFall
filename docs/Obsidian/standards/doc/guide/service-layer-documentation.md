---
title: 服务层文档标准(Service Docs)
aliases:
  - service-layer-documentation-standards
  - service-docs-standards
tags:
  - standards
  - standards/backend
  - standards/docs
  - standards/doc
status: active
enforcement: guide
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: app/services/** 的服务层设计与实现说明文档
related:
  - "[[standards/doc/guide/documentation]]"
  - "[[standards/core/guide/halfwidth-characters]]"
  - "[[standards/backend/standard/write-operation-boundary]]"
  - "[[standards/backend/standard/action-endpoint-failure-semantics]]"
  - "[[standards/backend/standard/error-message-schema-unification]]"
  - "[[reference/service/accounts-sync-permission-manager|示例: AccountPermissionManager 权限同步文档]]"
---

# 服务层文档标准(Service Docs)

> [!note] 目标
> 让读者在 30 秒内回答 4 个问题: 这段服务做什么, 谁调用它, 依赖什么, 失败/兼容语义是什么.

## 目的

- 统一 `app/services/**` 相关服务文档的最小可扫描结构, 降低 review 与维护成本.
- 强制显式化事务边界/失败语义/兼容逻辑, 避免知识只存在于代码与口口相传.

## 1. 适用范围

- 适用对象: `app/services/**` 下的 service/manager/orchestrator/read_service/write_service.
- 适用文档位置: `docs/Obsidian/reference/service/**` 或 `docs/Obsidian/architecture/**`(按用途选择).
  - reference/service: 偏实现与落地细节(流程, 失败语义, 监控, 决策表).
  - Architecture: 偏设计与边界(为什么这样做, 关键约束, 与其他域的关系).

## 2. 文档放置与命名

- 文件名: 英文 `kebab-case.md`, 推荐: `<domain>-<service-name>.md`.
  - 例: `accounts-sync-permission-manager.md`.
- 标题(title): 中文 + 明确对象, 避免 "杂项/临时/备忘录".
- `scope`: 必须指向主实现文件(或入口文件)路径, 例如 `scope: app/services/foo/bar_service.py`.
- `related`: 仅链接 SSOT 或强相关文档, 避免无限深的引用链.

## 3. 元信息(frontmatter)要求

除索引类 README 外, service docs 必须包含 YAML frontmatter, 且至少包含:

- `title`, `aliases`(至少 1 个), `tags`, `status`, `created`, `updated`, `owner`, `scope`, `related`.
- tags 推荐组合:
  - 必选: `service` 或 `architecture`(按文档目录选其一)
  - 可选: `services`, `services/<domain>`, `service/<domain>`, `diagram`, `decision-table`

## 4. 规则(必填结构, 最小章节)

> [!important] 约束
> 禁止只写大段文字. 必须包含可扫描的信息结构(列表/表格/图/决策表), 并能定位到代码入口.

### 4.1 概览(Overview)

- 这个服务解决的问题是什么.
- 核心职责边界(做什么/不做什么).
- 入口方法/函数(签名 + 调用方), 例如:
  - `FooService.run(instance_id, ...)`
  - `BarManager.synchronize(instance, ...)`
- 持久化影响: 读/写哪些表, 主要字段/列, 版本化字段(如 `snapshot.version`).

### 4.2 依赖与边界(Dependencies)

列出上下游依赖, 建议用表格:

| 类型 | 组件 | 用途 | 失败语义(摘要) |
| --- | --- | --- | --- |
| Caller | `AccountsSyncService` | 触发同步 | 失败是否中断批次 |
| DB | PostgreSQL | 主存储 | 事务边界 |
| Cache | Redis | 规则缓存 | miss 时回源策略 |
| External | none / <name> | 外部依赖 | 重试/超时 |

### 4.3 事务与失败语义(Transaction + Failure Semantics)

- 事务边界必须写清:
  - 路由层 `safe_route_call` commit/rollback, 或任务层 `app.app_context()`.
  - service 内部是否使用 `db.session.begin_nested()`.
  - "部分成功" vs "全量回滚" 的策略.
- 错误口径必须写清:
  - 业务失败: 返回 `success=false`(如存在).
  - 异常失败: 抛 `AppError/SystemError` 的 message_key/status_code/category/severity(至少写 message_key + status_code).

### 4.4 主流程图(Flow)

- 必须提供一张 flowchart(泳道图优先), 聚焦主链路.
- 约束:
  - 只画关键节点, 细节用注释/表格补充.
  - 循环体禁止展开到 "每条记录的每个字段" 级别.

### 4.5 时序图(Sequence)

- 当服务包含多组件交互(Repo/Cache/Builder/DB/Log)时, 必须提供一张 sequence.
- 约束:
  - 循环用 "loop each ..." 表示, 不把 3 层以上嵌套循环画全.
  - "写 DB" 建议聚合到 1 个节点(例如 "bulk insert assignments"), 不展开每行 SQL.

### 4.6 决策表/规则表(Decision Table)

当服务存在规则生成/差异计算/权限归一化/分类匹配等逻辑时, 必须提供决策表.

最低要求:
- 输入字段与归一化规则.
- 规则命中条件.
- 输出结构(schema), 包含版本号与未知字段处理策略.

### 4.7 兼容/防御/回退/适配逻辑(必须显式列出)

> [!warning] 强制要求
> 任何兼容/兜底/回退/适配逻辑都必须被文档化, 并附带清理条件. 这部分是后续删除遗留逻辑的唯一入口.

用表格列出, 推荐字段:

| 位置(文件:行号) | 类型 | 描述 | 触发条件 | 清理条件/期限 |
| --- | --- | --- | --- | --- |
| `app/.../x.py:123` | 兼容 | 字段别名, `data.get("new") or data.get("old")` | 旧数据仍存在 | 迁移完成后删除 |
| `app/.../y.py:45` | 防御 | guard clause, 避免 None 崩溃 | 上游可能传空 | 上游修复并加测试 |
| `app/.../z.py:67` | 回退 | failover 到备用实现 | 主依赖不可用 | 去掉旧依赖后删除 |

特别关注(必须写清原因):
- `or`/`||` 兜底, 例如 `a or b`, `data.get("new") or data.get("old")`.
- 静默吞异常后继续执行(必须解释为什么允许).
- 版本化/迁移/序列化/反序列化相关分支.

### 4.8 可观测性(Logs + Metrics)

- 日志:
  - event name(固定字符串), 关键字段(例如 instance_id, db_type, username, session_id).
  - error 日志是否包含 `error_type`/`error_message`.
- 指标(如有):
  - counter/gauge/histogram 名称.
  - label 维度约束(避免高基数).

### 4.9 测试与验证(Tests)

- 必须列出最小验证命令与范围:
  - unit: `uv run pytest -m unit tests/unit/...`
  - lint/typecheck(如涉及签名/类型): `make typecheck`
- 必须列出关键用例:
  - happy path
  - 失败语义(业务失败 vs exception)
  - 兼容/兜底分支(如果存在)


## 正反例

### 正例: 第一屏可回答关键问题

- frontmatter 完整, `scope` 能定位主入口文件.
- Overview 写清职责边界与入口方法/调用方.
- Transaction + Failure Semantics 写清事务边界与业务失败/异常口径.
- 兼容/兜底逻辑单独列出, 且给出清理条件/期限.

### 反例: 只有长段文字或缺失关键语义

- 未写事务边界/失败语义, review 无法判断 "失败是否回滚/是否可重试".
- 兼容/兜底分支散落在段落中, 无法追踪与清理.

## 5. 门禁/检查方式(Review Checklist)

- 是否标明入口与调用方.
- 是否写清事务边界与失败语义.
- 是否列出所有兼容/兜底逻辑与清理条件.
- 图是否可读(循环是否被折叠, 是否存在 3 层以上嵌套).
- 是否给出可执行的验证命令.

## 变更历史

- 2026-01-09: 初版, 定义 service docs 最小结构与审查清单.
- 2026-01-09: 补齐 standards 可扫描结构(目的/规则/正反例/门禁/变更历史).
