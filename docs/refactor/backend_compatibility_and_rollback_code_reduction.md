# 后端削减兼容/回退代码清单与收敛方案（基于 2025-12-17）

> 目标：系统性识别并削减“为旧接口/旧数据/旧依赖保留”的兼容与回退路径，降低复杂度与分支数量，缩小回归面，便于后续持续减码与质量门禁落地。

## 1. 前置结论：先定“支持矩阵”，否则无法判断哪些能删

### 1.1 运行时基线（仓库声明）
- Python：`>=3.11`（见 `pyproject.toml`）
- Flask：`>=3.1.2`（见 `pyproject.toml`）
- SQLAlchemy：`>=2.0.43`（见 `pyproject.toml`）
- APScheduler：`>=3.11,<3.12`（见 `pyproject.toml`）

### 1.2 本文“兼容/回退”定义（用于收敛）
- **兼容代码**：为了适配“旧路径/旧参数/旧返回结构/旧数据格式/旧依赖版本/可选依赖缺失”等而存在的分支、别名、包装器、双写双读。
- **回退代码**：当新路径不可用或失败时，退回旧路径/旧实现/降级策略的逻辑（包含容灾型降级，但需单独标注为“可靠性降级”）。

> 说明：纯粹的“输入校验兜底”（例如无法解析则返回默认值）不一定属于“兼容/回退”，但如果它明显是为旧行为保留，也纳入清单供你审查。

## 2. 尽可能“找全”的方法（可复跑）

### 2.1 关键词扫描（仅 Python）
用于抓到显式标注的兼容/旧版/回退/降级。
```bash
rg -n --hidden --type py -S "\\b(compat|compatibility|legacy|deprecated|fallback|workaround|shim)\\b|兼容|向后兼容|旧版|旧接口|历史版本|回退|降级" app
```

### 2.2 路由参数别名扫描（模式）
用于抓到“search/q、per_page/limit、sort/sort_by、order/sort_order、tags list/comma”等兼容。
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

## 3. 后端兼容/回退代码清单（按类型汇总，便于审查）

> 下述条目均是“可删候选”。是否删除取决于你是否仍需要支持对应的旧调用方/旧数据/旧环境。

### A. 路由/接口层：旧路径、旧蓝图、旧参数与旧返回结构

#### A1. 历史日志：旧 `/logs` 前缀 + 旧统计接口
- 位置：`app/routes/history/logs.py`
  - `logs_bp = Blueprint("logs", __name__)  # 兼容旧版 /logs 前缀请求`
  - `/api/stats`：`get_log_stats()` 明确标注“兼容旧前端”
  - 查询参数别名（同一套解析里同时支持多套命名）：`sort_by/sort`、`sort_order/order`、`q/search`、`per_page/limit`
  - 返回结构双制式：`/api/search` 返回 `{logs, pagination}`；`/api/list` 返回 Grid.js 风格 `{items,total,page,pages,limit}`
- 建议收敛：
  1. 明确“前端只用哪一套”：如果控制台已全量迁移到 `/history/logs/*` 与 `/api/search`，则可以删除 `logs_bp` 与 `/api/stats`。
  2. 固化参数命名：统一到 `page/per_page/sort/sort_order/search`（或你指定的一套），移除别名分支。
  3. 固化返回结构：统一到 `unified_success_response` 的 `data.pagination` 结构，逐步让前端 store 停止兼容多结构解析。

#### A2. 实例编辑：旧路径别名
- 位置：`app/routes/instances/detail.py:379`
  - `update_instance_detail_legacy()`：`/api/edit/<int:instance_id>` 的兼容别名（注释写的是旧版路径 `/instances/api/edit/<id>`）
  - 仓库内未检索到该旧路径的前端引用（仅在 docstring 出现）
- 建议收敛：加访问日志/指标 → 连续一段周期（如 30 天）无调用 → 删除该路由与相关测试/文档说明。

#### A3. 列表页/筛选：参数双写与兼容输入（集中分布）
这类兼容通常是“同一个资源同时服务两类前端/组件”，典型表现：
- `per_page` 与 `limit` 混用（同一端点兼容两套参数）
- `search` 与 `q` 混用
- `tags` 既支持 `?tags=a&tags=b` 也支持 `?tags=a,b`

文件分布（`per_page` 与 `limit` 同时出现的 routes 文件交集）：
- `app/routes/accounts/ledgers.py`
- `app/routes/capacity/instances.py`
- `app/routes/credentials.py`
- `app/routes/databases/ledgers.py`
- `app/routes/history/logs.py`
- `app/routes/history/sessions.py`
- `app/routes/instances/manage.py`
- `app/routes/tags/manage.py`
- `app/routes/users.py`

