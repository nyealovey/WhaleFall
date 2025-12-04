# CRUD 模态框通用重构文档

## 背景与目的
- “新建用户”模态框仍沿用旧的 `modal-header + form + footer` 样式，存在色彩冗余、字段间距不一、按钮语义混乱等问题，无法满足《界面色彩与视觉疲劳控制指南》中 2-3-4 规则与组件复用要求。
- 近期需要对“新建用户”进行重构，同时希望沉淀一套可复用的 CRUD 模态框规范，便于未来在凭据、实例、规则等场景上快速复制。
- 本文结合 color-guidelines.md，输出模态框标准结构、色彩策略、交互与开发落地步骤，作为设计/前端/测试的统一参考。

## 设计基线
1. **结构分区**
   - Header：使用 `chip-outline chip-outline--brand` + 标题，辅以 `status-pill--muted` 标记场景（如“新建”/“编辑”），背景仍为白色，禁止额外色块。
   - Body：按功能块分组（基础信息、权限配置、关联资源），区块之间使用 `color-mix` 描边 `var(--surface-muted) 45%`，与 color-guidelines 中的卡片保持一致。
   - Footer：最多两个按钮——主操作 `btn-primary`（提交）+ 次要操作 `btn-outline-secondary`（取消/关闭）。危险行为需通过二次确认，不允许在模态内引入 `btn-danger` 实心按钮。
2. **色彩策略**
   - 单个模态内主色 ≤2（`--accent-primary` + 文本色），辅助色 ≤3，语义色 ≤4；优先复用 `status-pill`、`chip-outline`、`ledger-chip` 承载状态与标签，禁止新增 HEX/RGB。
   - 输入框、分组背景全部使用白底；提示语、说明性文字采用 `var(--text-muted)`，不可使用浅灰背景模拟“只读”效果。
3. **布局规范**
   - 表单字段统一使用 `row g-3` + `col-md-6 col-12`（单列）或 `col-md-12`（多行文本），标签/说明与输入框间距遵循 `var(--spacing-sm)`。
   - 可选项说明使用内联 `chip-outline--muted`，例如展示密码策略、角色类型。
   - 错误提示使用 `text-danger` + 文本，不再额外配色。

## 交互与行为
1. **状态同步**
   - 模态打开时重置表单、清除校验提示，加载默认值（角色下拉、权限元数据）需要显示 `status-pill--muted` 的“加载中”文案，加载完成后替换为 `status-pill--info`。
   - 成功/失败通知统一交给全局 toast；模态内只负责展示字段级错误。
2. **校验与可用性**
   - 表单校验调用已有 `FormValidator` + `ValidationRules`，所有字段都必须提供中文错误提示，保持与 color-guidelines “文案≤4字”要求一致。
   - 禁止出现多处禁用按钮；当表单校验中时，提交按钮显示 loading 状态（`btn-loading` class + spinner），不可新增颜色。
3. **可访问性**
   - Tab 顺序遵循字段顺序；按钮区补充 `aria-label` 描述动作（例：`aria-label="提交新用户"`）。

## 组件清单
| 场景 | 组件/样式 | 说明 |
| --- | --- | --- |
| 模态标题 | `chip-outline chip-outline--brand` + `status-pill status-pill--muted` | 标记 CRUD 类型，如 “用户 · 新建”。 |
| 分组容器 | `.rule-detail-section` 同款结构 | 直接复用已存在的白底描边卡，保证色彩一致。 |
| 字段提示 | `chip-outline--muted` / `status-pill--info` | 展示匹配逻辑、角色类型等枚举说明。 |
| 列表/标签 | `ledger-chip-stack` | 展示已选标签、角色权限，遵守“超出用 +N”策略。 |
| CTA | `btn btn-primary` + `btn btn-outline-secondary` | 固定顺序：主操作在右，取消在左。 |

## 实施步骤
1. **审计**：罗列所有 CRUD 模态（用户、凭据、实例、账户规则等），对照 color-guidelines 做色彩盘点（记录当前主/辅/语义色、组件数量）。
2. **建立模板**：在 `app/templates/components/ui/` 下新增 `crud-modal.html`（或扩展现有 modal 组件），内置标题 chip + 分组区块 slot，减少重复结构。
3. **样式沉淀**：在 `app/static/css/components/` 新增 `crud-modal.css`，包含本文定义的 `crud-modal__section`、`crud-modal__meta` 等类，引用 color-guidelines 推荐 token。
4. **分批替换**：优先重构“新建用户”模态，验证结构后在同一 MR 中抽象公共 mixin；其余模态按业务模块逐步迁移，确保每次提交附带前/后截图。
5. **质检清单**：
   - [ ] 2-3-4 色彩规则通过。
   - [ ] 模态内仅出现 `status-pill` / `chip-outline` / `ledger-chip` 三类彩色组件。
   - [ ] 按钮数量 ≤2，语义明确。
   - [ ] 表单字段间距一致，无额外背景色。
   - [ ] `./scripts/refactor_naming.sh --dry-run` 与 `rg -n "#" app/templates/...`（HEX 检查）均通过。

## 验收与维护
- **设计**：在交付 Mockup 时附上字段分组、色彩统计与组件列表，评审会同步记录。
- **前端**：提 PR 时必须附上新旧对比截图，并说明是否复用共用模板。
- **测试**：新增“CRUD 模态视觉检查”用例，重点验证色彩数量、按钮语义、键盘可用性。
- **文档更新**：若未来增加新的 CRUD 元素（如批量导入步骤条），需在本篇追加“扩展组件”小节并引用 color-guidelines 的 token，未在 2 个版本内落地的扩展应清理。

> 只要页面使用 CRUD 模态（新建/编辑/复制等），就必须证明其满足本指南与《界面色彩与视觉疲劳控制指南》，否则评审可拒绝合并。

