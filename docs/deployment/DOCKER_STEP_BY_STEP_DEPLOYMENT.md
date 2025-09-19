# Docker分步部署指南

## 概述

本项目支持分两步部署Docker环境：
1. **第一步**：启动基础环境（PostgreSQL + Redis + Nginx）
2. **第二步**：启动Flask应用

支持两种环境：
- **本地开发环境**：macOS，无代理
- **服务器正式环境**：x86，有代理

## 本地开发环境（macOS，无代理）

### 第一步：启动基础环境

```bash
# 启动基础环境（PostgreSQL + Redis + Nginx）
./scripts/docker/start-dev-base.sh
```

**包含服务**：
- PostgreSQL (localhost:5432)
- Redis (localhost:6379)
- Nginx (http://localhost)

**检查状态**：
```bash
# 查看基础环境状态
docker-compose -f docker-compose.dev.yml ps postgres redis nginx

# 检查服务健康状态
curl http://localhost
```

### 第二步：启动Flask应用

```bash
# 启动Flask应用
./scripts/docker/start-dev-flask.sh
```

**包含服务**：
- Flask应用 (http://localhost:5001)
- 通过Nginx代理访问 (http://localhost)

**检查状态**：
```bash
# 查看完整环境状态
docker-compose -f docker-compose.dev.yml ps

# 检查Flask应用
curl http://localhost:5001/health
curl http://localhost
```

### 停止服务

```bash
# 停止所有服务
./scripts/docker/stop-dev.sh

# 停止并清理数据卷
./scripts/docker/stop-dev.sh --volumes

# 停止并清理镜像
./scripts/docker/stop-dev.sh --images
```

## 服务器正式环境（x86，有代理）

### 环境准备

```bash
# 设置代理环境变量
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,::1

# 复制生产环境配置
cp env.production .env
```

### 第一步：启动基础环境

```bash
# 启动基础环境（PostgreSQL + Redis + Nginx）
./scripts/docker/start-prod-base.sh
```

**包含服务**：
- PostgreSQL (localhost:5432)
- Redis (localhost:6379)
- Nginx (http://localhost)

**检查状态**：
```bash
# 查看基础环境状态
docker-compose -f docker-compose.prod.yml ps postgres redis nginx

# 检查服务健康状态
curl http://localhost
```

### 第二步：启动Flask应用

```bash
# 启动Flask应用（使用代理构建）
./scripts/docker/start-prod-flask.sh
```

**包含服务**：
- Flask应用（通过Nginx代理访问）
- 支持Oracle数据库连接

**检查状态**：
```bash
# 查看完整环境状态
docker-compose -f docker-compose.prod.yml ps

# 检查Flask应用
curl http://localhost/health
```

### 停止服务

```bash
# 停止所有服务
./scripts/docker/stop-prod.sh

# 停止并清理数据卷
./scripts/docker/stop-prod.sh --volumes

# 停止并清理镜像
./scripts/docker/stop-prod.sh --images
```

## 脚本说明

### 基础环境启动脚本

| 脚本 | 环境 | 功能 |
|------|------|------|
| `start-dev-base.sh` | 开发 | 启动PostgreSQL + Redis + Nginx |
| `start-prod-base.sh` | 生产 | 启动PostgreSQL + Redis + Nginx |

### Flask应用启动脚本

| 脚本 | 环境 | 功能 |
|------|------|------|
| `start-dev-flask.sh` | 开发 | 启动Flask应用（无代理构建） |
| `start-prod-flask.sh` | 生产 | 启动Flask应用（代理构建） |

### 停止脚本

| 脚本 | 环境 | 功能 |
|------|------|------|
| `stop-dev.sh` | 开发 | 停止所有开发环境服务 |
| `stop-prod.sh` | 生产 | 停止所有生产环境服务 |

## 环境配置

### 开发环境配置 (env.development)

```bash
# 数据库配置
POSTGRES_DB=whalefall_dev
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=xAfbY3VRSlPmHY8ell3iUYmXZqcCt9iz

# Redis配置
REDIS_PASSWORD=GNYn4gaKc998ZN72AXD_jDWGC5h8krL2

# 应用配置
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
```

### 生产环境配置 (env.production)

```bash
# 代理配置
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1,::1

# 数据库配置
POSTGRES_DB=whalefall_prod
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=xAfbY3VRSlPmHY8ell3iUYmXZqcCt9iz

# Redis配置
REDIS_PASSWORD=GNYn4gaKc998ZN72AXD_jDWGC5h8krL2

# 应用配置
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO
```

## 故障排除

### 基础环境启动失败

1. **检查Docker状态**：
   ```bash
   docker info
   ```

2. **检查端口占用**：
   ```bash
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   lsof -i :80    # Nginx
   ```

3. **查看日志**：
   ```bash
   docker-compose -f docker-compose.dev.yml logs postgres
   docker-compose -f docker-compose.dev.yml logs redis
   docker-compose -f docker-compose.dev.yml logs nginx
   ```

### Flask应用启动失败

1. **检查基础环境**：
   ```bash
   # 确保基础环境已启动
   docker-compose -f docker-compose.dev.yml ps postgres redis nginx
   ```

2. **检查代理配置**（生产环境）：
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```

3. **查看Flask日志**：
   ```bash
   docker-compose -f docker-compose.dev.yml logs whalefall
   ```

### 数据库连接问题

1. **检查数据库状态**：
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U whalefall_user -d whalefall_dev
   ```

2. **检查连接字符串**：
   ```bash
   echo $DATABASE_URL
   ```

3. **测试数据库连接**：
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres psql -U whalefall_user -d whalefall_dev -c "SELECT 1;"
   ```

## 最佳实践

### 开发环境

1. **使用开发模式**：Flask调试模式，热重载
2. **直接访问Flask**：可以通过5001端口直接访问
3. **日志级别**：使用DEBUG级别便于调试
4. **资源限制**：较低的资源限制

### 生产环境

1. **使用生产模式**：Flask生产模式，Supervisor管理
2. **通过Nginx访问**：不直接暴露Flask端口
3. **日志级别**：使用INFO级别
4. **资源限制**：较高的资源限制
5. **代理支持**：支持HTTP/HTTPS代理构建

### 安全建议

1. **密码管理**：使用强密码，定期更换
2. **网络隔离**：生产环境不暴露内部端口
3. **数据备份**：定期备份数据库和用户数据
4. **监控告警**：设置服务监控和告警

## 总结

分步部署的优势：
- **灵活性**：可以独立启动和停止各个组件
- **调试便利**：可以单独调试基础环境或Flask应用
- **资源优化**：根据需要启动相应服务
- **故障隔离**：问题定位更精确
- **环境隔离**：开发和生产环境完全分离
