# 部署 Runbook（Docker Compose）

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：生产部署（`docker-compose.prod.yml` / `Dockerfile.prod` / `.env`）与日常运维命令
> 关联：`../../standards/documentation-standards.md`；`../../standards/backend/configuration-and-secrets.md`；`../../standards/backend/database-migrations.md`；`../../standards/backend/task-and-scheduler.md`；`../../reference/database/schema-baseline.md`；`../hot-update/hot-update-guide.md`

## 适用场景

- 在单机/单实例上以 Docker Compose 方式部署 WhaleFall（包含 PostgreSQL、Redis、应用容器，应用容器内置 Nginx + Gunicorn + Supervisor）。
- 日常发布/配置变更（**不清库、不删卷** 的常规部署）。
- 需要“先能跑起来、可验证、可回滚”的标准操作流程。

> 注意：本仓库同时存在 `docker compose`（v2）与 `docker-compose`（v1）两种用法：  
> - `scripts/deploy/*` 使用 `docker compose`；  
> - `Makefile.prod` 使用 `docker-compose`。  
> 若你的机器只有一种，请自行安装另一种或做别名（例如 `alias docker-compose='docker compose'`）。

## 前置条件

1) **系统与工具**
- Linux 服务器（推荐 Ubuntu 22.04）。
- 已安装 Docker + Compose（可运行 `docker info` / `docker compose version`）。
- 已安装 `git`、`curl`。

2) **端口与网络**
- 默认会占用宿主机端口：`80`、`443`、`5001`、`5432`、`6379`（见 `docker-compose.prod.yml`）。
- 生产环境建议：
  - 仅对外开放 `80/443`；
  - `5432/6379` 用防火墙限制到本机/内网，或移除 Compose 的端口映射。

3) **配置与密钥（必须先看标准）**
- 按 `../../standards/backend/configuration-and-secrets.md` 生成并填写生产密钥：
  - `SECRET_KEY` / `JWT_SECRET_KEY` / `PASSWORD_ENCRYPTION_KEY`
  - `POSTGRES_PASSWORD` / `REDIS_PASSWORD`
- `.env` 必须为未跟踪文件，禁止提交到仓库。

4) **数据库初始化/迁移策略（必须二选一）**
- 迁移与基线规则见 `../../standards/backend/database-migrations.md` 与 `../../reference/database/schema-baseline.md`。
- **空库初始化二选一**（不要重复执行两条路径）：
  - 方案 A：直接 `flask db upgrade`
  - 方案 B：执行 `sql/init/postgresql/**` 后 `flask db stamp 20251219161048`

## 步骤

### 1) 拉取代码并进入目录

```bash
mkdir -p /opt/whalefall
cd /opt/whalefall
git clone https://github.com/nyealovey/WhaleFall.git .
```

### 2) 配置 `.env`

```bash
cp env.example .env
${EDITOR:-vim} .env
```

最小检查清单（生产必须非空）：
- `POSTGRES_PASSWORD` / `REDIS_PASSWORD`
- `SECRET_KEY` / `JWT_SECRET_KEY` / `PASSWORD_ENCRYPTION_KEY`
- `APP_NAME` / `APP_VERSION` / `FLASK_ENV=production`
- `DATABASE_URL`（容器网络内用 `postgres` 服务名）
- `CACHE_REDIS_URL`（容器网络内用 `redis` 服务名）

### 3) 验证环境变量（可选但推荐）

```bash
./scripts/setup/validate-env.sh
```

> 说明：`scripts/setup/validate-env.sh` 会校验 URL 形态与必填项；如失败，优先修正 `.env`，不要“跳过校验继续部署”。

### 4) 构建并启动生产环境

二选一（推荐优先用仓库入口 `make prod`）：

```bash
# 方式 A：Makefile 入口
make prod deploy
```

```bash
# 方式 B：直接 Docker Compose
docker compose -f docker-compose.prod.yml up -d --build
```

启动后应看到 3 个服务：
- `postgres`（容器名：`whalefall_postgres_prod`）
- `redis`（容器名：`whalefall_redis_prod`）
- `whalefall`（容器名：`whalefall_app_prod`，内置 Nginx + Gunicorn）

### 5) 初始化/升级数据库 Schema

#### 场景 A：全新环境（空库）

按 `../../reference/database/schema-baseline.md` **二选一**：

**方案 A（推荐）**：用 Alembic 建库

```bash
docker compose -f docker-compose.prod.yml exec whalefall bash -lc "cd /app && /app/.venv/bin/flask db upgrade"
```

