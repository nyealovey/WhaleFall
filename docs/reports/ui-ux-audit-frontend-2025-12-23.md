# 前端 UI/UX 查漏补缺评审（2025-12-23）

范围（基于仓库静态实现取样）：
- 模板：`app/templates/**`
- 样式：`app/static/css/**`（含 `variables.css` 与 components/pages）
- 脚本：`app/static/js/**`（含 page-loader、core/http、common 组件、各页面入口）

本报告按你的方法约束组织：先给 Top 5 用户路径 → 再按 1~9 维度给缺口地图（并给“应补写的规范小节标题”）→ 最后给 P0/P1/P2 的问题清单（每条含证据/影响/优先级/方案/验证）→ 附加输出“兜底点清单”。

---

## I. 关键用户路径（Top 5）

1) 登录与基础账户操作（高频入口）
- 登录页：输入用户名/密码 → 提交登录
- 登录后：顶栏进入目标模块 → 执行任务 → Toast/Alert 获取反馈
- 个人操作：修改密码 → 退出登录

2) 实例管理（核心生产力路径）
- 进入实例列表：筛选（搜索/类型/状态/标签/显示已删除）→ 查看列表结果
- 批量操作：勾选多行 → 批量测试连接 / 批量移入回收站 / 批量导入 / 导出 CSV
- 进入详情页：查看配置/状态/历史 →（可能）执行同步/修复 → 返回列表继续操作

3) 同步与排障闭环（“同步 → 结果”主链路）
- 触发同步：例如“同步所有账户”/手动执行任务/批量操作
- 进入会话中心：筛选会话 → 查看详情 → 追踪进度/失败原因
- 进入日志中心：筛选日志 → 打开详情 → 复制消息/上下文/堆栈 → 排障闭环

4) 账户台账与权限查看（管理后台高价值路径）
- 进入账户台账：按关键词/分类/标签筛选 → 按 DB 类型快速切换
- 查看权限：打开权限弹窗/策略中心 → 复制/核对权限信息
- 触发全量同步：确认影响范围 → 前往会话中心查看结果

5) 配置治理（凭据/标签/定时任务）
- 凭据管理：筛选 → 新建/编辑/删除 →（与实例/同步关联）验证影响
- 标签管理：筛选 → 新建/编辑/停用/删除 → 批量分配 → 回到实例/台账按标签筛选验证
- 定时任务：查看任务列表 → 启用/暂停/立即执行/删除 → 回到会话中心查看执行结果

---

## II. 缺口地图（按 1~9 维度逐条给：缺口描述 + 应补写规范小节标题）

### 1) 信息架构与导航
- 缺口描述：顶栏缺少“当前页高亮/定位信息”，页面也缺少面包屑，用户需要靠记忆判断“我在哪”。`page_header` 仅提供标题与动作区，不提供路径信息。证据：`app/templates/base.html:63`、`app/templates/components/ui/page_header.html:1`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《导航与定位：顶栏 active 规则（endpoint/path 映射）》
  - 《面包屑规范：何时出现/层级命名/返回行为》
  - 《列表→详情→返回：筛选条件与滚动位置保留策略》

### 2) 视觉层级与一致性（Design Consistency）
- 缺口描述：组件样式存在“同名多处定义”，导致跨页面风格漂移（例如 `.status-pill`、`.btn-icon` 既有组件基线，又被各页面 CSS 重写）。证据：`app/static/css/components/status-pill.css:3`、`app/static/css/pages/tags/index.css:97`、`app/static/css/pages/instances/list.css:141`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《组件基线优先级：components vs pages 的覆盖边界》
  - 《状态标签（status-pill）与语义色：统一尺寸/圆角/对比度》
  - 《图标按钮（btn-icon）规范：尺寸、间距、hover、focus、禁用态》

