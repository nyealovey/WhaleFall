# Architecture Boundary Violations 修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 一次性修复 `docs/changes/refactor/architecture-boundary-violations.md` 中列出的全部分层边界违规(含低严重度)。

**Architecture:** 统一依赖方向为 `API/Routes → Services → Repositories → Models`；将“读模型查询/数据访问”收敛到 Repository，将“业务编排/异常语义”收敛到 Service；API 不再直接 `.query`、不再直接依赖 Repository、也不再直接 import/调用 Tasks。

**Tech Stack:** Flask / Flask-RESTX、SQLAlchemy / Flask-SQLAlchemy、Pytest(uv)、Ruff、Pyright。

---

## 范围清单(来自扫描文档)

- 🔴 Repository → Service 反向依赖: `app/repositories/partition_repository.py`
- 🟡 API 直接 `.query`: `app/api/v1/namespaces/instances_connections.py`、`app/api/v1/namespaces/databases.py`、`app/api/v1/namespaces/accounts_classifications.py`、`app/api/v1/namespaces/tags.py`
- 🟡 API 直接依赖 Repository: `app/api/v1/namespaces/health.py`、`app/api/v1/namespaces/credentials.py`、`app/api/v1/namespaces/users.py`、`app/api/v1/namespaces/tags.py`
- 🟡 Services 内错误放置 Repository 文件: `app/services/account_classification/repositories.py`
- 🟢 Service 依赖 Forms 常量: `app/services/accounts/account_classifications_write_service.py`
- 🟢 API 直接 import Tasks: `app/api/v1/namespaces/instances_accounts_sync.py`

---

## Task 1: 修复 Repository → Service 反向依赖

**Files:**
- Modify: `app/repositories/partition_repository.py`
- Modify: `app/services/partition/partition_read_service.py`

**Steps:**
1. 删除 `PartitionRepository.fetch_partition_info()` 及其对 `PartitionStatisticsService` 的 import。
2. `PartitionReadService` 内改为直接调用 `PartitionStatisticsService().get_partition_info()` 获取分区信息。
3. 验证: `rg -n "from app\\.services\\.statistics\\.partition_statistics_service" app/repositories` 返回空。

---

## Task 2: 补齐“详情读取”Service，移除 API → Repository 依赖

**Files:**
- Create: `app/services/credentials/credential_detail_read_service.py`
- Create: `app/services/users/user_detail_read_service.py`
- Create: `app/services/tags/tag_detail_read_service.py`
- Modify: `app/services/users/user_write_service.py`
- Modify: `app/services/tags/tag_write_service.py`
- Modify: `app/api/v1/namespaces/credentials.py`
- Modify: `app/api/v1/namespaces/users.py`
- Modify: `app/api/v1/namespaces/tags.py`

**Steps:**
1. 为 Credentials/Users/Tags 新增 detail read service，统一提供 `get_*_or_error(id)` (抛 `NotFoundError`)。
2. `UserWriteService` / `TagWriteService` 构造函数改为可选注入 repository，默认内部创建，保证 API 不需要 import repository。
3. API 文件移除 `from app.repositories...`，改为通过 service 获取资源/执行写操作。
4. 验证: `rg -n "from app\\.repositories\\.(users|credentials|tags)_repository" app/api/v1/namespaces/(users|credentials|tags)\\.py` 返回空。

---

## Task 3: 修复 API 直接 `.query` (instances_connections)

**Files:**
- Modify: `app/services/instances/instance_detail_read_service.py`
- Modify: `app/api/v1/namespaces/instances_connections.py`

**Steps:**
1. `InstanceDetailReadService` 补充 `get_instance_by_id(instance_id) -> Instance | None`，供 API “存在即用/不存在返回 None” 场景使用。
2. `instances_connections.py` 中 `Credential.query.get` / `Instance.query.get` 全部改为调用对应的 detail read service。
3. 验证: `rg -n "\\.query\\." app/api/v1/namespaces/instances_connections.py` 返回空。

