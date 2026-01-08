# API 响应封套（JSON Envelope）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：所有返回 JSON 的接口（`app/routes/**`）与任务对外返回载荷

## 目的

- 统一 API 成功/失败的顶层结构，避免页面与脚本各自拼装响应导致口径漂移。
- 让前端可以用稳定方式读取 `response.success/response.message/response.data`，并把错误信息结构化沉淀到日志中心。

## 适用范围

- 路由层返回 JSON 的接口（含列表/详情/批量操作）。
- 任务或脚本需要返回“可被 UI/调用方直接消费”的 JSON 载荷时。

## 规则（MUST/SHOULD/MAY）

### 1) 统一封套（强约束）

- MUST：成功响应使用 `app/utils/response_utils.py` 的 `jsonify_unified_success(...)`（或底层 `unified_success_response(...)`）。
- MUST：错误响应由全局错误处理器统一生成（`unified_error_response(...)`），业务代码禁止手写错误 JSON。
- MUST NOT：在业务逻辑内随意拼 `{success: true/false, ...}` 或改写错误字段结构。

### 2) 成功响应字段（固定口径）

成功响应的顶层字段约定如下：

- MUST：`success: true`
- MUST：`error: false`
- MUST：`message: string`（可展示的成功摘要）
- MUST：`timestamp: string`（ISO8601）
- MAY：`data: object | list | string | number | boolean | null`
- MAY：`meta: object`

### 3) 失败响应字段（固定口径）

失败响应的顶层字段约定如下（由 `enhanced_error_handler` 输出）：

- MUST：`success: false`
- MUST：`error: true`
- MUST：`error_id: string`
- MUST：`category: string`
- MUST：`severity: string`
- MUST：`message_code: string`
- MUST：`message: string`（可展示的失败摘要）
- MUST：`timestamp: string`（ISO8601）
- MUST：`recoverable: boolean`
- MUST：`suggestions: list`
- MUST：`context: object`
- MAY：`extra: object`（仅允许放非敏感的诊断字段）

### 4) `data` 的结构约束（面向列表页）

- MUST：列表接口把 `items/total` 放在 `data` 内（推荐：`data.items` 为数组，`data.total` 为整数）。
- MAY：列表接口可在 `data` 内追加 `stats/filters/page/limit` 等字段，但不得污染顶层封套字段。

### 5) 错误消息与兼容约束

- MUST：错误消息口径遵循 [错误消息字段统一](./error-message-schema-unification.md)，禁止在任何层新增 `error/message` 互兜底链。
- SHOULD：当返回结构发生演进时，优先通过新增字段向前兼容，避免重命名/挪字段导致调用方写兼容分支。

## 正反例

### 成功响应示例

```json
{
  "success": true,
  "error": false,
  "message": "任务列表获取成功",
  "timestamp": "2025-12-25T09:00:00+08:00",
  "data": {
    "items": [],
    "total": 0
  }
}
```

### 失败响应示例

```json
{
  "success": false,
  "error": true,
  "error_id": "a1b2c3d4",
  "category": "system",
  "severity": "medium",
  "message_code": "INVALID_REQUEST",
  "message": "请求参数无效",
  "timestamp": "2025-12-25T09:00:00+08:00",
  "recoverable": true,
  "suggestions": ["请检查输入参数", "必要时联系管理员"],
  "context": {}
}
```

### 反例：手写错误封套

```python
return jsonify({"success": False, "msg": "failed"}), 400
```

## 门禁/检查方式

- 评审检查：
  - 路由 JSON 成功响应是否统一使用 `jsonify_unified_success`？
  - 是否出现手写错误 JSON、或把错误细节塞进 `message`？
- 结构漂移门禁（按需）：`./scripts/ci/error-message-drift-guard.sh`

## 变更历史

- 2025-12-25：新增标准文档，固化 JSON 封套字段与列表接口 `data.items/data.total` 约束。
