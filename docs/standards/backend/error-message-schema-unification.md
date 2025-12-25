# 错误消息字段统一（`error/message`）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-18  
> 更新：2025-12-25  
> 范围：任务/服务/路由返回结构与 API 响应封套

## 目的

- 消除 `error/message` 字段漂移，避免调用方写 `result.get("error") or result.get("message")` 互兜底链。
- 固化“产生方负责结构稳定”的契约，让错误可被结构化检索、统计与治理。

## 适用范围

- 内部结果对象：任务返回值、服务返回值（包含批量/多阶段流程）。
- 对外 API：JSON 响应封套中的错误提示字段。

## 规则（MUST/SHOULD/MAY）

### 1) 产生方契约（Producer-owned contract）

- MUST：产生方必须写入 `message`（人类可读、可展示的摘要文案）。
- SHOULD：失败时可写入 `error`（诊断信息/异常信息摘要），避免把堆栈/巨型 SQL 直接塞进 `message`。
- MAY：批量/多阶段场景可写入 `errors`（错误字符串列表）。
- SHOULD：如有机器可读需求，新增 `error_code`（受控枚举），禁止用 `message` 承载机器语义。

### 2) 消费方约束（禁止互兜底）

- MUST NOT：在业务逻辑中新增以下互兜底链：
  - `result.get("error") or result.get("message")`
  - `result.get("message") or result.get("error")`
- MUST：消费方只读取 canonical 字段（默认 `message`，必要时读取 `error_code`）。

### 3) 兼容与迁移边界

- SHOULD：如必须兼容历史结构，只允许在“边界层”做一次规范化（canonicalization），随后下游只读 canonical 字段。
- MUST：不得把兼容逻辑扩散到多层（任务 → 服务 → 路由 → 前端），否则后续无法一次性删除。

## 正反例

### Canonical 结果封套（推荐最小结构）

成功：

```json
{
  "status": "completed",
  "message": "执行成功",
  "details": {}
}
```

失败：

```json
{
  "status": "failed",
  "message": "执行失败",
  "error": "诊断信息（可选）",
  "errors": ["子任务失败1", "子任务失败2"]
}
```

### 禁止的互兜底链

```python
msg = result.get("error") or result.get("message")
```

## 门禁/检查方式

- 门禁脚本：`./scripts/code_review/error_message_drift_guard.sh`
- Baseline：`scripts/code_review/baselines/error_message_drift.txt`
- 规则：
  - 允许减少命中（删除漂移代码）
  - 禁止新增命中（新增漂移代码会阻断）

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为“标准契约文档”，剥离阶段性方案叙述，补齐 MUST/SHOULD/MAY 与门禁说明。
