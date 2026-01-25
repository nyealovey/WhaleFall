---
title: Schemas 校验层编写规范
aliases:
  - schemas-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: gate
created: 2026-01-12
updated: 2026-01-16
owner: WhaleFall Team
scope: "`app/schemas/**` 下所有 schema 与校验工具"
related:
  - "[[standards/backend/guide/layer/README|后端分层标准]]"
  - "[[standards/backend/gate/request-payload-and-schema-validation]]"
  - "[[standards/backend/gate/or-fallback-decision-table]]"
  - "[[standards/backend/hard/error-message-schema-unification]]"
  - "[[standards/backend/hard/sensitive-data-handling]]"
  - "[[standards/backend/guide/layer/types-layer]]"
  - "[[standards/backend/gate/layer/services-layer]]"
---

# Schemas 校验层编写规范

> [!note] 说明
> Schemas 层用于承载写路径参数的结构约束、字段校验、规范化(canonicalization)与兼容策略（字段 alias/形状迁移）。其目标是让 Service 只消费“已解析、已规范化、已校验”的 typed payload，避免在业务代码里散落 `data.get("x") or default` 的兜底链。

## 目的

- 统一字段校验与错误文案口径，降低 routes/api/services 各自校验导致的漂移。
- 将兼容/迁移逻辑显式化并可审计：旧字段名、旧形状、默认值策略集中在 schema 层处理。
- 提升可测试性：把输入校验从业务编排中剥离，单测覆盖边界与兼容分支。

## 适用范围

- `app/schemas/**` 下所有 schema 定义与校验辅助工具（例如 `validate_or_raise`）。

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: 写路径在进入 Service 的核心业务逻辑前必须经过 schema 校验（推荐在 Service 入口第一步使用 `app/schemas/validation.py::validate_or_raise`）。
- MUST: schema 负责字段级校验与规范化（例如 `"" -> None`、`str.strip()`、布尔/整数转换）。
- MUST NOT: schema 访问数据库或依赖 `db.session`。
- MUST NOT: schema 依赖 `app.models.*`, `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`。
- SHOULD: schema 校验失败时输出中文错误文案，并与 [[standards/backend/hard/error-message-schema-unification|错误消息字段统一]] 保持一致。

### 2) 兼容/迁移(字段 alias 与形状兼容)

- MUST: 旧字段名/旧形状兼容必须在 schema 层显式处理（alias/validator），禁止在 service 写 `data.get("new") or data.get("old")`。
- MUST: 任何兼容分支都要补单测覆盖，并在迁移完成后删除（避免长期保留 silent fallback）。
- SHOULD: 兼容策略优先选择：
  1) pydantic 字段 alias / `validation_alias`
  2) `model_validator(mode="before")` 做输入形状迁移
  3) `field_validator(..., mode="before")` 做单字段迁移/归一化

### 3) 默认值与兜底(`or` 使用约束)

- MUST: schema 中的默认值必须是“语义默认值”，并且可被审计（字段默认/`default_factory`/显式 `None`）。
- MUST: 当合法值可能为 `0/""/[]/{}` 时，禁止用 `or` 兜底（会覆盖合法值）；应改为 `is None` 或显式缺失判定（参见 [[standards/backend/gate/or-fallback-decision-table]]）。
- SHOULD: update/patch 场景必须用 `model_fields_set` 区分“缺失”与“显式提供但为空”（例如 `[]` 表示“清空”）。
- MAY: 对“空白字符串视为缺省”的字段使用 `cleaned or None` 做 canonicalization，但必须在注释/命名中明确语义，并补单测覆盖空白/缺失/合法空串策略（例如 `_parse_optional_string`）。

### 4) 组织方式与命名

- SHOULD: 按资源域拆文件：`instances.py`, `credentials.py`, `users.py` 等。
- SHOULD: schema 命名使用 `{Resource}{Action}Payload`：
  - `InstanceCreatePayload`
  - `CredentialUpdatePayload`
- SHOULD: 复用的校验/解析函数放在同文件的私有 helper（`_validate_*`, `_parse_*`），避免被跨文件随意复用导致口径漂移。

### 5) 基类与未知字段策略

- MUST: 写路径 schema 统一继承 `app/schemas/base.py::PayloadSchema`。
- SHOULD: 默认忽略未知字段（`extra="ignore"`）作为前向兼容策略：允许客户端携带扩展字段而不导致校验失败。
- MUST: 如果某类接口需要“严格拒绝未知字段”，必须在该 schema 内显式配置并在评审说明原因（避免全局口径分裂）。

### 6) 依赖规则

允许依赖:

- MUST: `pydantic`
- MUST: 标准库
- MAY: `app.core.exceptions`（用于抛出/映射项目错误）
- MAY: `app.core.constants.*`, `app.core.types.*`, `app.utils.*`（仅限纯函数/无副作用工具）

禁止依赖:

- MUST NOT: `app.models.*`, `app` 的 `db`
- MUST NOT: `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`

### 7) 测试要求

- SHOULD: 对每个 schema 的“必填校验/边界值/兼容分支/默认值策略”补 `tests/unit/**` 单测。
- SHOULD: 覆盖至少一个“输入为 MultiDict/Mapping 形状差异”场景（与 request payload adapter 配合）。

## 门禁/检查方式

- 评审检查:
  - 是否把兼容/兜底逻辑放在了 service 而不是 schema？
  - 是否出现 `or` 兜底覆盖合法空值的问题？
  - 是否出现对 models/db/services/repositories 的依赖？
- 自查命令(示例):

```bash
rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session\\b" app/schemas
```

## 变更历史

- 2026-01-12: 新增 Schemas 层标准, 覆盖 `app/schemas/**`.
- 2026-01-13: 澄清 schema 校验应由 Service 入口承载, 避免被误读为“必须在 API 层校验后才能进入 Service”.
