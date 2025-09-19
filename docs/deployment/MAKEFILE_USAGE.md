# Makefile 使用指南

## 📋 概述

鲸落项目现在使用分离的 Makefile 来管理不同环境的命令，提供了更清晰的环境隔离和更灵活的管理方式。

## 🏗️ 文件结构

```
├── Makefile          # 主 Makefile（环境选择器）
├── Makefile.dev      # 开发环境 Makefile
└── Makefile.prod     # 生产环境 Makefile
```

## 🚀 快速开始

### 查看所有可用命令
```bash
make help
```

### 开发环境
```bash
# 查看开发环境命令
make dev help

# 启动开发环境
make dev start

# 停止开发环境
make dev stop

# 查看开发环境日志
make dev logs
```

### 生产环境
```bash
# 查看生产环境命令
make prod help

# 部署生产环境
make prod deploy

# 启动生产环境
make prod start

# 停止生产环境
make prod stop
```

## 🔧 开发环境命令

### 环境管理
```bash
make dev start        # 启动开发环境
make dev stop         # 停止开发环境
make dev restart      # 重启开发环境
make dev status       # 查看服务状态
```

### 数据库管理
```bash
# 初始化数据库
DB_PASSWORD=your_password make dev init-db

# 快速初始化数据库
DB_PASSWORD=your_password make dev init-db-quick
```

### 日志查看
```bash
make dev logs         # 查看所有日志
make dev logs-db      # 查看数据库日志
make dev logs-redis   # 查看Redis日志
make dev logs-app     # 查看应用日志
```

### 开发工具
```bash
make dev shell        # 进入应用容器
make dev health       # 健康检查
make dev test         # 运行测试
make dev quality      # 代码质量检查
make dev format       # 格式化代码
```

### 维护命令
```bash
make dev clean        # 清理Docker资源
make dev clean-data   # 清理数据卷
make dev build        # 构建开发镜像
```

## 🏭 生产环境命令

### 安装和配置
```bash
make prod install     # 安装系统依赖
make prod config      # 配置环境文件
```

### 部署和管理
```bash
make prod deploy      # 部署生产环境
make prod start       # 启动生产环境
make prod stop        # 停止生产环境
make prod restart     # 重启生产环境
make prod status      # 查看服务状态
```

### 数据库管理
```bash
# 初始化数据库
DB_PASSWORD=your_password make prod init-db

# 快速初始化数据库
DB_PASSWORD=your_password make prod init-db-quick
```

### 日志和监控
```bash
make prod logs        # 查看所有日志
make prod logs-db     # 查看数据库日志
make prod logs-redis  # 查看Redis日志
make prod logs-app    # 查看应用日志
make prod health      # 健康检查
```

### 备份和恢复
```bash
make prod backup      # 备份数据
make prod restore FILE=backup_file.sql  # 恢复数据
```

### 版本管理
```bash
make prod update      # 更新到最新版本
make prod rollback    # 回滚到上一个版本
```

### 维护命令
```bash
make prod clean       # 清理Docker资源
make prod build       # 构建生产镜像
make prod shell       # 进入应用容器
make prod version     # 查看版本信息
```

## ⚡ 快速命令

为了简化常用操作，主 Makefile 提供了一些快速命令：

### 快速启动
```bash
make dev-start        # 快速启动开发环境
make prod-start       # 快速启动生产环境
```

### 快速停止
```bash
make dev-stop         # 快速停止开发环境
make prod-stop        # 快速停止生产环境
```

### 快速状态查看
```bash
make dev-status       # 快速查看开发环境状态
make prod-status      # 快速查看生产环境状态
```

### 快速日志查看
```bash
make dev-logs         # 快速查看开发环境日志
make prod-logs        # 快速查看生产环境日志
```

## 🔧 通用命令

### 项目依赖
```bash
make install          # 安装项目依赖
```

### 代码质量
```bash
make quality          # 代码质量检查
make format           # 格式化代码
make test             # 运行测试
```

### 维护
```bash
make clean            # 清理Docker资源
make health           # 健康检查
make version          # 查看版本信息
```

## 📝 环境变量

### 开发环境
- `DB_PASSWORD`: 数据库密码（必需）

### 生产环境
- `DB_PASSWORD`: 数据库密码（必需）
- `POSTGRES_USER`: PostgreSQL用户名
- `POSTGRES_DB`: PostgreSQL数据库名

## 🚨 注意事项

1. **环境隔离**: 开发环境和生产环境使用不同的 Docker Compose 文件
2. **密码安全**: 生产环境请使用强密码
3. **备份重要**: 生产环境操作前请先备份数据
4. **权限检查**: 确保有足够的 Docker 权限

## 🔍 故障排除

### 常见问题

1. **权限不足**
   ```bash
   sudo usermod -aG docker $USER
   # 重新登录
   ```

2. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :5001
   ```

3. **Docker 服务未启动**
   ```bash
   sudo systemctl start docker
   ```

4. **环境变量未设置**
   ```bash
   # 检查环境变量
   echo $DB_PASSWORD
   ```

## 📚 相关文档

- [Docker 部署指南](DOCKER_DEPLOYMENT.md)
- [环境配置指南](ENVIRONMENT_CONFIGURATION.md)
- [数据库管理指南](DATABASE_MANAGEMENT.md)
