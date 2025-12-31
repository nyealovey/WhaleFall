# 迁移期代码清理方案

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: app/, migrations/, sql/, scripts/, tests/unit/
> 关联: docs/standards/changes-standards.md; docs/standards/documentation-standards.md; docs/standards/backend/database-migrations.md; docs/standards/backend/task-and-scheduler.md; docs/standards/backend/configuration-and-secrets.md

## 动机与范围

- 项目已稳定, 迁移期代码会持续增加理解和维护成本.
- 目标是移除迁移期临时代码, 包括: 临时 API/路由, 数据回填脚本或任务, 迁移开关或 feature flag, 数据格式兼容逻辑.
- 兼容适配保留: 保持 MySQL5 兼容策略, 不做降级或移除.
- 不在范围: 新功能开发, 业务规则调整, 数据库历史迁移脚本修改.

## 不变约束 (行为/契约/性能门槛)

- 除明确移除的数据格式兼容外, 对外 API 行为和权限语义保持不变.
- 保持 MySQL5 兼容能力和现有部署方式.
- 不修改已发布的 migration 历史脚本, 不改变现有数据库 schema 语义.
- 性能基线不回退, 关键路径延迟不增加.

## 分层边界 (依赖方向/禁止项)

- 清理仅限迁移期逻辑, 不引入新的领域概念或持久化模型.
- 代码移除优先从调用链边缘向核心收敛, 避免在核心层引入条件分支.
- 后台任务修改必须在 Flask app.app_context() 内运行, 并遵循现有任务调度约束.

## 分阶段计划 (多 PR)

Phase 0: 代码扫描与审计清单
- 行动:
  - 扫描关键目录: app/, scripts/, sql/, tests/unit/.
  - 关键词扫描: migration, migrate, backfill, compat, legacy, deprecated, feature flag, toggle, fallback, v1/v2.
  - 输出迁移期代码清单, 逐条标注: 位置, 作用, 风险级别, 依赖方, 是否可直接删除.
- 验收:
  - 清单覆盖临时 API/路由, 回填脚本/任务, 迁移开关, 数据格式兼容点.
  - 清单存档并在 progress 中链接.

Phase 1: 移除临时 API/路由
- 行动: 删除迁移期临时接口及路由, 同步更新文档和测试.
- 验收: 相关测试通过, 无引用残留, 对外接口文档不再暴露临时入口.

Phase 2: 移除回填脚本与任务
- 行动: 删除数据回填脚本/任务和调度入口, 清理相关配置.
- 验收: 无任务触发入口残留, 监控和文档同步更新.

Phase 3: 移除迁移开关或 feature flag
- 行动: 清理开关定义, 默认值, 读取逻辑, env.example 对应项.
- 验收: 启动配置不依赖迁移开关, settings 校验通过.

Phase 4: 移除数据格式兼容逻辑
- 行动: 删除旧格式解析, 双写/双读, 字段兜底和转换逻辑.
- 验收: 仅保留新格式路径, 单元测试覆盖新格式, 文档明确格式要求.

Phase 5: 清理与收口
- 行动: 删除废弃代码注释与 TODO, 补齐测试, 更新变更记录.
- 验收: 全部门禁通过, progress Checklist 归档完成.

## 风险与回滚

- 风险: 旧客户端或历史数据仍依赖旧格式.
  - 预防: Phase 0 标注依赖方, 与业务方确认停用时间.
- 风险: 删除任务导致缺失修复通道.
  - 预防: 确认数据回填已完成, 需要时保留可复用脚本模板在 docs/changes/refactor/artifacts/.
- 回滚策略:
  - 回滚某阶段 PR, 恢复对应代码与配置.
  - 如发现旧格式仍被使用, 通过 git revert 恢复兼容逻辑并记录原因.

## 验证与门禁

- 单元测试: `uv run pytest -m unit`
- 格式化: `make format`
- Ruff 报告: `./scripts/ci/ruff-report.sh style`
- Pyright 报告: `./scripts/ci/pyright-report.sh`
- 命名巡检: `./scripts/ci/refactor-naming.sh --dry-run`
- 配置变更门禁: `./scripts/ci/secrets-guard.sh`
- 代码扫描复核: `rg -n "(migration|migrate|backfill|compat|legacy|deprecated|feature flag|toggle|fallback)" app scripts sql tests`
