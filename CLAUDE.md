# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库工作时提供指导。

- 协作硬约束与必读入口：`AGENTS.md`（SSOT：`docs/Obsidian/standards/`）
- 进一步的速查：`docs/agent/README.md`

## 项目概览

鲸落（WhaleFall）是面向 DBA 团队的数据库资源管理平台，提供实例、账户、容量与任务调度的统一管理与审计能力。支持 PostgreSQL、MySQL、SQL Server、Oracle。

## 快速开始

```bash
make install
make dev-start
make init-db
python app.py  # http://127.0.0.1:5001
```

## 质量与测试

```bash
make format
make typecheck
uv run pytest -m unit
./scripts/ci/ruff-report.sh style
./scripts/ci/pyright-report.sh
./scripts/ci/refactor-naming.sh --dry-run
./scripts/ci/eslint-report.sh quick  # 改动 JS 时
```

## 文档入口

- `docs/README.md`
- `docs/Obsidian/standards/backend/README.md`
- `docs/Obsidian/standards/ui/README.md`

## 当前开发重点（可能变化）

- Grid.js 列表页迁移：标准化 wiring/分页/日志
- 账户分类 V2：schema-less 权限架构（见设计文档）
- 路由安全：迁移到 `safe_route_call` 统一错误处理/日志
- 类型检查：提升 Pyright 覆盖率

