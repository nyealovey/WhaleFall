# 本地开发(从 0 跑起来)

> 状态: Draft  
> 适用人群: 开发者/贡献者  
> 目标: 用可复制命令在本机跑起 WhaleFall(依赖服务 + 迁移 + 首次登录)

## 1. 前置要求

- 已安装:
  - `uv`
  - Docker Desktop(推荐, 用于启动 PostgreSQL/Redis)

## 2. 安装依赖(uv/make)

```bash
# 安装 Python 依赖
make install

# (可选) 安装 dev 依赖(ruff/pyright/pytest 等)
uv sync --group dev
```

## 3. 准备 .env(开发环境)

> [!warning]
> `.env` 禁止提交到仓库, 只保留本机使用.

```bash
cp env.example .env
```

最小建议配置(按需覆盖/补齐):

```bash
# app runtime
FLASK_ENV=development
FLASK_DEBUG=1

# postgres (dev container)
POSTGRES_DB=whalefall_dev
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=dev

# redis (dev container)
REDIS_PASSWORD=dev

# app connects to local docker ports
DATABASE_URL=postgresql+psycopg://whalefall_user:dev@localhost:5432/whalefall_dev
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:dev@localhost:6379/0

# (推荐) 固定 secret, 避免每次重启导致 session/jwt 失效
SECRET_KEY=dev_secret_key_replace_me
JWT_SECRET_KEY=dev_jwt_secret_key_replace_me
```

更多配置项说明见 `docs/Obsidian/reference/config/environment-variables.md`.

## 4. 启动依赖服务(PostgreSQL + Redis)

```bash
# 启动 dev 依赖服务(只包含 postgres/redis)
make dev-start

# 查看状态
make dev-status
```

如需停止:

```bash
make dev-stop
```

## 5. 初始化数据库(init-db)

```bash
make init-db
```

说明:
- 该步骤会执行 Alembic/Flask-Migrate 的迁移.
- 如果你想快速重置到干净状态, 先看第 8 节.

## 6. 首次创建管理员账号(首次登录)

WhaleFall 不会自动创建 `admin` 账号. 你需要在初始化数据库后创建一次.

密码要求(与 `User.set_password` 一致):
- 长度 >= 8
- 必须包含: 大写字母 + 小写字母 + 数字

创建/获取一组可用的 `admin` 凭据(会打印明文密码到你的终端):

```bash
uv run python - <<'PY'
from __future__ import annotations

import secrets
import string

from app import create_app, db
from app.models.user import User


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isupper() for c in pwd) and any(c.islower() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


app = create_app(init_scheduler_on_start=False)
with app.app_context():
    existing = User.query.filter_by(username="admin").first()
    if existing:
        print("admin already exists")
    else:
        password = _generate_password()
        user = User(username="admin", password=password, role="admin")
        db.session.add(user)
        db.session.commit()
        print(f"admin created, password: {password}")
PY
```

## 7. 启动应用并验证

启动 Web:

```bash
uv run flask --app app:create_app run --host 127.0.0.1 --port 5001
```

验证 health:

```bash
curl -s http://127.0.0.1:5001/api/v1/health/basic
```

访问入口:
- Web: `http://127.0.0.1:5001`
- Swagger UI: `http://127.0.0.1:5001/api/v1/docs`

## 8. 重置 DB(清库重来)

当迁移链/数据状态混乱, 或你需要回到"全新环境"时:

```bash
# 停止并删除 dev volumes(会清空 postgres/redis 数据)
make dev clean-data

# 重新启动依赖服务
make dev-start

# 重新跑迁移
make init-db
```

## 9. 常见错误

### 9.1 make dev-start 失败: docker compose 不可用

- 确认 Docker Desktop 已启动.
- 确认 `docker compose version` 可用.

### 9.2 端口冲突(5432/6379)

- 如果本机已运行 PostgreSQL/Redis, 请先停止本机服务, 或修改 `docker-compose.dev.yml` 的端口映射, 并同步更新 `.env` 里的 `DATABASE_URL/CACHE_REDIS_URL`.

### 9.3 init-db 报错: 无法连接数据库

- 先确认 `make dev-status` 中 postgres/redis 为健康.
- 检查 `.env` 中 `DATABASE_URL` 是否为 `localhost:5432` 且用户名/密码/库名与 compose 一致.

### 9.4 登录失败: 没有 admin 用户

- 重新执行第 6 节的创建脚本.
