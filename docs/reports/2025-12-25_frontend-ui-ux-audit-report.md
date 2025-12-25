# 前端 UI/UX 审计报告（桌面端）- 2025-12-25

> 状态：Draft
> 负责人：WhaleFall FE / UI-UX Audit
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：`app/templates/**`、`app/static/css/**`、`app/static/js/**`（仅桌面端；重点校验 1024/1366/1440/1920）
> 关联：`../standards/documentation-standards.md`；`../standards/ui/README.md`；`../standards/ui/color-guidelines.md`；`../standards/ui/design-token-governance-guidelines.md`；`../standards/ui/pagination-sorting-parameter-guidelines.md`；`../standards/backend/api-response-envelope.md`；`../standards/backend/error-message-schema-unification.md`；`../standards/terminology.md`

## I. 摘要结论（先给结论）

- **整体结论**：当前前端已具备较成熟的“组件化基础设施”（Token、Toast、GridWrapper、DangerConfirm），但在“关键用户路径”的两个核心环节出现明显体验断点：**列表→详情→返回的上下文丢失**、以及**同步类动作的成功/失败判定与文案兜底导致的不可预测反馈**。这两类问题会直接影响效率与信任（用户会反复筛选/重复触发、或误以为成功）。
- **一致性与可访问性**：大量 `btn-icon` 图标按钮仍依赖 `title` 作为提示，缺少可访问名称，导致键盘/读屏体验不达标；同时存在少量 Token 规范破坏（如 `background: white`）与 FilterCard 栅格违规（`col-md-3`）。
- **优先级建议**：先用 0.5~2 天的修复把 P0/P1 的“上下文 + 反馈 + A11y”补齐；再做一次“契约收敛 + 兜底统计 + 逐步删除兜底”的中期治理，避免同类问题反复出现。

## II. 范围与方法

### 范围

- 模板：`app/templates/**`（重点：`app/templates/base.html`、列表页、详情页、模态组件）
- 样式：`app/static/css/**`（重点：`app/static/css/variables.css`、`app/static/css/global.css`、页面样式与组件样式）
- 脚本：`app/static/js/**`（重点：`page-loader`、`core/http-u.js`、`common/grid-wrapper.js`、FilterCard/Toast/DangerConfirm、典型页面入口）
- 典型任务：登录 → 列表筛选 → 查看详情 → 导出/同步 → 查看任务结果

### A. 关键用户路径（Top 5）

1) **登录与账号维护（高频 / 入口链路）**
   - `登录页` → 输入校验/提交 → `进入仪表盘` → `修改密码` → `退出登录`

2) **实例管理闭环（高价值 / 核心资产）**
   - `实例管理列表` → FilterCard 筛选/标签筛选 → 勾选/批量操作 → `查看详情` → 测试连接/同步账户/同步容量 → 移入回收站/恢复 → 返回列表继续操作 → 导出 CSV

3) **台账查询与导出（高频 / 决策支撑）**
   - `账户台账` → 筛选（搜索/分类/标签/DB 类型切换）→ 查看权限 → 导出 CSV → （可选）触发全量同步 → `会话中心` 查看结果

4) **异步任务结果追踪（高价值 / 信任建立）**
   - 触发同步/批量测试 → Toast/状态提示 → `会话中心` 筛选会话 → 打开会话详情 → 复制会话 ID/堆栈 →（可选）取消会话 → `日志中心` 查问题

5) **运维/管理（中频 / 风险高）**
   - `定时任务管理` → 查看运行/暂停 → 重新初始化任务 →（必要时）查看日志中心定位异常

### B. 启发式评审 + 证据取样

- 启发式维度：信息架构与导航、视觉一致性、表单、防错与风险操作、反馈与状态、表格与筛选、可访问性、性能、文案与国际化、前后端契约漂移对 UX 的影响。
- 证据取样原则：每条发现提供可定位证据（文件:行号/组件名/函数名/选择器），并给出短期止血/中期重构/长期规范化建议与验证方法。
- 契约漂移扫描：针对 `||` / `??` / 模板 `or` 等兜底链路进行抽样，评估其对 UX 的风险（文案漂移、错误不可预测、埋雷式成功判定）。

### C. 体验一致性扫描（跨页面一致性）

