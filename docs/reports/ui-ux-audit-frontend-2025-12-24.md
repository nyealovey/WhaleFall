# 前端 UI/UX 查漏补缺式评审（2025-12-24）

> 评审角色：资深 UI/UX 审计师 + 前端工程负责人 + 无障碍(Accessibility)专家 + 产品体验研究员  
> 评审范围：`app/templates/**`、`app/static/css/**`、`app/static/js/**`  
> 约束：仅桌面端（重点关注 1024/1366/1440/1920）；色彩必须来自 `variables.css`/token；`filter_card` 内控件栅格必须 `col-md-2 col-12`（发现违规必须标注证据）。  
> 方法说明：本次为“启发式评审 + 证据取样”的静态代码审计（未启动浏览器）；通过 `rg`/`nl -ba` 定位行号。当前环境未提供 `filesystem-mcp` 工具，因此改用 shell 读取文件定位证据。

---

## I. 关键用户路径 (Top 5)

1) 登录与基础账户操作（高频、所有用户必经）
- `auth/login.html` 登录 → 校验失败提示 → 登录成功进入仪表盘
- 右上角用户菜单 → 修改密码 → 退出登录

2) 实例管理主流程（高频、核心价值）
- `instances/list.html` 进入实例列表 → `filter_card` 筛选（搜索/DB类型/状态/标签）
- 选择实例 → 批量移入回收站 / 批量测试连接 → 导出 CSV
- 进入 `instances/detail.html` → 测试连接 / 同步账户 / 同步容量 → 返回列表继续操作

3) 台账管理（高价值、管理后台核心）
- `databases/ledgers.html` 数据库台账筛选（搜索/DB类型/标签）→ 导出 CSV → 打开容量趋势
- `accounts/ledgers.html` 账户台账筛选（搜索/分类/标签）→ 导出 CSV → 触发“同步所有账户”

4) 异步任务结果闭环（同步/导出后的“确认已完成”）
- 从台账/详情触发同步任务 → `history/sessions/sync-sessions.html` 会话中心筛选（状态/方式/分类）
- 打开会话详情 modal → 复制会话 ID / 错误堆栈 → 必要时取消会话

5) 日志排障（高价值、失败定位）
- `history/logs/logs.html` 日志中心筛选（关键词/级别/模块/时间范围）
- 打开日志详情 modal → 复制消息/上下文 JSON/堆栈 → 回到业务对象继续修复

---

## II. 缺口地图（按评审维度 1~9）

### 1) 信息架构与导航
- 缺口：全局导航缺少“当前页高亮/我在哪”的明确信号；无面包屑；部分返回路径会丢失列表上下文（筛选/分页/滚动）。
  - 需补写规范小节：**全局导航与定位规范（active 高亮 / aria-current / 面包屑）**
  - 需补写规范小节：**列表→详情→返回策略（return_to、筛选保留、滚动恢复）**
- 缺口：浏览器标签页标题缺少页面上下文，降低多标签并行效率。
  - 需补写规范小节：**页面标题（`<title>`）拼装与动态 AppName 更新规范**

### 2) 视觉层级与一致性（Design Consistency）
- 缺口：同类交互在不同页面实现不同（筛选器/按钮 loading/空态/结果入口），导致“体验像拼起来的”。
  - 需补写规范小节：**交互一致性基线（按钮/筛选/表格/弹窗/状态）**
- 缺口：链接样式默认去下划线，正文场景下可发现性下降。
  - 需补写规范小节：**链接 vs 按钮的视觉语义规范**

### 3) 表单与数据录入（效率 + 防错）
- 缺口：同类控件（密码显示/隐藏）在不同表单的无障碍与提示不一致；必填标识与校验反馈策略不统一。
  - 需补写规范小节：**表单输入与校验规范（必填、错误文案、触发时机、可行动性）**
  - 需补写规范小节：**敏感字段交互规范（密码可见性、复制、提示）**

### 4) 反馈与状态（系统可理解性）
- 缺口：导出/异步任务普遍缺少“开始/进行中/完成/去哪看结果”的闭环一致性。
  - 需补写规范小节：**异步任务反馈闭环规范（toast + loading + 结果入口 + 自动刷新策略）**
