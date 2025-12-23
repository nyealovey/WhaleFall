# 前端 UI/UX 查漏补缺审计报告（静态审计）— 2025-12-20

范围（仓库本地实现）：
- 模板：`app/templates/**`
- 样式：`app/static/css/**`（重点：`app/static/css/variables.css`、components/pages）
- 脚本：`app/static/js/**`（重点：page-loader、`core/http-u.js`、common 组件、各页面入口）

说明：
- 本报告以“用户能感知到”的体验问题为主，采用启发式评审 + 代码证据取样；未进行浏览器实机走查/网络抓包，因此“表现层”结论以实现推断为主，均给出可定位证据，便于你本地复现核对。
- 约束已遵守：仅桌面端视角（重点关注 1024/1366/1440/1920），不提出新增移动端 `@media` 适配；颜色一致性以 token/`variables.css` 为准；`filter_card` 栅格规范专项检查已覆盖。



II. “缺口地图”：按上述 1~9 维度逐条给：缺口描述 + 我应该补写的 UI/UX 规范小节标题

1) 信息架构与导航
- 缺口描述：顶部导航缺少“当前位置”提示（当前页高亮/aria-current），且缺少面包屑/返回策略统一；列表→详情→返回存在“丢上下文”。
- 我应该补写的 UI/UX 规范小节标题：**导航与定位：当前页高亮、面包屑、返回与上下文保留**

2) 视觉层级与一致性（Design Consistency）
- 缺口描述：全局按钮样式覆盖导致 outline 按钮边框被抹掉，主次/危险层级弱化；同一组件（`status-pill`、`btn-icon`）在多个页面 CSS 重复定义，尺寸/边框/颜色不一致；存在模板内联手写颜色，绕开 token。
- 我应该补写的 UI/UX 规范小节标题：**按钮层级与状态：主/次/危险/禁用/加载态**；**组件外观基线：status-pill、chip、btn-icon**；**颜色与 Token 使用规范（禁止手写色）**

3) 表单与数据录入（效率 + 防错）
- 缺口描述：表单控件的“必填/校验/错误提示”虽有工具链（JustValidate），但各页面对“提交中/失败/成功”的反馈方式不统一；高风险操作的确认/影响范围提示不一致。
- 我应该补写的 UI/UX 规范小节标题：**表单校验与错误文案规范**；**危险操作确认规范（范围/二次确认/可撤销）**

4) 反馈与状态（系统可理解性）
- 缺口描述：长耗时/异步任务（同步/批量操作）缺少“进度 + 结果入口”闭环；错误提示受契约漂移影响，同类错误在不同页面呈现不一致；空状态缺少“下一步”引导（如清除筛选）。
- 我应该补写的 UI/UX 规范小节标题：**Loading/Toast/Alert/Empty/Error 统一规范**；**异步任务反馈闭环：提交→进度→结果→重试/取消**

5) 数据表格与筛选（管理后台核心）
- 缺口描述：FilterCard 有规范，但存在栅格违规；分页参数命名（`page_size` vs `limit`）不统一，URL 可分享性与实际表格分页可能不一致；表格操作列大量图标按钮但可访问名称不足；“复制 ID/字段”能力不体系化。
- 我应该补写的 UI/UX 规范小节标题：**表格规范：列密度/固定列/复制/空状态/分页**；**筛选条（FilterCard）布局与交互规范**；**导出/同步交互规范（进度/耗时预期/结果入口）**

6) 可访问性（A11y）
- 缺口描述：图标按钮普遍只有 `title` 无 `aria-label`；`btn-close` 的可访问名称不一致（缺失/英文/中文混用）；`role="listbox"` 场景缺少键盘交互约束；缺少全站“跳到主内容”。
- 我应该补写的 UI/UX 规范小节标题：**无障碍基线：语义化、可访问名称、焦点可见、键盘可达**；**图标按钮与关闭按钮 A11y 规范**

7) 性能与体验（感知性能）
- 缺口描述：`base.html` 全站加载大量 JS/插件与部分页面 CSS，且存在每页额外请求（app-info）；`GridWrapper` 存在调试 `console.log` 与侵入式刷新逻辑，可能造成卡顿/噪音。
- 我应该补写的 UI/UX 规范小节标题：**资源加载策略与性能预算（按页加载/缓存/版本化）**；**调试日志与环境开关规范**

8) 文案与国际化（体验细节）
- 缺口描述：中英文混用（如关闭按钮 aria-label）；术语（禁用/停用/锁定）在不同模块不一致；时间格式存在 `MM/DD` 等非中文语境格式；错误提示有技术化倾向。
- 我应该补写的 UI/UX 规范小节标题：**文案风格指南（动词、语气、错误可行动性）**；**术语表（状态/操作名统一）**；**时间/数字/单位格式规范**

