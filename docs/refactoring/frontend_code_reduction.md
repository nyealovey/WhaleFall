# 前端代码减重方案

> 目标：在现有分层（services/stores/views）的基础上，持续削减重复代码与全局脚本，构建可组合、易维护的 UI 层。核心理念是“用结构化资产取代脚本堆叠”，必要时引入 UI 组件库或表单引擎。

## 1. 现状诊断

| 发现 | 说明 | 影响 |
| --- | --- | --- |
| 全局脚本过多 | `app/templates/base.html:220-254` 对所有页面注入 20+ JS（权限 viewer、连接管理、过滤器、表单校验等），即便页面用不到也会加载。 | 加载成本大、命名污染、难以 tree-shake。 |
| 表单逻辑重复 | 虽然 `ResourceFormController` 已统一提交体验，但 `FormValidator` / `ValidationRules` 仍需在 10+ 视图里重复 `addField`、自定义规则（参见 `modules/views/instances/form.js`, `credentials/form.js`, `tags/form.js`, `auth/login.js` 等）。 | 校验逻辑散落，难以批量调整。 |
| 视图粒度不够 | `modules/views/accounts/account-classification/index.js`、`instances/detail.js` 等仍包含上百行 DOM 交互，缺少可复用的子组件（如表单段落、表格控件）。 | 同类 UI 无法重用，代码量持续增长。 |
| CSS/模板重复 | 多个页面重复定义卡片、按钮、筛选条样式；同一模态在模板中 copy（例如权限模态、标签模态）。 | 样式维护成本高，难以统一主题。 |
| 构建链路缺失 | 目前仍以“静态文件 + `base.html` 注入”为主，未引入模块化打包器，无法 tree-shake 未用模块，也难以按需分发。 | 代码无法自动减重，需人工控制加载边界。 |

## 2. 减重原则
1. **组件化优先**：任何复用概率 >1 的 UI 区块都抽成组件（JS + 模板 + 样式），禁止在模板中复制 DOM 用片段。
2. **按需加载**：默认不在 `base.html` 注入业务脚本，统一改为页面 `extra_js`/`extra_css` 按需引入；全局只保留 `DOMHelpers`、`httpU` 等基础设施。
3. **数据驱动**：表单/列表/统计视图以 schema 或配置驱动渲染（参照 `ResourceFormController` 与字段定义），用配置代替重复脚本。
4. **工具链助力**：引入 UI 组件库或设计系统（可选），并结合构建工具（Vite/ESBuild）自动做 tree-shaking、代码拆包。

## 3. 组件化 UI 模块方案

> 聚焦“用 UI 模块减少代码量”：先建统一的 UI 组件层，再通过构建工具/按需加载削减全局脚本。其它减重手段（表单 schema、构建链路等）都围绕 UI 模块展开。

### 3.1 组件库选型与策略
1. **兼容现有 Bootstrap**：短期优先选择与 Bootstrap 5 原子样式兼容的组件库（Bootstrap 官方组件或 Flowbite）。若未来要更灵活，可接入 UnoCSS/Tailwind，但需评估学习成本。
2. **自研核心组件**：账户分类、标签、容量统计等有高度定制需求，可在 `app/static/js/modules/ui/` 下维护自研组件（Modal、Drawer、Notification、DataGrid、Stepper 等），通过 props/config 驱动。
3. **Design Tokens**：在 `css/variables.css` 增加颜色、间距、字号 tokens，让 UI 组件遵循同一套设计语言，后续换肤只改 tokens。

### 3.2 模块目录与接口
```
app/static/js/modules/ui/
├── modal/
│   ├── modal.js          # 逻辑（open/close/async 等）
│   └── modal.template.js # 模板或渲染函数
├── form/
│   ├── field.js          # 渲染单个输入控件
│   └── form-layout.js    # 步骤/双栏等布局
├── table/data-table.js
├── feedback/toast.js
└── index.js              # 统一导出
```
- 每个组件暴露 `createX(props)` 或 `useX()`，内部依赖 `DOMHelpers`、`mitt` 等现有基建。
- 模板部分可用字符串模板、`<template>` 或轻量虚拟 DOM。关键是“由组件接管 DOM”，页面只写配置。

