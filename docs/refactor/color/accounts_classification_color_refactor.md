# 账户分类管理页面色彩与交互重构方案

## 背景
- 分类管理页面（`app/templates/accounts/account-classification/index.html` + `app/static/js/modules/views/accounts/account-classification/index.js` + `app/static/css/pages/accounts/account-classification.css`）仍保留 `badge bg-*`、`text-success/danger` 等直接色值，当前首屏语义色 > 7，违背《界面色彩与视觉疲劳控制指南》以及账户台账试点成果。
- 统计卡、批量操作、模态按钮并存 `btn-primary/secondary/success/danger` 多色方案，且仍在 CSS 中硬编码 HEX/RGB，无法复用 `app/static/css/variables.css` 内的色彩 token。

## 重构目标
1. 页头、统计卡与工具栏统一“单主色 CTA + 中性色描边”节奏，禁止新增硬编码颜色，全部引用变量或 `ColorTokens`。
2. 列表列宽与组件与账户实例页保持一致：状态列 90px，标签列 ≥ 220px，操作列 90px；标签、状态、规则 Result 全面改为 `ledger-chip`、`ledger-chip-stack`、`status-pill` 等通用组件。
3. 所有模态、表单、批量操作仅使用主色和描边按钮；危险度提示通过 icon 或 `status-pill--danger`，不再依赖背景色块。
4. 自检阶段确保 `filter_card` 栏位遵循 `col-md-2 col-12` 栅格组合，并运行 `./scripts/refactor_naming.sh --dry-run` + `make test` 作为提交前检查。

## 设计策略
### 1. 页头与统计卡
- 页头按钮对齐账户台账：`新增分类` 使用主色 `btn-primary`，`导出`、`批量发布` 等改为 `btn-outline-secondary`；危险操作在 icon 上添加 `text-danger` 而非彩底。
- `stats_card` 背景设置为 `var(--surface-default)`，边框使用 `var(--border-subtle)`，数值采用 `var(--text-strong)`，并通过 `ledger-chip` 展示分类状态摘要。
- 统计 KPI 中若需强调环比，使用 `status-pill--muted` + 箭头图标替代红绿背景。

### 2. 列表 Grid
- `buildColumns` 中设置固定宽度：`status` 90px、`tags` 240px、`auto_rule` 220px、`actions` 90px，余下列弹性。
- `renderClassificationTags` 替换为 `renderChipStack`：标签 chip 走 `ledger-chip`, 超出以 `+N` 形式呈现；JS 中避免拼接 `badge` 类。
- `renderAutoRuleStatus` 与 `renderEnabled` 均使用 `status-pill`（文案“已启用/未启用”），状态颜色通过 `status-pill--success|--muted` 控制。
- 操作列按钮一律使用 `btn-icon btn-outline-secondary`，成功/失败反馈走 toast 或 `status-pill`，不再显示绿色按钮。

### 3. 模态与表单
- 模态 header/footer 背景保持白底，仅在标题左侧添加 `status-pill--muted`，说明当前分类状态。
- 表单控件与标签选择器使用灰底输入框，已选项复用 `ledger-chip`；筛选区所有输入列统一 `col-md-2 col-12`；若需要更宽（如标签多选）则通过 utility class（例：`u-col-span-2`）覆盖，并在 PR 中解释。
- 复杂操作（批量发布/撤销）在模态内显示 `status-pill--danger` 警示，不新增红色按钮。

### 4. CSS 与资源
- 删除 `account-classification.css` 中所有 HEX/RGB，改为引用 `var(--primary-500)` 等 token；若缺少 token，先在 `variables.css` 补充命名再使用。
- 引入 `ledger-chip`, `status-pill`, `chip-outline` 公共样式，可通过 `@use "../components/chip" as *` 或直接 `@import` 现有文件，确保命名空间不冲突。
- 清理 `.badge-*`、`.tag-success` 等遗留类，避免被模板引用。

## 实施步骤
1. **样式抽取**：在 `account-classification.css` 中移除硬编码颜色，引用公共 chip/pill 样式，若组件尚未暴露变量则补充 token 后引入；同时删除多余 `.badge`。
2. **JS 渲染调整**：重写 `buildColumns`、`renderClassificationTags`、`renderAutoRuleStatus`、操作列按钮，统一使用 `ledger-chip-stack`、`status-pill`、`btn-icon`。
3. **模板更新**：
   - 页头/统计卡替换按钮与 KPI 展示；
   - `filter_card` 输入列设置统一栅格；
   - 模态 footer 仅保留主色 + 描边按钮。
4. **行为核对**：根据危险度设置 icon/tooltip，保证无彩色背景误导；批量操作提示使用 toast。
5. **回归验证**：运行 `./scripts/refactor_naming.sh --dry-run`、`make test`；手动检查浏览器首屏语义色 ≤ 7，确保筛选列宽一致。

## 风险与缓解
- **辨识度下降**：为危险操作增加 icon + tooltip，并在确认流程使用 `status-pill--danger`；必要时在文案中加入“（危险操作）”。
- **组件依赖缺失**：若 chip/pill 公共样式尚未在账户模块加载，需要在 `account-classification.css` 顶部显式导入，避免因打包顺序导致样式缺失。
- **筛选栅格破坏布局**：新增 utility class 时必须在文档记录原因，并在自测中确认 1440px 分辨率下列宽一致。

## 验证与交付
- ✅ 浏览器检查：首屏颜色不超过 3 类语义色，筛选卡列宽统一。
- ✅ 交互自测：批量发布/撤销、导出、标签过滤、模态提交流程。
- ✅ 自动化：`./scripts/refactor_naming.sh --dry-run`、`make test`（必要时 `pytest -k account_classification`）。
- ✅ 文档：将结果链接同步到 `docs/standards/color-guidelines.md` “案例”章节，供后续 CRUD 页面参考。