---

## Task 4: 修复 API 直接 `.query` (databases)

**Files:**
- Create: `app/repositories/instance_databases_repository.py`
- Create: `app/services/instances/instance_database_detail_read_service.py`
- Modify: `app/api/v1/namespaces/databases.py`

**Steps:**
1. 新增 `InstanceDatabasesRepository.get_by_id(database_id)`。
2. 新增 `InstanceDatabaseDetailReadService.get_by_id_or_error(database_id)` (抛 `NotFoundError`)。
3. `databases.py` 中 `Instance.query.get` / `InstanceDatabase.query.filter_by(...)` 改为通过 service 获取。
4. 验证: `rg -n "\\.query\\." app/api/v1/namespaces/databases.py` 返回空。

---

## Task 5: 修复 API 直接 `.query` (accounts_classifications)

**Files:**
- Modify: `app/repositories/accounts_classifications_repository.py`
- Modify: `app/services/accounts/account_classifications_read_service.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `app/api/v1/namespaces/accounts_classifications.py`

**Steps:**
1. Repository 增补 “按 id 获取 classification/rule/assignment” 与 “usage counts” 的查询方法。
2. Read/Write service 提供 `get_*_or_error` 与 `get_classification_usage` 的门面方法(统一抛 `NotFoundError/SystemError`)。
3. API 中所有 `Model.query.*` 改为调用 service 方法。
4. 验证: `rg -n "\\.query\\." app/api/v1/namespaces/accounts_classifications.py` 返回空。

---

## Task 6: 移动错误放置的 repositories.py

**Files:**
- Move: `app/services/account_classification/repositories.py` → `app/repositories/account_classification_repository.py`
- Modify: `app/services/account_classification/orchestrator.py`

**Steps:**
1. 移动文件并修正 import 路径，保持类名 `ClassificationRepository` 不变。
2. 验证: `python -c "from app.services.account_classification.orchestrator import AccountClassificationService"` 能正常 import。

---

## Task 7: 修复 Service 依赖 Forms 常量

**Files:**
- Create: `app/constants/classification_constants.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `app/forms/definitions/account_classification_constants.py`
- Modify: `app/forms/definitions/account_classification_rule_constants.py`

**Steps:**
1. 将 `ICON_OPTIONS`/`RISK_LEVEL_OPTIONS`/`OPERATOR_OPTIONS` 提升到 `app/constants/classification_constants.py`。
2. Service 改为从 `app.constants.classification_constants` 导入。
3. Forms 层常量文件改为从 constants 复用导出(避免重复定义)。
4. 验证: `rg -n "from app\\.forms\\.definitions\\.account_classification_.* import" app/services/accounts/account_classifications_write_service.py` 返回空。

---

## Task 8: 修复 API 直接 import Tasks

**Files:**
- Modify: `app/services/accounts_sync/accounts_sync_actions_service.py`
- Modify: `app/api/v1/namespaces/instances_accounts_sync.py`

**Steps:**
1. `AccountsSyncActionsService` 将 `sync_task` 调整为可选参数；未传入时在运行期惰性加载默认任务函数(避免 import cycle)。
2. API 移除 `from app.tasks.accounts_sync_tasks import ...`，仅注入 `sync_service`。
3. 验证: `rg -n \"from app\\.tasks\\.accounts_sync_tasks\" app/api/v1/namespaces/instances_accounts_sync.py` 返回空。

---

## Task 9: 验证

**Commands:**
- `rg -n \"from app\\.services\" app/repositories/` (应无反向依赖)
- `rg -n \"\\.query\\.\" app/api/` (重点关注上述 4 个文件应为 0)
- `./scripts/ci/ruff-report.sh style` 或 `ruff check app tests`
- `make typecheck` (或 `./scripts/ci/pyright-report.sh`)
- `uv run pytest -m unit`

