# PostgreSQL 数据库迁移指南

## 概述

本指南将帮助您将泰摸鱼吧应用从SQLite迁移到PostgreSQL，并设置Redis缓存。

## 前置要求

- Docker 和 Docker Compose
- Python 3.13+
- 虚拟环境已激活

## 快速开始

### 1. 一键设置（推荐）

```bash
# 运行完整设置脚本
./scripts/setup_postgresql_complete.sh
```

这个脚本会自动：
- 设置环境配置
- 启动PostgreSQL和Redis容器
- 创建数据库表结构
- 迁移SQLite数据
- 验证迁移结果

### 2. 手动设置

如果您想分步执行，可以按照以下步骤：

#### 步骤1：设置环境配置
```bash
python scripts/setup_postgresql_env.py
```

#### 步骤2：启动容器
```bash
docker-compose -f docker-compose.dev.yml up -d
```

#### 步骤3：等待容器启动
```bash
# 检查容器状态
docker-compose -f docker-compose.dev.yml ps

# 检查PostgreSQL连接
docker exec taifish_postgres_dev pg_isready -U taifish_user -d taifish_dev

# 检查Redis连接
docker exec taifish_redis_dev redis-cli -a Taifish2024! ping
```

#### 步骤4：创建表结构
```bash
source .venv/bin/activate
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('表结构创建完成')
"
```

#### 步骤5：迁移数据
```bash
python scripts/accurate_migrate.py
```

#### 步骤6：验证迁移
```bash
python scripts/test_postgresql_connection.py
```

## 配置说明

### PostgreSQL配置
- **主机**: localhost
- **端口**: 5432
- **数据库**: taifish_dev
- **用户**: taifish_user
- **密码**: Taifish2024!

### Redis配置
- **主机**: localhost
- **端口**: 6379
- **密码**: Taifish2024!

### 环境变量
应用会自动使用以下环境变量：
```bash
DATABASE_URL=postgresql://taifish_user:Taifish2024!@localhost:5432/taifish_dev
REDIS_URL=redis://:Taifish2024!@localhost:6379/0
```

## 迁移的表

脚本会迁移以下表的数据：
- `users` - 用户表
- `instances` - 数据库实例表
- `credentials` - 凭据表
- `unified_logs` - 统一日志表
- `account_classifications` - 账户分类表
- `classification_rules` - 分类规则表
- `account_classification_assignments` - 分类分配表
- `classification_batches` - 分类批次表
- `permission_configs` - 权限配置表
- `database_type_configs` - 数据库类型配置表
- `sync_instance_records` - 同步实例记录表
- `sync_sessions` - 同步会话表
- `tasks` - 任务表
- `global_params` - 全局参数表
- `account_change_log` - 账户变更日志表
- `current_account_sync_data` - 当前账户同步数据表

## 故障排除

### 1. 容器启动失败
```bash
# 查看容器日志
docker-compose -f docker-compose.dev.yml logs

# 重启容器
docker-compose -f docker-compose.dev.yml restart
```

### 2. 数据库连接失败
```bash
# 检查PostgreSQL是否运行
docker exec taifish_postgres_dev pg_isready -U taifish_user -d taifish_dev

# 检查端口是否被占用
lsof -i :5432
```

### 3. 数据迁移失败
```bash
# 查看详细错误信息
python scripts/accurate_migrate.py

# 检查表结构
sqlite3 userdata/taifish_dev.db ".schema"
```

### 4. 应用启动失败
```bash
# 测试数据库连接
python scripts/test_postgresql_connection.py

# 检查环境变量
echo $DATABASE_URL
echo $REDIS_URL
```

## 清理

如果需要清理PostgreSQL数据：

```bash
# 停止容器
docker-compose -f docker-compose.dev.yml down

# 删除数据卷
docker volume rm taifish_postgres_dev_data taifish_redis_dev_data

# 重新开始
./scripts/setup_postgresql_complete.sh
```

## 性能优化

### PostgreSQL优化
- 已配置连接池（最大100个连接）
- 已启用查询日志（超过1秒的查询）
- 已创建性能索引

### Redis优化
- 已配置内存限制（128MB）
- 已启用LRU淘汰策略
- 已启用AOF持久化

## 监控

### 查看容器状态
```bash
docker-compose -f docker-compose.dev.yml ps
```

### 查看容器日志
```bash
# PostgreSQL日志
docker logs taifish_postgres_dev

# Redis日志
docker logs taifish_redis_dev
```

### 查看数据库统计
```bash
# 连接PostgreSQL
docker exec -it taifish_postgres_dev psql -U taifish_user -d taifish_dev

# 查看数据库大小
SELECT pg_size_pretty(pg_database_size(current_database()));

# 查看表大小
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size 
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 备份

### 备份PostgreSQL数据
```bash
# 创建备份
docker exec taifish_postgres_dev pg_dump -U taifish_user taifish_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
docker exec -i taifish_postgres_dev psql -U taifish_user taifish_dev < backup_file.sql
```

### 备份Redis数据
```bash
# Redis数据会自动持久化到Docker卷中
# 卷位置: /var/lib/docker/volumes/taifish_redis_dev_data/_data
```

## 下一步

迁移完成后，您可以：

1. 启动应用：`python app.py`
2. 访问应用：`http://localhost:5000`
3. 验证功能是否正常
4. 配置生产环境（如需要）

## 支持

如果遇到问题，请检查：
1. Docker是否正常运行
2. 端口5432和6379是否被占用
3. 虚拟环境是否已激活
4. 所有依赖是否已安装
