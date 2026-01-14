---
title: 第三方库(vendor)使用标准
aliases:
  - vendor-library-usage-standards
tags:
  - standards
  - standards/ui
status: active
created: 2026-01-14
updated: 2026-01-14
owner: WhaleFall Team
scope: "`app/templates/**` 引入的 vendor 库(bootstrap/chartjs/dayjs/lodash/mitt/numeral/umbrella/just-validate/fontawesome 等)及其项目封装(common/core/modules)"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/layer/README]]"
  - "[[standards/ui/javascript-module-standards]]"
---

# 第三方库(vendor)使用标准

## 目的

- 统一第三方库的入口, 避免在各处直接依赖 vendor global 导致插件/locale/timezone/行为分叉.
- 提供可审查的封装层, 让升级/替换/回滚第三方库更可控.
- 降低隐式全局耦合, 让分层规则与门禁更可执行.

## 总原则(MUST/SHOULD)

- MUST: 业务代码优先使用项目封装, 不直接调用 vendor global.
- MUST: 若需要补齐能力(新格式/新 helper/新事件规范), 应优先扩展封装层, 而不是在 view/store/service 内新增零散实现.
- MUST: `window.*` 的访问边界以 [[standards/ui/layer/README#全局依赖(window.*) 访问规则(SSOT)|全局依赖(window.*) 访问规则(SSOT)]] 为单一真源.
- SHOULD: 若确需直接访问 vendor global, 必须在评审中说明原因, 并给出收敛到封装层的计划.

## 现有入口(扫描摘要)

> [!note] 说明
> 本节用于把"当前仓库已存在的封装入口"显式化, 避免新代码重复造轮子.

- dayjs: `window.timeUtils`/`window.TimeFormats` -> `app/static/js/common/time-utils.js`
- numeral: `window.NumberFormat` -> `app/static/js/common/number-format.js`
- lodash: `window.LodashUtils` -> `app/static/js/common/lodash-utils.js`
- mitt:
  - 跨组件同步/观测: `window.EventBus` -> `app/static/js/common/event-bus.js`
  - store 私有 emitter: `options.emitter` 注入, 未传入回退 `window.mitt()`
- umbrella:
  - DOM: `window.DOMHelpers` -> `app/static/js/core/dom.helpers.js`
  - HTTP: `window.httpU` -> `app/static/js/core/http-u.js`
- bootstrap(modal): `window.UI.createModal` -> `app/static/js/modules/ui/modal.js`
- just-validate: `window.FormValidator`/`window.ValidationRules` -> `app/static/js/common/form-validator.js` + `app/static/js/common/validation-rules.js`

## 库级规则

### Grid.js(列表表格)

- MUST: Grid 列表页遵循 [[standards/ui/grid-standards|Grid 列表页标准]], 禁止在页面脚本直接 `new gridjs.Grid(...)` 或绕过 `Views.GridPage`.

### Bootstrap(交互组件)

推荐入口:

- SHOULD: Modal 优先使用 `window.UI.createModal(...)`, 统一事件清理与 loading 行为.
- MAY: 在 view 内直接使用 `window.bootstrap.Modal`, 如存在组件卸载/重复挂载场景, 则必须在 `destroy()` 中 `dispose()`.

约束说明:

- 禁止把 bootstrap 的实例管理逻辑散落在各页面(例如重复写 `shown.bs.modal/hidden.bs.modal` 清理); 应收敛到 `UI.createModal` 或等价封装.

### Chart.js(图表)

推荐入口:

- SHOULD: 优先复用已有图表组件(例如 `app/static/js/modules/views/components/charts/**`), 而不是在页面脚本里堆叠 Chart.js 配置.
- MUST: 任意重渲染/刷新必须先 `chart.destroy()`.
- SHOULD: 颜色与语义色使用 `window.ColorTokens`, 数值/百分比/容量格式使用 `window.NumberFormat`.

### JustValidate(表单校验)

推荐入口:

- MUST: 使用 `window.FormValidator.create(...)` 初始化校验, 并使用 `window.ValidationRules` 复用规则与文案.
- MUST NOT: 在业务代码中直接 `new JustValidate(...)` 或自定义一套重复的 rules/messages.
- MUST: modal/页面重复初始化时, 旧 validator 必须 `destroy()` 后再创建.

### Day.js(时间)

推荐入口:

- MUST: 使用 `window.timeUtils`/`window.TimeFormats` 进行解析与格式化.
- MUST NOT: 在 `app/static/js/modules/**` 内直接使用 `window.dayjs(...)` 或 `dayjs(...)`.

约束说明:

- `timeUtils` 负责 locale/timezone 与常见 parse formats 的单一真源.
- 如需新增插件或扩展 parse formats, 只能在 `app/static/js/common/time-utils.js` 内修改并复用.

### Numeral.js(数字格式化)

推荐入口:

- MUST: 使用 `window.NumberFormat.*`(如 `formatInteger/formatDecimal/formatBytes/formatPercent`)输出用户可见数字.
- MUST NOT: 直接调用 `window.numeral(...)` 或手写重复的千分位/字节/百分比格式化.

### Lodash(数据处理)

推荐入口:

- MUST: 使用 `window.LodashUtils`(封装后的 allowlist 方法).
- MUST NOT: 在业务代码中直接使用 `window._` 或解构 `_.xxx`.

约束说明:

- `LodashUtils` 通过 bind 规避 lodash 方法解构导致的 this 丢失风险.
- 如需新增 lodash 方法, 先在 `app/static/js/common/lodash-utils.js` 扩展 allowlist, 再在业务代码使用.

### mitt(事件)

推荐入口:

- UI 跨组件同步/观测: MAY 使用 `window.EventBus`(不得做业务编排).
- Stores: SHOULD 使用私有 emitter, 并支持 `options.emitter` 注入; 未传入时才回退 `window.mitt()`.

禁止项:

- MUST NOT: Services/Stores 内使用 `window.EventBus`(原因: 形成全局耦合与隐式 side effects).

事件命名:

- SHOULD: 遵循 `<domain>:<action>` 约定(参考 [[standards/ui/layer/stores-layer-standards#5) 事件命名与释放|Stores: 事件命名与释放]]).

### Umbrella.js(DOM/HTTP)

推荐入口:

- DOM: MUST 使用 `window.DOMHelpers`(选择/读写/disabled 切换/ready).
- HTTP: MUST 使用 `window.httpU` 作为 http client(或由 Page Entry 注入), 禁止直接使用 `u.ajax`.
- MUST NOT: 在业务代码里直接调用 `window.u(...)` 或依赖 umbrella 私有行为.

### Font Awesome(图标)

- SHOULD: 纯装饰图标加 `aria-hidden="true"`.
- SHOULD: 图标按钮必须具备可访问名称(如 `aria-label`), 参考 [[standards/ui/close-button-accessible-name-guidelines]].

## 门禁/自查

```bash
# 禁止在 modules 内直接调用 vendor global(示例)
rg -n "\\bdayjs\\(" app/static/js/modules
rg -n "\\bnumeral\\(" app/static/js/modules
rg -n "\\b_\\." app/static/js/modules
rg -n "\\bu\\(" app/static/js/modules
rg -n "new\\s+JustValidate\\b" app/static/js/modules
```

## 变更历史

- 2026-01-14: 新增 vendor 库使用标准, 覆盖 dayjs/lodash/mitt/numeral/umbrella/bootstrap/chartjs/just-validate/fontawesome 的入口与约束.