### 3) 表单与数据录入（效率 + 防错）
- 缺口描述：筛选表单的交互模式分裂：部分页面用 `UI.createFilterCard`，部分页面自写 submit/change/clear 逻辑，导致“清除/自动提交/URL 同步/埋点”等行为不一致。证据：`app/static/js/modules/ui/filter-card.js:133`、`app/static/js/modules/views/tags/index.js:260`、`app/static/js/modules/views/auth/list.js:251`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《筛选卡（FilterCard）交互规范：提交/清除/自动应用/防误触》
  - 《筛选字段命名与 query schema：search/db_type/status/tags/...》
  - 《表单校验与错误文案：时机/粒度/可行动性》

### 4) 反馈与状态（系统可理解性）
- 缺口描述：Loading 呈现存在多套实现（按按钮/按表单/按页面），且“图标按钮 loading 后恢复”逻辑存在缺陷风险；成功/失败反馈主要依赖 toast，但错误分级与文案模板未统一。证据：`app/static/js/modules/views/admin/scheduler/index.js:728`、`app/static/js/common/toast.js:157`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《加载态规范：按钮/表格/页面级（禁用、spinner、可取消）》
  - 《成功/失败反馈分级：toast vs inline vs modal》
  - 《错误文案模板：可重试/权限不足/参数错误/系统故障》

### 5) 数据表格与筛选（管理后台核心）
- 缺口描述：列表页“筛选状态是否进入 URL”不一致，导致分享链接/刷新/返回的可预测性不同；同时筛选控件栅格规范存在个别破例。证据：`app/static/js/modules/views/credentials/list.js:498`、`app/static/js/modules/views/instances/list.js:872`、`app/templates/accounts/ledgers.html:34`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《表格筛选可分享：URL 同步规则（replaceState vs 导航）》
  - 《分页/排序参数规范：page/page_size/sort/order（含兼容策略）》
  - 《filter_card 栅格规范：统一使用 col-md-2 col-12（破例流程）》

### 6) 可访问性（A11y）
- 缺口描述：大量 icon-only 按钮依赖 `title`，缺少稳定的可访问名称（aria-label / aria-labelledby），且图标 `<i>` 多数未显式 `aria-hidden`，屏幕阅读器体验不稳定。证据：`app/templates/auth/login.html:38`、`app/templates/history/logs/detail.html:17`、`app/static/js/modules/views/instances/list.js:559`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《图标按钮可访问名称规范：aria-label/aria-labelledby + title 的定位》
  - 《表单可访问性：label 绑定、必填标识、错误提示关联》
  - 《键盘可达性：focus-visible、弹窗初始焦点、Esc 行为》

### 7) 性能与体验（感知性能）
- 缺口描述：`base.html` 全局引入大量通用库/工具脚本，页面即使不使用也会加载；静态资源未做显式版本化（cache busting），可能导致“发布后旧 JS/CSS 缓存”引发的诡异问题。证据：`app/templates/base.html:237`、`app/templates/base.html:228`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《前端资源加载策略：全局依赖清单 + 页面按需引入》
  - 《静态资源版本化：Query 版本号/构建 hash/缓存策略》
  - 《大表格性能：渲染、事件委托、避免重复重绘》

### 8) 文案与国际化（体验细节）
- 缺口描述：部分功能按钮存在“占位/未实现”但仍以可点击主按钮展示，破坏信任；时间展示虽有 `time-utils`，但不同页面仍混用 `Date.toLocaleString` 与固定时区逻辑，缺少“时区显式说明”。证据：`app/templates/accounts/statistics.html:16`、`app/static/js/common/time-utils.js:4`、`app/static/js/modules/views/databases/ledgers.js:384`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《按钮文案与动词规范：创建/保存/删除/同步/导出》
  - 《时间展示规范：格式、时区、相对时间、单位》
  - 《“待上线/占位功能”处理：禁用态/提示/隐藏策略》

