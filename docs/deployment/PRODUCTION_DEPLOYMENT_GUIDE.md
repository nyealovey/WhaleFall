# 🐟 鲸落生产环境部署指南

## 📋 概述

本文档详细说明鲸落项目的生产环境部署配置，包括Docker容器化部署、Nginx配置、数据库设置、监控和运维等内容。

## 🏗️ 架构设计

### 生产环境架构图

```mermaid
graph TB
    subgraph "外部访问"
        U[用户] --> LB[负载均衡器]
    end
    
    subgraph "Docker容器集群"
        LB --> N[Nginx容器<br/>端口80/443]
        N --> F[Flask应用容器<br/>Gunicorn + Supervisor]
        F --> P[PostgreSQL容器<br/>端口5432]
        F --> R[Redis容器<br/>端口6379]
    end
    
    subgraph "数据持久化"
        P --> PV1[PostgreSQL数据卷]
        R --> PV2[Redis数据卷]
    end
    
    subgraph "日志系统"
        F --> L1[应用日志]
        N --> L2[Nginx日志]
        P --> L3[数据库日志]
    end
```

### 服务组件

| 组件 | 版本 | 端口 | 功能 |
|------|------|------|------|
| Nginx | 1.18+ | 80, 443 | 反向代理、静态文件服务 |
| Flask | 3.0.3 | 5001 | Web应用服务 |
| Gunicorn | 生产级 | - | WSGI服务器 |
| PostgreSQL | 15-alpine | 5432 | 主数据库 |
| Redis | 7-alpine | 6379 | 缓存和会话存储 |
| Supervisor | - | - | 进程管理 |

## 🔧 环境配置

### 1. 系统要求

**最低配置：**
- CPU: 4核心
- 内存: 8GB
- 存储: 50GB SSD
- 操作系统: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

**推荐配置：**
- CPU: 8核心
- 内存: 16GB
- 存储: 100GB SSD
- 操作系统: Ubuntu 22.04 LTS

### 2. 环境变量配置

#### 生产环境变量文件 (`env.production`)

```bash
# ============================================================================
# 代理配置（企业环境）
# ============================================================================
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1,::1,internal.company.com

# ============================================================================
# 数据库配置
# ============================================================================
POSTGRES_DB=whalefall_prod
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=your_secure_password_here

# ============================================================================
# Redis配置
# ============================================================================
REDIS_PASSWORD=your_redis_password_here

# ============================================================================
# 应用安全配置
# ============================================================================
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
BCRYPT_LOG_ROUNDS=12

# ============================================================================
# 应用配置
# ============================================================================
APP_NAME=鲸落
APP_VERSION=1.0.0
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO

# ============================================================================
# 缓存配置
# ============================================================================
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ============================================================================
# 数据库连接配置
# ============================================================================
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
DATABASE_URL_PROD=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# ============================================================================
# 会话配置
# ============================================================================
PERMANENT_SESSION_LIFETIME=3600

# ============================================================================
# 其他配置
# ============================================================================
DEBUG=false
TESTING=false
```

## 🐳 Docker配置详解

### 1. Docker Compose配置 (`docker-compose.prod.yml`)

#### 服务配置对比

| 配置项 | 开发环境 | 生产环境 | 说明 |
|--------|----------|----------|------|
| 数据库名 | whalefall_dev | whalefall_prod | 环境隔离 |
| 容器名后缀 | _dev | _prod | 避免冲突 |
| 内存限制 | 2G | 4G | 生产环境更高性能 |
| CPU限制 | 2.0 | 4.0 | 生产环境更多资源 |
| 端口暴露 | 80, 5001 | 80, 443, 5001 | 生产环境支持HTTPS |
| 代理支持 | 无 | 有 | 企业环境代理 |

#### 资源分配

**PostgreSQL容器：**
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2.0'
    reservations:
      memory: 1G
      cpus: '1.0'
```

**Redis容器：**
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

**Flask应用容器：**
```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '4.0'
    reservations:
      memory: 2G
      cpus: '2.0'
```

### 2. Dockerfile配置 (`Dockerfile.prod`)

#### 多阶段构建

```dockerfile
# 基础阶段
FROM ubuntu:22.04 as base
# 安装系统依赖、Python环境、Oracle客户端

# 开发阶段
FROM base as development
# 开发环境特定配置

# 生产阶段
FROM base as production
# 生产环境优化配置
```

#### 代理支持

生产环境Dockerfile支持企业代理：

```dockerfile
# 代理配置 - 构建时参数
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 设置代理环境变量
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
```

## 🌐 Nginx配置

### 1. 站点配置 (`nginx/sites-available/whalefall-prod`)

#### 关键配置项

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    # 日志配置
    access_log /var/log/nginx/whalefall_access.log;
    error_log /var/log/nginx/whalefall_error.log warn;
    
    # 静态文件服务（生产环境优化）
    location /static/ {
        alias /app/app/static/;
        expires 1y;  # 1年缓存
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:5001/health/;
        # 健康检查特殊设置
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5001;
        # 生产环境优化设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

#### 开发vs生产环境差异

| 配置项 | 开发环境 | 生产环境 | 说明 |
|--------|----------|----------|------|
| 静态文件缓存 | 1小时 | 1年 | 生产环境长期缓存 |
| Cache-Control | public | public, immutable | 生产环境更严格 |
| 错误处理 | 基础 | 完整 | 生产环境更完善 |

### 2. Gunicorn配置 (`nginx/gunicorn/gunicorn-prod.conf.py`)

#### 生产环境优化

```python
# 工作进程配置
workers = 2  # 固定2个进程
worker_class = "gevent"  # 异步工作器
worker_connections = 1000  # 连接数