- 按钮与操作区：主/次/危险按钮在大部分页面已统一使用 Bootstrap 语义类，但**图标按钮（btn-icon）的 a11y 命名不一致**（部分页面有 `aria-label`，多数仅有 `title`）。
- 表单与校验：已存在 JustValidate 封装与统一规则，但**校验失败提示的落点不统一**（有的 toast、有的字段内 invalid-feedback、有的两者混用），容易让用户“到底哪里错了”不明确。
- Toast/Alert：同时存在 Flash Alert（模板渲染）与 Toast（JS），**同类成功/失败反馈的载体不一致**，且错误消息解析存在兜底链路漂移风险。
- Loading/Empty：GridWrapper 有统一 loading/noRecords 文案，但不少页面还有自定义 loading/empty 容器，**空态缺少统一 CTA**（清除筛选/创建入口/去会话中心）。
- 错误分级：部分页面对“可重试/权限不足/参数错误/系统故障”缺少一致分级与下一步引导（多数仅展示一句话）。

### 缺口地图（按 1~9 维度逐条给：缺口描述 + 建议补写的 UI/UX 规范小节标题）

> 说明：`docs/standards/ui/*` 已覆盖部分标准（按钮层级、Token、危险确认、分页参数等），本节列的是“当前实现暴露出的可复用缺口”，建议补写为可门禁的细则。

1) 信息架构与导航
   - 缺口：缺少“当前页高亮/面包屑/返回保持上下文”的统一模式，详情页返回易丢筛选与滚动。
   - 建议补写：`Navigation & Context Patterns（面包屑/返回/高亮/保留筛选）`

2) 视觉层级与一致性（Design Consistency）
   - 缺口：少量页面 CSS 仍出现非 Token 颜色关键字；部分页面 inline style 固定尺寸导致视觉节奏不统一。
   - 建议补写：`No Inline Style for Layout（图表/表格尺寸与密度规范）`

3) 表单与数据录入（效率 + 防错）
   - 缺口：图标按钮/输入组的可访问名称、必填表达、错误提示文案一致性缺少统一清单。
   - 建议补写：`Form Field UX Checklist（必填/校验时机/错误可行动文案）`

4) 反馈与状态（系统可理解性）
   - 缺口：同步/导出等异步动作的“开始/进行中/完成/失败/去哪里看结果”未统一；存在成功判定兜底导致的错误成功提示。
   - 建议补写：`Async Operation Feedback Standard（toast + 结果入口 + 可取消/可重试）`

5) 数据表格与筛选（管理后台核心）
   - 缺口：FilterCard 栅格强约束虽在标准中定义，但缺少门禁；Grid 空状态缺少“下一步行动”组件化支持。
   - 建议补写：`FilterCard Compliance Gate（栅格/控件/清除行为）`、`Empty State Patterns for Lists（空态 CTA）`

6) 可访问性（A11y）
   - 缺口：`btn-icon`、图标按钮、模板 `<i>` 装饰图标缺少统一的 aria 规则与检查点；“读屏友好”的验证流程缺失。
   - 建议补写：`A11y Baseline for Admin UI（按钮命名/焦点/ARIA）`

7) 性能与体验（感知性能）
   - 缺口：base 全局脚本加载较重（dayjs 多插件、tom-select 等），缺少“按页面加载预算/拆分策略”的规范与测量口径。
   - 建议补写：`Frontend Performance Budget（全局依赖白名单 + 页面按需加载）`

8) 文案与国际化（体验细节）
   - 缺口：术语存在轻微漂移（禁用/停用）；时间展示虽固定时区但未显式提示，跨团队协作有歧义风险。
   - 建议补写：`Microcopy & Timezone Display Standard（术语/时区/单位）`

9) 前后端契约漂移对 UX 的影响（重点）
   - 缺口：前端多处 `||/??` 兜底解析（message/error/data 互兜底、字段别名），短期止血有效但长期会造成“错误提示漂移/成功判定不可信”。
   - 建议补写：`API Contract Drift Playbook（兜底命中统计 → 收敛 → 移除）`

### D. 最小可执行修复路线图

- 本次审计的“最小可执行修复路线图”已整理在 **IV. 建议与后续行动**（每项 0.5~2 天，最多 8 项）。

## III. 发现清单（按 P0/P1/P2）

### P0

#### P0-01 列表 → 详情 → 返回丢上下文（筛选条件/回收站视图/滚动）导致反复操作与误操作风险

- 证据：
  - `app/templates/instances/detail.html:151`（返回列表链接固定指向实例列表，无任何 return_to/query 透传）
  - `app/static/js/modules/views/instances/detail.js:377`（删除后跳转硬编码 `/instances`，同样丢失上下文）
  - `app/static/js/modules/views/instances/list.js:559`（进入详情的链接不携带当前筛选 URL，用“返回列表”无法复原上下文）
