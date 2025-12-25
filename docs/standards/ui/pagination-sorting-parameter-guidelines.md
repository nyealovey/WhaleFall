# 分页与排序参数规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-23  
> 更新：2025-12-25  
> 范围：所有列表页（GridWrapper）与后端列表 API（query params 与返回结构）

## 目的

- 列表页 URL 可分享且行为稳定：刷新/复制链接后分页大小不漂移。
- 前后端对分页字段达成单一约定，减少契约漂移与兼容分支。
- 逐步淘汰历史字段，同时保留可观测性（结构化日志）便于清理。

## 适用范围

- 前端：`app/static/js/common/grid-wrapper.js` 及所有列表页脚本。
- 后端：所有“列表接口”（支持分页/排序/筛选）。

## 规则（MUST/SHOULD/MAY）

### 1) 分页参数（统一）

- MUST：统一使用 `page`（从 1 开始）与 `page_size`（每页数量）。
- SHOULD：`page_size` 建议范围 `1~200`（具体上限以接口实现为准，后端需要做裁剪保护）。

### 2) 兼容字段（仅用于兼容旧链接/旧客户端）

- SHOULD：仅在解析阶段识别 `limit/pageSize`，并尽早转写为 `page_size`，避免“新代码继续输出旧字段”。
- MUST：兼容顺序为 `page_size` → `pageSize` → `limit`（与后端工具一致）。

### 3) 后端落点（强约束）

- MUST：列表接口统一通过 `app/utils/pagination_utils.py` 解析分页参数：
  - `resolve_page(...)`
  - `resolve_page_size(...)`（兼容 `limit/pageSize`）
- SHOULD：当请求使用旧字段时记录结构化日志（`module/action`），便于统计与清理。

## 正反例

### 正例：仅在解析阶段兼容

- 解析：支持 `limit/pageSize` → 输出：只使用 `page_size`。

### 反例：新代码继续输出旧字段

- GridWrapper 或页面脚本继续发送 `limit`，导致服务端/日志长期无法清零历史字段。

## 门禁/检查方式

- 脚本：`./scripts/ci/pagination-param-guard.sh`
- 规则：GridWrapper 分页请求必须使用 `page_size`，禁止回退为 `limit`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与门禁说明，统一“兼容字段”的边界与顺序。
