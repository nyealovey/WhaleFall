# 开发环境设置指南

## 概述

开发环境采用分离式启动模式：
- **数据库服务**：PostgreSQL + Redis（Docker容器）
- **Flask应用**：手动启动（本地Python环境）

## 快速开始

### 1. 启动数据库服务

```bash
# 方式1：使用Makefile
make start-db

# 方式2：直接运行脚本
./scripts/dev/start-dev-db.sh
```

### 2. 启动Flask应用

```bash
# 方式1：使用Makefile
make start-flask

# 方式2：直接运行脚本
./scripts/dev/start-flask.sh
```

### 3. 访问应用

- **Flask应用**：http://localhost:5001
- **PostgreSQL**：localhost:5432
- **Redis**：localhost:6379

## 环境配置

### 数据库配置

- **PostgreSQL**：
  - 数据库名：`whalefall_dev`
  - 用户名：`whalefall_user`
  - 密码：`Dev2024!`
  - 端口：`5432`

- **Redis**：
  - 密码：`RedisDev2024!`
  - 端口：`6379`

### 环境变量

开发环境使用 `env.development` 文件，包含：
- 数据库连接配置
- Redis连接配置
- Flask应用配置
- 安全密钥配置

## 开发流程

### 日常开发

1. **启动数据库服务**：
   ```bash
   make start-db
   ```

2. **启动Flask应用**（新终端）：
   ```bash
   make start-flask
   ```

3. **开发调试**：
   - 修改代码后，Flask应用会自动重载
   - 可以随时按 `Ctrl+C` 停止应用
   - 重新运行 `make start-flask` 启动应用

### 停止服务

1. **停止Flask应用**：按 `Ctrl+C`
2. **停止数据库服务**：
   ```bash
   make stop
   ```

## 故障排除

### 常见问题

1. **数据库连接失败**：
   - 确保数据库服务已启动：`make start-db`
   - 检查端口是否被占用：`lsof -i :5432`

2. **Flask应用启动失败**：
   - 检查Python依赖：`uv sync`
   - 检查环境变量：`cat .env`

3. **调度器初始化问题**：
   - 已修复调度器启动时序问题
   - 如果仍有问题，检查数据库连接

### 调试命令

```bash
# 查看数据库服务状态
docker compose -f docker-compose.dev.yml ps

# 查看数据库日志
docker compose -f docker-compose.dev.yml logs postgres

# 查看Redis日志
docker compose -f docker-compose.dev.yml logs redis

# 进入PostgreSQL容器
docker compose -f docker-compose.dev.yml exec postgres psql -U whalefall_user -d whalefall_dev

# 进入Redis容器
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

## 优势

- **开发灵活性**：Flask应用可以随时重启，无需重建容器
- **调试方便**：可以直接在IDE中调试Flask应用
- **资源节省**：不需要Nginx容器，减少资源占用
- **分离关注点**：数据库用容器，应用用本地环境
- **快速迭代**：代码修改后立即生效

## 注意事项

- Flask应用需要手动启动，不会自动启动
- 确保在项目根目录下运行命令
- 开发环境使用短密码，避免PostgreSQL连接问题
- 数据库服务需要先启动，Flask应用才能正常连接
