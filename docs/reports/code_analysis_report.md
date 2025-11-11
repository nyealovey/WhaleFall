# TaifishingV4 代码分析报告

> 基于 2025-11-12 最新统计，覆盖 `app/` 目录全部业务代码（排除 `vendor/`、`__pycache__/`、二进制图片等资产）。

- **统计范围**：`app/` 目录（剔除编译产物与静态二进制资源）
- **代码文件数**：257 个
- **总代码行数**：57,121 行
- **前端资产**：105 个文件 / 25,635 行（44.9%，含 `app/static` 与 `app/templates`）
- **后端代码**：152 个文件 / 31,486 行（55.1%，覆盖 `services/`、`routes/`、`models/` 等目录）

## 文件类型分布

| 文件类型 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| `.py` | 149 | 31,251 | 54.7% |
| `.js` | 44 | 15,049 | 26.2% |
| `.html` | 33 | 7,101 | 12.4% |
| `.css` | 28 | 3,485 | 6.1% |
| `.yaml` | 3 | 235 | 0.4% |

## 目录行数统计

| 目录 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| static | 72 | 18,534 | 32.3% |
| services | 60 | 11,055 | 19.4% |
| routes | 28 | 9,284 | 16.2% |
| templates | 33 | 7,101 | 12.4% |
| utils | 19 | 3,434 | 6.0% |
| models | 20 | 2,822 | 4.9% |
| tasks | 6 | 1,863 | 3.3% |
| constants | 12 | 1,519 | 2.6% |
| `app/` 根目录 | 3 | 1,061 | 1.9% |
| config | 3 | 235 | 0.4% |
| errors | 1 | 213 | 0.4% |

## 行数最多的 15 个文件

| 排名 | 文件 | 代码行数 |
| --- | --- | --- |
| 1 | `static/js/components/tag_selector.js` | 1,063 |
| 2 | `static/js/pages/accounts/account_classification.js` | 1,010 |
| 3 | `static/js/pages/admin/scheduler.js` | 976 |
| 4 | `static/js/pages/tags/batch_assign.js` | 844 |
| 5 | `routes/instance_detail.py` | 739 |
| 6 | `static/js/common/capacity_stats/manager.js` | 732 |
| 7 | `services/account_sync/adapters/sqlserver_adapter.py` | 726 |
| 8 | `static/js/common/permission_policy_center.js` | 716 |
| 9 | `templates/instances/detail.html` | 704 |
| 10 | `routes/instance.py` | 704 |
| 11 | `tasks/capacity_collection_tasks.py` | 678 |
| 12 | `routes/account_classification.py` | 670 |
| 13 | `services/aggregation/aggregation_service.py` | 667 |
| 14 | `tasks/capacity_aggregation_tasks.py` | 660 |
| 15 | `services/connection_adapters/connection_factory.py` | 656 |

## 超过 500 行的前端文件

| 文件 | 代码行数 |
| --- | --- |
| `static/js/components/tag_selector.js` | 1,063 |
| `static/js/pages/accounts/account_classification.js` | 1,010 |
| `static/js/pages/admin/scheduler.js` | 976 |
| `static/js/pages/tags/batch_assign.js` | 844 |
| `static/js/common/capacity_stats/manager.js` | 732 |
| `static/js/common/permission_policy_center.js` | 716 |
| `templates/instances/detail.html` | 704 |
| `static/js/pages/history/logs.js` | 613 |
| `static/js/pages/instances/detail.js` | 602 |
| `static/js/pages/admin/aggregations_chart.js` | 574 |
| `static/js/common/permission-modal.js` | 555 |
| `templates/accounts/account_classification.html` | 549 |

## 超过 500 行的后端文件

| 文件 | 代码行数 |
| --- | --- |
| `routes/instance_detail.py` | 739 |
| `services/account_sync/adapters/sqlserver_adapter.py` | 726 |
| `routes/instance.py` | 704 |
| `tasks/capacity_collection_tasks.py` | 678 |
| `routes/account_classification.py` | 670 |
| `services/aggregation/aggregation_service.py` | 667 |
| `tasks/capacity_aggregation_tasks.py` | 660 |
| `services/connection_adapters/connection_factory.py` | 656 |
| `routes/scheduler.py` | 643 |
| `services/account_sync/permission_manager.py` | 571 |
| `services/partition_management_service.py` | 565 |
| `__init__.py` | 544 |
| `routes/tags.py` | 535 |
| `routes/partition.py` | 531 |
| `routes/credentials.py` | 512 |

> 注：行数统计基于逐行计数，未区分注释/空行；如需更精细的逻辑行可配合 lint 或静态分析工具进一步处理。
