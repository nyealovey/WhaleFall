# TaifishingV4 服务层与工具层参考手册

## 📘 文档简介
- 覆盖 `app/services` 与 `app/utils` 下的核心类、函数。
- 为每个条目补充“引用情况”与“主要用途”，便于快速确认代码是否仍被使用。
- 引用信息来自 `rg` 搜索当前仓库（生成时间：`2025-11-05`，如有更新请重新校验）。

> 说明：若引用列标记为 `N/A`，表示该函数目前仅定义未直接调用或仅被测试使用，后续可视情况下线。

---

## 1. 服务层 (`app/services`)

### 1.1 账户分类服务 `account_classification_service.py`

核心类：`AccountClassificationService`

| 方法 | 参数 | 返回 | 描述 | 引用情况 | 主要用途 |
| --- | --- | --- | --- | --- | --- |
| `auto_classify_accounts_optimized` | `instance_id: int | None = None, created_by: int | None = None` | `dict[str, Any]` | 优化后的自动分类流程，支持全量重跑 | `app/routes/account_classification.py:502` | 实例详情页触发自动分类，写入分类结果与日志 |
| `invalidate_cache` | - | `bool` | 清理分类缓存 | `app/routes/account_classification.py:135` | 后台管理清空缓存按钮 |
| `invalidate_db_type_cache` | `db_type: str` | `bool` | 按数据库类型清缓存 | `app/routes/account_classification.py:126` | 更新分类规则后按类型刷新 |
| `get_rule_matched_accounts_count` | `rule_id: int` | `int` | 统计规则匹配数量 | `app/routes/account_classification.py:424` | 规则管理界面展示命中数量 |

内部方法（节选）：

| 方法 | 描述 | 引用情况 | 主要用途 |
| --- | --- | --- | --- |
| `_get_rules_sorted_by_priority` | 获取已排序规则 | 内部调用 | 保证按优先级执行 |
| `_evaluate_rule` | 评估单条规则 | 内部调用 | 规则匹配核心逻辑 |

全局实例：

```python
account_classification_service = AccountClassificationService()
```

---

### 1.2 账户统计服务 `account_statistics_service.py`

| 函数 | 参数 | 返回 | 描述 | 引用情况 | 主要用途 |
| --- | --- | --- | --- | --- | --- |
| `fetch_summary` | `instance_id: int | None = None, db_type: str | None = None` | `dict[str, int]` | 获取总体统计 | `app/routes/accounts/statistics.py:33` | 账户统计页 Overview |
| `fetch_db_type_stats` | - | `dict[str, dict[str, int]]` | 按数据库类型统计 | `app/routes/accounts/statistics.py:64` | 统计页表格数据 |
| `fetch_classification_stats` | - | `dict[str, dict[str, Any]]` | 分类维度统计 | `app/routes/accounts/statistics.py:82` | 分类统计卡片 |
| `build_aggregated_statistics` | - | `dict[str, Any]` | 综合数据 | `app/routes/accounts/statistics.py:23` | 汇总 API |

---

### 1.3 缓存服务 `cache_service.py`

核心类：`CacheService`

| 方法 | 描述 | 引用情况 | 主要用途 |
| --- | --- | --- | --- |
| `invalidate_user_cache(instance_id, username)` | 清除单个用户缓存 | `app/services/account_sync/account_sync_service.py:147` | 同步完成后刷新缓存 |
| `invalidate_instance_cache(instance_id)` | 清除实例缓存 | `app/routes/instance.py:271` | 编辑实例后刷新 |
| `get_cache_stats()` | 缓存统计 | `app/routes/cache.py:24` | 缓存监控页面 |
| `health_check()` | 健康检查 | `tests/unit/services/test_cache_service.py` | 单元测试（运行时监控） |

全局函数：

| 函数 | 描述 | 引用情况 | 主要用途 |
| --- | --- | --- | --- |
| `init_cache_service(cache)` | 初始化服务 | `app/__init__.py:108` | 应用启动时注册 |

---

### 1.4 数据库类型服务 `database_type_service.py`

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `get_all_types()` | 列出全部数据库类型 | `app/services/database_type_service.py:15` | 后端服务调用 |
| `get_active_types()` | 启用类型 | `app/routes/instances/create.py:42` 等 | 实例表单下拉 |
| `get_type_by_name(name)` | 指定类型 | `app/services/instance_service.py:67` | 实例校验 |
| `get_database_types_for_form()` | 表单展示数据 | `app/routes/common.py:172` | 下拉选项接口 |

