# Backend Standards: Infra/Schemas/Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 补齐并对齐后端标准文档: 新增 Infra 层与 Schemas 层编写规范; 新增 Bootstrap/Entrypoint 规范; 扩展现有 API 标准 scope 从 `app/api/v1/**` 到 `app/api/**` 并把 `app/api/__init__.py` 作为 API 层注册入口纳入标准。

**Architecture:** 以 `docs/Obsidian/standards/backend/layer/*.md` 为分层标准单一真源: Infra/Schemas 补齐为同一目录下的新 layer 标准; Bootstrap/Entrypoint 属于启动与组装, 作为后端通用标准放在 `docs/Obsidian/standards/backend/`; API 标准 scope 扩展后仍强调 “端点薄、逻辑下沉、事务边界统一” 的原则, 避免为 API 注册入口单开新层导致口径漂移。

**Tech Stack:** Flask + SQLAlchemy + APScheduler + pydantic + structlog.

---

## Task 1: 新增 `Infra 层编写规范`

**Files:**

- Create: `docs/Obsidian/standards/backend/layer/infra-layer-standards.md`

**Steps:**

1) 按现有 layer 标准模板补齐 frontmatter/章节:
   - scope: `app/infra/**` + `app/scheduler.py`
   - related: `write-operation-boundary`, `task-and-scheduler`, `sensitive-data-handling`, `error-message-schema-unification`
2) 明确 Infra 的职责边界(适配/封装/失败隔离/可观测性)与允许/禁止依赖
3) 明确事务边界允许点(例如 `safe_route_call`, worker), 与 [[standards/backend/write-operation-boundary]] 对齐
4) 给出自查命令(示例):

```bash
rg -n "from app\\.(services|repositories|routes|api)\\.|db\\.session\\.query\\b" app/infra app/scheduler.py
```

---

## Task 2: 新增 `Schemas 层编写规范`

**Files:**

- Create: `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md`

**Steps:**

1) 按现有 layer 标准模板补齐 frontmatter/章节:
   - scope: `app/schemas/**`
   - related: `request-payload-and-schema-validation`, `error-message-schema-unification`, `sensitive-data-handling`, `types-layer-standards`
2) 明确 Schemas 的职责边界(校验/规范化/兼容 alias/错误映射)与允许/禁止依赖
3) 明确 “兼容/回退/兜底” 应该放在 schema 层, 并要求补单测与迁移后删除
4) 给出自查命令(示例):

```bash
rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session\\b" app/schemas
```

---

## Task 3: 新增 `Bootstrap/Entrypoint 规范`

**Files:**

- Create: `docs/Obsidian/standards/backend/bootstrap-and-entrypoint.md`

**Steps:**

1) 定义启动/组装的单一入口: `app/__init__.py::create_app`
2) 明确 entrypoints 的范围与约束:
   - `app.py`(本地开发入口)
   - `wsgi.py`(生产/WSGI 入口)
   - 约束 “只负责组装与启动, 不引入业务逻辑”
3) 明确 `app/api/__init__.py` 是 API 层注册入口(不单开新层), 并指向 API 层标准

---

## Task 4: 扩展 API 标准 scope 到 `app/api/**`

**Files:**

- Modify: `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
- (可选) Modify: `docs/Obsidian/standards/backend/layer/README.md`(API 节点标注路径从 `app/api/v1` 扩到 `app/api`)

**Steps:**

1) 更新 frontmatter:
   - `scope` 从 `app/api/v1/**` 改为 `app/api/**`
   - 更新 `updated` 日期
2) 更新 “适用范围/目录结构” 章节, 显式包含:
   - `app/api/__init__.py`(blueprint 注册入口)
   - `app/api/v1/**`(当前版本化实现)
3) 全文检索确认没有遗留的 scope 描述冲突:

```bash
rg -n \"scope: `app/api/v1/\\*\\*`\" docs/Obsidian/standards/backend/layer/api-layer-standards.md
```

