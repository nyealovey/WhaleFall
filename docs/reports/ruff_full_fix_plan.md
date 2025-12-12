# Ruff 全量扫描修复计划（更新：2025-12-12 12:01）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_120100.txt`（本次扫描共 449 条告警，其中 96 条可通过 `ruff --fix` 自动修复，另有 43 条在 `--unsafe-fixes` 下可尝试自动化处理）。以下计划仅反映本次扫描后的当前状态。

## 1. 主要问题分布
| 类型 | 命中数（约） | 代表文件 | 行动建议 |
| --- | --- | --- | --- |
| **RUF003 / S105** 安全注释与全角标点 | 4 | `app/constants/http_headers.py` | 将注释中的全角逗号替换为半角，并在 CSRF 头常量旁使用英文说明+`# noqa: S105` 或改为配置项。 |
| **PLR0913/PLR0915/C901** 复杂函数 | 40+ | `app/models/{credential,instance,unified_log}.py`、`app/routes/instances/manage.py`、`app/routes/partition.py` | 引入 dataclass 参数对象、拆分 `_execute`、将重复逻辑下沉至 helper/service，逐步降低参数/分支数量。 |
| **I001/TC003** 导入顺序与 TYPE_CHECKING | 60+ | `app/routes/capacity/aggregations.py`、`app/routes/history/logs.py`、`app/routes/instances/detail.py`、`app/utils/response_utils.py` | 统一使用 `from __future__ import annotations`，将 `collections.abc`/第三方 typing 放入 TYPE_CHECKING 块，运行 isort/ruff 修复。 |
| **D202/D205** Docstring 空行格式 | 120+ | `app/routes/credentials.py`、`app/routes/history/logs.py`、`app/utils/route_safety.py`、`app/utils/response_utils.py` | 按“摘要句 + 空行 + 详细描述”格式编写，并移除 docstring 与正文之间的多余空行。 |
| **ANN*** 类型注解缺失 | 70+ | `app/routes/credentials.py`、`app/routes/history/logs.py`、`migrations/env.py` | 为内部 helper 补齐返回值/参数类型，公共函数使用显式返回类型，必要时引入 `typing.TYPE_CHECKING`。 |
| **UTILS 导入/结构** | 50+ | `app/utils/password_crypto_utils.py`、`app/utils/time_utils.py`、`app/utils/query_filter_utils.py`、`app/utils/structlog_config.py` | 将延迟导入提到模块顶部或包裹 TYPE_CHECKING，拆分多余 return，并补充 docstring。 |
| **其余（COM812/PLC0415/E501/N999 等）** | 若干 | `app/routes/partition.py`、`app/utils/sqlserver_connection_utils.py`、`app/views/scheduler_forms.py`、`nginx/gunicorn/*.py`、`tmp_ble_test.py` | 根据规则补拖尾逗号、限制行宽、移除无效模块名、补充模块 docstring 或删除临时文件。 |

## 2. P0（立即修复）
1. **CSRF 头常量（RUF003/S105）**：`app/constants/http_headers.py` 调整注释为半角逗号或英文说明，并保持 `# noqa: S105` 合规。  
2. **模型构造函数（PLR0913）**：`app/models/credential.py`、`app/models/instance.py`、`app/models/unified_log.py` 引入参数 dataclass 或工厂函数，限制 `__init__`/`create_log_entry` 参数数量 ≤5。  
3. **Capacity Aggregations 导入与类型（I001/TC003）**：整理 `from datetime import datetime` 与 `Callable` 至 TYPE_CHECKING 块，统一 isort，并确认最近新增的 `AggregationMeta` 使用 `typing` 中的别名。  
4. **Credentials Helper Docstring/注解（D202/ANN001/ANN202）**：`app/routes/credentials.py` 的 `_build_credential_filters` 等 helper 去掉 docstring 后空行，所有函数补齐参数/返回类型。  
5. **History Logs 类型守卫（TC003/ANN202）**：将 `Mapping` 移入 TYPE_CHECKING，`_apply_time_filters/_apply_log_sorting/_build_log_query` 等补齐泛型注解并消除 docstring 空行。  
6. **Route Safety 日志工具（PLR0913/D202/TC003）**：`app/utils/route_safety.py` 将 `Callable` 放入 TYPE_CHECKING，收紧 docstring，必要时引入辅助函数分担参数过多的问题。  
7. **Response Utils / Structlog 配置（I001/TC002）**：`app/utils/response_utils.py`、`app/utils/structlog_config.py` 统一导入顺序，将 `collections.abc`、`flask.typing.ResponseReturnValue`、`structlog.typing` 放入 TYPE_CHECKING。  

## 3. P1（结构性工作）
- **实例/分区路由复杂度**：`app/routes/instances/manage.py`、`app/routes/partition.py` 继续拆分 `_execute`、`get_core_aggregation_metrics`，引入查询与序列化 helper，顺带补齐拖尾逗号。  
- **Utilities 延迟导入治理**：`app/utils/password_crypto_utils.py`、`app/utils/time_utils.py`、`app/utils/query_filter_utils.py`、`app/utils/rate_limiter.py` 将运行期 import 抽至模块顶部，并通过 helper/类型注解减少重复返回路径（解决 PLC0415/TRY300/PLR0911）。  
- **Logging Pipeline**：`app/utils/logging/queue_worker.py`、`app/utils/structlog_config.py` 补充类型别名、lowercase 变量、将 `SQLAlchemy` 依赖移入 TYPE_CHECKING，避免运行期循环导入。  
- **版本解析器/密码工具**：`app/utils/version_parser.py`、`app/utils/password_crypto_utils.py`、`app/utils/sqlserver_connection_utils.py` 调整 ClassVar、拆分复杂函数，并控制行宽。  
- **Migrations & 配置文件**：`migrations/env.py` 增加 `__init__.py` 或重构为包；`nginx/gunicorn/*.py` 重命名为合法模块或剔除。  

## 4. 扫描统计
- 总计告警：449 条。  
- `ruff --fix` 可自动修复：96 条；`--unsafe-fixes` 额外可尝试：43 条。  
- 重点关注的模块：`app/constants/http_headers.py`、`app/routes/credentials.py`、`app/routes/history/logs.py`、`app/routes/capacity/aggregations.py`、`app/routes/instances/{detail,manage}.py`、`app/utils/*`、`migrations/env.py`、`nginx/gunicorn/*.py`。  

以上为 12:01 扫描后的最新情况，后续计划将以此为基线滚动更新。