- 影响：用户完成“筛选→进入详情→处理→返回继续处理”时，必须重新筛选/重新定位；在高频批处理场景会显著降低效率，并提高对错误对象操作的概率（丢上下文）。
- 根因：缺少统一的“列表上下文携带策略”（return_to 参数、sessionStorage、History state），详情页/跳转逻辑以固定 URL 为主。
- 建议：
  - 短期止血（0.5~2 天）：详情入口统一追加 `return_to=<encodeURIComponent(location.href)>`；详情页“返回列表”和删除后重定向优先使用 `return_to`，否则回退到列表页默认 URL。
  - 中期重构（1~2 周）：抽象 `BackLink`/`return_to` 组件与工具（解析/白名单校验/防开放重定向），覆盖所有“列表→详情/模态→返回”链路。
  - 长期规范化（可选）：把“上下文保留”写入 UI 标准并加门禁（例如：详情页必须支持 return_to；列表页必须把当前 URL 透传给详情入口）。
- 验证：
  - 手动用例：在 `实例管理` 设置搜索/标签/状态筛选并勾选“显示已删除”，进入任一详情 → 点击“返回列表”/执行“移入回收站”后返回，应保持筛选与回收站视图。
  - 截图对比：同一实例从列表进入详情前后，返回列表的筛选区与 Grid 状态保持一致（至少 URL query 一致）。

#### P0-02 “同步账户”成功判定存在兜底误判：失败也可能展示成功（信任断裂）

- 证据：`app/static/js/modules/views/instances/detail.js:280`（`const isSuccess = data?.success || Boolean(data?.message);` 以 message 存在作为成功信号）
- 影响：后端返回 `{success:false, message:"xxx"}` 或“失败但带 message”时，用户可能收到成功 Toast；这会直接损害对平台的信任，并造成误决策（以为已同步、实际上未同步）。
- 根因：前后端 JSON 封套/错误 schema 未完全收敛，前端用启发式兜底（message 存在即成功）弥补契约漂移。
- 建议：
  - 短期止血（0.5~2 天）：成功判定只接受 `success === true`；失败路径优先展示统一错误字段（对齐 `../standards/backend/api-response-envelope.md`），不要用 message 兜底成功。
  - 中期重构（1~2 周）：抽象统一的 `resolveApiResult`（成功/失败/可恢复/建议）并替换页面散落的判定逻辑；对“兜底命中”打点（如 `EventBus.emit('api:fallback-hit', {...})`）。
  - 长期规范化（可选）：制定“兜底退场机制”（埋点阈值/告警/删除计划），将兜底从“永久代码”变为“可观测的临时兼容层”。
- 验证：
  - 手动/Mock：模拟接口返回 `success:false,message:"权限不足"`，页面必须展示失败 Toast 且提供下一步（如去会话中心/日志中心）。
  - 指标：统计 “success=false 但 message 存在” 的兜底命中率，持续下降并最终清零。

### P1

#### P1-01 PageHeader 的 description 参数未渲染，导致“我能做什么”信息缺失（信息架构/引导不足）

- 证据：
  - `app/templates/components/ui/page_header.html:1`（macro 接收 `description` 但未输出任何描述节点）
  - `app/static/css/global.css:255`（存在 `.page-header__title p` 样式，实际模板未生成对应元素）
- 影响：用户进入页面只能看到标题，不易快速理解该页面的目的/关键操作；新用户学习成本上升，容易依赖反复点击探索。
- 根因：组件模板与样式/调用方参数不一致（实现缺口）。
- 建议：
  - 短期止血（0.5~2 天）：在 PageHeader 中当 `description` 存在时渲染 `<p>`；并补齐 `aria`（装饰图标 `aria-hidden`）。
  - 中期重构（1~2 周）：统一 PageHeader 的“标题 + 描述 + 主操作”结构（变体/密度），形成可复用规范。
  - 长期规范化：将 PageHeader 作为“信息架构基座组件”写入 UI 标准（含示例与禁用模式）。
- 验证：对比修复前后 `实例管理/账户台账/数据库台账/会话中心` 等页头是否出现一致的描述文本与对齐方式。

#### P1-02 FilterCard 栅格强约束被破坏（账户台账标签筛选 col-md-3），造成筛选区一致性风险