### 9) 前后端契约漂移对 UX 的影响（重点：兜底导致的混乱）
- 缺口描述：前端多处使用 `message || error`、`data.csrf_token ?? data.data.csrf_token`、分页字段多命名兼容等兜底；短期提升鲁棒性，但长期会让“同类错误提示/分页行为”不可预测，且难以定位后端不一致来源。证据：`app/static/js/core/http-u.js:221`、`app/static/js/common/csrf-utils.js:69`、`app/static/js/common/table-query-params.js:31`。
- 我应该补写的 UI/UX 规范小节标题：
  - 《接口响应 schema 规范：success/data/message/code（含错误分级）》
  - 《兜底策略治理：允许哪些兜底、如何埋点统计命中率、何时移除》
  - 《错误提示一致性：从后端 contract 到前端展示的闭环》

---

## III. UI/UX 问题清单（按 P0/P1/P2 分组）

### P0

#### P0-1：定时任务页图标按钮 loading 后可能丢失图标/变成文本，导致操作困惑
- 证据：
  - 图标按钮渲染为纯 `<i>`：`app/static/js/modules/views/admin/scheduler/index.js:544`
  - Loading 态保存的是 `.text()` 而不是原始 HTML：`app/static/js/modules/views/admin/scheduler/index.js:734`
  - 恢复时用 `.html(text)` 写回，无法恢复 `<i>`：`app/static/js/modules/views/admin/scheduler/index.js:759`
  - 恢复传入“启用/禁用/执行”文本：`app/static/js/modules/views/admin/scheduler/index.js:595`
- 影响：用户点击启用/暂停/立即执行后，按钮可能变空白或出现意外文本，破坏“可点/不可点”的可预期性，增加误操作与重复点击。
- 根因：交互实现层将“按钮内容恢复”简化成文本恢复，未区分 icon-only 与 text button 的原始结构；缺少 icon button 的统一 loading 规范。
- 建议：
  - 短期止血（0.5~1 天）：改为缓存并恢复 `innerHTML`（或 `data-original-html`），icon-only 按钮恢复 `<i>`；同时补齐 `aria-label` 与 `aria-busy`（见 P1-3）。
  - 中期重构（1~2 周）：抽出统一 `UI.setButtonLoading(button, {loadingText, mode})`，覆盖 icon-only 与 icon+text 两种模式，统一在各页面替换散落实现。
  - 长期规范化（可选）：把按钮状态（默认/hover/loading/disabled）写进组件规范，并在 ESLint/Review guard 中做扫描。
- 验证：
  - 手动：在“定时任务”页对同一任务连续执行“启用/暂停/立即执行”，观察按钮在完成后是否恢复原 icon 且宽度不抖动。
  - 无障碍：Tab 聚焦到按钮，屏幕阅读器能读出动作名称（不依赖 title）。

### P1

#### P1-1：存在手写颜色/阴影，绕过设计 token，导致主题一致性与可维护性风险
- 证据：
  - 顶栏“管理中心/用户中心”手写颜色：`app/templates/base.html:136`
  - Logo drop-shadow 使用手写 rgba：`app/templates/base.html:59`
  - Chart 颜色 fallback 使用手写 hex：`app/static/js/modules/theme/color-tokens.js:5`
  - 空数据图表 fallback 使用手写 rgba：`app/static/js/modules/views/components/charts/chart-renderer.js:21`
- 影响：同类语义色在不同组件/页面出现偏色；后续换主题/调整 token 时会出现“漏改点”，并造成用户对状态色的学习成本上升。
- 根因：token 治理缺少“模板/JS 侧禁止硬编码色值”的统一约束与检查；部分 fallback 未复用 `variables.css` 的 `--chart-color-*`。
- 建议：
  - 短期止血（0.5~1 天）：将 `base.html` 的 inline color/shadow 替换为 class + CSS 变量（例如 `.nav-link--admin` 使用 `var(--status-danger)` / `var(--accent-primary)` 的语义化 token）。
  - 中期重构（1~2 周）：`ColorTokens` 读取 `--chart-color-1..22` 作为唯一来源，移除 JS hardcode fallback；为“缺 token”场景做一次性告警而非默默回退。
  - 长期规范化（可选）：补写并启用“CSS token guard / 前端色值 guard”，在 CI 阶段阻断新增 hex/rgb/rgba。