其中明确出现 `search/q` 兼容的点（示例）：
- `app/routes/instances/manage.py:76`、`app/routes/instances/manage.py:309`
- `app/routes/accounts/ledgers.py:519`（`search_override = (search or q)`）
- `app/routes/history/logs.py:121`

建议收敛（按风险从低到高）：
1. **先统一前端发参**：让所有页面只发一套参数命名（并在接口层打印“使用了别名参数”的 debug 日志，观测存量）。
2. **再移除后端别名**：删除 `q`、`limit`、`tags=comma` 等别名支持。
3. **最后统一响应结构**：避免前端 stores 继续写多结构解析。

### B. 数据模型/服务层：旧数据格式与旧调用方式兼容

#### B1. 凭据密码：bcrypt 哈希/明文历史兼容（高价值但高风险）
- 位置：`app/models/credential.py:168` 起
  - `check_password()` 同时支持：
    - bcrypt 哈希（旧格式，`$2b$` 前缀）
    - 新加密格式（Fernet 加密字符串）
    - 明文（历史遗留兜底）
  - `get_plain_password()`：bcrypt 旧格式无法解密，依赖环境变量 `DEFAULT_{DBTYPE}_PASSWORD` 作为兜底
- 建议收敛（需要数据迁移策略）：
  1. **盘点存量**：统计数据库里 `Credential.password` 的分布（bcrypt/明文/新加密）。
  2. **迁移路径**：优先把明文与 bcrypt 存量升级到新加密格式（需要用户重录或后台迁移规则）。
  3. **移除旧逻辑**：在存量清零后删除 bcrypt/明文分支与 `DEFAULT_*_PASSWORD` 兜底要求。

#### B2. 同步会话统计：`legacy_counts` 兼容旧调用方
- 位置：`app/services/sync_session_service.py:222` 起
  - `complete_instance_sync(..., stats: SyncItemStats | None = None, **legacy_counts: int)`
  - 当 `stats` 缺省时从 `legacy_counts` 拼装默认值
- 建议收敛：全仓库调用方统一改为传 `stats`（结构化对象）→ 删除 `**legacy_counts` 与相关兜底逻辑。

#### B3. 统一日志模型：兼容旧 kwargs 构造方式
- 位置：`app/models/unified_log.py:30`、`app/models/unified_log.py:145`
  - `create_log_entry(payload: LogEntryParams | None = None, **entry_fields)`
  - `LogEntryKwargs` 明确描述“兼容旧接口的关键字参数”
- 建议收敛：全仓库统一使用 `LogEntryParams` → 删除 `**entry_fields` 旧入口与相关 TypedDict。

#### B4. 统一异常：`AppError` legacy kwargs（旧构造方式兼容）
- 位置：`app/errors/__init__.py:20` 起
  - `LegacyAppErrorKwargs` 与 `AppError.__init__(..., **legacy_kwargs)`
  - `AppValidationError = ValidationError` 属于历史别名
- 建议收敛：全仓库统一使用 `options=AppErrorOptions(...)` → 删除 `LegacyAppErrorKwargs` 与 `**legacy_kwargs`。

#### B5. 缓存服务：旧名字 `cache_manager` 与 `init_cache_manager`
- 位置：`app/services/cache_service.py:484` 起
  - `cache_manager` 全局变量（注释“向后兼容”）
  - `init_cache_manager()` 兼容旧入口，内部调用 `init_cache_service()`
- 建议收敛：全仓库统一用 `cache_service`/`init_cache_service` → 删除旧别名与旧初始化函数。

#### B6. 安全查询构造：list 参数格式的向后兼容入口
- 位置：`app/utils/safe_query_builder.py:395` 起
  - `build_safe_filter_conditions_list()` 明确标注“向后兼容不支持字典参数的代码”
- 建议收敛：统一调用方接受 dict/list 两种参数格式（或统一改 dict）→ 删除 list 兼容入口。

#### B7. 数据校验器：保留函数式调用方式
- 位置：`app/utils/data_validator.py:587` 起
  - 一组函数式 wrapper（`sanitize_form_data/validate_*`）用于兼容旧调用
- 建议收敛：全仓库统一改为 `DataValidator.xxx` 类方法调用 → 删除函数式 wrapper。

#### B8. 日志队列 worker：旧关闭方法别名
- 位置：`app/utils/logging/queue_worker.py:126`
  - `shutdown()` 仅调用 `close()`，注释“兼容旧关闭接口”
