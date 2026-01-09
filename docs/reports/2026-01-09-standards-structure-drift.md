# Standards Structure Drift Audit (2026-01-09)

## 摘要结论

- `docs/Obsidian/standards/**` 中存在"标准结构一致性漂移": 部分文档未显式包含 `目的/适用范围/规则/正反例/门禁/变更历史` 等可扫描结构.
- 索引类文档(README/入口索引)与 deprecated stub 属于"可预期例外", 但应在审计时单独标记, 避免误判.

## 范围与方法

### 范围

- 扫描目录: `docs/Obsidian/standards/**`

### 方法

- 逐文件提取 Markdown headings(`#` 行), 以"是否存在包含关键字的标题"判定结构是否齐全.
- 必需关键字(standards 结构): `目的`, `适用范围`, `规则`, `正反例`, `门禁/检查方式`, `变更历史`.

> [!note] 说明
> 该方法是"结构化可扫描"口径, 不是内容质量判断.
> 某些文档可能包含对应内容但未以标题显式呈现, 仍会被判为缺失.

## 发现清单

### A. 索引类/入口类(可预期例外)

- `docs/Obsidian/standards/README.md`: purpose, scope, rules, examples, gates, history
- `docs/Obsidian/standards/backend/README.md`: purpose, scope, rules, examples, gates, history
- `docs/Obsidian/standards/backend/layer/README.md`: purpose, scope, rules, examples, gates, history
- `docs/Obsidian/standards/doc/README.md`: purpose, scope, rules, examples, gates, history
- `docs/Obsidian/standards/ui/README.md`: purpose, scope, rules, examples, gates, history
- `docs/Obsidian/standards/ui/layer/README.md`: purpose, scope, rules, examples, gates, history

### B. Deprecated stub(可预期例外)

- `docs/Obsidian/standards/new-feature-delivery-standard.md`: purpose, scope, rules, examples, gates

### C. 可能需要补齐结构的 standards 文档

- `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md`: examples
- `docs/Obsidian/standards/backend/write-operation-boundary.md`: purpose, scope, rules, examples
- `docs/Obsidian/standards/doc/api-contract-markdown-standards.md`: examples, gates, history
- `docs/Obsidian/standards/doc/changes-standards.md`: scope, examples
- `docs/Obsidian/standards/doc/documentation-standards.md`: purpose, scope, examples
- `docs/Obsidian/standards/doc/service-layer-documentation-standards.md`: purpose, examples, gates, history
- `docs/Obsidian/standards/scripts-standards.md`: rules, examples
- `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md`: examples
- `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`: examples
- `docs/Obsidian/standards/ui/grid-list-page-skeleton-guidelines.md`: scope, rules, examples
- `docs/Obsidian/standards/ui/javascript-module-standards.md`: examples

## 建议

1. 明确例外口径: 对 README/索引类 standards, 允许省略标准结构章节, 但必须在 frontmatter `scope` 中显式标记"入口与索引".
2. 对 C 类文档二选一:
   - 补齐章节标题(不必扩写内容), 让结构可扫描; 或
   - 若其本质更像 guideline/reference, 则调整归类并由 standards 链接引用.

## 证据与数据来源

- 扫描口径: "是否存在包含关键字的 Markdown headings".

