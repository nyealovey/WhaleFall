# 迁移期代码清理设计

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: app/, scripts/, sql/, tests/unit/, env.example
> 关联: docs/changes/refactor/020-migration-code-cleanup-plan.md; docs/changes/refactor/020-migration-code-cleanup-progress.md

## 目标与范围

- 移除迁移期临时代码: 临时 API/路由, 回填脚本或任务, 迁移开关, 数据格式兼容逻辑.
- 保留环境兼容: MySQL5 兼容能力保持, 不做降级.
- 不修改历史迁移脚本, 不改变现有 schema 语义.

## 核心策略

- 采用风险优先分阶段, 每阶段独立 PR, 可单独回滚.
- 统一 fail-fast: 遇到旧格式或旧结构直接报错并中断流程, 以尽快暴露遗留依赖.
- 清理顺序: 数据格式兼容与迁移开关 -> 回填逻辑 -> 前端与 CORS 旧路径兼容 -> 迁移脚本与文档工具.

## 行为约束与回滚

- 不变约束: 对外 API 行为不做功能扩展, 仅移除旧格式兼容.
- 回滚策略: 每阶段通过 git revert 回滚; 若发现旧依赖, 先恢复兼容逻辑再修复数据或调用方.

## 验证与门禁

- 单元测试: `uv run pytest -m unit`.
- 代码质量门禁: `make format`, `./scripts/ci/ruff-report.sh style`, `./scripts/ci/pyright-report.sh`.
