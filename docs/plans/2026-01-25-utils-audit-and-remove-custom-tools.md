# Utils Audit + Remove Custom Tools Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 审计 `app/utils/` 工具使用情况，删除未使用模块；移除 `pagination_utils.py`、替换自研 `rate_limiter.py` 为 Flask-Limiter 扩展；删除 `sqlserver_connection_utils.py` 并清理 SQL Server 适配器对其依赖。

**Architecture:** 先用 ripgrep 统计 `app.utils.*` 直接引用；对未引用模块直接删除；对明确要移除但仍被引用的模块（rate_limiter/sqlserver_connection_utils）用等价/更标准的方式替换调用点；最后跑 `make typecheck` 与 unit tests 验证无回归。

**Tech Stack:** Flask 3 + Pyright + pytest + uv。

---

### Task 1: 审计 `app/utils` 模块引用情况

**Files:**
- Modify/Delete: `app/utils/*.py`

**Step 1: 统计每个 utils 模块的引用次数**

Run:
```bash
for f in app/utils/*.py; do
  base=$(basename "$f" .py)
  [ "$base" = "__init__" ] && continue
  rg -n "app\\.utils\\.${base}\\b" -S app tests scripts >/dev/null || true
done
```

Expected: 输出/确认哪些模块在 `app/tests/scripts` 范围内完全无引用。

**Step 2: 确认待删除清单**

- 未引用：`app/utils/pagination_utils.py` → 直接删除
- 强制移除：
  - `app/utils/rate_limiter.py`（改用 Flask-Limiter）
  - `app/utils/sqlserver_connection_utils.py`（SQLServer adapter 取消诊断工具）

---

### Task 2: 删除未使用的 `pagination_utils.py`

**Files:**
- Delete: `app/utils/pagination_utils.py`

**Step 1: 删除文件并确认无引用**

Run:
```bash
rg -n "pagination_utils" -S app tests
```

Expected: 无匹配。

---

### Task 3: 用 Flask-Limiter 替换自研 `rate_limiter.py`

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements-prod.txt`
- Modify: `app/__init__.py`
- Modify: `app/routes/auth.py`
- Modify: `app/api/v1/namespaces/auth.py`
- Modify/Delete: `tests/unit/services/test_cache_fallback_observability.py`
- Delete: `app/utils/rate_limiter.py`

**Step 1: 引入 Flask-Limiter 依赖**

- `pyproject.toml` 增加 `flask-limiter`
- `requirements-prod.txt` 增加/锁定对应版本（与线上策略一致）

**Step 2: 在 app 级别初始化 limiter**

- `app/__init__.py` 添加全局 `limiter` extension 并在 `initialize_extensions()` 中 `init_app`
- 默认 key 走 `request.remote_addr`（依赖现有 `TrustedProxyFix` 修正真实 IP）

**Step 3: 为登录/改密加上限流**

- Web 登录：仅限制 `POST`（`/auth/login`），key = `username + ip`
- API 登录：`POST /api/v1/auth/login`，同上
- API 改密：`POST /api/v1/auth/change-password`，key = `user_id + ip`

**Step 4: 统一 429 错误输出**

- 对 `/api/v1/**` 返回统一封套（message_key=`RATE_LIMIT_EXCEEDED`）
- 对 Web 登录返回 flash + redirect（维持原交互）

**Step 5: 删除自研模块与相关单测**

- 删除 `app/utils/rate_limiter.py`
- 移除/调整 `tests/unit/services/test_cache_fallback_observability.py` 中仅针对自研限流器的测试

---

### Task 4: 删除 `sqlserver_connection_utils.py` 并清理 SQL Server adapter

**Files:**
- Modify: `app/services/connection_adapters/adapters/sqlserver_adapter.py`
- Delete: `app/utils/sqlserver_connection_utils.py`

**Step 1: 移除 adapter 中的 diagnosis 字段与 import**

仅保留与其他 DB 一致的异常日志字段（error/error_type 等）。

**Step 2: 删除工具文件并确认无引用**

Run:
```bash
rg -n "sqlserver_connection_utils" -S app tests
```

Expected: 无匹配。

---

### Task 5: 全量验证

Run:
```bash
make format
make typecheck
uv run pytest -m unit -q
```

Expected: 全部通过。