9) 前后端契约漂移对 UX 的影响（重点）
- 缺口描述：前端大量使用 `message || error`、`response?.data || response`、`csrf_token ?? data.csrf_token` 等兜底；导致同类错误/成功提示漂移、成功判定不可靠，且难以定位后端不一致根因。
- 我应该补写的 UI/UX 规范小节标题：**API 返回 Schema 与错误规范（success/data/message/error）**；**前端解析策略与渐进移除兜底（含埋点与告警）**

C. 进行“体验一致性扫描”（证据取样）
- 按钮层级：outline 体系被全局覆盖，弱化主次/危险识别（2025-12-20 审计时 `app/static/css/global.css` 存在 `.btn { border: none; }`）。
- 图标按钮（btn-icon）：多处重复定义尺寸与边框，表现不一致（`app/static/css/components/tag-selector.css:290`、`app/static/css/pages/instances/list.css:141`、`app/static/css/pages/credentials/list.css:103`）。
- 状态标签（status-pill）：多处重复定义且 token 不一致；部分页面引用未定义变量导致样式失效（`app/static/css/pages/history/logs.css:60`、`app/static/css/pages/accounts/ledgers.css:102`、`app/static/css/variables.css:96`）。
- 关闭按钮：alert/scheduler/modal 的可访问名称缺失或英文混用（`app/templates/base.html:199`、`app/templates/admin/scheduler/modals/scheduler-modals.html:9`、`app/templates/components/ui/modal.html:6`）。
- Loading：按钮/模态的 loading 逻辑分散且文案不统一（`app/static/js/modules/views/auth/login.js:128`、`app/static/js/modules/views/instances/list.js:1212`、`app/static/js/modules/ui/modal.js:91`）。
- 错误提示解析：同类错误字段推断链条不一致，导致文案漂移（`app/static/js/core/http-u.js:214`、`app/static/js/modules/views/instances/detail.js:262`、`app/static/js/modules/views/components/permissions/permission-viewer.js:142`）。

---

III. “UI/UX 问题清单”（按 P0/P1/P2 分组；每条包含）

### P0

1) Outline/次按钮“看起来不像按钮”，全站层级被削弱
- 证据（2025-12-20 审计时）：`app/static/css/global.css` 曾存在 `.btn { ... border: none; }`，会覆盖 Bootstrap 的 outline 边框体系；典型使用：`app/templates/instances/detail.html:145`（多处 `btn-outline-secondary` 作为次按钮/快速操作）
- 影响：主次/危险操作区分度下降，用户更依赖记忆而非视觉识别；误点风险上升（尤其是“返回/同步/删除”等并列）。
- 根因：实现（全局样式覆盖）+ 一致性（未对 Bootstrap 按钮体系做约束评审）。
- 建议：
  - 短期止血（0.5~1 天）：移除或收窄 `.btn { border: none; }`（至少不要覆盖 `btn-outline-*`）；补齐 outline 默认态边框与 hover/focus 一致表现。
  - 中期重构（1~2 周）：建立“按钮层级 token/变量 + 组件类”并在模板中按语义选型（primary/secondary/danger/link/icon）。
  - 长期规范化：补写“按钮层级与状态”规范，并加入 lint/审查项（禁止全局覆盖破坏组件语义）。
- 落地（2025-12-23）：
  - 短期：恢复 `btn-outline-*` 的边框语义；次按钮在默认态可一眼识别为“可点击按钮”。
  - 中期：新增 `app/static/css/components/buttons.css`，用 token 覆盖 Bootstrap 按钮变量，统一主/次/危险按钮的状态表现。
  - 长期：新增规范 `docs/standards/button-hierarchy-guidelines.md`，并提供门禁脚本 `scripts/code_review/button_hierarchy_guard.sh` 防止回归。
- 验证：
  - 手动：在 1024/1366/1440/1920 宽度下对比“次按钮/危险按钮/图标按钮”默认态是否可一眼区分。
  - A11y：键盘 Tab 聚焦时 outline/secondary 按钮是否有清晰 focus ring。

2) 高风险操作缺少二次确认与影响范围提示（可能造成误操作/资源冲击）
- 证据（2025-12-20 审计时）：实例列表“批量删除”直接触发（无二次确认/范围说明）；账户台账“同步所有账户”直接触发（无二次确认/范围说明）。定位：`app/templates/instances/list.html`、`app/static/js/modules/views/instances/list.js`、`app/templates/accounts/ledgers.html`、`app/static/js/modules/views/accounts/ledgers.js`
- 影响：误触即提交任务（删除/同步），用户缺少“影响范围/不可撤销/耗时预期”，降低信任；对后台资源可能造成突发压力。
- 根因：交互设计缺失（危险操作模板未统一）+ 实现（页面各自处理）。
- 建议：
  - 短期止血（0.5~2 天）：为批量删除/同步增加统一确认模态（展示选中数量/预计影响/不可撤销提示/可跳转结果入口）。
  - 中期重构（1~2 周）：抽象 `UI.createDangerConfirmModal()`（可复用标题/范围/二次确认输入/确认 loading）。
  - 长期规范化：形成“危险操作确认规范”（删除/批量/导入导出/同步）并强制走统一组件。
