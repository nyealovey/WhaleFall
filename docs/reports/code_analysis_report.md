# TaifishingV4 代码分析报告

> 基于 2025-11-06 统计，覆盖 `app/` 目录全部代码文件（自动排除 `vendor/`、`__pycache__/` 等目录）。

- **统计范围**：`app/` 目录（排除 `vendor/`、编译产物）
- **代码文件数**：235 个
- **总代码行数**：58,780 行

## 文件类型分布

| 文件类型 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| `.py` | 128 | 32,361 | 55.1% |
| `.js` | 43 | 15,087 | 25.7% |
| `.html` | 33 | 7,213 | 12.3% |
| `.css` | 28 | 3,884 | 6.6% |
| `.yaml` | 3 | 235 | 0.4% |

## 目录行数统计

| 目录 | 文件数 | 代码行数 | 占比 |
| --- | --- | --- | --- |
| static | 71 | 18,971 | 32.3% |
| services | 44 | 10,294 | 17.5% |
| routes | 28 | 10,057 | 17.1% |
| templates | 33 | 7,213 | 12.3% |
| models | 20 | 3,556 | 6.0% |
| utils | 14 | 3,493 | 5.9% |
| tasks | 6 | 2,089 | 3.6% |
| constants | 12 | 1,519 | 2.6% |
| `app/` 根目录 | 3 | 1,140 | 1.9% |
| config | 3 | 235 | 0.4% |
| errors | 1 | 213 | 0.4% |

## 行数最多的 15 个文件

| 排名 | 文件 | 代码行数 |
| --- | --- | --- |
| 1 | `services/account_classification_service.py` | 1,090 |
| 2 | `static/js/pages/admin/scheduler.js` | 1,080 |
| 3 | `static/js/components/tag_selector.js` | 1,063 |
| 4 | `static/js/pages/accounts/account_classification.js` | 1,039 |
| 5 | `routes/instance.py` | 924 |
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

> 注：行数统计基于逐行计数，未区分注释/空行；如需更精细的逻辑行可配合 lint 或静态分析工具进一步处理。
