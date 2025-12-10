# Pyright 类型检查报告 (2025-12-10 11:08)

## 概览
- 诊断总数: **617** (错误 577, 警告 40)
- 受影响文件: **99** 个
- 详细报告: `docs/reports/pyright_full_2025-12-10_110801.txt`

## 规则分布
| 规则 | 数量 | 示例位置 | 处理建议 |
| --- | --- | --- | --- |
| reportAttributeAccessIssue | 175 | `/Users/apple/Github/WhaleFall/app/__init__.py:119:9` | 修复所有 reportAttributeAccessIssue 相关的类型告警 |
| reportArgumentType | 115 | `/Users/apple/Github/WhaleFall/app/errors/__init__.py:297:20` | 修复所有 reportArgumentType 相关的类型告警 |
| reportReturnType | 114 | `/Users/apple/Github/WhaleFall/app/models/database_type_config.py:146:16` | 修复所有 reportReturnType 相关的类型告警 |
| reportCallIssue | 61 | `/Users/apple/Github/WhaleFall/app/models/unified_log.py:116:13` | 修复所有 reportCallIssue 相关的类型告警 |
| reportGeneralTypeIssues | 48 | `/Users/apple/Github/WhaleFall/app/models/database_size_aggregation.py:145:62` | 修复所有 reportGeneralTypeIssues 相关的类型告警 |
| reportUnsupportedDunderAll | 40 | `/Users/apple/Github/WhaleFall/app/forms/definitions/__init__.py:22:5` | 修复所有 reportUnsupportedDunderAll 相关的类型告警 |
| reportOptionalMemberAccess | 29 | `/Users/apple/Github/WhaleFall/app/routes/cache.py:34:31` | 修复所有 reportOptionalMemberAccess 相关的类型告警 |
| reportPossiblyUnboundVariable | 11 | `/Users/apple/Github/WhaleFall/app/routes/history/logs.py:477:74` | 修复所有 reportPossiblyUnboundVariable 相关的类型告警 |
| reportIncompatibleMethodOverride | 9 | `/Users/apple/Github/WhaleFall/app/models/user.py:35:5` | 修复所有 reportIncompatibleMethodOverride 相关的类型告警 |
| reportMissingImports | 8 | `/Users/apple/Github/WhaleFall/app/services/form_service/scheduler_job_service.py:11:10` | 修复所有 reportMissingImports 相关的类型告警 |
| reportOptionalSubscript | 2 | `/Users/apple/Github/WhaleFall/tests/unit/services/test_classification_form_service.py:61:12` | 修复所有 reportOptionalSubscript 相关的类型告警 |
| reportUnusedExcept | 1 | `/Users/apple/Github/WhaleFall/app/tasks/accounts_sync_tasks.py:114:28` | 修复所有 reportUnusedExcept 相关的类型告警 |
| reportAssignmentType | 1 | `/Users/apple/Github/WhaleFall/app/utils/query_filter_utils.py:87:34` | 修复所有 reportAssignmentType 相关的类型告警 |
| reportRedeclaration | 1 | `/Users/apple/Github/WhaleFall/app/utils/safe_query_builder.py:49:18` | 修复所有 reportRedeclaration 相关的类型告警 |
| reportInvalidTypeForm | 1 | `/Users/apple/Github/WhaleFall/scripts/audit_colors.py:38:42` | 修复所有 reportInvalidTypeForm 相关的类型告警 |
| reportOperatorIssue | 1 | `/Users/apple/Github/WhaleFall/scripts/code/safe_update_code_analysis.py:84:9` | 修复所有 reportOperatorIssue 相关的类型告警 |

## 建议动作
- 优先处理错误级别的规则, 避免 SQLAlchemy/Flask 运行期异常。
- 补齐缺失的类型存根或在 `pyrightconfig.json` 中豁免确实安全的场景。
- 与业务开发同步修复脚本/任务中的未绑定变量及可空引用。
