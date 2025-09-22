# 鲸落 - 脚本工具目录

本目录包含鲸落项目的各种脚本工具，按功能分类组织。

## 📁 目录结构

```
scripts/
├── deployment/          # 部署相关脚本
├── ssl/                # SSL证书管理脚本
├── local/              # 本地开发脚本
├── quality/            # 代码质量检查脚本
├── database/           # 数据库管理脚本
└── README.md           # 本说明文档
```

## 🚀 部署脚本 (deployment/)

### 核心部署脚本
- `deploy-base.sh` - 基础环境部署脚本（PostgreSQL、Redis、Nginx）
- `deploy-flask.sh` - Flask应用部署脚本
- `start-all.sh` - 启动所有服务
- `stop-all.sh` - 停止所有服务
- `update-version.sh` - 版本更新和回滚脚本
- `test-deployment.sh` - 部署方案测试脚本

### 使用方法
```bash
# 部署基础环境
./scripts/deployment/deploy-base.sh

# 部署Flask应用
./scripts/deployment/deploy-flask.sh

# 启动所有服务
./scripts/deployment/start-all.sh

# 停止所有服务
./scripts/deployment/stop-all.sh

# 更新版本
./scripts/deployment/update-version.sh 4.1.0

# 测试部署
./scripts/deployment/test-deployment.sh
```

## 🔐 SSL证书管理脚本 (ssl/)

### SSL证书脚本
- `generate-ssl-cert.sh` - 生成自签名SSL证书
- `ssl-manager.sh` - SSL证书管理工具
- `ssl-backup.sh` - SSL证书备份和恢复
- `update-external-ssl.sh` - 更新外部SSL证书
- `verify-ssl-cert.sh` - 验证SSL证书

### 使用方法
```bash
# 生成SSL证书
./scripts/ssl/generate-ssl-cert.sh

# 管理SSL证书
./scripts/ssl/ssl-manager.sh help

# 备份SSL证书
./scripts/ssl/ssl-backup.sh backup

# 更新外部证书
./scripts/ssl/update-external-ssl.sh -c cert.pem -k key.pem

# 验证SSL证书
./scripts/ssl/verify-ssl-cert.sh -c cert.pem -k key.pem
```

## 🏠 本地开发脚本 (local/)

### 本地开发脚本
- `start-local-nginx.sh` - 启动本地Nginx代理
- `test-local-nginx.sh` - 测试本地Nginx功能

### 使用方法
```bash
# 启动本地Nginx
./scripts/local/start-local-nginx.sh

# 测试本地Nginx
./scripts/local/test-local-nginx.sh
```

## 📊 代码质量检查脚本 (quality/)

### 质量检查脚本
- `quality_check.py` - 完整代码质量检查
- `quick_check.py` - 快速代码质量检查

### 使用方法
```bash
# 完整质量检查
uv run python scripts/quality/quality_check.py

# 快速质量检查
uv run python scripts/quality/quick_check.py

# 或使用Makefile
make quality
make quality-full
```

## 🗄️ 数据库管理脚本 (database/)

### 数据库脚本
- `export_permission_configs.py` - 导出权限配置数据
- `reset_admin_password.py` - 重置管理员密码
- `show_admin_password.py` - 显示管理员密码
- `init_database.sh` - 完整数据库初始化脚本（使用Docker）
- `quick_init.sh` - 快速数据库初始化脚本（使用Docker）

### 使用方法
```bash
# 导出权限配置
uv run python scripts/database/export_permission_configs.py

# 重置管理员密码
uv run python scripts/database/reset_admin_password.py

# 显示管理员密码
uv run python scripts/database/show_admin_password.py

# 快速初始化数据库（推荐）
DB_PASSWORD=your_password ./scripts/database/quick_init.sh

# 完整初始化数据库
DB_PASSWORD=your_password ./scripts/database/init_database.sh

# 使用Docker直接导入
docker exec -i whalefall_postgres_dev psql -U whalefall_user -d whalefall_dev < sql/init_postgresql.sql
```

## 🛠️ 快速使用指南

### 1. 生产环境部署
```bash
# 一键部署所有服务
make all

# 分步部署
make base    # 部署基础环境
make flask   # 部署Flask应用
```

### 2. 服务管理
```bash
# 启动服务
make start

# 停止服务
make stop

# 查看状态
make status

# 查看日志
make logs
```

### 3. 版本更新
```bash
# 更新版本
make update

# 回滚版本
make rollback

# 备份数据
make backup
```

### 4. 代码质量
```bash
# 快速检查
make quality

# 完整检查
make quality-full

# 自动修复
make fix-code
```

## 📋 脚本分类说明

### 部署脚本 (deployment/)
- 用于生产环境部署和管理
- 包含基础环境和Flask应用的部署
- 支持版本更新和回滚

### SSL证书管理 (ssl/)
- 用于SSL证书的生成、管理和验证
- 支持自签名证书和外部证书
- 提供备份和恢复功能

### 本地开发 (local/)
- 用于本地开发环境
- 包含Nginx代理和测试工具
- 便于开发调试

### 代码质量 (quality/)
- 用于代码质量检查和修复
- 集成多种检查工具
- 支持自动修复

### 数据库管理 (database/)
- 用于数据库相关操作
- 包含权限配置导出
- 提供用户管理功能

## ⚠️ 注意事项

1. **权限设置**: 确保脚本有执行权限
   ```bash
   chmod +x scripts/**/*.sh
   ```

2. **环境要求**: 部分脚本需要特定环境
   - Docker和Docker Compose
   - Python 3.13+
   - uv包管理器

3. **路径依赖**: 脚本需要在项目根目录运行

4. **配置检查**: 运行前确保配置文件正确

## 🔧 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x scripts/**/*.sh
   ```

2. **路径错误**
   ```bash
   # 确保在项目根目录运行
   pwd
   # 应该显示: /path/to/TaifishingV4
   ```

3. **依赖缺失**
   ```bash
   # 安装依赖
   uv sync
   ```

### 获取帮助
```bash
# 查看Makefile帮助
make help

# 查看脚本帮助
./scripts/deployment/deploy-base.sh --help
./scripts/ssl/ssl-manager.sh help
```

---

**维护者**: TaifishingV4 Team  
**最后更新**: 2024-12-19  
**版本**: v1.0.0