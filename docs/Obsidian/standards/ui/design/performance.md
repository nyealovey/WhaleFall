---
title: 前端性能标准(SSR + Progressive Enhancement)
aliases:
  - ui-performance-standards
tags:
  - standards
  - standards/ui
status: active
enforcement: design
created: 2026-01-24
updated: 2026-01-24
owner: WhaleFall Team
scope: "`app/templates/**` + `app/static/**` 的资源加载, SSR 优先与前端交互增强"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/design/vercel-react-best-practices-mapping]]"
  - "[[standards/ui/design/vendor-library-usage]]"
  - "[[standards/ui/design/layer/page-entry-layer]]"
  - "[[standards/ui/design/layer/views-layer]]"
---

# 前端性能标准(SSR + Progressive Enhancement)

## 目的

- 降低首屏成本: 默认路径更快, 非必需资源不进入首屏.
- 避免"隐式变慢": 防止异步瀑布, 重复请求, 重复事件绑定导致性能劣化.
- 保持可审查: 性能策略能在模板与 Page Entry 层被审查, 而不是散落在各页面脚本.

## 适用范围

- `app/templates/base.html` 及所有页面模板.
- `app/static/js/**`(尤其是 `modules/pages|views|stores|services`).
- `app/static/css/**`.

## 总原则

- SSR first: 首屏关键内容与关键操作由 Jinja 渲染完成.
- Progressive Enhancement: JS 只做增强. JS 失败可以降级, 但不能让核心路径不可用.
- Per-page loading: 资源默认按页引入, `base.html` 只保留全站必需资源.
- No waterfalls: 独立异步任务默认并行, 只有有依赖时才串行.

## 规则(MUST/SHOULD/MAY)

### 1) 资源加载策略(把"bundle size"翻译成 Jinja)

- MUST: `base.html` 只引入"全站每页都需要"的 CSS/JS. 任何 page-only 资源必须放到页面的 `extra_css`/`extra_js`.
- MUST: 新增第三方库(vendor)前必须先回答: "是否每页都用到". 默认答案是 "否", 因此默认按页引入.
- SHOULD: 页面脚本按需引入, 且必须能在没有该脚本时保持页面不报错(例如不存在的 `page_id` 需要 fail-fast 退出).
- SHOULD: 同一资源不得重复引入(例如同一文件被 `base.html` 与页面 `extra_js` 同时引入).
- MAY: 对"高频即将访问"页面做轻量预取(如 prefetch), 但必须可撤销且不能引入全站常驻成本.

### 2) SSR first + Progressive Enhancement

- MUST: 首屏关键数据必须由 SSR 渲染, 不允许页面空壳等待 JS 拉取首屏必需数据.
- MUST: 核心动作必须存在非 JS 路径:
  - 允许: `<form method="post">` 提交后由后端重定向/刷新.
  - 允许: JS 仅用于提升体验(异步提交, toast, 局部刷新).
- SHOULD: JS 增强必须是"幂等 mount": 重复 mount 不应重复绑定事件或造成状态污染.

### 3) 避免异步瀑布(No waterfalls)

- MUST: Page Entry/Views 内的多个独立请求默认并行:
  - 使用 `Promise.all([...])` 或等价策略.
  - 只有存在依赖(后一个请求依赖前一个返回值)时才允许串行, 且必须在代码里写清依赖原因.
- MUST: 不得在页面启动阶段重复请求同一资源:
  - 需要复用的数据应进入 store state, 并通过事件驱动 view 更新.
- SHOULD: 对"可跳过路径"延后 `await` 到分支内部, 避免阻塞未走到的分支.

### 4) DOM 与事件性能

- MUST: 列表/表格行内操作必须使用事件委托, 禁止为每行单独绑定 handler.
- SHOULD: 批量 DOM 更新必须合并:
  - 优先切换 class, 避免循环内频繁读写 layout 相关属性造成 layout thrashing.
- SHOULD: 滚动相关事件默认使用 `passive: true`(除非需要 `preventDefault`).

## 正反例

### 正例: 并行请求 + 失败短路

```javascript
async function loadInitialData(serviceA, serviceB) {
  const [a, b] = await Promise.all([serviceA.list(), serviceB.list()]);
  return { a, b };
}
```

### 反例: 无依赖却串行 await(瀑布)

```javascript
async function loadInitialData(serviceA, serviceB) {
  const a = await serviceA.list();
  const b = await serviceB.list(); // 反例: 与 a 无依赖, 却被串行阻塞
  return { a, b };
}
```

## 门禁/自查

```bash
# 1) 关注 base.html 的全站引入是否膨胀
rg -n \"<script |<link \" app/templates/base.html

# 2) 查找页面模板是否把 page-only 资源误塞进 base
rg -n \"\\{%\\s*block\\s+extra_(css|js)\\s*%\\}\" -S app/templates

# 3) 启发式查找串行瀑布(需要人工复核, 不是硬门禁)
rg -n \"await\\s+.*\\n\\s*await\\s+\" app/static/js -S

# 4) 查找可能的重复事件绑定(需要人工复核)
rg -n \"addEventListener\\(\" app/static/js/modules -S
```

