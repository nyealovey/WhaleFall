# 系统仪表盘（Dashboard Overview）色彩与交互重构方案

## 背景
- 页面：`app/templates/dashboard/overview.html`、`app/static/js/modules/views/dashboard/overview.js`、`app/static/css/pages/dashboard/overview.css`。
- 现状：统计卡背景、子卡片、图表控件、筛选器分别使用 6+ 种语义色，Grid/列表内仍残留 `badge bg-*`、`text-success` 等硬编码样式，主/次操作按钮在同一区域出现多种饱和底色，严重违背《界面色彩与视觉疲劳控制指南》中的“2-3-4 规则”“单主色 CTA”要求，也与凭据列表等已治理页面风格不一致。

## 目标
1. 单屏非图表可视色彩 ≤7，严格遵循色彩 2-3-4 规则；页面背景、统计卡、Widget 内部全部引用 `app/static/css/variables.css` token。
2. 统计卡、状态列表、告警小组件统一使用 `status-pill`、`chip-outline`、`ledger-chip-stack` 组件，不再保留 `badge bg-success/bg-danger`。
3. 仪表盘所有操作按钮（时间范围、刷新、导出、过滤）仅保留一个 `btn-primary` CTA，其他使用 `btn-outline-*`。
4. JS 渲染逻辑复用 `renderStatusPill/renderChipStack`，列宽和状态列 70px 的基线与凭据、账户台账一致，彻底移除硬编码颜色。

## 设计策略
### 1. Stats Card 区域
- 结构：白底 + `var(--gray-200)` 描边 + `var(--shadow-sm)` 阴影，图标默认 `var(--text-muted)`；单屏最多 2 种背景（白 & 极浅灰）。
- KPI 数字使用 `var(--text-primary)`，增量/同比通过 `status-pill`（`success|danger|muted`）或 `chip-outline--brand` 表达，禁止再使用红/绿渐变底。
- 卡片交互（刷新、展开）改为描边按钮或 `btn-icon`。

### 2. 筛选器与控件
- 时间范围、TOP、类型切换按钮统一 `btn-outline-primary`，仅“刷新仪表盘”或“立即同步”保留 `btn-primary`；下拉/搜索表单的列宽采用 `col-md-3 col-12`，与凭据列表对齐。
- 选中态通过 `ledger-chip` 描边加粗或 `fw-semibold` 字重呈现，不改变背景色。

### 3. 列表 / Widget
- 告警、同步任务、近期操作等列表使用与凭据/实例相同的列宽策略（状态列 70px、操作列 90px、标签列 ≥200px）。
- `renderStatusPill` 用于显示“正常/延迟/失败”，`renderChipStack` 用于展示告警标签、资源类型等；`renderDbTypeChip` 可复用凭据列表的实现来渲染数据库/资源类型。
- 交替行背景、hover 样式沿用 `color-mix(in srgb, var(--surface-muted) 10%, transparent)` 与 20% 的组合，杜绝自定义色块。

### 4. 图表/趋势
- 图表主体可沿用图表库默认配色，但图表外的 Meta（标题、筛选、图例）遵循 `--text-primary` / `--text-muted`，图例图标若需区分语义，限定在 `--info-color`、`--warning-color` 等已定义 token 内。

## 实施步骤
1. **模板（HTML）**
   - 重构 `stats_card` 宏和仪表盘顶部按钮组：主 CTA = `btn-primary`，其余 `btn-outline-secondary/btn-outline-primary`，图标按钮改 `btn-icon`。
   - 筛选器表单列宽改为 `col-md-3 col-12`，删除 `btn-light`、`badge` 等遗留类。
   - Widget 内状态展示统一调用 `status-pill` 组件（可通过宏或 include）。
2. **CSS**
   - 在 `dashboard/overview.css` 中导入/复用 `ledger-chip`、`status-pill` 样式（如源自 `instances/list.css`），删除所有 `#XXX .badge-*`、`background: #f44336` 等硬编码；交替行、hover、按钮描边使用变量。
   - 新增 `.dashboard-stat-card`、`.dashboard-widget` 等类，控制阴影、留白、栅格宽度，确保卡片背景≤2种。
3. **JS**
   - 在 `overview.js` 引入 `renderStatusPill`、`renderChipStack`、`renderDbTypeChip` 等 helper（可直接参考 `credentials/list.js` 最新实现）。
   - 列定义：状态列 70px，标签/元数据列 ≥220px，操作列 90px；所有状态值统一映射到 `status-pill` variant，按钮回调走 toast。
   - 清理 `class="badge bg-success"` 之类字符串拼接，所有颜色转为 token/组件。
4. **QA 与质检**
   - 自检 `./scripts/refactor_naming.sh --dry-run`、`rg "#" app/templates/dashboard -n` 确认无硬编码颜色。
   - 在桌面端检查多种角色下页面色彩数 ≤7，并执行 `make test` 或至少覆盖 `pytest -m unit -- app/tests/dashboard` 相关用例。

## 风险与缓解
- **指标波动辨识度下降**：取消彩色背景后用户可能难以快速分辨升/降。解决：在 `status-pill` 内加入 `fa-arrow-up/fa-arrow-down`，必要时显示百分比并提供 tooltip。
- **历史 Widget 样式不统一**：部分自定义组件可能仍引用私有 CSS。需要同步排查 `app/static/css/pages/dashboard/` 下所有文件并在 code review 中拉 checklist，防止遗漏。

## 推广建议
- 将本方案与凭据列表重构一同纳入“视觉疲劳治理”基线，所有 Dashboard 类迭代必须复用 `ledger-chip`/`status-pill`；提交 PR 时附上本页面与指南的 checklist（主色数量、是否存在硬编码颜色、状态列宽度）。
- 若后续新增仪表盘组件（例如容量趋势、告警分布），在设计阶段即引用本方案并在 `docs/standards/ui/color-guidelines.md` 登记例外色彩，确保透明度与可回溯。