- 证据：`app/templates/accounts/ledgers.html:34`（`tag_selector_filter(... col_class='col-md-3 col-12')`，违反 `../standards/ui/color-guidelines.md` 的 FilterCard 约束）
- 影响：筛选区的布局与其他列表页不一致；在 1024/1366 宽度下更容易出现不对齐/换行不可预测，降低“扫一眼就会用”的熟悉感。
- 根因：局部页面为适配控件占用而突破栅格规则，缺少门禁/例外流程。
- 建议：
  - 短期止血（0.5~2 天）：改回 `col-md-2 col-12`；如确需更宽，改为“组件内部自适应”（例如按钮/预览区断行）而不是改栅格。
  - 中期重构（1~2 周）：新增门禁脚本或 CI 检查（扫描 `filter_card` 区域内是否存在非 `col-md-2 col-12`/像素宽度）。
  - 长期规范化：在标准中明确“允许突破的唯一场景 + 评审要求 + 退场机制”。
- 验证：在 1024/1366/1440/1920 四档宽度下截图比对筛选区单行对齐、控件高度一致性。

#### P1-03 图标操作按钮（btn-icon）缺少可访问名称（aria-label），依赖 title，读屏/键盘体验不达标

- 证据（抽样）：
  - `app/static/js/modules/views/instances/list.js:559`（查看详情/测试连接图标按钮无 `aria-label`）
  - `app/static/js/modules/views/credentials/list.js:201`（编辑/删除图标按钮无 `aria-label`）
  - `app/templates/history/sessions/detail.html:15`（复制会话 ID 图标按钮无 `aria-label`）
- 影响：屏幕阅读器无法准确朗读按钮用途；键盘用户难以在无悬浮提示时理解当前焦点；可访问性与可用性同时下降。
- 根因：缺少对 `btn-icon` 的统一组件约束与门禁（部分页面已做，如 `app/static/js/modules/views/admin/scheduler/index.js:544` 具备 aria-label，说明标准未覆盖到全局）。
- 建议：
  - 短期止血（0.5~2 天）：给所有 `btn-icon` 补齐 `aria-label`；装饰性 `<i>` 统一加 `aria-hidden="true"`。
  - 中期重构（1~2 周）：封装生成操作按钮的 helper（保证 title/aria-label 同步）；对新增 `btn-icon` 做 lint/扫描门禁。
  - 长期规范化：补写 “Icon Button 可访问名称” 检查清单，纳入 PR 模板与自动化检测（axe）。
- 验证：使用键盘 Tab 遍历所有列表页操作列；用读屏（VoiceOver/NVDA）确认按钮朗读内容与业务含义一致。

#### P1-04 Navbar 在窄窗口（<992）会折叠但缺少 toggler，导致导航不可达（桌面分屏场景会踩坑）

- 证据：`app/templates/base.html:62`（存在 `collapse navbar-collapse` 容器，但模板中无 `navbar-toggler` 按钮）
- 影响：当用户在桌面端分屏/缩窄窗口（仍属于桌面使用场景）时，导航可能折叠且无法展开，用户被“困在当前页”。
- 根因：Bootstrap Navbar 结构不完整（缺少 toggler 触发器与 aria 关联）。
- 建议：
  - 短期止血（0.5~2 天）：补齐 `navbar-toggler`（绑定 `data-bs-target="#navbarNav"`，并设置 `aria-controls/aria-expanded/aria-label`）。
  - 中期重构（1~2 周）：补写导航的“桌面窄宽度策略”（允许折叠但必须可用；或固定不折叠）。
  - 长期规范化：把导航可用性纳入 UI 回归清单（1024/900 分屏）。
- 验证：将浏览器宽度缩到 ~900px（桌面分屏），确认可打开导航并可访问全部菜单项。

#### P1-05 错误提示口径分散：`message || error || fallback` 兜底链导致同类错误提示漂移（不可预测）

- 证据（抽样）：
  - `app/static/js/core/http-u.js:214`（`body.message || body.error || ...`）
  - `app/static/js/modules/views/components/connection-manager.js:61`（错误消息从 `response.message`/`error.message` 多路兜底）
  - `app/static/js/modules/views/instances/detail.js:281`（`data?.message || data?.data?.result?.message`）
