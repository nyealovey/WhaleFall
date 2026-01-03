# Ruff Style (D/I/PLC/G) Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:verification-before-completion` before claiming completion.

**Goal:** Make `uv run ruff check . --select D,I,PLC,G` pass with zero diagnostics by fixing missing docstrings and import ordering, without loosening rules.

**Architecture:** Prefer automated fixes first (ruff `--fix` for `I001`/`D202` etc.), then apply systematic, minimal docstrings that follow repo standards (Chinese + Google style, ASCII punctuation). Keep changes surgical and avoid unrelated refactors.

**Tech Stack:** Ruff, Black, isort, Flask-RESTX resources, Alembic migrations.

---

### Task 1: Baseline and scope confirmation

**Files:**
- Read: `pyproject.toml`
- Read: `docs/standards/coding-standards.md`
- Read: `docs/standards/halfwidth-character-standards.md`

**Step 1: Capture current error distribution**

Run: `uv run ruff check . --select D,I,PLC,G --output-format json`
Expected: non-zero exit with a stable set of codes (mostly `D101/D102/D107/D103`, plus a few `I001`).

**Step 2: Identify top offending files**

Run a small script to count diagnostics by file/code.
Expected: majority under `app/api/v1/namespaces/*.py` and some under `migrations/versions/*.py`.

---

### Task 2: Apply automated fixes (imports + docstring spacing)

**Files:**
- Modify: `app/**.py`
- Modify: `migrations/**.py`

**Step 1: Fix import ordering**

Run: `uv run ruff check . --select I --fix`
Expected: `I001` resolved.

**Step 2: Fix docstring formatting issues**

Run: `uv run ruff check . --select D202 --fix`
Expected: removes blank lines after docstrings where applicable.

---

### Task 3: Add missing docstrings in API namespaces

**Files:**
- Modify: `app/api/v1/namespaces/*.py`

**Step 1: Add class docstrings (`D101`)**

For each `BaseResource` subclass without docstring, add a 1-line summary docstring ending with `.` (ASCII).

**Step 2: Add HTTP method docstrings (`D102`)**

For each `get/post/put/delete` method without docstring, add a short docstring (one-liner is acceptable) ending with `.` (ASCII).

Notes:
- Avoid fullwidth punctuation (`。` `，` `：`) in docstrings per `halfwidth-character-standards.md`.
- Do not add empty lines after docstrings (avoid `D202`).

---

### Task 4: Add missing docstrings in services/repositories/types/migrations

**Files:**
- Modify: `app/services/**/*.py`
- Modify: `app/repositories/**/*.py`
- Modify: `app/types/**/*.py`
- Modify: `migrations/versions/**/*.py`

**Step 1: Add `__init__` docstrings (`D107`)**

Add a short docstring describing the initializer purpose.

**Step 2: Add public function docstrings (`D103`)**

Add a short docstring ending with `.` (ASCII).

**Step 3: Migrations**

Ensure `upgrade()`/`downgrade()` functions have docstrings and no blank line after docstring.

---

### Task 5: Verification

**Step 1: Ruff full style gate**

Run: `uv run ruff check . --select D,I,PLC,G`
Expected: `All checks passed!`

**Step 2: Pre-commit gates (targeted)**

Run: `uv run pre-commit run ruff ruff-style-guard --all-files`
Expected: `Passed`

**Step 3: Unit tests**

Run: `uv run pytest -m unit`
Expected: all tests pass.
