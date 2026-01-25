# 002 移除 ResourceFormView 表单体系方案

> 状态: Completed
> 负责人: @apple
> 创建: 2026-01-23
> 更新: 2026-01-23
> 范围: 移除 `ResourceFormView` + `app/forms/**` 表单定义体系, 统一为 "标签管理" 风格的 API + Modal CRUD
> 关联: `docs/Obsidian/standards/doc/guide/changes.md`, `docs/Obsidian/standards/core/guide/halfwidth-characters.md`, `docs/Obsidian/standards/backend/gate/layer/api-layer.md`

---

## 动机与范围

当前项目存在 2 套并行的表单方案:

1) 旧方案: `ResourceFormView`(服务端渲染独立表单页, `GET/POST`), 配套 `app/forms/definitions/**` + `app/views/form_handlers/**`.
2) 新方案: 参考标签管理页, "页面 + Modal + JS Controller + /api/v1/*" 的 CRUD 交互.

并行带来的问题:

- UX 不一致: 有的资源是独立表单页, 有的是模态框.
- 维护成本高: 字段与校验在模板/JS/API 三处容易漂移.
- 代码残留: 多个 `*/create` `*/<id>/edit` 路由已被模态替代, 但旧实现仍在仓库里, 增加理解成本.

本次重构目标:

- 彻底移除 `ResourceFormView` 体系(代码, 路由, 模板, 文档引用).
- 所有资源管理的新增/编辑表单统一放在模态框模板中, 通过 `/api/v1/*` 执行写操作.

## 现状盘点(以代码为准)

已采用 Modal CRUD 的管理页(示例):

- 标签: `app/routes/tags/manage.py`, `app/templates/tags/index.html`, `app/templates/tags/modals/tag-modals.html`, `app/api/v1/namespaces/tags.py`
- 用户: `app/templates/auth/list.html`, `app/templates/auth/modals/user-modals.html`, `app/api/v1/namespaces/users.py`
- 实例: `app/templates/instances/list.html`, `app/templates/instances/modals/instance-modals.html`, `app/api/v1/namespaces/instances.py`
- 账户分类: `app/templates/accounts/account-classification/index.html`, `app/api/v1/namespaces/accounts_classifications.py`
- 凭据: `app/routes/credentials.py` 已明确 "表单路由已由前端模态替代"

仍残留的 `ResourceFormView` 入口/代码:

- 独立页面表单: `app/routes/auth.py` 的 `/auth/change-password` + `app/templates/auth/change_password.html`
- 仍注册的旧表单路由(但页面已用模态): `app/routes/users.py`, `app/routes/instances/manage.py`, `app/routes/accounts/classifications.py`
- 旧表单体系代码: `app/views/mixins/resource_forms.py`, `app/views/*_forms.py`, `app/views/form_handlers/**`, `app/forms/**`

## 目标形态(统一的 "标签管理" CRUD 模式)

每个资源管理页遵循同一套边界与文件组织:

- 页面路由: `app/routes/**` 只负责渲染管理页(列表/详情), 不再暴露独立 `create/edit` 表单页.
- 表单 UI: `app/templates/**/modals/*.html`(模态框) + 页面模板 `index/list.html`.
- 前端交互: `app/static/js/modules/views/**`(页面挂载 + 模态控制器) + `app/static/js/modules/services/**`(API 封装).
- 后端写操作: 统一走 `app/api/v1/namespaces/**` 的 `/api/v1/*` 端点, 且写接口必须 `@require_csrf`.

## 不变约束

- 安全不变:
  - 写接口仍强制 CSRF(`@require_csrf`), 前端统一用 `httpU` 注入 `X-CSRFToken`(来自 `base.html` 的 `<meta name="csrf-token">`).
  - 权限不降级: `@api_permission_required` 保持现有口径.
  - 频控不放松: 密码修改仍保留 `password_reset_rate_limit`.
- 行为不变(面向 UI 用户):
  - 资源的新增/编辑/删除能力仍可用, 仅交互形态从独立页面统一为模态框.
  - 不新增/修改 DB schema, 不改业务口径.
- API 契约不变:
  - `/api/v1/**` 响应封套与错误口径遵循既有实现, 不引入新格式.

## 关键决策(已确认)

- Instances: 创建/编辑实例不提供 `tag_names` 入口(降低复杂性), 标签仅通过标签管理/批量分配维护.
- Users: 用户模态补齐 `is_active` 开关, 支持启用/停用.
- Change Password: 修改密码成功后强制登出, 并跳转登录页(`/auth/login`).

