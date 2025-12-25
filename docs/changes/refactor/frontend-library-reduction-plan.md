# 前端减码：第三方库“可替换/可下沉”清单与最小新增依赖方案（基于 2025-12-17）

> 本文面向“不改变功能”的前端减码：通过**更充分使用现有第三方库**、以及**谨慎引入极少量新库**，把重复的页面脚本/组件脚本压缩到可维护的基座与少量业务差异代码。  
> 约束：功能完全等价、桌面端限定（禁止新增移动端 `@media`）、`filter_card` 控件栅格遵循 `col-md-2 col-12`、颜色来自 `variables.css`、以及代码重复度（`jscpd`）长期 **≤5%**。

## 1. 当前基线（前端相关）

### 1.1 行数基线（2025-12-17）
- `app/static/js`：**34,875 行**（107 个文件，不含 `app/static/vendor`）
  - `app/static/js/modules/views`：24,299 行（48 文件）
  - `app/static/js/modules/stores`：4,738 行（11 文件）
  - `app/static/js/modules/services`：1,819 行（15 文件）
  - `app/static/js/common`：2,285 行（9 文件）
  - `app/static/js/core`：528 行（2 文件）
- 典型“高收益减码区”：Grid/List 类页面脚本（大量重复骨架）+ 自研标签选择器组件（1,200 行量级）+ 页面初始化/订阅模板。

### 1.2 GridWrapper 覆盖的页面（优先试点池）
以下页面明确使用 `GridWrapper`（存在强烈“骨架重复”特征）：
- `app/static/js/modules/views/instances/list.js`
- `app/static/js/modules/views/credentials/list.js`
- `app/static/js/modules/views/accounts/ledgers.js`
- `app/static/js/modules/views/databases/ledgers.js`
- `app/static/js/modules/views/auth/list.js`
- `app/static/js/modules/views/history/logs/logs.js`
- `app/static/js/modules/views/history/sessions/sync-sessions.js`
- `app/static/js/modules/views/tags/index.js`
- `app/static/js/modules/views/admin/partitions/partition-list.js`

这些文件合计约 **7,419 行**，是“第一波减码”最可控的集中战场（结构相似、回归点相对明确）。

### 1.3 当前重复度基线（硬门禁）
- 基线命令：`npx -y jscpd app --format python,javascript,html,css --reporters console --silent --ignore "**/static/vendor/**"`
- 基线结果（2025-12-17）：**3.57% duplicated lines**（2,920 行重复）
- 门禁：任何阶段都不得超过 **5%**；发现重复块必须优先抽共享（禁止复制粘贴式迁移）。

## 2. 你项目里已经有的第三方库（以及“用没用上”）

> 这部分只列“对减码有直接价值”的库。路径以 `app/templates/base.html` 与 `app/static/vendor/` 为准。

| 领域 | 第三方库 | 当前状态 | 现有加载方式 | 备注（减码视角） |
| --- | --- | --- | --- | --- |
| UI 基座 | Bootstrap 5 | 已使用 | `base.html` 全局加载 | 你已经在用 Bootstrap Toast/Modal 等，继续“吃透”能减少自研 UI 脚本 |
| 表格 | Grid.js | 已使用 | 多个页面按需加载 | `GridWrapper` 已做服务端分页/排序封装，减码关键在“页面骨架”而非换表格库 |
| 图表 | Chart.js | 已使用 | 统计/仪表盘页面按需加载 | 图表管理器代码大，但多是业务特化，换库未必减码 |
| 日期时间 | Day.js + 插件 | 已使用 | `base.html` 全局加载 | 统一格式化与时区处理可下沉，避免页面重复逻辑 |
| 事件总线 | mitt | 已使用 | `base.html` 全局加载 | 适合做 store/page 的统一事件协议，减少页面订阅模板 |
| 工具库 | Lodash | 已使用 | `base.html` 全局加载 | 主要用于 debounce/orderBy/uniqBy 等，建议集中封装“真正需要的那几招” |
| DOM/轻量操作 | Umbrella JS | 已使用 | `base.html` 全局加载 | `DOMHelpers` 是二次封装；减码空间有限但可做一致性约束 |
| 数字格式化 | Numeral.js | 已使用 | `base.html` 全局加载 | `number-format.js` 可继续下沉，减少页面重复 |
| 表单校验 | JustValidate | 已使用 | `base.html` 全局加载 | 已有 `FormValidator` 与 `validation-rules.js`，可考虑“减法式”收敛规则表 |
| 选择器增强 | Tom Select | **已引入但疑似未初始化** | `base.html` 全局加载 + 模板支持 `data-tom-select` | 是“替换自研标签选择器”的潜在大收益点 |
| HTTP | Axios | **仓库存在但未加载** | 仅在 `app/static/vendor/axios` | 若启用，可替换 `httpU` 的 XHR 实现并用拦截器统一 CSRF/错误处理 |
| 进度条 | NProgress | **仓库存在但未使用** | `app/static/vendor/nprogress` | 可与 htmx/axios 配合做全局加载反馈，但不是减码核心 |