- 验证：
  - 代码：`rg -n \"#[0-9a-fA-F]{3,8}|rgba?\\(\" app/templates app/static/js` 除 `variables.css` 外不新增命中。
  - 视觉：截图对比顶栏与危险确认/危险按钮在不同页面的一致性（同一语义色同一观感）。

#### P1-2：filter_card 栅格规范出现破例（col-md-3），破坏筛选区布局一致性
- 证据：账户台账筛选卡的标签筛选使用 `col-md-3 col-12`：`app/templates/accounts/ledgers.html:34`。
- 影响：同类筛选控件在不同页面宽度分配不同，用户扫视/肌肉记忆被打断；在 1024 宽度下更容易出现换行与对齐不齐，降低表单效率。
- 根因：缺少“破例流程/替代方案”（例如通过内部控件自适应，而不是改栅格列宽）。
- 建议：
  - 短期止血（0.5 天）：回收为 `col-md-2 col-12`，并通过局部 utility class 让内部按钮/chips 区域支持换行或更紧凑展示（不改变栅格列宽）。
  - 中期重构（1 周）：为“标签筛选（含 chips 预览）”定义专用组件规范（含建议宽度策略），避免各页面自行调列宽。
  - 长期规范化（可选）：在代码评审 guard 中扫描 `filter_card` 内是否存在非 `col-md-2 col-12`。
- 验证：
  - 手动：在 1024/1366/1440 宽度下打开账户台账/实例列表/凭据管理，筛选区对齐一致且不出现异常挤压。

#### P1-3：大量 icon-only 按钮缺少可访问名称（依赖 title），A11y 体验不稳定
- 证据（取样）：
  - 登录页“显示/隐藏密码”按钮仅图标无 aria-label：`app/templates/auth/login.html:38`
  - 统计页刷新按钮仅图标无 aria-label：`app/templates/instances/statistics.html:14`、`app/templates/accounts/statistics.html:13`
  - 日志详情复制按钮仅图标无 aria-label：`app/templates/history/logs/detail.html:17`
  - 列表行内操作按钮仅 title：`app/static/js/modules/views/instances/list.js:559`、`app/static/js/modules/views/databases/ledgers.js:227`
- 影响：屏幕阅读器用户无法可靠理解按钮用途；键盘用户在焦点移动时缺少明确提示；title 在触屏/部分读屏场景不可用或体验差。
- 根因：缺少“btn-icon 必须提供可访问名称”的组件级约束；页面 CSS/JS 复用不足导致每页各自生成按钮。
- 建议：
  - 短期止血（0.5~1 天）：为所有 `.btn-icon` 补齐 `aria-label`（与 title 同文案），并将图标 `<i>` 统一加 `aria-hidden="true"`。
  - 中期重构（1~2 周）：沉淀宏/函数：模板侧提供 `icon_button(label, ...)`，JS 侧提供 `renderIconButton({label, icon, ...})`，强制 label 必填。
  - 长期规范化（可选）：新增 guard：扫描 `.btn-icon` 缺失 aria-label/aria-labelledby 的情况。
- 验证：
  - 无障碍：用浏览器 Accessibility Tree 检查 `.btn-icon` 均有 Name；键盘 Tab 逐个聚焦可读。
  - 回归：检查 tooltip 仍可用，但不再作为唯一信息来源。