- 缺口：同类错误提示来源不一致（toast/alert/页面内），且消息字段解析存在漂移。
  - 需补写规范小节：**成功/错误/空态/Loading 统一规范（优先级、位置、文案模板）**

### 5) 数据表格与筛选（管理后台核心）
- 缺口：筛选器实现分裂（`UI.createFilterCard` vs 页面自写），导致 debounce/清空/URL 记忆/事件广播不一致，并出现真实功能缺陷（日志筛选）。
  - 需补写规范小节：**FilterCard 组件规范（栅格、键、自动提交、清空、URL 同步、埋点）**
- 缺口：表格操作列大量使用 icon-only 按钮但无统一 A11y 约束；复制/固定列/长文本处理缺少统一模式。
  - 需补写规范小节：**表格列与操作栏规范（密度、复制、长文本、icon-only A11y）**

### 6) 可访问性（A11y）
- 缺口：icon-only 按钮缺少可访问名称；装饰性图标未统一 `aria-hidden`；下拉菜单缺少 focus 态强化；缺少 skip-link。
  - 需补写规范小节：**A11y 基线清单（导航/表单/按钮/模态/Toast/表格）**
  - 需补写规范小节：**icon-only 按钮可访问名称规范（aria-label/visually-hidden/title 兜底）**

### 7) 性能与体验（感知性能）
- 缺口：`base.html` 全局加载大量 JS/CSS（含页面级样式），登录页/轻量页也承担成本；组件 CSS 在 body 内重复引入，存在 FOUC 风险。
  - 需补写规范小节：**资源加载策略（按页加载、组件资源清单、去重）**
- 缺口：静态资源未做显式版本化，发布后缓存一致性与回滚可控性弱。
  - 需补写规范小节：**静态资源缓存与版本化规范（build hash、cache headers）**

### 8) 文案与国际化（体验细节）
- 缺口：时间格式/是否含年份/时区处理在不同页面不一致；部分错误文案包含技术细节或拼接不一致。
  - 需补写规范小节：**时间/数字/单位格式规范（时区、年份、相对时间）**
  - 需补写规范小节：**错误文案写作规范（分级、可行动、避免技术化暴露）**

### 9) 前后端契约漂移对 UX 的影响（重点）
- 缺口：前端存在大量 `message || error`、`data?.x ?? data?.data?.x`、`response.data || response` 的兜底解析，导致同类错误提示与行为不可预测，掩盖后端 schema 不一致。
  - 需补写规范小节：**统一 API 响应 Schema 规范（success/message/error/data/request_id）**
  - 需补写规范小节：**前端兼容层与兜底埋点规范（命中率统计→渐进移除）**

---

## III. UI/UX 问题清单（按 P0/P1/P2 分组）

### P0

#### 1) 浏览器标签页标题被 app-info 脚本覆盖，页面上下文丢失
- 优先级：P0
- 证据：`app/templates/base.html:8`；`app/templates/base.html:324`
- 影响：用户无法通过标签页标题快速分辨“我在哪/哪个页”，多标签并行效率下降；可访问性（读屏/历史记录）也变差。
- 根因：动态加载 appName 的脚本直接覆盖 `<title>`，忽略页面模板 `block title` 的页面级信息架构。
- 建议：
  - 短期止血（0.5~2 天）：只更新“AppName”部分，不覆盖页面标题；例如保留原始 title 并拼接为 `页面标题 - AppName`，或仅更新 `#app-name/#footer-app-name` 不改 `<title>`。
  - 中期重构（1~2 周）：建立统一的 title 生成器（Jinja 宏/单一函数），明确“页面名/模块名/AppName”的拼装规则。
  - 长期规范化（可选）：补充“页面标题规范”文档，并对新增页面做门禁检查（必须包含页面上下文）。
- 验证：
  - 手动：打开“实例管理/日志中心/会话中心”三页，观察标签页标题是否包含各自页面名且 AppName 更新后仍保留页面名。
  - 回归：多标签打开后可快速区分，浏览器历史记录标题不再统一成同一个字符串。

