# 后端削减兼容/回退代码清单与收敛方案（基于 2025-12-18）

> 目标：系统性识别并削减“为旧接口/旧数据/旧依赖保留”的兼容与回退路径，降低复杂度与分支数量，缩小回归面，便于后续持续减码与质量门禁落地。

## 1. 前置结论：先定“支持矩阵”，否则无法判断哪些能删

### 1.1 运行时基线（仓库声明）
- Python：`>=3.11`（见 `pyproject.toml`）
- Flask：`>=3.1.2`（见 `pyproject.toml`）
- SQLAlchemy：`>=2.0.43`（见 `pyproject.toml`）
- APScheduler：`>=3.11,<3.12`（见 `pyproject.toml`）

### 1.2 本文“兼容/回退”定义（用于收敛）
- **兼容代码**：为了适配“旧路径/旧参数/旧返回结构/旧数据格式/旧依赖版本”等而保留的分支、别名、包装器、双写双读。
- **回退代码**：当新路径不可用或失败时，退回旧路径/旧实现/降级策略的逻辑（包含容灾型降级，但需单独标注为“可靠性降级”）。

> 说明：纯粹的“输入校验兜底”（例如无法解析则返回默认值）不一定属于“兼容/回退”。但如果它明显是为旧行为保留（例如旧字段/旧返回结构仍在流通），也纳入清单供你审查。

## 2. 尽可能“找全”的方法（可复跑）

### 2.1 关键词扫描（仅 Python）
用于抓到显式标注的兼容/旧版/回退/降级。
```bash
rg -n --hidden --type py -S "\\b(compat|compatibility|legacy|deprecated|fallback|workaround|shim)\\b|兼容|向后兼容|旧版|旧接口|历史版本|回退|降级" app
```

### 2.2 路由参数别名扫描（模式）
用于抓到 `search/q`、`per_page/limit`、`sort/sort_by`、`order/sort_order`、`tags list/comma` 等兼容。
```bash
rg -n -P "args\\.get\\(\\\"[A-Za-z0-9_]+\\\"\\)\\s*or\\s*args\\.get\\(\\\"[A-Za-z0-9_]+\\\"\\)" app/routes
rg -n "request.args.get(\"search\") or request.args.get(\"q\")" app/routes
comm -12 <(rg -l "per_page" app/routes | sort) <(rg -l "\\blimit\\b" app/routes | sort)
```

### 2.3 可选依赖/版本兼容扫描
用于抓到 try-import / ModuleNotFoundError / “运行环境可能未安装”一类兼容。
```bash
rg -l --type py "optional dependency|运行环境可能未安装|未安装|ModuleNotFoundError|ImportError" app | sort
```

### 2.4 `or`/`||` 兜底与数据结构兼容扫描（仅 Python）
用于抓到“字段别名、返回结构差异、默认值兜底、SQL 字符串中的 `||`”等隐式兼容/防御逻辑。
```bash
# 1) 字段别名 / 返回结构兼容：data.get('new') or data.get('old')
rg -n --hidden --type py -P "\\b\\w+\\.get\\(\\s*['\\\"][^'\\\"]+['\\\"][^\\)]*\\)\\s*or\\s*\\w+\\.get\\(\\s*['\\\"][^'\\\"]+['\\\"][^\\)]*\\)" app

# 2) 默认值兜底：payload.get('x') or {} / [] / ""
rg -n --hidden --type py -P "\\.get\\([^\\n\\)]*\\)\\s*or\\s*(\\{\\}|\\[\\]|\\\"\\\"|''|0)" app

# 3) JSON 请求体兜底：request.get_json(...) or {}
rg -n --hidden --type py -S "request\\.get_json\\([^\\)]*\\)\\s*or\\s*\\{\\}" app/routes

# 4) 环境变量别名：os.getenv(A) or os.getenv(B)
rg -n --hidden --type py -P "os\\.(getenv|environ\\.get)\\(\\\"[^\\\"]+\\\"\\)\\s*or\\s*os\\.(getenv|environ\\.get)\\(\\\"[^\\\"]+\\\"\\)" app

# 5) 注意：Python 源码里的 `||` 通常是 SQL 字符串拼接（不是逻辑兜底）
rg -n --hidden --type py "\\|\\|" app
```

