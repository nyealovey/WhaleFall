---
title: Vercel React Best Practices 到 Flask + Jinja 的映射
aliases:
  - vercel-react-best-practices-mapping
tags:
  - standards
  - standards/ui
  - reference
status: active
enforcement: design
created: 2026-01-24
updated: 2026-01-24
owner: WhaleFall Team
scope: 将 Vercel React Best Practices 的核心性能思想映射到 SSR(Jinja) + Progressive Enhancement 的落地策略
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/performance-standards]]"
  - "[[standards/ui/vendor-library-usage-standards]]"
  - "[[standards/ui/layer/page-entry-layer-standards]]"
---

# Vercel React Best Practices 到 Flask + Jinja 的映射

> [!note] 说明
> 原文面向 React/Next.js, 但其核心是"减少无谓客户端成本 + 避免瀑布 + 让默认路径更快". 在 Flask + Jinja(SSR) 项目中, 这些原则依然成立, 只是落点从"组件/Hook"迁移为"模板结构 + 资源加载 + Page Entry wiring + 少量增强 JS".

## 1) 一句话抓住核心

- React/Next 的核心目标: 少发 JS, 少做 hydration, 少做无谓重渲染, 避免 async waterfall, 让首屏更快.
- Flask/Jinja 的等价目标: SSR 输出首屏与关键数据, JS 只做增强(交互, 校验, 局部刷新), 并通过"按需加载"把页面成本降到最低.

## 2) 类别映射表(React/Next -> Flask/Jinja)

| 原则类别(原文) | React/Next 常见落点 | Flask/Jinja 的等价落点 | 本仓库标准入口 |
|---|---|---|---|
| Eliminating Waterfalls | `await` 串行, API route 串行, Suspense 边界不当 | Page Entry/Views 的多请求并行(`Promise.all`), 后端路由一次性准备页面数据, 避免页面启动时再串行拉首屏必需数据 | [[standards/ui/performance-standards]] |
| Bundle Size Optimization | 避免 barrel import, dynamic import, defer third-party | `base.html` 只放全站必需资源, vendor 默认按页引入, 页面脚本只在需要的模板里加载 | [[standards/ui/vendor-library-usage-standards]] |
| Server-Side Performance | RSC 序列化边界, per-request dedupe, cache | 后端路由/服务层避免 N+1, 模板不做重计算, SSR 输出尽量接近最终 UI, 可缓存的在后端缓存 | [[standards/backend/layer/services-layer-standards]] |
| Client-Side Data Fetching | dedupe listener, SWR, storage 版本化 | 避免重复绑定全局事件, 统一 store/view 生命周期, localStorage 只保存最小必要且要版本化 | [[standards/ui/layer/views-layer-standards]] |
| Re-render Optimization | derived state, memoization, effect deps | DOM 更新做"最小改动", 避免整块 re-render, 事件处理放在 handler, 共享状态集中到 store | [[standards/ui/layer/stores-layer-standards]] |
| Rendering Performance | content-visibility, SVG precision | 长列表优先 SSR + 分页, 或使用 `content-visibility`, 避免大 SVG/复杂阴影导致渲染开销 | [[standards/ui/design-token-governance-guidelines]] |
| JavaScript Performance | batch DOM/CSS, cache loops | 批量 DOM 变更(类名切换), 事件委托, 避免 layout thrashing | [[standards/ui/layer/views-layer-standards]] |
| Advanced Patterns | init once, stable refs | 全局模块只初始化一次, 页面 mount/destroy 可重复执行且不泄漏 | [[standards/ui/layer/page-entry-layer-standards]] |

## 3) 在本仓库的可执行落地(不依赖 React)

### A. SSR 优先 + Progressive Enhancement

- 首屏可读/可操作必须由模板输出完成, JS 仅增强体验.
- JS 失败时允许"体验降级", 但不允许"不可用".

### B. 资源按需加载(把"bundle size"翻译成 Jinja 语言)

- 默认策略: 资源按页加载, 只有"全站每页都用到"的才进入 `base.html`.
- 任何新增 vendor 必须先回答: 这是不是每页都需要? 如果不是, 就按页引入.

### C. 避免异步瀑布(把"await waterfall"翻译成 Page Entry/Views 语言)

- 如果页面启动必须发多个请求, 默认并行.
- 只有存在依赖关系时才允许串行, 并在代码里写清楚依赖原因.
- 对同一资源的重复请求要 dedupe, 优先复用 store 状态/缓存.

## 4) 非目标

- 不引入新的前端构建工具(ESM bundler, React, Next.js).
- 不把"性能优化"当成口号式的微优化, 优先做结构性收益: 按需加载, SSR 优先, 避免瀑布, 生命周期可清理.