#### 2) 日志中心筛选条件未真正传递到查询/统计，导致筛选几乎失效
- 优先级：P0
- 证据：`app/templates/history/logs/logs.html:54`；`app/static/js/modules/views/history/logs/logs.js:284`；`app/static/js/modules/views/history/logs/logs.js:323`；`app/routes/history/logs.py:114`
- 影响：用户无法按关键词/模块/时间范围有效定位日志；统计卡片也可能与筛选不一致；在日志量大时会造成“页面很慢且找不到信息”的强挫败感。
- 根因：前端筛选键名在 `resolveFilters()` 与 `sanitizeFilters()` 之间不一致（search/module/hours 未被保留），属于历史字段迁移后的残留；同时与后端参数（`search/module/hours`）不匹配。
- 建议：
  - 短期止血（0.5~2 天）：修正 `sanitizeFilters()`，确保保留并传递 `search/module/hours`（由 `time_range` 映射得到）；同时让 grid 与 stats 使用同一套 params。
  - 中期重构（1~2 周）：将“筛选键名 schema”收敛到一个共享工具（例如 `buildFilters()`），并在 FilterCard 组件层统一 URL 同步/清空策略。
  - 长期规范化（可选）：为筛选参数建立类型/枚举与门禁（禁止 legacy key 漂移回归）。
- 验证：
  - 手动：在日志中心切换模块/时间范围/搜索关键词，观察请求 query 是否包含对应字段；结果集与统计是否同步变化。
  - 用例：输入 2 字符搜索应生效；清空后回到默认 1d 时间范围与全量模块。

#### 3) 实例详情“同步账户”成功判定使用 `message` 兜底，可能把失败展示为成功
- 优先级：P0
- 证据：`app/static/js/modules/views/instances/detail.js:279`；`app/static/js/modules/views/instances/detail.js:281`
- 影响：用户被误导为“同步成功”，后续在台账/会话中心发现数据未更新；信任受损且会重复触发任务造成资源浪费。
- 根因：前端为兼容多种返回结构，使用 `data?.success || Boolean(data?.message)` 推断成功；但 `message` 在失败场景也可能存在，导致误判。
- 建议：
  - 短期止血（0.5~2 天）：改为严格判断 `success === true`（或 HTTP 2xx + success true）；失败时优先展示后端给出的明确错误字段，并提供“去会话中心查看进度/错误”的入口。
  - 中期重构（1~2 周）：抽出统一的 `resolveApiResult()`，所有“同步/导入/批量”统一解析 `success/message/error/request_id`。
  - 长期规范化（可选）：配合后端统一响应 schema，移除 `message` 推断成功的兜底，并对兜底命中率做埋点与告警。
- 验证：
  - 构造返回 `{success:false,message:'xxx'}` 时必须展示错误；返回 `{success:true,message:'ok'}` 时展示成功；回到会话中心可找到对应任务记录（若为异步）。

### P1

#### 1) 列表→详情→返回丢筛选上下文（实例详情“返回列表”硬跳转）
- 优先级：P1
- 证据：`app/templates/instances/detail.html:151`；`app/static/js/modules/views/instances/list.js:638`；`app/static/js/modules/views/instances/detail.js:377`
- 影响：用户在筛选后进入详情，再点击“返回列表/删除后返回”会丢失筛选与上下文，重复操作成本高。
- 根因：详情页的返回链接与删除后的 redirect 仅指向 `/instances`，没有携带 `return_to` 或从 referrer 恢复。
- 建议：
  - 短期止血（0.5~2 天）：从列表进入详情时在 URL 携带 `return_to={{ request.full_path }}`；详情页“返回列表”优先使用该参数；删除后的跳转同理。
  - 中期重构（1~2 周）：抽象“列表/详情返回”通用组件与安全校验（仅允许站内路径）。
  - 长期规范化（可选）：将“列表上下文保持”写成规范并覆盖所有列表页（实例/标签/凭据/台账/会话/日志）。
- 验证：在实例列表设置筛选→进入详情→点击返回/删除后返回，仍保留筛选与分页；浏览器后退也行为一致。

