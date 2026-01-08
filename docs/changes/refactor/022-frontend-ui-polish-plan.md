# 022 frontend ui polish plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: `app/templates/**`, `app/static/css/**`
> 关联: `docs/Obsidian/standards/documentation-standards.md`, `docs/Obsidian/standards/changes-standards.md`, `docs/Obsidian/standards/halfwidth-character-standards.md`, `docs/Obsidian/standards/ui/README.md`

---

## 动机与范围

目标: 在不改变后端接口与页面架构的前提下, 修复当前 UI 体系中的"断层"与"漂移", 让设计 token, 组件样式与模板用法一致, 并补齐最基础的响应式与可访问性基线.

本计划覆盖:

- 页面头部: `page_header` 组件的描述信息渲染与一致的视觉层级.
- 响应式基线: `<meta name="viewport">` 与 navbar toggler(含可访问名称).
- 字体系统: Inter 与 `--font-family-base` 的收敛, 避免"定义但不生效".
- 轻量标签组件: `chip-outline` / `ledger-chip` 的样式收敛, 避免页面级重复定义与跨文件 `@import` 耦合.
- 动效与可访问性: 收敛 `transition: all`, 增加 `prefers-reduced-motion` 降噪.
- 危险语义: danger confirm modal 的视觉语义强化(不改交互流程).

非目标:

- 不重写模板体系(Jinja2)或引入新的前端框架.
- 不调整路由, API, 数据结构, 也不修改页面信息架构(IA)与功能编排.
- 不新增颜色 token 或改变品牌色策略(沿用 `app/static/css/variables.css`).

## 现状扫描摘要

### 1) 页面头部信息层级缺失

- `page_header` 传入了 `description`, 但组件未渲染该字段: `app/templates/components/ui/page_header.html`.
- 全局样式已为 `p` 预留样式, 但当前不会出现: `app/static/css/global.css`.

影响: 页面标题区缺少副标题, 信息密度上升, 新用户难以快速理解页面意图.

### 2) 响应式基线缺失

- 缺少 `<meta name="viewport">`: `app/templates/base.html`.
- navbar 使用了 `.navbar-expand-lg` 与 `.collapse`, 但缺少 toggler 按钮, 移动端不可展开导航: `app/templates/base.html`.

影响: 小屏/移动端可用性显著不足, 且不符合 Bootstrap 预期用法.

### 3) 字体体系漂移

- `theme-orange.css` 定义 `--bs-body-font-family: 'Inter', ...`: `app/static/css/theme-orange.css`.
- `global.css` 又覆盖了 `body { font-family: system stack }`, 导致 Inter 实际不生效: `app/static/css/global.css`.
- `--font-family-base` 定义后未被引用: `app/static/css/variables.css`.

影响: 字体策略不一致, 未来维护容易出现"改了但没变"的错觉.

### 4) chip 组件样式重复与耦合

- `chip-outline` / `ledger-chip` 在多个页面 CSS 中重复定义, 且存在 `@import` 复用: `app/static/css/pages/*`, `app/static/css/components/tag-selector.css`, `app/static/css/pages/about.css`.

影响: 样式漂移风险高, 同名 class 在不同页面表现不一致, 也增加维护成本.

### 5) 动效与可访问性降噪不足

- 多处使用 `transition: all`(例如 card, dropdown, pagination), 不利于性能与可控性: `app/static/css/global.css`, `app/static/css/components/buttons.css`.
- 缺少 `prefers-reduced-motion` 路径, 无法为不适用户提供降噪: `app/static/css/global.css`, `app/static/css/pages/auth/login.css`.

### 6) 危险确认弹窗的视觉语义偏弱

- 全局 `.modal-header` 统一使用品牌色, danger confirm modal 与普通 modal 视觉上不够区分: `app/static/css/global.css`, `app/templates/components/ui/danger_confirm_modal.html`.

## 不变约束(行为/契约/性能门槛)

- 后端接口不变: 路由, API, payload, 返回结构均不调整.
- 页面架构不变: 不重排导航信息架构, 不重构页面布局结构(仅补齐缺失元素与收敛样式).
- token 治理不变: 不引入硬编码颜色, 遵循 `docs/Obsidian/standards/ui/design-token-governance-guidelines.md` 与 `docs/Obsidian/standards/ui/color-guidelines.md`.
- 桌面端体验不退化: 1920x1080 与 2560x1440 基线视口下信息密度与可读性不低于现状(见 `docs/Obsidian/standards/ui/layout-sizing-guidelines.md`).
- class API 尽量稳定: `chip-outline`, `ledger-chip`, `status-pill` 等既有 class 名称保持可用, 避免改动引发模板连锁变更.

