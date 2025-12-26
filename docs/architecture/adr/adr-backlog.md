# ADR 待办清单（Backlog）

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-25
> 更新：2025-12-26
> 范围：架构决策待办清单
> 关联：./README.md；../../standards/documentation-standards.md

> 说明：本清单用于把“缺失的架构决策与约束”变成可执行文档任务。优先级可按 P0→P2 推进。

## P0

1. ADR-003：Secrets 管理与轮换（哪些必须固定、如何注入、轮换步骤、禁止提交策略）
2. ADR-001：部署拓扑与进程模型（入口边界、端口暴露最小化、Gunicorn 并发模型）
3. ADR-007：日志策略（stdout/DB/文件、脱敏、保留、导出权限、审计）
4. ADR-006：健康检查语义（live/ready）与 SLO（依赖判定、超时、返回码）

## P1

5. ADR-002：Scheduler 拓扑（是否独立进程、jobstore 选型、幂等/去重/补偿、告警信号）
6. ADR-004：API 分区与版本化（internal vs public、认证方式、CSRF/CORS 对齐）
7. ADR-005：错误封套与兼容窗口（message/error 漂移治理、前端兜底削减与监控）
8. ADR-008：外部依赖失败策略（timeout/retry/circuit-break、缓存降级、限流）

## P2

9. ADR-009：数据迁移策略（Alembic 规则、滚动发布兼容、回滚策略、schema 版本）
10. ADR-010：前端供应链治理（vendor manifest/校验和/升级回滚；是否引入构建工具）