#### 2) 全局导航缺少当前页高亮与 `aria-current`，用户难回答“我在哪”
- 优先级：P1
- 证据：`app/templates/base.html:65`（导航链接无 active/aria-current）；`app/templates/base.html:51`（已有 `data-page` 可用但未用于导航定位）
- 影响：用户在多模块切换时需要额外认知成本；对新用户学习与回溯路径不友好。
- 根因：导航未与 endpoint/page_id 建立映射；缺少定位组件（面包屑/当前页高亮）。
- 建议：
  - 短期止血（0.5~2 天）：在模板端基于 `request.endpoint` 或 `page_id` 计算 active，添加 `.active` 与 `aria-current="page"`；必要时给 dropdown 父级也高亮。
  - 中期重构（1~2 周）：引入面包屑（可挂在 `page_header`），并在页面级声明 `nav_section`。
  - 长期规范化（可选）：补充“导航与定位”规范与可视化回归检查项。
- 验证：分别打开“实例管理/日志中心/会话中心/定时任务”，导航能正确高亮且键盘/读屏能读出当前页。

#### 3) Page Header 的 description 参数未渲染，页面语义信息缺失
- 优先级：P1
- 证据：`app/templates/components/ui/page_header.html:1`（存在 description 参数）但 `app/templates/components/ui/page_header.html:12` 仅渲染 h1；样式却已预留 `app/static/css/global.css:255`
- 影响：页面顶部缺少“这页做什么”的一句话说明；对新用户理解与排障效率有直接影响。
- 根因：组件实现与调用方约定不一致（调用方传了 description，但组件未输出）。
- 建议：
  - 短期止血（0.5~2 天）：在 page_header 中渲染 description（如 `<p>`），并限制最大宽度避免与 actions 挤压。
  - 中期重构（1~2 周）：page_header 支持面包屑 slot/secondary meta slot。
  - 长期规范化（可选）：在“页面头部规范”中明确 title/description/actions 的布局规则（含 1024/1366 下换行策略）。
- 验证：检查多页面（仪表盘/实例/台账/日志/会话）均显示 description 且布局稳定。

#### 4) Tag Selector 组件在 body 内重复引入 CSS，存在 FOUC/重复加载风险
- 优先级：P1
- 证据：`app/templates/components/tag_selector.html:2`；`app/templates/instances/list.html:12`；`app/templates/instances/list.html:102`
- 影响：样式加载顺序不稳定（`<link>` 出现在 body 底部）；网络上可能重复请求同一 CSS；维护时容易引发“某页样式突然不对”的偶发问题。
- 根因：组件模板同时承担“资源引入 + DOM 结构”两种职责，且被放在 `extra_js` 内 include。
- 建议：
  - 短期止血（0.5~2 天）：移除 `tag_selector.html` 内 `<link>`；统一在页面 `extra_css` 引入；若要自动化，引入“组件资源清单”宏。
  - 中期重构（1~2 周）：组件按需注册（page_id→依赖映射），由 page-loader 统一注入。
  - 长期规范化（可选）：制定组件打包规范（模板只负责结构；资源在 head 统一管理）。
- 验证：DevTools network 中 `tag-selector.css` 只加载一次；刷新无样式闪烁；所有含标签选择器的页面样式一致。

#### 5) FilterCard 实现分裂（统一组件 vs 页面自写），导致行为漂移与缺陷高发
- 优先级：P1
- 证据：统一组件 `app/static/js/modules/ui/filter-card.js:133`；使用示例 `app/static/js/modules/views/instances/list.js:589`；自写实现 `app/static/js/modules/views/tags/index.js:263`、`app/static/js/modules/views/credentials/list.js:362`、`app/static/js/modules/views/databases/ledgers.js:309`
- 影响：同类筛选器在不同页面“手感不同”（debounce、清空、是否同步 URL、是否广播事件）；且更容易出现日志中心这种“字段丢失”的真实 bug。
- 根因：缺少“FilterCard 唯一实现与规范”约束，导致多版本并存。
- 建议：
  - 短期止血（0.5~2 天）：选定唯一方案（建议 `UI.createFilterCard`）并开始迁移 1~2 个页面（tags/credentials）作为样板。
  - 中期重构（1~2 周）：逐页迁移并清理旧逻辑；把 debounce/auto-apply/clear 作为组件参数统一。
  - 长期规范化（可选）：补写 FilterCard 规范与门禁（禁止新增页面自写筛选绑定）。
