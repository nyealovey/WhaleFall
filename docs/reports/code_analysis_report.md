# TaifishingV4 代码分析报告

> 基于 2025-11-10 最新统计，覆盖 `app/` 目录全部业务代码（排除 `vendor/`、`__pycache__/`、二进制图片等资产）。

- **统计范围**：`app/` 目录（剔除编译产物与静态二进制资源）
- **代码文件数**：253 个
- **总代码行数**：58,222 行
- **前端资产**：106 个文件 / 25,625 行（44.0%，含 `app/static` 与 `app/templates`）
- **后端代码**：147 个文件 / 32,597 行（56.0%，覆盖 `services/`、`routes/`、`models/` 等目录）

## 文件类型分布

| 文件类型 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| `.py` | 143 | 32,310 | 55.5% |
| `.js` | 43 | 15,036 | 25.8% |
| `.html` | 33 | 7,100 | 12.2% |
| `.css` | 28 | 3,485 | 6.0% |
| `.yaml` | 3 | 235 | 0.4% |
| （无扩展名） | 3 | 56 | 0.1% |

## 目录行数统计

| 目录 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| static | 72 | 18,523 | 31.8% |
| services | 59 | 10,999 | 18.9% |
| routes | 28 | 9,286 | 15.9% |
| templates | 34 | 7,102 | 12.2% |
| models | 20 | 3,558 | 6.1% |
| utils | 14 | 3,493 | 6.0% |
| tasks | 6 | 2,091 | 3.6% |
| constants | 12 | 1,519 | 2.6% |
| `app/` 根目录 | 4 | 1,203 | 2.1% |
| config | 3 | 235 | 0.4% |
| errors | 1 | 213 | 0.4% |

## 行数最多的 15 个文件

| 排名 | 文件 | 代码行数 |
| --- | --- | --- |
| 1 | `static/js/pages/accounts/account_classification.js` | 1,092 |
| 2 | `static/js/components/tag_selector.js` | 1,063 |
| 3 | `static/js/pages/admin/scheduler.js` | 976 |
| 4 | `tasks/capacity_aggregation_tasks.py` | 888 |
| 5 | `static/js/pages/tags/batch_assign.js` | 844 |
| 6 | `utils/structlog_config.py` | 794 |
| 7 | `services/aggregation/aggregation_service.py` | 776 |
| 8 | `models/permission_config.py` | 775 |
| 9 | `routes/instance_detail.py` | 739 |
| 10 | `static/js/common/capacity_stats/manager.js` | 732 |
| 11 | `services/account_sync/adapters/sqlserver_adapter.py` | 724 |
| 12 | `static/js/common/permission_policy_center.js` | 716 |
| 13 | `templates/instances/detail.html` | 704 |
| 14 | `routes/instance.py` | 702 |
| 15 | `tasks/capacity_collection_tasks.py` | 678 |

## 超过 500 行的前端文件

| 文件 | 代码行数 |
| --- | --- |
| `static/js/pages/accounts/account_classification.js` | 1,092 |
| `static/js/components/tag_selector.js` | 1,063 |
| `static/js/pages/admin/scheduler.js` | 976 |
| `static/js/pages/tags/batch_assign.js` | 844 |
| `static/js/common/capacity_stats/manager.js` | 732 |
| `static/js/common/permission_policy_center.js` | 716 |
| `templates/instances/detail.html` | 704 |
| `static/js/pages/history/logs.js` | 613 |
| `static/js/pages/instances/detail.js` | 602 |
| `static/js/pages/admin/aggregations_chart.js` | 574 |
| `static/js/common/permission-modal.js` | 555 |
| `templates/accounts/account_classification.html` | 548 |

## 超过 500 行的后端文件

| 文件 | 代码行数 |
| --- | --- |
| `tasks/capacity_aggregation_tasks.py` | 888 |
| `utils/structlog_config.py` | 794 |
| `services/aggregation/aggregation_service.py` | 776 |
| `models/permission_config.py` | 775 |
| `routes/instance_detail.py` | 739 |
| `services/account_sync/adapters/sqlserver_adapter.py` | 724 |
| `routes/instance.py` | 702 |
| `tasks/capacity_collection_tasks.py` | 678 |
| `routes/account_classification.py` | 670 |
| `services/connection_adapters/connection_factory.py` | 656 |
| `routes/scheduler.py` | 643 |
| `services/partition_management_service.py` | 565 |
| `services/account_sync/permission_manager.py` | 551 |
| `__init__.py` | 544 |
| `routes/tags.py` | 535 |
| `routes/partition.py` | 531 |
| `routes/credentials.py` | 512 |

> 注：行数统计基于逐行计数，未区分注释/空行；如需更精细的逻辑行可配合 lint 或静态分析工具进一步处理。
