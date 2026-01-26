---
title: Obsidian frontmatter 重复检查
aliases:
  - obsidian-frontmatter-duplicate-check
tags:
  - reference
  - reference/examples
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: 检查 `title/aliases` 是否重复, 规避 Obsidian 链接歧义与冲突
related:
  - "[[reference/examples/README]]"
  - "[[standards/doc/guide/document-boundary]]"
---

# Obsidian frontmatter 重复检查

## 用法

在仓库根目录运行:

`python3 scripts/dev/docs/obsidian_frontmatter_duplicates.py`

## 输出解读

- `Duplicate aliases`: 同名 alias 被多个文件占用, Obsidian 解析时会出现歧义.
- `Duplicate titles`: 同名 title 被多个文件占用, 也会导致链接歧义.

## 处理建议

- 选择 1 份作为 SSOT, 其余文件:
  - 删除, 或
  - 改为 deprecated stub(保留 alias 并跳转到 SSOT), 或
  - 改为索引入口(仅列链接, 不重复写规则/内容)