# 性能优化
max_requests = 1000  # 最大请求数
max_requests_jitter = 50  # 抖动
preload_app = True  # 预加载应用

# 日志配置
loglevel = "info"  # 生产环境日志级别
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

## 🔄 进程管理

### Supervisor配置 (`nginx/supervisor/whalefall-prod.conf`)

```ini
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisord.log
pidfile=/var/run/supervisord.pid

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
directory=/etc/nginx
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/nginx/nginx.log

[program:whalefall]
command=/app/.venv/bin/gunicorn --config /app/gunicorn.conf.py app:app
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=false
stdout_logfile=/app/userdata/logs/whalefall.log
stderr_logfile=/app/userdata/logs/whalefall_error.log
```

## 🚀 部署流程

### 1. 环境准备

```bash
# 1. 安装Docker和Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER

# 2. 克隆项目
git clone https://github.com/your-org/TaifishingV4.git
cd TaifishingV4

# 3. 配置环境变量
cp env.production .env
# 编辑.env文件，设置正确的配置
```

### 2. 部署命令

```bash
# 使用Makefile部署
make prod deploy

# 或者直接使用Docker Compose
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. 验证部署

```bash
# 检查服务状态
make prod status

# 健康检查
make prod health

# 查看日志
make prod logs
```

## 📊 监控和运维

### 1. 日志管理

#### 日志文件位置

| 服务 | 日志文件 | 说明 |
|------|----------|------|
| Nginx | `/var/log/nginx/whalefall_access.log` | 访问日志 |
| Nginx | `/var/log/nginx/whalefall_error.log` | 错误日志 |
| Flask | `/app/userdata/logs/whalefall.log` | 应用日志 |
| Flask | `/app/userdata/logs/whalefall_error.log` | 应用错误日志 |
| Gunicorn | `/app/userdata/logs/gunicorn_access.log` | Gunicorn访问日志 |
| Gunicorn | `/app/userdata/logs/gunicorn_error.log` | Gunicorn错误日志 |

#### 日志查看命令

```bash
# 查看所有日志
make prod logs

# 查看特定服务日志
make prod logs-app    # 应用日志
make prod logs-db     # 数据库日志
make prod logs-redis  # Redis日志
```

### 2. 健康检查

#### 自动健康检查

```bash
# 应用健康检查
curl -f http://localhost/health

# 数据库健康检查
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod

# Redis健康检查
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

#### 监控指标

| 指标 | 阈值 | 说明 |
|------|------|------|
| CPU使用率 | < 80% | 避免过载 |
| 内存使用率 | < 85% | 防止OOM |
| 磁盘使用率 | < 90% | 避免空间不足 |
| 响应时间 | < 2s | 用户体验 |
| 错误率 | < 1% | 系统稳定性 |

### 3. 备份和恢复

#### 数据备份

```bash
# 备份数据库
make prod backup

# 手动备份
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U whalefall_user -d whalefall_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 数据恢复

```bash
# 恢复数据库
make prod restore FILE=backup_file.sql

# 手动恢复
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod < backup_file.sql
```

## 🔒 安全配置

### 1. 网络安全

- 使用防火墙限制端口访问
- 配置HTTPS证书（推荐）
- 设置适当的CORS策略

### 2. 应用安全

- 使用强密码和密钥
- 定期更新依赖包
- 启用日志审计

### 3. 数据安全

- 数据库连接加密
- 敏感数据加密存储
- 定期备份数据

## 🛠️ 故障排除

### 1. 常见问题

#### 容器启动失败

```bash
# 检查容器日志
docker logs whalefall_app_prod

# 检查Nginx配置
docker exec whalefall_app_prod nginx -t

# 检查环境变量
docker exec whalefall_app_prod env | grep -E "(POSTGRES|REDIS|SECRET)"
```

#### 数据库连接失败

```bash
# 检查数据库状态
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod

# 检查网络连接
docker network ls
docker network inspect taifishingv4_whalefall_prod_network
```

#### 应用无法访问

```bash
# 检查端口映射
docker port whalefall_app_prod

# 检查防火墙
sudo ufw status
sudo iptables -L
```

### 2. 性能优化

#### 数据库优化

```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_accounts_created_at ON accounts(created_at);
CREATE INDEX CONCURRENTLY idx_permissions_user_id ON permissions(user_id);

-- 分析表统计信息
ANALYZE accounts;
ANALYZE permissions;
```

#### 应用优化

```python
# 启用数据库连接池
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# 启用Redis缓存
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://:password@redis:6379/0'
```

## 📈 扩展和维护

### 1. 水平扩展

- 使用Docker Swarm或Kubernetes
- 配置负载均衡器
- 实现数据库读写分离

### 2. 版本更新

```bash
# 更新到最新版本
make prod update

# 回滚到上一个版本
make prod rollback
```

### 3. 监控集成

- 集成Prometheus + Grafana
- 配置告警规则
- 实现自动化运维

## 📚 参考文档

- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose文档](https://docs.docker.com/compose/)
- [Nginx配置指南](https://nginx.org/en/docs/)
- [Gunicorn配置](https://docs.gunicorn.org/en/stable/configure.html)
- [PostgreSQL文档](https://www.postgresql.org/docs/)
- [Redis文档](https://redis.io/documentation)

---

**注意**: 本指南基于当前项目配置，请根据实际环境需求进行调整。定期更新文档以保持与代码同步。
