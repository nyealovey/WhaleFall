# TaifishingV4 代码分析报告

> 基于 2025-11-07 统计，覆盖 `app/` 目录全部代码文件（自动排除 `vendor/`、`__pycache__/` 等目录）。

- **统计范围**：`app/` 目录（排除 `vendor/`、编译产物）
- **代码文件数**：238 个
- **总代码行数**：58,192 行

## 文件类型分布

| 文件类型 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| `.py` | 131 | 32,389 | 55.7% |
| `.js` | 43 | 14,983 | 25.7% |
| `.html` | 33 | 7,100 | 12.2% |
| `.css` | 28 | 3,485 | 6.0% |
| `.yaml` | 3 | 235 | 0.4% |

## 目录行数统计

| 目录 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| static | 71 | 18,468 | 31.7% |
| services | 47 | 10,832 | 18.6% |
| routes | 28 | 9,534 | 16.4% |
| templates | 33 | 7,100 | 12.2% |
| models | 20 | 3,556 | 6.1% |
| utils | 14 | 3,493 | 6.0% |
| tasks | 6 | 2,091 | 3.6% |
| constants | 12 | 1,519 | 2.6% |
| `app/` 根目录 | 3 | 1,151 | 2.0% |
| config | 3 | 235 | 0.4% |
| errors | 1 | 213 | 0.4% |

## 行数最多的 15 个文件

| 排名 | 文件 | 代码行数 |
| --- | --- | --- |
| 1 | `services/account_classification_service.py` | 1,090 |
| 2 | `static/js/components/tag_selector.js` | 1,063 |
| 3 | `static/js/pages/accounts/account_classification.js` | 1,039 |
| 4 | `routes/instance.py` | 981 |
| 5 | `static/js/pages/admin/scheduler.js` | 976 |
| 6 | `tasks/capacity_aggregation_tasks.py` | 888 |
| 7 | `static/js/pages/tags/batch_assign.js` | 844 |
| 8 | `utils/structlog_config.py` | 794 |
| 9 | `services/aggregation/aggregation_service.py` | 776 |
| 10 | `models/permission_config.py` | 775 |
| 11 | `routes/instance_detail.py` | 738 |
| 12 | `static/js/common/capacity_stats/manager.js` | 732 |
| 13 | `services/account_sync/adapters/sqlserver_adapter.py` | 724 |
| 14 | `static/js/common/permission_policy_center.js` | 716 |
| 15 | `templates/instances/detail.html` | 704 |

## 超过 500 行的文件清单

| 文件 | 代码行数 |
| --- | --- |
| `services/account_classification_service.py` | 1,090 |
| `static/js/components/tag_selector.js` | 1,063 |
| `static/js/pages/accounts/account_classification.js` | 1,039 |
| `routes/instance.py` | 981 |
| `static/js/pages/admin/scheduler.js` | 976 |
| `tasks/capacity_aggregation_tasks.py` | 888 |
| `static/js/pages/tags/batch_assign.js` | 844 |
| `utils/structlog_config.py` | 794 |
| `services/aggregation/aggregation_service.py` | 776 |
| `models/permission_config.py` | 775 |
| `routes/instance_detail.py` | 738 |
| `static/js/common/capacity_stats/manager.js` | 732 |
| `services/account_sync/adapters/sqlserver_adapter.py` | 724 |
| `static/js/common/permission_policy_center.js` | 716 |
| `templates/instances/detail.html` | 704 |
| `tasks/capacity_collection_tasks.py` | 678 |
| `services/connection_adapters/connection_factory.py` | 656 |
| `routes/scheduler.py` | 643 |
| `routes/account_classification.py` | 635 |
| `static/js/pages/history/logs.js` | 613 |
| `static/js/pages/instances/detail.js` | 602 |
| `static/js/pages/admin/aggregations_chart.js` | 574 |
| `services/partition_management_service.py` | 565 |
| `static/js/common/permission-modal.js` | 555 |
| `services/account_sync/permission_manager.py` | 551 |
| `templates/accounts/account_classification.html` | 548 |
| `__init__.py` | 544 |
| `routes/tags.py` | 535 |
| `routes/partition.py` | 531 |
| `routes/credentials.py` | 512 |

> 注：行数统计基于逐行计数，未区分注释/空行；如需更精细的逻辑行可配合 lint 或静态分析工具进一步处理。
