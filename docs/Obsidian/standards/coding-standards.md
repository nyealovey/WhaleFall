---
title: 编码规范
aliases:
  - coding-standards
tags:
  - standards
  - standards/general
status: active
enforcement: guide
created: 2025-11-21
updated: 2026-01-25
owner: WhaleFall Team
scope: 仓库内所有 Python/JS/CSS/Jinja2 代码与脚本
related:
  - "[[standards/README]]"
  - "[[standards/halfwidth-character-standards]]"
  - "[[standards/naming-standards]]"
  - "[[standards/backend/layer/routes-layer-standards]]"
  - "[[standards/backend/layer/api-layer-standards]]"
  - "[[standards/backend/layer/types-layer-standards]]"
  - "[[standards/backend/layer/schemas-layer-standards]]"
  - "[[standards/testing-standards]]"
  - "[[standards/ui/README]]"
---

# 编码规范

## 目的

- 统一编码风格与工程约束，减少“代码能跑但不可维护”的长期成本。
- 通过固定的门禁与检查方式，把问题拦在合并前（而不是线上）。

## 适用范围

- Python：`app/`、`scripts/`、`tests/`
- 前端与模板：`app/static/`、`app/templates/`

## 规则（MUST/SHOULD/MAY）

### 1) 格式与风格

- MUST：提交前运行 `make format`（black + isort），避免在评审中讨论格式。
- SHOULD：Python 使用四空格缩进，单行长度建议 ≤120.
- SHOULD: 避免不可见空白字符与代码相关文本的全角 ASCII 变体, 详见 [[standards/halfwidth-character-standards]].
- SHOULD：导入顺序遵循“标准库 → 第三方 → 本地模块”，并把 `app` 视为一方导入根。

### 2) 日志与可观测性

- MUST：新代码禁止使用 `print`；统一使用结构化日志（structlog）。
- MUST：日志字段使用结构化参数（`logger.info(..., key=value)`），禁止用 f-string 拼接日志内容。
- SHOULD：在路由/任务/服务边界写入 `module/action/context` 等维度字段，保证可追踪。

### 3) 边界层异常与封套（以分层标准为准）

- SHOULD: Routes/API 的异常处理、事务语义与封套口径, 以分层标准为单一真源:
  - [[standards/backend/layer/routes-layer-standards|Routes 层编写规范]]
  - [[standards/backend/layer/api-layer-standards|API 层编写规范]]
- SHOULD: 避免在边界层手写 `try/except Exception` + 记录日志 + 返回错误响应的模板(容易造成口径漂移与重复日志)。

### 4) 类型与 schema（以 types/schemas 标准为准）

- SHOULD：共享的 `TypedDict/TypeAlias/Protocol` 优先集中在 `app/core/types/`，避免在业务模块临时声明大量 `dict[str, Any]` 结构。
- SHOULD: 字段级校验/类型转换/默认值/兼容策略优先收敛到 schema, 避免散落在 Routes/API/Service.
- SHOULD：新增/调整共享类型后，对相关代码运行 `ruff check <files> --select ANN,ARG,RUF012` 与 `make typecheck`，避免 `Any` 回退。

### 5) 前端与样式（以 UI 标准为准）

- SHOULD：UI 相关细则以 [[standards/ui/README|UI 标准索引]] 为准(本文件不重复维护 UI 细粒度约束)。
- SHOULD: 色彩优先使用 design token/CSS variables, 参考 [[standards/ui/design-token-governance-guidelines|设计 Token 治理]].

### 6) 测试（当前仓库基线）

- SHOULD：测试组织、marker 与目录约定以 [[standards/testing-standards|测试规范]] 为准。
- SHOULD：新增测试优先覆盖“服务层/工具函数/规则引擎”等可复用逻辑，而不是在视图层堆集成用例。

## 正反例

### Docstring（中文 + Google 风格）

```python
def resolve_page_size() -> int:
    """解析分页每页数量.

    兼容历史字段并做范围裁剪.

    Returns:
        解析后的每页数量.

    """
    return 20
```

## 门禁/检查方式

- Python 格式化：`make format`
- Python Lint：`ruff check .`（或按改动范围执行 `ruff check <paths>`）
- Python 类型检查：`make typecheck`（等价于运行 pyright）
- 命名巡检：`./scripts/ci/refactor-naming.sh --dry-run`
- JS 静态检查（如改动 `app/static/js`）：`./scripts/ci/eslint-report.sh quick`
- 结果结构漂移门禁（如涉及结果封套/错误字段）：`./scripts/ci/error-message-drift-guard.sh`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写并收敛为“可执行的规则 + 门禁”，移除与现状不一致的 Make/目录说明。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
