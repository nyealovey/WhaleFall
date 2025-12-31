# 迁移期代码清理进度

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: app/, migrations/, sql/, scripts/, tests/unit/
> 关联: ./020-migration-code-cleanup-plan.md

关联方案: ./020-migration-code-cleanup-plan.md

## 当前状态

- Phase 0 清单已输出, 见 docs/changes/refactor/artifacts/020-phase0-migration-code-inventory.md.
- Phase 1 已完成: 已移除 connections test 旧结构兼容与 legacy CORS 资源匹配; 权限快照严格校验与分类 DSL v4 迁移清理已完成.
- Phase 2-4 已完成: 已移除运行时回填逻辑/迁移开关/数据格式兼容点(tag_names, pageSize/limit)并补齐防御测试.
- Phase 5(部分) 已完成: 已移除 ops userdata->volume 迁移入口与 docs route tooling 脚本(MIG-012/013).
- Phase 5(部分) 已完成: 已清理 docs/plans 中对已移除 doc tooling 的引用, 并更新 scripts standards 中的文档脚本映射说明.
- 门禁验证: `uv run pytest -m unit` / `make format` / secrets-guard / refactor-naming / touched-files ruff check 通过；repo-wide ruff(style) 与 pyright(full) 仍存在既有 baseline 问题(不在本次清理范围).

## Checklist

Phase 0: 代码扫描与审计清单
- [x] 输出迁移期代码清单并归档到 docs/changes/refactor/artifacts/
- [x] 标注需保留的兼容适配(仅 MySQL5 等环境兼容)
- [x] 标注所有数据格式兼容点并列为待移除项

Phase 1: 移除临时 API/路由
- [x] 删除迁移期临时 API/路由
- [x] 更新相关文档与测试

Phase 2: 移除回填脚本与任务
- [x] 删除回填脚本与任务
- [x] 清理调度入口与配置

Phase 3: 移除迁移开关或 feature flag
- [x] 删除开关定义与读取逻辑
- [x] 清理 env.example 与 settings 校验

Phase 4: 移除数据格式兼容逻辑
- [x] 删除旧格式解析和兜底转换
- [x] 补齐新格式测试与文档

Phase 5: 清理与收口
- [x] 移除废弃注释, TODO, 兼容分支残留
- [x] 完成门禁与验证, 更新变更记录（以 unit tests + 本次改动范围门禁为准）

## 变更记录

- 2025-12-31: 建立 plan 与 progress 文档.
- 2025-12-31: 输出 Phase 0 扫描清单 docs/changes/refactor/artifacts/020-phase0-migration-code-inventory.md.
- 2025-12-31: Phase 1 - 移除 connections test `data.result` 兼容结构, 收紧 CORS 到 `/api/v1/**`, 补齐相关单测与修复测试隔离问题.
- 2025-12-31: Phase 2-4 - 移除 tag_names 字符串兼容与前端 pageSize/limit 兼容, 并补齐防御测试.
- 2025-12-31: Phase 5(部分) - 删除 `scripts/ops/docker/volume_manager.sh` 的 migrate 子命令与 `Makefile.prod` 的 migrate-volumes 目标.
- 2025-12-31: Phase 5(部分) - 移除 `scripts/dev/docs` 下的迁移期 doc tooling 脚本(MIG-012/013)与文档引用.
- 2025-12-31: Phase 5(部分) - 清理 docs/plans 中对已移除 doc tooling 的引用, 并更新 scripts standards 中的文档脚本映射说明.
- 2025-12-31: Phase 5 - 完成门禁验证并修复 `tests/unit/routes/test_api_v1_partition_contract.py` 的日期硬编码导致的用例漂移问题.
