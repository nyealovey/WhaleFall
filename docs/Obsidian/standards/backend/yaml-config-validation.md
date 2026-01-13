---
title: YAML 配置读取与校验标准
aliases:
  - yaml-config-validation
tags:
  - standards
  - standards/backend
status: active
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/config/*.yaml`, `app/schemas/yaml_configs.py`, 相关读取入口"
related:
  - "[[standards/backend/configuration-and-secrets]]"
  - "[[standards/backend/request-payload-and-schema-validation]]"
  - "[[standards/backend/compatibility-and-deprecation]]"
---

# YAML 配置读取与校验标准

## 1. 目的

- 将 YAML 配置文件的“形状适配 + 类型校验 + 默认值策略”收敛到读取入口，避免运行期散落 `or` 兜底链修补配置形状。
- 明确一次性 canonicalization 的位置，使下游逻辑只消费稳定结构（减少语义漂移与隐式优先级）。

## 2. 适用范围

- `app/config/*.yaml`（例如 filters、scheduler tasks 等）的读取入口。
- 任何将 YAML mapping 解析为业务规则/过滤规则/调度配置的路径。

## 3. 规则（MUST/SHOULD）

### 3.1 读取入口一次性校验（强约束）

- MUST: YAML 读取入口必须在加载后立即做 schema 校验与 canonicalization（只执行一次），产出 typed config 后再进入业务逻辑。
- MUST NOT: 在运行期用 `raw.get("x") or default` / `raw.get("new") or raw.get("old")` 等兜底链“修补”配置形状（这会隐藏配置错误并引入隐式优先级）。
- MUST: schema 校验失败必须抛出异常（例如 `ValueError`）并携带可定位信息（至少包含配置路径与错误摘要），禁止 silent fallback 为 `{}`/`[]`。

### 3.2 schema 的落点与组织

- MUST: YAML 配置 schema 统一放在 `app/schemas/yaml_configs.py`（或按域拆分到 `app/schemas/**`），并使用 pydantic 做运行期校验。
- SHOULD: 在 schema 内完成“低风险规范化”：
  - 规则 key（如 `db_type`）统一小写
  - 列表项 `strip()`、过滤空白项
  - 明确缺省值（`default_factory=list/dict`）而不是在业务侧 `or []/{}` 兜底

### 3.3 测试要求（门禁）

- MUST: 每个 YAML 配置读取入口至少覆盖 2 类单测：
  - 正例：合法配置 -> 输出结构稳定（含 canonicalization 结果）
  - 反例：缺失必填 key / 类型错误 -> 抛出异常（不允许 silent fallback）

## 4. 门禁/检查方式

- 单元测试：`uv run pytest -m unit`
  - scheduler tasks：`tests/unit/services/test_yaml_config_validation_scheduler_tasks.py`
  - filters：`tests/unit/services/test_yaml_config_validation_filters.py`