## 3. “可替换 / 可下沉”清单（面向减码）

> 解释：  
> - **可替换**：用第三方库（或你已 vendored 的库）替掉自研实现，从而**直接删除大量手写代码**。  
> - **可下沉**：不一定换库，但把重复骨架下沉到稳定基座，让页面只保留“差异逻辑”，从而**大幅缩短单页脚本**。  
> 下表按“前端减码 ROI（收益/风险比）”排序。

| 优先级 | 领域 | 现状（代码位置） | 建议动作 | 目标（可删/可缩） | 预计净减码 | 风险与控制点 |
| ---: | --- | --- | --- | --- | ---: | --- |
| P0 | Grid/List 页面骨架 | 9 个 GridWrapper 页面合计约 7,419 行（见 1.2） | **可下沉**：抽 `grid_list_page` 基座（初始化/筛选/分页/批量/订阅/销毁），页面仅保留列定义与少量自定义 renderer | 把每个页面的“模板代码”压到 200~350 行级别 | 3,000 ~ 5,000 | 需冻结页面交互契约（筛选、批量、导出、权限）并逐页回归 |
| P0 | 标签筛选组件 | `app/static/js/modules/views/components/tags/*` 合计 1,203 行 + 关联 store/service | **可替换**：用 Tom Select（多选 + 远端加载 + create）替代自研 modal/preview/controller | 删除自研 controller/view/modal-adapter 的大部分；保留极薄“桥接层”与服务调用 | 800 ~ 1,200 | 标签展示/预览样式、分类/禁用标签、创建标签流程需要对齐现状 |
| P0 | 选择控件增强（筛选下拉） | `templates/components/filters/macros.html` 已支持 `data-tom-select`，但缺少统一初始化 | **可下沉**：补一段“全局初始化器”统一启用 Tom Select（仅对标注的 select 生效） | 让页面不再写“下拉联动/搜索/清空”样板代码 | 200 ~ 600 | 需要确保不破坏原生表单提交与 `filter_card` 自动提交逻辑 |
| P1 | 筛选卡 FilterCard | `app/static/js/modules/ui/filter-card.js`（358 行） + 多页面使用 | **可下沉**：把“表单序列化/触发 submit/事件总线广播/自动提交”收敛到统一协议；若引入 htmx 则可进一步替换 | 减少页面重复的筛选处理代码，避免每页各写一套 | 300 ~ 800 | 不允许破坏 `col-md-2 col-12` 与现有 query 参数兼容性 |
| P1 | 前端 HTTP 客户端 | `app/static/js/core/http-u.js`（352 行） + `common/csrf-utils.js`（215 行） | **可替换**（不新增依赖）：启用已 vendored 的 Axios，做一个薄封装并逐步迁移 services | 删除自研 XHR + 手写序列化/解析分支；统一 CSRF/错误处理 | 200 ~ 500 | 风险集中在：错误码处理、超时/取消、以及旧接口返回结构兼容 |
| P1 | 模态/弹窗封装 | `app/static/js/modules/ui/modal.js`（206 行）+ 页面内重复 modal 操作 | **可下沉**：统一 modal 打开/关闭/加载态/确认对话框模板 | 页面移除重复的 modal 控制代码 | 150 ~ 400 | modal DOM 结构不能大改，否则会影响现有选择器与样式 |
| P2 | 表单校验规则表 | `app/static/js/common/validation-rules.js`（402 行） | **可下沉/可替换**：将规则收敛成“少量通用规则 + 页面级差异规则”，优先删掉重复 message/规则定义 | 规则表从“大全”变成“必需子集” | 100 ~ 300 | 回归重点：字段级错误提示文案与触发时机 |
| P2 | 时间/格式化工具 | `app/static/js/common/time-utils.js`（404 行） | **可下沉**：保留少量“统一格式化 API”，删除页面重复处理与不必要的包装逻辑 | 统一格式化入口，减少页面散落逻辑 | 50 ~ 150 | 确保时区/locale 行为不回归（尤其是列表里的时间显示） |

### 3.1 关键替换点：用 Tom Select 替代自研标签选择器（建议先做）
为什么它是“高收益、低依赖”的替换：
- Tom Select 已全局加载（但当前没有统一初始化/使用），属于“零新增依赖”。
- 现有标签筛选涉及 3 个脚本文件（合计 1,203 行）并被多个列表页复用，是典型的“自研 UI 组件体量过大”。