- 落地（2025-12-23）：
  - 短期：为“批量删除实例”“同步所有账户”等高风险入口补充二次确认与影响范围提示，并提供“会话中心”结果入口。
  - 中期：新增统一组件 `UI.confirmDanger(options)`（基于 Bootstrap Modal + `UI.createModal`），替代全站 `confirm()`。
  - 长期：新增规范 `docs/standards/danger-operation-confirmation-guidelines.md`，并提供门禁脚本 `scripts/code_review/browser_confirm_guard.sh` 防止回归。
- 验证：
  - 手动：误点场景（未选中/选中 1 条/选中 N 条）均有明确提示；确认后按钮进入 loading 且不可重复提交。
  - 体验：确认弹窗中明确“影响范围/不可撤销/结果查看入口”，用户能复述“我将做什么、影响什么”。

3) 异步任务/同步结果的“成功判定”与“错误文案”不可靠，可能把失败当成功
- 证据：实例详情把 `message` 作为成功信号：`app/static/js/modules/views/instances/detail.js:262`（`const isSuccess = data?.success || Boolean(data?.message);`）；错误/成功消息多字段兜底：`app/static/js/core/http-u.js:214`（`body.message || body.error ...`）与 `app/static/js/modules/views/components/connection-manager.js:198`（`result.message || result.error`）
- 影响：用户收到“成功 toast”但实际失败/部分失败，导致后续流程异常（结果不一致、重复提交、排障成本上升），严重损害信任。
- 根因：前后端契约漂移（success/message/error 不统一）+ 实现兜底（用多字段推断成功/失败）。
- 建议：
  - 短期止血（1~2 天）：统一前端成功判定只认 `success === true`；失败只认 `success === false`（无 `success` 则视为未知并提示“请到会话中心确认结果”）。
  - 中期重构（1~2 周）：收敛后端返回 schema（`{ success, data, message, error }`），前端只消费一种；逐页删除“message 即成功”的推断逻辑。
  - 长期规范化：在 `http-u` 层加“契约漂移埋点”（见文末“兜底点清单”），统计兜底命中率并告警。
- 验证：
  - 用例：模拟后端返回 `success:false, message:'xxx'`，前端必须展示失败；返回 `success:true, error:'xxx'` 必须视为异常并记录漂移。
  - 数据：上线后观察“兜底命中率”趋势应下降。

4) 连接测试结果渲染未转义，错误信息可能破坏布局/存在注入风险
- 证据：`app/static/js/modules/views/components/connection-manager.js:194`（`container.html(\`...\${result.message || result.error}...\`)` 直接拼接进 HTML）
- 影响：一旦后端返回包含特殊字符/HTML 的错误信息，UI 可能错位甚至被注入；用户看到“技术堆栈/原始报错”降低专业感。
- 根因：实现（字符串拼接缺少 escape/白名单渲染）+ 契约（错误字段内容不受控）。
- 建议：
  - 短期止血（0.5~1 天）：对 `result.message/result.error` 做 HTML 转义或改为 `textContent` 注入；仅对可信字段（如版本号）做安全插值。
  - 中期重构（1~2 周）：统一“错误展示组件”只接受纯文本与错误码；复杂内容放入“详情展开”并做安全渲染。
  - 长期规范化：错误 schema 增加 `code` 与 `detail`，前端按 code 映射可行动文案。
- 验证：
  - 安全：构造包含 `<script>`/`<img onerror>` 的错误消息，页面不得执行/不得破版。
  - 体验：错误提示应可读、可行动（包含下一步：重试/查看会话/联系管理员）。

### P1

1) 页面头部“描述信息”未渲染，导致用户缺少上下文解释（尤其是只读/权限差异）
- 证据：宏未使用 `description`：`app/templates/components/ui/page_header.html:1`；调用侧传入描述但不会显示：`app/templates/instances/list.html:16`、`app/templates/tags/index.html:15`
- 影响：用户更难理解当前页目的/权限边界（例如只读模式、页面用途），学习成本增加。
- 根因：实现缺漏（宏参数未落地）+ 设计（未验证页面 header 信息层级）。
- 建议：
  - 短期止血（0.5 天）：在 `page_header` 宏中渲染 `description`（如 `<p>`），并定义空值行为。
  - 中期重构：统一 page header 信息架构（标题/描述/操作区/辅助入口）。
  - 长期规范化：写入“页面头部规范”（包含何时必须写描述、只读提示、关键快捷入口）。
- 验证：对比 5 个核心页面 header 区域，描述文本可见且不挤压操作区；只读用户能在 3 秒内理解限制。

