# WhaleFall Canvas

本目录存放 WhaleFall 的 `.canvas` 文件, 用于在 Obsidian 里维护可编辑的架构图/流程图.

## 约定(Mermaid <-> Canvas)

- Mermaid: 文档内的渲染版本, 便于在 Markdown 里 review 与 diff.
- Canvas: 可编辑版本, 用于协作讨论与后续迭代(推荐先改 Canvas, 再同步 Mermaid).
- MUST: 每个出现在 `docs/Obsidian/architecture/**` 的 Mermaid 图, 都要有一个对应的 `docs/Obsidian/canvas/**.canvas`.
- MUST: 文档与 Canvas 相互引用.
  - 文档 -> Canvas: 在 Mermaid 图下方增加 `Canvas: [[canvas/...]]`.
  - Canvas -> 文档: Canvas 内增加一个 `file` node 指向对应 `.md`, 并尽量使用 `subpath` 指到图标题.

## 重要边界

- API contract 的 SSOT 是 `docs/Obsidian/API/**-api-contract.md`, Canvas 不能作为 contract SSOT.

## Canvas 索引

### Global

- [[canvas/global-system-architecture.canvas]]
- [[canvas/global-c4-l1-system-context.canvas]]
- [[canvas/global-c4-l2-runtime-topology.canvas]]
- [[canvas/global-c4-l3-component-layering.canvas]]
- [[canvas/global-layer-first-module-dependency-graph.canvas]]
- [[canvas/global-business-capability-map.canvas]]
- [[canvas/cross-cutting-capabilities.canvas]]

### Auth

- [[canvas/auth/web-login-sequence.canvas]]
- [[canvas/auth/api-login-sequence.canvas]]

### Sync sessions

- [[canvas/sync-sessions/sync-session-flow.canvas]]

### Credentials

- [[canvas/credentials/credentials-connection-flow.canvas]]
- [[canvas/credentials/credentials-connection-sequence.canvas]]
- [[canvas/credentials/credentials-connection-state-machine.canvas]]
- [[canvas/credentials/credentials-connection-domain-components.canvas]]
- [[canvas/credentials/credentials-connection-erd.canvas]]

### Instances

- [[canvas/instances/instances-flow.canvas]]
- [[canvas/instances/instances-sequence.canvas]]
- [[canvas/instances/instances-state-machine.canvas]]
- [[canvas/instances/instances-domain-components.canvas]]
- [[canvas/instances/instances-erd.canvas]]

### Accounts

- [[canvas/accounts/accounts-flow.canvas]]
- [[canvas/accounts/accounts-sequence.canvas]]
- [[canvas/accounts/accounts-session-sequence.canvas]]
- [[canvas/accounts/accounts-state-machine.canvas]]
- [[canvas/accounts/accounts-domain-components.canvas]]
- [[canvas/accounts/accounts-erd.canvas]]

### Account classification

- [[canvas/account-classification/account-classification-flow.canvas]]
- [[canvas/account-classification/account-classification-sequence.canvas]]
- [[canvas/account-classification/account-classification-state-machine.canvas]]
- [[canvas/account-classification/account-classification-domain-components.canvas]]
- [[canvas/account-classification/account-classification-erd.canvas]]

### Capacity

- [[canvas/capacity/capacity-flow.canvas]]
- [[canvas/capacity/capacity-sequence.canvas]]
- [[canvas/capacity/aggregation-stats-flow.canvas]]
- [[canvas/capacity/capacity-aggregation-sequence.canvas]]
- [[canvas/capacity/capacity-state-machine.canvas]]
- [[canvas/capacity/capacity-domain-components.canvas]]
- [[canvas/capacity/capacity-erd.canvas]]

### Tags

- [[canvas/tags/tags-bulk-flow.canvas]]

### Databases ledger

- [[canvas/databases-ledger/databases-ledger-domain-components.canvas]]
- [[canvas/databases-ledger/databases-ledger-flow.canvas]]

### Files exports

- [[canvas/files/files-exports-flow.canvas]]

### Dashboard

- [[canvas/dashboard/dashboard-domain-components.canvas]]

### Observability

- [[canvas/observability/unified-logs-flow.canvas]]

### Scheduler

- [[canvas/scheduler/scheduler-flow.canvas]]
- [[canvas/scheduler/scheduler-sequence.canvas]]
- [[canvas/scheduler/scheduler-state-machine.canvas]]
- [[canvas/scheduler/scheduler-domain-components.canvas]]
- [[canvas/scheduler/scheduler-erd.canvas]]
