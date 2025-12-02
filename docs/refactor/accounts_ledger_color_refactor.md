# 账户台账页面色彩精简重构方案

## 背景
- 账户台账视图（`app/templates/accounts/ledgers.html` + `app/static/css/pages/accounts/ledgers.css`）当前同时呈现数据库类型胶囊、状态徽章、标签筛选和批量操作按钮等十余种高饱和色块，违背《界面色彩与视觉疲劳控制指南》（`docs/standards/color-guidelines.md`）提出的“单视区可视色彩 ≤ 7”与“语义色不超 4”要求。
- 用户在桌面端长时间浏览表格会出现“颜色太杂”的疲劳反馈，导航/筛选/表格的主任务不突出。

## 改造目标
1. 遵循色彩 2-3-4 规则：主色 2（品牌橙 + 中性灰）、辅助色 3（侧边浅蓝/描边灰/柔和橙）、语义色 4（成功/警告/危险/信息）。
2. 将列表中彩色胶囊数量减少 ≥60%，统一映射到 ColorTokens（`app/static/css/variables.css`）。
3. 通过描边、字重、留白表达层级，让用户在 2 分钟内可聚焦主要指标（账户、可用性、标签）。

## 设计策略
### 1. 导航与筛选区
- 顶部按钮组：`btn-primary` 仅保留在“同步所有账户”，其他工具使用 `btn-outline-primary` 或 `btn-outline-light`。
- 筛选 chips：使用灰底描边（`border-color: var(--accent-primary)`，`background: var(--surface-elevated)`），选中态只调高字重。
- 过滤 CTA：保持单一实心主色按钮，其余 CTA 采用描边风格，避免双主色并行。

### 2. 表格与徽章
- 状态列（可用性/是否删除/是否超级）统一改为文本 + 图标，文本颜色使用 `var(--text-primary)`，仅当状态为“禁用/危险”时才套用 `--danger-color` 背景。
- 数据库类型胶囊：改成描边标签，默认 `color: var(--accent-primary)`、`background: transparent`、`border: 1px solid currentColor`。
- 标签列：
  - 引入“分组标签”组件，将“主从”“生产环境”“地域”合并为单个胶囊，内部使用中性色圆点区隔。
  - 胶囊底色统一 `var(--surface-muted)` 的 40% 透明度，文字使用中性灰。
- 行背景：交替行使用 `background: color-mix(in srgb, var(--surface-muted) 5%, transparent)`，其余保持白底。

### 3. 图标与数字
- 列表中的数量、版本号取消颜色，全部采用 `font-weight: 500` 的文本表现。
- 仅在 hover 或交互态改变描边颜色，禁止引入新背景。

## 实施步骤
1. **样式梳理**
   - 统计 `app/static/css/pages/accounts/ledgers.css` 中的颜色引用，全部重定向到 `variables.css` token。
   - 删除旧的 `.badge-success/.badge-warning` 等类，统一引入 `status-pill`、`tag-chip` 组件样式。
2. **组件重构**
   - 新增 `components/status_pill.html` 与对应 CSS/JS（若复用价值高）。
   - 在 `accounts/ledgers.js` 的 Grid 列渲染函数里替换颜色类名，改用新的描边胶囊。
3. **交互验证**
   - 浏览器手工核对四个典型场景（全部、单一 DB 类型、筛选标签、批量导出），确认未新增多余色块。
   - QA 按《色彩指南》附录执行“视觉疲劳”检查，确保色彩数达标。
4. **文档与交付**
   - 在 PR 描述中引用本方案与 `color-guidelines.md`，附上新旧对比截图。
   - 更新 `docs/standards/color-guidelines.md` 的“使用案例”章节（若新增）。

## 验证指标
- 设计自检：浏览器扩展（如 Color Contrast Analyzer）统计账户台账首屏颜色数 ≤ 7。
- 用户访谈：内部 5 人试用 48 小时后反馈“视觉疲劳”降级为“不明显”。
- 功能无回归：`make test`、`pytest -k accounts_ledgers`（若存在）通过。

## 风险与缓解
- **品牌感下降**：若主色使用过少，可在 header 背景或关键 CTA 保留渐变，但数量不超过 2 处。
- **开发范围扩大**：若其他页面共享组件（如标签 chip），须提前沟通影响面，采用 feature flag（CSS scope）逐页切换。
- **旧截图/文档失真**：同步更新产品手册中的界面截图，避免培训资料与实际 UI 不一致。

## 时间线建议
| 阶段 | 内容 | 负责人 | 预计耗时 |
| --- | --- | --- | --- |
| T+0 | 梳理现有颜色 & 组件依赖 | UI/前端 | 0.5 天 |
| T+0.5 | 完成样式与组件改造，提交 PR | 前端 | 1.5 天 |
| T+2 | QA 验证 + 内测反馈 | QA/产品 | 1 天 |
| T+3 | 发布到 staging，收集 48h 反馈 | 产品 | 2 天 |
| T+5 | 评估指标、更新指南案例 | UI/文档 | 0.5 天 |

> 本方案为 color-guidelines 的首个试点页面，所有例外（如确需新增语义色）必须提前在设计评审会上备案。