- 影响：同类错误在不同页面展示不同文案；用户无法形成稳定心智模型（“这次失败到底是权限、参数还是系统故障？”），支持与排障成本增加。
- 根因：前后端错误 schema 未完全收敛；前端多点解析，缺少统一的错误展示策略（与 `../standards/backend/api-response-envelope.md` 目标不一致）。
- 建议：
  - 短期止血（0.5~2 天）：统一走一个前端 `resolveUnifiedError()`（优先读取封套字段：`message_code/recoverable/suggestions`），页面仅展示“可行动摘要”。
  - 中期重构（1~2 周）：对所有兜底点加“兜底命中统计”（EventBus/日志上报），并对命中率高的接口优先修后端返回结构。
  - 长期规范化：建立“兜底退场”流程（阈值/告警/清理计划），避免兜底永久存在。
- 验证：构造 4 类错误（参数错/权限不足/系统故障/可重试），在实例/台账/会话中心触发，检查文案与动作（重试/联系管理员/查看会话）一致。

#### P1-06 设计 Token 规范破坏：页面样式出现 `background: white`，存在主题一致性与未来扩展风险

- 证据：`app/static/css/pages/auth/change-password.css:22`（硬编码 `background: white;`）
- 影响：当主题/Token 调整（或引入暗色模式）时，该页面容易出现“白块突兀/对比不一致”；也违反“颜色来源统一 Token”的约束（见 `../standards/ui/color-guidelines.md`）。
- 根因：页面样式未完全遵循 Token 输出（或历史遗留）。
- 建议：
  - 短期止血（0.5~2 天）：替换为 `background: var(--surface-elevated);` 并补齐必要的对比度检查。
  - 中期重构（1~2 周）：补充“禁止颜色关键字/HEX/RGB” 的门禁（目前 Token 门禁主要覆盖 var 引用是否存在，未覆盖硬编码）。
  - 长期规范化：把“颜色硬编码扫描”纳入代码审查脚本与 PR 门禁。
- 验证：对比修改前后页面在默认主题下视觉一致；并通过搜索确认该页面无硬编码颜色关键字残留。

#### P1-07 base 全局脚本加载偏重，影响首屏与交互响应（感知性能风险）

- 证据：`app/templates/base.html:246`（全局加载 `dayjs` 多插件、`tom-select`、`lodash` 等；即使页面不使用也会下载/解析）
- 影响：冷启动/弱设备下 TTI 变慢；“点了没反应”的风险增加；同时增加长期维护成本（全局依赖难以瘦身）。
- 根因：依赖以“全站可用”为目标而非“按需加载”；缺少性能预算与白名单。
- 建议：
  - 短期止血（0.5~2 天）：把 Tom Select/JustValidate 等移到确实需要的页面（extra_js）或做惰性初始化（检测到 `data-tom-select` 再加载）。
  - 中期重构（1~2 周）：定义“全局基础依赖白名单”与“页面依赖清单”，并在构建/部署中输出资源体积报告。
  - 长期规范化：建立性能预算（总 JS 体积、首屏请求数、解析耗时阈值）与回归检查流程。
- 验证：用浏览器 Performance/Network 对比调整前后首屏脚本请求数与解析耗时；确保页面功能不回归。

#### P1-08 同步/批量动作失败路径缺少兜底反馈：success=false 且无 error 时可能静默（“我刚做了什么？”不可回答）

- 证据（抽样）：
  - `app/static/js/modules/views/instances/detail.js:424`（仅处理 `data.success` 或 `data.error`，否则无提示）
  - `app/static/js/modules/views/accounts/ledgers.js:1033`（仅处理 `result?.success` 或 `result?.error`，否则无提示）
- 影响：用户触发同步后可能没有任何反馈（既不成功也不失败提示），导致重复点击/重复触发任务，增加系统负载与用户焦虑。
- 根因：接口返回结构不稳定 + 前端未对“不满足预期封套”的情况给出兜底提示与引导。
- 建议：
  - 短期止血（0.5~2 天）：在 else 分支统一 toast：`操作未完成，请稍后在会话中心确认`，并附带入口链接（会话中心）。
  - 中期重构（1~2 周）：统一用封套字段（success/error/recoverable/suggestions）驱动反馈与 CTA。
  - 长期规范化：为“异步任务”建立统一 UI 模式（开始→进行中→结果入口→失败可重试）。
- 验证：触发同步后，无论返回结构如何，用户都能得到明确反馈与下一步入口；并能在会话中心找到对应记录。

### P2

#### P2-01 TagSelectorFilter 使用固定 DOM id（open-tag-filter-btn/selected-tag-names），未来扩展到多筛选器会冲突

