# UI 组件化推进方案

> 目标：在 `modules/ui/` + `templates/components/ui/` 下沉淀通用 UI 资产，减少页面层重复 DOM/JS，最终实现“页面只组合组件 + 填充配置”。

## 1. 背景
- 经过筛选卡的重构（`UI.createFilterCard` + `components/ui/filter_card.html`），账户/实例/标签/日志/会话等页面的筛选逻辑已统一：模板只 include UI 片段，视图脚本只提供回调。
- 其余 UI 场景仍存在大量复制粘贴：模态窗口、统计卡、批量操作区、步骤/表单段、TagSelector 等。继续沿用“JS 行为 + 模板结构”双线抽离，可显著减轻维护成本。

## 2. 已完成里程碑
1. **FilterCard 组件**
   - JS：`app/static/js/modules/ui/filter-card.js`，封装注册/自动提交/事件广播，提供 `emit`, `serialize`, `destroy`。
   - 模板：`app/templates/components/ui/filter_card.html`，统一卡片 DOM；`components/filters/macros.html` 仅承担配置桥接。
   - 适用页面：accounts / instances / credentials / tags / logs / sync_sessions / capacity_stats 等，原先 7 套筛选 JS 已删除。
2. **Modal 组件（逐步推广中）**
   - JS：`app/static/js/modules/ui/modal.js` 暴露 `UI.createModal`，合并 open/close/loading/confirm 逻辑。
   - 模板：`app/templates/components/ui/modal.html`，可配置对话框尺寸/滚动/页脚内容。
   - 已接入：凭据删除（credentials/list）、标签删除（tags/index）、日志详情查看（history/logs）。下一步继续覆盖 tags 批量操作、实例/会话详情等模态。

> 这一模式验证了“JS 行为 + 模板结构”的组合是可行的，可作为后续组件的蓝本。

## 3. 下一批优先组件
| 组件 | 现状痛点 | 目标产出 |
| --- | --- | --- |
| Modal/Dialog | 各页面重复 `<div class="modal">` + bootstrap 初始化，按钮与 loading 逻辑分散。 | `UI.createModal` + `components/ui/modal.html`，支持 confirm/danger/async 等模式。（已落地） |
| StatsCard & Card Layout | 统计页面复制大量 `.card` DOM，更新颜色/图标需逐页改。 | `components/ui/stats_card.html` + 对应 JS helper，字段和图标通过 config 注入。（已落地） |
| BatchActionToolbar | 实例/标签/凭据都有“批量选中 + 操作”区域，按钮状态逻辑重复。 | `UI.createBatchToolbar({ selectAllSelector, actions })` + 模板 slot。 |
| Form Field / Section | Resource Form 仍在模板中手写 label/col 布局。 | `components/ui/form_field.html` + schema -> template helper，配合 ResourceFormController。 |
| Table/List Shell | 多个页面重复 table header + loading/empty 状态。 | `components/ui/table.html` + JS helper（分页、排序、loading 管理）。 |

## 4. 推进步骤
1. **梳理结构**：对每类 UI 收集引用（模板 + JS），确认共有属性/差异点，列出 config schema。
2. **定义接口**：
   - JS：`modules/ui/<component>.js` 暴露 `createX(options)`（挂载/更新/销毁）。
   - 模板：`components/ui/<component>.html` 负责 DOM，传入的数据用 context。
3. **试点替换**：
   - 每个组件先在一个页面验证（例如 Modal -> 凭据删除、StatsCard -> 容量统计）。
   - 验证通过后编写 README/示例，再推广到其他页面。
4. **按需加载**：在 `base.html` 仅保留必要的 UI 基础（FilterCard、Modal），其他组件随页面 chunk 注入。
5. **监控指标**：通过 `cloc modules/views`、bundle size、模板行数等量化减重效果。

## 5. 任务拆分
| 任务 | 负责人 | 输出物 | 备注 |
| --- | --- | --- | --- |
| Modal 组件 | @devA | `UI.createModal`, `components/ui/modal.html` | 兼容 bootstrap，支持 confirm/loading。 |
| StatsCard 组件 | @devB | `components/ui/stats_card.html`, config 示例 | 首先改 `statistics/*.html`。 |
| BatchActionToolbar | @devC | JS helper + 模板 | 先用于实例/标签页面。 |
| Form Field 模板 | @devD | `components/ui/form_field.html`, schema 映射 | 与 `ResourceFormController` 对齐。 |
| Table Shell | @devE | `components/ui/table.html` + pagination helper | 日志/会话先接入。 |

每个任务需同步更新 `docs/refactoring/view_layer_inventory.md` 与示例文档（截图/说明）。

## 6. 验收标准
- 80%+ 使用频率最高的 UI 场景均有对应组件（Modal/StatsCard/Toolbar/Form/Table）。
- 视图脚本行数进一步下降（监控 `cloc modules/views`），模板中的重复 DOM 明显减少。
- 新组件附带 README/示例，PR 模板中新增“是否使用 UI 组件”检查项。
- `base.html` 中业务脚本 ≤ FilterCard + Modal 等 2~3 个，其余均按需加载。

## 7. 后续安排
- 本周锁定 Modal + StatsCard 试点，下周批量替换批量操作区与表格壳。
- 结合 `docs/refactoring/frontend_code_reduction.md` 的阶段计划，记录完成度与代码减重数据。
- 完成一轮组件化后，考虑引入 Storybook/VitePress 展示组件，方便培训和设计对齐。

通过延续 FilterCard 的模式，把模板与脚本拆到 `components/ui/` 与 `modules/ui/`，可以持续削减前端重复代码，让每个页面只负责 glue 逻辑与配置。*** End Patch
