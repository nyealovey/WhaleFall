# Docker 持久化卷管理

## 📋 概述

鲸落项目现在使用Docker命名卷进行数据持久化，确保数据在容器重启、更新或迁移后不会丢失。这种方式比绑定挂载更加可靠和高效。

## 🏗️ 卷结构

### 开发环境卷
- `whalefall_postgres_data` - PostgreSQL数据库数据
- `whalefall_redis_data` - Redis缓存数据
- `whalefall_nginx_logs` - Nginx访问日志
- `whalefall_nginx_ssl` - Nginx SSL证书
- `whalefall_app_data` - 应用用户数据

### 生产环境卷
- `whalefall_postgres_data` - PostgreSQL数据库数据
- `whalefall_redis_data` - Redis缓存数据
- `whalefall_nginx_logs` - Nginx访问日志
- `whalefall_nginx_ssl` - Nginx SSL证书
- `whalefall_app_data` - 应用用户数据

## 🚀 快速开始

### 1. 创建卷
```bash
# 开发环境
make dev create-volumes

# 生产环境
make prod create-volumes
```

### 2. 迁移现有数据
```bash
# 从userdata目录迁移到卷
make dev migrate-volumes
make prod migrate-volumes
```

### 3. 启动服务
```bash
# 开发环境
make dev start

# 生产环境
make prod start
```

## 📦 卷管理命令

### 基本命令
```bash
# 列出所有卷
make dev volumes
make prod volumes

# 查看卷大小
make dev volume-size
make prod volume-size

# 备份卷
make dev backup-volumes
make prod backup-volumes

# 恢复卷
make dev restore-volumes
make prod restore-volumes
```

### 高级命令
```bash
# 直接使用卷管理脚本
./scripts/docker/volume_manager.sh list
./scripts/docker/volume_manager.sh create dev
./scripts/docker/volume_manager.sh backup prod --backup-dir /opt/backups
./scripts/docker/volume_manager.sh migrate dev --force
```

## 🔧 卷管理脚本

### 脚本位置
`scripts/docker/volume_manager.sh`

### 功能特性
- ✅ 卷的创建、备份、恢复
- ✅ 从userdata目录迁移数据
- ✅ 卷大小查看和清理
- ✅ 支持开发和生产环境
- ✅ 强制操作确认
- ✅ 彩色日志输出

### 使用示例
```bash
# 查看帮助
./scripts/docker/volume_manager.sh --help

# 列出所有卷
./scripts/docker/volume_manager.sh list

# 创建开发环境卷
./scripts/docker/volume_manager.sh create dev

# 备份生产环境卷
./scripts/docker/volume_manager.sh backup prod --backup-dir /opt/backups

# 恢复开发环境卷
./scripts/docker/volume_manager.sh restore dev

# 迁移数据到卷
./scripts/docker/volume_manager.sh migrate dev --force

# 查看卷详情
./scripts/docker/volume_manager.sh inspect whalefall_postgres_data

# 查看卷大小
./scripts/docker/volume_manager.sh size prod
```

## 📊 数据迁移

### 从userdata目录迁移
如果你之前使用绑定挂载（`./userdata`），可以轻松迁移到命名卷：

```bash
# 1. 停止服务
make dev stop
make prod stop

# 2. 创建卷
make dev create-volumes
make prod create-volumes

# 3. 迁移数据
make dev migrate-volumes
make prod migrate-volumes

# 4. 启动服务
make dev start
make prod start
```

### 迁移验证
```bash
# 检查数据是否正确迁移
make dev volume-size
make prod volume-size

# 检查服务状态
make dev status
make prod status
```

## 💾 备份和恢复

### 备份策略
```bash
# 开发环境备份
make dev backup-volumes

# 生产环境备份（指定备份目录）
BACKUP_DIR=/opt/whale_fall_backups make prod backup-volumes
```

### 恢复策略
```bash
# 恢复开发环境
make dev restore-volumes

# 恢复生产环境
BACKUP_DIR=/opt/whale_fall_backups make prod restore-volumes
```

### 备份文件格式
- 文件名: `{volume_name}_{timestamp}.tar`
- 格式: tar.gz压缩
- 位置: `./backups/` 或指定目录

## 🧹 清理和维护

### 清理卷
```bash
# 清理开发环境卷（需要确认）
make dev clean-data

# 清理生产环境卷（需要确认）
make prod clean-data
```

### 卷维护
```bash
# 查看卷使用情况
docker system df -v

# 清理未使用的卷
docker volume prune

# 查看特定卷详情
docker volume inspect whalefall_postgres_data
```

## 🔍 故障排除

### 常见问题

1. **卷不存在**
   ```bash
   # 创建缺失的卷
   make dev create-volumes
   ```

2. **权限问题**
   ```bash
   # 检查卷权限
   docker volume inspect whalefall_postgres_data
   ```

3. **数据迁移失败**
   ```bash
   # 强制迁移
   ./scripts/docker/volume_manager.sh migrate dev --force
   ```

4. **备份恢复失败**
   ```bash
   # 检查备份文件
   ls -la ./backups/
   ```

### 调试命令
```bash
# 查看所有卷
docker volume ls

# 查看卷内容
docker run --rm -v whalefall_postgres_data:/data alpine ls -la /data

# 查看卷大小
docker run --rm -v whalefall_postgres_data:/data alpine du -sh /data
```

## 📈 性能优化

### 卷性能
- 命名卷比绑定挂载性能更好
- 支持Docker的卷驱动优化
- 更好的跨平台兼容性

### 存储优化
```bash
# 查看卷使用情况
docker system df

# 清理未使用的卷
docker volume prune

# 压缩卷数据
docker run --rm -v whalefall_postgres_data:/data alpine sh -c "cd /data && tar czf /tmp/backup.tar.gz . && rm -rf * && tar xzf /tmp/backup.tar.gz"
```

## 🔒 安全考虑

### 数据安全
- 卷数据存储在Docker管理的目录中
- 支持卷加密（需要Docker企业版）
- 定期备份重要数据

### 访问控制
```bash
# 限制卷访问权限
docker run --rm -v whalefall_postgres_data:/data:ro alpine ls /data

# 只读挂载
docker run --rm -v whalefall_postgres_data:/data:ro alpine cat /data/postgresql.conf
```

## 📚 相关文档

- [Docker Compose配置](DOCKER_COMPOSE_CONFIGURATION.md)
- [Makefile使用指南](MAKEFILE_USAGE.md)
- [备份和恢复策略](BACKUP_RECOVERY.md)
- [部署指南](DEPLOYMENT_GUIDE.md)

## 🎯 最佳实践

1. **定期备份**: 设置定时任务备份重要卷
2. **监控使用**: 定期检查卷使用情况
3. **测试恢复**: 定期测试备份恢复流程
4. **版本控制**: 记录卷的创建和修改时间
5. **文档更新**: 保持卷管理文档的更新

## ⚠️ 注意事项

1. **数据迁移**: 迁移前请确保数据已备份
2. **权限问题**: 确保Docker有足够的权限管理卷
3. **存储空间**: 监控磁盘空间使用情况
4. **备份策略**: 制定合适的备份和恢复策略
5. **测试环境**: 在生产环境操作前先在测试环境验证
