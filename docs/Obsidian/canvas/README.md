---
title: WhaleFall Canvas
aliases:
  - canvas
tags:
  - canvas
  - canvas/index
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: docs/Obsidian/canvas 下 .canvas 文件约定与入口
related:
  - "[[architecture/README]]"
  - "[[architecture/flows/README]]"
  - "[[standards/doc/documentation-standards]]"
---

# WhaleFall Canvas

本目录存放 WhaleFall 的 `.canvas` 文件, 用于在 Obsidian 里维护可编辑的架构图/流程图.

## 约定(Mermaid <-> Canvas)

- Mermaid: 文档内的渲染版本, 便于在 Markdown 里 review 与 diff.
- Canvas: 可编辑版本, 用于协作讨论与后续迭代(推荐先改 Canvas, 再同步 Mermaid).
- MUST: 每个出现在 `docs/Obsidian/architecture/**` 的 Mermaid 图, 都要有一个对应的 `docs/Obsidian/canvas/**.canvas`.
- MUST: 文档与 Canvas 相互引用.
  - 文档 -> Canvas: 在 Mermaid 图下方增加 `Canvas: [[canvas/...]]`.
  - Canvas -> 文档: Canvas 内增加一个 `file` node 指向对应 `.md`, 并尽量使用 `subpath` 指到图标题.

## 重要边界

- API contract 的 SSOT 是 `docs/Obsidian/API/**-api-contract.md`, Canvas 不能作为 contract SSOT.

## 关键入口(少量)

- [[canvas/global-system-architecture.canvas]]
- [[canvas/global-c4-l1-system-context.canvas]]
- [[canvas/global-layer-first-module-dependency-graph.canvas]]
- [[canvas/cross-cutting-capabilities.canvas]]

## 全量浏览(不维护手工清单)

```query
path:"canvas"
```
