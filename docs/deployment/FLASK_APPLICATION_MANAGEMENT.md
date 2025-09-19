# Flask应用管理文档

## 概述

本文档介绍如何在生产环境中管理Flask应用，包括启动、停止、重启、调试等操作。

## 环境配置

### 生产环境架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   PostgreSQL    │    │     Redis       │
│  (反向代理)      │    │   (数据库)      │    │    (缓存)       │
│   Port: 80/443  │    │   Port: 5432    │    │   Port: 6379    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Flask应用      │
                    │  (业务逻辑)     │
                    │  Port: 5001     │
                    └─────────────────┘
```

### 服务依赖关系
- **Flask应用** 依赖 PostgreSQL 和 Redis
- **Nginx** 代理请求到 Flask 应用
- **基础环境** (PostgreSQL + Redis + Nginx) 可以独立运行
- **Flask应用** 通过 profiles 管理，可以独立启动/停止

## Flask应用管理

### 1. 启动Flask应用

#### 方法1：使用生产环境脚本（推荐）
```bash
# 启动基础环境（PostgreSQL + Redis + Nginx）
./scripts/docker/start-prod-base.sh

# 启动Flask应用
./scripts/docker/start-prod-flask.sh
```

#### 方法2：使用Docker Compose
```bash
# 启动基础环境
docker compose -f docker-compose.prod.yml up -d postgres redis nginx

# 启动Flask应用
docker compose -f docker-compose.prod.yml --profile flask up -d whalefall
```

#### 方法3：手动启动
```bash
# 构建Flask镜像
docker build -f Dockerfile.prod --target production -t whalefall:prod .

# 启动Flask容器
docker run -d \
  --name whalefall_app_prod \
  --network whalefall_prod_network \
  --env-file .env \
  -v ./userdata:/app/userdata \
  whalefall:prod
```

### 2. 停止Flask应用

#### 方法1：停止Flask容器
```bash
# 停止Flask应用容器
docker stop whalefall_app_prod

# 删除Flask应用容器
docker rm whalefall_app_prod
```

#### 方法2：使用Docker Compose
```bash
# 停止Flask应用
docker compose -f docker-compose.prod.yml --profile flask down
```

#### 方法3：停止整个生产环境
```bash
# 停止所有生产环境服务
./scripts/docker/stop-prod.sh
```

### 3. 重启Flask应用

#### 方法1：重启容器
```bash
# 重启Flask应用容器
docker restart whalefall_app_prod
```

#### 方法2：重新构建并启动
```bash
# 停止Flask应用
docker stop whalefall_app_prod
docker rm whalefall_app_prod

# 重新构建镜像
./scripts/docker/start-prod-flask.sh
```

### 4. 查看Flask应用状态

#### 检查容器状态
```bash
# 查看所有容器
docker ps -a

# 查看Flask应用容器
docker ps | grep whalefall_app_prod
```

#### 检查健康状态
```bash
# 检查Flask应用健康状态
docker exec whalefall_app_prod curl -f http://localhost:5001/health

# 检查详细健康状态
docker exec whalefall_app_prod curl -f http://localhost:5001/health/detailed
```

#### 查看日志
```bash
# 查看Flask应用日志
docker logs whalefall_app_prod

# 查看实时日志
docker logs -f whalefall_app_prod

# 查看最近30行日志
docker logs whalefall_app_prod --tail 30

# 查看特定时间段的日志
docker logs whalefall_app_prod --since "2025-01-01T00:00:00"
```

### 5. 调试Flask应用

#### 进入容器调试
```bash
# 进入Flask应用容器
docker exec -it whalefall_app_prod bash

# 在容器内执行命令
docker exec whalefall_app_prod python -c "import app; print('Flask app loaded successfully')"
```

#### 检查进程状态
```bash
# 查看容器内进程
docker exec whalefall_app_prod ps aux

# 查看supervisor状态
docker exec whalefall_app_prod supervisorctl status

