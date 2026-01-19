# Settings Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify `app/settings.py` by removing redundancy and reducing boilerplate without changing runtime behavior.

**Architecture:** Keep `Settings` as the single env/config entrypoint; refactor internal helpers/validators for readability and delete unused/duplicate logic.

**Tech Stack:** Python 3.11, `pydantic-settings` (Pydantic v2), `python-dotenv`, `cryptography`

### Task 1: Establish Baseline (Smoke)

**Files:**
- Test: `tests/unit/test_settings_database_url_policy.py`
- Test: `tests/unit/test_settings_password_encryption_key_validation.py`

**Step 1: Run targeted unit tests**

Run: `.venv/bin/pytest -m unit tests/unit/test_settings_database_url_policy.py tests/unit/test_settings_password_encryption_key_validation.py`

Expected: `passed` with exit code `0`.

### Task 2: Simplify `load_dotenv()` Behavior

**Files:**
- Modify: `app/settings.py`
- Test: `tests/unit/test_settings_database_url_policy.py`

**Step 1: Update `Settings.load()` to always use project `.env` path**

Change `load_dotenv(...)` to pass `DOTENV_PATH` directly (avoid `exists()` branching / parent directory searching).

**Step 2: Run targeted unit tests**

Run: `.venv/bin/pytest -m unit tests/unit/test_settings_database_url_policy.py`

Expected: `passed` with exit code `0`.

### Task 3: Remove Redundant Mapping / Duplicate Logic

**Files:**
- Modify: `app/settings.py`

**Step 1: Remove `dict(...)` wrapper in `to_flask_config()`**

Use `self.sqlalchemy_engine_options` directly.

**Step 2: Remove duplicate redis URL validation**

Delete the `_validate()` check that asserts `CACHE_TYPE=redis` must have `CACHE_REDIS_URL` (already enforced/filled in `_normalize_cache_redis_url()`).

### Task 4: Reduce Boilerplate in Validators and Helpers

**Files:**
- Modify: `app/settings.py`

**Step 1: Simplify `_strip_blank_to_none` and `_parse_csv_values`**

Keep semantics, reduce branching / manual loops.

**Step 2: Deduplicate `_ensure_secret_keys`**

Loop over key attributes to avoid duplicated logic and keep error/log wording consistent.

**Step 3: Remove unused `is_production` property (if still unused)**

Replace its single usage with a local `is_production`/`environment_normalized` check.

### Task 5: Verification

**Files:**
- Verify: `app/settings.py`

**Step 1: Run ruff on touched file**

Run: `.venv/bin/ruff check app/settings.py`

Expected: no violations, exit code `0`.

**Step 2: Run unit tests**

Run: `.venv/bin/pytest -m unit`

Expected: `passed` with exit code `0`.

