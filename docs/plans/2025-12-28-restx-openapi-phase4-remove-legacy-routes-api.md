# 004 Flask-RESTX/OpenAPI Phase 4 (Remove Legacy `*/api/*` Routes) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除 `app/routes/**` 下所有 legacy `*/api/*` JSON API 路由实现，仅保留返回 HTML 的页面路由；旧路径继续由 `app/api/__init__.py::_register_legacy_api_shutdown` 统一返回 `410 API_GONE`。

**Architecture:** 保留现有页面蓝图（render_template/redirect 等），移除所有 rule 含 `/api` 的路由与对应 handler；对仅包含 API 的蓝图（common/health/cache/files 等）从 `app/__init__.py::configure_blueprints` 中移除；若页面仍依赖某个旧 `/api` endpoint（例如登出），将其迁移为非 `/api` 的页面路由并保持模板可用。

**Tech Stack:** Flask, pytest, uv

---

## Tasks

### Task 1: Inventory & safety check

**Files:**
- Inspect: `app/routes/**`
- Inspect: `app/templates/**`, `app/static/**`

**Checklist:**
- 确认模板/前端不再引用 `*/api/*`（仅允许 `/api/v1/**`）
- 若存在页面动作仍在 `*/api/*`（例如 form action / logout），先迁移为页面路由

---

### Task 2: Remove legacy API routes under `app/routes/**`

**Files:**
- Modify: `app/routes/**/*.py`（删除所有 `@bp.route("/api...")` / `add_url_rule("/api...")`）
- Modify: `app/__init__.py`（`configure_blueprints()` 移除 API-only 蓝图注册项）
- Modify: `app/routes/**/__init__.py`（如移除了导出的 API-only blueprint）

**Expected:**
- `rg -n \"@.*\\.route\\(\\\"/api|add_url_rule\\(\\\"/api\" app/routes` 无匹配

---

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Changes:**
- Phase 4 checklist 中 “移除旧 `*/api/*` 路由实现...” 标记为完成
- 记录本次清理范围（仅保留页面路由）

---

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/docs/check_api_routes_reference.py` (如该脚本仍用于门禁)