- 建议收敛：统一调用 `close()` → 删除 `shutdown()`。

#### B9. 常量别名：`SyncType`
- 位置：`app/constants/sync_constants.py:194`
  - `SyncType = SyncOperationType  # 保持向后兼容`
- 建议收敛：统一改用 `SyncOperationType` → 删除别名。

#### B10. 响应工具：错误响应参数的兼容入口
- 位置：`app/utils/response_utils.py:130`
  - `jsonify_unified_error_message(..., **options)` 明确写“兼容 category/severity/extra 等可选元数据”
- 建议收敛：把 `category/severity/extra` 变成显式关键字参数（或统一改 `options=AppErrorOptions(...)`），再删除 `**options` 的“宽口子”入口。

#### B11. 聚合/统计：兼容字段与兼容载荷
- 位置：
  - `app/services/aggregation/aggregation_service.py:133`（`_aggregation` 标注“用于兼容接口”）
  - `app/services/statistics/database_statistics_service.py:282`（示例数据里标注“兼容字段”）
- 建议收敛：明确“兼容字段”的生命周期（何时停止输出/消费），在前后端契约统一后删除这些字段与分支。

#### B12. 应用初始化入口：历史参数保留
- 位置：`app/__init__.py:152`
  - `configure_app(app, config_name: str | None = None)` 的 `config_name` 注释写“保留以兼容历史接口”
- 建议收敛：如果已不再支持“按名称选择配置”的旧入口，移除 `config_name` 参数与相关分支/日志。

### C. 依赖/环境层：可选依赖、版本差异与 OS 差异兼容

#### C1. APScheduler 版本/缺失兼容（与当前依赖声明可能冲突）
- 位置：`app/services/form_service/scheduler_job_service.py:14`、`:41`
  - `except ModuleNotFoundError:  # 兼容 APScheduler 4.x`
  - `except ModuleNotFoundError as trigger_import_error:  # 兼容无 APScheduler 环境`
- 风险提示：`pyproject.toml` 已固定 APScheduler 3.x；若生产环境不允许“无 APScheduler”，这两段兼容可直接进入删除候选。

#### C2. Windows 兼容：`fcntl` 缺失兜底
- 位置：`app/scheduler.py:29`
  - `try: import fcntl ... except ImportError: fcntl = None`（注释“Windows 环境不会加载”）
- 建议收敛：若明确“不支持 Windows 部署”，可删该分支并简化锁逻辑；若仍支持，则保留但应明确写入部署文档与测试矩阵。

#### C3. 数据库驱动可选安装（try-import + 缺失时返回 False）
文件清单（命中“可能未安装/optional dependency/ImportError”）：
- `app/services/connection_adapters/adapters/mysql_adapter.py`
- `app/services/connection_adapters/adapters/postgresql_adapter.py`
- `app/services/connection_adapters/adapters/sqlserver_adapter.py`
- `app/services/connection_adapters/adapters/oracle_adapter.py`
- `app/services/accounts_sync/adapters/sqlserver_adapter.py`
- `app/services/accounts_sync/adapters/oracle_adapter.py`

建议收敛方向（二选一）：
1. **强依赖策略**：所有驱动都作为必选依赖安装 → 删除 try-import 与“未安装返回 False”的分支，失败直接抛出明确错误。
2. **可选依赖策略**：将驱动拆成 extras（如 `.[mysql]`、`.[oracle]`）→ 保留 try-import，但将“缺失”变成前置配置校验与更明确的错误提示（避免运行期静默返回 False）。

#### C4. 密码工具：残留的 ImportError 兜底（疑似历史遗留）
- 位置：`app/utils/password_crypto_utils.py:56` 起
  - 注释写“延迟导入避免循环导入”，但实际已提前导入 logger；try/except ImportError 可能是遗留回退壳
- 建议收敛：明确 logger 永远可用后，删除无效的 ImportError 兜底壳，避免误导与隐藏错误。

### D. 运行期“降级/回退”逻辑（可靠性/容灾类，是否删除需要你明确取舍）

#### D1. 速率限制：缓存失败降级到内存
- 位置：`app/utils/rate_limiter.py:45`、`:120`
  - 当缓存不可用时自动降级到内存 store（行为会改变：多实例下限流不一致）
- 建议：是否删除取决于你对“可用性优先”还是“一致性优先”。如果生产必须强一致限流，建议改为“缓存不可用即拒绝请求或进入保护模式”，并去掉隐式降级。

#### D2. 数据库类型校验：动态配置失败回退到静态白名单
- 位置：`app/utils/data_validator.py:498`
  - 获取 `DatabaseTypeService.get_active_types()` 失败时回退到 `SUPPORTED_DB_TYPES`
