# services/credentials + routes/credentials + templates/credentials

## Core Purpose

- 提供“凭据(credential)”的列表/详情页渲染入口（routes + templates）。
- 提供凭据的读写服务（list/detail/write/options），供 API 与页面逻辑复用。

## Unnecessary Complexity Found

- `app/routes/credentials.py:32-76`: `_build_credential_filters()` 解析 page/limit/sort，但当前 `index()` 仅渲染筛选 UI，并未使用 page/limit/sort（还重复读取 `request.args`）。属于“为未来预留”的复杂度。
- `app/routes/credentials.py:79-97`: `_normalize_filter_choice()` / `_normalize_status_choice()` / `_extract_tags()` 仅服务于 `_build_credential_filters()`，可随之删除。
- `app/routes/credentials.py:125`: `index()` 返回类型包含 `tuple[Response, int]`，但当前实现始终返回 HTML 字符串。
- `app/services/credentials/credential_detail_page_service.py:17-36`: `CredentialDetailPageService` + `CredentialDetailPageContext` 为单处使用（`app/routes/credentials.py:196-199`），与 `CredentialDetailReadService` 功能重叠。
- 可能的死代码（与路由注释“表单路由已由前端模态替代”矛盾）：
  - `app/views/credential_forms.py:19-57`
  - `app/views/form_handlers/credential_form_handler.py:16-52`
  - `app/forms/definitions/credential.py:5-51`（且模板 `credentials/form.html` 在仓库中不存在）

## Code to Remove

- `app/routes/credentials.py:32-97`: 删除 `_build_credential_filters()` 及其专用 helper，改为在 `index()` 内最小化解析 query 参数（可删 LOC 估算：~70）。
- `app/services/credentials/credential_detail_page_service.py:1-36`: 删除单次使用的 page service/context，改由 route 直接使用 `CredentialDetailReadService`（可删 LOC 估算：~35）。
- 若确认无调用：
  - `app/views/credential_forms.py:1-57`
  - `app/views/form_handlers/credential_form_handler.py:1-52`
  - `app/forms/definitions/credential.py:1-51`
  - 以及 `app/forms/definitions/__init__.py` 中的 `CREDENTIAL_FORM_DEFINITION` 惰性导入映射
  - 可删 LOC 估算：~160+

## Simplification Recommendations

1. `app/routes/credentials.py:index()`
   - Current: 先构建 `CredentialListFilters`（含未使用字段），再重复读取 `request.args` 传给模板。
   - Proposed: 仅解析 `search/credential_type/db_type/status/tags` 并一次性复用；保持渲染参数不变。
   - Impact: 少一个“过滤器构造层”，减少重复与未使用逻辑。

2. `app/routes/credentials.py:detail()`
   - Current: 单独的 PageService/Context。
   - Proposed: 直接使用 `CredentialDetailReadService().get_credential_or_error(...)`。
   - Impact: 删除一次性抽象，减少文件与导入链。

3. 移除未接入路由的表单 View/Handler/Definition
   - Current: 仍保留 ResourceFormView 体系的 credential 表单代码，但模板缺失且无路由入口。
   - Proposed: 删除死代码，并同步清理 `app/forms/definitions/__init__.py` 的 lazy mapping。
   - Impact: 明确“凭据仅通过前端模态处理”的事实，减少误导。

## YAGNI Violations

- `app/routes/credentials.py:32-76`: page/limit/sort 等“预留能力”在当前页面未被使用。
- `app/services/credentials/credential_detail_page_service.py:17-36`: 为单次调用引入 PageContext/Service 层。

## Final Assessment

- 可删 LOC 估算：~260（视死代码删除范围而定）
- Complexity: Medium -> Low
- Recommended action: Proceed（优先删未使用的过滤器构造与单次 PageService；确认后删除未接入路由的表单体系代码）。

