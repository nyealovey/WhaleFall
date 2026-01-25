---
title: Jinja 模板组织与复用标准
aliases:
  - jinja-template-composition-standards
tags:
  - standards
  - standards/ui
status: active
enforcement: design
created: 2026-01-24
updated: 2026-01-24
owner: WhaleFall Team
scope: "`app/templates/**` 的页面结构, 组件化复用, 数据下发与资源按需加载"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/performance-standards]]"
  - "[[standards/ui/template-event-binding-standards]]"
  - "[[standards/ui/layer/page-entry-layer-standards]]"
  - "[[standards/ui/component-dom-id-scope-guidelines]]"
---

# Jinja 模板组织与复用标准

## 目的

- 让页面模板保持"薄": 只表达结构与意图, 不承载业务编排与交互实现.
- 降低复制粘贴: UI 结构复用通过 components/macros 收敛, 避免每页一套实现.
- 固化数据下发与 hook: 模板只下发 dataset 与 `data-action`, 交互由 JS 分层实现.

## 适用范围

- `app/templates/**` 下所有页面与组件模板.

## 规则(MUST/SHOULD/MAY)

### 1) 页面结构(统一骨架)

- MUST: 页面模板必须 `extends "base.html"`.
- MUST: 页面必须设置 `page_id`, 供 `page-loader` 启动.
- SHOULD: 页面仅通过 `extra_css`/`extra_js` 引入 page-only 资源, 禁止把页面私有资源塞进 `base.html`.

正例:

```jinja2
{% extends "base.html" %}
{% set page_id = "InstancesListPage" %}

{% block extra_js %}
  <script src="{{ url_for('static', filename='js/modules/views/instances/list.js') }}"></script>
{% endblock %}
```

### 2) 模板复用优先级(从低成本到高成本)

- MUST: 优先复用已有 components/macros, 再考虑新增.
- SHOULD: 相同结构重复 >= 3 次时, 抽到 `templates/components/**`.
- SHOULD: 如果一个 UI 结构跨页面复用, 应优先抽为 macro/组件, 而不是复制粘贴.
- MUST NOT: 为了"可能复用"提前抽象复杂 macro, 导致调用参数爆炸或阅读成本变高.

### 3) 数据下发契约(dataset)

- MUST: 页面配置必须通过"单一根节点"下发 dataset, 避免把数据散落在多个不相关节点.
- MUST: dataset key 使用 `kebab-case`, JS 侧通过 `dataset.camelCase` 读取.
- SHOULD: 对 dataset 中的动态键名建立 allowlist, 禁止透传危险键到对象写入/URL 参数.

### 4) 事件与 hook(模板只声明意图)

- MUST NOT: 模板内联事件处理器(`onclick="..."` 等), 见 [[standards/ui/template-event-binding-standards]].
- MUST: 通过 `data-action="..."` 等 hook 声明意图, 由 JS 侧绑定事件或事件委托.

### 5) 模板中的逻辑边界

- MUST: 模板内允许的逻辑仅限于:
  - 轻量 `if/for` 展示逻辑.
  - 字段存在性检查与显示分支.
- MUST NOT: 在模板里做"重计算"或发起查询/调用, 需要的数据必须在后端路由/服务层准备好.
- SHOULD: 避免在 `for` 循环内拼装复杂字符串与条件组合, 优先在后端准备好展示字段.

## 正反例

### 正例: 模板只声明意图, JS 做绑定

```html
<button type="button" class="btn btn-primary" data-action="refresh">
  刷新
</button>
```

### 反例: 模板内联 onclick

```html
<button onclick="refresh()">刷新</button>
```

## 门禁/自查

```bash
# 1) 页面是否设置 page_id
rg -n \"\\{%\\s*set\\s+page_id\\s*=\\s*\" app/templates

# 2) 禁止 inline handler
rg -n \"\\son[a-zA-Z]+\\s*=\\s*\\\"\" app/templates

# 3) 组件与宏位置是否合理(人工复核)
find app/templates/components -type f | head
```

