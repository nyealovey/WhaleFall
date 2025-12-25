# 界面色彩与视觉疲劳控制

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-02  
> 更新：2025-12-25  
> 范围：所有管理页面（表格、卡片、详情弹窗、筛选区、标签/状态展示）

## 目的

- 控制单屏色彩数量与饱和度，降低“信息噪声”造成的视觉疲劳。
- 强化语义映射：同一语义状态绑定固定 token/组件，避免页面自定义样式。
- 通过组件化（pill/chip）承载色彩，而不是靠页面随意上色。

## 适用范围

- 全站 CSS：`app/static/css/**`
- Token 定义：`app/static/css/variables.css`
- 组件样式：`app/static/css/components/**`
- 模板与页面：`app/templates/**`

## 规则（MUST/SHOULD/MAY）

### 1) Token 与颜色来源

- MUST：色彩统一由 `app/static/css/variables.css` 或既有 Token 输出，禁止在 CSS/HTML/JS 中硬编码 HEX/RGB/RGBA。
- MUST：新增颜色必须先在 `variables.css` 定义 Token，并在评审中说明“原因 + 退场机制”。
- SHOULD：优先通过组件 class（`status-pill`、`chip-outline`、`ledger-chip` 等）承载色彩，而不是页面级别自定义。

### 2) 色彩 2-3-4 规则（默认基线）

- SHOULD：主色 ≤2（品牌主色 + 一种中性色）。
- SHOULD：辅助色 ≤3（用于导航/次级按钮/图表，不得另行定义新 Token）。
- SHOULD：语义色 ≤4（固定使用 `--success-color`、`--warning-color`、`--danger-color`、`--info-color`，禁止装饰性滥用）。

### 3) 组件级约束

- MUST：状态类信息使用 `status-pill`（变体 `success|info|warning|danger|muted`），禁止叠加高饱和 `badge bg-*` 作为状态载体。
- MUST：类型/分类/轻量标签使用 `chip-outline` 体系，避免页面自建“彩色标签块”。
- SHOULD：多标签或上下文元数据使用 `ledger-chip-stack`（展示全部，超出用 `+N`），避免一屏出现大量彩色块。

### 4) 按钮与危险语义

- MUST：触发层面的危险操作按钮优先使用 `btn-outline-danger` 或危险图标按钮（详见 [按钮层级与状态](./button-hierarchy-guidelines.md)）。
- MUST：危险操作的“最终确认”按钮使用 `btn-danger`（详见 [高风险操作二次确认](./danger-operation-confirmation-guidelines.md)）。

### 5) 筛选区（FilterCard）约束

- MUST：所有 `filter_card` 渲染的搜索/下拉控件必须采用 `col-md-2 col-12` 栅格，禁止写死像素宽度；如需突破必须在评审中说明。

## 正反例

### 正例：用组件承载语义色

- 状态：`status-pill status-pill--success`
- 标签：`chip-outline chip-outline--muted`

### 反例：页面硬编码颜色

- 在模板/CSS 里直接写 `#ff5a00`、`rgb(255, 90, 0)` 等。

## 案例（改造记录入口）

色彩治理的具体改造记录按页面归档在：[改造记录目录](../../changes/refactor/color/)。

## 门禁/检查方式

- Token 未定义门禁：`./scripts/ci/css-token-guard.sh`
- 组件样式漂移门禁（按需）：`./scripts/ci/component-style-drift-guard.sh`
- 人工评审检查：
  - 是否出现硬编码颜色（HEX/RGB/RGBA）？
  - 是否新增了不在组件体系内的“彩色标签/徽章”？
  - 是否在单屏引入过多语义色？

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为标准结构，修正与仓库约束不一致的筛选栅格规则，补齐案例入口与门禁说明。
