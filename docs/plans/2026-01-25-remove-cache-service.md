# Remove CacheService Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 彻底删除 `CacheService` 体系（`app/services/cache_service.py`），缓存仅保留 `CacheManager`（`app/utils/cache_utils.py`）这一套抽象，同时保证现有分类缓存/健康检查/缓存管理 API 的对外行为不回归。

**Architecture:** 以 `CacheManagerRegistry.get()` 作为唯一缓存入口；补齐 `CacheManager` 的 `delete()` 与 `get_stats()` 能力；将分类缓存访问器 `ClassificationCache` 改为直接读写固定 key（`classification_rules:*`）；`CacheActionsService`/health API 取消对 `CacheService` 的依赖，改为调用 `CacheManager`/现有 health service。

**Tech Stack:** Flask + Flask-Caching(redis backend) + pytest

---

### Task 1: CacheManager 补齐能力（delete / stats / default_timeout 对齐 Settings）

**Files:**
- Modify: `app/utils/cache_utils.py`
- Modify: `app/__init__.py`
- Test: `tests/unit/services/test_cache_fallback_observability.py`

**Step 1: 写一个失败的测试（delete + fallback 日志字段）**

在 `tests/unit/services/test_cache_fallback_observability.py` 增加：
- `CacheManager.delete()`：当底层 cache.delete 抛异常时应返回 False，并带 `fallback=True`/`fallback_reason` 的 warning log
- `CacheManager.set(timeout=0)`：timeout=0 必须被原样透传（不被 default_timeout 覆盖）

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/services/test_cache_fallback_observability.py -q`
Expected: FAIL（方法不存在或日志字段不符合断言）

**Step 3: 最小实现**

在 `app/utils/cache_utils.py`：
- 给 `CacheManager.__init__` 增加 `default_timeout` 入参（默认仍为 300）
- 新增 `delete(key) -> bool`
- 新增 `get_stats() -> dict[str, object]`（优先读取 `cache.cache.info()`；不可用时返回可解释的结构）
- 将 get/set/delete 的异常日志统一补齐：`fallback=True`、`fallback_reason`、`error_type`

在 `app/__init__.py`：
- 初始化 CacheManager 时传入 `settings.cache_default_timeout_seconds`

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/services/test_cache_fallback_observability.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/utils/cache_utils.py app/__init__.py tests/unit/services/test_cache_fallback_observability.py
git commit -m "refactor: enhance cache manager primitives"
```

---

### Task 2: 分类缓存改为 CacheManager（替换掉对 CacheService 的依赖）

**Files:**
- Modify: `app/services/account_classification/cache.py`
- Modify: `app/services/account_classification/orchestrator.py`（如需适配新接口）
- Test: `tests/unit/services/test_account_classification_facts_and_cache_guards.py`

**Step 1: 写一个失败的测试（ClassificationCache 只接受 wrapped schema）**

将 `tests/unit/services/test_account_classification_facts_and_cache_guards.py` 中的 stub manager 从
`get_classification_rules_cache()` 迁移为 `CacheManager.get(key)` 语义：
- 当 `CacheManager.get("classification_rules:all")` 返回 `{"rules": [...]}` 时命中
- 当返回 legacy list 时必须返回 None（保持现有 gate）

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_facts_and_cache_guards.py -q`
Expected: FAIL（接口尚未迁移）

**Step 3: 最小实现**

在 `app/services/account_classification/cache.py`：
- 注入依赖从 `CacheService` 改为 `CacheManager`
- key 固定为：
  - 全量：`classification_rules:all`
  - 按类型：`classification_rules:{db_type}`
- TTL 读取 `current_app.config["CACHE_RULE_TTL"]`（与 Settings 一致）
- invalidate_all / invalidate_db_type 通过 `CacheManager.delete(key)` 实现

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_facts_and_cache_guards.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/account_classification/cache.py tests/unit/services/test_account_classification_facts_and_cache_guards.py
git commit -m "refactor: move classification cache to cache manager"
```

---

### Task 3: CacheActionsService 去 CacheService 化（保留 API 行为）

**Files:**
- Modify: `app/services/cache/cache_actions_service.py`
- Modify: `app/api/v1/namespaces/cache.py`（若需要）
- Test: `tests/unit/routes/test_api_v1_cache_contract.py`
- Test: `tests/unit/services/test_cache_fallback_observability.py`

**Step 1: 写一个失败的测试（cache contract 不依赖 cache_service 全局单例）**

在 `tests/unit/routes/test_api_v1_cache_contract.py`：
- 移除 `monkeypatch.setattr(cache_service_module, "cache_service", ...)`
- 改为 patch `CacheActionsService` 的内部依赖（例如 `_get_cache_manager()` 或 `_get_classification_cache()`）返回 dummy

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -q`
Expected: FAIL

**Step 3: 最小实现**

在 `app/services/cache/cache_actions_service.py`：
- 统计：改为 `CacheManager.get_stats()`
- `clear-classification`：仍然走 `AccountClassificationService().invalidate_cache()/invalidate_db_type_cache()`
- `clear-user/instance/all`：维持现有“成功但不实际清理”的行为（仅日志 + True），不引入 scan/keys 等模式删除（用户明确不考虑）

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/cache/cache_actions_service.py app/api/v1/namespaces/cache.py tests/unit/routes/test_api_v1_cache_contract.py
git commit -m "refactor: decouple cache actions from cache service"
```

---

### Task 4: Health API 去 CacheService 化

**Files:**
- Modify: `app/services/health/health_checks_service.py`
- Modify: `app/api/v1/namespaces/health.py`
- Test: `tests/unit/routes/test_api_v1_health_extended_contract.py`

**Step 1: 写一个失败的测试（/health/cache 不再 patch _get_cache_service）**

在 `tests/unit/routes/test_api_v1_health_extended_contract.py`：
- 移除对 `_get_cache_service` 的 monkeypatch
- 改为 patch `app.services.health.health_checks_service.check_cache_health` 返回 `{healthy: True, status: "connected"}`

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_health_extended_contract.py -q`
Expected: FAIL

**Step 3: 最小实现**

在 `app/api/v1/namespaces/health.py`：
- `check_cache_health()` 直接复用 `app.services.health.health_checks_service.check_cache_health`
- 删除对 `CacheService/cache_service/CACHE_EXCEPTIONS` 的 import

在 `app/services/health/health_checks_service.py`：
- 删除对 `app.services.cache_service.CACHE_EXCEPTIONS` 的依赖（改为复用 `cache_utils` 的异常集合，或本地定义）

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_health_extended_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/health/health_checks_service.py app/api/v1/namespaces/health.py tests/unit/routes/test_api_v1_health_extended_contract.py
git commit -m "refactor: remove cache service dependency from health checks"
```

---

### Task 5: 删除 CacheService（含初始化与引用清理）

**Files:**
- Delete: `app/services/cache_service.py`
- Modify: `app/__init__.py`
- Update imports/usages across repo

**Step 1: 删除文件并清理引用**

- 从 `app/__init__.py` 移除 `init_cache_service` import 与调用
- 删除所有 `from app.services.cache_service import ...` 的引用

**Step 2: 全量测试**

Run: `make typecheck`
Run: `uv run pytest -m unit -q`

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove cache service subsystem"
```