**方案 B**：先执行 SQL 初始化脚本，再 stamp 基线版本

```bash
set -a; source .env; set +a
docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < sql/init/postgresql/init_postgresql.sql
# 分区子表按需执行（示例：2025-07/2025-08）
docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < sql/init/postgresql/partitions/init_postgresql_partitions_2025_07.sql
docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < sql/init/postgresql/partitions/init_postgresql_partitions_2025_08.sql
docker compose -f docker-compose.prod.yml exec whalefall bash -lc "cd /app && /app/.venv/bin/flask db stamp 20251219161048"
```

#### 场景 B：已有库（升级）

```bash
docker compose -f docker-compose.prod.yml exec whalefall bash -lc "cd /app && /app/.venv/bin/flask db upgrade"
```

## 验证

1) **服务状态**

```bash
docker compose -f docker-compose.prod.yml ps
```

2) **健康检查（建议同时走 Nginx 与直连 Gunicorn）**

```bash
curl -f http://localhost/health/api/basic
curl -f http://localhost:5001/health/api/health
```

3) **关键日志**

```bash
docker compose -f docker-compose.prod.yml logs --tail 200 whalefall
docker compose -f docker-compose.prod.yml logs --tail 200 postgres
docker compose -f docker-compose.prod.yml logs --tail 200 redis
```

4) **容器内日志位置（用于精确定位）**
- Supervisor：`/var/log/supervisord.log`
- Nginx：
  - ` /var/log/nginx/whalefall_access.log`
  - ` /var/log/nginx/whalefall_error.log`
- Gunicorn：
  - `/app/userdata/logs/gunicorn_access.log`
  - `/app/userdata/logs/gunicorn_error.log`
  - `/app/userdata/logs/whalefall.log`
  - `/app/userdata/logs/whalefall_error.log`

## 回滚

### 回滚代码（不清库）

1) 回滚到上一个提交（示例）：

```bash
git log --oneline -n 20
git reset --hard <good_commit_sha>
```

2) 重新构建并启动（与部署方式保持一致）：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

> 若你使用了热更新脚本，请改用 `../hot-update/hot-update-guide.md` 的回滚流程（脚本会强制以远端为准）。

### 回滚数据库

- 迁移回滚依赖具体 revision 是否提供 downgrade，且存在生产风险；默认建议走“备份恢复”。
- 建议在每次上线前执行一次 `pg_dump` 备份，必要时按备份文件恢复。

## 故障排查

### 1) `docker-compose` / `docker compose` 命令不存在

- 优先确保 `docker compose version` 可用（Docker Compose v2）。
- 若 `make prod` 依赖 `docker-compose` 但系统只有 v2，可临时使用：

```bash
alias docker-compose='docker compose'
```

### 2) `.env` 校验失败（URL/必填项）

- 直接运行并修复：

```bash
./scripts/setup/validate-env.sh
```

- `docker-compose.prod.yml` 内会覆盖部分变量（如 `DATABASE_URL` / `CACHE_REDIS_URL`），但 **`.env` 仍必须通过校验**，否则 `make prod deploy` 会失败。

### 3) 端口冲突（80/443/5432/6379/5001）

- 查看占用：

```bash
sudo ss -lntp | egrep '(:80|:443|:5001|:5432|:6379)\\b' || true
```

- 处理方式：
  - 停掉占用端口的服务；或
  - 修改 `docker-compose.prod.yml` 的端口映射后再部署。

### 4) 应用容器 `unhealthy` / 启动失败

```bash
docker compose -f docker-compose.prod.yml logs --tail 200 whalefall
docker exec -it whalefall_app_prod bash
```

容器内重点检查：
- Supervisor 是否在运行：`ps aux | grep supervisord`
- Nginx 是否在运行：`ps aux | grep nginx`
- Gunicorn 是否在运行：`ps aux | grep gunicorn`
- Nginx 配置：`nginx -t`（配置位于 `/etc/nginx/sites-enabled/whalefall`）

### 5) 迁移失败（重复建表 / 基线不一致）

- 按 `../../standards/backend/database-migrations.md` 与 `../../reference/database/schema-baseline.md` 执行：
  - 空库：`upgrade` 或 `SQL init + stamp` 二选一
  - 已有库：优先 `stamp` 对齐版本，再 `upgrade`

### 6) 数据/日志不持久化

- 当前 `docker-compose.prod.yml` **未为应用容器挂载持久化卷**（`/app/userdata` 在容器内）。  
  需要长期保留 `uploads/logs/backups` 时，应在生产环境增加 volume 挂载并做权限校验后再上线。