---

### 1.5 分区管理服务 `partition_management_service.py`

核心类：`PartitionManagementService`

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `create_partition(partition_date)` | 创建指定月份分区 | `app/routes/partition.py:58` | 后台创建分区按钮 |
| `create_future_partitions(months_ahead)` | 批量创建未来分区 | `app/routes/partition.py:82` | 定时任务或后台操作 |
| `cleanup_old_partitions(retention_months)` | 清理旧分区 | `app/routes/partition.py:106` | 后台清理动作 |
| `get_partition_info()` | 获取分区详情 | `app/routes/partition.py:36` | 分区管理列表 |
| `get_partition_statistics()` | 输出统计数据 | `app/routes/partition.py:43` | 页面统计总览 |

数据类 `PartitionAction` 在同文件定义，主要用于模板渲染，引用 `app/routes/partition.py:37`。

---

### 1.6 调度器健康服务 `scheduler_health_service.py`

| 方法 / 数据类 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `SchedulerHealthService.inspect(scheduler)` | 调度器健康检查 | `app/routes/scheduler.py:140` | 管理后台健康检测 |
| `SchedulerHealthReport` / `ExecutorReport` | 结果结构 | `app/routes/scheduler.py:146` | 序列化输出 |
| 全局实例 `scheduler_health_service` | - | `app/routes/scheduler.py:37` | 路由依赖注入 |

---

### 1.7 同步会话服务 `sync_session_service.py`

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `create_session(sync_type, sync_category="account", created_by=None)` | 创建同步会话 | `app/tasks/account_sync_tasks.py:42` 等 | 账户同步、任务驱动 |
| `add_instance_records(session_id, instance_ids, ...)` | 批量添加实例记录 | `app/tasks/account_sync_tasks.py:53` | 同步任务初始化 |
| `start_instance_sync(record_id)` | 标记开始 | `app/tasks/account_sync_tasks.py:67` | 阶段状态流转 |
| `complete_instance_sync(...)` | 标记完成 | `app/tasks/account_sync_tasks.py:110` | 成功统计 |
| `fail_instance_sync(record_id, ...)` | 标记失败 | `app/tasks/account_sync_tasks.py:123` | 错误记录 |
| `get_session_records(session_id)` | 获取实例记录 | `app/routes/sync_sessions.py:120` | 会话详情页 |
| `cancel_session(session_id)` | 取消同步 | `app/routes/sync_sessions.py:214` | 手动终止同步 |

全局实例 `sync_session_service` 在 `app/tasks/account_sync_tasks.py`、`app/routes/sync_sessions.py` 等多处使用。

---

## 2. 工具层 (`app/utils`)

### 2.1 缓存工具 `cache_utils.py`

核心类：`CacheManager`

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `get / set / delete / clear` | 基础缓存操作 | `app/utils/cache_utils.py` 内部调用 | 封装底层缓存 |
| `get_or_set` | 缓存缺省写入 | `app/services/account_classification_service.py:71` | 规则缓存 |
| `invalidate_pattern` | 按模式失效 | `app/services/account_classification_service.py:63` | 批量清缓存 |
| 装饰器 `cached`, `dashboard_cache` | 函数级缓存 | `app/routes/dashboard.py:42` | 仪表盘缓存 |

全局函数：`init_cache_manager` 在 `app/__init__.py:105` 被调用。

---

### 2.2 数据验证工具 `data_validator.py`

核心类：`DataValidator`

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `validate_instance_data` | 校验实例表单 | `app/routes/instances/create.py:95` | 创建实例前校验 |
| `validate_batch_data` | 批量校验 | `app/routes/instances/list.py:350` | 批量导入 |
| `sanitize_input / sanitize_form_data` | 清洗数据 | 多处 | 防注入、防脏数据 |
| `validate_required_fields` | 必填校验 | 多处 | API 参数校验 |

兼容函数（同名）用于老代码继续调用。

---

### 2.3 装饰器工具 `decorators.py`

