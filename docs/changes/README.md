# 变更记录

> 状态: Active

本目录用于沉淀与 PR/Issue 对齐的变更文档(feature/bugfix/refactor/docs/perf/security).

## 规则摘要

- 文档应描述 "为什么改, 改了什么, 怎么验证, 怎么回滚".
- `docs/changes/**` 下新增文档必须带三位编号前缀(每个子目录从 `001` 开始递增), 详见 `../Obsidian/standards/doc/guide/documentation.md`.
- 多 PR / 多阶段推进的事项 SHOULD 拆分为 `*-plan.md`(方案) 与 `*-progress.md`(进度), 详见 `../Obsidian/standards/doc/guide/changes.md`.
- 变更完成且无需持续维护时, 按 `../Obsidian/standards/doc/guide/documentation.md` 的规则归档到 `../_archive/`.

## 子目录(入口)

- feature: `docs/changes/feature/`
- bugfix: `docs/changes/bugfix/`
- refactor: `docs/changes/refactor/`
- docs: `docs/changes/docs/`
- perf: `docs/changes/perf/`
- security: `docs/changes/security/`
