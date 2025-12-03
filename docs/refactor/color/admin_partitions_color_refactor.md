# 分区管理页面色彩与栅格重构方案

## 背景
- 现有分区管理视图（`app/templates/admin/partitions/index.html` + `app/static/js/modules/views/admin/partitions/index.js` + `app/static/css/pages/admin/partitions.css`）延续历史配色：统计卡使用 `bg-primary/bg-warning`，操作按钮混用 `btn-danger/btn-light`，表格列中还有 `badge bg-*` 与自定义 HEX，导致首屏语义色 > 8，严重偏离《界面色彩与视觉疲劳控制指南》。
- 批量操作、清理分区等高风险动作仍依赖背景色提示，未统一到 `status-pill`、`ledger-chip` 组件；筛选卡也未按 `col-md-2 col-12` 栅格对齐，影响复用。
- 本方案参考账户台账重构成果，目标是让分区管理成为“色彩治理”基线页面之一。

## 改造目标
1. 页面所有颜色均引用 `app/static/css/variables.css` 或 `ColorTokens`，确保单视区色彩遵守 2-3-4 规则，禁止新增 HEX/RGB。
2. 页头 CTA、统计卡、筛选卡统一“单主色 CTA + 中性色描边”节奏：`创建分区` 为唯一实心主色，其余按钮改为描边或图标辅助。
3. 列表列宽与组件一次性收敛：状态列 70px，表空间/数据库列 220px，可用容量/阈值列 160px，操作列 90px；状态/标签均使用 `status-pill`、`ledger-chip-stack`。
4. 模态、批量操作与警示信息仅通过 `status-pill--danger` / icon + 文案提示，不再出现满屏红底；`filter_card` 输入列全部遵循 `col-md-2 col-12`，多列需求通过 utility class（必须写入 PR 说明）。
5. 交付前运行 `./scripts/refactor_naming.sh --dry-run` 与 `make test`，并在 PR checklist 勾选“命名规范已自检”。

## 设计策略
### 1. 导航与筛选区
- 顶部按钮组：
  - `创建分区` 使用 `btn-primary`（品牌主色）。
  - `清理旧分区`、`批量刷新元数据` 改为 `btn-outline-secondary`，危险性通过 `text-danger` icon + tooltip 体现。
- 筛选卡：所有输入列采用 `col-md-2 col-12`；多选标签展示 `ledger-chip`，状态筛选使用 `status-pill--muted` 风格；筛选结果提示条使用文字 + `status-pill--muted`。

### 2. 统计卡
- 背景 `var(--surface-default)`，描边 `var(--border-subtle)`，阴影统一 `var(--shadow-card)`；
- 数值主体 `font-weight: 600`，趋势对比通过 `status-pill--success|--danger|--muted` 表达。
- 统计卡内若需强调容量上限，使用灰度条 `meter` + `var(--accent-primary)`，避免额外颜色。

### 3. 列表 Grid 与组件
- `buildColumns` 设置固定宽度（状态 70px、表空间/数据库 220px、可用容量 160px、操作 90px），其他列弹性。
- `renderPartitionTags` 切换为 `ledger-chip-stack`，超过 3 项显示 `+N`。
- `renderPartitionStatus` 使用 `status-pill`（“已创建/缺失/清理中/禁用”），颜色通过 `status-pill--success|--warning|--muted|--danger`。
- 容量阈值列使用文案 + `status-pill--danger`（当 >80%）或 `status-pill--muted`（正常），取消红/绿背景条。
- 操作列按钮统一 `btn-icon btn-outline-secondary`，执行成功后通过 toast 告知，禁止绿色“成功”按钮。

### 4. 模态与警示
- 模态 header、footer 均使用白底 + 中性色描边；
- 警示信息（例如“强制清理会删除历史任务”）以 `status-pill--danger` + `alert` 组件描述，禁止整块红底；
- 表单按钮仅保留主色 CTA + 描边取消键，危险动作在 icon/文案中提示。

### 5. CSS 与资源策略
- `admin/partitions.css` 删除所有硬编码色值/老 `.badge-*` 定义，引入 `ledger-chip`、`chip-outline`、`status-pill` 公共样式（与账户台账保持同源）。
- 使用 CSS 自定义属性控制列宽与间距，例如 `--partition-status-width: 70px`，便于其它页面复用。
- 行 hover 背景沿用账户台账：`color-mix(in srgb, var(--surface-muted) 10%, transparent)`；交替行 5%。

## 实施步骤
1. **样式治理**：清理 `admin/partitions.css` 中的 `badge`、HEX 色值，导入公共 chip/pill 组件；新增必要 token 时先在 `variables.css` 声明。
2. **模板/JS 改造**：
   - 页头按钮、筛选卡栅格、统计卡结构按设计策略重写；
   - JS 中 `buildColumns`、`renderPartitionStatus`、`renderPartitionTags`、容量阈值渲染全部切换为统一组件；
   - 批量操作提示改用 icon + 描边按钮。
3. **交互增强**：替换 `alert-danger` 弹窗为 `status-pill--danger` + toast；操作成功仅用 toast/文案提示。
4. **验证**：在桌面端（≥1440px）检查首屏颜色 ≤7、栅格对齐；运行 `./scripts/refactor_naming.sh --dry-run`、`make test`；视需要执行 `pytest -k admin_partitions`。
5. **文档与推广**：将改造记录同步到 `docs/standards/color-guidelines.md` 的案例章节，供其它 admin 页面复用。

## 验证指标
- 色彩计数：浏览器截图通过插件统计语义色 ≤4；
- 交互回归：批量清理/刷新、创建、筛选流程全部通过；
- 自动化：`make test` + 针对性 pytest；
- 命名守卫：`./scripts/refactor_naming.sh --dry-run` 输出“无需要替换的内容”。

## 风险与缓解
- **危险操作辨识度下降**：在按钮 icon 和确认模态文案中明确“危险操作”，并使用 `status-pill--danger`；必要时增加确认步骤。
- **组件依赖缺失**：若 `ledger-chip`、`status-pill` 尚未在 admin 模块加载，需在 CSS 入口显式引入；同时在构建脚本中确认打包顺序。
- **筛选卡栅格破坏布局**：如需更大列宽，通过 utility class `u-col-span-2` 处理并在 PR 中注明原因。

## 推广建议
- 以本页面为 admin 系统标准模板，后续 `admin/quotas`、`admin/tasks` 等页面直接复用配色与列宽策略。
- 若新增语义色或组件，先更新 `docs/standards/color-guidelines.md` 并获得 UI 审核，再在具体页面启用。
