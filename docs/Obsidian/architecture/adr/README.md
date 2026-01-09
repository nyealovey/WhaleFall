# ADR 使用说明

> ADR（Architecture Decision Record）用于记录“架构决策”和“决策理由”，避免长期演进中出现口径漂移与隐性约束。

## 1. 适用范围

- 架构决策：部署拓扑、进程模型、任务调度拓扑、API 分区与版本化、错误封套、数据迁移策略、日志与可观测性、安全基线、外部依赖韧性策略等。
- 不适用：纯代码实现细节、一次性 bug 修复记录。

## 2. 文件命名

- 建议使用：`NNNN-<kebab-case-title>.md`
- 示例：`0003-secrets-management.md`

## 3. 状态枚举

- Proposed：待讨论/待落地
- Accepted：已采纳并执行
- Deprecated：已废弃（需写替代方案）
- Superseded：被后续 ADR 取代（需指向新 ADR）

## 4. 推荐内容结构

- 背景与问题定义
- 决策
- 备选方案（含取舍）
- 影响范围
- 风险与回退策略
- 验证方式（可观测性/演练/测试）
- 后续行动项

## 5. 待办清单

见：[adr-backlog.md](./adr-backlog.md)