2) 列表→详情→返回“丢筛选上下文”，用户需要重复筛选定位
- 证据：详情页返回链接固定跳转：`app/templates/instances/detail.html:151`（`href="{{ url_for('instances.index') }}"` 不带 query）；列表页虽在 URL 内同步筛选：`app/static/js/modules/views/instances/list.js:803`
- 影响：用户从列表进入详情后点击“返回列表”会丢筛选/分页/滚动位置，效率下降，产生挫败感。
- 根因：交互缺少“返回策略”统一（浏览器 back vs 页面按钮）+ 实现未传递 return_to。
- 建议：
  - 短期止血（0.5~1 天）：在列表页进入详情时附带 `?return_to=...` 或写入 `sessionStorage`；详情页“返回列表”优先回到 `return_to`。
  - 中期重构：为所有“列表→详情”建立统一返回机制（包含滚动位置恢复）。
  - 长期规范化：写入“上下文保留规范”（筛选、分页、滚动、选中态）。
- 验证：在实例列表设置筛选→进详情→点击“返回列表”，筛选条件与列表定位保持一致（截图对比）。

3) 顶部导航缺少当前页高亮/aria-current，用户难回答“我在哪”
- 证据：导航链接无 active/aria-current 逻辑：`app/templates/base.html:59` 起（多处 `nav-link` 仅静态渲染）
- 影响：信息架构可发现性下降；用户在多模块（历史/设置/数据管理）间切换时更易迷路。
- 根因：交互缺失（定位线索不足）+ 实现未基于 `request.path` 或 `page_id` 高亮。
- 建议：
  - 短期止血（0.5~1 天）：基于当前路由为对应 nav-link 增加 `active` 与 `aria-current="page"`；下拉项同理。
  - 中期重构：引入“导航配置表”（route→menu mapping），避免散落模板逻辑。
  - 长期规范化：写入“导航与信息架构规范”（层级、命名、权限、面包屑）。
- 验证：随机进入 10 个页面，用户无需滚动即可从导航判断当前位置；无障碍树中存在 aria-current。

4) 浏览器标题（`<title>`）被运行时脚本覆盖，标签页不再反映具体页面
- 证据：`app/templates/base.html:308`（`pageTitleElement.text(\`${appName} - 数据同步管理平台\`)` 覆盖模板 `block title`）
- 影响：多标签工作时难以分辨页面；历史记录/书签/无障碍辅助技术对页面识别能力下降。
- 根因：实现（动态 app-name 需求与页面 title 需求冲突）+ 缺少 title 规范。
- 建议：
  - 短期止血（0.5 天）：仅替换品牌名（如把“鲸落”替换为 appName），保留 page-specific title 片段。
  - 中期重构：在模板侧输出 `data-app-name` 或 `meta`，避免每页额外请求并统一 title 拼接。
  - 长期规范化：写入“页面标题规范”（格式、顺序、是否含环境/租户）。
- 验证：登录页/实例详情/会话中心等标签页标题均包含页面名且品牌名可动态替换。

5) `filter_card` 栅格规范存在违规（破坏一致性与未来维护门禁）
- 证据：`app/templates/accounts/ledgers.html:34` 使用 `col_class='col-md-3 col-12'`；规范要求 filter_card 内搜索/下拉控件使用 `col-md-2 col-12`
- 影响：FilterCard 视觉与交互密度不一致；后续新增控件更易出现对齐/换行不可预测。
- 根因：一致性约束未工具化（缺少模板层 guard）+ 局部需求未通过“局部 utility class”方式表达。
- 建议：
  - 短期止血（0.5 天）：恢复为 `col-md-2 col-12`；若确需更宽，按规范采用“局部 utility class + 评审说明”而不是改栅格基线。
  - 中期重构：为 FilterCard 增加 lint/脚本检查（模板扫描 `col-md-(?!2)`）。
  - 长期规范化：补写 FilterCard 规范（控件类型、默认栅格、允许突破的条件与方式）。
- 验证：在 1024/1366 宽度下 FilterCard 同类控件对齐一致；扫描脚本命中为 0。

6) 图标按钮（btn-icon）缺少可访问名称，键盘/读屏不可用或体验差
- 证据：实例列表操作列图标按钮仅 `title`：`app/static/js/modules/views/instances/list.js:508`；会话中心取消按钮同样：`app/static/js/modules/views/history/sessions/sync-sessions.js:401`；日志详情复制按钮：`app/templates/history/logs/detail.html:17`
- 影响：读屏用户无法理解按钮含义；键盘用户也缺少明确提示（title 不稳定被读取）；无障碍合规风险。
- 根因：实现（图标按钮模板未统一要求 `aria-label`/`aria-hidden`）+ 组件规范缺失。
- 建议：
  - 短期止血（0.5~1 天）：所有 icon-only `<button>/<a>` 必须补 `aria-label`（与 title 一致）；装饰性 `<i>` 补 `aria-hidden="true"`.
  - 中期重构：抽象“IconButton”模板/渲染 helper，强制传入 label。
  - 长期规范化：写入“图标按钮 A11y 规范”（名称、状态、禁用、tooltip）。
