# Standards Boundary Audit (2026-01-09)

## 摘要结论

- 已补齐 SSOT 边界标准: `docs/Obsidian/standards/doc/document-boundary-standards.md`(standards vs reference vs operations).
- Obsidian frontmatter 冲突(重复 `title/aliases`)目前为 0.
- `docs/Obsidian/standards/**` 中"大段代码块"(单个 code fence >20 行)已清零, 长示例/模板已迁移到 `docs/Obsidian/reference/examples/**` 并由 standards 以链接引用.
- 发现少量标准文档包含明显的 checklist/runbook 倾向内容, 建议拆分并迁移到 `docs/Obsidian/reference/**` 或 `docs/changes/**`.

## 范围与方法

### 范围

- 扫描目录: `docs/Obsidian/standards/**`
- 对照目录: `docs/Obsidian/reference/**`

### 方法

- frontmatter 重复检查: `python3 scripts/dev/docs/obsidian_frontmatter_duplicates.py`
- code fence 长度扫描: 以单个 code fence 行数 >20 作为"大段代码块"判定
- checklist 倾向扫描: `rg -n "Checklist|清单|步骤|Step\\s+\\d+|Run:" docs/Obsidian/standards`

## 发现清单

### P0 - 标准 SSOT 含大段代码块(需迁移到 reference/examples)

> 口径: 单个 code fence >20 行.
> 当前扫描结果: 0 处(已修复).

长示例/模板已迁移到:

- `docs/Obsidian/reference/examples/ui-layer-examples.md`
- `docs/Obsidian/reference/examples/backend-layer-examples.md`
- `docs/Obsidian/reference/examples/scripts-templates.md`
- `docs/Obsidian/reference/examples/testing-examples.md`

### P1 - 标准边界可疑(偏 checklist/runbook/迁移手册)

- `docs/Obsidian/standards/ui/gridjs-migration-standard.md`
  - 已修复: checklist 已迁移到 `docs/Obsidian/reference/development/gridjs-migration-checklist.md`, standards 仅保留规则 + 链接引用.
- `docs/Obsidian/standards/version-update-guide.md`
  - 已修复: 清单与回归检查已迁移到 `docs/Obsidian/reference/development/version-update-checklist.md`, standards 仅保留规则 + 门禁口径 + 链接引用.
- `docs/Obsidian/standards/scripts-standards.md`
  - 已修复: 迁移映射/迁移步骤/兼容性过渡已迁移到 `docs/changes/refactor/026-scripts-directory-structure-migration.md`, standards 仅保留结构 + 硬约束 + 门禁入口.
- `docs/Obsidian/standards/testing-standards.md`
  - 部分修复: 长示例已迁移到 `docs/Obsidian/reference/examples/testing-examples.md` 并由 standards 链接引用.
  - 待评估: "测试状态概览/快速开始"仍偏 reference/runbook, 可后续按边界继续拆分.

### P2 - 重复/冲突风险(当前未命中硬冲突)

- frontmatter 重复(title/aliases): 未发现.
- 文本相似度(去除 frontmatter 与 code blocks 后): 未发现明显重复的 standards 文档对.
- 已处理的边界问题: "新增功能交付标准" 已迁移为 reference checklist, standards 保留 deprecated stub(兼容入口).

## 建议与后续行动

1. 以 `docs/Obsidian/standards/doc/document-boundary-standards.md` 为唯一口径, 逐步把 standards 内的大段代码块迁移到 `docs/Obsidian/reference/examples/**`, 并用 wikilink 引用.
2. 对 "迁移标准/版本更新/脚本规范/测试规范" 做拆分: standards 只保留规则与门禁, checklist/runbook/现状清单落到 reference/changes/operations.
3. 如需门禁化: 可新增 CI guard(例如检测 standards 内 code fence 行数阈值), 但应先在团队内确认阈值与例外(如 mermaid 图).

## 证据与数据来源

- `python3 scripts/dev/docs/obsidian_frontmatter_duplicates.py` 输出:
  - `Duplicate aliases: 0`
  - `Duplicate titles: 0`
- code fence 扫描口径: 单个 code fence 行数 >20 计为 P0.
- 当前扫描结果: `docs/Obsidian/standards/**` 0 处 P0 违规(>20 行 code fence).
