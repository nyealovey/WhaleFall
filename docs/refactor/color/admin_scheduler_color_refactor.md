# 定时任务管理页面色彩与交互重构方案

## 背景
- 现有定时任务管理页（`app/templates/admin/scheduler/index.html` + `app/static/js/modules/views/admin/scheduler/index.js` + `app/static/css/pages/admin/scheduler.css`）沿用历史配色：页头/批量按钮混用 `btn-light/btn-danger/btn-info`，统计卡使用 `bg-primary/bg-warning`，任务列表中 `badge bg-*` 与 HEX 色值并存。
- 任务状态、任务类型、计划表达等使用不同色块提示，单屏语义色 > 8，违背《界面色彩与视觉疲劳控制指南》的“2-3-4 规则”以及账户分类落地经验。
- 模态 & 提示信息仍依赖纯红背景提醒失败，缺少统一的 `status-pill`/`chip-outline` 组件，导致色彩复用差、维护成本高。

## 改造目标
1. 页头与批量操作遵循“单主色 CTA + 中性色描边”节奏：`新建任务` 保留主色，其余操作（刷新/导出/批量暂停）全部用描边按钮，危险操作仅加 `text-danger` 图标。
2. 统计卡与总览模块完全使用白底 + 阴影，差异通过 `status-pill` 标注；单屏统计卡颜色 ≤ 2，遵循 color-guidelines 的 stats card 规范。
3. 任务列表列宽与组件一次性对齐：状态列 70px、cron/模块 chip 列 ≥ 220px、执行计划 160px、操作列 90px；任务状态、执行结果、下一次运行时间全部换成 `status-pill`/`chip-outline`。
4. 模态窗口及 toast 提示统一使用 `status-pill--danger`、`alert` 等组件；不再出现自定义红/黄背景。筛选器若存在，栅格需满足 `col-md-2 col-12` 要求。
5. 开发完成前必须运行 `./scripts/refactor_naming.sh --dry-run` 与 `make test`，并在 PR 说明中列出“首屏颜色计数 ≤7”与“命名脚本通过”截图。

## 设计策略
### 1. 导航与操作区
- 页头按钮组：`新建任务` 使用 `btn-primary`；`立即刷新`、`导出日志`、`批量暂停` 改为 `btn-outline-secondary`，危险度信息通过 icon (`fa-exclamation-triangle text-danger`) 或 tooltip 体现。
- Toolbar 中的筛选器/搜索框采用默认灰底输入框；选中项使用 `ledger-chip` 显示关键词，删除操作使用 `btn-icon`。

### 2. 统计卡
- 统计卡容器采用 `partition-stat-card` 同款样式：白底、`var(--gray-200)` 边框、`--shadow-sm` 阴影。
- 指标（运行中任务、失败任务、暂停任务、平均延迟）采用 `status-pill` 表示趋势，不再单独定义 `bg-success/bg-danger`。
- 数值字体 2rem/600，次级描述 0.85rem；差异信息如“较昨日 +5%”使用 `status-pill--success|--danger|--muted`。

### 3. 任务列表 Grid
- `buildColumns` 设置标准宽度：
  - `name` 列展示任务名称 + 描述，使用纯文本；
  - `module`/`task_type` 列使用 `chip-outline`（品牌描边或 `chip-outline--muted`）；
  - `status`/`last_result` 列使用 `status-pill`（`success|warning|danger|muted`）；
  - `schedule`（cron 表达式）使用单色 `chip-outline` 并提供 tooltip；
  - `next_run_at` 列宽 160px，使用 `status-pill--muted` 加图标。
- 操作列按钮统一 `btn-outline-secondary btn-icon`（查看/立即执行/暂停等），危险操作只在 tooltip 中提示，不换背景色。

### 4. 模态与提醒
- 所有模态头部/底部保持白底 + 中性色描边，主体文本遵循“标题 16px/600 + 正文 14px/400”。
- 提醒信息（例如“立即执行会占用 worker”）使用 `status-pill--warning` 或 `alert alert-warning`，禁止 `bg-warning`。
- 确认弹窗保留主色确认按钮 + 描边取消按钮；危险操作在按钮文本中附 “（危险操作）”。

### 5. CSS 与资源治理
- `app/static/css/pages/admin/scheduler.css` 中删除所有 `bg-*`、HEX/RGB 色值，改为引用 `variables.css` token。
- 引入 `ledger-chip`、`chip-outline`、`status-pill` 的公共样式或在页面内定义同名 class 引入变量。
- 行背景采用 color-guidelines 建议：偶数行 `color-mix(in srgb, var(--surface-muted) 10%, transparent)`，hover 20%。

## 实施步骤
1. **模板调整**：
   - 更新页头按钮、统计卡结构、筛选卡栅格；
   - 列表模板（若使用 gridjs）中为每列添加 `data-column-id`，便于 JS 渲染。
2. **JS 重构**：
   - 在 `admin/scheduler/index.js` 中新增 `renderStatusPill`、`renderChip` 辅助；
   - 重新定义列宽与 formatter，确保 `status-pill`、`chip-outline` 使用统一文案；
   - 操作按钮点击后，只用 toast 表示成功/失败，不切换按钮颜色。
3. **CSS 清理**：
   - 引入公共组件样式，删除 `badge` 和硬编码背景；
   - 为统计卡、列表 hover、btn-icon 等场景添加 token 化样式。
4. **自检**：
   - 手动盘点首屏色彩（目标 ≤7）；
   - 运行 `./scripts/refactor_naming.sh --dry-run`、`make test`；
   - 若涉及命名规范调整，在 PR 中贴出脚本“无需要替换的内容”截图。
5. **推广与回归**：
   - 将本方案链接到 `docs/standards/color-guidelines.md` 的案例章节；
   - 其他 Admin 模块（如 Scheduler 子页面）沿用本策略，减少色彩回归成本。

## 风险与缓解
- **任务状态辨识度下降**：通过 `status-pill` 文案 + icon（✔、⚠、✖）补足语义；若需额外区分，在 tooltip 中注明失败原因。
- **批量操作误触**：描边按钮 + tooltip 提醒“将暂停所有任务”；危险操作仍在确认模态中强调。
- **图标/颜色缺失**：若公共 CSS 未引入，需要在 `admin/scheduler.css` 顶部 `@import` 对应组件样式，或在模板中引用 `accounts` 模块使用的组件文件。

## 验证清单
- ✅ 首屏颜色 ≤ 7、语义色 ≤ 4（按指南统计）；
- ✅ `status-pill` / `chip-outline` / `ledger-chip` 复用率 100%，无 `badge bg-*`；
- ✅ 统计卡仅使用白底/浅灰两种背景；
- ✅ `./scripts/refactor_naming.sh --dry-run` 与 `make test` 通过；
- ✅ PR 描述列出“色彩治理”步骤、截图，并在 `docs/standards/color-guidelines.md` “案例”段添加定时任务条目。
