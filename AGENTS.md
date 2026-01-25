# 仓库使用规范（协作入口 + 必要硬约束）

> 详细规范以 `docs/Obsidian/standards/` 为单一真源。本文件只保留“入口 + 硬约束 + 常用命令”。

## Quick Reference

- **目录**：`app/`（Flask） · `migrations/` · `sql/` · `docs/` · `scripts/` · `tests/unit/`
- **依赖/启动**：`make install` · `make dev-start` · `make init-db` · `python app.py`（默认 `http://127.0.0.1:5001`）
- **质量/测试**：`make format` · `make typecheck` · `uv run pytest -m unit`
- **报告类检查**：`./scripts/ci/ruff-report.sh style` · `./scripts/ci/pyright-report.sh` · `./scripts/ci/eslint-report.sh quick`（改动 JS） · `./scripts/ci/refactor-naming.sh --dry-run`
- **更多速查（非 SSOT）**：`docs/agent/README.md`

## 必须遵循（SSOT）

- 文档/编码/命名：`docs/Obsidian/standards/doc/guide/documentation.md` · `docs/Obsidian/standards/core/guide/coding.md` · `docs/Obsidian/standards/core/gate/naming.md`
- 后端/UI 索引：`docs/Obsidian/standards/backend/README.md` · `docs/Obsidian/standards/ui/README.md`

## 硬约束

- `.env` 禁止提交；`env.example` 禁止写入真实密钥/口令（门禁：`./scripts/ci/secrets-guard.sh`）
- 新增/调整配置项必须走 `app/settings.py`（解析 + 默认值 + 校验）
- 迁移脚本禁止修改历史版本（规则：`docs/Obsidian/standards/backend/hard/database-migrations.md`）
- 后台任务必须运行在 Flask `app.app_context()` 内（规则：`docs/Obsidian/standards/backend/hard/task-and-scheduler.md`）
- API 响应封套/错误口径遵循：`docs/Obsidian/standards/backend/gate/layer/api-layer.md`、`docs/Obsidian/standards/backend/hard/error-message-schema-unification.md`
- 分支/提交：日常 PR → `dev`；发布/线上修复 → `main`（详见 `docs/Obsidian/standards/core/guide/git-workflow.md`）；提交前缀建议 `fix:`/`feat:`/`refactor:`/`docs:`/`chore:`（≤72 字）
- 除代码相关文本（文件路径/命令/字段/函数/路由/关键字等）外，说明尽量使用中文
- 不要无依据添加 defensive fallback（吞异常、silent fallback 等）；如必须引入需写清运行时场景/复现用例/测试需求与验证方式
