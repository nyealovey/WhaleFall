# 账户权限详情 & 权限变更历史模态重构方案

## 背景
- 场景：账户台账页面中“查看权限详情”“查看权限变更历史”两类模态（模板位于 `app/templates/accounts/modals/`，脚本在 `app/static/js/modules/views/accounts/ledgers.js`）。
- 现状问题（对照《界面色彩与视觉疲劳控制指南》与账户台账治理结果）：
  1. 模态主体仍使用 `badge bg-*`、`alert-*`、彩色标签，导致单 modal 内颜色＞10，无法与已治理的台账列表共鸣。
  2. 权限状态/风险提示使用 `text-success`/`text-danger` 文本或 `btn-danger`，没有统一的 `status-pill`/`chip-outline` 组件，语义映射模糊。
  3. JSON/差异信息通过彩色表格或 `pre` + 背景色呈现，未复用已有 `ledger-chip` 或 code block 样式；权限变更列表宽度失衡，时间/操作者列过窄。
  4. 操作按钮（复制、导出、关闭）混用 `btn-primary`/`btn-danger`/`btn-outline-light`，违反“单主色 CTA”原则。

## 目标
1. 两类模态均采用“白底 + 描边 + 阴影 + token 组件”布局，在对话框内将非图表颜色控制在 ≤7 种。
2. 权限状态、风险级别、角色标签统一借助 `status-pill`、`chip-outline`、`ledger-chip-stack`，禁止使用 `badge bg-*` 或内联 HEX。
3. 权限详情中的列表/JSON 区域使用标准 `code-block`、`statistics-panel` 样式；变更历史以时间轴/表格形式呈现，列宽遵循账户台账基线（时间列 ≥160px、状态列 90px、操作者列 150px）。
4. 模态 footer 仅保留一个 `btn-primary` CTA（如“导出权限”或“恢复权限”）+ 一个 `btn-outline-secondary`（关闭/复制），其余操作使用 `btn-icon`。

## 设计策略
### 1. 模态结构
- 头部：标题 + `status-pill`（展示当前权限状态/风险）。右上角可选 `btn-icon`（复制 JSON）。
- 主体采用 2-3 段落：
  - 账户摘要卡（ID、所属实例、角色、创建时间）→ `chip-outline--brand/muted`。
  - 权限列表/授权项 → `ledger-row` 或表格 + `status-pill`。
  - JSON/附加信息 → `<pre class="permission-code-block">`，等宽字体。
- 变更历史模态：顶部展示账户信息，下方使用垂直时间轴或表格（每行含时间、操作者、变更摘要、`status-pill` 表示类型）。

### 2. 状态映射
- `granted/active` → `status-pill--success`；`revoked/suspended` → `status-pill--warning`；`error/failed` → `status-pill--danger`；其他 → `status-pill--muted`。
- 权限类型（读、写、管理）使用 `chip-outline`，多标签时采用 `ledger-chip-stack`。

### 3. 表格与时间轴
- 表格列宽：时间 180px、操作者 150px、操作类型 120px、描述自适应，操作列 90px。
- 时间轴样式复用实例详情方案：点线 + `status-pill` + 描述。
- JSON 差异采用 `code-block code-block--muted`，提供“复制 JSON”按钮（`btn-icon`）。

### 4. 空态与反馈
- 当账户无自定义权限时，显示 `modal-empty`（白底描边 + icon）并给出 CTA（例如“前往账户管理”）。
- 错误提示使用 `status-pill--danger` + 文案，不再使用 `alert-danger`。

## 实施步骤
1. **模板**
   - 新建 `accounts/modals/account-permission-detail.html`、`permission-history.html`（或重写现有文件）。
   - 引入组件：`permission-summary-card`、`permission-section`、`permission-code-block`、`permission-history-timeline`。
   - Footer 同步“单主色 CTA + 描边关闭”。
2. **CSS (`app/static/css/pages/accounts/permissions.css`)**
   - 定义模态专属样式：
     - `.permission-modal__summary`（grid + chip-outline）、`.permission-list`（ledger-row）、`.permission-history`（timeline/table）、`.permission-code-block`（白底等宽）。
     - `.modal-empty`、`.permission-status-pill` 等统一引用 token。
3. **JS (`accounts/ledgers.js`)**
   - 在渲染函数中使用 `renderStatusPill`, `renderChipStack`, `formatTime`，构造权限详情/历史 HTML。
   - 提供复制按钮逻辑（`navigator.clipboard.writeText`），遵循日志/实例详情模态模式。
4. **API 扩展（若需要）**
   - 权限历史接口返回 `changed_at`、`changed_by`、`change_type`、`before/after` JSON，供前端渲染时间轴和 code block。
5. **QA**
   - `./scripts/refactor_naming.sh --dry-run`、`rg -n '#[0-9A-Fa-f]{3,6}' app/templates/accounts/modals app/static/css/pages/accounts/permissions.css`。
   - 手工检查不同状态（授予、收回、失败）模态的颜色数量，确保 `btn-primary` 仅出现一次。

## 推广
- 将该模态样式封装为 `components/ui/modals/permission_detail.html`，供实例/凭据等权限详情复用。
- 在 PR checklist 中新增“权限模态色彩治理”项，要求附上截图与 `rg` 检查结果。
- 未来如新增“批量权限操作”模态，必须复用上述组件，并在指南中登记任何新增语义色。