落地建议（保持功能等价的前提下）：
1. 先做“并行跑”而不是“一刀切”：新建一个仅在某个页面启用的 Tom Select 标签筛选控件（例如 `instances/list`）。
2. 完整对齐现状能力：
   - 多选、搜索、清空、禁用标签（is_active=false 的展示）、提交格式（当前 hidden input 用逗号拼接）。
   - 若现状支持“新建标签”：优先用 Tom Select 的 `create` 能力对齐；必要时再保留一个极薄的 modal 作为 fallback。
3. 完成试点后，才删除旧 controller/view/modal-adapter（否则不计入净减码）。

### 3.2 关键下沉点：Grid/List 页面基座化（不引入新库也能显著减码）
对 Grid/List 页面常见“重复骨架”建议统一下沉到一个基座（示例能力，不是强制接口）：
- 依赖校验：`DOMHelpers`/`GridWrapper`/`httpU`/`mitt` 的存在性检查不应散落各页面。
- Grid 初始化：分页/排序/空态/错误态、统一 fetch headers、统一列宽/通用 renderer。
- 批量选择：checkbox 委托、selection state 与 store 同步。
- FilterCard：统一从筛选表单取值并驱动 grid refresh。
- 生命周期：订阅/解绑/销毁。

这样页面脚本只需要：
- 列定义（columns）与少量 renderer
- 页面独有的 toolbar action
- 页面独有的业务差异（例如额外的批量动作）

## 4. 最小新增依赖方案（推荐：只引入 1 个库）

> 目标：在不引入 React/Vue 这类“框架 + 构建链路”的前提下，显著减少“页面脚本负责一切”的手写代码。  
> 推荐引入：**htmx**（单文件、可渐进迁移、无需打包链路）。

### 4.1 方案 M1：引入 htmx（新增 1 个库，推荐）
**新增内容（最小化）**
- 新增一个 vendor 文件：`app/static/vendor/htmx/htmx.min.js`
- 在 `base.html`（或仅特定页面）引入：`<script src="{{ url_for('static', filename='vendor/htmx/htmx.min.js') }}"></script>`

**减码机制（为什么有效）**
- 让“筛选/分页/排序/局部刷新”从“写 JS 控制状态机”变成“HTML 声明式 + 服务端渲染片段”。
- 你可以把 9 个 Grid/List 页面的大量代码（请求、渲染、状态同步、错误处理）迁回服务端模板与少量通用脚本。

**建议迁移路线（严格保持功能等价）**
1. 先从一个页面试点：`instances/list`（1,318 行）或 `credentials/list`（1,011 行）。
2. 不改外部契约：保留原 API/URL 参数；新增的只是“返回 HTML 片段的 endpoint”或“同一 endpoint 按 Accept 返回 HTML/JSON”。
3. 先替换“筛选 + 列表刷新”，保留批量动作/导出按钮的现有实现；确认稳定后再逐步替换批量/弹窗交互。

**预计净减码（保守估算）**
- 仅把 9 个 Grid/List 页面的“筛选 + 列表渲染”改为 htmx：净减 **3,000~6,000 行**（取决于每页能删掉多少 renderer/状态代码）。
- 如果同时删掉 `GridWrapper` 与部分 FilterCard 逻辑（被 htmx 替代）：再净减 **500~1,200 行**。

**风险与控制**
- 风险：页面交互细节（排序、分页、批量选择、错误提示）回归。
- 控制：以页面为单位逐个迁移；每迁移一个页面，必须跑一次 `jscpd≤5%` 与 `npm run lint:js`，并手工回归关键流程。

### 4.2 方案 M0：不新增任何库（保守线）
如果你暂时不想引入 htmx：
- 只做“基座下沉 + 用现有 Tom Select/Axios”也能减码，但通常更偏“中等收益、低风险”：
  - Grid/List 页面基座化：3,000~5,000 行
  - Tom Select 替换自研标签选择器：800~1,200 行
  - Axios 替换自研 httpU（按需）：200~500 行

## 5. 验收与门禁（建议写进 PR 模板/CI）
1. `app/static/js` 总行数下降趋势明确（每阶段收口必须下降）。
2. `npx -y jscpd app ... --threshold 5` 长期通过（≤5%）。
3. `npm run lint:js` 通过（0 error/warning）。
4. 关键页面回归清单（至少覆盖）：
   - `instances/list`：筛选、分页、排序、批量、导出、权限可见性
   - `credentials/list`：筛选、批量、状态展示、编辑/删除
   - `accounts/ledgers`、`databases/ledgers`：标签筛选、表格刷新与导出
   - `history/logs`、`history/sessions`：筛选、分页、跳转详情

## 6. 附录：统计/门禁命令
- 行数统计：`python3 scripts/code/analyze_code.py app --exclude vendor __pycache__ .git node_modules --top 50`
- 重复度门禁：`npx -y jscpd app --format python,javascript,html,css --reporters console --silent --ignore "**/static/vendor/**" --threshold 5`
- JS 静态检查：`npm run lint:js`

