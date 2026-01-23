# services/credentials + routes/credentials + templates/credentials

## Status

- 2026-01-23: 已完成 - 已移除旧表单体系(ResourceFormView)残留, 凭据管理仅保留 "页面 + 模态 + /api/v1" 路径.

## Core Purpose

- 提供“凭据(credential)”的列表/详情页渲染入口（routes + templates）。
- 提供凭据的读写服务（list/detail/write/options），供 API 与页面逻辑复用。

## Unnecessary Complexity Found

- `app/routes/credentials.py:32-76`: `_build_credential_filters()` 解析 page/limit/sort，但当前 `index()` 仅渲染筛选 UI，并未使用 page/limit/sort（还重复读取 `request.args`）。属于“为未来预留”的复杂度。
- `app/routes/credentials.py:79-97`: `_normalize_filter_choice()` / `_normalize_status_choice()` / `_extract_tags()` 仅服务于 `_build_credential_filters()`，可随之删除。
- `app/routes/credentials.py:125`: `index()` 返回类型包含 `tuple[Response, int]`，但当前实现始终返回 HTML 字符串。
- `app/services/credentials/credential_detail_page_service.py:17-36`: `CredentialDetailPageService` + `CredentialDetailPageContext` 为单处使用（`app/routes/credentials.py:196-199`），与 `CredentialDetailReadService` 功能重叠。

## Code to Remove

- `app/routes/credentials.py:32-97`: 删除 `_build_credential_filters()` 及其专用 helper，改为在 `index()` 内最小化解析 query 参数（可删 LOC 估算：~70）。
- `app/services/credentials/credential_detail_page_service.py:1-36`: 删除单次使用的 page service/context，改由 route 直接使用 `CredentialDetailReadService`（可删 LOC 估算：~35）。

## Simplification Recommendations

1. `app/routes/credentials.py:index()`
   - Current: 先构建 `CredentialListFilters`（含未使用字段），再重复读取 `request.args` 传给模板。
   - Proposed: 仅解析 `search/credential_type/db_type/status/tags` 并一次性复用；保持渲染参数不变。
   - Impact: 少一个“过滤器构造层”，减少重复与未使用逻辑。

2. `app/routes/credentials.py:detail()`
   - Current: 单独的 PageService/Context。
   - Proposed: 直接使用 `CredentialDetailReadService().get_credential_or_error(...)`。
   - Impact: 删除一次性抽象，减少文件与导入链。

3. 表单形态保持统一
   - Current: 凭据管理已采用模态 + API。
   - Proposed: 继续保持该交互形态，不新增独立 create/edit 表单页。
   - Impact: UX 统一，减少维护入口与重复校验逻辑。

## YAGNI Violations

- `app/routes/credentials.py:32-76`: page/limit/sort 等“预留能力”在当前页面未被使用。
- `app/services/credentials/credential_detail_page_service.py:17-36`: 为单次调用引入 PageContext/Service 层。

## Final Assessment

- 可删 LOC 估算：~260（视死代码删除范围而定）
- Complexity: Medium -> Low
- Recommended action: Proceed（优先删未使用的过滤器构造与单次 PageService；确认后删除未接入路由的表单体系代码）。
