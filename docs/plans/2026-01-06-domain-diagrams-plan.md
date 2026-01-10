# Domain Diagrams Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add developer-facing domain diagram docs (flow, sequence, state machine, API contract) so engineers can map UI actions to code paths and data writes.

**Architecture:** One markdown doc per domain under `docs/Obsidian/architecture/`, each following the same template (Flow, Sequence, State machine, API contract). Keep diagrams aligned with actual code entrypoints and storage tables.

**Tech Stack:** Mermaid diagrams in Markdown, Flask-RESTX endpoints, SQLAlchemy models.

## Scope

- Already done: `docs/Obsidian/architecture/accounts-permissions-domain.md`, `docs/Obsidian/architecture/instances-domain.md`.
- To add next: credentials + connections, capacity + partitions, scheduler, classification.

## Task 1: Add credentials + connections domain doc

**Files:**
- Create: `docs/Obsidian/architecture/credentials-connections-domain.md`
- Modify: `docs/Obsidian/architecture/README.md`

**Step 1: Draft main flow diagram (Flow)**
- Include: credential CRUD (password encryption), connection test (existing instance vs new params), key branches (missing params, unsupported db_type, connect failed).

**Step 2: Draft main sequence diagram (Sequence)**
- Pick one "click once" chain: `POST /api/v1/instances/actions/test` with `instance_id`.
- Participants must include PostgreSQL + External DB; include Redis as "not used" if not participating.

**Step 3: Add optional state machine**
- Prefer: derived instance connection health status (good/warning/poor/unknown), or credential state (active/inactive/deleted).

**Step 4: Add API contract table**
- List endpoints for `credentials` and `connections`, note idempotency and pagination.

**Step 5: Doc quality check**
Run: `rg -n "[，。：；、】【（）…“”‘’、】【]" docs/Obsidian/architecture/credentials-connections-domain.md`
Expected: no matches (enforce halfwidth ASCII punctuation).

## Task 2: Add capacity + partitions domain doc

**Files:**
- Create: `docs/Obsidian/architecture/capacity-partitions-domain.md`
- Modify: `docs/Obsidian/architecture/README.md`

**Step 1: Flow diagram**
- Include: scheduled collection + aggregation tasks and instance action sync-capacity, plus partition create/cleanup/health monitor.

**Step 2: Sequence diagram**
- Pick one chain: scheduled collection task (`collect_database_sizes`) or aggregation task; include SyncSession/SyncInstanceRecord writes.

**Step 3: Optional state machines**
- Include: SyncSession + SyncInstanceRecord status, and partition lifecycle if helpful.

**Step 4: API contract table**
- List `capacity` + `partition` endpoints and key query params (period, pagination, filters).

**Step 5: Doc quality check**
- Same halfwidth punctuation check.

## Task 3: Add scheduler domain doc

**Files:**
- Create: `docs/Obsidian/architecture/scheduler-domain.md`
- Modify: `docs/Obsidian/architecture/README.md`

**Step 1: Flow diagram**
- YAML config -> APScheduler jobstore -> job execution -> dispatch to `app/tasks/*`.

**Step 2: Sequence diagram**
- Pick one chain: `POST /api/v1/scheduler/jobs/{job_id}/run` -> scheduler -> task.

**Step 3: Optional state machine**
- Job state (paused/running) + task execution state (success/failure).

**Step 4: API contract table**
- Scheduler job endpoints list.

**Step 5: Doc quality check**
- Same halfwidth punctuation check.

## Task 4: Add classification domain doc

**Files:**
- Create: `docs/Obsidian/architecture/classification-domain.md`
- Modify: `docs/Obsidian/architecture/README.md`

**Step 1: Flow diagram**
- Rules load (cache/db) -> fetch accounts -> evaluate DSL -> write assignments -> invalidate caches.

**Step 2: Sequence diagram**
- Pick one chain: `POST /api/v1/accounts-classifications/actions/auto-classify`.

**Step 3: Optional state machine**
- Rule lifecycle (active/inactive) and assignment lifecycle (active/inactive/batch).

**Step 4: API contract table**
- Endpoints for classifications, rules, assignments, validation, auto-classify.

**Step 5: Doc quality check**
- Same halfwidth punctuation check.

## Optional: Commit hygiene (human)

- After each domain doc: `git add docs/Obsidian/architecture/*-domain.md docs/Obsidian/architecture/README.md`
- Commit message examples: `docs: add credentials connections domain diagrams`
