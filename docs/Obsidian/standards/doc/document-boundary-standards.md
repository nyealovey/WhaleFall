---
title: 文档边界与归类标准(standards vs reference)
aliases:
  - document-boundary-standards
tags:
  - standards
  - standards/doc
status: active
created: 2026-01-09
updated: 2026-01-10
owner: WhaleFall Team
scope: "`docs/Obsidian/**` 与 `docs/changes/**` 的文档归类, SSOT 边界与冲突处理"
related:
  - "[[standards/doc/documentation-standards]]"
  - "[[standards/halfwidth-character-standards]]"
  - "[[standards/README]]"
  - "[[reference/README]]"
  - "[[operations/README]]"
  - "[[architecture/README]]"
  - "[[reference/service/README]]"
---

# 文档边界与归类标准(standards vs reference)

> [!important] SSOT
> 本文定义"文档应该放哪里"与"什么才算标准"的边界, 用于解决: 标准被写成参考手册/功能说明/执行清单, 导致 SSOT 漂移与审查成本上升.

## 目的

- 定义 `docs/Obsidian/**` 各目录的语义边界, 避免不同类型文档混写.
- 让新增/迁移/重构文档时有明确判定规则, 可审查, 可回滚.
- 为"冲突/重复"提供统一处理口径, 避免同一主题出现多份 SSOT.

## 适用范围

- Obsidian vault 内的所有笔记:
  - `docs/Obsidian/standards/**`
  - `docs/Obsidian/reference/**`
  - `docs/Obsidian/reference/service/**`
  - `docs/Obsidian/operations/**`
  - `docs/Obsidian/architecture/**`
  - `docs/Obsidian/API/**`
- vault 外但与归类强相关的目录:
  - `docs/changes/**`
  - `docs/plans/**`
  - `docs/reports/**`

## 规则(MUST/SHOULD/MAY)

### 1) 目录边界(语义定义)

> [!note] 原则
> 一份文档必须有且只有一个"主类型". 如果同时满足多个类型, 必须拆分为多份文档, 并用 wikilink 互相链接.

| 目录                              | 主类型                | 核心问题                        | 允许包含                                        | 禁止包含                                                       |
| ------------------------------- | ------------------ | --------------------------- | ------------------------------------------- | ---------------------------------------------------------- |
| `docs/Obsidian/standards/**`    | 标准(SSOT)           | "我们必须/应该如何做"                | MUST/SHOULD/MAY, 门禁/检查方式, 最小示例(≤20 行), 变更历史 | 功能说明书, 字段/参数表(仅参考用), 逐步执行清单(以操作为主), 大段代码/可运行脚本             |
| `docs/Obsidian/reference/**`    | 参考手册(SSOT)         | "它是什么/参数是什么/契约是什么"          | 字段表, 默认值, 示例, 契约说明                          | 开发流程标准, 组织规范, 门禁规则(应引用 standards)                          |
| `docs/Obsidian/operations/**`   | Runbook            | "怎么部署/怎么回滚/怎么排障"            | 可复制执行的步骤, 风险提示, 验证与回滚                       | 研发编码标准(应引用 standards), 设计动机与长篇背景(应放 architecture)          |
| `docs/Obsidian/architecture/**` | 架构设计               | "为什么这样设计/关键边界是什么"           | ADR, 分层边界的设计理由, 关键数据流与取舍                    | 可执行的运维步骤(应放 operations), 作为规则 SSOT 的 MUST 列表(应放 standards) |
| `docs/Obsidian/reference/service/**` | 服务实现解读(Service Docs) | "某个 service 具体怎么工作/失败语义是什么" | 流程图, 决策表, 兼容/兜底清单, 调用方与依赖                   | 对全仓通用的规则 SSOT(应放 standards)                                |
| `docs/Obsidian/API/**`          | API contract(SSOT) | "对外 API 的 endpoint 清单是什么"   | method/path 清单, 关键约束(摘要), 指向实现与 OpenAPI     | 把 contract 写成大段实现说明(应放 reference/service/architecture)                |
| `docs/changes/**`               | 变更记录               | "这次改了什么/怎么验收/怎么回滚"          | plan/progress/record, 验证命令, 影响面             | 把长期规则写进 changes(应上升为 standards)                            |
| `docs/plans/**`                 | 计划(执行向)            | "如何一步步落地"                   | 任务拆解, 验证点                                   | 作为最终 SSOT 的规则(应迁移到 standards/reference)                    |
| `docs/reports/**`               | 报告(阶段性)            | "我们发现了什么/风险是什么"             | 发现清单与证据                                     | 作为长期规则 SSOT(应迁移到 standards)                                |

### 2) standards vs reference 的判定

- MUST: 如果文档的核心目的是"约束未来的实现与协作方式", 它属于 `standards/**`.
  - 典型特征: 有 MUST/SHOULD/MAY, 有门禁/检查方式, 会被 PR review 用作硬依据.
- MUST: 如果文档的核心目的是"描述稳定的接口/字段/参数/契约", 它属于 `reference/**` 或 `API/**`.
  - 典型特征: 以表格/字段说明/示例为主, 面向查阅, 很少出现"开发者应该如何组织代码"的规则.