## 3. 防御/兼容/回退/适配逻辑清单（Python, 基于 2025-12-18 扫描）

> 输出格式：每条都给出“位置/类型/描述/建议”，便于你直接逐条点开审查与删减。

### 3.1 数据结构兼容（字段别名/字段迁移/返回结构差异，关注 `or` 兜底）

> 注：`error/message` 字段漂移已按 `docs/refactor/backend_error_message_schema_unification.md` 统一并清零命中；
> 门禁脚本 `./scripts/code_review/error_message_drift_guard.sh` 用于禁止回归。

- 位置：`app/__init__.py:223`
  - 类型：兼容（已删除）
  - 描述：已取消 `SQLALCHEMY_DATABASE_URI` 环境变量的兼容读取，仅支持 `DATABASE_URL`。
  - 建议：清理部署环境中的旧变量，仅保留 `DATABASE_URL`（否则会回退到默认 SQLite 开发库）。

- 位置：`app/utils/logging/handlers.py:160`
  - 类型：防御
  - 描述：日志模块字段兜底：`module` 缺失时尝试从 `logger` 名推断，并 `or` 兜底为 `"app"`。
  - 建议：若 structlog pipeline 已强制填充 `module`，可移除推断逻辑；否则保留但监控缺失率并在告警中提示。

- 位置：`app/utils/logging/handlers.py:161`
  - 类型：兼容（已删除）
  - 描述：已统一采用 `event` 作为日志消息字段来源，不再从 `message` 键兜底读取。
  - 建议：全仓库与 structlog pipeline 统一只写 `event`；如仍有第三方库写入 `message`，应在上游适配（而不是在 DB 写入层做兼容）。

- 位置：`app/routes/files.py:504`
  - 类型：兼容（已删除）
  - 描述：已统一标签展示字段为 `display_name`，不再从旧字段 `name` 兜底读取。
  - 建议：确保导出/渲染链路输出的标签结构始终包含 `display_name`（必要时在上游序列化阶段补齐），避免因缺字段导致导出内容为空。

- 位置：`app/services/account_classification/classifiers/oracle_classifier.py:147`
  - 类型：兼容（已删除）
  - 描述：Oracle 权限快照角色字段统一为 `oracle_roles`，不再从 `roles` 兜底读取。
  - 建议：接口与前端仅消费 `oracle_roles`；清理任何残留的 `roles` 输出，避免旧键继续流通。

- 位置：`app/services/account_classification/classifiers/oracle_classifier.py:163`
  - 类型：兼容（已删除）
  - 描述：Oracle 系统权限字段统一为 `oracle_system_privileges`，不再兼容 `system_privileges` 等旧键。
  - 建议：后端输出与前端渲染统一使用 `oracle_system_privileges`；如需与规则表达式字段区分（`system_privileges`），建议仅在“权限快照”层使用前缀。

- 位置：`app/services/account_classification/classifiers/oracle_classifier.py:227`
  - 类型：兼容（已删除）
  - 描述：Oracle 表空间权限字段统一为 `oracle_tablespace_privileges`，不再兼容 `tablespace_privileges_oracle/tablespace_privileges` 等旧键。
  - 建议：后端输出与前端渲染统一使用 `oracle_tablespace_privileges`；后续如要进一步与 DB 字段对齐，可评估是否重命名持久化列（需 migration）。