| 装饰器 / 函数 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `admin_required`, `login_required`, `permission_required` 等 | 权限控制 | 广泛：`app/routes` | 接口访问控制 |
| `require_csrf` | CSRF 校验 | 主要后台表单 POST | 保证表单安全 |
| `has_permission` | 权限判断辅助 | `app/routes/*.py` | 自定义逻辑中调用 |

---

### 2.4 响应工具 `response_utils.py`

| 函数 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `unified_success_response` / `jsonify_unified_success` | 构造统一成功响应 | `app/routes/*` 大量 | 标准化 API |
| `unified_error_response` / `jsonify_unified_error` | 构造错误响应 | 同上 | 错误处理 |
| `jsonify_unified_error_message` | 快速错误响应 | `app/routes/account_sync.py:154` 等 | 简化错误返回 |

---

### 2.5 时间工具 `time_utils.py`

核心类：`TimeUtils`（全局实例 `time_utils`）

| 方法 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `now` / `now_china` | 获取当前时间 | 各服务模块 | 写入日志、记录时间 |
| `to_china` / `to_utc` | 时区转换 | `app/services/account_sync/account_sync_service.py:119` 等 | 统一时间处理 |
| `format_china_time` 等 | 格式化输出 | `app/routes/history/logs.py:76` | 前端显示 |
| `get_relative_time` | 相对时间 | `app/utils/time_utils.py` 内部 | 统计 |

---

### 2.6 安全查询构建器 `safe_query_builder.py`

| 条目 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `SafeQueryBuilder` | 构建安全 SQL 条件 | `app/services/account_sync/account_sync_filters.py:52` | 构造过滤语句 |
| `build_safe_filter_conditions` | 统一入口 | `app/services/account_sync/account_sync_filters.py:30` | 账户过滤 |

---

### 2.7 速率限制工具 `rate_limiter.py`

| 条目 | 描述 | 引用情况 | 用途 |
| --- | --- | --- | --- |
| `RateLimiter.is_allowed` | 检查配额 | `app/utils/rate_limiter.py` 内部+测试 | 登录限流 |
| 装饰器 `login_rate_limit` 等 | 应用在登录/重置接口 | `app/routes/auth.py:70` | 防爆破 |
| `init_rate_limiter` | 初始化 | `app/__init__.py:118` | 应用启动注册 |

---

## 3. 服务子模块概览

| 子模块 | 文件 / 目录 | 引用情况 | 用途说明 |
| --- | --- | --- | --- |
| `services/account_sync/` | `account_query_service`, `coordinator`, `inventory_manager`, `adapters/*` | 调用点集中于 `app/services/account_sync/account_sync_service.py`、`app/tasks/account_sync_tasks.py`、`app/routes/account_sync.py` | 账户同步全流程（任务、路由、协调器、适配器） |
| `services/aggregation/` | `aggregation_service`, `calculator`, `*_runner.py` | `app/tasks/capacity_collection_tasks.py`, `app/routes/capacity.py` | 容量/实例聚合逻辑 |
| `services/connection_adapters/` | `connection_factory`, `connection_test_service` 等 | `app/services/database_sync/*`, `app/routes/instance_detail.py` | 数据库连接、连通性测试 |
| `services/database_sync/` | `coordinator`, `persistence`, `adapters/*` | `app/routes/capacity.py`, `app/tasks/capacity_collection_tasks.py` | 容量同步主流程 |

---

## 4. 统计信息速览

- **服务模块**：7 个核心服务 + 4 个子模块包。
- **工具模块**：7 个常用工具。
- **主要全局实例**：`account_classification_service`、`scheduler_health_service`、`sync_session_service`、`time_utils` 等。
- **常见引用场景**：路由调用（`app/routes/*`）、定时任务（`app/tasks/*`）、服务内部调用与测试。

> 推荐做法：清理未引用的函数前，先确认是否在单元测试或未来计划中使用；引用信息可通过 `rg` 或 `pyright` 再次验证。

---

## 5. 改进建议

1. 为高频服务（账户同步、容量同步）补充自动化测试覆盖所有对外方法。
2. 在 VSCode 中配置代码透视（Call Hierarchy）以持续监控引用变化。
3. 若未来合并或下线模块，可使用本表的引用情况作为排查依据。

> 本文档可与 `docs/fix_account_sync_success_message.md` 联动，确保同步类任务的实现与日志规范一致。
