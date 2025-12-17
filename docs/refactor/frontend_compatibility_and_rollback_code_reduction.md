# 前端削减兼容/回退代码清单与收敛方案（基于 2025-12-17）

> 目标：系统性识别并削减“为旧模板调用方式/旧 API 返回结构/旧浏览器能力/旧全局接口”保留的兼容与回退路径，减少全局耦合与分支，让页面脚本可持续减码与可维护。

## 1. 前置结论：先定“前端支持矩阵”，否则无法判断哪些能删

### 1.1 项目硬约束（仓库规范）
- 仅支持桌面端（禁止新增移动端 `@media` 适配）。
- `filter_card` 控件栅格遵循 `col-md-2 col-12`（本文不改样式，仅做兼容/回退收敛）。

### 1.2 本文“兼容/回退”定义（用于收敛）
- **兼容代码**：为了适配“旧模板的内联 `onclick` 调用方式、旧全局函数名、旧返回结构、旧参数命名、旧资源/变量名”等而保留的接口暴露、别名、双解析、桥接文件。
- **回退代码**：新路径不可用/未加载/失败时退回旧方式（例如“没加载 store 就直接调 service”、“没 Grid 就回到 GET 刷新”）。
- **浏览器兼容回退**：基于 feature detection 的回退（例如 `requestSubmit`、clipboard API）。

## 2. 尽可能“找全”的方法（可复跑）

### 2.1 关键词扫描（JS/CSS）
```bash
rg -n --hidden "兼容|向后兼容|旧版|旧接口|回退|降级|legacy|deprecated|fallback" app/static/js app/static/css
```

### 2.2 内联事件扫描（模板与 JS 生成 HTML）
```bash
rg -n "onclick=\\\"" app/templates
rg -n "onclick=\\\"" app/static/js
```

### 2.3 全局接口暴露扫描（`window.*`/`global.*` 赋值）
```bash
rg -n -P "(?:window|global)\\.[A-Za-z0-9_$]+\\s*=" app/static/js --hidden -o
```

### 2.4 bootstrap 桥接脚本与模板引用
```bash
rg -n "js/bootstrap/" app/templates
find app/static/js/bootstrap -type f -maxdepth 3 -print
```

## 3. 前端兼容/回退清单（按类型汇总，便于你逐条审查）

> 下述条目均是“可删候选”。是否删除取决于你是否仍需要支持对应的旧模板写法/旧后端返回结构/旧浏览器范围。

### A. 模板内联 `onclick`（导致必须暴露全局函数/对象）

这些 `onclick` 会强制你在 `window` 上挂函数（或挂 Actions 对象），属于**典型历史包袱**：阻碍页面脚本模块化、加大命名冲突风险、让 refactor 很难分层。

出现位置（模板侧）见附录 5.1，代表性调用包括：
- `instances/detail.html`：`testConnection()`、`syncAccounts()`、`syncCapacity(id,name)`、`openEditInstance(event)`、`confirmDeleteInstance(event)`、`viewInstanceAccountPermissions(id)`、`viewAccountChangeHistory(id)`
- `accounts/ledgers.html`：`syncAllAccounts()`、`AccountsActions.exportCSV()`
- `dashboard/overview.html`：`refreshDashboard(this)`
- `instances/statistics.html`：`manualRefresh(this)`
- `accounts/account-classification/index.html`：`autoClassifyAll(event)`、`openCreateClassificationModal(event)`、`openCreateRuleModal(event)`

建议收敛（推荐优先级最高）：
1. **把模板的 `onclick` 改为 `data-action` + 事件委托**（脚本里统一 `document.addEventListener('click', ...)` 分发）。
2. **删除 `window.xxx = ...` 的暴露**：页面逻辑只在模块内部闭包中维护，减少全局 API 面。
3. **对外接口只保留“页面入口 mount”一个**（或连 mount 也自启动），避免暴露细粒度 action。

