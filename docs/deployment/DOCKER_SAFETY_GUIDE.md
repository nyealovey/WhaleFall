# Docker安全使用指南

## 概述

本指南说明如何安全地使用Docker脚本，避免意外删除重要数据。

## ⚠️ 重要警告

### 数据安全原则
1. **永远不要随意删除数据卷** - 这会导致数据库数据永久丢失
2. **谨慎删除镜像** - 删除后需要重新构建，耗时较长
3. **备份重要数据** - 在清理前确保有备份

## 脚本分类

### 1. 安全脚本（推荐使用）

#### 启动脚本
```bash
# 本地开发环境
./scripts/docker/start-dev-base.sh      # 启动基础环境
./scripts/docker/start-dev-flask.sh     # 启动Flask应用

# 服务器正式环境
./scripts/docker/start-prod-base.sh     # 启动基础环境
./scripts/docker/start-prod-flask.sh    # 启动Flask应用
```

**特点**：
- ✅ 只启动服务，不删除任何数据
- ✅ 自动检查依赖和配置
- ✅ 等待服务就绪

#### 停止脚本
```bash
# 本地开发环境
./scripts/docker/stop-dev.sh            # 停止所有服务（安全）

# 服务器正式环境
./scripts/docker/stop-prod.sh           # 停止所有服务（安全）
```

**特点**：
- ✅ 只停止服务，不删除容器
- ✅ 保留所有数据和配置
- ✅ 可以随时重新启动

### 2. 清理脚本（谨慎使用）

#### 开发环境清理
```bash
./scripts/docker/cleanup-dev.sh -c      # 清理未使用的容器（安全）
./scripts/docker/cleanup-dev.sh -i      # 清理未使用的镜像（安全）
./scripts/docker/cleanup-dev.sh -v      # 清理未使用的数据卷（危险）
./scripts/docker/cleanup-dev.sh -f      # 清理Flask应用镜像（需要确认）
./scripts/docker/cleanup-dev.sh -a      # 清理所有数据（非常危险）
```

#### 生产环境清理
```bash
./scripts/docker/cleanup-prod.sh -c     # 清理未使用的容器（安全）
./scripts/docker/cleanup-prod.sh -i     # 清理未使用的镜像（安全）
./scripts/docker/cleanup-prod.sh -v     # 清理未使用的数据卷（危险）
./scripts/docker/cleanup-prod.sh -f     # 清理Flask应用镜像（需要确认）
./scripts/docker/cleanup-prod.sh -a     # 清理所有数据（非常危险）
```

## 安全使用建议

### 日常使用（推荐）

```bash
# 启动开发环境
./scripts/docker/start-dev-base.sh
./scripts/docker/start-dev-flask.sh

# 停止开发环境
./scripts/docker/stop-dev.sh

# 重启开发环境
./scripts/docker/stop-dev.sh
./scripts/docker/start-dev-base.sh
./scripts/docker/start-dev-flask.sh
```

### 定期维护（谨慎）

```bash
# 清理未使用的容器和镜像（安全）
./scripts/docker/cleanup-dev.sh -c
./scripts/docker/cleanup-dev.sh -i

# 清理未使用的数据卷（需要确认）
./scripts/docker/cleanup-dev.sh -v
```

### 完全重置（危险）

```bash
# 完全清理所有数据（非常危险）
./scripts/docker/cleanup-dev.sh -a
```

## 数据备份

### 备份数据库
```bash
# 备份PostgreSQL数据
docker-compose -f docker-compose.dev.yml exec postgres pg_dump -U whalefall_user whalefall_dev > backup.sql

# 备份Redis数据
docker-compose -f docker-compose.dev.yml exec redis redis-cli --rdb /data/dump.rdb
```

### 备份用户数据
```bash
# 备份用户数据目录
tar -czf userdata_backup_$(date +%Y%m%d_%H%M%S).tar.gz userdata/
```

## 故障恢复

### 容器无法启动
```bash
# 查看容器状态
docker-compose -f docker-compose.dev.yml ps

# 查看容器日志
docker-compose -f docker-compose.dev.yml logs whalefall

# 重启特定服务
docker-compose -f docker-compose.dev.yml restart whalefall
```

### 数据损坏
```bash
# 停止所有服务
./scripts/docker/stop-dev.sh

# 从备份恢复数据
# 1. 恢复数据库
docker-compose -f docker-compose.dev.yml exec postgres psql -U whalefall_user -d whalefall_dev < backup.sql

# 2. 恢复用户数据
tar -xzf userdata_backup_20241201_120000.tar.gz

# 重新启动服务
./scripts/docker/start-dev-base.sh
./scripts/docker/start-dev-flask.sh
```

## 最佳实践

### 1. 开发环境
- 使用 `stop-dev.sh` 停止服务，不要使用清理选项
- 定期备份重要数据
- 使用版本控制管理代码变更

### 2. 生产环境
- 永远不要在生产环境使用清理脚本
- 定期备份数据库和用户数据
- 使用监控工具监控服务状态

### 3. 测试环境
- 可以使用清理脚本重置环境
- 确保测试数据可以重新生成
- 定期清理避免磁盘空间不足

## 常见错误

### ❌ 错误做法
```bash
# 不要这样做 - 会删除所有数据
./scripts/docker/cleanup-dev.sh -a

# 不要这样做 - 会删除数据库数据
./scripts/docker/cleanup-dev.sh -v

# 不要这样做 - 会删除应用镜像
./scripts/docker/cleanup-dev.sh -f
```

### ✅ 正确做法
```bash
# 正确的停止方式
./scripts/docker/stop-dev.sh

# 正确的重启方式
./scripts/docker/stop-dev.sh
./scripts/docker/start-dev-base.sh
./scripts/docker/start-dev-flask.sh

# 正确的清理方式（仅清理未使用的资源）
./scripts/docker/cleanup-dev.sh -c
./scripts/docker/cleanup-dev.sh -i
```

## 总结

- **启动和停止脚本是安全的**，可以放心使用
- **清理脚本是危险的**，需要谨慎使用
- **始终备份重要数据**，特别是在清理前
- **在生产环境中避免使用清理脚本**
- **遇到问题时先查看日志**，不要急于清理
