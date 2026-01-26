# Cache Strategy Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为下拉/筛选项引入短 TTL 缓存（最终一致），并减少分类缓存的无效写入，整体降低 DB 读压力与 Redis 写放大。

**Architecture:** 以 `CacheManagerRegistry` 为唯一缓存入口，新增 `OptionsCache`（固定 key + 短 TTL）供 `FilterOptionsService` 读取；分类规则缓存仅保留 `classification_rules:all` 的必要命中点，分类统计从全量规则缓存计算分组，不再依赖/写入 `classification_rules:{db_type}`。

**Tech Stack:** Flask + Flask-Caching(redis) + pytest + pyright

---

### Task 1: 增加 Options TTL 配置（CACHE_OPTIONS_TTL）

**Files:**
- Modify: `app/settings.py`
- Test: `tests/unit/test_settings_cache_options_ttl.py`

**Step 1: 写失败测试（settings 能读 CACHE_OPTIONS_TTL 且拒绝负数）**

Create `tests/unit/test_settings_cache_options_ttl.py`：

```python
import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_cache_options_ttl_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_OPTIONS_TTL", "60")
    settings = Settings.load()
    assert settings.cache_options_ttl_seconds == 60


@pytest.mark.unit
def test_settings_cache_options_ttl_rejects_negative(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_OPTIONS_TTL", "-1")
    with pytest.raises(ValueError, match=r\"CACHE_OPTIONS_TTL\"):
        Settings.load()
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/test_settings_cache_options_ttl.py -q`
Expected: FAIL（字段不存在或校验不生效）

**Step 3: 最小实现**

在 `app/settings.py`：
- 增加 `DEFAULT_CACHE_OPTIONS_TTL_SECONDS = 60`
- 增加 `Settings.cache_options_ttl_seconds`（alias: `CACHE_OPTIONS_TTL`）
- `to_flask_config()` 写入 `CACHE_OPTIONS_TTL`
- `_validate()` 增加 `CACHE_OPTIONS_TTL` 负数校验

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/test_settings_cache_options_ttl.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/settings.py tests/unit/test_settings_cache_options_ttl.py
git commit -m "feat: add cache options ttl setting"
```

---

### Task 2: 引入 OptionsCache 并缓存 FilterOptionsService 读路径

**Files:**
- Create: `app/services/common/options_cache.py`
- Modify: `app/services/common/filter_options_service.py`
- Test: `tests/unit/services/test_filter_options_service_cache.py`

**Step 1: 写失败测试（命中缓存时不应触发 repository 查询；空列表也必须缓存）**

Create `tests/unit/services/test_filter_options_service_cache.py`：

```python
from __future__ import annotations

import pytest

from app.services.common.filter_options_service import FilterOptionsService


@pytest.mark.unit
def test_filter_options_service_caches_instance_select_options(monkeypatch) -> None:
    calls = {"repo": 0}

    class _Repo:
        def list_active_instances(self, *, db_type=None):  # noqa: ANN001
            calls["repo"] += 1
            return []

    service = FilterOptionsService(repository=_Repo())
    assert service.list_instance_select_options(db_type=None) == []
    assert service.list_instance_select_options(db_type=None) == []
    assert calls["repo"] == 1
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/services/test_filter_options_service_cache.py -q`
Expected: FAIL（目前无缓存/会调用两次 repo）

**Step 3: 最小实现**

在 `app/services/common/options_cache.py`：
- 使用 `CacheManagerRegistry.get()` 作为默认 manager（未初始化则返回 None，视为缓存不可用）
- key 统一使用固定前缀：`whalefall:v1:options:*`
- TTL 读取 `current_app.config["CACHE_OPTIONS_TTL"]`，默认 60s
- 提供必要的 `get_* / set_*` 方法（tags/categories/classifications/instances/databases + api options）

在 `app/services/common/filter_options_service.py`：
- 注入 `OptionsCache`（默认启用）
- 对以下方法增加缓存：
  - `list_active_tag_options()`
  - `list_tag_categories()`
  - `list_classification_options()`
  - `list_instance_select_options(db_type)`
  - `list_database_select_options(instance_id)`
  - `get_common_instances_options(db_type)`
  - `get_common_databases_options(filters)`
- 注意：命中判断用 `cached is not None`（空列表也应视为命中）

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/services/test_filter_options_service_cache.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/common/options_cache.py app/services/common/filter_options_service.py tests/unit/services/test_filter_options_service_cache.py
git commit -m "feat: cache filter options with short ttl"
```

---

### Task 3: 精简分类缓存写入 + 统计从全量规则缓存计算

**Files:**
- Modify: `app/services/account_classification/orchestrator.py`
- Modify: `app/services/cache/cache_actions_service.py`
- Test: `tests/unit/services/test_cache_fallback_observability.py`
- Test: `tests/unit/routes/test_api_v1_cache_contract.py`

**Step 1: 写失败测试（分类统计不依赖 per-db_type key）**

在 `tests/unit/services/test_cache_fallback_observability.py` 新增/调整断言：
- 当 `CacheManager.get(\"classification_rules:all\")` 返回 `{\"rules\": [{\"db_type\": \"mysql\"}, ...]}` 时，`db_type_stats[\"mysql\"][\"rules_count\"]` > 0
- 不再要求读取 `classification_rules:{db_type}`，也不再有“mysql 单独失败”的 partial failure case

**Step 2: 运行测试确认失败**

Run: `uv run pytest -m unit tests/unit/services/test_cache_fallback_observability.py -q`
Expected: FAIL（当前仍按 db_type key 读取/统计）

**Step 3: 最小实现**

在 `app/services/account_classification/orchestrator.py`：
- 删除 `_group_rules_by_db_type()` 内对 `self.cache.set_rules_by_db_type(...)` 的调用（避免每次分类都写入 Redis）

在 `app/services/cache/cache_actions_service.py`：
- `get_classification_cache_stats()` 改为：
  1) 读取 `classification_rules:all`
  2) 从 `rules` 列表按 `db_type` 分组计数（normalize lower）
  3) 填充 `CLASSIFICATION_DB_TYPES` 的 `db_type_stats`

**Step 4: 运行测试确认通过**

Run: `uv run pytest -m unit tests/unit/services/test_cache_fallback_observability.py -q`
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/account_classification/orchestrator.py app/services/cache/cache_actions_service.py tests/unit/services/test_cache_fallback_observability.py tests/unit/routes/test_api_v1_cache_contract.py
git commit -m "refactor: reduce classification cache writes"
```

---

### Task 4: 文档与全量验证

**Files:**
- Modify: `docs/changes/refactor/003-cache-strategy-optimization-plan.md`
- Create: `docs/changes/refactor/003-cache-strategy-optimization-progress.md`

**Step 1: 补齐 progress 文档（checklist + 变更记录）**

创建 `docs/changes/refactor/003-cache-strategy-optimization-progress.md`，并在 plan 中补齐“已落地项/验证命令”。

**Step 2: 全量门禁**

Run: `make typecheck`
Run: `uv run pytest -m unit -q`

**Step 3: Commit**

```bash
git add docs/changes/refactor/003-cache-strategy-optimization-plan.md docs/changes/refactor/003-cache-strategy-optimization-progress.md
git commit -m "docs: add cache strategy optimization progress"
```

