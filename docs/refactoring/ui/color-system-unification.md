# 色彩体系统一（去渐变化）重构方案

## 背景
- 2025-11-27 前端已完成“布局壳 + page_header”重构（参考 `page-layout-alignment.md`），筛选卡、表格、导航全部接入 `.layout-shell` 与 `page-section`，并统一了筛选列宽（`col-md-2 col-12`）。
- 当前主题仍沿用 Flatly 的绿蓝渐变（`body { background: linear-gradient(...) }`），但卡片、筛选等容器已经具备统一结构，具备整体替换色彩体系的前置条件。
- 产品希望页面在对齐布局后继续去除多套主题色，采用单色分层 + 单一主色（参考 ui.shadcn）以便维护；因此需要更新本文档指导后续色彩统一工作，并标记已完成与待做事项，便于追踪。

## 当前状态（2025-11-27）
1. **布局落地**：`base.html`、`app/static/css/global.css` 已添加 `.layout-shell`、`page-section`、`page-header__*` 样式；导航 Logo 与主菜单通过 `.navbar-container` 同行展示。
2. **组件规范**：`components/filters/macros.html` 默认 `col-md-2 col-12`，所有筛选卡页面（实例/账户/凭据等）均使用 `page_header` 宏；`docs/refactoring/ui/page-layout-alignment.md` 已同步规范。
3. **色彩仍待统一**：全局背景/卡片仍依赖 Flatly 渐变与多套颜色变量，`theme-orange.css` 尚未创建，`variables.css` 中也未引入 `--surface-*`/`--accent-*` 系列变量。下一阶段需按下文方案推进色彩重构。

## 改造目标
1. 全局背景、卡片、筛选组件等容器仅使用单色（`--surface-base`/`--surface-elevated`），彻底移除渐变背景（保留图表局部渐变即可）。
2. 只保留一套主色（橙色，OKLCH `oklch(0.646 0.222 41.116)`）及标准状态色集，通过 CSS 变量输出，按钮、链接、Tag、高亮统一调色。
3. 提供“Flatly → Shadcn”覆盖方案：在不改 HTML/JS 的前提下，通过新增 CSS 文件快速获得 Inter 字体 + 橙色主色 + 紧凑 focus ring，并在 `base.html` 中配置加载顺序。
4. 确保 UI 取色器检查背景/卡片/按钮时仅检测到单色，梯度仅允许出现在图表、数据条等视觉化组件。

## 设计与实施方案

### 1. 单色化背景与层级
- 在 `app/static/css/variables.css` 中定义：`--surface-base`, `--surface-elevated`, `--surface-muted`, `--text-primary`, `--text-muted` 等变量，所有页面共用一套暗色值。
- 将 `global.css`、页面级 CSS 中的 `background: linear-gradient(...)` 改为 `background-color: var(--surface-*)`；`filter-card`、`.card`、`.main-content` 等容器全部引用变量，形成“同色系不同明度”的层级感。
- 若某些可视化模块确需渐变（例如图表 series），限制在 `.chart-*` 或特定组件内实现，禁止在结构容器上使用。

### 2. 主色/状态色策略
- 在变量文件中声明：`--accent-primary`（橙色）、`--accent-primary-rgb`、`--accent-primary-hover`、`--focus-ring` 等，按钮、链接、Tag、高亮复制这些值。
- 成功/警告/危险类颜色维持单色平面（OKLCH 或 HEX），不再叠加渐变或多重阴影；同时确保 `contrast ratio` >= 4.5，满足可读性。
- `form-control`, `.form-select` 的 focus 状态统一引用 `--focus-ring`（橙色透明度 0.25），实现一致的强调效果。

### 3. Flatly → Shadcn 覆盖方案
> 仅通过 CSS override 即可把 Flatly 默认绿蓝色换成橙色 + Inter 字体。

1. **引入 Inter 字体**（`base.html` `<head>`）：
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
   ```
2. **新增 `static/css/theme-orange.css`**，在 Flatly 之后引入：
   ```css
   :root {
       --shadcn-orange: #f97316;
       --shadcn-orange-rgb: 249, 115, 22;
       --bs-primary: var(--shadcn-orange);
       --bs-primary-rgb: var(--shadcn-orange-rgb);
       --bs-body-font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
       --bs-border-radius: 0.5rem;
       --bs-border-radius-lg: 0.75rem;
       --bs-border-radius-sm: 0.3rem;
   }

   body {
       font-family: var(--bs-body-font-family);
       font-weight: 400;
       color: #0f172a;
   }

   .btn-primary {
       background-color: var(--shadcn-orange) !important;
       border-color: var(--shadcn-orange) !important;
       font-weight: 500;
   }
   .btn-primary:hover,
   .btn-primary:focus {
       background-color: #ea580c !important;
       border-color: #ea580c !important;
   }

   .form-control:focus,
   .form-select:focus {
       border-color: var(--shadcn-orange) !important;
       box-shadow: 0 0 0 0.25rem rgba(249, 115, 22, 0.25) !important;
   }

   a { color: #ea580c; }
   a:hover { color: #c2410c; text-decoration: underline; }

   .card,
   .list-group-item,
   .form-control {
       border-color: #e2e8f0;
   }
   .badge.bg-primary { background-color: var(--shadcn-orange) !important; }
   .page-link { color: #ea580c; }
   .page-item.active .page-link {
       background-color: var(--shadcn-orange);
       border-color: var(--shadcn-orange);
   }
   ```
3. **`base.html` 引入顺序**：
   ```html
   <link href="{{ url_for('static', filename='vendor/bootstrap/bootstrap-flatly.min.css') }}" rel="stylesheet">
   <link href="{{ url_for('static', filename='css/theme-orange.css') }}" rel="stylesheet">
   ```
4. **微调建议**：卡片添加 `shadow-sm border-0`，使用 `<small class="text-muted">` 显示辅助说明；需要更细部件（Navbar、Modal 等）可继续在 `theme-orange.css` 追加选择器。

### 4. 实施步骤
1. 在 `variables.css` 中添加暗色变量与主色定义，同时删除遗留的多套主题配置。
2. 扫描 `global.css` 及 `app/static/css/pages/**`，统一替换背景/按钮/状态相关渐变，确保都引用新变量。
3. 创建 `theme-orange.css` 并在 `base.html` 中注册；逐步验证按钮、表单、链接的 hover/focus 视觉是否符合预期。
4. 与布局重构联动：在完成 `page-layout-alignment` 的页面上优先切换色彩方案，确认卡片、筛选区、表格边界一致。

## 验收标准
1. Chrome DevTools 取色器在页面背景、卡片、主要按钮上仅检测到单色值，无 `linear-gradient`。
2. 所有 `.btn-primary`、链接、徽章统一使用橙色主色，Hover/Focus 值与 `theme-orange.css` 定义一致。
3. `make quality`、`./scripts/refactor_naming.sh --dry-run` 均通过；设计验收在 1280px、1440px 视口下截图确认色彩统一。

## 关联文档
- 布局方案详见 `page-layout-alignment.md`，建议先完成布局壳与 page header 重构，再切换色彩方案减少视觉回归。
