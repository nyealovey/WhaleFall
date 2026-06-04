---
title: Semantic Color Contract
aliases:
  - color-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: guide
created: 2025-12-02
updated: 2026-06-04
owner: WhaleFall Team
scope: "`app/static/css/**`, `app/templates/**`, `app/static/js/**`"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/gate/design-token-governance]]"
---

# Semantic Color Contract

## SSOT

- Visual palette and color roles are defined by root `DESIGN.md`.
- This document only preserves semantic usage boundaries and checks.

## Rules

- MUST: First-party CSS uses tokens from `app/static/css/variables.css`; do not hardcode new HEX/RGB/RGBA outside token definitions.
- MUST: `Signal Copper` is the only decorative accent. Status colors are semantic only: healthy, warning, danger, informational.
- MUST NOT: Restore purple/neon gradients, decorative gradients, page-private color systems, or high-saturation badge variants.
- SHOULD: Status information uses `status-pill`; lightweight metadata uses `chip-outline` or existing ledger chip stacks.
- SHOULD: New visual changes first check `DESIGN.md`, then add or adjust tokens only when a reusable role is missing.

## Checks

- `./scripts/ci/css-token-guard.sh`
- `./scripts/ci/ui-standards-audit-guard.sh`
- `./scripts/ci/component-style-drift-guard.sh`