#### P1-4：多个列表页筛选仅更新 Grid，不同步 URL，导致“刷新/分享/返回”丢上下文
- 证据：
  - 用户管理：grid 存在时仅 `updateFilters` 并 `return`：`app/static/js/modules/views/auth/list.js:317`
  - 凭据管理：grid 存在时仅 `updateFilters` 并 `return`：`app/static/js/modules/views/credentials/list.js:498`
  - 标签管理：更新 grid 但无 `history.replaceState/pushState`：`app/static/js/modules/views/tags/index.js:314`
  - 数据库台账：submit/clear 仅操作 grid，不同步地址栏：`app/static/js/modules/views/databases/ledgers.js:314`
  - 对照：实例列表已做 URL 同步：`app/static/js/modules/views/instances/list.js:872`
- 影响：用户无法复制“当前筛选结果”的链接；刷新页面后筛选丢失；从详情/其他页面返回时上下文不可预测，增加重复操作与排障成本。
- 根因：缺少跨页面统一的“筛选 → URL”策略与工具；不同页面在“服务端跳转 vs 前端刷新”之间混用。
- 建议：
  - 短期止血（1~2 天）：为 users/credentials/tags/databases 等列表页补齐 `replaceState` 同步（复用 `TableQueryParams.buildSearchParams` 或抽通用 helper），保证最少 search/status/page/page_size 进入 URL。
  - 中期重构（1~2 周）：让 `GridWrapper` 支持可选的 `syncUrl({allowedKeys, basePath})`，由 wrapper 统一完成（避免每页手写）。
  - 长期规范化（可选）：在规范中明确“哪些筛选必须可分享”，并为特殊页面提供例外说明。
- 验证：
  - 手动：应用筛选 → 复制 URL → 新开标签页打开，应还原筛选并得到一致结果。
  - 回归：浏览器后退/前进应可恢复上一次筛选状态。

#### P1-5：同名组件（status-pill / btn-icon）多处重复定义，导致跨页面样式漂移
- 证据（取样）：
  - 组件基线：`app/static/css/components/status-pill.css:3`
  - 页面重复定义：`app/static/css/pages/tags/index.css:97`、`app/static/css/pages/credentials/list.css:62`、`app/static/css/pages/admin/scheduler.css:122`
  - `.btn-icon` 多处定义且尺寸不同：`app/static/css/pages/instances/list.css:141`、`app/static/css/pages/tags/index.css:128`、`app/static/css/pages/admin/scheduler.css:115`
- 影响：用户跨页面看到同一“状态标签/图标按钮”尺寸、圆角、密度不同，形成不一致的视觉语言；工程侧维护成本高，修复一个页面容易漏掉其他页面。
- 根因：组件沉淀策略不清晰，pages 层样式覆盖组件基线，缺少统一归口与删除旧样式的收敛动作。
- 建议：
  - 短期止血（1~2 天）：确定 `components/*.css` 为唯一基线来源；在 2~3 个高频页面先删除/收敛重复定义，验证无回归后推广。
  - 中期重构（1~2 周）：建立“组件 CSS 清单”与迁移 checklist（pages 不允许再定义同名组件类）。
  - 长期规范化（可选）：新增 CSS guard（仓库已存在相关脚本入口），对重复定义做检测并阻断新增。
- 验证：
  - 视觉：抽 3 个页面（实例列表/标签管理/定时任务），对比 `.status-pill` 与 `.btn-icon` 的尺寸与对齐一致。
  - 代码：`rg -n \"^\\.status-pill\" app/static/css/pages` 命中逐步归零（或仅保留页面特例并写明原因）。

#### P1-6：危险操作按钮层级不一致（同类操作用不同按钮语义/配色），增加误触风险
- 证据：
  - 实例列表“移入回收站”使用 `btn-outline-secondary text-danger`（而非语义危险按钮）：`app/templates/instances/list.html:59`
  - 凭据删除弹窗取消按钮用 `btn-secondary`，与全局危险确认弹窗的 `btn-outline-secondary` 不一致：`app/templates/credentials/list.html:65`、`app/templates/components/ui/danger_confirm_modal.html:30`
  - 标签删除弹窗取消按钮为 `btn-outline-secondary`：`app/templates/tags/index.html:106`
