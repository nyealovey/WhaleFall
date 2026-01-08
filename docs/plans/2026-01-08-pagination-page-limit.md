# Pagination `page` + `limit` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将列表分页 query 参数统一为 `page` + `limit`（替代 `page_size`），并同步前端/文档/门禁/测试，避免契约漂移。

**Architecture:** 后端 `app/utils/pagination_utils.py` 仅使用 `limit` 作为分页大小参数；前端统一只发送 `limit`；不再解析 `page_size`。文档与 CI 门禁同步更新。

**Tech Stack:** Flask + Flask-RESTX, vanilla JS（GridWrapper/TableQueryParams）, pytest, ripgrep-based CI scripts.

---

### Task 1: Backend pagination param normalization

**Files:**
- Modify: `app/utils/pagination_utils.py`
- Modify: `app/api/v1/namespaces/accounts.py`
- Modify: `app/api/v1/namespaces/logs.py`

**Step 1: Write/adjust unit tests (if any)**
- 如果有后端分页解析单测，补充：仅支持 `limit`。

**Step 2: Implement minimal change**
- `resolve_page_size(...)` 读取 `args.get("limit")`，并保持裁剪逻辑不变。
- 修正复用 `resolve_page_size` 解析其它字段（如 hours）时的 key。

**Step 3: Run**
- `uv run pytest -m unit`

---

### Task 2: Frontend request params migrate to `limit`

**Files:**
- Modify: `app/static/js/common/grid-wrapper.js`
- Modify: `app/static/js/common/table-query-params.js`
- Modify: `app/static/js/modules/stores/logs_store.js`
- Modify: `app/static/js/modules/views/instances/list.js`

**Step 1: Update canonical keys**
- GridWrapper 分页请求拼接 `limit=...`，并移除 URL 中 `page_size` 避免双字段并存。
- TableQueryParams 解析层仅支持 `limit`，输出只保留 `limit`。
- 业务代码（logs_store / instances list）请求参数从 `page_size` 改为 `limit`。

**Step 2: Run**
- `uv run pytest -m unit`

---

### Task 3: Docs + gates + contract sync

**Files:**
- Modify: `docs/Obsidian/API/accounts-api-contract.md`
- Modify: `docs/Obsidian/standards/backend/api-naming-standards.md`
- Modify: `docs/Obsidian/standards/ui/pagination-sorting-parameter-guidelines.md`
- Modify: `scripts/ci/pagination-param-guard.sh`
- (Optional) Modify: `CLAUDE.md`

**Step 1: Update docs**
- 将文档中 `page_size` 改为 `limit`。

**Step 2: Update CI gate**
- 门禁改为强制 GridWrapper 使用 `limit=`，并阻止 `page_size=`。

**Step 3: Run**
- `./scripts/ci/pagination-param-guard.sh`
- `uv run pytest -m unit`