## 分层边界(依赖方向/禁止项)

- `variables.css` 只定义 token, 不写组件规则.
- `global.css` 只覆盖全局基线(布局壳, 统一卡片/表单/分页/模态基线), 不包含具体业务页面定制.
- `css/components/**` 放可复用组件(例如 chips, buttons, table, filters), 允许被页面复用.
- `css/pages/**` 只放页面私有差异, 禁止复制通用组件定义(例如 `chip-outline`).

## 分阶段计划(每阶段验收口径)

### Phase 0: 基线与验收口径

目标: 固定验证口径与回滚方式, 避免"边改边漂移".

步骤:

- 运行 UI 相关门禁:
  - `./scripts/ci/css-token-guard.sh`
  - `./scripts/ci/component-style-drift-guard.sh`
  - `./scripts/ci/inline-px-style-guard.sh`
- 若涉及按钮语义与确认弹窗, 额外运行:
  - `./scripts/ci/button-hierarchy-guard.sh`
  - `./scripts/ci/danger-button-semantics-guard.sh`
- 记录 3 个代表性页面的基线检查点(桌面 + 小屏):
  - Dashboard: `app/templates/dashboard/overview.html`
  - Grid list: `app/templates/instances/list.html`
  - Logs: `app/templates/history/logs/logs.html`

验收:

- 门禁通过, 或在 `progress` 文档中记录已知失败项与原因.

回滚:

- 通过 git revert 回退本阶段改动.

### Phase 1: page header 描述渲染补齐

目标: 恢复标题区"标题 + 副标题"的信息层级, 且不影响不传 description 的页面.

步骤:

- 在 `app/templates/components/ui/page_header.html` 中渲染 `description`, 并使用已有 `.page-header__title p` 样式.
- 保持 `description` 可选, 不要求所有页面立刻补齐.

验收:

- 已传 `description` 的页面展示副标题, 未传的页面无空白占位.

回滚:

- 回退 `page_header` 模板改动即可.

### Phase 2: 响应式基线修复(viewport + navbar toggler)

目标: 让 Bootstrap navbar 的 collapse 在小屏可用, 且满足基本可访问性.

备注: 当前确认该站点仅面向桌面端使用(确认日期: 2026-01-04), 本阶段暂不执行, 作为未来需要支持小屏时的可选项保留.

步骤:

- 在 `app/templates/base.html` 补齐 `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- 为 navbar 增加 toggler 按钮, 绑定 `data-bs-toggle="collapse"` 与 `data-bs-target="#navbarNav"`.
- toggler 必须具备可访问名称(例如 `aria-label="展开或收起导航"`), 并满足 btn-close / icon button 的可访问约束风格(参考 `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md`).

验收:

- 小屏宽度下可展开/收起导航, 且无明显布局抖动.

回滚:

- 回退 `base.html` 的新增 meta 与按钮即可.

### Phase 3: 字体系统收敛

目标: 统一"全站正文用什么字体"的单一真源, 避免 token 与实际渲染不一致.

决策点(二选一, 选其一并明确写入 progress):

- A: 全站启用 Inter 作为正文, system stack 作为 fallback.
- B: 全站继续使用 system stack, Inter 仅作为可选资产或移除其引用.

当前决策: A (确认日期: 2026-01-04)

步骤(通用):

- 确保 `body` 字体只由一个入口决定(本计划选择 `--font-family-base` 为真源, 并令 `--bs-body-font-family` 引用它).
- 清理重复覆盖, 避免同一属性在多个文件里互相打架.

验收:

- 主要页面(至少 Dashboard, Instances list, Logs)字体一致, 且无"局部掉回系统字体"现象.

回滚:

- 回退字体相关 CSS 覆盖改动即可.

### Phase 4: chip 组件样式收敛

目标: 把 `chip-outline` / `ledger-chip` 从页面 CSS 中收敛为组件, 避免重复定义与 `@import` 耦合.

步骤:

- 新增 `app/static/css/components/chips.css`, 作为 `chip-outline`, `ledger-chip`, `ledger-chip-stack` 的唯一基线定义.
- 在 `app/templates/base.html` 引入 `chips.css`.
- 逐步移除页面 CSS 内对同名 class 的重复定义, 页面仅保留必要的 spacing/布局差异.
- `tag-selector.css` 只保留 tag selector 组件本身差异, 不再作为 chips 的"事实来源".

验收:

- `rg -n \"\\.chip-outline\\b|\\.ledger-chip\\b\" app/static/css/pages` 不再命中基础定义(允许命中修饰器或容器限定规则).
- 核心页面 chips 展示一致, 不因页面不同而出现 padding/字号漂移.