- 影响：用户对“危险操作”的识别依赖页面经验而非一致规则；在批量/删除等高风险场景下增加误触概率。
- 根因：缺少按钮层级与危险操作的统一规范落地；部分页面通过 `text-danger` 做局部修饰，绕开语义按钮体系。
- 建议：
  - 短期止血（0.5~1 天）：统一危险操作主按钮使用 `btn-outline-danger/btn-danger`，取消按钮统一 `btn-outline-secondary`；批量危险操作按钮禁用态也要符合语义。
  - 中期重构（1~2 周）：将“危险操作确认”统一迁移到 `UI.confirmDanger`，并规范化 confirmButtonClass（warning vs danger 的规则）。
  - 长期规范化（可选）：把按钮层级规则写入 `docs/standards/button-hierarchy-guidelines.md` 的“页面落地检查表”。
- 验证：
  - 手动：抽 3 个危险场景（实例回收站、凭据删除、标签删除），确认按钮层级一致且无需读文案也可识别风险。

#### P1-7：顶栏缺少 active/定位信息，且折叠菜单缺少 toggler，信息架构可发现性不足
- 证据：
  - 顶栏链接均未设置 active/aria-current：`app/templates/base.html:66`
  - 使用 `collapse navbar-collapse` 但未见 `navbar-toggler`（小宽度下无法展开菜单）：`app/templates/base.html:63`
  - 页面头部宏不含面包屑：`app/templates/components/ui/page_header.html:1`
- 影响：用户难以快速确认“当前所在模块”，在多标签页/深层操作后容易迷失；小窗宽度（仍可能是桌面场景）下导航可用性下降。
- 根因：导航态未与后端 endpoint/path 建立映射；缺少“定位组件（active/breadcrumb）”的基线实现。
- 建议：
  - 短期止血（1 天）：在 `base.html` 为当前 endpoint 匹配的菜单项增加 `active` 与 `aria-current="page"`；补齐 `navbar-toggler` 与按钮可访问名称。
  - 中期重构（1~2 周）：抽出 `nav_active(endpoint)` 宏/过滤器，统一管理菜单映射；对 dropdown 的子项也支持高亮。
  - 长期规范化（可选）：定义“页面信息架构”标准模板：标题 + 面包屑 + 主要动作 + 次要动作。
- 验证：
  - 手动：进入 5 个核心页面，顶栏能明确高亮当前模块；缩小浏览器宽度后仍可通过 toggler 展开菜单。

#### P1-8：静态资源未显式版本化 + 页脚版本硬编码，发布后易出现缓存错配与信任问题
- 证据：
  - 页脚版本号硬编码：`app/templates/base.html:228`
  - CSS/JS 引用均无版本 query：`app/templates/base.html:21`、`app/templates/base.html:237`
- 影响：发布后用户可能命中旧缓存（旧 JS 对新接口/DOM），出现“偶现 bug”；页脚版本与真实版本不一致会降低用户信任与排障效率。
- 根因：缺少统一的静态资源 cache busting 方案；版本号来源未与后端构建/发布流程打通。
- 建议：
  - 短期止血（1 天）：从后端注入 `app_version`，统一用于页脚与静态资源 query（例如 `?v={{ app_version }}`）。
  - 中期重构（1~2 周）：建立构建产物 hash/manifest（若无打包链路，也至少保证版本号随发布变更）。
  - 长期规范化（可选）：将“缓存策略/版本号”纳入发布 Checklist 与文档（`docs/standards/VERSION_UPDATE_GUIDE.md` 可扩展）。
- 验证：
  - 手动：修改静态文件后发布，访问页面确保请求 URL 变化；清缓存与不清缓存结果一致。

