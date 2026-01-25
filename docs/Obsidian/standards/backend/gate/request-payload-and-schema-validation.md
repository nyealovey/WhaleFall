---
title: 请求 payload 解析与 schema 校验标准
aliases:
  - request-payload-and-schema-validation
tags:
  - standards
  - standards/backend
status: active
enforcement: gate
created: 2026-01-04
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/utils/request_payload.py`, `app/schemas/**`, `app/services/**`, `app/api/v1/**`, `app/forms/handlers/**`"
related:
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/layer/schemas-layer-standards]]"
  - "[[standards/backend/compatibility-and-deprecation]]"
---

# 请求 payload 解析与 schema 校验标准

## 1. 目的

- 统一写路径的取参逻辑, 避免 form/json/query 的解析与清洗散落在 routes/services/forms 中.
- 统一写路径的取参逻辑, 避免 form/json(body) 的解析与清洗散落在 routes/services/forms 中.
- 统一字段校验与类型转换, 让 service 层只消费"已解析, 已规范化, 已校验"的 typed payload.
- 收敛 `or`/truthy 兜底, 把默认值与兼容策略显式化并可审计.

## 2. 适用范围

- 所有写操作(创建/更新/批量写入/修改密码)的入口与服务层.
- 任何从 JSON mapping(`request.get_json()`) 或 `MultiDict`(`request.form` 等) 进入系统的**写路径 body payload**.
- 不包含 query 参数(`request.args`): API 使用 `reqparse`/`@ns.expect(parser)`；Routes 参考 [[standards/backend/layer/routes-layer-standards]] 的建议做显式 `strip/cast`。

## 3. 规则

### 3.1 请求 payload 解析

- MUST: 对写路径 body payload（JSON dict / `request.form` MultiDict / task payload）在进入业务编排前必须使用 `app/utils/request_payload.py::parse_payload` 做基础解析与规范化；且在一次请求链路中 MUST 只执行一次（API/Routes/Service 入口三选一，优先选择可复用入口：Service）。
- MUST: 对 "必须为 list" 的字段使用 `list_fields`, 并保证输出形状稳定(单值也输出 list).
- MUST: 对敏感字段(如 password)显式声明 `preserve_raw_fields`, 禁止依赖字段名包含判断.
- SHOULD: 对 checkbox 类布尔字段使用 `boolean_fields_default_false`, 只对 MultiDict 缺失字段补 False.
- MUST NOT: 在业务代码中重复做 strip/NUL 清理与 list 折叠, 以免出现语义漂移.

#### 3.1.1 职责边界：parse_payload vs schema（避免双重规范化导致漂移）

| 层 | 负责 | 不负责 |
|---|---|---|
| `parse_payload` | shape-level 适配（JSON mapping / MultiDict → 稳定 dict）、NUL 清理、list 形状稳定、MultiDict 缺失布尔字段补 False（受控） | 字段语义级默认值、字段 alias/迁移、业务规则、对外错误码口径 |
| schema（`app/schemas/**`） | semantic-level 规范化与校验（类型转换、默认值、`"" -> None`、alias/形状迁移），并产出 typed payload | 在 service 内直接读 `request.*`、在多层重复做 parse/strip/兜底链 |

### 3.2 Schema 校验与错误映射

- MUST: 写路径 schema 统一放在 `app/schemas/**`, 并继承 `app/schemas/base.py::PayloadSchema`.
- MUST: service 层使用 `app/schemas/validation.py::validate_or_raise` 执行校验并抛出项目 `ValidationError`.
- MUST: schema validator 内可用 `ValueError("...")` 表达字段校验失败（会被 pydantic 收集为校验错误）；`validate_or_raise(...)` 必须将其转换为项目 `ValidationError`，禁止让 `ValueError` 穿透到 routes/api。
- MUST: 需要透传 `message_key` 时, schema 侧抛出 `SchemaMessageKeyError(message, message_key="...")`.
- SHOULD: 可选字符串字段统一 canonicalize, 常见规则为 `"" -> None`, 避免 "空串 vs 未提供" 语义漂移.

最小链路示例（ValueError → ValidationError）：

```python
from pydantic import field_validator

from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError


class ExamplePayload(PayloadSchema):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("名称不能为空")
        if value == "forbidden":
            raise SchemaMessageKeyError("不允许的名称", message_key="INVALID_NAME")
        return value
```

> 说明：service 调用 `validate_or_raise(ExamplePayload, sanitized)` 时会捕获 pydantic 校验错误并抛出项目 `ValidationError`（HTTP 边界再映射为统一错误封套）。

### 3.3 Service 层消费规范

- MUST: service 层消费 schema 对象, 禁止直接访问 raw dict 并做 `data.get("x") or default` 兜底.
- MUST: 对 update 场景, 以 `model_fields_set` 判断字段是否传入, 禁止用 truthy 分支判断是否更新.
- SHOULD: 需要兼容旧字段/旧形状时, 优先在 schema 侧用 alias/validator 兼容并加单测; 迁移完成后删除兼容入口.

### 3.4 防御/兼容/回退/适配约束

- MUST: 任何新增的兼容/回退逻辑必须在 schema/adapter 侧显式化, 并写入变更文档的 "发现清单" 与单测.
- MUST: 迁移完成后关闭临时兼容逻辑, 避免长期保留 silent fallback.

## 4. 正反例

### 4.1 正例

```python
from app.schemas.instances import InstanceCreatePayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload

sanitized = parse_payload(
    request.form,
    list_fields=["tag_names"],
    boolean_fields_default_false=["is_active"],
)
params = validate_or_raise(InstanceCreatePayload, sanitized)
```

### 4.2 反例

```python
data = request.form
name = (data.get("name") or "").strip()
tag_names = data.getlist("tag_names") or []
is_active = bool(data.get("is_active"))  # checkbox 缺失语义不明确
```

## 5. 门禁/检查方式

- 单元测试: `uv run pytest -m unit`
- 类型检查: `make typecheck`
- Ruff(style 报告): `./scripts/ci/ruff-report.sh style`

## 6. 变更历史

- 2026-01-04: 引入 `pydantic` 写路径 schema + `parse_payload`, 并删除旧 `DataValidator`.
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
