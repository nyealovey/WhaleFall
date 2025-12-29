# Grid List Page Skeleton Phase 0 (Instances/List Pilot) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a reusable `Views.GridPage` skeleton + P0 plugins, then migrate `instances/list` to it with no behavior change (URL sync keeps current behavior).

**Architecture:** Add shared helpers (`UI.escapeHtml`, `UI.resolveErrorMessage`, `UI.renderChipStack`, `GridRowMeta.get`). Implement `Views.GridPage` controller with a minimal plugin API and strict filter allowlist. Migrate `app/static/js/modules/views/instances/list.js` to be “config + domain renderers”, delegating filter wiring / URL sync / export / grid action delegation to plugins.

**Tech Stack:** Grid.js + `GridWrapper`, vanilla JS modules (IIFE + `window.*` exports), Bootstrap, Jinja2 templates, existing UI modules (`UI.createFilterCard`, toast, confirmDanger).

---

## Task 1: Add shared helpers

**Files:**
- Create: `app/static/js/modules/ui/ui-helpers.js`
- Create: `app/static/js/common/grid-row-meta.js`

**Step 1: Implement `UI.escapeHtml`, `UI.resolveErrorMessage`, `UI.renderChipStack`**

Expected API:
- `UI.escapeHtml(value) -> string`
- `UI.resolveErrorMessage(error, fallback) -> string`
- `UI.renderChipStack(names, { gridHtml, ... }) -> string|gridjs.Html`

**Step 2: Implement `GridRowMeta.get(row)`**

Expected API:
- `GridRowMeta.get(row) -> Object`

**Step 3: Wire scripts for the pilot page**

Modify: `app/templates/instances/list.html` to include these scripts before `js/modules/views/instances/list.js`.

**Step 4: Verify**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: no new lint errors in changed files.

---

## Task 2: Implement `Views.GridPage` skeleton + P0 plugins

**Files:**
- Create: `app/static/js/modules/views/grid-page.js`
- Create: `app/static/js/modules/views/grid-plugins/filter-card.js`
- Create: `app/static/js/modules/views/grid-plugins/url-sync.js`
- Create: `app/static/js/modules/views/grid-plugins/action-delegation.js`
- Create: `app/static/js/modules/views/grid-plugins/export-button.js`

**Step 1: Implement `Views.GridPage.mount(config)`**

Requirements:
- Resolve `root/grid/filterForm` (root-scoped query)
- Filter allowlist for filters (block `__proto__/prototype/constructor`)
- Normalize pagination keys via `TableQueryParams.normalizePaginationFilters`
- Provide ctx methods:
  - `applyFiltersFromValues(values, options)`
  - `applyFilters(filters, options)`
  - `applyFiltersFromForm(options)`
  - `getFilters()`
  - `buildSearchParams(filters)`
- Lifecycle: `destroy()` unbinds plugin listeners and destroys filter card if created by plugin

**Step 2: Implement P0 plugins**

- `filterCard`: create `UI.createFilterCard` and forward submit/change to `ctx.applyFiltersFromValues(...)`.
- `urlSync`: on `filtersChanged`, update `history.replaceState` using current behavior (basePath defaults to `location.pathname`).
- `actionDelegation`: delegate `[data-action]` clicks to an allowlisted `actions` map.
- `exportButton`: bind export button click and navigate to `endpoint?query` using `ctx.buildSearchParams`.

**Step 3: Verify**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: no new lint errors.

---

## Task 3: Migrate `instances/list` to `Views.GridPage`

**Files:**
- Modify: `app/static/js/modules/views/instances/list.js`
- Modify: `app/templates/instances/list.html`

**Step 1: Replace page wiring with `Views.GridPage.mount(...)`**

- Remove local implementations of:
  - filter card init + submit/change wiring
  - URL sync (`history.replaceState`) wiring
  - export button wiring
  - grid action delegation wiring
- Keep page-specific logic:
  - store/service/modal setup
  - selection (checkboxes + batch actions)
  - domain renderers / columns / server mapping

**Step 2: Replace duplicated helpers**

- Replace `escapeHtml(...)` with `UI.escapeHtml(...)`
- Replace `resolveRowMeta(...)` with `GridRowMeta.get(...)`
- Replace `renderChipStack(...)` with `UI.renderChipStack(...)`

**Step 3: Verify**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: no new lint errors.

Manual check (optional):
- Open `/instances` and confirm: filter works, URL updates, export downloads, grid actions work, selection + batch actions work.

