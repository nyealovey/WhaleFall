# 账户变更历史弹窗色彩与组件重构方案

## 背景
- 当前“变更历史”弹窗重用早期自定义 UI：纯橙顶栏、左右圆角与 `badge` 条框，整体使用 HEX 实底色（`#ff5a00`、`#8fd19e`）+ 白底内容，严重偏离《界面色彩与视觉疲劳控制指南》（`docs/standards/ui/color-guidelines.md`）对 2-3-4 规则及组件化要求。
- 权限变更列表以纯文本 + 绿色块状标签呈现，没有复用 `status-pill`、`chip-outline`、`ledger-chip-stack`，语义色无法与其它页面匹配也无法同源控制。
- 模态内容行距/间距缺失，文本对齐混乱（例：“锁定状态 从 否 调整为 是”），同时没有空状态提示，观看体验疲劳。

## 重构目标
1. 将变更历史弹窗完全对齐仪表盘视觉：主色仅保留 `var(--accent-primary)`，辅助色不超过 3，语义色固定 `success|warning|danger|info`；所有颜色由 `variables.css` token 驱动。
2. 复用 chip/pill/ledger 体系：变更类型（add/remove/update）显示 `status-pill`，具体权限使用 `ledger-chip-stack`，字段变更使用 `chip-outline` + `status-pill` 对比前后值。
3. 重新梳理模态信息结构：按照“顶栏信息-权限变更-其他属性-时间戳”层级，采用统一留白与分隔线，保证阅读节奏由排版而非色块驱动。

## 设计策略
### 1. 模态骨架
- 头部采用白底卡片 + `chip-outline chip-outline--brand` 标题“变更历史”；右侧 `status-pill--info` 展示操作类型（新增/撤销/调整），下方辅以 `status-pill--muted` 显示操作人或实例名称。
- 模态主体背景使用 `color-mix(in srgb, var(--surface-muted) 6%, var(--surface-elevated))`，四角圆角 `var(--border-radius-lg)`，阴影 `var(--shadow-sm)`，禁止彩色顶部条。

### 2. 权限变更
- 使用 `permission-section` 风格的分组：
  - “角色变更”：`ledger-chip-stack` 展示新增/移除角色，使用 `status-pill--success/--danger` 表示方向。
  - “系统权限变更”：同样采用 chip stack，附带 `status-pill` 标注“新增/移除”。
  - “其他属性”区块以 `permission-stack` 布局，左侧 `chip-outline--muted` 表示字段名，右侧 `status-pill` 显示“从 A 调整为 B”，其中旧值使用 `ledger-chip--muted`，新值使用常规 chip。
- 超出三条时启用 `+N` 计数 chip，确保单屏色块 ≤ 7。

### 3. 日志与时间
- 时间戳/操作者信息置于底部 `permission-section`，使用 `status-pill--muted` + 小字号 `var(--text-muted)`，禁止再用纯文本灰色。
- 若存在备注，放入 `chip-outline chip-outline--ghost`，与其他内容保持一致。

### 4. CSS 与组件复用
- 新增 `app/static/css/pages/accounts/changes.css` 或复用 `privileges.css` 组件，所有样式仅控制布局：分组间距、栈布局、滚动高度。颜色/阴影全部引用 token，禁止出现 `#` 颜色写法。
- 模态内容高度控制在 `max-height: 70vh`，内容区域滚动，页脚按钮使用 `btn-outline-secondary`。

## 实施步骤
1. **模板重构**：在 `app/templates/components/account_change_modal.html`（假定路径）中引入 `permission-section` 结构，删除旧 `alert`/彩色 header，添加 `chip-outline` 标题与 `status-pill` 元信息。
2. **JS 渲染**：更新 `account-change-viewer.js`（或现有脚本），在构建变更列表时按字段分类，输出 chip/stack HTML；提供 `changeTypeToVariant` 映射确保新增/删除/修改使用不同 `status-pill`。
3. **样式补充**：创建/更新 `changes.css`，导入 `tag-selector.css` 公共组件，仅补上排版逻辑；在 `base.html` 中按需引入。
4. **自检**：
   - `rg -n "bg-"`、`rg -n "#" app/templates/components/account_change_modal.html` 保证无硬编码颜色。
   - `./scripts/refactor_naming.sh --dry-run` 与 `make quality`。

## 风险与缓解
- **旧脚本依赖**：若前端某些场景仍引用旧的 `alert` 结构，需要同步更新渲染逻辑或提供兼容层；可通过 data-version 属性进行灰度。
- **长文本**：权限/字段值可能包含长字符串，建议为 `ledger-chip` 增加 tooltip 并在 CSS 中允许换行；超长文本 fallback 为 `pre-wrap`。
- **滚动性能**：变更历史可能一次性渲染大量条目，应限制单次显示条数或启用分页，避免 DOM 过大。

## 推广
- 将变更历史弹窗作为“历史/日志类模态”基线，应用到实例变更、凭据更新等页面。
- 在 `docs/standards/ui/color-guidelines.md` 的“实施步骤”中增加“历史弹窗案例”条目，提醒所有日志类弹窗引用同一套组件与色彩控制。