#### P1-9：统计页提供“导出”主按钮但无实现，属于“可点击但无结果”的信任破坏点
- 证据：
  - 实例统计导出按钮无 data-action/链接：`app/templates/instances/statistics.html:17`
  - 账户统计导出按钮无 data-action/链接：`app/templates/accounts/statistics.html:16`
  - 页面脚本仅绑定刷新动作（未见导出绑定）：`app/static/js/modules/views/instances/statistics.js:546`、`app/static/js/modules/views/accounts/statistics.js:4`
- 影响：用户点击后无反馈，会认为系统不可靠；也会增加“是不是我权限不够/是不是卡了”的困惑。
- 根因：功能未实现但 UI 以“可操作主按钮”形态暴露，缺少占位功能的产品化处理。
- 建议：
  - 短期止血（0.5 天）：未实现前改为禁用态并提示“待上线”，或直接隐藏按钮。
  - 中期重构（1~2 周）：实现导出（同步导出或异步任务 + 会话中心查看结果），并复用危险确认/进度提示规范。
  - 长期规范化（可选）：建立“占位功能”准入规则：必须有明确状态与下一步入口。
- 验证：
  - 手动：点击导出必有明确反馈（开始下载/弹窗/跳转会话中心），无“沉默失败”。

### P2

#### P2-1：时间/时区策略未统一，用户难以判断时间口径
- 证据：
  - `time-utils` 默认时区固定为 Asia/Shanghai：`app/static/js/common/time-utils.js:4`
  - 数据库台账使用 `Date.toLocaleString('zh-CN')`（口径与 time-utils 可能不同）：`app/static/js/modules/views/databases/ledgers.js:384`
- 影响：跨模块查看“开始时间/耗时/采集时间”时可能出现口径不一致（尤其在非上海时区环境），降低排障效率。
- 根因：缺少“统一时间格式化入口”的强制规范；历史代码混用原生 Date 与 time-utils。
- 建议：
  - 短期止血（0.5~1 天）：将关键页面（会话中心/日志中心/台账）统一改为 `timeUtils.formatTime(...)` 输出，并在 UI 上明确时区（例如“(UTC+8)”）。
  - 中期重构（1~2 周）：让时区来自后端配置（env/用户偏好），并在页面 header/表格列名统一标注。
  - 长期规范化（可选）：补写时间规范并在 code review 中检查禁止直接 `new Date(...).toLocaleString()`。
- 验证：
  - 手动：抽取 3 个页面的同一时间字段，对比展示格式与时区标注一致。

#### P2-2：调试输出与错误处理分散，增加噪音与契约漂移风险
- 证据：
  - 凭据列表存在 `console.log` 调试输出：`app/static/js/modules/views/credentials/list.js:492`
  - `http-u` 仍在解析 `body.message || body.error`：`app/static/js/core/http-u.js:221`
  - CSRF token 解析存在 `data?.csrf_token ?? data?.data?.csrf_token`：`app/static/js/common/csrf-utils.js:69`
- 影响：调试日志污染控制台，排障成本上升；错误文案字段不统一会让“同类错误提示”在不同页面漂移。
- 根因：缺少前端侧统一的错误 schema 与兜底收敛计划；各模块自写 resolveErrorMessage/兜底逻辑。
- 建议：
  - 短期止血（0.5~1 天）：清理明显 debug log；统一页面侧尽量只消费 `error.message`（由 httpU buildError 生成）。
  - 中期重构（1~2 周）：补齐“兜底命中埋点”，统计 `body.error` / `data.data.csrf_token` 命中率，驱动后端收敛。
  - 长期规范化（可选）：建立“契约漂移门禁”到前端（与后端 drift guard 对齐）。
- 验证：
  - 控制台：正常操作不应出现无意义 log；错误提示在 3 个模块中一致可预测。

### D. 最小可执行修复路线图（≤8 项，每项 0.5~2 天）