- 验证：tags/credentials/databases-ledger 的筛选行为与 instances/logs/sessions 一致；清空/自动提交/URL 记忆符合统一规则。

#### 6) filter_card 栅格规范违规：账户台账标签筛选使用 `col-md-3 col-12`
- 优先级：P1
- 证据：`app/templates/accounts/ledgers.html:34`
- 影响：破坏筛选区域的统一栅格节奏；在不同桌面宽度下容易出现对齐不齐、按钮列被挤压等问题；也违背仓库既定规范，后续容易出现更多“例外扩散”。
- 根因：为获得更宽的控件空间，直接修改了栅格列，而非使用允许的“局部 utility class + 评审说明”方式。
- 建议：
  - 短期止血（0.5~2 天）：恢复为 `col-md-2 col-12`；如确需更宽，改为控件内部 `w-100`/多行折叠，或在局部容器增加 scoped utility class（不改栅格列）。
  - 中期重构（1~2 周）：增强标签筛选 preview 的省略/折叠展示，减少对宽度的依赖。
  - 长期规范化（可选）：在 FilterCard 规范中写明“允许突破栅格的唯一方式”并配套审查脚本。
- 验证：账户台账筛选区在 1024/1366/1440/1920 下对齐一致；动作按钮列稳定；无新增栅格例外。

#### 7) 大量 icon-only 按钮缺少 `aria-label`，无障碍不可用且不一致
- 优先级：P1
- 证据：缺失示例 `app/templates/history/logs/detail.html:17`、`app/static/js/modules/views/history/sessions/sync-sessions.js:400`、`app/static/js/modules/views/instances/list.js:559`、`app/static/js/modules/views/databases/ledgers.js:227`；对照：已正确提供 `aria-label` 的示例 `app/static/js/modules/views/admin/scheduler/index.js:544`
- 影响：读屏用户无法理解按钮用途；键盘用户也缺少稳定提示；影响合规与可用性。
- 根因：缺少 icon-only 按钮的强约束与自动修复机制（title 不是可靠的可访问名称）。
- 建议：
  - 短期止血（0.5~2 天）：为所有 `btn-icon` 增加 `aria-label`；装饰性 `<i>` 统一 `aria-hidden="true"`；模板端可加 `<span class="visually-hidden">`。
  - 中期重构（1~2 周）：增加 ESLint/脚本门禁：发现 `btn-icon` 且无 `aria-label/aria-labelledby` 阻断；或在渲染器统一注入。
  - 长期规范化（可选）：补写 icon-only A11y 规范与示例库（对齐现有 `button-hierarchy-guidelines.md`）。
- 验证：用 VoiceOver/NVDA 聚焦按钮能读出动作名称；Accessibility Tree 中按钮均有 Name。

#### 8) Navbar 高度硬编码（76px）+ 动态 AppName，窄屏/长名称时可能遮挡内容
- 优先级：P1
- 证据：`app/static/css/global.css:56`（navbar fixed）与 `app/static/css/global.css:129`（main-content margin-top 固定）；AppName 动态更新 `app/templates/base.html:312`
- 影响：在 1024 宽度或 AppName 变长导致导航换行时，页面顶部内容被遮挡；属于明显可感知的布局缺陷。
- 根因：布局对 navbar 高度做了硬编码假设，未做自适应。
- 建议：
  - 短期止血（0.5~2 天）：用 CSS 变量 `--navbar-height` 替代固定 76px，并在 DOMContentLoaded 读取实际高度写入变量；同时限制 `#app-name` 最大宽度并省略号。
  - 中期重构（1~2 周）：将 header 设计成可换行且不会遮挡内容的布局（sticky + padding-top）。
  - 长期规范化（可选）：补写 layout 规范与桌面宽度检查清单（1024/1366/1440/1920）。
