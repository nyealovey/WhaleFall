# TagSelectorFilter Scoped DOM IDs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `TagSelectorFilter` reusable on the same page by scoping DOM ids to `field_id` and scoping JS queries to the filter container, eliminating collisions caused by fixed ids.

**Architecture:** Keep `field_id` as the stable scope key. The Jinja macro renders `${field_id}-*` ids and a scope container (`data-tag-selector-scope="${field_id}"`). JS binds per-filter “activation” on the open button, and reuses the single modal controller by swapping the active filter’s hidden input + callbacks on each open.

**Tech Stack:** Jinja2 macros, vanilla JS modules, Bootstrap modal, ripgrep, CI guard scripts (`scripts/ci/*-guard.sh`).

---

## Task 1: Scope the macro DOM ids (Phase 1)

**Files:**
- Modify: `app/templates/components/filters/macros.html`

**Step 1: Update fixed ids to `${field_id}-*`**

Replace:

```html
<label for="open-tag-filter-btn">...</label>
<button id="open-tag-filter-btn">...</button>
<div id="selected-tags-preview">...</div>
<div id="selected-tags-chips">...</div>
<input id="selected-tag-names" ...>
```

With:

```html
<label for="{{ field_id }}-open">...</label>
<button id="{{ field_id }}-open">...</button>
<div id="{{ field_id }}-preview">...</div>
<div id="{{ field_id }}-chips">...</div>
<input id="{{ field_id }}-selected" ...>
```

**Step 2: Verify templates still pass `field_id`**

Check these templates already pass unique `field_id`:
- `app/templates/instances/list.html`
- `app/templates/accounts/ledgers.html`
- `app/templates/databases/ledgers.html`

---

## Task 2: Make TagSelectorHelper support per-filter scope (Phase 1)

**Files:**
- Modify: `app/static/js/modules/views/components/tags/tag-selector-controller.js`

**Step 1: Fix TagSelectorManager.create to not construct duplicate controllers**

Ensure `create(root, options)` returns existing instance when the modal root already has `data-tag-selector-id`.

**Step 2: Add scoped binding support to TagSelectorHelper**

Add options:
- `scope` (string, equals `field_id`) and/or
- `container` (Element)

Derive filter elements from the container:

```js
const container = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
const openBtn = container.querySelector(`#${scope}-open`);
const previewEl = container.querySelector(`#${scope}-preview`);
const chipsEl = container.querySelector(`#${scope}-chips`);
const hiddenInput = container.querySelector(`#${scope}-selected`);
```

On open click:
- set `instance.options.hiddenInputSelector = hiddenInput`
- set `instance.options.hiddenValueKey = hiddenValueKey`
- set `instance.options.onConfirm = (...) => updatePreviewDisplay(previewEl, chipsEl, selectedTags)`
- sync selection from `hiddenInput.value` via `instance.store.actions.selectBy(...)`
- open the modal

---

## Task 3: Migrate calling pages off fixed ids (Phase 1)

**Files:**
- Modify: `app/static/js/modules/views/instances/list.js`
- Modify: `app/static/js/modules/views/accounts/ledgers.js`
- Modify: `app/static/js/modules/views/databases/ledgers.js`

**Step 1: Replace `document.getElementById('selected-tag-names')` etc**

Use scope/container queries based on `data-tag-selector-scope` (matches template `field_id`):
- instances: `instance-tag-selector`
- accounts: `account-tag-selector`
- databases: `database-tag-selector`

**Step 2: Update TagSelectorHelper.setupForForm(...) calls**

Stop passing fixed selectors; pass `scope` (and optionally `container`) so the helper self-derives elements.

---

## Task 4: Add UI standard for scoped DOM ids (Phase 2, no Option B)

**Files:**
- Create: `docs/standards/ui/component-dom-id-scope-guidelines.md`
- Modify: `docs/standards/ui/README.md`

**Step 1: Document rules**

Include:
- reusable components must not use fixed global ids
- prefer `data-*-scope` + `${scope}-*` ids or container-scoped queries
- forbid copy/paste fixed ids in macros/components

---

## Task 5: Add CI guard against fixed TagSelectorFilter ids (Phase 2, no Option B)

**Files:**
- Create: `scripts/ci/tag-selector-filter-id-guard.sh`

**Step 1: Guard rules**

Fail if any of these appear in `app/templates` or `app/static/js`:
- `open-tag-filter-btn`
- `selected-tag-names`
- `selected-tags-preview`
- `selected-tags-chips`

Also fail if `tag_selector_filter` macro contains these fixed ids.

Run locally:

```bash
./scripts/ci/tag-selector-filter-id-guard.sh
```

---

## Task 6: Verification

**Step 1: Ensure fixed ids are zero in runtime code**

```bash
rg -n "open-tag-filter-btn|selected-tag-names|selected-tags-preview|selected-tags-chips" app/templates app/static/js
```

Expected: no matches.

**Step 2: Manual sanity**

On a page that can render 2 filters (or by temporarily duplicating one filter in a template), verify:
- open A updates A preview/hidden input only
- open B updates B preview/hidden input only

