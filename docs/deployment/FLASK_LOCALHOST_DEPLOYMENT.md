# Flask应用localhost部署指南

## 概述

本指南介绍如何将Flask应用部署为Docker容器，并连接到宿主机上运行的PostgreSQL和Redis服务（通过localhost连接）。

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                        宿主机                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ PostgreSQL  │  │   Redis     │  │   Flask Docker      │  │
│  │ (localhost) │  │ (localhost) │  │   (host网络)        │  │
│  │   :5432     │  │   :6379     │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 前提条件

### 1. 宿主机服务
确保以下服务在宿主机上运行：

- **PostgreSQL**: 监听 `localhost:5432`
- **Redis**: 监听 `localhost:6379`

### 2. 环境配置
复制并配置环境变量：

```bash
cp env.production .env
```

编辑 `.env` 文件，确保以下配置正确：

```bash
# 数据库配置
POSTGRES_DB=whalefall_prod
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=your_secure_password

# Redis配置
REDIS_PASSWORD=your_redis_password

# 应用配置
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
```

## 部署步骤

### 1. 快速部署

```bash
# 启动Flask应用
make flask start

# 查看状态
make flask status

# 健康检查
make flask health
```

### 2. 手动部署

```bash
# 构建镜像
docker-compose -f docker-compose.flask-only.yml build

# 启动服务
docker-compose -f docker-compose.flask-only.yml up -d

# 查看日志
docker-compose -f docker-compose.flask-only.yml logs -f
```

## 配置说明

### Docker Compose配置

Flask应用使用以下关键配置：

```yaml
services:
  whalefall:
    # 使用host网络模式
    network_mode: "host"
    
    # 环境变量配置
    environment:
      - DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}
      - CACHE_REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0
```

### 网络配置

- **网络模式**: `host` - 使用宿主机网络
- **数据库连接**: `localhost:5432` - 直接连接宿主机PostgreSQL
- **Redis连接**: `localhost:6379` - 直接连接宿主机Redis

## 管理命令

### 基本操作

```bash
# 启动应用
make flask start

# 停止应用
make flask stop

# 重启应用
make flask restart

# 查看状态
make flask status
```

### 日志管理

```bash
# 查看所有日志
make flask logs

# 查看应用日志
make flask logs-app

# 实时查看日志
make flask logs-follow
```

### 维护操作

```bash
# 进入容器shell
make flask shell

# 健康检查
make flask health

# 重新构建
make flask rebuild

# 清理资源
make flask clean
```

## 访问应用

部署成功后，可以通过以下地址访问：

- **主应用**: http://localhost
- **管理界面**: http://localhost/admin
- **健康检查**: http://localhost/health

## 故障排除

### 1. 连接问题

如果Flask应用无法连接到PostgreSQL或Redis：

```bash
# 检查宿主机服务状态
sudo netstat -tlnp | grep -E ':(5432|6379)'

# 检查容器网络
docker exec whalefall_app_prod netstat -tlnp | grep -E ':(5432|6379)'

# 测试连接
docker exec whalefall_app_prod ping localhost
```

### 2. 权限问题

确保PostgreSQL和Redis允许localhost连接：

**PostgreSQL配置** (`postgresql.conf`):
```
listen_addresses = 'localhost'
port = 5432
```

**PostgreSQL认证** (`pg_hba.conf`):
```
local   all             all                                     trust
host    all             all             127.0.0.1/32            md5
```

**Redis配置**:
```
bind 127.0.0.1
port 6379
```

### 3. 日志查看

```bash
# 查看详细日志
make flask logs-app

# 查看容器内部日志
docker exec whalefall_app_prod tail -f /app/userdata/logs/app.log
```

## 性能优化

### 1. 资源限制

在 `docker-compose.flask-only.yml` 中调整资源限制：

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

### 2. 连接池配置

在环境变量中配置数据库连接池：

```bash
# 数据库连接池配置
SQLALCHEMY_ENGINE_OPTIONS='{"pool_size": 20, "max_overflow": 30, "pool_recycle": 3600}'
```

## 安全注意事项

1. **网络安全**: 使用host网络模式，确保宿主机防火墙配置正确
2. **密码安全**: 使用强密码，定期更换
3. **访问控制**: 配置PostgreSQL和Redis的访问控制
4. **日志安全**: 定期清理敏感日志信息

## 监控和维护

### 1. 健康监控

```bash
# 定期健康检查
make flask health

# 查看资源使用情况
docker stats whalefall_app_prod
```

### 2. 日志轮转

应用内置日志轮转功能，日志文件位于：
- `/app/userdata/logs/app.log`
- `/app/userdata/logs/auth.log`
- `/app/userdata/logs/database.log`

### 3. 备份策略

定期备份PostgreSQL数据库：

```bash
# 数据库备份
pg_dump -h localhost -U whalefall_user whalefall_prod > backup_$(date +%Y%m%d).sql
```

## 升级和维护

### 1. 应用升级

```bash
# 停止应用
make flask stop

# 重新构建
make flask build

# 启动新版本
make flask start
```

### 2. 配置更新

修改 `.env` 文件后：

```bash
# 重启应用使配置生效
make flask restart
```

## 总结

这种部署方式适合以下场景：

- ✅ 已有PostgreSQL和Redis服务运行在宿主机
- ✅ 需要Flask应用直接访问宿主机服务
- ✅ 简化网络配置，避免容器网络复杂性
- ✅ 便于调试和维护

通过host网络模式，Flask应用可以直接访问localhost的PostgreSQL和Redis服务，简化了部署和配置过程。
