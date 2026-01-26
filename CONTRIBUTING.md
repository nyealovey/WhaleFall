# Contributing

本仓库的协作与约束以 `docs/Obsidian/standards/` 为单一真源.

## Workflow

- 分支策略: 见 `docs/Obsidian/standards/core/guide/git-workflow.md`.
- 日常开发: 从 `dev` 拉分支, PR 合入 `dev`.

## Local checks

- Install: `make install`
- Format: `make format`
- Typecheck: `make typecheck`
- Unit tests: `uv run pytest -m unit`

## Optional: pre-commit

如果你希望在本地提交前自动执行基础门禁:

- Install: `uv sync --extra dev` (或按你的 Python 环境安装 `pre-commit`)
- Enable: `pre-commit install`
- Run: `pre-commit run --all-files`