- 证据：`app/templates/components/filters/macros.html:156`（按钮 id 固定为 `open-tag-filter-btn`，hidden input id 固定为 `selected-tag-names`）
- 影响：一旦某页面出现多个标签筛选器（或复用组件到表格内/多卡片），会出现事件绑定错位、label for 指向冲突、测试不稳定等问题。
- 根因：组件未做 scope 化（id 未与 `field_id` 绑定）。
- 建议：
  - 短期止血（0.5~2 天）：将 id 改为 `${field_id}-open`、`${field_id}-selected` 等，并在 JS 侧按容器 `data-tag-selector-scope` 查询。
  - 中期重构（1~2 周）：把 TagSelectorFilter 的 DOM 结构固化为可复用组件（避免外部依赖固定 id）。
  - 长期规范化：为“组件必须无全局固定 id”设立标准与门禁。
- 验证：在同一页面渲染两个 tag_selector_filter，确认互不干扰（打开/选中/清除/提交均正确）。

#### P2-02 Grid 空状态文案过于终止式（“未找到记录”），缺少下一步行动（清除筛选/创建入口）

- 证据：`app/static/js/common/grid-wrapper.js:93`（`noRecordsFound: "未找到记录"`；无 CTA/引导）
- 影响：用户在空结果时不知道下一步（清除筛选？扩大时间范围？去创建标签/实例？）；会增加试错与学习成本。
- 根因：空态作为“纯文案”而非“可行动组件”处理。
- 建议：
  - 短期止血（0.5~2 天）：在各列表页检测到空结果时增加一行提示（例如 FilterCard 下方 `空结果：建议清除筛选` + 清除按钮）。
  - 中期重构（1~2 周）：为 GridWrapper 增加可注入的 EmptyState renderer（可按页面自定义 CTA）。
  - 长期规范化：沉淀“空态模板库”（无结果/无数据/无权限/系统故障）。
- 验证：设置筛选条件无结果时，页面出现明确引导与一键清除；并在清除后能恢复到有数据状态。

#### P2-03 会话中心 30s 自动刷新缺少显式开关/暂停策略，可能打断阅读与复制（感知体验抖动）

- 证据：`app/static/js/modules/views/history/sessions/sync-sessions.js:32`（`AUTO_REFRESH_INTERVAL = 30000`，默认开启）
- 影响：用户查看/复制会话详情时，列表可能刷新导致焦点/滚动/选择状态变化；“我正在看什么”被打断。
- 根因：自动刷新缺少“用户控制”和“场景暂停”（如打开详情 modal 时）。
- 建议：
  - 短期止血（0.5~2 天）：增加“自动刷新”开关（默认开），并在详情 modal 打开时暂停刷新。
  - 中期重构（1~2 周）：将自动刷新与“进行中会话”状态绑定（仅 running 时刷新；completed 后停止）。
  - 长期规范化：统一“后台任务页面”的刷新策略标准（可预测、可控、可暂停）。
- 验证：打开详情 modal 后不再刷新；关闭 modal 恢复；running 会话结束后自动刷新停止或降频。

#### P2-04 时间展示固定 Asia/Shanghai 但 UI 未显式标注时区，跨时区协作存在误读风险

- 证据：`app/static/js/common/time-utils.js:4`（`const TIMEZONE = "Asia/Shanghai";`）
- 影响：在跨团队/跨地区协作或日志对齐场景，用户可能将时间误解为本地时区，导致错误判断（何时触发、持续多久）。
- 根因：时区被作为实现细节隐藏，缺少 UI 层显式提示。
- 建议：
  - 短期止血（0.5~2 天）：在“会话中心/日志中心/详情面板”增加时区徽标（如 `UTC+8 Asia/Shanghai`）。
  - 中期重构（1~2 周）：允许在用户设置中切换显示时区（保持后端 timestamp 不变）。
  - 长期规范化：形成“时间展示规范”（格式、时区、相对时间/绝对时间切换）。
- 验证：会话列表与详情中展示的时间均带时区标识；对同一 timestamp 在不同页面显示一致。

#### P2-05 图表/表格存在 inline style 固定尺寸（px），导致页面节奏不可调且在 1366×768 下更易“首屏挤压”

- 证据（抽样）：
  - `app/templates/capacity/databases.html:94`（canvas `style="height: 550px; width: 100%;"`）
  - `app/templates/admin/partitions/charts/partitions-charts.html:19`（容器 `style="height: 400px;"`）