- 验证：把窗口调到 1024 并模拟超长 AppName，确保 main-content 顶部不被遮挡。

#### 9) 全局资源加载偏“全量”，登录页/轻量页也承担大量 JS/CSS 成本
- 优先级：P1
- 证据：`app/templates/base.html:246`（全站引入 numeral/mitt/lodash/umbrella/http/dayjs 插件等）；`app/templates/base.html:46`（全站引入 `pages/accounts/privileges.css`）
- 影响：首屏请求数与 JS 解析成本上升；缓存失效时感知更明显；对“快速打开/刷新”体验不利。
- 根因：缺乏“按页依赖声明”的加载机制；页面级 CSS/JS 被放进 base。
- 建议：
  - 短期止血（0.5~2 天）：把明显页面级 CSS（`privileges.css`）移到实际使用页面；Tom Select/部分 dayjs 插件改为按需加载（仅在存在 `data-tom-select` 或需要时间格式化页面加载）。
  - 中期重构（1~2 周）：建立 `page_id -> assets` 映射（registry），由 page-loader 注入（保持无构建前提下的按需加载）。
  - 长期规范化（可选）：引入静态资源版本化与依赖图，避免重复与漂移。
- 验证：比较登录页（未登录）加载的资源数量/总字节数；Lighthouse/Performance 中 TTI 改善；功能页资源仍齐全。

#### 10) 导出/异步任务缺少“进度预期 + 结果入口”的一致闭环
- 优先级：P1
- 证据：实例导出直接跳转 `app/static/js/modules/views/instances/list.js:1078`；批量测试仅 toast `app/static/js/modules/views/instances/list.js:1065`；数据库台账导出 `window.open` 且无失败反馈 `app/static/js/modules/views/databases/ledgers.js:360`；对照：账户台账同步确认提供会话中心入口 `app/static/js/modules/views/accounts/ledgers.js:1108`
- 影响：用户不知道是否已开始/是否在后台跑/去哪看结果；易重复点击；对“系统可理解性”打击明显。
- 根因：缺少“异步任务 UX 模式”的统一规范与通用组件，导致各页面自行实现。
- 建议：
  - 短期止血（0.5~2 天）：导出按钮统一使用 `UI.setButtonLoading` 并 toast 提示“已开始导出”；异步任务确认/成功 toast 统一附加“前往会话中心查看进度”的链接或按钮。
  - 中期重构（1~2 周）：抽象 `UI.taskFeedback()`（支持 request_id/resultUrl），并在服务层返回统一 `request_id`。
  - 长期规范化（可选）：补写异步任务反馈闭环规范与埋点（开始/成功/失败/取消）。
- 验证：触发导出/批量测试/同步后，用户能清晰看到 loading、成功/失败、以及“去哪看结果”；不会重复提交。

### P2

#### 1) 链接默认去下划线，正文/表格场景可发现性下降
- 优先级：P2
- 证据：`app/static/css/theme-orange.css:24`
- 影响：用户更难识别可点击链接（尤其在非按钮式链接、表格详情链接场景）；对色觉缺陷用户更不友好。
- 根因：全局链接样式以“干净”为目标，但未区分“导航链接/正文链接”语义。
- 建议：
  - 短期止血（0.5~2 天）：限定去下划线的范围（例如仅导航/按钮型链接）；正文/详情区域链接恢复 underline 或增加更强的非颜色线索。
  - 中期重构（1~2 周）：建立“链接 vs 按钮”视觉语义规范并落到 CSS 作用域。
  - 长期规范化（可选）：补写链接规范并加入可访问性检查项（非颜色区分）。
- 验证：在正文/详情区域，链接在非 hover 状态也可被快速识别；色盲模拟下仍可区分。