1) 修复 scheduler 图标按钮 loading/恢复逻辑（P0-1），并补齐 icon-only aria-label（P1-3 的一部分）。
2) 建立统一的 icon button 生成与 A11y 规范（模板宏 + JS helper），迁移 2 个高频页面（实例列表/日志详情）。
3) 在 users/credentials/tags/databases 等列表页补齐“筛选 → URL replaceState”同步（P1-4），并统一 query key 白名单。
4) 收敛 `.status-pill` 与 `.btn-icon`：以 components 为基线，选 3 个高频页面删掉 pages 层重复定义（P1-5）。
5) 清理模板/JS 的手写颜色点位（P1-1），并把 chart fallback 颜色改为读取 `--chart-color-*`。
6) 统一危险操作按钮层级与确认体验：危险按钮语义化 + 全面迁移到 `UI.confirmDanger`（P1-6）。
7) 顶栏增加 active/aria-current 与 navbar toggler（P1-7），补齐“我在哪”的定位信息。
8) 静态资源版本化 + 页脚版本来源统一（P1-8），并将“未实现导出按钮”改为禁用/隐藏或补齐实现（P1-9）。

---

## 附加输出：兜底/兼容/回退/适配（前端侧）

> 目标：将“兜底”从无声容错升级为可观测（埋点/告警），并推动后端契约收敛后逐步移除。

| 位置（文件:行号） | 类型 | 描述（对 UX 的风险） | 建议（收敛/埋点/移除策略） |
|---|---|---|---|
| `app/static/js/core/http-u.js:221` | 兜底/兼容 | `body.message || body.error`：同类错误在不同接口可能展示不同字段，造成文案漂移 | 统一后端错误 schema（建议固定 `message`）；前端在命中 `body.error` 时 `EventBus.emit('contract:error-field-fallback', {...})` 统计命中率，降到 0 后移除 fallback |
| `app/static/js/common/csrf-utils.js:69` | 兼容 | `data.csrf_token ?? data.data.csrf_token`：前端必须猜响应形状，错误时表现为“偶发 403/CSRF 缺失” | 统一 `/auth/api/csrf-token` 响应为 `{csrf_token}`；命中 `data.data.csrf_token` 时埋点 `contract:csrf-legacy-shape` |
| `app/static/js/common/table-query-params.js:31` | 兼容 | `page_size/pageSize/limit` 多命名兼容：分页行为不可预测，用户感知为“同一筛选不同页面页大小不一致” | 明确唯一参数 `page_size`；当前已在命中旧字段时发事件：`app/static/js/common/table-query-params.js:83`，建议接入统一日志/监控并推动后端/旧链接迁移 |
| `app/static/js/modules/stores/logs_store.js:152` | 兼容 | `data.limit ?? data.per_page ?? data.perPage`：列表页大小/分页口径漂移，影响用户对“总数/页数”的理解 | 与后端约定统一字段并移除多字段解析；短期在非主字段命中时埋点统计 |
| `app/static/js/modules/theme/color-tokens.js:5` | 回退 | chart 色板 hardcode hex：换主题/换 token 时会出现局部偏色 | 以 `variables.css` 的 `--chart-color-*` 为唯一来源；fallback 也从 CSS vars 读取（若缺失则上报而不是 silent） |
| `app/static/js/modules/views/components/charts/chart-renderer.js:21` | 回退 | 空态背景色 hardcode rgba：与 token 治理冲突，空态观感在不同主题下不可控 | 用 `ColorTokens.withAlpha(ColorTokens.resolveCssVar('--chart-color-1'), 0.2)` 等生成；hardcode 作为最后兜底时应同时告警 |
| `app/static/js/modules/views/admin/scheduler/index.js:591` | 兜底 | `error.response.message || error.message`：上层仍在猜错误结构，导致同类错误文案不一致 | 统一只消费 `error.message`（由 httpU.buildError 统一生成）；命中 `error.response.message` 时埋点以推动收敛 |