### B. JS 生成 HTML 中的 `onclick="..."`（把全局耦合扩散到运行期 DOM）

这类兼容比模板内联更隐蔽：HTML 字符串里写死 `onclick`，等同于把“全局函数名”当作 API 契约。

出现位置（JS 侧）见附录 5.2，典型包括：
- `app/static/js/modules/views/instances/list.js`：`onclick="InstanceListActions.testConnection(...)"`（Grid 单元格动作）
- `app/static/js/modules/views/accounts/ledgers.js`：`onclick="AccountsActions.viewPermissions(...)"`（Grid 单元格动作）
- `app/static/js/modules/views/auth/list.js`：`onclick="AuthListActions.openEditor(...)"` / `requestDelete(...)`
- `app/static/js/modules/views/credentials/list.js`：`onclick="openCredentialEditor(...)"` / `deleteCredential(...)`
- `app/static/js/modules/views/tags/index.js`：`onclick="TagsIndexActions.openEditor(...)"` / `confirmDelete(...)`
- `app/static/js/modules/views/tags/batch-assign.js`：`onclick="batchAssignManager.toggle..."`
- `app/static/js/modules/views/accounts/account-classification/index.js`：表格行按钮 `onclick="editRule(...)"` 等（依赖全局函数）

建议收敛：
- 所有“表格动作按钮”统一输出 `data-action`/`data-id`，并在 mount 时做**事件委托**，彻底移除字符串 onclick。

### C. `bootstrap/` 桥接脚本（页面入口的冗余层）

现状：模板引用 `app/static/js/bootstrap/**.js`，bootstrap 只做一件事：`DOMContentLoaded` 时调用 `window.XXXPage.mount()`；而多数页面模块内部已经自行处理 DOM ready（或完全可以通过 `defer` 解决）。

模板引用点见附录 5.3，bootstrap 文件清单如下（19 个）：
- `app/static/js/bootstrap/accounts/account-classification.js`
- `app/static/js/bootstrap/accounts/ledgers.js`
- `app/static/js/bootstrap/admin/partitions.js`
- `app/static/js/bootstrap/admin/scheduler.js`
- `app/static/js/bootstrap/auth/change-password.js`
- `app/static/js/bootstrap/auth/list.js`
- `app/static/js/bootstrap/auth/login.js`
- `app/static/js/bootstrap/capacity/databases.js`
- `app/static/js/bootstrap/capacity/instances.js`
- `app/static/js/bootstrap/credentials/list.js`
- `app/static/js/bootstrap/dashboard/overview.js`
- `app/static/js/bootstrap/databases/ledgers.js`
- `app/static/js/bootstrap/history/logs.js`
- `app/static/js/bootstrap/history/sync-sessions.js`
- `app/static/js/bootstrap/instances/detail.js`
- `app/static/js/bootstrap/instances/list.js`
- `app/static/js/bootstrap/instances/statistics.js`
- `app/static/js/bootstrap/tags/batch-assign.js`
- `app/static/js/bootstrap/tags/index.js`

建议收敛（两条路线二选一）：
1. **页面模块自启动**：模块在加载后自行 `DOMContentLoaded` mount → 模板不再引用 bootstrap。
2. **保留单一通用 bootstrap**：实现一个通用入口（按 `data-page` 映射到 `window.XxxPage.mount`），删掉 18 个重复 bootstrap 脚本。

### D. “为旧模板/旧全局名保留”的显式兼容接口（最典型的可删候选）

#### D1. CSRF：旧全局函数 `getCSRFToken`
- 位置：`app/static/js/common/csrf-utils.js:182`
  - `window.getCSRFToken = function() { ... }`（注释“提供向后兼容的全局函数”）
- 建议收敛：前端统一改用 `window.csrfManager.getToken()` 或由 `httpU` 统一注入；删掉 `getCSRFToken`。

#### D2. 账户台账：暴露 `AccountsActions`/`syncAllAccounts` 以兼容旧模板
- 位置：`app/static/js/modules/views/accounts/ledgers.js:961` 起
  - `exposeGlobalActions()` 明确写“兼容旧模板”
