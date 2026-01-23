# Remove ResourceFormView Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 彻底移除旧表单体系(ResourceFormView + app/forms/** + app/views/form_handlers/**)，全站统一为“标签管理”风格：页面 GET 渲染 + 模态表单 + JS + `/api/v1/**` 写接口。

**Architecture:** 页面路由(`app/routes/**`)只负责 `render_template`；新增/编辑/删除等写操作只走 `/api/v1/**`；表单 UI 统一放 `app/templates/**/modals/**`，交互放 `app/static/js/modules/views/**/modals/**`，并通过 `httpU` 注入 CSRF 头。

**Tech Stack:** Flask + Jinja2 + Bootstrap Modal + Vanilla JS modules + `/api/v1`(RestX) + `httpU` + `FormValidator/ValidationRules`.

> 详细迁移清单与决策记录请以 `docs/changes/refactor/002-remove-resource-form-view-plan.md` 为准(单一真源)。

---

### Task 1: 基线盘点(删除入口前的自查)

**Files:**
- Read: `docs/changes/refactor/002-remove-resource-form-view-plan.md`

**Step 1: 全仓确认旧体系引用点为空**

Run:
```bash
rg -n "ResourceFormView|ResourceFormDefinition|app\\.forms\\.|views\\.form_handlers" app
```
Expected: 无输出。

**Step 2: 运行单测作为基线**

Run:
```bash
uv run pytest -m unit
```
Expected: PASS。

---

### Task 2: 修改密码迁移为全站模态 + 成功后强制登出跳转登录页

**Files:**
- Create: `app/templates/auth/modals/change-password-modals.html`
- Create: `app/static/js/modules/views/auth/modals/change-password-modals.js`
- Modify: `app/templates/base.html`
- Modify: `app/routes/auth.py`
- Delete: `app/templates/auth/change_password.html`
- Delete: `app/static/js/modules/views/auth/change_password.js`
- Delete: `app/static/css/pages/auth/change-password.css`

**Step 1: 新增模态模板并在 base 注入**

要点:
- 在 `base.html` 的用户菜单，将“修改密码”改为 `data-action="open-change-password"` 的按钮。
- 在页面底部 include `auth/modals/change-password-modals.html`。
- 全站加载 `js/modules/views/auth/modals/change-password-modals.js`。

**Step 2: 模态提交到 `/api/v1/auth/change-password`**

JS 要点(示例):
```js
const resp = await httpU.post("/api/v1/auth/change-password", payload);
if (!resp?.success) throw new Error(resp?.message || "密码修改失败");
await httpU.post("/api/v1/auth/logout", {});
window.location.href = "/auth/login";
```

**Step 3: 兼容旧入口 URL**

`GET /auth/change-password` 保留但 302 到可打开模态的页面(例如 Dashboard)，并带 query: `open_change_password=1`。

**Step 4: 验证**

Run:
```bash
uv run pytest -m unit
```
Expected: PASS。

---

### Task 3: 移除 Users/Instances/Accounts Classifications 的旧 create/edit 表单路由

**Files:**
- Modify: `app/routes/users.py`
- Modify: `app/routes/instances/manage.py`
- Modify: `app/routes/accounts/classifications.py`

**Step 1: 删除旧路由**

要点:
- 仅保留列表页/详情页等 GET-only 路由。
- create/edit/delete 一律走 `/api/v1/**`。

**Step 2: 验证**

Run:
```bash
uv run pytest -m unit
```
Expected: PASS。

---

### Task 4: 用户模态补齐 is_active 开关

**Files:**
- Modify: `app/templates/auth/modals/user-modals.html`
- Modify: `app/static/js/modules/views/auth/modals/user-modals.js`

**Step 1: 模态中新增开关**

要点:
- create 默认启用；edit 回显 `user.is_active`。
- submit payload 必须包含 `is_active`(boolean)。

**Step 2: 验证**

Run:
```bash
uv run pytest -m unit
```
Expected: PASS。

---

### Task 5: 删除 ResourceFormView 体系残留代码与旧模板

**Files:**
- Delete: `app/views/**`
- Delete: `app/forms/**`
- Delete: `app/templates/**/form*.html`(确认无引用后)

**Step 1: 删除旧目录与模板**

Run:
```bash
rg -n "ResourceFormView|app/forms/|views/form_handlers" app
```
Expected: 无输出。

**Step 2: 全量验证**

Run:
```bash
make format
make typecheck
uv run pytest -m unit
```
Expected: 全部 PASS。