#### 2) FilterCard 操作按钮宽度固定为 50%，点击目标偏小且可能换行
- 优先级：P2
- 证据：`app/static/css/components/filters/filter-common.css:71`
- 影响：在 1024/1366 宽度下 actions 列更窄，按钮面积变小；用户更可能误点/重复点，产生“没点上”的错觉。
- 根因：样式对按钮宽度做了硬编码，未考虑栅格列宽变化。
- 建议：
  - 短期止血（0.5~2 天）：改为 `width: 100%` 或基于容器的自适应；保持桌面端布局不新增移动端 media。
  - 中期重构（1~2 周）：在 FilterCard 规范中约束 actions 区的布局与最小点击面积。
  - 长期规范化（可选）：把 actions 区做成可复用子组件，避免页面 CSS 继续覆盖。
- 验证：在 1024/1366 下按钮不换行、点击面积足够、视觉对齐稳定。

#### 3) 时间展示格式不一致（year/时区/格式混用），排障与对账易误判
- 优先级：P2
- 证据：数据库台账使用 `toLocaleString` 且不含年份 `app/static/js/modules/views/databases/ledgers.js:384`；会话中心使用 `timeUtils.formatDateTime` `app/static/js/modules/views/history/sessions/sync-sessions.js:372`；统一工具已存在 `app/static/js/common/time-utils.js:4`
- 影响：跨年/跨时区时用户可能误判事件先后；定位同步问题更困难。
- 根因：页面脚本未统一使用 `timeUtils`，各自实现日期格式化。
- 建议：
  - 短期止血（0.5~2 天）：统一改为 `timeUtils` 输出（建议包含年份 + 秒 + 明确时区策略）。
  - 中期重构（1~2 周）：文档化时间/数字格式规范，并在 views 层 lint 禁止直接 `new Date().toLocaleString()`。
  - 长期规范化（可选）：对所有时间字段建立展示组件（相对时间 + 悬停绝对时间）。
- 验证：同一时间字段在不同页面表现一致；在系统时区变更/跨年数据下不产生歧义。

#### 4) `--bs-primary-rgb` 为手写值，可能与 `--accent-primary` 漂移导致局部偏色
- 优先级：P2
- 证据：`app/static/css/theme-orange.css:3`；`app/static/css/variables.css:16`
- 影响：依赖 `--bs-primary-rgb` 的 Bootstrap 透明色/阴影可能与当前主色不一致；在更换主题色时更明显。
- 根因：同一语义色存在双来源（OKLCH 主色 vs 手写 RGB）。
- 建议：
  - 短期止血（0.5~2 天）：运行时从 `--accent-primary` 解析出 rgb 写入 `--bs-primary-rgb`，避免漂移。
  - 中期重构（1~2 周）：将 Bootstrap 相关 token 全部指向单一来源（只维护 `accent-primary`）。
  - 长期规范化（可选）：在 token 治理规范中增加“禁止手写 RGB 影子 token”的条款与门禁。
- 验证：修改 `--accent-primary` 后，Bootstrap 透明色/阴影同步变化；不存在“某些组件橙色变两种”的现象。

#### 5) “只读模式”用 `<span class="btn ... disabled">` 伪按钮，语义不清
- 优先级：P2
- 证据：`app/static/js/modules/views/accounts/account-classification/index.js:414`
- 影响：用户可能误以为可点击；读屏不会把它识别为按钮，交互语义混乱。
- 根因：用样式模拟禁用按钮，而非使用语义化元素与 `disabled/aria-disabled`。
- 建议：
  - 短期止血（0.5~2 天）：改为 `<button disabled>` 或显式 `role="button" aria-disabled="true"` 且不可聚焦；并提供可读文本。
  - 中期重构（1~2 周）：建立“只读模式 UI”组件（统一锁 icon + tooltip + 语义）。
  - 长期规范化（可选）：A11y 规范加入“禁止伪按钮元素”条款并做门禁。
- 验证：键盘 Tab 不会聚焦到伪按钮；读屏能正确读出“只读模式（不可用）”或直接跳过。

---

## IV. 最小可执行修复路线图（<= 8 条，每条 0.5~2 天）