- 建议收敛：模板与 Grid 动作改事件委托；删除对外暴露对象。

#### D3. 账户分类：大量 `window.xxx = ...` 维持旧接口
- 位置：`app/static/js/modules/views/accounts/account-classification/index.js:647` 起
  - `openCreateClassificationModal/openCreateRuleModal/.../autoClassifyAll/...` 等大量全局函数
- 建议收敛：模板从 `onclick` 迁移到 `data-action` 后，这些全局函数可整体删除。

#### D4. TimeUtils：对外暴露大量旧全局函数名
- 位置：`app/static/js/common/time-utils.js:389` 起
  - 除 `window.timeUtils` 外，还暴露 `window.formatTime/window.parseTime/...` 等一批别名
- 建议收敛：统一仅保留 `window.timeUtils`（或统一仅保留 `TimeUtils` 单一对象），逐步删掉散落全局别名。

#### D5. ConnectionManager：废弃方法空实现
- 位置：`app/static/js/modules/views/components/connection-manager.js:216`
  - `showBatchTestProgress()` 已废弃但保留空实现“兼容老代码”
- 建议收敛：确认无调用后删除该方法（并删掉所有调用点）。

### E. 回退/降级逻辑（新路径缺失/失败时退回旧方式）

#### E1. 分区管理：Store 缺失/失败回退到 service 直连
- 位置：`app/static/js/modules/views/admin/partitions/index.js:49`、`:78`
  - `createPartitionStore 未加载 -> 回退到直接调用服务`
  - `PartitionStore 加载失败 -> 回退到直接加载`
- 建议收敛：当 store 方案稳定后删除回退路径；或者明确“没有 store 也能跑”作为长期策略，并补齐统一的降级抽象。

#### E2. 标签列表：没有 Grid 时回退到 GET 刷新
- 位置：`app/static/js/modules/views/tags/index.js:306` 起
  - `tagsGrid` 不存在 → 拼 query 跳转（旧式刷新）
- 建议收敛：统一依赖 Grid（或统一无 Grid 纯服务端渲染），删掉混合模式。

### F. 浏览器能力兼容回退（是否删除取决于你支持的浏览器范围）

#### F1. `requestSubmit` 回退
- 位置：`app/static/js/modules/ui/filter-card.js:82`
  - 不支持 `form.requestSubmit()` 时回退 `form.submit()`
- 建议：若明确仅支持现代桌面浏览器，可删掉回退（并把“浏览器基线”写进标准）。

#### F2. 剪贴板：clipboard API 不可用时回退 `document.execCommand('copy')`
- 位置：
  - `app/static/js/modules/views/history/logs/log-detail.js:100` 起
  - `app/static/js/modules/views/history/sessions/session-detail.js:96` 起
- 建议：若明确不再支持旧浏览器/旧安全上下文，可去掉 `execCommand` 回退，仅保留 clipboard API + 失败提示。

### G. API 返回结构兼容（前端为了“接住多种 shape”而产生的分支）

这类兼容经常是“前后端演进不同步”的结果。删掉它通常需要后端先统一输出契约（对应后端文档：`docs/refactor/backend_compatibility_and_rollback_code_reduction.md`）。

典型点：
- 日志 store：`app/static/js/modules/stores/logs_store.js:181`（兼容 `data/logs/items` 多结构 + pagination 多字段）
- 图表 data source：`app/static/js/modules/views/components/charts/data-source.js:40`、`:58`（兼容 `summary/items/list/data` 多结构）
- 数据库台账：`app/static/js/modules/views/databases/ledgers.js:209`（同时写入 `database` 与 `database_id` 兼容旧逻辑）

建议收敛：
1. 后端统一 response schema（只保留一种结构）。
2. 前端 stores 删除 “unwrap/兼容字段” 分支，改为强契约解析（失败即报错 + 统一 toast）。