- 验证：
  - A11y：用键盘 Tab 遍历操作列，读屏能读出“查看详情/取消会话/复制消息”等。
  - 自动化：axe/lighthouse 不再报 “Buttons do not have an accessible name”。

7) 关闭按钮（btn-close）可访问名称缺失/英文混用，体验不一致
- 证据：alert close 无 aria-label：`app/templates/base.html:199`；scheduler 模态 close 无 aria-label：`app/templates/admin/scheduler/modals/scheduler-modals.html:9`；通用 modal close aria-label 为英文：`app/templates/components/ui/modal.html:6`
- 影响：读屏读出英文或无法读出；不同组件行为/语义不一致，降低整体品质感。
- 根因：组件规范缺失 + 模板实现不统一。
- 建议：
  - 短期止血（0.5 天）：统一为中文 `aria-label="关闭"`；对 alert/toast/modal 一致化。
  - 中期重构：将 close 按钮统一由 `components/ui/modal.html` 与统一 alert/toast helper 渲染，避免手写。
  - 长期规范化：写入“关闭按钮与可访问名称规范”。
- 验证：读屏在任何关闭按钮上均朗读“关闭”；静态扫描不再出现缺失 aria-label 的 btn-close。

8) 时间展示格式不一致（`MM/DD` vs `YYYY-MM-DD`），中文语境下可读性差
- 证据：实例列表自定义格式为 `MM/DD HH:mm`：`app/static/js/modules/views/instances/list.js:1253`；全局 TimeUtils 已提供 `YYYY-MM-DD HH:mm:ss` 等：`app/static/js/common/time-utils.js:307`；模板侧使用 `china_datetime`：`app/templates/instances/detail.html:59`
- 影响：用户在不同页面对同一字段“最后同步/时间范围”产生理解偏差；跨页面对比成本上升。
- 根因：实现各自为政（未复用 TimeUtils/模板 filter）+ 缺少时间格式规范。
- 建议：
  - 短期止血（0.5~1 天）：统一前端展示使用 TimeUtils（或明确规定：列表用 smartTime，详情用 dateTime）。
  - 中期重构：时间渲染全部走 `timeUtils.formatSmartTime/formatDateTime`，避免页面内自定义格式。
  - 长期规范化：写入“时间/时区/格式规范”，并明确“列表/详情/日志”的格式策略。
- 验证：实例列表与详情页相同字段时间格式一致；用户可在 1 秒内无歧义读出年月日。

9) GridWrapper 存在调试日志与侵入式刷新路径，影响性能与问题定位
- 证据：`console.log` 常驻：`app/static/js/common/grid-wrapper.js:128`、`:157`、`:170`；refresh 内部操纵 pipeline/store（更难预测）
- 影响：控制台噪音干扰排障；在大表格/频繁筛选时可能增加卡顿与不可预期刷新问题。
- 根因：实现（调试代码未做环境隔离）+ 缺少性能/日志规范。
- 建议：
  - 短期止血（0.5 天）：移除或加环境开关（仅 dev 打印）；最小化 refresh 逻辑（优先使用 gridjs 官方 updateConfig/forceRender 路径）。
  - 中期重构：统一表格刷新 API（含节流、防抖、取消过期请求）。
  - 长期规范化：写入“表格性能与日志规范”（默认禁 console.log）。
- 验证：筛选连续输入时不出现明显卡顿；生产环境控制台无 GridWrapper 日志。

10) 分页参数命名与 URL 同步不一致（`page_size` vs `limit` vs `pageSize`），可分享性与行为不稳定
- 证据：GridWrapper 使用 `limit`：`app/static/js/common/grid-wrapper.js:54`；多页面将筛选编码为 `page_size`：`app/static/js/modules/views/instances/list.js:753`、`app/static/js/modules/views/history/sessions/sync-sessions.js:543`；用户管理还兼容 `pageSize`：`app/static/js/modules/views/auth/list.js:35`
- 影响：复制 URL 分享/刷新后，表格分页大小可能不一致；前后端参数混用增加维护成本。
- 根因：契约漂移（分页参数多版本共存）+ 前端未统一参数层。
- 建议：
  - 短期止血（1 天）：确定单一参数（建议 `page_size`）并在 GridWrapper 与各页面同步；旧参数保留兼容但埋点统计。
  - 中期重构：抽象 `TableQueryParams` 工具（parse/serialize），所有页面复用。
  - 长期规范化：写入“分页与排序参数规范”，后端同步对齐。
- 验证：设置不同 page size 后刷新页面仍保持；URL 参数与实际请求参数一致（抓包核对）。

