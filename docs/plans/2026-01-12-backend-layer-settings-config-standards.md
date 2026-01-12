# Backend Standards: Settings/Config Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 按现有配置标准优先对齐 `app/settings.py` 的职责边界与兜底策略, 并补齐 Settings/Config 层编写规范文档（可新增 `settings-layer-standards.md`）。

**Architecture:** 保持 `docs/Obsidian/standards/backend/configuration-and-secrets.md` 作为“配置与密钥”总入口, 新增 `docs/Obsidian/standards/backend/layer/settings-layer-standards.md` 描述 Settings/Config 层的边界、依赖、兼容/回退策略与自查口径；必要时在总入口文档中补齐与 `app/settings.py` 一致的规则与示例。

**Tech Stack:** Flask + python-dotenv + dataclasses + structlog.

---

## Task 1: 新增 Settings/Config 层编写规范

**Files:**

- Create: `docs/Obsidian/standards/backend/layer/settings-layer-standards.md`

**Steps:**

1) 按 layer 标准模板补齐 frontmatter/章节，scope 覆盖 `app/settings.py`
2) 明确职责边界（解析 env、默认值、校验、导出到 `app.config`），禁止业务逻辑/DB/网络
3) 明确兼容/回退策略（env var alias、`or` 兜底约束、dev fallback）
4) 给出自查命令（env 读取散落扫描、敏感信息日志检查）

---

## Task 2: 对齐现有配置标准（优先）

**Files:**

- Modify: `docs/Obsidian/standards/backend/configuration-and-secrets.md`

**Steps:**

1) 补充/对齐：Settings 单一真源、生产必需项、`app.py/wsgi.py` 的入口允许默认值、敏感信息日志约束
2) 增加到 `related`：`settings-layer-standards`
3) 更新 frontmatter 的 `updated` 日期