### H. 视觉/资源兼容（历史命名与旧资源）

#### H1. CSS 变量：旧变量命名兼容层
- 位置：`app/static/css/variables.css:29`
  - `--primary-color/--secondary-color/...` 等旧变量名映射到新 token
- 建议收敛：全仓库 CSS 迁移完后删除旧变量，避免设计系统长期双轨。

#### H2. Font Awesome v4 兼容字体
- 位置：`app/static/vendor/fontawesome/webfonts/fa-v4compatibility.woff2`
- 建议收敛：确认模板与脚本不再使用 v4 icon 名称后，可去掉 v4 compatibility 资源（并同步 vendor 体积清理计划）。

### I. CommonJS/Node 兼容壳（若不再需要，可删）
- 位置：
  - `app/static/js/common/csrf-utils.js:213`
  - `app/static/js/modules/views/components/connection-manager.js:224`
  - 代码形态：`if (typeof module !== 'undefined' && module.exports) { module.exports = ... }`
- 建议：如果前端不在 Node 环境复用这些文件，删除该兼容壳，减少分支与误导。

## 4. 建议的收敛路线（避免“一刀切”回归）

### 4.1 分阶段策略（推荐）
1. **先收敛事件体系（最高 ROI）**
   - 模板与 JS 生成 HTML 全部去掉 `onclick` → 统一事件委托。
2. **再收敛全局 API 面**
   - 仅保留页面入口（`XxxPage.mount` 或模块自启动），删掉细粒度全局函数与 Actions 对象。
3. **再删除 bootstrap 冗余层**
   - 选定“模块自启动”或“通用 bootstrap”路线，删掉重复 bootstrap 脚本。
4. **最后统一 API 契约**
   - 后端只返回一种 shape → 前端删掉多结构解析与回退逻辑。

### 4.2 删除前的“最小核验清单”（建议写进 PR 模板）
- `onclick=`：模板与 JS 生成 HTML 中均为 0（用 `rg -n "onclick=\\\"" ...` 验证）。
- 全局暴露：`rg -n -P "(?:window|global)\\.[A-Za-z0-9_$]+\\s*=" ... -o` 的结果显著下降，并且只剩“明确允许的入口对象”。
- 关键页面回归：实例详情、实例列表、账户台账、标签页、日志中心、调度器、分区管理。

## 5. 附录：自动扫描命中列表（便于你逐条点开审查）