11) 设计 token 缺口：多页面引用 `--border-radius-pill` 但变量未定义，导致圆角样式失效/漂移
- 证据：使用处：`app/static/css/pages/history/logs.css:65`、`app/static/css/pages/dashboard/overview.css:110`；变量定义处未包含该 token：`app/static/css/variables.css:96`
- 影响：进度条/状态 pill 等 UI 组件圆角可能回落为默认（通常是直角），造成跨页面“同组件不同形态”的割裂感。
- 根因：Token 治理缺失（使用了未定义变量）+ 组件样式复用不足（多处各写一套）。
- 建议：
  - 短期止血（0.5 天）：在 `variables.css` 增加 `--border-radius-pill`（如 `999px`）并统一引用；确认不影响现有圆角体系。
  - 中期重构：收敛 `status-pill/progress` 等为组件级 CSS（从 pages 抽到 components）。
  - 长期规范化：建立 token 校验（扫描 CSS 中 `var(--xxx)` 必须在 token 文件中有定义）。
- 验证：检查仪表盘进度条/会话中心/日志中心等页面，圆角样式一致且无 CSS var fallback 报错。

### P2

1) Tag 筛选组件使用全局固定 ID，扩展到多实例会冲突（且 JS 选择器不做 scope）
- 证据：Filter 宏固定 id：`app/templates/components/filters/macros.html:157`（`open-tag-filter-btn`、`selected-tags-preview`、`selected-tags-chips`、`selected-tag-names`）；实例列表用全局选择器：`app/static/js/modules/views/instances/list.js:823`
- 影响：一旦同页出现第二个 tag-selector（或复用到多个 FilterCard/Modal），DOM id 冲突导致交互错乱；可维护性差。
- 根因：组件设计未参数化（field_id 未贯穿到内部节点）+ 实现依赖全局 querySelector。
- 建议：
  - 短期止血（0.5~1 天）：将这些 id 全部改为基于 `field_id` 的派生（如 `${field_id}__open`）；JS 通过 `data-tag-selector-scope` 在容器内查询。
  - 中期重构：封装 TagSelectorHelper 为“可多实例”API（传 rootElement 而非一堆 selector）。
  - 长期规范化：写入“可复用组件的 ID/作用域规范”。
- 验证：在同页放置 2 个标签筛选器，互不影响；选择/清除/预览均正确。

2) FilterCard 操作区按钮布局（宽度 50% 且纵向堆叠）浪费空间、降低可扫视性
- 证据：`app/static/css/components/filters/filter-common.css:61`（`.filter-actions` 纵向）+ `:68`（按钮 `width: 50%`）
- 影响：在桌面端高频筛选场景，用户需要更多视线/鼠标移动；按钮区域“空白感”增加。
- 根因：视觉布局缺少对“桌面密度/效率”的统一规范。
- 建议：
  - 短期止血（0.5 天）：在不引入移动端适配前提下，改为横向并列（或 100% 宽度单列但不留 50% 空白），并保持与其他页面操作区一致。
  - 中期重构：建立“FilterCard 密度模式”（regular/compact）并统一配置入口。
  - 长期规范化：补写“筛选条布局规范”（按钮位置、密度、快捷清除）。
- 验证：1024/1366 宽度下 FilterCard 一屏可承载更多筛选控件且操作按钮可快速定位。

3) 运行时内联样式/手写颜色绕开 token，存在一致性与主题切换风险
- 证据：`app/templates/base.html:52`（`rgba(0,0,0,0.1)`）与 `app/templates/base.html:129`（`#ff6b6b`）
- 影响：主题/配色调整难以统一；局部颜色“看起来不属于系统”，降低一致性与品牌感。
- 根因：未建立“禁止内联颜色”门禁 + 缺少替代 token/utility。
- 建议：
  - 短期止血（0.5 天）：替换为 token/utility class（如使用 `var(--status-danger)` 或既有 `.text-danger`）。
  - 中期重构：增加模板扫描脚本，禁止出现 `style="...#..."`/`rgba(...)`（非 token 文件除外）。
  - 长期规范化：写入“颜色 token 使用规范”，并约定阴影也走变量（`--shadow-*`）。
- 验证：模板扫描为 0 命中；视觉回归截图对比颜色一致。

4) 资源加载偏“全站大一统”，首屏感知性能存在优化空间
- 证据：`app/templates/base.html:233` 起全站加载 numeral/mitt/lodash/umbrella/dayjs 多插件/just-validate/tom-select 等；并在每页额外请求 app-info：`app/templates/base.html:289`
- 影响：首屏 JS 解析与网络请求增多；在低性能设备/高延迟网络下更明显；对“只读页面/错误页”也产生额外成本。
- 根因：资源按页拆分与缓存策略未明确。
- 建议：
  - 短期止血（1~2 天）：将非必需库移到页面 `extra_js`；app-info 改为服务端渲染或加缓存（并避免覆盖 page title）。
  - 中期重构：建立“按页依赖清单”（page_id→scripts），结合 page-loader 做按需加载。
  - 长期规范化：写入“资源加载策略与性能预算”并做构建版本化（hash）。
