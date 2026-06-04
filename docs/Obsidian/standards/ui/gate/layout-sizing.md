---
title: Layout Sizing Gate
aliases:
  - layout-sizing-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: gate
created: 2025-12-28
updated: 2026-06-04
owner: WhaleFall FE
scope: "`app/templates/**`, `app/static/css/**`"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/gate/design-token-governance]]"
---

# Layout Sizing Gate

## SSOT

- Visual density, spacing mood, typography scale, radius, shadows, and motion are defined by root `DESIGN.md`.
- This document only keeps enforceable implementation constraints for Flask/Jinja/CSS.

## Rules

- MUST: Page content uses `.layout-shell > .layout-shell-inner` as the width contract.
- MUST: Web pages that extend `base.html` set `{% set page_density = 'dense' %}` unless the page is intentionally outside the operations console.
- MUST: `base.html` defaults `data-density` to `dense`; do not restore `regular` or `compact` page-density tiers.
- MUST: Vertical groups use `.page-section`; spacing is controlled by `--page-spacing-dense`.
- MUST: Filter controls use shared `width_preset` semantic widths; do not restore Bootstrap grid column snippets in templates.
- MUST NOT: Templates add inline `style="width: ..."` or `style="height: ..."` for layout. Server templates emit data attributes; JS/CSS applies visuals after mount.
- SHOULD: Fixed-format controls, tables, charts, and cards use shared component classes and CSS tokens instead of page-private sizing rules.

## Checks

- `./scripts/ci/inline-px-style-guard.sh`
- `./scripts/ci/css-token-guard.sh`
- `pytest -m unit` for template density contracts
