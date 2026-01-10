# Prompts 与协作模板

> 状态：Draft

本目录用于存放可复用的提示词与协作模板（评审清单、专项分析提示等）。

## 约定

- 新增文件名统一使用英文 `kebab-case.md`。
- 本目录下 prompts 默认产出 "审计报告类文档": 输出应保存到 `docs/reports/`, 并遵守 `docs/Obsidian/standards/doc/documentation-standards.md` 中 `reports/*` 的最小结构与命名规范.
- 单次会话的临时产物不要长期堆放在这里：
  - 若与具体变更绑定，放到 `changes/`。
  - 若是评审结论，放到 `reports/`。
  - 过期内容进入 `_archive/`。

## 索引

- `architecture.md`
- `database.md`
- `frontend.md`
- `performance.md`
- `refactor.md`
- `security.md`
