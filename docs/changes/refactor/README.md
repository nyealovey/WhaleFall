# Refactor 变更

> 状态: Active

本目录用于记录行为不变的结构性调整 (重构, 瘦身, 抽象, 拆分, 兼容/回退逻辑清理等).

## 命名规则

- 本目录及其子目录下新增文档文件名必须使用三位编号前缀 (每个子目录从 `001` 开始递增): `NNN-short-title.md`.
- 多 PR / 多阶段推进的事项 SHOULD 拆分为:
  - `NNN-short-title-plan.md`
  - `NNN-short-title-progress.md`

## 写作规范

详见: `../../Obsidian/standards/doc/changes-standards.md`.

## 如何查找

- 按编号: `ls docs/changes/refactor | sort`
- 按关键词: `rg -n \"keyword\" docs/changes/refactor`
- 按 PR/Issue: 从 PR 描述或 `docs/changes/README.md` 入口进入
