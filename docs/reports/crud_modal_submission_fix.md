# CRUD 模态表单提交修复复盘

## 背景
- 2025-11-30 起，用户管理、凭据管理、实例管理与标签管理等 CRUD 流程在点击“保存/创建”后没有任何响应，导致页面无法发起网络请求。
- 线上反馈最初来自 `feat: CRUD 全链路修复`（commit 862f4a8e）合入后的一轮回归测试，运营同学在桌面端多次尝试都无法提交。
- 由于本轮改造主要引入统一的 FormValidator 校验链路，初期怀疑是校验配置回退或规则冲突所致。

## 问题表现
- 所有新建/编辑模态的“保存”按钮点击无效，不触发 loading，也没有 toast。
- 浏览器开发者工具里没有网络请求记录，Console 也没有新的错误日志。
- 使用 `scripts/crud_smoke.py` 触发的接口链路均正常，说明后端逻辑完好、问题只存在前端交互。

## 影响范围
| 模块 | 模板文件 | 说明 |
| --- | --- | --- |
| 用户管理 | `app/templates/auth/modals/user-modals.html` | 新建/编辑用户按钮为 `type="button"`，没有触发表单 `submit` |
| 凭据管理 | `app/templates/credentials/modals/credential-modals.html` | “添加凭据”按钮同样为孤立按钮 |
| 实例管理 | `app/templates/instances/modals/instance-modals.html` | “保存”按钮与 `#instanceModalForm` 脱钩 |
| 标签管理 | `app/templates/tags/modals/tag-modals.html` | “保存”按钮与 `#tagModalForm` 脱钩 |

## 根因分析
1. 模态组件统一封装在 `components/ui/modal.html`，表单主体放在 `modal-body`，按钮位于 `modal-footer`。
2. 新版 CRUD 改造迁移到 FormValidator/JustValidate，但遗漏了 `button` 与对应 `<form>` 的关联：
   - 按钮被声明为 `type="button"`，同时没有绑定任何 `click` 事件。
   - FormValidator 只监听 `form` 的 `submit` 事件，因此永远不会触发 `onSuccess` 回调。
3. 由于网络请求没有发起，页面层面表现为“点击保存没有反应”，并非后端错误。

## 修复方案
- 将模态页脚中的确认按钮改为真正的提交按钮：`type="submit"`。
- 使用原生的 `form="<form-id>"` 属性显式关联到 modal body 中的 `<form>`，即便按钮位于表单外也能触发 `submit`。
- 受影响模板已全部修复：
  - `app/templates/auth/modals/user-modals.html`
  - `app/templates/credentials/modals/credential-modals.html`
  - `app/templates/instances/modals/instance-modals.html`
  - `app/templates/tags/modals/tag-modals.html`
- 其余依赖 `data-modal-confirm` 并使用 UI Modal 辅助库的弹框不受影响，无需调整。

## 验证步骤
1. `make dev start-flask` 启动后端（若已在 docker compose 环境，请保证 `http://localhost:5000` 可访问）。
2. 登录后台，依次打开“用户管理”“凭据管理”“实例管理”“标签管理”页面。
3. 分别点击“新增”按钮，随便填写必填项后点击“保存/创建”：
   - 提交按钮应出现 loading spinner。
   - 浏览器 Network 面板应看到 POST/PUT 请求。
   - 成功后弹出绿色 toast，并刷新表格。
4. 重复步骤 3，在 JustValidate 中故意制造校验错误（例如清空必填项），确保按钮点击后会显示校验提示而不会发起请求。
5. 如有自动化需求，可扩展 `scripts/crud_smoke.py`，新增一步通过 Selenium/Playwright 检查提交按钮的 `type` 和 `form` 属性，但当前修复已满足手工验证。

## 风险与后续
- 风险较低，仅调整 HTML 属性，不影响后端接口与数据。
- 建议在 UI 层添加 `data-testid="submit"` 之类的探针，方便后续 E2E 测试校验。
- 后续优化：
  1. 将 FormValidator 初始化逻辑封装进统一的模态工厂，减少重复代码。
  2. 在 CI 中加入简单的 lint（如 ESLint/DOMLint）检测“在 form 外的按钮若为提交用途必须声明 form 属性”。
