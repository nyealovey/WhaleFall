# Deploy Script Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stop running PostgreSQL partition init scripts during prod deploy and make health checks fail correctly when DB/Redis are not connected.

**Architecture:** Keep deploy behavior unchanged except (1) skip the optional partitions init block and (2) replace grep-based “healthy/success” checks with JSON-based checks against `/health/api/health` fields (`data.status`, `data.database`, `data.redis`).

**Tech Stack:** Bash scripts, Docker Compose, Flask health endpoint JSON.

### Task 1: Skip partition init scripts

**Files:**
- Modify: `scripts/deploy/deploy-prod-all.sh:392`

**Step 1: Remove the partition init block**
- Delete the block that executes `sql/init/postgresql/partitions/init_postgresql_partitions_2025_07.sql`.

**Step 2: Replace with an explicit log**
- Log that partition initialization is disabled/skipped.

**Step 3: Run syntax check**
- Run: `bash -n scripts/deploy/deploy-prod-all.sh`
- Expected: exit code `0`

### Task 2: Make deployment health verification strict

**Files:**
- Modify: `scripts/deploy/deploy-prod-all.sh:519`

**Step 1: Add a helper to validate `/health/api/health`**
- Implement a small helper using `python3` + `json` to ensure:
  - `success == true`
  - `data.status == "healthy"`
  - `data.database == "connected"`
  - `data.redis == "connected"`

**Step 2: Replace grep checks**
- Replace any `grep -E "(healthy|success)"` checks on `/health/api/health` with the strict validator.
- Replace `grep -q "healthy"` (substring bug: matches `unhealthy`) with the strict validator.

**Step 3: Run syntax check**
- Run: `bash -n scripts/deploy/deploy-prod-all.sh`
- Expected: exit code `0`