# 查看supervisor日志
docker exec whalefall_app_prod cat /var/log/supervisord.log
```

#### 检查网络连接
```bash
# 检查数据库连接
docker exec whalefall_app_prod python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.models import db
    result = db.session.execute('SELECT 1').scalar()
    print(f'Database connection: {result}')
"

# 检查Redis连接
docker exec whalefall_app_prod python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app import cache
    cache.set('test', 'value')
    result = cache.get('test')
    print(f'Redis connection: {result}')
"
```

### 6. 更新Flask应用

#### 更新代码
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 停止Flask应用
docker stop whalefall_app_prod
docker rm whalefall_app_prod

# 3. 重新构建并启动
./scripts/docker/start-prod-flask.sh
```

#### 更新依赖
```bash
# 1. 修改pyproject.toml
# 2. 重新构建镜像
docker build -f Dockerfile.prod --target production -t whalefall:prod .

# 3. 重启Flask应用
docker restart whalefall_app_prod
```

### 7. 监控Flask应用

#### 资源使用情况
```bash
# 查看容器资源使用
docker stats whalefall_app_prod

# 查看容器详细信息
docker inspect whalefall_app_prod
```

#### 应用性能监控
```bash
# 查看Flask应用日志中的性能信息
docker logs whalefall_app_prod | grep -E "(INFO|WARNING|ERROR)"

# 查看Gunicorn工作进程
docker exec whalefall_app_prod ps aux | grep gunicorn
```

## 常见问题排查

### 1. Flask应用无法启动

#### 检查gunicorn安装
```bash
# 检查gunicorn是否安装
docker exec whalefall_app_prod which gunicorn

# 检查虚拟环境
docker exec whalefall_app_prod ls -la /app/.venv/bin/
```

#### 检查依赖安装
```bash
# 检查Python包
docker exec whalefall_app_prod pip list | grep gunicorn
```

### 2. 数据库连接问题

#### 检查数据库连接
```bash
# 检查PostgreSQL连接
docker exec whalefall_app_prod python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://whalefall_user:password@postgres:5432/whalefall_prod')
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

### 3. Redis连接问题

#### 检查Redis连接
```bash
# 检查Redis连接
docker exec whalefall_app_prod python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, password='password', decode_responses=True)
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
"
```

### 4. 网络连接问题

#### 检查网络连通性
```bash
# 检查容器网络
docker network ls
docker network inspect whalefall_prod_network

# 测试网络连接
docker exec whalefall_app_prod ping postgres
docker exec whalefall_app_prod ping redis
```

## 最佳实践

### 1. 启动顺序
1. 先启动基础环境（PostgreSQL + Redis + Nginx）
2. 等待基础服务健康检查通过
3. 再启动Flask应用

### 2. 监控建议
- 定期检查容器健康状态
- 监控应用日志中的错误信息
- 设置资源使用告警

### 3. 备份策略
- 定期备份数据库数据
- 备份应用配置文件
- 备份SSL证书

### 4. 安全建议
- 定期更新依赖包
- 使用非root用户运行应用
- 限制容器资源使用

## 相关脚本

### 生产环境脚本
- `scripts/docker/start-prod-base.sh` - 启动基础环境
- `scripts/docker/start-prod-flask.sh` - 启动Flask应用
- `scripts/docker/stop-prod.sh` - 停止生产环境

### 开发环境脚本
- `scripts/docker/start-dev-base.sh` - 启动开发基础环境
- `scripts/docker/start-dev-flask.sh` - 启动开发Flask应用
- `scripts/docker/stop-dev.sh` - 停止开发环境

## 配置文件

### Docker配置
- `docker-compose.prod.yml` - 生产环境Docker Compose配置
- `Dockerfile.prod` - 支持代理的Dockerfile
- `nginx/conf.d/whalefall-docker.conf` - Nginx配置

### 应用配置
- `.env` - 环境变量配置
- `pyproject.toml` - Python依赖配置
- `app/__init__.py` - Flask应用初始化

---

**注意**: 在生产环境中操作Flask应用时，请确保先备份重要数据，并测试操作步骤。
