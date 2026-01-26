---
title: 生产部署 Runbook (全量重建脚本)
aliases:
  - production-deployment
tags:
  - operations
  - operations/deployment
  - runbook
  - risky
status: draft
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: 使用 scripts/deploy/deploy-prod-all.sh 进行生产环境完全重建(含 DB 初始化与 Alembic stamp)
related:
  - "[[operations/deployment/deployment-guide|标准部署 Runbook]]"
  - "[[standards/backend/standard/configuration-and-secrets]]"
  - "[[standards/backend/standard/database-migrations]]"
  - "[[reference/database/schema-baseline]]"
---

# 生产部署 Runbook (全量重建脚本)

> [!danger] High risk
> `scripts/deploy/deploy-prod-all.sh` 可能停止容器, 删除 volumes(数据丢失), 并将 PostgreSQL `pg_hba.conf` 改为 `trust`(安全风险).
> 优先使用 [[operations/deployment/deployment-guide|标准部署 Runbook]]; 只有在明确场景下才使用本 Runbook.

## 适用场景

- 新机器首次部署, 希望用脚本一键拉起 `postgres/redis/whalefall` 并执行数据库初始化.
- 环境严重漂移/不可控, 决定 "停止现有环境 -> 重新构建镜像 -> 重新拉起服务"(可选清理卷).
- 灾备演练的标准化脚本入口(要求事先准备好备份与回滚方案).

> [!note] Not for daily release
> 不适用: 只做小改动, 追求最小变更/最小风险的日常发布.
> 日常发布优先使用 [[operations/deployment/deployment-guide|标准部署]] 或 [[operations/hot-update/hot-update-guide|热更新]].

## 前置条件

### 1) 强制备份

- 若机器上已有数据, 必须先备份 PostgreSQL 数据(建议 `pg_dump`), 并确认备份可用.

### 2) 脚本行为确认(高风险点)

`scripts/deploy/deploy-prod-all.sh` 可能执行:

- `docker compose down` 停止现有容器.
- (可选) 删除 WhaleFall 相关 docker volumes(会清空数据库数据与 Redis 数据).
- 修改 PostgreSQL 容器内 `pg_hba.conf` 为 `trust`(见脚本 `fix_postgresql_connection`), 存在安全风险.

### 3) 工具

- 必须支持 `docker compose`(脚本使用 v2 子命令).
- 已安装 `git`, `curl`.

### 4) 配置

- `env.example` 已复制为 `.env` 且必填项已填写(见 [[standards/backend/standard/configuration-and-secrets]]).

## 步骤

### 1) 进入部署目录并确认 `.env`

```bash
cd /opt/whalefall
test -f .env || cp env.example .env
${EDITOR:-vim} .env
```

### 2) 运行全量部署脚本

```bash
bash scripts/deploy/deploy-prod-all.sh
```

脚本关键交互点:
- 若检测到历史卷, 会提示是否删除数据, 并要求输入 `DELETE ALL DATA` 才会执行删除.
- 输入不匹配会退出部署.

### 3) (强烈建议) 部署完成后恢复 PostgreSQL 访问控制

脚本会把 `pg_hba.conf` 从 `scram-sha-256` 替换为 `trust` 来 "快速绕过连接问题".
如果 `docker-compose.prod.yml` 同时暴露了 `5432:5432`, 将导致任何可访问该端口的来源都可以无密码连接数据库.

最低加固动作(二选一或同时做):

**A. 立即恢复 `pg_hba.conf` (推荐)**

```bash
docker compose -f docker-compose.prod.yml exec postgres sh -lc "sed -i 's/host all all all trust/host all all all scram-sha-256/' /var/lib/postgresql/data/pg_hba.conf && psql -U postgres -c 'SELECT pg_reload_conf();'"
```

**B. 限制端口暴露 (推荐)**

- 用防火墙限制 `5432/6379` 仅本机/内网可访问, 或在 `docker-compose.prod.yml` 移除 `ports: 5432:5432` / `6379:6379`.

## 验证

### 1) 服务状态

```bash
docker compose -f docker-compose.prod.yml ps
```

### 2) 健康检查

```bash
curl -f http://localhost/api/v1/health/basic
curl -f http://localhost:5001/api/v1/health/health
```

### 3) 数据库表数量(确认初始化有效)

```bash
set -a; source .env; set +a
docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

### 4) 日志(失败时优先看这里)

```bash
docker compose -f docker-compose.prod.yml logs --tail 200 whalefall
docker compose -f docker-compose.prod.yml logs --tail 200 postgres
```

## 回滚

### 1) 代码回滚

- 若本次部署的代码有问题: 回退到上一个可用提交后, 按 [[operations/deployment/deployment-guide]] 的 "回滚代码" 重新构建并启动.

### 2) 数据回滚(优先)

- 若本次部署影响了数据库结构/数据: 用部署前的备份恢复到 PostgreSQL(推荐).
- 不要依赖 "删除卷重来" 当作回滚: 一旦误删卷, 只有备份能救.

## 故障排查

### 1) 脚本提示缺少 `docker compose`

```bash
docker compose version
```

若不可用, 请先安装 Docker Compose v2 插件, 再重试.

### 2) 脚本在 "修复 PostgreSQL 连接" 卡住/失败

- 先确认 postgres 容器健康:

```bash
docker compose -f docker-compose.prod.yml ps postgres
docker compose -f docker-compose.prod.yml logs --tail 200 postgres
```

- 若 `pg_hba.conf` 已被写为 `trust` 仍无法连接, 说明问题不在认证而在网络/容器状态, 不要继续扩大权限, 优先修复容器运行问题.

### 3) 数据库初始化失败(SQL 执行报错)

- 参考 [[reference/database/schema-baseline]], 确认:
  - 是否对 "非空库" 重复执行了初始化脚本.
  - 是否漏执行分区脚本导致插入分区表时报错.

### 4) 应用容器启动但页面 502/504

- Nginx/Gunicorn 由 Supervisor 托管(见 `/etc/supervisor/conf.d/whalefall.conf`), 进入容器检查:

```bash
docker exec -it whalefall_app_prod bash
ps aux | egrep 'supervisord|nginx|gunicorn' | grep -v grep
nginx -t || true
tail -n 200 /app/userdata/logs/gunicorn_error.log || true
```
