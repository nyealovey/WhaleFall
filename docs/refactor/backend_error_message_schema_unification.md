# 后端 `error/message` 字段统一重构方案（基于 2025-12-18）

## 1. 背景与问题定义

当前后端多处存在任务/服务/路由返回结构的字段漂移：同一语义的“失败原因/提示信息”在不同链路中以 `error` 或 `message` 输出，导致调用方不得不写出如下兜底链：

- `result.get("error") or result.get("message")`
- `result.get("message") or result.get("error")`

这类漂移带来的问题：

- **调用方复杂度上升**：每个消费点都要写兼容分支，且方向不一致（有的优先 `error`，有的优先 `message`）。
- **难以清理**：一旦传播到多层（任务 → 服务 → 路由 → 前端），删除任一处兜底都可能引发线上回归。
- **语义混乱**：`message` 可能是“人类可读提示”，也可能被当成“错误详情”；`error` 同理。
- **监控不可用**：聚合错误提示字段不稳定，难以做结构化检索与指标统计。

本文给出统一规范与迁移步骤，并建立“基准/门禁”，确保后续不再引入新的漂移代码。

## 2. 统一目标（What good looks like）

### 2.1 统一原则：写端负责（Producer-owned contract）

**谁产生结果，谁保证结果结构稳定**。具体要求：

- 产生方必须写入 `message`（人类可读、可展示、可用于 API 响应的摘要）。
- 产生方可选写入 `error`（失败详情，通常是异常信息/诊断信息）。
- 产生方可选写入 `errors`（多个错误字符串的列表，适用于批量/多阶段场景）。
- 消费方禁止在业务逻辑中写 `error/message` 互相兜底链；只读取 canonical 字段（见 2.2）。

### 2.2 Canonical 结果封套（Result Envelope）

建议在“任务返回值/服务返回值/路由返回值”三类结构中，统一遵循以下最小封套：

#### 成功（completed）
```json
{
  "status": "completed",
  "message": "执行成功",
  "metrics": {},
  "details": {}
}
```

#### 跳过（skipped）
```json
{
  "status": "skipped",
  "message": "无可处理数据，已跳过",
  "metrics": {},
  "details": {}
}
```

#### 失败（failed）
```json
{
  "status": "failed",
  "message": "执行失败（面向用户/运维的摘要）",
  "error": "失败详情（异常/诊断信息，可选）",
  "errors": ["批量错误1", "批量错误2"]
}
```

约束说明：

- `message` 必填，且必须可展示（不要直接塞入巨型 SQL/堆栈）。
- `error` 可选，建议仅在 `status == "failed"` 时出现。
- `errors` 可选，建议仅在批量/多阶段时使用。
- 如存在错误码需求，优先新增 `error_code`（受控枚举），避免用 `message` 承载“机器可读”的语义。

## 3. 迁移策略（如何从“漂移”到“统一”）

### 3.1 一次性规则：只在“边界层”做 canonicalization

允许存在一个“边界层规范化”步骤，用于把历史返回结构收敛到 canonical：

- **任务入口/路由入口**：接收第三方/历史任务结果时，先 canonicalize，然后下游只读 canonical 字段。
- **服务层内部**：禁止再做 `error/message` 互兜底；如遇到缺 `message` 的上游结果，应回到上游修复，而不是在中间层兜底。

这一步的目标是把“漂移兼容”集中到一个位置，便于后续一次删除。

### 3.2 分阶段落地建议

1. **Phase 0（基准）**：锁定现状漂移命中清单，禁止新增（见第 4 节门禁）。
2. **Phase 1（统一规范）**：在代码库新增一个 result helper（建议放在 `app/utils/`），提供：
   - `canonicalize_result_message(...)`：确保 `message` 存在（必要时从 `error` 映射过来，或回退到默认文案）。
   - `extract_result_message(...)`：只读 `message`，不再 `or` 兜底。
3. **Phase 2（修写端）**：逐个修复产生方，保证每个失败分支都写入 `message`，并在需要时补充 `error/errors`。
4. **Phase 3（删读端兜底）**：移除所有 `error/message` 互兜底链，调用方只读 `message`（或只读 `error_code`）。
5. **Phase 4（收敛基准）**：更新 baseline，使“漂移命中”为 0。

## 4. 基准与门禁（防止回归）

### 4.1 基准文件（Baseline）

仓库提供基于 ripgrep 的基准检查，用于锁定当前 `error/message` 漂移命中，并禁止新增命中。

- 脚本：`scripts/code_review/error_message_drift_guard.sh`
- Baseline：`scripts/code_review/baselines/error_message_drift.txt`

检查逻辑：

- 允许在后续重构中**减少**命中（即删除漂移代码）。
- 禁止引入新的命中（即新增漂移代码）。

### 4.2 使用方法

- 日常检查（默认模式，禁止新增）：
```bash
./scripts/code_review/error_message_drift_guard.sh
```

- 更新 baseline（仅在“清理完成后”或“确有新增但已评审同意”时执行）：
```bash
./scripts/code_review/error_message_drift_guard.sh --update-baseline
```

### 4.3 开发规范（写代码时的约束）

- 禁止新增 `result.get("error") or result.get("message")` / `...message... or ...error...` 互兜底链。
- 新增/修改任何返回结果结构时，必须保证 `message` 存在；失败时可补充 `error/errors`。
- 对外 API（路由）优先返回 `message`；内部诊断信息写入结构化日志字段（而不是拼接进 `message`）。

## 5. 与现有“兼容削减清单”的关系

`docs/refactor/backend_compatibility_and_rollback_code_reduction.md` 的 3.1 剩余条目主要集中在 `error/message` 漂移。后续执行清理时，应以本文作为统一规范，做到：

- 上游写端统一 → 下游读端只读 `message` → 删除所有兜底链。