- 影响：固定高度导致首屏信息密度不可控；在常见桌面高度（如 768）下，用户需要更频繁滚动，降低效率。
- 根因：布局尺寸未纳入 Token/组件体系，使用 inline style 快速落地但难以统一治理。
- 建议：
  - 短期止血（0.5~2 天）：改为 CSS class + `clamp()` 或基于视口高度的变量（仍保持桌面端，无需移动端适配）。
  - 中期重构（1~2 周）：沉淀“图表容器高度规范”（不同页面/不同图表密度）并抽组件。
  - 长期规范化：禁止关键布局使用 inline style，纳入门禁（扫描 `style="...px"`）。
- 验证：在 1366×768 与 1440×900 下对比首屏可见信息量与滚动次数；确认图表不溢出且可读。

#### P2-06 术语轻微漂移（禁用 vs 停用）增加认知负担与误解成本

- 证据：
  - `app/static/js/modules/views/instances/list.js:501`（实例状态使用“禁用”）
  - `app/templates/tags/index.html:52`（标签状态使用“停用标签”）
- 影响：用户会尝试推断“禁用”和“停用”是否不同语义（权限/软删/不可用），增加学习成本。
- 根因：缺少对“可见文案”的集中审查与术语门禁（见 `../standards/terminology.md` 的目标，但未细化到状态词）。
- 建议：
  - 短期止血（0.5~2 天）：统一状态词（择一：禁用/停用），并全站替换。
  - 中期重构（1~2 周）：把状态词加入术语表与 UI 标准，避免再引入同义词。
  - 长期规范化：在 PR 检查中加入“术语扫描/字典”提示。
- 验证：全站同一语义状态只出现一种词；搜索仓库确认无残留混用。

### 兜底/兼容/回退/适配（前端侧）

> 目的：列出会影响 UX 预测性的关键兜底点（尤其是 `||/??/or` 兜底），并给出“收敛契约/渐进移除兜底”的策略建议（含埋点统计命中率）。

| 位置（文件:行号） | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| `app/static/js/core/http-u.js:214` | 兼容/防御 | 错误消息解析使用 `body.message || body.error || ...` 兜底，容易掩盖后端错误 schema 漂移，导致同类错误提示不一致 | 对齐 `../standards/backend/api-response-envelope.md` 与 `../standards/backend/error-message-schema-unification.md`；在兜底命中时打点并逐步移除旧字段兜底 |
| `app/static/js/modules/views/instances/detail.js:280` | 兼容（高风险） | `success || Boolean(message)` 将 message 作为成功信号，可能把失败当成功（直接 UX 信任风险） | 立即移除该兜底；只接受 `success===true`；并对“success 缺失/类型错误”打点告警 |
| `app/static/js/modules/views/components/connection-manager.js:61` | 兼容/防御 | 连接测试错误从 `response.message`/`error.message`/默认文案多路兜底，可能暴露技术细节或产生漂移 | 统一通过 httpU 的错误结构 + 统一错误展示层；对 `error.message` 直出做分级（可行动摘要 + 详情） |
| `app/static/js/common/grid-wrapper.js:416` | 兼容/回退 | 分页参数兼容 `pageSize/limit` 并 emit `pagination:legacy-page-size-param`（良性兼容 + 可观测） | 保留埋点并推动后端/前端链接逐步清零旧字段；在命中率为 0 后删除兼容分支 |
| `app/static/js/modules/views/instances/list.js:654` | 兼容 | filter 字段 `search || q` 兼容旧参数，说明筛选字段存在历史别名 | 统计 `q` 命中率；对外只保留 `search`；在后端与前端同步清理旧参数 |
| `app/static/js/modules/views/components/tags/tag-selector-view.js:230` | 兼容 | 分类数据 shape 兼容对象/数组（`item.value/name/[0]`），意味着接口返回不统一 | 收敛后端返回结构（固定为 `{value,label,count}`）；在兜底命中时记录日志/告警并制定清理计划 |
| `app/static/js/modules/ui/danger-confirm.js:34` | 兼容 | `request_id || requestId` 兼容两种字段命名 | 统一为 `request_id`；埋点统计 `requestId` 命中率并清理 |
| `app/templates/base.html:205` | 兼容 | Flash message 的 category 把 `error` 映射为 `danger`（历史兼容），icon 也跟随兜底 | 统一后端 flash category 枚举；前端保留映射但添加命中统计，逐步清理旧 category |
| `app/static/css/variables.css:9` | 兼容 | CSS Token 兼容别名 `--surface-default`/`--text-secondary` | 统计旧 Token 引用位置并逐步替换；在清理完成后移除别名并更新门禁 |

