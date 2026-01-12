# Backend Layer Standards Alignment (1.1-1.3) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 依据 `docs/reports/2026-01-11-backend-layer-layer10-focus-issue-report.md` 的决定, 修复 1.1/1.2/1.3 的标准与实现漂移: 修正文档依赖图方向、收窄 constants 依赖规则、将 payload 解析/转换从 `app/core/types/**` 迁移到 `app/utils/**`.

**Architecture:** 保持“箭头语义 = 上层依赖下层”不变, 仅修正 Errors/Constants/Types 的箭头方向; Constants 标准改为禁止业务层/有副作用模块, 但允许 `app.core.constants.*` 同层互相 import; Types 层严格只保留类型定义, 解析/转换函数迁移到 Utils, 并同步更新引用与相关文档.

**Tech Stack:** Flask + SQLAlchemy + pytest + pyright + ruff.

---

## Verification Baseline(完成后必跑)

Run:

```bash
./scripts/ci/pyright-guard.sh
uv run pytest -m unit
```

Expected:

- `pyright` diagnostics: 0(Exit 0)
- `pytest` Exit 0

---

## Task 1: Fix `layer/README.md` 依赖图方向(1.1, 方案 A)

**Files:**

- Modify: `docs/Obsidian/standards/backend/layer/README.md`

**Steps:**

1) 将 Errors/Constants/Types 的箭头改为 “各层 --> Errors/Constants/Types”
2) 更新 frontmatter 的 `updated` 日期

---

## Task 2: 收窄 `constants-layer-standards.md` 依赖规则(1.2, 采用建议)

**Files:**

- Modify: `docs/Obsidian/standards/backend/layer/constants-layer-standards.md`

**Steps:**

1) 将 “MUST NOT: `app.*`” 改为明确禁止业务层/有副作用模块, 并显式允许 `app.core.constants.*` 同层互相 import
2) 更新 frontmatter 的 `updated` 日期

---

## Task 3: 迁移 `app/core/types/**` 的解析/转换逻辑到 `app/utils/**`(1.3, 方案 A)

**Files:**

- Create: `app/utils/request_payload.py`
- Create: `app/utils/payload_converters.py`
- Delete: `app/core/types/request_payload.py`
- Delete: `app/core/types/converters.py`
- Modify: `app/services/**`(更新 import)
- Modify: `app/views/form_handlers/**`(更新 import)
- Modify: `app/schemas/**`(更新 import)
- Modify: `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`(更新路径与示例)

**Steps:**

1) 复制 `app/core/types/request_payload.py` 到 `app/utils/request_payload.py`(保持 `parse_payload(...)` API 不变)
2) 复制 `app/core/types/converters.py` 到 `app/utils/payload_converters.py`(保持 `as_bool/as_int/...` API 不变)
3) 批量更新 import:
   - `app.core.types.request_payload` → `app.utils.request_payload`
   - `app.core.types.converters` → `app.utils.payload_converters`
4) 删除旧的 `app/core/types/request_payload.py` 与 `app/core/types/converters.py`, 避免 Types 层继续承载逻辑
5) 更新标准文档中的路径与示例 import
6) 运行 Verification Baseline, 修复任何失败后再结束