## 分层边界(依赖方向)

- `app/routes/**`:
  - MUST NOT: import `app/views/*_forms.py` 或 `ResourceFormView`
  - SHOULD: 只 render 模板, 或做最小的 query 参数解析(用于筛选默认值)
- `app/templates/**`:
  - 负责 UI 结构, 不承载写入逻辑
- `app/static/js/modules/**`:
  - 写操作必须走 `/api/v1/**`(通过 `httpU`)
- `app/api/v1/**`:
  - 负责输入校验, 权限, CSRF, 统一封套
- `app/services/**`:
  - 承载业务逻辑与 DB 写入

## 迁移清单(按模块)

### A) Users(用户管理)

现状:

- 管理页已是模态: `app/templates/auth/list.html` + `app/templates/auth/modals/user-modals.html`
- 但仍保留旧路由: `app/routes/users.py` 中的 `/create`, `/<int:user_id>/edit`(依赖 `app/views/user_forms.py`)

目标:

- 删除 `app/routes/users.py` 的旧表单路由与 `UserFormView` 依赖
- 删除旧模板 `app/templates/users/form.html`(若不再被引用)
- 在用户模态中补齐 `is_active` 开关(旧表单曾支持, 当前模态缺失)

### B) Instances(实例管理)

现状:

- 管理页已是模态: `app/templates/instances/list.html` + `app/templates/instances/modals/instance-modals.html`
- 但仍保留旧路由: `app/routes/instances/manage.py` 的 `/create`, `/<int:instance_id>/edit`(依赖 `app/views/instance_forms.py`)
- 存量旧模板: `app/templates/instances/form.html`

目标:

- 删除旧表单路由与 `InstanceFormView` 依赖
- 删除旧模板 `app/templates/instances/form.html`(确认无引用后)
- 创建/编辑实例不支持 `tag_names`(显式决策): 标签只在标签管理/批量分配中维护

### C) Accounts Classifications(账户分类管理)

现状:

- 管理页已是模态: `app/templates/accounts/account-classification/index.html` + `modals/*`
- 但仍保留旧表单路由: `app/routes/accounts/classifications.py` 的 `*/create`, `*/edit`(依赖 `app/views/classification_forms.py`)
- 存量旧模板: `app/templates/accounts/account-classification/classifications_form.html`, `app/templates/accounts/account-classification/rules_form.html`

目标:

- 删除旧表单路由与 `ResourceFormView` 依赖
- 删除不再使用的旧表单模板

### D) Auth Change Password(修改密码)

现状:

- 仍为独立页面表单: `app/routes/auth.py` 的 `/auth/change-password` + `app/templates/auth/change_password.html`
- 同时已经存在 API 写接口: `POST /api/v1/auth/change-password`(`app/api/v1/namespaces/auth.py`)

目标:

- 将修改密码迁移为全站可用的模态框:
  - 模态模板: 建议新增 `app/templates/auth/modals/change-password-modals.html`, 并在 `base.html` 引入
  - 前端控制器: 新增 `app/static/js/modules/views/auth/modals/change-password-modals.js`, 调用 `/api/v1/auth/change-password`
  - 导航触发: `app/templates/base.html` 的 "修改密码" 改为 `data-action="open-change-password"`
- 移除独立页面入口与其脚本(或保留为 302 redirect 到包含模态的页面, 但不再走 `ResourceFormView`)

### E) 删除整套 ResourceFormView 体系(最终目标)

计划移除的代码目录/文件:

- `app/views/mixins/resource_forms.py`
- `app/views/*_forms.py`(instance/user/classification/password/scheduler)
- `app/views/form_handlers/**`
- `app/forms/**`

同时移除对应的旧表单模板(确认无引用后):

- `app/templates/instances/form.html`
- `app/templates/users/form.html`
- `app/templates/accounts/account-classification/classifications_form.html`
- `app/templates/accounts/account-classification/rules_form.html`
- `app/templates/auth/change_password.html`

## 分阶段计划

### Phase 0: 基线盘点与功能对齐清单

目标: 明确 "哪些能力来自旧表单页", 并确认模态方案是否已覆盖.

步骤:

- 全仓定位旧体系引用点: `rg -n "ResourceFormView|app\\.views\\..*_forms|app\\.forms\\.|form_handlers" app`
- 定位仍注册的 `create/edit` 路由: `rg -n "add_url_rule\\(\"/create\"|/edit\"|ChangePasswordFormView" app/routes`
- 对齐字段能力(至少覆盖: required 字段, is_active, password optional 等)

