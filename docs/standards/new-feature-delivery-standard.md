# 新增功能交付标准（复用优先）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-11-27  
> 更新：2025-12-25  
> 范围：所有新增功能（API、页面、异步任务、脚本与配置）

## 目的

- 优先复用既有“目录结构 + 通用组件 + 规范门禁”，减少重复造轮子。
- 交付时同步补齐契约、文档与验证记录，避免“功能上线但无法维护/排障”。

## 适用范围

- 新增/扩展路由与页面：`app/routes/`、`app/views/`、`app/templates/`、`app/static/`
- 新增/扩展服务与任务：`app/services/`、`app/tasks/`、`app/scheduler.py`
- 新增/扩展协议与类型：`app/types/`、`docs/reference/`

## 规则（MUST/SHOULD/MAY）

### 1) 设计与落点选择

- MUST：开工前先全仓检索（`rg`）同类能力，优先扩展既有模块（例如已有同域蓝图/服务时不得另起炉灶）。
- MUST：在需求/方案中记录“复用来源”（具体到文件路径或模块名），评审必须可追溯。
- SHOULD：新增能力按业务域落位（routes/services/templates/static 同步归属同一 domain），避免跨目录散落。

### 2) 后端实现约束

- MUST：路由层使用 `safe_route_call`（详见 [编码规范](./coding-standards.md)）。
- MUST：对外响应使用统一封套与错误口径，禁止写 `error/message` 互兜底链（详见 [错误消息字段统一](./backend/error-message-schema-unification.md)）。
- MUST：共享结构类型先在 `app/types/` 定义再复用，避免临时 `dict[str, Any]`。
- SHOULD：新配置项优先收敛到 `app/settings.py`（避免业务代码散落 `os.getenv`），必要时同步更新 `env.example`。

### 3) 前端与模板约束

- MUST：颜色与 Token 治理遵循 [设计 Token 治理](./ui/design-token-governance-guidelines.md) 与 [界面色彩与视觉疲劳控制](./ui/color-guidelines.md)。
- MUST：危险操作确认遵循 [高风险操作二次确认](./ui/danger-operation-confirmation-guidelines.md)，禁止使用浏览器 `confirm()`。
- SHOULD：列表页优先使用 GridWrapper 与统一分页/排序参数（详见 [Grid.js 列表页迁移标准](./ui/gridjs-migration-standard.md)）。

### 4) 文档与变更记录

- MUST：新增功能需要同步新增/更新 `docs/changes/feature/` 下的变更文档，至少包含“目标/非目标、兼容性与迁移、回滚、验证方式”。
- SHOULD：对外接口（路由、JSON 字段、配置项）发生变化时，同步更新 `docs/reference/` 对应参考手册。
- MAY：当新增规则具有可复用价值时，把它上升为 `docs/standards/` 标准，并补齐门禁。

### 5) 验证与门禁

- MUST：提交前完成以下最小自检（按实际改动取子集）：
  - `make format`
  - `ruff check <paths>`
  - `make typecheck`
  - `./scripts/refactor_naming.sh --dry-run`
  - `pytest -m unit`（或最小相关用例集）
  - `./scripts/code_review/eslint_report.sh quick`（如改动 `app/static/js`）

## 正反例

### 正例：扩展已有模块

- 已存在 `app/routes/tags/` 时，新增“标签批量能力”应先扩展该域，而不是新增 `app/routes/tag_bulk_api.py`。

### 反例：重复造轮子

- 页面内直接 new `gridjs.Grid` 自行拼分页/排序参数（应复用 GridWrapper）。
- 业务模块临时构造 `dict[str, Any]` 作为共享结构（应在 `app/types/` 定义）。

## 门禁/检查方式

- 代码质量：`make format`、`ruff check`、`make typecheck`
- 规范门禁脚本（按场景选择）：`scripts/code_review/*_guard.sh`
- 变更记录：检查是否新增/更新 `docs/changes/` 文档并在 PR 描述中给出验证步骤

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为“交付标准”，删除与现状不一致的开发环境/Makefile 说明，改为引用可验证的门禁命令。
