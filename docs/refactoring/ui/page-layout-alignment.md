# 页面头部与内容宽度对齐重构方案

## 背景
- 线上在日志中心、仪表盘等多个页面出现“顶部菜单下方的标题区域（`.page-header`）宽度与下方表格/卡片不一致”的现象（见截图）。
- 产品希望标题区与页面主体保持强一致，以营造统一的视觉节奏并便于后续组件复用。
- 项目整体使用 Flask + Bootstrap（Flatly 主题），但模板和 CSS 经过多次叠加式迭代，存在容器类混用、局部样式覆盖等问题，导致尺寸不一致。

## 现状分析

| 模块 | 文件 | 主要问题 |
| --- | --- | --- |
| 全局布局 | `app/templates/base.html`, `app/static/css/global.css:69-211` | `body > .main-content > .container` 强制了 1320px 宽度，同时 `page-header` 又包裹一层 `.container`，等于在 1320px 里再套 1140px；而多数页面正文使用 `.container-fluid` 或自定义 `row`，实际宽度取决于外部 `.main-content .container`，造成“标题窄、内容宽”的视觉错位。 |
| 页面头部 | 15+ 页面（例如 `app/templates/history/logs/logs.html:8-42`, `app/templates/dashboard/overview.html:8-38`） | 头部结构完全复制，包含 `.page-header > .container > .d-flex`，没有复用组件，且难以批量注入统一的间距/按钮区。 |
| 内容网格 | 多数列表页使用 `.container-fluid` 包裹卡片/表格，再嵌套 `.row`。由于 `.container-fluid` 横向 padding 为 `var(--bs-gutter-x)`，实际宽度比 `.page-header`（无 padding）更宽，在 1280px~1440px 的常见桌面分辨率下也会出现明显错位。 |
| 样式层 | `.page-header` 在 `app/static/css/global.css:194-211` 中固定 `padding: var(--spacing-xl) 0`，缺少内层容器控制；与 `.logs-page`, `.credentials-page` 等页面级样式错误叠加。 |

## 根因
1. **容器类型混乱**：`container`、`container-fluid`、自定义 `page` 容器交替嵌套，缺乏单一的布局壳（layout shell）。
2. **头部组件缺位**：没有可复用的 `page_header()` 宏或组件，导致每个模板各自调整。
3. **CSS 不成体系**：`global.css` 与页面 CSS 没有通过变量约束宽度，导致后续维护只能“叠 patch”。

## 改造目标
1. 标题、筛选区、表格/卡片在视觉宽度上保持 100% 对齐（与导航容器一致）。
2. 建立统一布局壳：顶部导航、面包屑、头部、内容区共用同一组栅格变量。
3. 通过宏/组件降低模板重复度，便于后续维护深色视觉风格。
4. 色彩体系由独立文档《色彩体系统一（去渐变化）》负责，本篇聚焦布局与栅格壳体。

## 设计与方案

### 1. Layout Shell 统一规范
- **新增 CSS**：在 `app/static/css/global.css` 中增加 `.layout-shell`、`.layout-wide`, `.layout-narrow` 等壳样式，通过 CSS 变量 `--layout-max-width` 控制最大宽度。
- **Base 模板调整**：将 `base.html` 中 `<div class="main-content"><div class="container">` 替换为 `<div class="main-content"><div class="layout-shell">`，layout-shell 内部再根据需要渲染 `.layout-content`，避免默认注入 Bootstrap `.container`。
- **模板抽象**：`base.html` 新增 `content_outer` 区块，默认包裹在 `.layout-shell` + `.layout-shell-inner` 内；需要自定义 `page-section` 组合的页面可覆盖该区块并直接输出新的布局壳。
- **媒体查询**：在 `variables.css` 中定义断点映射，使 layout-shell 在 `xl` 以上维持固定宽度，在更大屏幕允许轻微增量（例如 1320 -> 1440）。

### 2. 页面头部组件化
- 在 `app/templates/components/ui/page_header.html`（新文件）中实现宏：
  ```jinja2
  {% macro page_header(icon=None, title='', description=None, size='lg') -%}
  <header class="page-header page-header--{{ size }}">
    <div class="layout-shell">
      <div class="layout-shell-inner">
        <div class="page-header__body">
          <div class="page-header__content">
            {% if icon %}<span class="page-header__icon"><i class="{{ icon }}"></i></span>{% endif %}
            <div class="page-header__title">
              <h1>{{ title }}</h1>
              {% if description %}<p>{{ description }}</p>{% endif %}
            </div>
          </div>
          {% if caller is defined %}<div class="page-header__actions">{{ caller() }}</div>{% endif %}
        </div>
      </div>
    </div>
  </header>
  {%- endmacro %}
  ```
- 头部内部使用 `.layout-shell-inner` 控制与主体一致的水平 padding。
- 现有页面全部替换为宏调用，确保结构一致。

