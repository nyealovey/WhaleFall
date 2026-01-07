# Refactor 变更

> 状态: Active

本目录用于记录行为不变的结构性调整 (重构, 瘦身, 抽象, 拆分, 兼容/回退逻辑清理等).

## 命名规则

- 本目录及其子目录下新增文档文件名必须使用三位编号前缀 (每个子目录从 `001` 开始递增): `NNN-short-title.md`.
- 多 PR / 多阶段推进的事项 SHOULD 拆分为:
  - `NNN-short-title-plan.md`
  - `NNN-short-title-progress.md`

## 写作规范

详见: `../../standards/changes-standards.md`.

## 文档清单

- `docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`
- `docs/changes/refactor/001-backend-repository-serializer-boundary-progress.md`
- `docs/changes/refactor/002-backend-write-operation-boundary-plan.md`
- `docs/changes/refactor/002-backend-write-operation-boundary-progress.md`
- `docs/changes/refactor/003-backend-form-service-removal-plan.md`
- `docs/changes/refactor/003-backend-form-service-removal-progress.md`
- `docs/changes/refactor/004-flask-restx-openapi-migration-plan.md`
- `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`
- `docs/changes/refactor/005-btn-icon-accessible-name-plan.md`
- `docs/changes/refactor/005-btn-icon-accessible-name-progress.md`
- `docs/changes/refactor/006-navbar-toggler-accessible-plan.md`
- `docs/changes/refactor/006-navbar-toggler-accessible-progress.md`
- `docs/changes/refactor/007-design-token-no-hardcoded-colors-plan.md`
- `docs/changes/refactor/007-design-token-no-hardcoded-colors-progress.md`
- `docs/changes/refactor/008-async-action-feedback-plan.md`
- `docs/changes/refactor/008-async-action-feedback-progress.md`
- `docs/changes/refactor/009-tag-selector-filter-scoped-dom-ids-plan.md`
- `docs/changes/refactor/009-tag-selector-filter-scoped-dom-ids-progress.md`
- `docs/changes/refactor/010-grid-empty-state-cta-plan.md`
- `docs/changes/refactor/010-grid-empty-state-cta-progress.md`
- `docs/changes/refactor/011-timezone-display-and-config-plan.md`
- `docs/changes/refactor/011-timezone-display-and-config-progress.md`
- `docs/changes/refactor/012-no-inline-px-sizes-plan.md`
- `docs/changes/refactor/012-no-inline-px-sizes-progress.md`
- `docs/changes/refactor/013-status-terminology-consistency-plan.md`
- `docs/changes/refactor/013-status-terminology-consistency-progress.md`
- `docs/changes/refactor/014-api-action-business-failure-vs-exception-plan.md`
- `docs/changes/refactor/014-api-action-business-failure-vs-exception-progress.md`
- `docs/changes/refactor/015-layout-sizing-system-plan.md`
- `docs/changes/refactor/015-layout-sizing-system-progress.md`
- `docs/changes/refactor/016-grid-list-page-skeleton-plan.md`
- `docs/changes/refactor/016-grid-list-page-skeleton-progress.md`
- `docs/changes/refactor/017-account-permissions-refactor-v4-plan.md`
- `docs/changes/refactor/017-account-permissions-refactor-v4-progress.md`
- `docs/changes/refactor/018-account-permission-status-dedup-plan.md`
- `docs/changes/refactor/018-account-permission-status-dedup-progress.md`
- `docs/changes/refactor/019-permission-config-version-tags-plan.md`
- `docs/changes/refactor/019-permission-config-version-tags-progress.md`
- `docs/changes/refactor/020-migration-code-cleanup-plan.md`
- `docs/changes/refactor/020-migration-code-cleanup-progress.md`
- `docs/changes/refactor/021-dependency-and-utils-library-refactor-plan.md`
- `docs/changes/refactor/021-dependency-and-utils-library-refactor-progress.md`
- `docs/changes/refactor/022-frontend-ui-polish-plan.md`
- `docs/changes/refactor/022-frontend-ui-polish-progress.md`
- `docs/changes/refactor/023-compatibility-and-fallback-cleanup-plan.md`
- `docs/changes/refactor/023-compatibility-and-fallback-cleanup-progress.md`
- `docs/changes/refactor/024-layer-first-api-restructure-plan.md`
- `docs/changes/refactor/024-layer-first-api-restructure-progress.md`
