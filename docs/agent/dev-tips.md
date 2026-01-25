# 开发 / 排障技巧

## 运行单个测试

```bash
uv run pytest tests/unit/test_specific.py::test_function_name -v
```

## 调试与日志

- 本地启用调试：在 `.env` 设置 `FLASK_DEBUG=true`（不要提交 `.env`）
- 依赖服务日志：`make dev-logs`（或 `make dev logs-db` / `make dev logs-redis`）
- 如启用本地文件日志：`make dev logs-app`（默认读取 `userdata/logs/app.log`，运行时可能才会生成）
- 结构化日志/统一日志表：见 `docs/agent/architecture.md`（以及 `unified_log`）
- UI 查看统一日志：`/history/logs`

## 连接开发数据库（psql）

```bash
make dev shell
```

## 数据库迁移

```bash
# 创建新迁移
uv run flask --app app:create_app db migrate -m "description"

# 应用迁移
uv run flask --app app:create_app db upgrade

# 回滚
uv run flask --app app:create_app db downgrade
```

迁移硬约束（SSOT）：`docs/Obsidian/standards/backend/hard/database-migrations.md`

## 管理员账户管理

```bash
# 显示管理员密码
python scripts/show_admin_password.py

# 重置管理员密码
python scripts/reset_admin_password.py
```