### 3. 内容区容器策略
- 引入 `.page-section` 工具类：`<section class="page-section page-section--fluid">` 内部自动应用 `layout-shell-inner`，再根据 `--gap` 控制卡片间距。
- 列表/统计页面统一改用：
  ```html
  <section class="page-section">
    <div class="page-grid">
      ...
    </div>
  </section>
  ```
  其中 `.page-grid` 封装 `.row` 与 gutter，避免手写 `.container-fluid`.

### 4. 间距与紧凑性策略
- **统一垂直节距变量**：在 `variables.css` 中定义 `--page-spacing-tight`, `--page-spacing-regular`，`page-header` 与 `page-section` 默认使用 `regular`，当页面设置 `data-density="compact"` 时自动降为 `tight`（例如 24px → 16px）。
- **参考 UI（ui.shadcn）**：截图显示标题区完成后与图表/筛选控件之间仅约 16~20px 的留白，卡片之间的间距一致。我们需复刻这种“紧凑而不拥挤”的节奏，将 `page-header` 的底部间距锁定在 20px，并允许通过 `data-density="compact"` 将相邻 `page-section` 间距压缩到 16px；常规模式下保持 24px。
- **头部与筛选区的距离**：`page-header` 结尾增加 `margin-bottom: var(--page-spacing-regular)`，而 `page-section` 的 `padding-top` 为 0，使两者之间的视觉间隔由单一变量控制；桌面端保持 24~32px，通过 `data-density="compact"` 可进一步压缩为 16px。
- **筛选区与表格卡片**：`filter_card` 宏外层包裹 `.page-section`，并通过 `page-section--stacked` 修饰类将相邻块的 `margin-top` 设置为 `var(--page-spacing-tight)`。表格卡片 `.card` 增加 `margin-top: var(--page-spacing-tight)`，确保过滤器与表格保持 16-20px 的间隔。
- **自适应策略（桌面断点）**：在 1440px 以上保持 1320~1440px 固定宽度，1280px 以下逐步减小 `layout-shell` 的左右 Padding，重点保证常规桌面分辨率（1280/1366/1440）下的视觉一致性，无需针对更小屏幕做特殊折行。

### 5. 依赖文件关系图
```
base.html
 ├── 引用 page_header 宏（新的 components/ui/page_header.html）
 ├── layout-shell (global.css)
 └── 页面内容 (各模板) -> page-section, page-grid
```


> 色彩体系统一与 Flatly→Shadcn 覆盖方案现已拆分至《color-system-unification.md》，如需配色细节请参考该文档。

## 改造步骤

1. **基线准备**
   - 在 `global.css` 与 `variables.css` 中声明新的布局变量与壳样式。
   - 新建 `components/ui/page_header.html` 宏，并在 `docs/refactor-table-styles.md` 中更新引用示例。

2. **模板批量替换**
   - 第一阶段覆盖最常用的 6 个页面：仪表盘、日志中心、凭据、实例列表、账户列表、数据库统计。
   - 使用 `{{ page_header(...) }}` 替换原有的 `<div class="page-header">` 块。
   - 同时将 `container-fluid` 调整为 `page-section` 结构。

3. **样式细化**
  - 编写 `page-header__body`, `page-header__actions`, `page-section` 样式，重点优化桌面端列间距即可。
   - 检查 `app/static/css/pages/**` 是否存在 `margin-top`, `padding` 等局部覆写，必要时迁移或移除。

4. **脚本/组件联动**
   - 筛选卡片等组件（`components/filters/macros.html`）若依赖 `.container-fluid` 宽度，需要同步更新 CSS 选择器，避免因父级变更导致样式错位。

5. **验证流程**
   - 本地 `make dev start-flask` 运行后手动检查 PC 端 1440px、1280px、1024px 三种宽度。
   - 运行 `make quality` 确认没有 lint / 命名违规，必要时执行 `./scripts/refactor_naming.sh --dry-run`。

## 风险与回滚
- **风险：** 改动 global layout 可能影响所有页面；需通过 feature flag 或分阶段发布。
- **回滚策略：** `<body data-layout="legacy">` 可作为开关，CSS 中使用 `[data-layout="legacy"] .page-header { ... }` 保留原样，确保问题时可快速切换。

## 验收标准
1. 所有页面头部与下方表格/卡片在 1280px 以上屏幕下左右对齐偏差 < 4px。
2. Lighthouse/Chrome DevTools 设备模拟中，`page_header`、`page-section` 在 768px 以下断点自动改为纵向布局。
3. QA 逐页截图比对通过，并在 `docs/reports/界面巡检.md` 中附上“命名规范”检查记录。

## 后续建议
- 将布局壳逻辑沉淀为 Jinja + Web Component（例如 `<page-shell>`），便于未来引入前后端分离。
- 在 `docs/refactor-table-styles.md` 与设计稿之间对齐，形成 UI 规范库。
