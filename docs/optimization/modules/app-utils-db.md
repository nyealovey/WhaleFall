# Module: `app/utils/db`（safe_query_builder/sqlserver_connection_utils/database_type_utils/query_filter_utils/cache_utils）

## Simplification Analysis

### Core Purpose

- `app/utils/safe_query_builder.py`：为账户同步等场景生成参数化 WHERE 条件，避免 SQL 注入
- `app/utils/sqlserver_connection_utils.py`：SQL Server 连接失败时提供可解释的诊断结果（供连接适配器日志使用）
- `app/utils/database_type_utils.py`：数据库类型字符串规范化 + 展示名/图标/颜色/schema 等纯函数
- `app/utils/query_filter_utils.py`：将 ORM 查询结果/枚举列表格式化为 UI 下拉 options（纯格式化）
- `app/utils/cache_utils.py`：Flask-Caching 的最小封装（初始化注册 + `@cached`/`@dashboard_cache`）

### Unnecessary Complexity Found

- `app/utils/cache_utils.py:130`/`app/utils/cache_utils.py:147`：`delete/clear` 在仓库内无调用方（YAGNI），保留只会扩大“可用 API 面”，增加维护成本。
- `app/utils/cache_utils.py:161`：`CacheManager.get_or_set` 在仓库内无调用方（YAGNI）；当前实际只需要 `get/set/build_key` 支撑装饰器即可。
- `app/utils/cache_utils.py:190`：`invalidate_pattern(self, pattern)` 作为模块级函数且无调用方，属于“未来可能用到”的扩展点（YAGNI），并引入额外异常处理分支与类型转换噪音。
- `app/utils/cache_utils.py:56`：`_generate_key` 仅被 `build_key` 调用，属于不必要的间接层（一次性抽象）。
- `app/utils/cache_utils.py:274`/`app/utils/cache_utils.py:280`：`cached()` 内部重复 `get_system_logger()`，可直接复用 `CacheManager.system_logger`，减少重复获取与变量噪音（不改变日志字段）。

- `app/utils/sqlserver_connection_utils.py:19`/`app/utils/sqlserver_connection_utils.py:31`：`diag_logger` 仅初始化但从未使用，属于死字段（YAGNI）。
- `app/utils/sqlserver_connection_utils.py:178`/`app/utils/sqlserver_connection_utils.py:230`：`get_connection_string_suggestions/analyze_error_patterns` 无调用方，属于“工具箱式”扩展（YAGNI）。

- `app/utils/safe_query_builder.py:97`：未被调用的 `_generate_placeholder` 属于死代码（YAGNI）。
- `app/utils/safe_query_builder.py:289`：`add_database_specific_condition(..., db_specific_rules=None)` 的 `db_specific_rules` 参数与实现内的 `db_specific_rules = ...` 未被使用（YAGNI）。

- `app/utils/database_type_utils.py:44`/`app/utils/database_type_utils.py:56`：`get_database_type_default_port/database_type_requires_port` 在仓库内无调用方（YAGNI）。
- `app/utils/query_filter_utils.py:10`：`TYPE_CHECKING + cast(...)` 仅为类型“装饰”，运行期无收益；在已启用 `from __future__ import annotations` 的前提下属于噪音。

### Code to Remove

- `app/utils/cache_utils.py:22`（已删除）- 未使用的 `TypingCallable`（Estimated LOC reduction: ~1）
- `app/utils/cache_utils.py:56`（已内联并删除）- `_generate_key` 一次性抽象（Estimated LOC reduction: ~30）
- `app/utils/cache_utils.py:130`（已删除）- `CacheManager.delete`（Estimated LOC reduction: ~16）
- `app/utils/cache_utils.py:147`（已删除）- `CacheManager.clear`（Estimated LOC reduction: ~14）
- `app/utils/cache_utils.py:161`（已删除）- `CacheManager.get_or_set`（Estimated LOC reduction: ~29）
- `app/utils/cache_utils.py:190`（已删除）- `invalidate_pattern`（Estimated LOC reduction: ~33）
- `app/utils/cache_utils.py:233`/`app/utils/cache_utils.py:274`/`app/utils/cache_utils.py:280`（已改写）- 复用 `manager.system_logger`（净删少量重复变量）

- `app/utils/sqlserver_connection_utils.py:19`/`app/utils/sqlserver_connection_utils.py:31`（已删除）- 未使用的 `diag_logger` 字段与导入（Estimated LOC reduction: ~2）
- `app/utils/sqlserver_connection_utils.py:178`（已删除）- `get_connection_string_suggestions`（Estimated LOC reduction: ~50）
- `app/utils/sqlserver_connection_utils.py:230`（已删除）- `analyze_error_patterns`（Estimated LOC reduction: ~30）

- `app/utils/safe_query_builder.py:97`（已删除）- 未使用的 `_generate_placeholder`（Estimated LOC reduction: ~23）
- `app/utils/safe_query_builder.py:289`（已删除）- 未使用的 `db_specific_rules` 形参与分支（Estimated LOC reduction: ~4）

- `app/utils/database_type_utils.py:44`（已删除）- 未使用的 `get_database_type_default_port`（Estimated LOC reduction: ~5）
- `app/utils/database_type_utils.py:56`（已删除）- 未使用的 `database_type_requires_port`（Estimated LOC reduction: ~4）

- `app/utils/query_filter_utils.py:10`（已删除/改写）- `TYPE_CHECKING + cast(...)` 噪音（净删少量类型样板）

- Estimated LOC reduction: ~250 LOC（净删；`git diff --numstat` 合计 -250）

### Simplification Recommendations

1. 面向“仓库实际调用链”收敛工具模块对外 API 面
   - Current: 工具模块含多种“可能用得到”的方法/函数（delete/clear/get_or_set/invalidate_pattern 等）
   - Proposed: 仅保留被调用的最小集合（`build_key/get/set` + 装饰器入口）
   - Impact: 降低维护面与误用风险；阅读更聚焦

2. 删除死代码/死字段，避免“假装可用”的扩展点
   - Current: `sqlserver_connection_utils`/`safe_query_builder` 中存在未被引用的函数/字段
   - Proposed: 删除无调用方的实现；需要时再按真实用例补回
   - Impact: 更少分支与更少测试负担；减少误导

3. 对“纯格式化”函数去类型样板噪音
   - Current: `TYPE_CHECKING + cast(...)` 让代码更长但不改变运行期行为
   - Proposed: 保留纯函数语义，删去运行期无意义的类型装饰
   - Impact: 代码更直观；避免在工具层引入不必要的复杂度

### YAGNI Violations

- “未来可能需要”的缓存批量失效/通用 CRUD（`invalidate_pattern/delete/clear/get_or_set`）
- SQL Server 连接诊断里的“附加能力”（连接串建议/错误关键词分析）无真实调用链支撑
- `SafeQueryBuilder` 中未使用的占位符生成器与无效参数

### Final Assessment

Total potential LOC reduction: ~250 LOC（已落地）
Complexity score: Medium → Low
Recommended action: 保持 `app/utils/db` 作为“被调用即有用”的最小工具集；新增能力必须先有明确调用方与测试/复现场景

