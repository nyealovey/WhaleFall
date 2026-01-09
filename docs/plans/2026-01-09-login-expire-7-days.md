# Login Expiration (7 days) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 控制“记住我/长期登录”最长 7 天，到期必须重新登录。

**Architecture:** 通过 `app.config["REMEMBER_COOKIE_DURATION"]` 配置 Flask-Login remember_token 过期时间；配置来源统一走 `app/settings.py`；增加契约测试校验 `Set-Cookie` 的 `Expires`。

**Tech Stack:** Flask, Flask-Login, pytest, uv

### Task 1: 写失败测试（remember_token 7 天过期）

**Files:**
- Modify: `tests/unit/routes/test_api_v1_auth_contract.py`

**Step 1: Write the failing test**

```python
@pytest.mark.unit
def test_api_v1_auth_login_sets_remember_cookie_expire_in_7_days(app, client, monkeypatch) -> None:
    # ... patch flask_login.login_manager.datetime.utcnow()
    # ... login then assert remember_token Expires == fixed_now + timedelta(days=7)
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_auth_contract.py::test_api_v1_auth_login_sets_remember_cookie_expire_in_7_days -q`

Expected: FAIL（当前默认 remember_token 为 365 天）

### Task 2: 增加 Settings 配置并写入 Flask config

**Files:**
- Modify: `app/settings.py`

**Step 1: Write minimal implementation**

```python
DEFAULT_REMEMBER_COOKIE_DURATION_SECONDS = 7 * 24 * 3600
# Settings 增加 remember_cookie_duration_seconds
# to_flask_config 写入 REMEMBER_COOKIE_DURATION
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_auth_contract.py::test_api_v1_auth_login_sets_remember_cookie_expire_in_7_days -q`

Expected: PASS

### Task 3: 更新 env.example（可选）

**Files:**
- Modify: `env.example`

**Step 1: Add config key**

```bash
REMEMBER_COOKIE_DURATION=604800
```

### Task 4: 回归验证

Run: `uv run pytest -m unit -q`

Expected: PASS