### 5.1 模板内 `onclick` 命中
```text
app/templates/dashboard/overview.html:14:    <button type="button" class="btn btn-primary" onclick="refreshDashboard(this)">
app/templates/errors/error.html:51:                        <button onclick="history.back()" class="btn btn-outline-secondary">
app/templates/instances/detail.html:141:                    <button type="button" class="btn btn-primary" onclick="testConnection()">
app/templates/instances/detail.html:144:                    <button type="button" class="btn btn-outline-secondary" onclick="syncAccounts()">
app/templates/instances/detail.html:147:                    <button type="button" class="btn btn-outline-secondary" onclick="syncCapacity({{ instance.id }}, '{{ instance.name }}')">
app/templates/instances/detail.html:154:                    <button type="button" class="btn btn-outline-secondary" data-action="edit-instance" onclick="openEditInstance(event)">
app/templates/instances/detail.html:157:                    <button type="button" class="btn btn-outline-danger" data-action="delete-instance" onclick="confirmDeleteInstance(event)">
app/templates/instances/detail.html:364:                                        <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceAccountPermissions({{ account.id }})" title="查看权限">
app/templates/instances/detail.html:367:                                        <button class="btn btn-sm btn-outline-secondary" onclick="viewAccountChangeHistory({{ account.id }})" title="查看变更记录">
app/templates/instances/detail.html:417:                                        <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceAccountPermissions({{ account.id }})" title="查看权限">
app/templates/instances/detail.html:420:                                        <button class="btn btn-sm btn-outline-secondary" onclick="viewAccountChangeHistory({{ account.id }})" title="查看变更记录">
app/templates/instances/detail.html:470:                                        <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceAccountPermissions({{ account.id }})" title="查看权限">
app/templates/instances/detail.html:473:                                        <button class="btn btn-sm btn-outline-secondary" onclick="viewAccountChangeHistory({{ account.id }})" title="查看变更记录">
app/templates/instances/detail.html:523:                                        <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceAccountPermissions({{ account.id }})" title="查看权限">
app/templates/instances/detail.html:526:                                        <button class="btn btn-sm btn-outline-secondary" onclick="viewAccountChangeHistory({{ account.id }})" title="查看变更记录">
app/templates/instances/detail.html:579:                                        <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceAccountPermissions({{ account.id }})" title="查看权限">
app/templates/instances/detail.html:582:                                        <button class="btn btn-sm btn-outline-secondary" onclick="viewAccountChangeHistory({{ account.id }})" title="查看变更记录">
app/templates/accounts/ledgers.html:19:    <button type="button" class="btn btn-primary" onclick="syncAllAccounts()">
app/templates/accounts/ledgers.html:73:                                        onclick="AccountsActions.exportCSV()">
app/templates/instances/statistics.html:13:    <button type="button" class="btn btn-outline-secondary btn-icon" data-action="refresh-stats" onclick="manualRefresh(this)" title="刷新统计">
app/templates/accounts/account-classification/index.html:18:    <button class="btn btn-outline-secondary" type="button" onclick="autoClassifyAll(event)">
app/templates/accounts/account-classification/index.html:37:                                <button class="btn btn-primary btn-sm" type="button" onclick="openCreateClassificationModal(event)">
app/templates/accounts/account-classification/index.html:56:                                <button class="btn btn-primary btn-sm" type="button" onclick="openCreateRuleModal(event)">
```

### 5.2 JS 中 `onclick` 命中（HTML 字符串内联）
```text
app/static/js/modules/views/credentials/list.js:204:                <button ... onclick="openCredentialEditor(${credentialId}, this)" ...>
app/static/js/modules/views/credentials/list.js:207:                <button ... onclick="deleteCredential(${credentialId}, ...)" ...>
app/static/js/modules/views/history/logs/logs.js:647:            <button ... onclick="window.LogsPage.openDetail(${logId})" ...>
app/static/js/modules/views/instances/detail.js:1033:            <button class="btn btn-outline-primary" onclick="loadDatabaseSizes()">
app/static/js/modules/views/accounts/ledgers.js:555:            <button ... onclick="AccountsActions.viewPermissions(${meta.id}, this)" ...>
app/static/js/modules/views/auth/list.js:703:        <button ... onclick="AuthListActions.openEditor(${userId})" ...>
app/static/js/modules/views/auth/list.js:706:        <button ... onclick="AuthListActions.requestDelete(${userId}, ...)" ...>
app/static/js/modules/views/instances/list.js:482:            `<button ... onclick="InstanceListActions.testConnection(${meta.id}, this)" ...>`,
app/static/js/modules/views/tags/batch-assign.js:215:                    <div ... onclick="batchAssignManager.toggleInstanceGroup('${dbType}')">
app/static/js/modules/views/tags/batch-assign.js:280:                    <div ... onclick="batchAssignManager.toggleTagGroup('${category}')">
app/static/js/modules/views/tags/index.js:691:        <button ... onclick="TagsIndexActions.openEditor(${tagId})" ...>
app/static/js/modules/views/tags/index.js:694:        <button ... onclick="TagsIndexActions.confirmDelete(${tagId}, ...)" ...>
app/static/js/modules/views/accounts/account-classification/index.js:352:            <button ... onclick="editClassification(${classification.id})" ...>
app/static/js/modules/views/accounts/account-classification/index.js:359:                <button ... onclick="deleteClassification(${classification.id})" ...>
app/static/js/modules/views/accounts/account-classification/index.js:522:            <button ... onclick="viewRule(${rule.id})" ...>
app/static/js/modules/views/accounts/account-classification/index.js:525:            <button ... onclick="editRule(${rule.id})" ...>
app/static/js/modules/views/accounts/account-classification/index.js:528:            <button ... onclick="deleteRule(${rule.id})" ...>
```