- 验证：对比优化前后首屏请求数/JS 体积；关键页面加载时间下降（Lighthouse/Performance 面板）。

5) 细节一致性：术语（禁用/停用/锁定）与状态文案在不同模块不一致
- 证据：标签使用“停用”：`app/templates/tags/index.html:53`；实例统计使用“禁用”：`app/templates/instances/statistics.html:47`；凭据列表使用“启用/停用”：`app/static/js/modules/views/credentials/list.js:877`
- 影响：用户跨模块理解成本增加（同一状态不同叫法）；运营/培训文档难统一。
- 根因：缺少全局术语表与状态映射。
- 建议：
  - 短期止血（0.5~1 天）：建立状态映射表（UI 文案统一）并在各页面引用。
  - 中期重构：将状态枚举与文案放入统一模块（如 `common/status-dict`）。
  - 长期规范化：写入“术语表/状态机规范”，并作为评审清单项。
- 验证：同一状态在 3 个核心模块展示一致；产品/运营可复用同一套术语。

6) 表格空状态/错误态缺少可行动引导，用户不知道下一步做什么
- 证据：GridWrapper 语言包仅给出“未找到记录/加载数据失败”：`app/static/js/common/grid-wrapper.js:67`
- 影响：筛选无结果时用户需要自行猜测（该清除哪个筛选、是否无权限、是否接口失败）；效率下降且容易误以为系统坏了。
- 根因：反馈规范缺失（Empty/Error 没有统一模板）+ 表格组件能力未产品化（缺少“重置筛选/刷新/查看会话”入口）。
- 建议：
  - 短期止血（0.5~1 天）：为 noRecordsFound/error 提供更可行动文案（例如“清除筛选”“刷新”“去会话中心查看任务结果”），至少在页面层补充空状态区块。
  - 中期重构：GridWrapper 支持注入 Empty/Error 渲染函数（而不是纯字符串），允许不同页面带 CTA。
  - 长期规范化：写入“空状态/错误态规范”（必须包含原因假设 + 下一步动作）。
- 验证：在筛选为 0 结果/接口 500/无权限三种情况下，用户都能在页面内找到明确下一步入口。

---

IV. “最小可执行修复路线图”（最多 8 条行动项，每条可在 0.5~2 天落地）

1) 修复按钮层级基线：收敛 `.btn` 全局覆盖，恢复 outline/危险态的可识别性（0.5~1 天）
2) 危险操作统一确认：为批量删除/全量同步补确认模态与范围提示，并统一 loading/防重复提交（1~2 天）
3) 错误/成功判定收敛：前端只认 `success`；补“未知结果→去会话中心确认”兜底文案（1~2 天）
4) 错误展示安全化：统一错误文本注入走 escape/textContent，替换 ConnectionManager 的 HTML 拼接（0.5~1 天）
5) 列表→详情→返回上下文：引入 `return_to` 或 sessionStorage，恢复筛选/分页（0.5~1 天）
6) A11y 快速修复包：icon-only 按钮补 `aria-label`，所有 `btn-close` 统一中文 aria-label，补充必要 `aria-hidden`（0.5~1 天）
7) 表格参数统一：确定 `page_size`/`limit` 单一口径，GridWrapper 与各页面同步，并对旧参数做埋点（1~2 天）
8) 去除生产调试噪音：移除 GridWrapper `console.log` 或加环境开关；建立“日志规范”检查点（0.5 天）

---

附加输出：兜底/兼容/回退/适配（前端侧）

> 说明：以下“兜底点”会直接影响 UX 的可预测性（尤其是错误提示/成功判定/分页/数据解析）。建议用“统一 schema + 渐进移除兜底 + 埋点统计命中率”的方式收敛。

1) 位置：`app/static/js/core/http-u.js:214`
- 类型：防御/回退
- 描述：`resolveErrorMessage` 使用 `body.message || body.error` 推断错误文案，掩盖后端错误字段不一致。
- 建议：后端统一错误字段（建议 `error.message` 或 `message` 单一）；前端保留兼容期同时埋点 `error_field_fallback`（记录命中字段与 endpoint）。

2) 位置：`app/static/js/common/csrf-utils.js:69`
- 类型：兼容
- 描述：CSRF token 解析 `data?.csrf_token ?? data?.data?.csrf_token`，表示接口返回层级不稳定。
- 建议：后端固定 `{"csrf_token": "..."}`；前端加埋点 `csrf_token_fallback_depth` 并在命中时告警/统计。

3) 位置：`app/static/js/modules/views/instances/list.js:391`
- 类型：兼容/防御
- 描述：列表数据处理使用 `response?.data || response || {}`，表示有的接口返回包裹层、有的不包裹。
- 建议：统一服务端分页响应结构；前端抽象 `unwrapResponse(response)` 并对“非预期形态”埋点。

