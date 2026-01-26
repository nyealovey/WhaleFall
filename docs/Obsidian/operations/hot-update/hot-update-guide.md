---
title: 热更新 Runbook (覆盖代码 + 迁移 + 重启)
aliases:
  - hot-update-guide
tags:
  - operations
  - operations/hot-update
  - runbook
status: draft
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: 生产环境热更新脚本 scripts/deploy/update-prod-flask.sh(不重建镜像, 保留数据)
related:
  - "[[operations/hot-update/README|热更新 Runbook 索引]]"
  - "[[operations/deployment/deployment-guide|标准部署 Runbook]]"
  - "[[standards/backend/standard/configuration-and-secrets]]"
  - "[[standards/backend/standard/database-migrations]]"
  - "[[reference/database/schema-baseline]]"
---

# 热更新 Runbook (覆盖代码 + 迁移 + 重启)

> [!danger] Data loss risk
> 热更新脚本会 `git reset --hard origin/main` 并覆盖运行中容器内 `/app/`.
> 运行前务必确认: 仓库工作区无未提交改动, 且你接受 "以远端 main 为准".

## 适用场景

- 生产环境需要快速发布小改动(页面/接口/逻辑修复), 希望不重建镜像, 尽量降低停机时间.
- 已通过 `docker-compose.prod.yml` 部署并正在运行(`postgres/redis/whalefall` 均 Up).
- 允许脚本按 "远端 main 分支" 为真源, 把本地工作区强制同步到 `origin/main`.

> [!note] Not suitable
> 不适用(建议走 [[operations/deployment/deployment-guide|标准部署]]):
> - 依赖变更(Python 包/系统依赖变更)需要重新构建镜像.
> - 需要从某个指定 commit/tag 部署(该脚本默认强制 `reset --hard origin/main`).
> - 需要变更 Dockerfile / Nginx / Supervisor 启动方式并验证镜像层.

## 前置条件

### 1) 必备工具

- `docker compose` 可用(脚本使用 v2 子命令).
- `git` 可用, 且当前目录是 WhaleFall Git 仓库.
- `curl` 可用(用于健康检查).

### 2) 运行状态

- `docker compose -f docker-compose.prod.yml ps` 显示 `postgres/redis/whalefall` 都是 `Up`.
- `.env` 存在且包含生产密钥(详见 [[standards/backend/standard/configuration-and-secrets]]).

### 3) 风险认知(脚本会做的事)

- 强制同步代码: `git fetch origin main` + `git reset --hard origin/main` (会丢弃本地未提交改动).
- 覆盖容器内 `/app/`: 把仓库代码拷贝进运行中的 `whalefall` 容器.
- 清理缓存: 删除 `__pycache__/*.pyc`, 并清理 `/var/cache/nginx` 等.
- 数据库迁移: 尝试执行 `flask db stamp`(必要时)与 `flask db upgrade`(参见脚本的防御逻辑).
- 重启服务: 重启 `whalefall` 容器并 reload Nginx.

## 步骤

### 1) 进入部署目录并确认仓库干净

```bash
cd /opt/whalefall
git status --porcelain
```

> 若有本地未提交改动: 先提交/备份, 否则热更新脚本会被 `reset --hard` 清掉.

### 2) 运行热更新脚本

```bash
bash scripts/deploy/update-prod-flask.sh
```

脚本成功后会输出本次部署的 commit (`git rev-parse --short HEAD`) 与健康检查结果.

## 验证

### 1) 服务状态

```bash
docker compose -f docker-compose.prod.yml ps
```

### 2) 健康检查(脚本默认检查 5001 直连)

```bash
curl -f http://localhost/api/v1/health/basic
curl -f http://localhost:5001/api/v1/health/health
```

### 3) 关键日志

```bash
docker compose -f docker-compose.prod.yml logs --tail 200 whalefall
docker exec -it whalefall_app_prod bash -lc "tail -n 200 /app/userdata/logs/gunicorn_error.log || true"
```

## 回滚

### 1) 回滚代码(推荐: 回滚远端, 再热更新)

该热更新脚本默认 "以 GitHub 为准", 强制同步到 `origin/main`.

- 想回滚生产, 推荐先让远端 `main` 回到可用状态(`git revert` 或回滚发布流程), 再运行热更新脚本一次.

### 2) 回滚数据库

- 默认不建议在生产直接执行 `flask db downgrade`; 优先使用部署前备份恢复.
- 迁移基线与 stamp 规则参考 [[reference/database/schema-baseline]].

## 故障排查

### 1) 脚本提示 `docker compose` 不存在

```bash
docker compose version
```

若不可用, 请先安装 Docker Compose v2 插件, 或改走 `make prod deploy` (但注意 `Makefile.prod` 使用 `docker-compose`).

### 2) Git 同步失败(无法 fetch / origin/main 不存在)

- 确认 remote/branch 名称:

```bash
git remote -v
git branch -vv
```

- 默认脚本假设存在 `origin` 且有 `main` 分支, 若你使用 `master` 或私有源, 请先调整脚本或使用标准部署流程.

### 3) `flask db stamp/upgrade` 失败

优先按标准文档排查与修复(不要反复重试扩大破坏面):

- [[standards/backend/standard/database-migrations]]
- [[reference/database/schema-baseline]]

手工进入容器执行(用于排障):

```bash
docker exec -it whalefall_app_prod bash
cd /app
/app/.venv/bin/flask db current || true
/app/.venv/bin/flask db history | head
/app/.venv/bin/flask db upgrade
```

### 4) 热更新后页面仍是旧资源(浏览器缓存)

- 对静态资源更新, 浏览器可能需要强制刷新:
  - Chrome/Edge: `Ctrl+F5`
  - macOS: `Cmd+Shift+R`

### 5) 热更新后出现 502/504

```bash
docker compose -f docker-compose.prod.yml logs --tail 200 whalefall
docker exec -it whalefall_app_prod bash -lc "ps aux | egrep 'supervisord|nginx|gunicorn' | grep -v grep"
```

重点检查:
- Supervisor 是否仍在托管进程(`/var/log/supervisord.log`)
- Gunicorn 是否可启动(`/app/userdata/logs/gunicorn_error.log`)
- Nginx 配置是否可 reload (`nginx -t`)