### 5.3 模板引用 `js/bootstrap/*` 清单
```text
app/templates/credentials/list.html:82:<script src="{{ url_for('static', filename='js/bootstrap/credentials/list.js') }}"></script>
app/templates/instances/detail.html:660:<script src="{{ url_for('static', filename='js/bootstrap/instances/detail.js') }}"></script>
app/templates/instances/statistics.html:257:<script src="{{ url_for('static', filename='js/bootstrap/instances/statistics.js') }}"></script>
app/templates/instances/list.html:104:<script src="{{ url_for('static', filename='js/bootstrap/instances/list.js') }}"></script>
app/templates/history/logs/logs.html:88:<script src="{{ url_for('static', filename='js/bootstrap/history/logs.js') }}"></script>
app/templates/history/sessions/sync-sessions.html:86:<script src="{{ url_for('static', filename='js/bootstrap/history/sync-sessions.js') }}"></script>
app/templates/dashboard/overview.html:205:    <script src="{{ url_for('static', filename='js/bootstrap/dashboard/overview.js') }}"></script>
app/templates/capacity/instances.html:266:<script src="{{ url_for('static', filename='js/bootstrap/capacity/instances.js') }}"></script>
app/templates/admin/partitions/index.html:97:<script src="{{ url_for('static', filename='js/bootstrap/admin/partitions.js') }}"></script>
app/templates/capacity/databases.html:265:<script src="{{ url_for('static', filename='js/bootstrap/capacity/databases.js') }}"></script>
app/templates/auth/change_password.html:121:<script src="{{ url_for('static', filename='js/bootstrap/auth/change-password.js') }}"></script>
app/templates/accounts/account-classification/index.html:139:    <script src="{{ url_for('static', filename='js/bootstrap/accounts/account-classification.js') }}"></script>
app/templates/admin/scheduler/index.html:128:<script src="{{ url_for('static', filename='js/bootstrap/admin/scheduler.js') }}"></script>
app/templates/accounts/ledgers.html:102:<script src="{{ url_for('static', filename='js/bootstrap/accounts/ledgers.js') }}"></script>
app/templates/tags/bulk/assign.html:158:<script src="{{ url_for('static', filename='js/bootstrap/tags/batch-assign.js') }}"></script>
app/templates/auth/login.html:65:<script src="{{ url_for('static', filename='js/bootstrap/auth/login.js') }}"></script>
app/templates/tags/index.html:130:<script src="{{ url_for('static', filename='js/bootstrap/tags/index.js') }}"></script>
app/templates/databases/ledgers.html:83:<script src="{{ url_for('static', filename='js/bootstrap/databases/ledgers.js') }}"></script>
app/templates/auth/list.html:62:<script src="{{ url_for('static', filename='js/bootstrap/auth/list.js') }}"></script>
```

