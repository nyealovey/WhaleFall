# 常用命令

> 目标：把“怎么跑起来 / 怎么自检”集中到一页。

## 安装依赖

```bash
make install
```

## 启动/停止开发依赖（Docker：PostgreSQL + Redis）

```bash
make dev-start
make dev-status
make dev-logs
make dev-stop
```

更多子命令（如 `logs-db`/`logs-redis`/`logs-app`/`shell`）：`make dev help`

## 初始化数据库（运行迁移）

```bash
make init-db
```

## 启动 Flask 应用

```bash
python app.py  # http://127.0.0.1:5001
```

## 代码质量

```bash
make format
make typecheck
./scripts/ci/ruff-report.sh style
./scripts/ci/pyright-report.sh
./scripts/ci/refactor-naming.sh --dry-run
./scripts/ci/eslint-report.sh quick  # 改动 JS 时
```

## 测试

```bash
uv run pytest -m unit
```

### 测试分层（约定）

- 单元测试：`tests/unit/`（隔离、快速、无外部依赖）
- 集成测试：`tests/integration/`（需要 DB/Redis）
- 常用标记：`@pytest.mark.unit`、`@pytest.mark.integration`

## 本地“一键自检”（可选）

```bash
make dev quality
```
