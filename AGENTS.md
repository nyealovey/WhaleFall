# 仓库使用规范

> 说明：本文件只保留“仓库协作入口 + 必要硬约束”。详细规范以 `docs/Obsidian/standards/` 为单一真源。

## 1. 目录结构（现状）

- Flask 应用代码：`app/`（`routes/`、`models/`、`services/`、`tasks/`、`utils/`、`templates/`、`static/`）
- 数据库迁移：`migrations/`
- 初始化 SQL 与运维 SQL：`sql/`
- 项目文档：`docs/`
- 工具脚本：`scripts/`
- 测试：`tests/unit/`

## 2. 常用命令（本仓库可用）

- 安装依赖：`make install`
- 代码格式化：`make format`
- 类型检查：`make typecheck`
- Ruff（报告）：`./scripts/ci/ruff-report.sh style`（或 `ruff check <paths>`）
- Pyright（报告）：`./scripts/ci/pyright-report.sh`（或 `make typecheck`）
- ESLint（报告，改动 JS 时）：`./scripts/ci/eslint-report.sh quick`
- 命名巡检：`./scripts/ci/refactor-naming.sh --dry-run`
- 单元测试：`uv run pytest -m unit`（或 `./.venv/bin/pytest -m unit`）

## 3. 必须遵循的标准（单一真源）

- 文档结构与编写：`docs/Obsidian/standards/doc/documentation-standards.md`
- 编码规范：`docs/Obsidian/standards/coding-standards.md`
- 命名规范：`docs/Obsidian/standards/naming-standards.md`
- 后端标准索引：`docs/Obsidian/standards/backend/README.md`
- UI 标准索引：`docs/Obsidian/standards/ui/README.md`

## 4. 安全与配置（要点）

- `.env` 禁止提交；`env.example` 禁止写入真实密钥/口令。
- `env.example` 密钥门禁：`./scripts/ci/secrets-guard.sh`
- 新增/调整配置项必须走 `app/settings.py`（解析 + 默认值 + 校验）；详见 `docs/Obsidian/standards/backend/configuration-and-secrets.md`。

## 5. 数据库与任务（要点）

- 迁移脚本不可修改历史版本；初始化路径与基线约束详见 `docs/Obsidian/standards/backend/database-migrations.md`。
- 后台任务必须运行在 Flask `app.app_context()` 内；详见 `docs/Obsidian/standards/backend/task-and-scheduler.md`。
- API 响应封套与错误口径详见：
  - `docs/Obsidian/standards/backend/api-response-envelope.md`
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md`

## 6. PR 与提交（精简约定）

- 分支约定：日常开发 PR 目标为 `dev`；仅发布/线上修复合入 `main`。详见 `docs/Obsidian/standards/git-workflow-standards.md`。
- 提交信息建议使用：`fix:` / `feat:` / `refactor:` / `docs:` / `chore:`，主题长度 ≤72 字。
- PR 描述必须写清：变更范围、验证命令、是否影响配置/迁移/对外接口、是否需要回滚说明。

## 7. 文档与说明语言

- 除代码相关内容（如文件路径、命令、字段名、函数名、路由、关键字等）外，其他文字说明尽量使用中文。

## 8. 防御性分支约束

- 不要“顺手”添加无明确依据的防御性分支/兜底逻辑（例如检查全局变量是否存在、silent fallback、吞异常后继续执行等）。
- 仅当有明确的运行时场景/复现用例/测试需求，或由安全/兼容性要求驱动时才引入，并在变更说明中写清理由与验证方式。