- 位置：`app/services/accounts_sync/adapters/mysql_adapter.py:349`
  - 类型：兼容（已删除）
  - 描述：已统一 `original_username/host` 仅存放于 `permissions.type_specific`，不再从账户顶层字段兜底读取。
  - 建议：如仍存在外部调用方拼装“顶层 original_username/host”的旧 payload，应同步改为写入 `permissions.type_specific`（否则会因缺字段跳过权限补全）。

- 位置：`app/tasks/capacity_aggregation_tasks.py:108`
  - 类型：数据特定（已删除）
  - 描述：已统一聚合结果的记录数指标键为 `processed_records`，不再兼容 `total_records/aggregations_created` 的 `or` 兜底链。
  - 建议：如仍存在外部调用方读取旧键，请同步改为读取 `processed_records`，避免统计字段回退为 0。

- 位置：`app/tasks/capacity_aggregation_tasks.py:125`
  - 类型：兼容（已删除）
  - 描述：聚合任务结果的失败消息已统一为 `message`，不再对 `error/message` 做 `or` 互兜底。
  - 建议：保持 `message` 必填、`error` 可选用于诊断；用 `./scripts/code_review/error_message_drift_guard.sh` 防止回归。

- 位置：`app/services/accounts_sync/accounts_sync_service.py:475`
  - 类型：兼容（已删除）
  - 描述：SyncOperationResult 已保证失败分支写入 `message`，日志仅消费 `message`，不再回退 `error`。
  - 建议：保持所有失败返回包含 `message`（对外摘要）与可选 `error`（诊断详情），并依赖门禁脚本阻止新增互兜底链。

- 位置：`app/routes/accounts/sync.py:114`
  - 类型：兼容（已删除）
  - 描述：路由层规范化结果已仅消费 `message`（由上游保证 `message` 必填），不再从 `error` 兜底。
  - 建议：统一以 `docs/refactor/backend_error_message_schema_unification.md` 作为结果结构契约，避免在读端写互兜底链。

- 位置：`app/routes/databases/capacity_sync.py:229`
  - 类型：兼容（已删除）
  - 描述：容量同步失败提示已统一只读 `message`，不再在 `message/error` 间漂移并通过 `or` 兜底。
  - 建议：写端确保失败分支始终包含 `message`；如需要诊断信息，再补充可选 `error` 字段。

- 位置：`app/routes/capacity/aggregations.py:202`
  - 类型：兼容（已删除）
  - 描述：聚合回调 payload 已统一在失败时写入 `message`，路由仅消费 `message`，不再 `error/message` 互兜底。
  - 建议：runner/callback 的失败 payload 必须包含 `message`（摘要）与可选 `error`（详情），避免把漂移扩散到路由层。

- 位置：`app/routes/capacity/aggregations.py:211`
  - 类型：兼容（已删除）
  - 描述：同上：异常路径已仅消费 `message`。
  - 建议：同上。

- 位置：`app/routes/connections.py:193`
  - 类型：兼容（已删除）
  - 描述：ConnectionTestService 已统一失败返回写入 `message`，路由仅消费 `message`，不再 `error/message` 互兜底。
  - 建议：保持对外 `message` 可展示、对内 `error` 可诊断；用门禁脚本阻止新增互兜底链。

- 位置：`app/routes/connections.py:240`
  - 类型：兼容（已删除）
  - 描述：同上。
  - 建议：同上。

- 位置：`app/services/account_classification/auto_classify_service.py:133`
  - 类型：兼容（已删除）
  - 描述：分类编排器失败结果已统一写入 `message`，AutoClassifyService 仅消费 `message`，不再 `error/message` 互兜底。
  - 建议：将 `docs/refactor/backend_error_message_schema_unification.md` 作为分类引擎返回结构契约，避免在中间层扩散兼容分支。

### 3.2 运行期回退/降级（failover/failsafe/graceful degradation）

- 位置：`app/utils/rate_limiter.py:45`、`app/utils/rate_limiter.py:120`
  - 类型：回退
  - 描述：缓存速率限制检查失败时回退到内存 store（可用性优先，但会导致多实例下限流不一致）。
  - 建议：明确“强一致限流”还是“可用性优先”。若要求强一致，可改为 fail-closed（缓存不可用则拒绝/保护模式）并移除隐式降级。