### 5.4 全局暴露接口命中（`window.*`/`global.*` 赋值）
> 生成命令见 2.3；该列表基本等同于“前端全局 API 面清单”（按“文件 -> 导出符号”聚合）。
```text
files_with_exports: 87
total_unique_exports_across_files: 171

- app/static/js/common/csrf-utils.js: csrfManager, getCSRFToken
- app/static/js/common/event-bus.js: EventBus
- app/static/js/common/form-validator.js: FormValidator
- app/static/js/common/grid-wrapper.js: GridWrapper
- app/static/js/common/lodash-utils.js: LodashUtils
- app/static/js/common/number-format.js: NumberFormat
- app/static/js/common/time-utils.js: TimeFormats, formatDate, formatDateTime, formatRelativeTime, formatSmartTime, formatTime, formatTimeOnly, getChinaTime, getTimeRange, isToday, isValidTime, isYesterday, parseTime, timeUtils
- app/static/js/common/toast.js: toast
- app/static/js/common/validation-rules.js: ValidationRules
- app/static/js/core/dom.helpers.js: DOMHelpers, u
- app/static/js/core/http-u.js: httpU, u
- app/static/js/modules/services/account_classification_service.js: AccountClassificationService
- app/static/js/modules/services/capacity_stats_service.js: CapacityStatsService
- app/static/js/modules/services/connection_service.js: ConnectionService
- app/static/js/modules/services/credentials_service.js: CredentialsService
- app/static/js/modules/services/dashboard_service.js: DashboardService
- app/static/js/modules/services/database_ledger_service.js: DatabaseLedgerService
- app/static/js/modules/services/instance_management_service.js: InstanceManagementService
- app/static/js/modules/services/instance_service.js: InstanceService
- app/static/js/modules/services/logs_service.js: LogsService
- app/static/js/modules/services/partition_service.js: PartitionService
- app/static/js/modules/services/permission_service.js: PermissionService
- app/static/js/modules/services/scheduler_service.js: SchedulerService
- app/static/js/modules/services/sync_sessions_service.js: SyncSessionsService
- app/static/js/modules/services/tag_management_service.js: TagManagementService
- app/static/js/modules/services/user_service.js: UserService
- app/static/js/modules/stores/account_classification_store.js: createAccountClassificationStore
- app/static/js/modules/stores/credentials_store.js: createCredentialsStore
- app/static/js/modules/stores/database_store.js: createDatabaseStore
- app/static/js/modules/stores/instance_store.js: createInstanceStore
- app/static/js/modules/stores/logs_store.js: createLogsStore
- app/static/js/modules/stores/partition_store.js: createPartitionStore
- app/static/js/modules/stores/scheduler_store.js: createSchedulerStore
- app/static/js/modules/stores/sync_sessions_store.js: createSyncSessionsStore
- app/static/js/modules/stores/tag_batch_store.js: createTagBatchStore
- app/static/js/modules/stores/tag_list_store.js: createTagListStore
- app/static/js/modules/stores/tag_management_store.js: createTagManagementStore
- app/static/js/modules/theme/color-tokens.js: ColorTokens
- app/static/js/modules/ui/filter-card.js: UI
- app/static/js/modules/ui/modal.js: UI
- app/static/js/modules/views/accounts/account-classification/index.js: AccountClassificationPage, DEBUG_ACCOUNT_CLASSIFICATION, autoClassifyAll, createClassification, createRule, deleteClassification, deleteRule, editClassification, editRule, loadClassificationsForRules, loadPermissions, openCreateClassificationModal, openCreateRuleModal, searchMatchedAccounts, updateClassification, updateRule, viewRule
- app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js: AccountClassificationModals
- app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js: AccountClassificationRuleModals
- app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js: AccountClassificationPermissionView, PermissionPolicyCenter
- app/static/js/modules/views/accounts/ledgers.js: AccountsListPage
- app/static/js/modules/views/admin/partitions/charts/partitions-chart.js: AggregationsChartPage, PartitionStoreInstance, aggregationsChartManager
- app/static/js/modules/views/admin/partitions/index.js: AdminPartitionsPage, PartitionStoreInstance, formatPartitionSize
- app/static/js/modules/views/admin/partitions/modals/partitions-modals.js: PartitionsModals
- app/static/js/modules/views/admin/partitions/partition-list.js: PartitionsListGrid
- app/static/js/modules/views/admin/scheduler/index.js: SchedulerPage, deleteJob, disableJob, enableJob, formatTime, getSchedulerJob, loadJobs, runJobNow, viewJobLogs
- app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js: SchedulerModals
- app/static/js/modules/views/auth/change_password.js: ChangePasswordPage, getPasswordStrength, togglePasswordVisibility, updatePasswordRequirements, updatePasswordStrength
- app/static/js/modules/views/auth/list.js: AuthListActions, AuthListPage
- app/static/js/modules/views/auth/login.js: LoginPage, hideLoadingState, togglePasswordVisibility, updatePasswordStrength
- app/static/js/modules/views/auth/modals/user-modals.js: UserModals
- app/static/js/modules/views/capacity/databases.js: CapacityDatabasesPage, databaseCapacityStatsManager
- app/static/js/modules/views/capacity/instances.js: InstanceAggregationsPage, instanceCapacityStatsManager
- app/static/js/modules/views/components/charts/chart-renderer.js: CapacityStatsChartRenderer
- app/static/js/modules/views/components/charts/data-source.js: CapacityStatsDataSource
- app/static/js/modules/views/components/charts/filters.js: CapacityStatsFilters
- app/static/js/modules/views/components/charts/manager.js: CapacityStats
- app/static/js/modules/views/components/charts/summary-cards.js: CapacityStatsSummaryCards
- app/static/js/modules/views/components/charts/transformers.js: CapacityStatsTransformers
- app/static/js/modules/views/components/connection-manager.js: connectionManager
- app/static/js/modules/views/components/permissions/permission-modal.js: PermissionModalInstance, createPermissionsModal, renderPermissionsByType, showPermissionsModal
- app/static/js/modules/views/components/permissions/permission-viewer.js: fetchAccountPermissions, viewAccountPermissions
- app/static/js/modules/views/components/tags/tag-selector-controller.js: TagSelectorController, TagSelectorHelper
- app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js: TagSelectorModalAdapter
- app/static/js/modules/views/components/tags/tag-selector-view.js: TagSelectorView
- app/static/js/modules/views/credentials/list.js: CredentialsListPage, deleteCredential, openCredentialEditor
- app/static/js/modules/views/credentials/modals/credential-modals.js: CredentialModals
- app/static/js/modules/views/dashboard/overview.js: DashboardOverviewPage, refreshDashboard, showDashboardError, showDashboardSuccess, showDashboardWarning, updateSystemStatus
- app/static/js/modules/views/databases/ledgers.js: DatabaseLedgerPage
- app/static/js/modules/views/history/logs/log-detail.js: LogDetailView
- app/static/js/modules/views/history/logs/logs.js: LogsPage
- app/static/js/modules/views/history/logs/modals/log-detail-modal.js: LogsLogDetailModal
- app/static/js/modules/views/history/sessions/modals/session-detail-modal.js: SyncSessionDetailModal
- app/static/js/modules/views/history/sessions/session-detail.js: SessionDetailView
- app/static/js/modules/views/history/sessions/sync-sessions.js: SyncSessionsPage, cancelSession, getDurationBadge, getProgressInfo, getStatusColor, getStatusText, getSyncCategoryText, getSyncTypeText, viewSessionDetail
- app/static/js/modules/views/instances/detail.js: InstanceDetailPage, confirmDeleteInstance, loadDatabaseSizes, openEditInstance, syncAccounts, syncCapacity, testConnection, toggleDeletedAccounts, toggleDeletedDatabases, viewAccountChangeHistory, viewInstanceAccountPermissions
- app/static/js/modules/views/instances/list.js: InstanceBatchCreateController, InstanceListActions, InstancesListPage
- app/static/js/modules/views/instances/modals/batch-create-modal.js: BatchCreateInstanceModal
- app/static/js/modules/views/instances/modals/instance-modals.js: InstanceModals
- app/static/js/modules/views/instances/statistics.js: InstanceStatisticsPage, manualRefresh
- app/static/js/modules/views/tags/batch-assign.js: TagsBatchAssignPage, batchAssignManager
- app/static/js/modules/views/tags/index.js: TagsIndexActions, TagsIndexPage
- app/static/js/modules/views/tags/modals/tag-modals.js: TagModals
```