回滚:

- 如遇风险, 允许先保留旧定义一段时间, 但必须在 `progress` 中记录"保留原因 + 清理截止阶段".

### Phase 5: 动效收敛与 reduced motion 支持

目标: 在保持现有精致感的前提下, 降低不必要的动效与性能开销.

步骤:

- 将关键组件的 `transition: all` 收敛为具体属性(例如 `transform`, `box-shadow`, `background-color`).
- 增加 `@media (prefers-reduced-motion: reduce)`:
  - 禁用非必要的入场动画(`fadeIn`, `slideInUp`)
  - 将 hover 位移类动效降级为无位移或更短时间

验收:

- 默认模式下视觉效果不明显退化.
- `prefers-reduced-motion: reduce` 下页面不会持续触发明显动画.

回滚:

- 回退 `prefers-reduced-motion` 与 transition 收敛改动即可.

### Phase 6: danger confirm modal 视觉语义强化

目标: 不改流程, 只让危险确认在视觉上更"像危险", 降低误触.

步骤:

- 为 `.danger-confirm-modal` 增加 scoped CSS:
  - header 使用 danger 语义色或弱化品牌色, 与普通 modal 拉开差异
  - 保持 close button 可见(必要时调整 `filter: invert()` 范围)
- 不改 `UI.confirmDanger` 的行为, 不新增防御性分支.

验收:

- danger confirm modal 与普通 modal 在首屏视觉上可区分.
- 通过 `./scripts/ci/danger-button-semantics-guard.sh`.

回滚:

- 回退新增 CSS 即可.

## 兼容/适配/回退策略(如存在)

- 模板兼容: `page_header` 的 `description` 渲染保持可选, 不要求所有调用点同步修改.
- 样式兼容: `chip-outline` / `ledger-chip` 保持 class 名称不变, 收敛只改变"定义位置", 不改变调用方式.
- 渐进回退: chips 收敛阶段允许短期保留旧定义(避免一次性影响面过大), 但必须在 `progress` 中记录保留原因与清理截止阶段.
- 响应式适配: 新增 viewport 与 navbar toggler 为增量改动, 桌面端布局不应改变; 如出现影响, 优先以最小 CSS scoped 修复而非改动模板结构.

## 验收指标

- 组件一致性: chips 组件在多个页面表现一致, 且基础定义收敛到 `css/components/`.
- 信息层级: `page_header` 能展示 description, 标题区可读性提升.
- 可用性: navbar 在小屏可展开/收起, 且有可访问名称.
- 可访问性: 支持 `prefers-reduced-motion`, 动效可降噪.
- 门禁: `css-token-guard`, `component-style-drift-guard` 通过.

## 清理计划(删除旧实现/兼容逻辑)

- chips: 删除 `app/static/css/pages/**` 内对 `.chip-outline` / `.ledger-chip` 的基础定义, 页面仅保留必要的局部修饰.
- imports: 移除页面级 `@import` 作为 chips 复用手段(例如 `about.css`), 统一由 `base.html` 引入组件 CSS.
- 动效: 全局与组件 CSS 中逐步清理 `transition: all`, 以可控属性替代.

## 风险与回滚

- 兼容性风险: `color-mix`, `oklch`, `backdrop-filter` 在旧浏览器可能不生效. 本计划不新增类似能力, 但在修改过程中避免扩大其使用面.
- 样式回归风险: chips 收敛可能影响多个页面. 缓解: 分阶段落地, 每阶段做代表页面回归, 并保持可快速 revert.
- 字体变更风险: 字体切换会影响字号与行高观感. 缓解: Phase 3 先做小范围验证, 再全局收敛.

## 验证与门禁

- UI token: `./scripts/ci/css-token-guard.sh`
- 样式漂移: `./scripts/ci/component-style-drift-guard.sh`
- 模板 inline px: `./scripts/ci/inline-px-style-guard.sh`
- 按钮语义(如涉及): `./scripts/ci/button-hierarchy-guard.sh`
- 危险按钮语义(如涉及): `./scripts/ci/danger-button-semantics-guard.sh`
- 半角字符(文档与注释): `rg -n -P \"[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]\" docs app scripts tests`

## 附录: 关键文件清单(便于检索)

- base 模板: `app/templates/base.html`
- page header: `app/templates/components/ui/page_header.html`
- tokens: `app/static/css/variables.css`
- global baseline: `app/static/css/global.css`
- chips(现状分散): `app/static/css/components/tag-selector.css`, `app/static/css/pages/*`
- danger modal: `app/templates/components/ui/danger_confirm_modal.html`
