# 鲸落 - 数据目录结构说明

## 📁 统一数据存储

所有持久化数据统一存储在 `/opt/whale_fall_data` 目录下，便于管理和备份。

## 🗂️ 目录结构

```
/opt/whale_fall_data/
├── app/                    # 应用数据
│   ├── logs/              # 应用日志
│   ├── exports/           # 导出文件
│   ├── backups/           # 应用备份
│   └── uploads/           # 上传文件
├── postgres/              # PostgreSQL数据库数据
├── redis/                 # Redis缓存数据
├── nginx/                 # Nginx数据
│   ├── logs/              # Nginx访问日志
│   └── ssl/               # SSL证书文件
└── backups/               # 系统备份
```

## 🔧 目录说明

### 应用数据 (`/opt/whale_fall_data/app/`)

- **logs/**: 应用运行日志
  - 结构化日志文件
  - 错误日志
  - 访问日志
  - 定时任务日志

- **exports/**: 导出文件
  - CSV导出文件
  - Excel导出文件
  - 报表文件

- **backups/**: 应用备份
  - 数据库备份
  - 配置文件备份
  - 用户数据备份

- **uploads/**: 上传文件
  - 用户上传的文件
  - 临时文件

### 数据库数据 (`/opt/whale_fall_data/postgres/`)

- PostgreSQL数据库文件
- 事务日志
- 索引文件
- 配置文件

### 缓存数据 (`/opt/whale_fall_data/redis/`)

- Redis数据文件
- AOF日志文件
- 持久化快照

### Nginx数据 (`/opt/whale_fall_data/nginx/`)

- **logs/**: Nginx访问日志
  - 访问日志
  - 错误日志
  - 访问统计

- **ssl/**: SSL证书
  - 证书文件
  - 私钥文件
  - 中间证书

### 系统备份 (`/opt/whale_fall_data/backups/`)

- 数据库备份文件
- 应用数据备份
- 配置文件备份
- 系统状态快照

## 🚀 初始化

### 自动初始化

首次运行 `./scripts/deploy.sh start` 时会自动创建目录结构。

### 手动初始化

```bash
# 初始化数据目录
./scripts/init-data-dirs.sh init

# 检查目录状态
./scripts/init-data-dirs.sh check

# 显示目录结构
./scripts/init-data-dirs.sh structure
```

## 🔐 权限设置

### 目录权限

- **主目录**: `755` (drwxr-xr-x)
- **应用数据**: `755` (drwxr-xr-x)
- **PostgreSQL**: `700` (drwx------)
- **Redis**: `755` (drwxr-xr-x)
- **Nginx**: `755` (drwxr-xr-x)

### 用户权限

- **应用数据**: `1000:1000` (whalefall用户)
- **PostgreSQL**: `999:999` (postgres用户)
- **Redis**: `999:999` (redis用户)
- **Nginx**: `101:101` (nginx用户)

## 💾 备份策略

### 自动备份

```bash
# 执行备份
./scripts/deploy.sh backup
```

备份文件存储在 `/opt/whale_fall_data/backups/` 目录。

### 手动备份

```bash
# 备份数据库
docker compose exec postgres pg_dump -U whalefall_user whalefall_prod > /opt/whale_fall_data/backups/database_$(date +%Y%m%d_%H%M%S).sql

# 备份应用数据
tar -czf /opt/whale_fall_data/backups/app_$(date +%Y%m%d_%H%M%S).tar.gz /opt/whale_fall_data/app/

# 备份整个数据目录
tar -czf /opt/whale_fall_data/backups/full_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/whale_fall_data/
```

## 🔄 迁移指南

### 从旧版本迁移

1. **停止服务**
   ```bash
   ./scripts/deploy.sh stop
   ```

2. **备份现有数据**
   ```bash
   # 备份Docker volumes
   docker run --rm -v whalefall_data:/data -v $(pwd):/backup alpine tar czf /backup/whalefall_data_backup.tar.gz -C /data .
   ```

3. **创建新目录结构**
   ```bash
   ./scripts/init-data-dirs.sh init
   ```

4. **迁移数据**
   ```bash
   # 解压备份数据到新目录
   tar xzf whalefall_data_backup.tar.gz -C /opt/whale_fall_data/app/
   ```

5. **启动服务**
   ```bash
   ./scripts/deploy.sh start
   ```

## 📊 监控和维护

### 磁盘使用情况

```bash
# 查看数据目录大小
du -sh /opt/whale_fall_data/*

# 查看详细使用情况
du -h /opt/whale_fall_data/
```

### 清理日志

```bash
# 清理应用日志（保留最近7天）
find /opt/whale_fall_data/app/logs -name "*.log" -mtime +7 -delete

# 清理Nginx日志（保留最近30天）
find /opt/whale_fall_data/nginx/logs -name "*.log" -mtime +30 -delete
```

### 健康检查

```bash
# 检查目录权限
ls -la /opt/whale_fall_data/

# 检查磁盘空间
df -h /opt/whale_fall_data/

# 检查服务状态
./scripts/deploy.sh status
```

## ⚠️ 注意事项

1. **备份重要**: 定期备份 `/opt/whale_fall_data` 目录
2. **权限正确**: 确保目录权限设置正确
3. **磁盘空间**: 监控磁盘使用情况，避免空间不足
4. **安全考虑**: 确保数据目录只有授权用户可访问
5. **迁移测试**: 在生产环境迁移前，先在测试环境验证

## 🔗 相关文档

- [生产环境部署指南](PRODUCTION_DEPLOYMENT.md)
- [生产环境启动指南](PRODUCTION_STARTUP_GUIDE.md)
- [备份和恢复指南](BACKUP_RECOVERY.md)
