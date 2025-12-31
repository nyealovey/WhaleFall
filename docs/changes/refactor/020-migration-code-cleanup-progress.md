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

## Checklist

Phase 0: 代码扫描与审计清单
- [x] 输出迁移期代码清单并归档到 docs/changes/refactor/artifacts/
- [x] 标注需保留的兼容适配(仅 MySQL5 等环境兼容)
- [x] 标注所有数据格式兼容点并列为待移除项

Phase 1: 移除临时 API/路由
- [ ] 删除迁移期临时 API/路由
- [ ] 更新相关文档与测试

Phase 2: 移除回填脚本与任务
- [ ] 删除回填脚本与任务
- [ ] 清理调度入口与配置

Phase 3: 移除迁移开关或 feature flag
- [ ] 删除开关定义与读取逻辑
- [ ] 清理 env.example 与 settings 校验

Phase 4: 移除数据格式兼容逻辑
- [ ] 删除旧格式解析和兜底转换
- [ ] 补齐新格式测试与文档

Phase 5: 清理与收口
- [ ] 移除废弃注释, TODO, 兼容分支残留
- [ ] 完成门禁与验证, 更新变更记录

## 变更记录

- 2025-12-31: 建立 plan 与 progress 文档.
- 2025-12-31: 输出 Phase 0 扫描清单 docs/changes/refactor/artifacts/020-phase0-migration-code-inventory.md.