1) 修复 `<title>` 策略：动态 AppName 不覆盖页面标题（`app/templates/base.html:291`）。
2) 修复日志中心筛选键名与传参：search/module/hours 全链路一致（模板→JS→后端），并补上清空后的默认时间范围。
3) 修复实例详情“同步账户”成功判定与错误展示：仅 `success===true` 视为成功，并统一提供“会话中心查看进度”入口。
4) A11y 扫描与修复：全站 `btn-icon` 补齐 `aria-label`，装饰图标统一 `aria-hidden="true"`；对照 scheduler 页的正确实现。
5) TagSelector 资源去重：移除组件模板中的 `<link>`，确保 CSS 只在 head 加载一次。
6) FilterCard 统一：迁移 tags/credentials/databases-ledger 到 `UI.createFilterCard`，收敛 debounce/clear/URL 同步策略。
7) Header 高度自适应：用 CSS 变量替代 76px 固定值，并对 `#app-name` 做宽度限制避免换行遮挡内容。
8) 资源按页加载与版本化：把明显页面级 CSS（如 privileges）移出 base；为静态资源引入 build hash（解决缓存一致性与回滚）。

---

## 附加输出：兜底/兼容/回退/适配（前端侧）

> 目标：把“为了兼容而写的兜底”变成可度量、可收敛的迁移路径。建议统一埋点：`EventBus.emit('compat:fallback_hit', { key, path, detail })`，并在控制台/后端聚合命中率，驱动后续移除。

| 位置 | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| `app/static/js/core/http-u.js:214` | 回退 | `resolveErrorMessage()` 使用 `body.message || body.error || ...`，同类错误提示字段不一致会导致文案漂移。 | 后端统一错误 schema；前端对 `body.error` 命中做埋点，逐步移除 `error` 兜底。 |
| `app/static/js/common/csrf-utils.js:69` | 适配 | `data?.csrf_token ?? data?.data?.csrf_token`：CSRF token 位置不稳定。 | 后端固定 token 字段位置；前端记录命中分支（root vs nested），达标后移除 nested 分支。 |
| `app/static/js/modules/views/instances/detail.js:279` | 防御（高风险） | `success || Boolean(message)` 推断成功，可能把失败当成功。 | 严格以 `success===true` 判定；对“message-only”响应埋点并推动后端修复。 |
| `app/static/js/modules/views/instances/list.js:1022` | 兼容 | `response?.message || '批量移入回收站失败'`：message 字段存在与否影响用户看到的错误文案。 | 引入统一 `resolveApiMessage/resolveApiError`；对缺 message 的接口补齐后端。 |
| `app/static/js/modules/views/instances/list.js:1062` | 兼容 | `result?.error || '批量测试失败'`：错误字段使用 `error` 而非 `message`。 | 统一为 `error` schema（error_code + message）；过渡期埋点 `errorFieldUsed`。 |
| `app/static/js/common/grid-wrapper.js:416` | 兼容 | page_size 同时兼容 `pageSize/limit`，并通过 EventBus 发 `pagination:legacy-page-size-param`。 | 保留埋点，统计 legacy 参数来源；后端与前端统一仅接受 `page_size` 后移除兼容。 |
| `app/static/js/modules/stores/sync_sessions_store.js:113` | 兼容 | 分页字段兼容 `page/current_page`、`pages/total_pages`、`has_next/has_more` 等多套命名。 | 统计各字段命中率并制定“只保留一套命名”的迁移计划；达标后删掉次要分支。 |
| `app/static/js/modules/stores/sync_sessions_store.js:156` | 适配 | 列表提取兼容 `payload.sessions ?? payload.items ?? payload`。 | 统一会话列表返回字段（例如 `items`）；前端记录 fallback 命中后移除。 |
| `app/static/js/modules/views/admin/partitions/index.js:398` | 适配 | `response?.data?.data ?? response?.data ?? response`：出现三层嵌套 data。 | 后端统一去掉重复 data 包裹；前端对 `data.data` 命中做告警。 |
| `app/static/js/modules/views/admin/scheduler/index.js:271` | 防御 | `error?.response?.message || error?.message || '网络或服务器错误'`：错误结构不一导致文案不可预测。 | 统一使用 http-u 的 Error 构造与 error.response schema；并区分网络/权限/参数/系统故障文案模板。 |

