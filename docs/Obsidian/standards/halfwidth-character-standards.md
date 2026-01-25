---
title: 半角字符与全角字符禁用规范
aliases:
  - halfwidth-character-standards
tags:
  - standards
  - standards/general
status: active
enforcement: guide
created: 2025-12-26
updated: 2026-01-25
owner: WhaleFall Team
scope: "`docs/**` 文档, 代码注释, Docstring"
related:
  - "[[standards/doc/documentation-standards]]"
---

# 半角字符与全角字符禁用规范

> [!note]
> 本规范的目标是“减少隐形字符与易混淆字符”, 避免复制粘贴与 diff 产生噪音. 不要求中文内容强行改用英文标点.

## 目的

- 避免全角空格/不换行空格等不可见字符导致的格式错乱与隐性错误.
- 避免“全角 ASCII 变体”混入代码相关文本(路径/命令/标识符/键名), 造成复制粘贴失败或难以检索.

## 适用范围

- 文档: `docs/**` 下所有 Markdown.
- 注释: Python `#`, docstring, JS/CSS `//` `/* ... */`, Jinja2 注释等.

不适用/不强制:

- 用户可见文案/错误消息/测试夹具等业务数据字符串(它们不是注释). 如产品侧也需要统一, 另行制定文案规范.

## 规则(MUST/SHOULD/MAY)

- SHOULD: 新增或修改的文档/注释遵循本规范. 存量内容遵循"越改越干净"原则, 在改动附近顺手清理.

### 1) 禁止不可见/易混淆空白字符(MUST NOT)

- MUST NOT: 使用全角空格 `\x{3000}`.
- MUST NOT: 使用不换行空格 `\x{00A0}`(NBSP).

原因: 这两类字符往往肉眼不可见, 会造成对齐错乱/复制粘贴失败/难以检索.

### 2) 代码相关文本必须使用半角 ASCII(SHOULD)

对于“代码相关文本”, SHOULD 使用半角 ASCII, 避免全角 ASCII 变体导致 copy/search 失败. 代码相关文本包括:

- 代码块与 inline code(反引号包裹的部分)
- 文件路径/命令/字段名/函数名/路由/关键字/环境变量名

注: 正文叙述(中文段落)允许使用中文标点, 本规范不强制统一为英文标点.

### 3) 例外(仅限必要场景)(MAY)

- MAY: 在讨论"字符本身"的技术文档里, 使用 Unicode code point(如 `\x{FF1A}`)表达问题字符, 避免直接粘贴全角字符造成二次污染.

## 正反例

### 注释

反例:

```python
# 注意\uFF1A这里需要兜底
```

正例:

```python
# 注意: 这里需要兜底
```

## 门禁/检查方式

- 评审检查: 优先处理“不可见空白字符”和“代码相关文本中的全角 ASCII 变体”.
- 自查命令(示例, 不要求 0 命中, 主要用于定位隐形字符):

```bash
# 定位不可见空白字符
rg -n -P "[\\x{3000}\\x{00A0}]" docs app scripts tests

# 定位常见的“全角 ASCII 变体”(可选)
rg -n -P "[\\x{FF01}-\\x{FF5E}]" docs app scripts tests
```

## 变更历史

- 2025-12-26: 新增半角字符要求, 禁用全角/非 ASCII 标点与全角空格.
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
- 2026-01-25: 减负: 收敛为“不可见字符 + 代码相关文本”两类约束, 不再把中文叙述标点作为硬约束.
