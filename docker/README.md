# 鲸落 - Docker环境配置

## 📁 目录结构

```
docker/
├── README.md                    # Docker配置说明
├── Dockerfile                   # ARM64版本Dockerfile
├── Dockerfile.x86_64           # x86_64版本Dockerfile
├── .dockerignore               # Docker忽略文件
├── compose/                    # Docker Compose配置
│   ├── docker-compose.yml      # ARM64版本
│   └── docker-compose.x86_64.yml # x86_64版本
├── configs/                    # 配置文件
│   ├── nginx.conf              # Nginx配置
│   └── env.example             # 环境变量示例
└── scripts/                    # Docker相关脚本
    ├── start_macos.sh          # macOS启动脚本
    ├── start_x86_64.sh         # x86_64启动脚本
    └── install_oracle_client.sh # Oracle客户端安装
```

## 🚀 快速开始

### ARM64架构 (Apple Silicon Mac)

```bash
# 使用ARM64版本
docker-compose -f docker/compose/docker-compose.yml up -d
```

### x86_64架构 (Intel Mac / Linux)

```bash
# 使用x86_64版本
docker-compose -f docker/compose/docker-compose.x86_64.yml up -d
```

### macOS专用启动脚本

```bash
# ARM64版本
./docker/scripts/start_macos.sh

# x86_64版本
arch -x86_64 zsh -c "./docker/scripts/start_x86_64.sh"
```

## 🐳 Docker镜像说明

### ARM64版本 (Dockerfile)
- 基础镜像: `python:3.9-slim`
- 架构: `linux/arm64`
- 特点: 原生ARM64性能，部分数据库驱动可能不可用

### x86_64版本 (Dockerfile.x86_64)
- 基础镜像: `python:3.9-slim`
- 架构: `linux/amd64`
- 特点: 完整数据库驱动支持，性能略低于原生ARM64

## ⚙️ 配置说明

### 环境变量
复制 `docker/configs/env.example` 到项目根目录的 `.env` 文件：

```bash
cp docker/configs/env.example .env
# 编辑 .env 文件，配置你的环境变量
```

### Nginx配置
Nginx配置文件位于 `docker/configs/nginx.conf`，包含：
- 反向代理配置
- 静态文件服务
- Gzip压缩
- 健康检查

## 🔧 服务说明

### 核心服务
- **flask**: Flask应用服务
- **postgres**: PostgreSQL数据库
- **redis**: Redis缓存
- **nginx**: 反向代理

### 任务服务
- **celery-worker**: Celery工作进程
- **celery-beat**: Celery定时任务

## 📊 端口映射

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| flask | 8000 | 8000 | Flask应用 |
| postgres | 5432 | 5432 | PostgreSQL数据库 |
| redis | 6379 | 6379 | Redis缓存 |
| nginx | 80 | 80 | Web服务器 |

## 🛠️ 开发命令

### 构建镜像
```bash
# ARM64版本
docker-compose -f docker/compose/docker-compose.yml build

# x86_64版本
docker-compose -f docker/compose/docker-compose.x86_64.yml build
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker/compose/docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f docker/compose/docker-compose.yml logs -f flask
```

### 进入容器
```bash
# 进入Flask容器
docker-compose -f docker/compose/docker-compose.yml exec flask bash

# 进入PostgreSQL容器
docker-compose -f docker/compose/docker-compose.yml exec postgres psql -U taifish_user -d taifish_dev
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f docker/compose/docker-compose.yml restart

# 重启特定服务
docker-compose -f docker/compose/docker-compose.yml restart flask
```

## 🗄️ 数据持久化

### 数据卷
- `postgres_data`: PostgreSQL数据
- `redis_data`: Redis数据
- `userdata`: 用户数据目录

### 数据备份
```bash
# 备份PostgreSQL数据
docker-compose -f docker/compose/docker-compose.yml exec postgres pg_dump -U taifish_user taifish_dev > backup.sql

# 恢复PostgreSQL数据
docker-compose -f docker/compose/docker-compose.yml exec -T postgres psql -U taifish_user taifish_dev < backup.sql
```

## 🔍 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   lsof -i :8000
   lsof -i :5432
   lsof -i :6379
   ```

2. **权限问题**
   ```bash
   # 修复用户数据目录权限
   sudo chown -R $USER:$USER userdata/
   chmod -R 755 userdata/
   ```

3. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose -f docker/compose/docker-compose.yml ps postgres
   docker-compose -f docker/compose/docker-compose.yml logs postgres
   ```

4. **Redis连接失败**
   ```bash
   # 检查Redis状态
   docker-compose -f docker/compose/docker-compose.yml ps redis
   docker-compose -f docker/compose/docker-compose.yml logs redis
   ```

### 清理命令
```bash
# 停止并删除所有容器
docker-compose -f docker/compose/docker-compose.yml down

# 删除所有数据卷（谨慎使用）
docker-compose -f docker/compose/docker-compose.yml down -v

# 清理Docker缓存
docker system prune -f
```

## 📝 注意事项

1. **架构选择**: 建议使用x86_64版本以获得完整的数据库驱动支持
2. **数据安全**: 定期备份数据库和用户数据
3. **资源监控**: 监控容器资源使用情况
4. **日志管理**: 定期清理日志文件
5. **安全更新**: 定期更新基础镜像和依赖包

## 🔗 相关文档

- [项目主文档](../doc/README.md)
- [部署文档](../doc/deployment/README.md)
- [API文档](../doc/api/README.md)
- [数据库驱动指南](../doc/DATABASE_DRIVERS.md)