- 建议：如果动态配置是权威来源，失败应更早暴露并阻断；如果静态白名单是安全兜底，保留但应配合监控与告警。

#### D3. SQL Server 权限采集：SID 路径失败回退到用户名路径
- 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:619`、`:629`、`:998`
  - 当 SID 路径无结果/不可用时回退到按用户名查询，避免权限为空
- 建议：这是“结果正确性优先”的业务兜底。若决定删，需要确认：所有目标环境都能稳定读取 SID 且不会再出现空权限回退场景。

#### D4. 调度器开关：`ENABLE_SCHEDULER`
- 位置：`app/scheduler.py:412` 起
  - 环境变量开关属于“运维回退/止血开关”
- 建议：保留但要文档化，并明确默认值与生产使用策略（何时允许关闭、关闭后影响范围）。

## 4. 建议的收敛路线（避免“一刀切”回归）

### 4.1 分阶段策略（建议）
1. **观测期（不改行为）**
   - 对“旧路径/旧参数/旧返回结构/旧别名入口”加结构化日志埋点或计数器（例如记录 `used_legacy_param=true`）。
2. **迁移期（改调用方，不删后端兼容）**
   - 前端/脚本/任务统一改用新参数/新入口（例如统一 `search`、统一 `per_page`、统一 `options=...`）。
3. **收口期（删除兼容与回退壳）**
   - 删除后端别名/旧入口/旧参数解析分支；同步删对应测试与文档。
4. **稳定期（门禁固化）**
   - 在 code review 门禁中新增约束：禁止再引入 `q/search`、`limit/per_page` 双制式与旧路径别名。

### 4.2 删除前的“最小核验清单”（建议写进 PR 模板）
- 路由：确认 templates/JS 不再引用旧路径；必要时加 access log 证据。
- 参数：全链路只发送一套参数命名；接口对旧参数返回明确错误（或 400 + 提示）。
- 数据：旧格式数据已迁移（尤其是 `Credential.password` 的 bcrypt/明文）。
- 依赖：是否仍需要可选驱动/Windows/无 APScheduler 的运行方式，有明确决定。

## 5. 附录：自动扫描命中列表（便于你逐条点开审查）

### 5.1 Python 关键词命中（兼容/旧版/回退/降级）
> 生成命令见 2.1。
```text
app/services/accounts_sync/adapters/oracle_adapter.py:325:        兼容 Oracle 11g 及以上版本.
app/services/accounts_sync/adapters/sqlserver_adapter.py:619:                # 若 SID 路径未返回任何角色/权限,尝试按用户名回退
app/services/accounts_sync/adapters/sqlserver_adapter.py:629:                # 回退到基于用户名的查询,避免因无法读取 SID 而导致权限为空
app/services/accounts_sync/adapters/sqlserver_adapter.py:998:        """基于用户名回退查询数据库权限,用于无法读取 SID 的场景."""
app/services/cache_service.py:484:cache_manager: CacheService | None = None  # 向后兼容
app/services/cache_service.py:505:    """兼容旧入口,内部调用新的初始化方法.
app/services/aggregation/aggregation_service.py:133:            _aggregation: 聚合结果对象,当前用于兼容接口.
app/services/database_sync/database_sync_service.py:3:该模块提供与历史版本兼容的 `DatabaseSizeCollectorService`,内部委托
app/services/database_sync/database_sync_service.py:40:    """数据库容量采集服务(兼容包装器).
app/services/database_sync/database_sync_service.py:42:    提供与历史版本兼容的接口,内部委托给 CapacitySyncCoordinator 实现.
app/utils/logging/queue_worker.py:126:        """兼容旧关闭接口.
app/services/aggregation/calculator.py:187:        # fallback - treat as same duration sliding window
app/utils/response_utils.py:130:        **options: 兼容 category/severity/extra 等可选元数据.
app/services/statistics/database_statistics_service.py:282:            'average_size_mb': 2048.01,  # 平均容量(MB,兼容字段)
app/utils/time_utils.py:36:# 向后兼容的时间格式字典
app/utils/time_utils.py:167:            format_str: strftime 兼容格式,默认为 `%Y-%m-%d %H:%M:%S`.
app/utils/rate_limiter.py:45:    当缓存不可用时自动降级到内存模式.
app/utils/rate_limiter.py:120:                    "缓存速率限制检查失败,降级到内存模式",
app/services/sync_session_service.py:237:            **legacy_counts: 兼容旧接口的统计键值对,如 items_synced 等.
app/routes/instances/detail.py:60:    """从请求数据中解析 is_active,兼容表单/JSON/checkbox.
app/routes/instances/detail.py:83:        # 兼容 JSON 中提供数组的情况,取最后一个
app/routes/instances/detail.py:102:    """安全解析整数,无法解析时回退默认值."""
app/routes/instances/detail.py:380:    """兼容旧版路径 `/instances/api/edit/<id>` 的别名."""
app/utils/safe_query_builder.py:395:# 为了向后兼容,添加一个便捷函数返回list格式的参数
app/utils/safe_query_builder.py:401:    """构建安全的过滤条件 - 返回 list 格式参数(向后兼容).
app/utils/safe_query_builder.py:404:    用于向后兼容不支持字典参数的代码.
app/utils/data_validator.py:498:            logger.warning("获取数据库类型配置失败,回退到静态白名单: %s", exc)
app/utils/data_validator.py:587:# 兼容旧的函数式调用方式 ----------------------------------------------------
app/constants/sync_constants.py:194:# 向后兼容的别名
app/constants/sync_constants.py:195:SyncType = SyncOperationType  # 保持向后兼容
app/__init__.py:152:        config_name: 配置名称,保留以兼容历史接口.
app/routes/history/logs.py:3:统一管理日志检索、统计与下发的接口,支撑控制台与旧版前端.
app/routes/history/logs.py:36:# 兼容旧版 /logs 前缀请求
app/routes/history/logs.py:58:    """旧版日志统计过滤条件."""
app/routes/history/logs.py:277:    """解析旧版统计接口的查询条件."""
app/routes/history/logs.py:314:    """在查询上复用旧版接口的公共过滤条件."""
app/routes/history/logs.py:331:    """创建旧版统计的基础查询对象."""
app/routes/history/logs.py:348:    """执行旧版统计查询并返回聚合结果."""
app/routes/history/logs.py:550:    """获取日志统计 API(兼容旧前端).
app/routes/accounts/ledgers.py:145:    fallback = (raw_string or "").strip()
app/routes/accounts/ledgers.py:146:    if not fallback:
app/routes/accounts/ledgers.py:148:    return [tag.strip() for tag in fallback.split(",") if tag.strip()]
app/services/form_service/scheduler_job_service.py:14:except ModuleNotFoundError:  # pragma: no cover - 兼容 APScheduler 4.x
app/services/form_service/scheduler_job_service.py:41:except ModuleNotFoundError as trigger_import_error:  # pragma: no cover - 兼容无 APScheduler 环境
app/services/form_service/scheduler_job_service.py:70:        """初始化资源 id,兼容 apscheduler Job 接口."""
app/models/credential.py:168:        # 旧版本凭据使用 bcrypt 哈希,需要调用 bcrypt 校验
app/models/credential.py:177:        # NOTE: 明文密码兜底处理,仅用于兼容历史数据
app/models/unified_log.py:30:        列出兼容旧接口的关键字参数,便于构造 `LogEntryParams`.
app/models/unified_log.py:145:            **entry_fields: 兼容旧调用方式的关键字参数,会被转换为 payload.
app/routes/partition.py:110:    """校验周期类型,非法时回退 daily."""
app/errors/__init__.py:21:    """AppError 兼容关键字参数结构.
app/errors/__init__.py:23:    保留对旧版本 ``AppError`` 调用方式的支持,便于增量迁移.
app/errors/__init__.py:80:        **legacy_kwargs: 为兼容旧调用方式保留的关键字参数,与 ``options`` 中字段一致。
app/errors/__init__.py:105:            **legacy_kwargs: 与 ``options`` 字段一致的关键字参数,用于维持兼容.
app/errors/__init__.py:166:            overrides: 兼容旧接口的关键字参数集合.
app/errors/__init__.py:178:        """确保 legacy 关键字参数与支持列表一致.
app/errors/__init__.py:202:            overrides: 旧版关键字参数,优先级高于 dataclass 字段.
app/errors/__init__.py:327:    抛出后提醒调用方重试或降级,默认返回 502.
```

### 5.2 可选依赖/版本兼容文件清单
```text
app/scheduler.py
app/services/accounts_sync/adapters/oracle_adapter.py
app/services/accounts_sync/adapters/sqlserver_adapter.py
app/services/connection_adapters/adapters/mysql_adapter.py
app/services/connection_adapters/adapters/oracle_adapter.py
app/services/connection_adapters/adapters/postgresql_adapter.py
app/services/connection_adapters/adapters/sqlserver_adapter.py
app/services/form_service/scheduler_job_service.py
app/utils/password_crypto_utils.py
```