验收口径:

- 输出一份 "功能对齐清单"(本方案文档的 A-D 小节)并确认是否需要补齐字段.

### Phase 1: 修改密码迁移为模态(消灭最后一个独立表单页)

步骤(预期文件):

- 新增模态模板并在 `base.html` 引入:
  - Create: `app/templates/auth/modals/change-password-modals.html`
  - Modify: `app/templates/base.html`(将链接改为按钮, 增加 modal include)
- 新增前端控制器:
  - Create: `app/static/js/modules/views/auth/modals/change-password-modals.js`
  - Modify: 需要在全站加载该脚本(建议在 `base.html` 的 `extra_js` 或全局 bundle 中引入)
- 使用 `httpU.post("/api/v1/auth/change-password", payload)` 提交, 成功后:
  - toast 成功提示
  - 强制登出并跳转 `/auth/login`
- 删除或改造旧入口:
  - Modify: `app/routes/auth.py` 移除 `/auth/change-password` 或改为 redirect
  - Delete: `app/templates/auth/change_password.html`(若无引用)
  - Delete: `app/static/js/modules/views/auth/change_password.js`(若无引用)

验收口径:

- 手工验证:
  - 顶部用户菜单点击 "修改密码" 可打开模态
  - 输入错误旧密码, API 返回错误封套, toast 展示可读提示
  - 成功修改后, 强制登出并跳转登录页
- 回归验证:
  - `uv run pytest -m unit`

### Phase 2: 移除残留的旧表单路由(create/edit)

步骤:

- Modify: `app/routes/users.py` 删除 `/create`, `/<int:user_id>/edit` 路由注册与 `UserFormView` import
- Modify: `app/routes/instances/manage.py` 删除 `/create`, `/<int:instance_id>/edit` 路由注册与 `InstanceFormView` import
- Modify: `app/routes/accounts/classifications.py` 删除 `*/create`, `*/edit` 路由注册与 `AccountClassificationFormView` import

验收口径:

- `rg -n "app\\.views\\.(user|instance|classification)_forms" app/routes` 结果为空
- 手工验证:
  - Users/Instances/Account Classifications 页面 CRUD 正常(模态 + API)

### Phase 3: 删除 ResourceFormView 体系代码与旧模板

步骤:

- Delete: `app/views/mixins/resource_forms.py`
- Delete: `app/views/*_forms.py`
- Delete: `app/views/form_handlers/**`
- Delete: `app/forms/**`
- Delete: 对应旧表单模板(按 "迁移清单" 中列出的文件)
- 全仓修复 import 与 lint/typecheck 报错

验收口径:

- `rg -n "ResourceFormView|ResourceFormDefinition|app\\.forms\\." app` 结果为空
- `make format`
- `make typecheck`
- `uv run pytest -m unit`

### Phase 4: 文档与开发者入口更新

步骤:

- 更新 Quick Reference/协作入口里与旧表单体系相关的描述(若存在):
  - `AGENTS.md`
  - `docs/agent/README.md`
  - `docs/simplified-architecture-proposal.md`(若提及旧体系)

验收口径:

- `rg -n "ResourceFormView|forms/definitions|form_handlers" docs` 结果为空(允许 `docs/changes/**` 历史文档命中)

## 风险与回滚

主要风险:

- 直接访问旧 URL 的兼容性: 书签或外部链接命中 `*/create` `*/edit` `auth/change-password`
- 前端依赖加载顺序: 模态控制器若未全站加载, 可能导致点击无响应
- 表单字段能力回退: 旧表单页存在但模态缺字段(例如用户 `is_active`)

回滚策略:

- 若出现阻断性问题: 回滚本次变更(恢复旧路由与旧模板)
- 若仅是 URL 兼容问题: 将旧 URL 改为 302 redirect 到对应管理页, 并在管理页自动打开模态(通过 query param 或 hash)

## 验证与门禁

建议门禁命令:

- `make format`
- `make typecheck`
- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/pyright-report.sh`
- `uv run pytest -m unit`

建议的全仓搜索自查:

- `rg -n "ResourceFormView|ResourceFormDefinition|app\\.forms\\.|views\\.form_handlers" app`
- `rg -n "/create\\b|/edit\\b|change-password" app/routes app/templates`
