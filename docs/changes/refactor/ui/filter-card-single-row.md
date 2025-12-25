# 搜索筛选卡片单行化重构方案

## 背景
目前各业务页面（实例、凭据、标签、日志中心、统计面板等）的筛选区域都基于 `filter_card` 宏。由于历史上逐页拼接的 `col-md-*` 栅格组合不一致，导致按钮、标签选择器或宽字段常常折行。业务方提出“**所有筛选元素在桌面端需保持单行展示**”的体验要求，以便：

- 减少空白和视觉跳动，避免用户频繁滚动寻找字段。
- 使“筛选/清除”按钮位置固定。
- 为后续新增字段留出统一扩展方式（比如横向滚动或折叠更多条件）。

## 现状问题

1. **栅格宽度不统一**：部分页面手写 `col-md-3`、`col-md-4`，部分直接放 `col-12`。当字段总宽度超过 12 栅格时自然换行。
2. **操作区位置漂移**：筛选按钮在有些页面位于第一列、有些位于最后一列，元素高度也不一致。
3. **长内容缺乏约束**：标签选择器或下拉字段没有最小/最大宽度，导致挤占邻居空间。

## 设计目标

1. **桌面端单行**：在 ≥1280px 视口时，所有过滤字段 + 操作区排列在同一行，**禁止出现横向滚动条**，通过紧凑尺寸控制来实现。
2. **中小屏降级**：在 <1280px 视口自动换行（按 2 列或 1 列）以保证可用性。
3. **统一操作区**：筛选按钮固定在右侧末端，“清除”放在按钮下方并贴右对齐。
4. **组件化配置**：通过 `filter_card` 宏接受 `layout="single-row"` 参数，避免每个页面单独写 CSS。

## 布局规范

| 元素 | 桌面宽度 | 中屏宽度 (<1280px) | 说明 |
| --- | --- | --- | --- |
| 普通字段（输入、下拉、标签选择器） | `min-width: 180px; max-width: 240px; flex: 0 0 220px` | `flex: 1 1 45%` | 宽度受限于 240px，上限处自动截断/出现省略号，不得撑破一行。 |
| 标签选择器（token picker） | `max-width: 260px`，可通过 `data-filter-size="260"` 控制 | `flex: 1 1 100%` | 采用紧凑模式（标签两列堆叠、按钮字号减小）。 |
| 操作区（按钮 + 清除） | `flex: 0 0 148px` | `flex: 1 1 100%` | 主按钮 38px 高，辅助按钮文本尺寸 14px。 |
| 卡片容器 | `display:flex; flex-wrap:nowrap; overflow-x:hidden;` | `flex-wrap:wrap;` | 使用 `gap: var(--spacing-md)`，通过 `calc(100% - padding)` 控制总宽度。 |

## 实施步骤

1. **新增样式**  
   - 在 `app/static/css/components/filter-card.css`（若不存在则创建）中定义 `.filter-card--single-row`、`.filter-card__item`、`.filter-card__actions` 等类，实现上述 flex 布局与响应式规则，并设置 `overflow-x:hidden`。
   - 给标签选择器等组件新增 `.filter-card__item--compact`/`data-filter-size` 支持，默认 `max-width: 240px`，禁止拉伸或撑破。

2. **增强宏**  
   - 修改 `app/templates/components/filters/macros.html`，在 `filter_card` 宏中加入 `layout='stacked'` 默认值，若传入 `single-row` 则添加 `filter-card--single-row` 类，并将 slot 内容包裹在 `.filter-card__body` 中。

3. **更新业务页面**  
   - 逐页将 `filter_card(...)` 调用补充 `layout='single-row'`，同时调整 `col_class` 参数为 `filter-card__item`（或直接去掉 `col-*` 类，由宏内部控制）。
   - 操作按钮推荐通过 `filter_card` 的 `actions` slot（若无则新增）统一生成，确保位置一致。

4. **回归检查**  
   - 桌面宽度下各页面（凭据、实例、标签、日志、数据库统计、账户分类等）截图对比，确保无换行。
   - 缩放到 1024px 确认自动换行为 2 列且按钮仍在最右/最下。

## 风险与缓解

| 风险 | 影响 | 缓解策略 |
| --- | --- | --- |
| 旧页面仍依赖 `col-md-*` 栅格 | 单行布局失效 | 扫描 `filter_card` 调用，统一清理 `col_class`，仅保留 `filter-card__item`。 |
| 自定义字段（如 tag-selector）宽度不可控 | 仍可能挤占空间 | 为自定义组件提供 `data-filter-size` 属性，在宏中读取并赋值 `style="flex: 0 0 var(--value)"`，默认 240px。 |
| IE/老旧浏览器不支持新 flex 样式 | 可能不再兼容 | 项目已定位桌面端现代浏览器，可在文档中说明最低支持 Chrome 95+。 |

## 时间成本预估

- 样式与宏改造：0.5 天
- 业务页面批量替换与自测：1.5 天
- 回归（含截图、核对需求方）：0.5 天

> 总计约 2.5 个工作日，建议与设计确认布局及滚动条样式后执行。

## 输出要求

1. 提交 PR 前附上至少 3 页（凭据/实例/日志）对比截图。
2. 在 `docs/standards/version-update-guide.md` 的“页面回归检查”段落补充该规范（待需求稳定后更新）。
3. 新增/改动 CSS 需跑通 `make format && make quality`，并确认 `filter_card` 宏的 Jinja 语法无 lint 问题。

## 紧凑模式准则

为确保“所有字段＋操作区在单行展示”且不依赖滚动条，补充以下准则：

- **字段宽度上限**：任何 `filter-card__item` 的 `max-width` ≤ 240px，除非显式传入 `data-filter-size`。标签选择器默认 220px，并将标签列表改为多行小尺寸显示。
- **输入/选择组件 padding**：统一使用 `var(--spacing-sm)`，高度 36px，减少垂直空间。
- **按钮区域**：筛选按钮宽度 120px，高度 38px，清除按钮改为文本链接（14px），上下间距 4px。
- **标签选择器紧凑样式**：图标+文案单行展示，所选标签以 `chip-outline chip-outline--muted` 形式自动换行，不再占据整行。
- **无滚动条约束**：`.filter-card--single-row` 通过 `overflow-x:hidden` 避免出现横向滚动。若字段数量超出容器宽度，优先缩减字段宽度（遵守上限）再在 1280px 以下自动换行。