## IV. 建议与后续行动

### 最小可执行修复路线图（0.5~2 天/项，最多 8 项）

1) **补齐“返回保持上下文”机制**：实例列表 → 详情的入口增加 `return_to`，详情页返回/删除后重定向优先回到 `return_to`（覆盖 P0-01）。
2) **修复同步类动作的成功/失败判定与反馈闭环**：移除 `success||message`；失败统一落到可行动摘要 + 会话中心入口；并补齐“未知结构”兜底提示（覆盖 P0-02、P1-08）。
3) **A11y 快速修补（btn-icon）**：全站扫描 `btn-icon`，补齐 `aria-label` 与装饰 icon `aria-hidden`；补齐登录页密码显隐按钮的可访问名称与状态（覆盖 P1-03）。
4) **修复 FilterCard 栅格违规并加门禁**：将账户台账标签筛选改回 `col-md-2 col-12`；新增脚本扫描 FilterCard 中的栅格/像素宽度违规（覆盖 P1-02）。
5) **修复 PageHeader 描述缺失并建立页面引导统一样式**：PageHeader 渲染 description；对关键页面补齐“页面目的/只读模式提示/主操作”一致表达（覆盖 P1-01）。
6) **性能减负（先砍最贵的全局依赖）**：把 Tom Select/JustValidate/dayjs 插件从 base 挪到按需加载；输出一次“首屏资源体积与请求数”基线（覆盖 P1-07）。
7) **空态/错误态组件化**：为 Grid 列表提供可注入 EmptyState（含清除筛选/创建入口）；统一“加载失败”与“无结果”的下一步动作（覆盖 P2-02）。
8) **时间与术语一致性补齐**：在会话/日志相关页面标注时区；统一“禁用/停用”等状态词，并更新 `../standards/terminology.md`（覆盖 P2-04、P2-06）。

### UI 规范/组件规范缺口清单（建议补写成文档/规范，避免同类问题反复）

- Icon Button 标准：`btn-icon` 必须有 `aria-label`、禁用态、危险态与 tooltip 规则。
- Navigation & Context：面包屑/当前页高亮/return_to/保持筛选与滚动的位置策略（含安全白名单）。
- Async Operation Feedback：同步/导出/批量任务的反馈闭环与结果入口（会话中心/日志中心），以及失败可重试策略。
- Empty State Patterns：无数据/无结果/无权限/系统故障的空态模板与 CTA 规范。
- Performance Budget：全局依赖白名单、页面按需依赖、资源体积阈值与回归检查流程。
- API Contract Drift Playbook：兜底点登记、命中率统计、告警与清理计划模板。

## V. 证据与数据来源

- 代码与模板（抽样清单）：
  - `app/templates/base.html`（导航、全局脚本、flash message）
  - `app/templates/components/ui/page_header.html`、`app/static/css/global.css`
  - `app/templates/instances/list.html`、`app/static/js/modules/views/instances/list.js`
  - `app/templates/instances/detail.html`、`app/static/js/modules/views/instances/detail.js`
  - `app/templates/accounts/ledgers.html`、`app/static/js/modules/views/accounts/ledgers.js`
  - `app/static/js/core/http-u.js`、`app/static/js/common/grid-wrapper.js`
  - `app/templates/history/sessions/detail.html`、`app/static/js/modules/views/history/sessions/sync-sessions.js`
  - `app/static/css/pages/auth/change-password.css`
- 标准文档（作为判定依据）：
  - `../standards/documentation-standards.md`
  - `../standards/ui/color-guidelines.md`、`../standards/ui/design-token-governance-guidelines.md`
  - `../standards/ui/pagination-sorting-parameter-guidelines.md`
  - `../standards/backend/api-response-envelope.md`、`../standards/backend/error-message-schema-unification.md`
  - `../standards/terminology.md`
- 可复现的检索方式（示例）：
  - `rg -n \"btn-icon\" app/static/js/modules/views`
  - `rg -n \"filter_card\\(\" app/templates`
  - `rg -n \"\\|\\||\\?\\?\" app/static/js/core app/static/js/modules`
  - `rg -n \"style=\\\"[^\\\"]*\\b\\d+px\\b\" app/templates`