### 3.3 渐进式落地
1. **锁定高收益模块（Top 10）**  
   | 模块 | 视图文件 | 行数 (approx.) | 优先级理由 | 目标组件 |  
   | --- | --- | --- | --- | --- |  
   | 标签批量分配 | `modules/views/tags/batch_assign.js` | ~866 | 含 TagSelector/实例列表/批量操作，重复度极高 | TagSelector、BatchActionPanel、SelectionSummary |  
   | 调度中心 | `modules/views/admin/scheduler.js` | ~985 | 模态/表单/列表混在一起 | JobList、JobModal、CronHelper |  
   | 实例列表 | `modules/views/instances/list.js` | ~829 | 表格/筛选/批操作通用性强 | DataTable、FilterPanel、BulkActionBar |  
   | 账户分类 | `modules/views/accounts/account-classification/index.js` | ~1,015 | 包含列表 + 权限配置 | TreeView、PermissionConfig、ColorPicker |  
   | 日志/会话中心 | `modules/views/history/{logs,sync_sessions}.js` | 600–700 | 列表 + 筛选 + 详情抽屉模式一致 | Timeline/Table、StatusBadge、Drawer |  
   | 容量/聚合统计 | `modules/views/admin/aggregations-chart.js`、`capacity-stats/*.js` | 120–735 | 卡片/图表配置重复 | StatsCard、ChartWidget |  
   先针对这些文件拆出 UI 组件，其他较小页面（表单、登录、凭据等）在 Phase 2 迁移。
2. **四步抽离法**  
   - **Step A：模板外提** – 将页面中重复出现的 DOM 结构（模态壳、筛选面板、列表表头等）移到 `templates/components/ui/*.html` 或 JS 模板函数中。  
   - **Step B：脚本封装** – 在 `modules/ui/` 定义组件类/工厂（如 `createModal`, `createDataTable`），内部处理 DOM/事件，把原来散落在视图的代码搬进去。  
   - **Step C：视图重写为配置** – 在视图文件中只保留组件初始化与参数（字段、列、按钮 actions），删除原手写 DOM 逻辑。  
   - **Step D：替换模板引用** – 模板改为 include 新组件（或直接空 DIV），让视图脚本 mount UI 组件；同时删除旧 include 的脚本。
3. **阶段划分**  
   - **阶段 1（试点）**：标签批量分配 + 实例列表，验证 DataTable、Modal、FilterPanel、BatchActions 四类组件。  
   - **阶段 2（扩展）**：调度中心、账户分类、日志/会话，新增 TreeView、Drawer、PermissionConfig 组件。  
   - **阶段 3（表单/统计）**：凭据/实例表单改用 Form 组件，容量/聚合页面使用 StatsCard & ChartWidget，清理全局表单脚本。  
   每阶段完成后，用 `cloc` 对比组件 vs 视图的行数，确认有实际减重。
4. **自动化脚手架**：提供 `scripts/create_ui_component.py`（或 Make 目标）自动生成 `modules/ui/<component>/index.js + template.js + README.md`，避免每次手动搭目录。
5. **文档与 Story**：在 `docs/ui/` 或 Storybook 中维护组件 API 和案例，组件合并前必须更新文档 + 截图，与页面开发解耦。
6. **双轨运行**：新页面/功能默认使用 UI 模块；旧页面在所属组件稳定后，再逐一迁移，避免一次性重写导致风险。

### 3.4 与表单/视图的结合
1. **表单驱动**：组件库提供 `Form`/`Field` 组件，能接收 schema（字段类型、校验、UI 设置）并自动渲染。这样视图层只写 schema，脚本行数显著减少。
2. **状态绑定**：UI 组件与 store 通过事件通信（如 `modal.on('confirm', handler)`），视图层不直接操作 DOM，可以在不同页面复用。
3. **权限/标签等复杂组件**：将 `permission-viewer`、`tag-selector` 等复杂逻辑封装成 UI 模块，提供 `open(data)` / `update(props)` 接口，杜绝模板里 include + JS 脚本的重复模式。

