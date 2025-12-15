# Ruff 全量扫描修复计划（更新：2025-12-15 08:35）

> 最新全量报告：`docs/reports/ruff_full_2025-12-15_083508.txt`（生成于 2025-12-15 08:35:08）。以下计划取代 2025-12-13 版本，请以本计划为准。

## 1. 规则匹配数量（按出现次数降序）
| 规则 | 数量 | 典型文件（示例） |
| --- | --- | --- |
| TC003 | 3 | `app/services/connection_adapters/adapters/oracle_adapter.py`、`app/services/form_service/scheduler_job_service.py` |
| TC001 | 3 | `app/tasks/accounts_sync_tasks.py` |
| ARG002 | 2 | `app/services/form_service/scheduler_job_service.py` |
| PLR0911 | 1 | `app/services/form_service/password_service.py` |
| D400 | 1 | `migrations/__init__.py` |
| D415 | 1 | `migrations/__init__.py` |
| UP037 | 1 | `migrations/env.py` |
| I001 | 1 | `tmp_ble_test.py` |

> 注：P0/P1 项落地后需重新生成全量报告，确认是否还有残留规则或新增告警。

## 2. P0（立即处理，影响稳定性/可读性）
- **PLR0911（1）**：`ChangePasswordFormService.validate` 仍保留 7 个返回语句，需拆出字段校验/密码校验辅助函数，或在失败分支集中收集错误后统一返回，保证返回路径 ≤6。重构时注意保持日志与国际化 key 不变。
- **TC003 + ARG002（3+2）**：`scheduler_job_service` 兜底触发器类和 `Callable` 需仅在 TYPE_CHECKING 块导入，运行期保留最小依赖；`_MissingTrigger.__init__` 中的 `*args/**kwargs` 若未使用需改为 `_` 或显式忽略，避免噪声。
- **TC001（3）**：`accounts_sync_tasks` 的 `SyncSession`/`SyncInstanceRecord`/`LoggerProtocol` 仅用于类型标注，应移入 TYPE_CHECKING，运行期引用通过字符串注解完成，以降低循环导入风险并符合类型治理要求。

## 3. P1（批量快捷修复）
- **TC003（oracle_adapter）**：`Mapping`/`Sequence` 只用于类型注解，可放入 TYPE_CHECKING 并维持运行期最小依赖；若运行期需要 `Sequence` 判断，改为 `collections.abc` + 局部导入并添加注释。
- **D400/D415（migrations/__init__.py）**：改为“句号 + 中文内容”，保持与仓库 docstring 规范一致。
- **UP037（migrations/env.py）**：`process_revision_directives` 的 `_context: "MigrationContext"` 改为未加引号的注解（配合 `from __future__ import annotations` 已启用）。
- **I001（tmp_ble_test.py）**：整理 import / 空行，若文件仅用于占位可考虑直接移除 import，保留上下文说明。

## 4. P2（后续关注）
- 当前报告无新的复杂度/性能类告警，但 `password_service` 与 `scheduler_job_service` 属于高频触发点，重构时需关注单测覆盖以及并发条件。

## 5. 收尾与遗留
- 完成以上 P0/P1 后，重新执行 `ruff check` 全量扫描并更新报告文件名（例如 `docs/reports/ruff_full_2025-12-15_<新的时间>.txt`），同时同步本计划。
- 若仍有较低优先级告警，请在 PR 描述中注明遗留原因与后续计划。

## 6. 验证顺序
1. **定向高优先级**：`ruff check app --select PLR0911,ARG002,TC001,TC003`.
2. **公共模块**：`ruff check migrations tmp_ble_test.py --select D400,D415,UP037,I001`.
3. **全量兜底**：`ruff check` + `pyright`，必要时执行 `pytest -m unit -k "password_service or scheduler_job_service"` 关注行为正确性。

## 7. 输出与跟踪
- 生成新的 Ruff 报告与计划文件后，应在 PR 中附运行命令与关键结果。
- 若修复过程中需要重构密码表单或调度器服务，务必同步相关单测或补充回归步骤，防止回退。
