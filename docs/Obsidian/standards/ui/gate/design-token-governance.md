---
title: Design Token Governance
aliases:
  - design-token-governance-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: gate
created: 2025-12-23
updated: 2026-06-04
owner: WhaleFall Team
scope: "`app/static/css/**` token definitions and references"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/guide/color]]"
---

# Design Token Governance

## SSOT

- Token roles and visual intent come from root `DESIGN.md`.
- `app/static/css/variables.css` is the implementation surface for reusable CSS variables.
- This document governs token lifecycle only; it does not define a separate visual style.

## Rules

- MUST: Reusable tokens are defined once in `variables.css`.
- MUST: Any `var(--token)` reference in first-party CSS resolves to a defined token, except allowed external prefixes such as `--bs-*`.
- MUST NOT: Reintroduce global gradient tokens, oversized radius tokens, heavy shadow tiers, or multiple page-density tiers.
- SHOULD: Historical token aliases are temporary and must be marked as compatibility aliases with a cleanup intent.
- SHOULD: Page CSS may define local variables only inside the component/page scope that consumes them.

## Checks

- `./scripts/ci/css-token-guard.sh`
- `./scripts/ci/ui-standards-audit-guard.sh`