### 3.5 构建与按需加载
1. **Vite/ESBuild**：把 UI 组件和视图统一纳入模块化构建，产出 `vendor-ui.js`（基础组件）+ `page chunks`，自动 tree-shake 未用组件。
2. **动态导入**：对于较重的 UI 模块（如 DataGrid/Charts），提供 `import('.../data-table.js')` 的懒加载封装，仅在组件 mount 时加载。
3. **性能基线**：UI 组件 bundle 控制在 <100KB gzip；每个页面首次加载只引入自身所需组件，避免全局脚本。

### 3.6 成功标准
- 80% 以上的新表单/模态使用 UI 模块渲染，删除大量模板/脚本重复代码。
- `base.html` 只加载 UI 基础设施和极少量 vendor，所有业务 UI 都通过页面入口按需 import。
- 组件库有完善文档、示例以及 lint 检查（例如禁止直接在视图里写模态 DOM）。

## 4. 阶段性计划

| 阶段 | 目标 | 关键动作 | 产出 |
| --- | --- | --- | --- |
| Phase 1 – UI 基础建设 | 落地 UI 模块目录和构建链路 | - 创建 `modules/ui/`、引入 Vite 构建<br>- 实现 Modal、Drawer、Toast 等基础组件<br>- 搭建 tokens + 样式基线 | `vendor-ui.js`、UI 组件文档、构建脚本 |
| Phase 2 – 试点改造 | 以标签批量分配、实例/凭据表单为试点 | - 用 UI 模块重写页面，自 schema 渲染表单与校验<br>- 把 `FormValidator` 换成局部 `createFormValidation(schema)`<br>- 总结迁移指南 | POC 页面、schema -> UI 示例、迁移手册 |
| Phase 3 – 全面迁移 | 推动全站视图逐步接入 UI 模块 | - 批量替换老模态/表格/筛选条<br>- 清理 `base.html` 中多余脚本，保证按需加载<br>- 制定 lint/测试规范，防止回退 | 减重报告、lint 规则、剩余风险清单 |

## 5. 指标与验收
- **代码量**：目标是视图层 JS 代码总行数下降 ≥30%（可用 `cloc modules/views` 监控）。
- **全局脚本**：`base.html` 中业务脚本 ≤5 个，体积 ≤150KB。
- **复用度**：关键 UI 组件（模态、统计卡、表单字段）复用率 ≥80%，杜绝复制粘贴。
- **表单自动化**：80%+ 动态表单通过 schema 渲染 + 校验，无需手写校验逻辑。
- **体验**：首次加载脚本体积减少 ≥40%，TTI 改善；同时维持 Lighthouse 分数 ≥90。

## 6. 引入 UI 模块的注意事项
1. **逐页迁移**：先从新页面或影响面小的功能开始试点，避免一次性重写导致回归风险。
2. **样式隔离**：UI 模块使用 BEM/Scoped CSS，或通过构建工具限定作用域，防止与旧样式互相污染。
3. **渐进增强**：保留旧 DOM 结构的 fallback，必要时提供 `no-js` 模式；确保即便 UI 模块加载失败也能基本使用。
4. **文档+示例**：每个 UI 模块必须附带示例/截图，避免只靠代码理解；并在 PR 模板中新增“是否复用 UI 模块”检查项。

## 7. 后续行动
- 选定试点（建议“标签批量分配 + 实例表单”），输出第一版 schema 驱动表单与 UI 组件示例。
- 在 `docs/refactoring/frontend_script_refactor_plan.md` 增加“代码减重”章节，跟踪各阶段指标。
- 引入自动化指标采集（`cloc` + `bundle-size` 脚本），提交 PR 时自动报告增减量。

通过上述策略，可把“堆栈式脚本维护”转为“配置驱动 + 组件复用”，达到真正意义上的前端代码瘦身。
