# Pyright Zero-Error Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Fix all Pyright errors in `pyrightconfig.json` (app + scripts + tests) until `uv run pyright --project pyrightconfig.json` returns 0 errors.

**Architecture:** Prefer improving type-safety at the source (stubs/types + narrowings) rather than sprinkling ignores. For SQLAlchemy models that are instantiated with keyword arguments, add typed `__init__` signatures driven by `TypedDict` + `Unpack` types under `app/types/`.

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, Pyright, Ruff, pytest, uv.

---

### Task 1: Reproduce and snapshot current Pyright diagnostics

**Files:**
- Modify: `docs/reports/` (optional: store report artifacts)

**Step 1: Run Pyright**

Run: `uv run pyright --project pyrightconfig.json --outputjson > /tmp/pyright.json`
Expected: non-zero errors (current baseline was ~464 errors).

**Step 2: Identify top offending files**

Run: `jq -r '.generalDiagnostics[].file' /tmp/pyright.json | sort | uniq -c | sort -nr | head`
Expected: `app/services/accounts_sync/permission_manager.py`, capacity services, and contract tests near the top.

---

### Task 2: Add `prometheus_client` stub to satisfy optional dependency imports

**Files:**
- Create: `app/types/stubs/prometheus_client/__init__.pyi`

**Step 1: Add minimal stub**

Define `Counter` and `Histogram` classes with `.labels(...) -> Self` and methods used by the code (`inc`, `observe`).

**Step 2: Verify missing-import errors are gone**

Run: `uv run pyright --project pyrightconfig.json`
Expected: `reportMissingImports` for `prometheus_client` disappears.

---

### Task 3: Fix `JsonValue` mapping usage in `permission_manager.py`

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`
- Reference types: `app/types/structures.py`

**Step 1: Locate `.get()` / `.keys()` on `JsonValue`**

Run: `rg "\\.get\\(|\\.keys\\(\\)" app/services/accounts_sync/permission_manager.py`

**Step 2: Add narrowings**

Use `isinstance(value, Mapping)` / `isinstance(value, dict)` guards before calling mapping methods; normalize to `dict[str, JsonValue]` when needed.

**Step 3: Verify fewer Pyright errors**

Run: `uv run pyright --project pyrightconfig.json`
Expected: `reportAttributeAccessIssue` in `permission_manager.py` reduced to 0.

---

### Task 4: Fix ORM attribute conversions in capacity aggregation read services

**Files:**
- Modify: `app/services/capacity/database_aggregations_read_service.py`
- Modify: `app/services/capacity/instance_aggregations_read_service.py`

**Step 1: Replace `int(model.id)` patterns**

Use `getattr(model, "id", None)` (and other fields) and `cast` to concrete runtime types before conversions / `.isoformat()`.

**Step 2: Verify**

Run: `uv run pyright --project pyrightconfig.json`
Expected: `reportArgumentType` / `reportGeneralTypeIssues` from `Column[...]` conversions eliminated.

---

### Task 5: Add typed kwargs support for frequently-instantiated SQLAlchemy models

**Files:**
- Create: `app/types/orm_kwargs.py`
- Modify: model files under `app/models/` that are instantiated with keyword args in app code/tests

**Step 1: Find model constructor callsites**

Run: `rg -n "=[[:space:]]*[A-Z][A-Za-z0-9_]*\\(" tests app | rg -n "instance_id=|account_id=|created_at=|updated_at="`

**Step 2: For each high-frequency model, define `TypedDict` kwargs**

Example pattern:

```python
class InstanceAccountKwargs(TypedDict, total=False):
    instance_id: int
    account_id: int
    ...
```

**Step 3: Add `__init__(self, **kwargs: Unpack[...]) -> None`**

Keep implementation empty (delegate to SQLAlchemy) but provide signature for Pyright.

**Step 4: Verify**

Run: `uv run pyright --project pyrightconfig.json`
Expected: Large reduction in `reportCallIssue` (“No parameter named ...”).

---

### Task 6: Fix remaining test diagnostics (contract tests) without weakening type safety

**Files:**
- Modify: failing tests under `tests/unit/`

**Step 1: Re-run Pyright and focus on tests**

Run: `uv run pyright --project pyrightconfig.json`

**Step 2: Resolve remaining call/type issues**

Prefer:
- typed model kwargs (Task 5), or
- build objects then assign attributes, or
- `cast()` at test boundaries for intentionally dynamic fixtures.

**Step 3: Verify**

Run: `uv run pyright --project pyrightconfig.json`
Expected: 0 errors.

---

### Task 7: Verification

**Files:**
- None

**Step 1: Run unit tests**

Run: `uv run pytest -m unit`
Expected: PASS.

**Step 2: (Optional) Run pre-commit locally**

Run: `uv run pre-commit run --all-files`
Expected: PASS (or at least no new failures introduced by typing changes).