- 位置：`app/utils/data_validator.py:498`
  - 类型：回退
  - 描述：动态数据库类型配置获取失败时，回退到静态白名单 `SUPPORTED_DB_TYPES`。
  - 建议：若动态配置是权威来源，应更早暴露并阻断；若静态白名单是安全兜底，应配合告警并记录失败频次。

- 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:613`、`app/services/accounts_sync/adapters/sqlserver_adapter.py:623`、`app/services/accounts_sync/adapters/sqlserver_adapter.py:1008`
  - 类型：回退
  - 描述：SQL Server 权限采集在 SID 路径无结果/不可用时回退到“按用户名查询”，避免权限为空。
  - 建议：这是“结果完整性优先”的业务兜底。若决定删除，需要确认所有目标环境都能稳定读取 SID 且不会再出现空权限场景。

- 位置：`app/scheduler.py:404`
  - 类型：回退
  - 描述：`ENABLE_SCHEDULER` 运维开关属于“止血回退路径”，可在运行期关闭调度器。
  - 建议：保留但文档化默认值与生产策略（何时允许关闭、关闭后影响范围），并在日志/监控中暴露当前开关状态。

### 3.3 兼容包装器 / 适配层（wrapper/facade/bridge）

- 位置：`app/services/database_sync/database_sync_service.py:3`、`app/services/database_sync/database_sync_service.py:40`
  - 类型：兼容
  - 描述：`DatabaseSizeCollectorService` 被标注为“历史版本兼容包装器”，内部委托 `CapacitySyncCoordinator`。
  - 建议：统一调用方直接使用协调器/新服务接口；迁移完成后删除包装器与旧命名，降低服务层分支数量。

- 位置：`app/services/aggregation/aggregation_service.py:133`
  - 类型：兼容
  - 描述：`_commit_with_partition_retry(self, _aggregation: object, ...)` 的 `_aggregation` 参数仅用于“兼容接口签名”，当前逻辑已不再需要分区重试。
  - 建议：调整 runner/callback 签名移除无用参数后删除该兼容入口，避免长期携带无效参数。

- 位置：`app/services/form_service/scheduler_job_service.py:49`
  - 类型：兼容
  - 描述：`SchedulerJobResource.__post_init__` 通过 `getattr(self.job, \"id\", \"\")` 初始化 `id`，用于兼容 APScheduler Job 接口差异。
  - 建议：若运行时 Job 总能提供 `id`，直接使用 `self.job.id` 并让类型系统兜底；否则保留并在缺失时抛出更明确的错误。

- 位置：`app/errors/__init__.py:212`
  - 类型：兼容
  - 描述：`AppValidationError = ValidationError` 属于历史别名，便于旧代码增量迁移。
  - 建议：全仓库统一改用 `ValidationError` 导入后删除别名，避免同时维护两套命名。

- 位置：`app/utils/time_utils.py:36`
  - 类型：兼容
  - 描述：`TIME_FORMATS` 被标注为“向后兼容的时间格式字典”，对外暴露 key->format 的旧式映射。
  - 建议：确认调用方是否仍依赖 `TIME_FORMATS[...]`；若已全部改为 `TimeFormats` 常量，可删除该字典并统一入口。

- 位置：`app/constants/sync_constants.py:194`
  - 类型：兼容
  - 描述：存在“向后兼容的别名”注释但当前未提供实际别名实现，属于遗留兼容标记。
  - 建议：如果确无别名需求，删除该注释；若仍需别名，补齐具体迁移计划与删除时间点，避免注释长期漂移。

### 3.4 防御与数据收敛（coercion/canonicalization）

- 位置：`app/routes/instances/detail.py:60`、`app/routes/instances/detail.py:83`
  - 类型：数据特定
  - 描述：`is_active` 输入兼容：同时支持表单/JSON/checkbox，并兼容数组值（取最后一个）与多种 truthy/falsy 字符串。
  - 建议：若前端已统一为 JSON boolean，可收敛为单一解析路径并在校验失败时返回 400；迁移期可对“非 boolean 输入”打点观测。

- 位置：`app/routes/instances/detail.py:102`
  - 类型：防御
  - 描述：`_safe_int` 无法解析时回退默认值（避免输入异常导致 500）。
  - 建议：对关键参数优先改为显式 ValidationError（400）而不是静默回退，避免错误输入被吞掉；非关键参数可保留兜底。

- 位置：`app/routes/partition.py:110`
  - 类型：防御
  - 描述：周期类型非法时回退到 `daily`（隐式纠错）。
  - 建议：如果该参数来自 UI 且应严格校验，建议改为 400 并提示可选值；若仍需容错，至少记录一次“发生过回退”的日志/计数。

- 位置：`app/services/aggregation/calculator.py:187`
  - 类型：防御
  - 描述：存在 “fallback - treat as same duration sliding window” 的兜底分支（当前在 `_normalize` 严格校验下可能不可达）。
  - 建议：确认该分支是否仍可达；若不可达，删除兜底与注释以减少死代码与误导。

- 位置：`app/services/statistics/database_statistics_service.py:282`
  - 类型：防御
  - 描述：存在“兼容字段已移除”的遗留注释，属于已完成迁移的提示信息。
  - 建议：若该注释不再提供行动价值，删除以降低噪声；需要保留时可改为 changelog/PR 记录，避免长期驻留在代码中。

### 3.5 `||` 命中说明（Python 源码内多为 SQL 语法, 非逻辑兜底）

- 位置：`app/services/accounts_sync/adapters/oracle_adapter.py:334`
  - 类型：数据特定
  - 描述：SQL 文本中使用 `||` 做字符串拼接（Oracle/PostgreSQL 语法），不是 Python 的兜底运算符。
  - 建议：在做“兜底扫描”时将 SQL 字符串命中单独看待，避免误判为逻辑回退。

- 位置：`app/services/partition_management_service.py:485`
  - 类型：数据特定
  - 描述：同上：PostgreSQL SQL 文本中 `schemaname||'.'||tablename` 为拼接表达式。
  - 建议：同上。

- 位置：`app/services/partition_management_service.py:486`
  - 类型：数据特定
  - 描述：同上：`pg_total_relation_size(schemaname||'.'||tablename)` 为拼接表达式。
  - 建议：同上。

## 4. 建议的收敛路线（避免“一刀切”回归）

### 4.1 分阶段策略（建议）
1. **观测期（不改行为）**
   - 对“旧字段/旧 key/旧返回结构”加结构化日志埋点或计数器（例如 `used_legacy_key=true`）。
2. **迁移期（改调用方，不删后端兼容）**
   - 前端/脚本/任务统一改用 canonical schema（例如统一只用 `error` 或只用 `message`；统一 `processed_records`）。
3. **收口期（删除兼容与回退壳）**
   - 删除后端别名/旧入口/旧字段兜底分支；同步删对应测试与文档。
4. **稳定期（门禁固化）**
   - 在 code review 门禁中新增约束：禁止再引入 `error/message` 双制式、`.get('new') or .get('old')` 兼容兜底等隐式分支（除非提供明确的迁移计划与删除时间点）。

### 4.2 删除前的“最小核验清单”（建议写进 PR 模板）
- 路由：确认 templates/JS 不再引用旧路径；必要时加 access log 证据。
- 参数：全链路只发送一套参数命名；接口对旧参数返回明确错误（或 400 + 提示）。
- 数据：字段别名/旧 key 已迁移（例如 `display_name/name`、`error/message`、`processed_records/total_records`）。
- 依赖：数据库驱动是否视作强依赖（缺失时是否允许启动），以及运维开关/降级路径的取舍有明确决定。

## 5. 附录：自动扫描命中列表（便于你逐条点开审查）

### 5.1 Python 关键词命中（兼容/旧版/回退/降级）
> 生成命令见 2.1。
```text
app/services/accounts_sync/adapters/oracle_adapter.py:319:        兼容 Oracle 11g 及以上版本.
app/services/statistics/database_statistics_service.py:282:            # 兼容字段已移除
app/services/form_service/scheduler_job_service.py:49:        """初始化资源 id,兼容 apscheduler Job 接口."""
app/services/accounts_sync/adapters/sqlserver_adapter.py:613:                # 若 SID 路径未返回任何角色/权限,尝试按用户名回退
app/services/accounts_sync/adapters/sqlserver_adapter.py:623:                # 回退到基于用户名的查询,避免因无法读取 SID 而导致权限为空
app/services/accounts_sync/adapters/sqlserver_adapter.py:1008:        """基于用户名回退查询数据库权限,用于无法读取 SID 的场景."""
app/errors/__init__.py:290:    抛出后提醒调用方重试或降级,默认返回 502.
app/utils/time_utils.py:36:# 向后兼容的时间格式字典
app/utils/time_utils.py:167:            format_str: strftime 兼容格式,默认为 `%Y-%m-%d %H:%M:%S`.
app/services/database_sync/database_sync_service.py:3:该模块提供与历史版本兼容的 `DatabaseSizeCollectorService`,内部委托
app/services/database_sync/database_sync_service.py:40:    """数据库容量采集服务(兼容包装器).
app/services/database_sync/database_sync_service.py:42:    提供与历史版本兼容的接口,内部委托给 CapacitySyncCoordinator 实现.
app/utils/rate_limiter.py:45:    当缓存不可用时自动降级到内存模式.
app/utils/rate_limiter.py:120:                    "缓存速率限制检查失败,降级到内存模式",
app/services/aggregation/aggregation_service.py:133:            _aggregation: 聚合结果对象,当前用于兼容接口.
app/constants/sync_constants.py:194:# 向后兼容的别名
app/routes/instances/detail.py:60:    """从请求数据中解析 is_active,兼容表单/JSON/checkbox.
app/routes/instances/detail.py:83:        # 兼容 JSON 中提供数组的情况,取最后一个
app/routes/instances/detail.py:102:    """安全解析整数,无法解析时回退默认值."""
app/utils/data_validator.py:498:            logger.warning("获取数据库类型配置失败,回退到静态白名单: %s", exc)
app/services/aggregation/calculator.py:187:        # fallback - treat as same duration sliding window
app/routes/history/logs.py:3:统一管理日志检索、统计与下发的接口,支撑控制台与旧版前端.
app/routes/partition.py:110:    """校验周期类型,非法时回退 daily."""
```

### 5.2 可选依赖/版本兼容文件清单
> 生成命令见 2.3；当前无命中（说明已清理 try-import/ImportError 兜底）。
```text
（当前无命中）
```

### 5.3 `or` 兜底命中（字段别名/返回结构差异）
> 生成命令见 2.4（第 1 条）。
```text
（当前无命中：已统一 `error/message` 字段并建立漂移门禁。）
```

### 5.4 环境变量别名命中（`or`）
> 生成命令见 2.4（第 4 条）。
```text
（当前无命中：已取消 `SQLALCHEMY_DATABASE_URI` 环境变量兼容读取，仅支持 `DATABASE_URL`。）
```

### 5.5 `||` 命中（SQL 文本, 非逻辑兜底）
> 生成命令见 2.4（第 5 条）。
```text
app/services/accounts_sync/adapters/oracle_adapter.py:334:                    ELSE TO_CHAR(max_bytes / 1024 / 1024) || ' MB'
app/services/partition_management_service.py:485:            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
app/services/partition_management_service.py:486:            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
```
