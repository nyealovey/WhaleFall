# Route Layer Thin Service Refactor Progress

> 状态: Done
> 负责人: WhaleFall Team
> 创建: 2026-01-08
> 更新: 2026-01-08
> 范围: `app/api/v1/namespaces/**`, `app/routes/**`, `app/services/**`, `tests/unit/routes/**`
> 关联: `docs/plans/2026-01-08-route-layer-thin-service-refactor.md`
> 扫描清单: `docs/plans/2026-01-08-route-layer-scan-inventory.md`

## Milestones

- [x] Task 0: 冻结对外契约（baseline tests）
  - [x] API contract 增加 `Service` 列（标准 + 现有 contract 文档）
  - [x] 跑 baseline 契约测试（`uv run pytest -m unit`）
- [x] Task 1: instances sync-capacity -> `InstanceCapacitySyncActionsService`
- [x] Task 2: tags bulk actions -> `TagsBulkActionsService`
- [x] Task 3: cache actions -> `CacheActionsService`
- [x] Task 4: scheduler run/reload -> `SchedulerActionsService`
- [x] Task 5: databases ledgers export -> `DatabaseLedgerExportService`
- [x] Task 6: logs export -> extend `LogsExportService`
- [x] Task 7: api auth login -> `LoginService`
- [x] Task 8: classifications validate-expression -> validation service
- [x] Task 9: 页面路由下沉（可选 Phase 2）
- [x] Task 10: 回归验证 + 清理
- [ ] (Optional) Task 11: 薄路由门禁脚本

## Timeline（建议）

> 说明：这是“工作日”节奏建议；实际可根据评审资源压缩或拆分。日期以 2026-01-08 为起点。

| Day | Date | Focus | Exit Criteria |
| --- | --- | --- | --- |
| D0 | 2026-01-08 | 盘点 + 计划 + baseline | plan + progress + scan inventory 完整；Task 0（docs）DONE；baseline tests PASS |
| D1 | 2026-01-09 | instances sync-capacity | Task 1 完成；对应契约测试 PASS |
| D2 | 2026-01-10 | tags bulk + cache actions | Task 2/3 完成；对应契约测试 PASS |
| D3 | 2026-01-11 | scheduler actions + exports | Task 4/5/6 完成；files 契约测试 PASS |
| D4 | 2026-01-12 | auth + validate-expression | Task 7/8 完成；对应契约测试 PASS |
| D5 | 2026-01-13 | 回归 + 清理 | Task 10 完成；`uv run pytest -m unit -q` PASS |
| D6 | 2026-01-14 | Phase 2（可选） | 页面路由下沉完成（如执行） |

## Endpoint-level Progress

> 说明: `Status` 建议使用 `TODO / DOING / DONE / BLOCKED`.

| Endpoint | Location | Target Service | Status | Notes |
| --- | --- | --- | --- | --- |
| `POST /api/v1/instances/<id>/actions/sync-capacity` | `app/api/v1/namespaces/instances.py:743` | `app/services/capacity/instance_capacity_sync_actions_service.py` | DONE | 注意 409 失败路径仍需 commit inventory（不能抛异常） |
| `POST /api/v1/tags/bulk/actions/assign` | `app/api/v1/namespaces/tags.py:571` | `app/services/tags/tags_bulk_actions_service.py` | DONE | 下沉 Instance/Tag query + 双重循环 |
| `POST /api/v1/tags/bulk/actions/remove` | `app/api/v1/namespaces/tags.py:654` | `app/services/tags/tags_bulk_actions_service.py` | DONE | - |
| `POST /api/v1/tags/bulk/instance-tags` | `app/api/v1/namespaces/tags.py:727` | `app/services/tags/tags_bulk_actions_service.py` | DONE | - |
| `POST /api/v1/tags/bulk/actions/remove-all` | `app/api/v1/namespaces/tags.py:783` | `app/services/tags/tags_bulk_actions_service.py` | DONE | - |
| `POST /api/v1/cache/actions/clear-user` | `app/api/v1/namespaces/cache.py:102` | `app/services/cache/cache_actions_service.py` | DONE | 保持 cache_service monkeypatch 点 |
| `POST /api/v1/cache/actions/clear-instance` | `app/api/v1/namespaces/cache.py:163` | `app/services/cache/cache_actions_service.py` | DONE | - |
| `POST /api/v1/cache/actions/clear-all` | `app/api/v1/namespaces/cache.py:214` | `app/services/cache/cache_actions_service.py` | DONE | 保持“吞 cache 异常继续”的范围 |
| `POST /api/v1/cache/actions/clear-classification` | `app/api/v1/namespaces/cache.py:275` | `app/services/cache/cache_actions_service.py` | DONE | db_type canonicalize/white-list 校验 |
| `GET /api/v1/cache/classification/stats` | `app/api/v1/namespaces/cache.py:334` | `app/services/cache/cache_actions_service.py` | DONE | - |
| `POST /api/v1/scheduler/jobs/<id>/actions/run` | `app/api/v1/namespaces/scheduler.py:229` | `app/services/scheduler/scheduler_actions_service.py` | DONE | 保持后台线程+create_app fallback |
| `POST /api/v1/scheduler/jobs/actions/reload` | `app/api/v1/namespaces/scheduler.py:301` | `app/services/scheduler/scheduler_actions_service.py` | DONE | 保持 scheduler_module monkeypatch 点 |
| `GET /api/v1/databases/ledgers/exports` | `app/api/v1/namespaces/databases.py:304` | `app/services/files/database_ledger_export_service.py` | DONE | 保持 tags 参数兼容与 `DatabaseLedgerService.iterate_all` patch 点 |
| `GET /api/v1/logs/export` | `app/api/v1/namespaces/logs.py:355` | `app/services/files/logs_export_service.py` | DONE | 保持 `LogsExportService.list_logs` patch 点 |
| `POST /api/v1/auth/login` | `app/api/v1/namespaces/auth.py:135` | `app/services/auth/login_service.py` | DONE | 不改 message_key/错误口径 |
| `POST /api/v1/accounts/classifications/rules/actions/validate-expression` | `app/api/v1/namespaces/accounts_classifications.py:593` | `app/services/accounts/account_classification_expression_validation_service.py` | DONE | DSL v4 校验口径不变 |

## Optional: Page Routes（Phase 2）

| Route | Location | Target | Status | Notes |
| --- | --- | --- | --- | --- |
| `GET/POST /login`（页面） | `app/routes/auth.py:39` | `app/services/auth/login_service.py`（复用 `LoginService.authenticate`） | DONE | 下沉 `User.query` + `check_password` |
| `GET /instances/`（页面） | `app/routes/instances/manage.py:26` | `app/services/instances/instance_list_page_service.py` | DONE | 下沉 `Credential.query` + tag options |
| `GET /credentials/<id>`（页面） | `app/routes/credentials.py:177` | `app/services/credentials/credential_detail_page_service.py` | DONE | 统一 NotFound 口径（`NotFoundError`） |
| `GET /accounts/statistics`（页面） | `app/routes/accounts/statistics.py:63` | `app/services/statistics/accounts_statistics_page_service.py` | DONE | 下沉 instances/recent syncs 查询 |
