# Core Constants Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 清理 `app/core/constants/` 中未使用的常量；移除 `tag_categories.py` 的硬编码分类，改为从数据库读取标签分类。

**Architecture:** 以 ripgrep 做静态引用审计；删除“完全无引用”的常量/导出；标签分类通过 SQLAlchemy 对 `tags.category` 做 `distinct + order_by` 获取，API `/api/v1/tags/categories` 返回分类字符串列表，`category_names` 口径退化为 `value->value` 映射（因为分类/标签均为自定义）。

**Tech Stack:** Flask + SQLAlchemy + pytest (unit) + ruff/pyright。

---

### Task 1: 审计 constants 使用情况（只删“确定无引用”的项）

**Files:**
- Modify: `app/core/constants/filter_options.py`
- Modify: `app/core/constants/database_types.py`
- Modify: `app/core/constants/sync_constants.py`
- Modify: `app/core/constants/__init__.py`

**Step 1: 列出 constants 的引用点（只读）**

Run:
```bash
rg -n "app\\.core\\.constants" -S app tests
```

Expected: 输出各 constants 模块的 import 位置，确认可删目标为“全仓无引用”的符号。

**Step 2: 标记可删除项（只写在本计划，不改代码）**

- `PAGINATION_SIZES` / `STATUS_SYNC_OPTIONS` / `SYNC_TYPES` / `SYNC_CATEGORIES`：全仓无引用（仅定义+导出）。
- `DatabaseType.ALL` / `DatabaseType.DEFAULT_PORTS`：全仓无引用（仅定义）。
- `SyncConstants.OPERATION_TYPE_DESCRIPTIONS` / `SyncConstants.CATEGORY_DESCRIPTIONS` / `SyncConstants.OPERATION_TYPE_VALUES` / `SyncConstants.CATEGORY_VALUES`：全仓无引用（仅定义）。

---

### Task 2: 移除硬编码标签分类常量，分类从数据库读取

**Files:**
- Delete: `app/core/constants/tag_categories.py`
- Modify: `app/repositories/tags_options_repository.py`
- Modify: `app/services/tags/tag_options_service.py`
- Modify: `app/services/tags/tags_bulk_actions_service.py`
- Modify: `app/services/common/filter_options_service.py`
- Modify: `app/models/tag.py`
- Test: `tests/unit/routes/test_api_v1_tags_contract.py`

**Step 1: 先写/强化单测（让 bug 可见）**

在 `tests/unit/routes/test_api_v1_tags_contract.py` 的 `test_api_v1_tags_categories_contract` 增加断言：
- `categories` 为 `list[str]`
- 且包含写入的分类（例：`"other"`）

Run:
```bash
uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py::test_api_v1_tags_categories_contract -q
```

Expected: 修改前若接口返回的是 tuple/二元组结构，应能暴露类型/内容不符合预期。

**Step 2: 实现从 DB 读取分类（最小改动）**

- `TagsOptionsRepository.list_categories()` 改为查询 `Tag.category` 的 distinct 列表（建议仅返回 `list[str]`）。
- `TagOptionsService.list_categories()` 透传 `list[str]` 给 API。
- `TagOptionsService.list_all_tags()` 里 `category_names` 改为从 DB 分类构造 `{category: category}`。
- `TagsBulkActionsService.list_instance_tags()` 里 `category_names` 改为从返回的 tags 集合构造 `{category: category}`。
- `FilterOptionsService.list_tag_categories()` 移除对硬编码映射的依赖，label 使用 `build_category_options` 的默认 fallback（label=category）。
- `Tag` model 移除对 `TAG_CATEGORY_CHOICES` 的 import；若 `get_category_choices` 无引用则删除。

**Step 3: 删除 `tag_categories.py` 并清理所有引用**

Run:
```bash
rg -n "TAG_CATEGORY_CHOICES|tag_categories" -S app tests
```

Expected: 不再出现相关 import/引用。

**Step 4: 运行单测验证**

Run:
```bash
uv run pytest -m unit -q
```

Expected: PASS

---

### Task 3: 删除未使用常量并修复导出/引用

**Files:**
- Modify: `app/core/constants/filter_options.py`
- Modify: `app/core/constants/__init__.py`
- Modify: `app/core/constants/database_types.py`
- Modify: `app/core/constants/sync_constants.py`

**Step 1: 删除 `filter_options.py` 中全仓无引用的常量**

删除：
- `PAGINATION_SIZES`
- `STATUS_SYNC_OPTIONS`
- `SYNC_TYPES`
- `SYNC_CATEGORIES`

并同步更新 `app/core/constants/__init__.py` 的 import 与 `__all__`。

**Step 2: 删除 `database_types.py` / `sync_constants.py` 中无引用字段**

删除：
- `DatabaseType.ALL`
- `DatabaseType.DEFAULT_PORTS`
- `SyncConstants.OPERATION_TYPE_DESCRIPTIONS`
- `SyncConstants.CATEGORY_DESCRIPTIONS`
- `SyncConstants.OPERATION_TYPE_VALUES`
- `SyncConstants.CATEGORY_VALUES`

**Step 3: 运行质量检查**

Run:
```bash
make format
make typecheck
uv run pytest -m unit
```

Expected: 全部通过