4) 位置：`app/static/js/modules/views/accounts/ledgers.js:120`
- 类型：兼容/防御
- 描述：同类 `response?.data || response || {}` 用于 total 解析，契约漂移重复出现。
- 建议：同上，收敛到单一响应结构；在 store/service 层统一 unwrap，页面不再关心多形态。

5) 位置：`app/static/js/modules/views/instances/modals/batch-create-modal.js:177`
- 类型：兼容/回退
- 描述：成功处理 `response?.response || response?.data || response`，说明存在“二次包裹/多层嵌套”的不稳定返回。
- 建议：后端统一；前端兼容期埋点 `response_wrapper_depth` 并逐页移除。

6) 位置：`app/static/js/modules/views/components/permissions/permission-viewer.js:129`
- 类型：兼容
- 描述：权限接口把 payload 解包为 `data.data` 或 `data`（`data && data.data ? data.data : data`）。
- 建议：后端统一 `data` 层；前端埋点 `permissions_payload_unwrap`，兼容期结束后删除分支。

7) 位置：`app/static/js/modules/views/components/permissions/permission-viewer.js:142`
- 类型：回退
- 描述：错误提示 `data?.error || data?.message`，导致同类错误提示字段漂移。
- 建议：统一错误 schema；前端只消费一个字段，并埋点 `error_message_field_used`。

8) 位置：`app/static/js/modules/views/instances/list.js:602`
- 类型：兼容
- 描述：筛选值解析 `values?.search || values?.q`，说明同一筛选字段存在两种命名。
- 建议：统一 query 参数命名（建议 `search`）；兼容期埋点 `filter_key_alias_hit`（q→search）。

9) 位置：`app/static/js/common/grid-wrapper.js:54`
- 类型：契约适配
- 描述：分页参数使用 `limit`，而多页面 URL/筛选逻辑使用 `page_size`（见 `instances/list.js:753` 等）。
- 建议：确定唯一分页参数（推荐 `page_size`）；GridWrapper 与后端同步；兼容期对旧参数埋点。

10) 位置：`app/static/js/modules/views/auth/list.js:35`
- 类型：兼容
- 描述：用户管理兼容 `pageSize`（camelCase）与 `page_size`（snake_case）。
- 建议：明确唯一参数；前端兼容期埋点 `page_size_alias_hit`。

11) 位置：`app/static/js/modules/views/instances/list.js:1192`
- 类型：回退
- 描述：连接测试失败提示使用 `result?.error || result?.message || '连接失败'`，同类错误字段不稳定。
- 建议：统一错误字段；前端只消费一个字段；埋点统计 `result_error_field_used`。

12) 位置：`app/static/js/modules/views/instances/detail.js:262`
- 类型：回退（高风险）
- 描述：把 `Boolean(data?.message)` 当作成功信号，可能把失败当成功（见 P0 问题）。
- 建议：只认 `success`；无 `success` 视为未知并引导去“会话中心”核对；埋点 `success_inferred_from_message`（应最终为 0）。

13) 位置：`app/static/js/modules/views/instances/detail.js:264`
- 类型：兼容
- 描述：成功消息 `data?.message || data?.data?.result?.message`，说明后端嵌套层级漂移。
- 建议：统一 message 位置；埋点 `message_depth_fallback`。

14) 位置：`app/static/js/modules/views/instances/detail.js:685`
- 类型：回退
- 描述：变更历史错误展示 `data?.error || data?.message`。
- 建议：错误 schema 收敛；前端只消费一个字段；埋点 `history_error_field_used`。

15) 位置：`app/static/js/modules/views/credentials/list.js:979`
- 类型：兼容/回退
- 描述：凭据错误来自 `payload?.error?.message`（嵌套 error.message），与其他页面的 `data.error/data.message` 不一致。
- 建议：统一错误对象形态（例如 `{ error: { code, message } }`）；兼容期埋点 `error_object_shape`。

16) 位置：`app/static/js/modules/views/admin/scheduler/index.js:769`
- 类型：回退
- 描述：定时任务错误使用 `payload?.error?.message || '...'`，与其他页面不同层级。
- 建议：统一 scheduler API 错误结构；前端适配期埋点。

17) 位置：`app/static/js/modules/views/accounts/account-classification/index.js:650`
- 类型：兼容
- 描述：错误提示优先 `error?.response?.error` 再 `error.message`，说明错误对象结构不统一（Error vs response payload）。
- 建议：在 http 层统一抛出标准 Error（含 `code/message/details`）；页面不再猜测结构；埋点 `error_shape_fallback`。

埋点建议（用于渐进移除兜底）：
- 事件名建议：`contract:fallback`
- 字段建议：`{ page_id, endpoint, kind, fallback_chain, chosen_key, status, sample }`
- 采样：对高频接口做 1% 采样，或仅在“非主路径字段命中”时上报；可先写入后端日志中心，后续再做指标化。
