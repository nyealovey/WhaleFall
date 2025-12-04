# 批量创建实例模态框重构方案

## 背景
- “批量创建实例”模态沿用 2023 年旧稿，存在高饱和警示色、表单栅格不统一、状态提示与日志弹窗不一致等问题，已偏离《界面色彩与视觉疲劳控制指南》所定义的 Dashboard 基线。
- 近期多次在测试和运营场景中反映：模态高度过长，选项卡层级与进度提示位置混乱，导致用户在大量复制实例参数时易产生误操作。
- 本文档用于指导设计与前端同步重构，明确配色、布局、交互和验收清单，避免再次出现“多主色 CTA”“badge bg-*”等历史问题。

## 现状问题
1. **色彩违例**：同一模态内存在 `btn-warning`, `badge bg-success`, `text-danger` 等超过 8 种色块，违背“色彩 2-3-4 规则”。
2. **组件不统一**：选中实例、任务进度使用自定义样式，未复用 `chip-outline`、`status-pill`、`ledger-chip-stack`，造成视觉割裂。
3. **栅格失衡**：表单行混用 `col-md-4/6/12`，某些必填项在 1440px 屏幕仍换行；同时 CTA 区域堆叠两个 `btn-primary`。
4. **状态提示不清**：导入 CSV、检测模板、创建任务各自使用不同的 tooltip 与消息位置，用户无法快速定位错误字段。
5. **信息过载**：示例参数、实例列表、校验日志全部同时展开，导致模态主体高度>900px，需要频繁滚动。

## 重构目标
1. **视觉统一**：所有状态/分类/数量信息仅使用 `status-pill` 与 `chip-outline`，按钮遵循“单主色 CTA”策略。
2. **结构清晰**：模态拆分成“导入与预览”“参数补全”“执行确认”三个折叠面板，默认只展开当前步骤。
3. **高效输入**：表单字段统一 `col-md-4 col-12` 栅格，并提供批量粘贴/自动补全提示。
4. **无冗余状态**：只展示符合条件的实例（已禁用或校验失败的移至“异常摘要”折叠区）。
5. **可回归**：提供明确的验收 checklist，确保与 color-guidelines.md 一致。

## 设计方案

### 1. 视觉基线
- **色彩**：
  - 主色：`--accent-primary`（顶栏、唯一 CTA）。
  - 辅助：`--surface-muted`、`--sidebar-accent`，总数 ≤3。
  - 语义：`--success-color` / `--warning-color` / `--danger-color` / `--info-color`，仅在状态 pill 中使用。
- **组件**：
  - 状态 pill 5 种变体（成功/警告/危险/信息/禁用）。
  - `chip-outline--muted` 用于标签/批次号；`chip-outline--brand` 用于“当前模板”。
  - `ledger-chip-stack` 展示待创建的实例标签。

### 2. 结构与布局
| 区域 | 组件 | 说明 |
| --- | --- | --- |
| 导入与预览 | 上方 tabs + 上传区 + CSV 预览 | Tabs 使用 `chip-outline` 样式；文件状态通过 `status-pill`. 预览表格 ≤ 6 行，超出滚动 |
| 参数补全 | 表单栅格 + Bulk Assist_banner | 每行 `col-md-4 col-12`，通过 `form-floating` + 12px 辅助文案；Bulk Assist 信息使用 `chip-outline` 告知自动填充策略 |
| 执行确认 | 任务摘要 + 风险告警 | 摘要字段（数据库类型、批次数、预计耗时）以 `chip-outline` 展示；风险告警使用 `status-pill--warning` 置顶 |

### 3. 交互流
1. **上传**：拖拽/点击上传 CSV → 成功后自动进入预览；失败则在上传框下方显示 `status-pill--danger` + 错误文案，并提供重新上传按钮（`btn-outline-secondary`）。
2. **字段映射**：预览表格第一行展示列头映射状态，若缺失必填列，直接在列头右侧给出 `chip-outline--brand` 提示并阻断下一步。
3. **批量补全**：用户可在“参数补全”区域一次性输入默认密码、端口；每个字段右侧提供 `ledger-chip` 显示已覆盖多少实例（例：`覆盖 12 个实例`）。
4. **确认执行**：点击“立即创建”后，显示 Loading 状态（`btn-primary` disabled + spinner）；成功后提示 `status-pill--success` 并关闭模态；失败时保留模态并展开“异常摘要”。

### 4. 状态与空态
- **空上传**：显示插画 + “尚未选择 CSV”，按钮为 `btn-outline-secondary`。
- **无实例可创建**：在预览区域展示 `ledger-chip` 列表说明被过滤原因，并隐藏 CTA。
- **异常摘要**：折叠面板内以表格列出失败行（序号、原因、字段）；每行使用 `status-pill--danger`。允许导出日志。

### 5. 开发与实现要点
1. **模板结构**：将现有 `app/templates/instances/modals/batch-create.html` 拆分为基础模板 + macro，保持可复用性。
2. **CSS**：新增 `app/static/css/pages/instances/batch-create-modal.css`，仅引用已存在 token，不得写死颜色。
3. **JS Store**：扩展 `app/static/js/modules/stores/instances_store.js`（若已有）以管理批量创建状态；异步校验用 `async/await`，并统一错误处理。
4. **可访问性**：Modal 内部使用 `aria-live=polite` 通知上传/校验结果；折叠面板按钮具备 `aria-expanded`。
5. **命名校验**：改动完成后运行 `./scripts/refactor_naming.sh --dry-run`，确保未产生 `_api` 等违规命名。

## 验收清单
1. 色彩数量符合 2-3-4 规则，无 `badge bg-*`、无硬编码 HEX。
2. 模态在 1280px 与 1440px 分辨率下高度 < 720px（默认展开单个面板）。
3. 状态提示全部为 `status-pill`，按钮遵循“单主色 CTA”策略。
4. 表单行统一 `col-md-4 col-12`，栅格对齐，不再出现 2 列 3 列混排。
5. 预览表格 hover 与 Dashboard 列表一致（颜色、交替行）。
6. QA 按照本文“交互流”走查四个关键路径：上传成功、上传失败、字段缺失、执行失败。
7. 文档、设计、实现三方确认通过后，在 PR 描述中附本文件链接并记录自测命令。

> 本方案若需变更，请同步更新本文，并在 PR 中说明原因与退场计划。