- SHOULD: 当同一主题同时需要"规则"与"字段/契约", 必须拆分:
  - standards: 写约束与门禁
  - reference + API: 写契约与字段表(按类型选择, 不要混写)
    - reference: `docs/Obsidian/reference/**`: 字段/参数/默认值/示例(面向查阅)
    - API: `docs/Obsidian/API/**`: `/api/v1/**` 的 endpoint 清单(method/path)与摘要约束(面向审查)

### 3) "功能标准"的处理原则

> [!warning] 禁止混写
> 以"功能/交付"为主题的文档, 很容易把"规则 SSOT"与"执行清单"混在一起.

- MUST: "执行清单/交付 checklist" 放在 `reference/development/**`(查阅型), 不放在 standards.
- MUST: standards 只定义硬约束(例如必须补变更文档, 必须跑哪些门禁), 不把每一步操作展开成 runbook.
- MAY: standards 内保留旧文件作为 deprecated stub(仅做跳转), 用于兼容历史链接, 但必须标记 `status: deprecated` 并指向新位置.

### 4) 正反例/示例与代码块的边界

> [!important] 标准 SSOT 不放大段代码
> 标准的价值是"约束与边界", 不是"复制粘贴可运行实现". 大段代码会导致:
> - 读者把标准当成实现模板, 进而产生 drift 与不一致实现
> - 标准 diff 噪音大, 审查成本高

- MUST: `standards/**` 内的代码块必须保持"最小示例"原则:
  - 单个 code fence 建议 ≤20 行.
  - 超过该长度的完整实现/脚本/正反例, 必须迁移到 `docs/Obsidian/reference/examples/**`, 并在 standards 内用 wikilink 引用.
- SHOULD: standards 中的"正反例"章节只写"判定点"(规则要点), 不粘贴完整实现.
- MAY: 对于必须保留的最小片段, 优先使用伪代码/截断片段, 并说明"只表达边界, 不是可直接复制的实现模板".

### 5) 去重原则(单一真源)

- MUST: 同一主题只能有 1 份 SSOT:
  - 标准 SSOT: `docs/Obsidian/standards/**`
  - 契约 SSOT: `docs/Obsidian/reference/**` 或 `docs/Obsidian/API/**`
- MUST: 发现重复时, 必须选择一份作为 SSOT, 其余:
  - 删除, 或
  - 改为 deprecated stub(保留 alias/跳转), 或
  - 改为索引入口(只列链接, 不再重复解释)

### 6) 冲突处理原则(标准之间)

- MUST: 发现标准冲突时, 不允许"各写各的"长期共存, 必须合并或明确优先级.
- SHOULD: 优先级默认规则:
  1) scope 更窄/更具体的标准优先(例如 `standards/ui/layer/**` 优先于 `standards/coding-standards`)
  2) 同 scope 冲突时, 以明确标注 SSOT 的文档为准, 并通过 PR 解决冲突
- MUST: 冲突解决后, 需要更新索引入口与相关 wikilinks, 避免读者继续读到旧规则.

## 正反例

### 正例: 标准(规则 SSOT)

- `docs/Obsidian/standards/backend/write-operation-boundary.md`
- `docs/Obsidian/standards/ui/layer/README.md`

### 正例: 参考手册(契约 SSOT)

- `docs/Obsidian/reference/config/environment-variables.md`
- `docs/Obsidian/reference/database/schema-baseline.md`

### 正例: Runbook(操作手册)

- `docs/Obsidian/operations/deployment/production-deployment.md`

### 正例: 服务层文档(实现说明)

- `docs/Obsidian/reference/service/accounts-sync-overview.md`

### 正例: API contract(清单 SSOT)

- `docs/Obsidian/API/api-v1-api-contract.md`

### 反例: 把执行清单写成标准

- 以 "交付 checklist" 为主体, 但放在 `standards/**` 且作为规则 SSOT, 会导致:
  - 标准边界被稀释(审查依据不清)
  - 后续更难拆分与归档

## 门禁/检查方式

> [!note] 说明
> 目前仓库内未提供一键自动化门禁. 以下命令用于人工自查/排查, 可在后续脚本化.

### 1) 检查 aliases/title 重复(Obsidian 冲突高风险)

运行: `python3 scripts/dev/docs/obsidian_frontmatter_duplicates.py`

参考输出与用法说明: [[reference/examples/obsidian-frontmatter-duplicate-check|Obsidian frontmatter 重复检查]]

### 2) 检查 standards 是否出现明显"清单/功能说明"倾向

```bash
rg -n "Checklist|清单|步骤|Step\\s+\\d+|Run:" docs/Obsidian/standards
```

### 3) 半角字符自查(文档新增/修改前)

```bash
rg -n -P "[\\u3000\\u3001\\u3002\\u3010\\u3011\\uff01\\uff08\\uff09\\uff0c\\uff1a\\uff1b\\uff1f\\u2018\\u2019\\u201c\\u201d\\u2013\\u2014\\u2026]" docs/Obsidian
```

## 变更历史

- 2026-01-09: 基于现有 vault 结构补齐"standards vs reference"边界定义, 并补充示例/代码块的归类口径与自查入口.
