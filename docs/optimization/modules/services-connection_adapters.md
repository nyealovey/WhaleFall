# services/connection_adapters + services/connections

## Core Purpose

- 为“连接测试/连接参数校验/连接状态查询”提供可复用的 Service 能力：
  - 连接适配器选择与实例化（ConnectionFactory）
  - 连接测试与版本解析（ConnectionTestService）
  - 连接状态读取（InstanceConnectionStatusService）
  - 写路径 payload 解析/校验（InstanceConnectionsWriteService）

## Unnecessary Complexity Found

- （已落地）`app/services/connection_adapters/connection_factory.py:65`：对 `Instance.db_type` 进行 `getattr + str + None fallback` 的防御性样板。
  - 连接工厂与适配器本质依赖 `db_type` 字段；该字段在 ORM 与临时测试实例中都稳定存在。

- （已落地）`app/services/connections/instance_connection_status_service.py:34-67`：用 `object + getattr` 组装 payload。
  - 实际来源是 `InstancesRepository.get_instance()`（ORM Instance），字段是稳定的；`getattr` 会掩盖契约并增加噪音。

## Code to Remove

- `app/services/connection_adapters/connection_factory.py:65`：移除对 `db_type` 的多余防御性取值（可删 LOC 估算：~2-4）。
- `app/services/connections/instance_connection_status_service.py:34-67`：移除 `getattr` 样板，改为基于 `Instance` 的直接字段访问（可删 LOC 估算：~6-12）。

## Simplification Recommendations

1. 工厂与状态读取：直接使用稳定的 ORM 字段
   - Current: `getattr(..., default)` 让读者误以为字段可能缺失。
   - Proposed: 以模型字段为契约，Service 仅做轻量映射与格式化。
   - Impact: 降噪、降低分支与默认值误导风险。

## YAGNI Violations

- `connection_factory` 中对 `Instance.db_type` 的“字段可能不存在”的兜底（缺少明确运行时证据）。

## Final Assessment

- 可删 LOC 估算：~8-16（已落地）
- Complexity: Low -> Lower
- Recommended action: Done（保持对外行为不变，仅移除防御性样板与 `getattr` 噪音）。

