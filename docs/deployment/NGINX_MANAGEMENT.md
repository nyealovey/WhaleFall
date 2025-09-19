# Nginx 管理指南

## 📋 概述

鲸落项目现在使用脚本化的方式管理Nginx配置和SSL证书，不再依赖文件挂载。这种方式更加灵活，支持动态配置更新和证书管理。

## 🏗️ 架构设计

### 配置管理方式
- ✅ **脚本化管理**: 通过脚本上传和管理配置文件
- ✅ **动态更新**: 支持配置热重载，无需重启容器
- ✅ **版本控制**: 自动备份配置文件
- ✅ **验证机制**: 配置上传前进行语法检查

### SSL证书管理
- ✅ **证书生成**: 支持自签名证书生成
- ✅ **证书上传**: 支持外部证书上传
- ✅ **证书验证**: 自动验证证书有效性
- ✅ **证书备份**: 自动备份和恢复功能

## 🚀 快速开始

### 1. 启动Nginx服务
```bash
# 开发环境
make dev start

# 生产环境
make prod start
```

### 2. 上传配置文件
```bash
# 开发环境（仅HTTP）
make dev nginx-upload-config

# 生产环境（HTTP+HTTPS）
make prod nginx-upload-config
```

### 3. 生成SSL证书（仅生产环境需要）
```bash
# 生产环境（指定域名）
make prod ssl-generate --domain example.com

# 注意：开发环境不启用HTTPS，无需SSL证书
```

## 📦 Nginx管理命令

### 基本管理
```bash
# 查看Nginx状态
make dev nginx-status
make prod nginx-status

# 重载配置
make dev nginx-reload
make prod nginx-reload

# 重启服务
make dev nginx-restart
make prod nginx-restart

# 查看日志
make dev nginx-logs
make prod nginx-logs

# 查看配置
make dev nginx-config
make prod nginx-config

# 进入容器
make dev nginx-shell
make prod nginx-shell
```

### 配置管理
```bash
# 上传配置文件
make dev nginx-upload-config
make prod nginx-upload-config

# 直接使用脚本
./scripts/nginx/nginx_manager.sh upload-config dev --config-file nginx.conf
./scripts/nginx/nginx_manager.sh upload-config prod --config-file nginx.conf
```

## 🔐 SSL证书管理

### 证书生成
```bash
# 生成自签名证书
make dev ssl-generate
make prod ssl-generate

# 指定域名和有效期
make dev ssl-generate --domain localhost --days 365
make prod ssl-generate --domain example.com --days 730
```

### 证书上传
```bash
# 上传外部证书
make dev ssl-upload --cert-file cert.pem --key-file key.pem
make prod ssl-upload --cert-file cert.pem --key-file key.pem

# 直接使用脚本
./scripts/nginx/ssl_manager.sh upload dev --cert-file cert.pem --key-file key.pem
```

### 证书管理
```bash
# 列出证书
make dev ssl-list
make prod ssl-list

# 验证证书
make dev ssl-verify
make prod ssl-verify

# 备份证书
./scripts/nginx/ssl_manager.sh backup dev
./scripts/nginx/ssl_manager.sh backup prod

# 恢复证书
./scripts/nginx/ssl_manager.sh restore dev
./scripts/nginx/ssl_manager.sh restore prod
```

## 🔧 脚本功能详解

### Nginx管理脚本 (`scripts/nginx/nginx_manager.sh`)

#### 功能特性
- ✅ **状态监控**: 查看Nginx运行状态和配置
- ✅ **配置管理**: 上传、验证、重载配置文件
- ✅ **日志查看**: 实时查看Nginx访问日志
- ✅ **容器管理**: 进入容器进行调试
- ✅ **健康检查**: 验证Nginx配置语法

#### 使用示例
```bash
# 查看帮助
./scripts/nginx/nginx_manager.sh --help

# 查看状态
./scripts/nginx/nginx_manager.sh status dev

# 上传配置
./scripts/nginx/nginx_manager.sh upload-config dev --config-file nginx.conf

# 重载配置
./scripts/nginx/nginx_manager.sh reload dev

# 查看日志
./scripts/nginx/nginx_manager.sh logs dev

# 进入容器
./scripts/nginx/nginx_manager.sh shell dev
```

### SSL证书管理脚本 (`scripts/nginx/ssl_manager.sh`)

#### 功能特性
- ✅ **证书生成**: 生成自签名SSL证书
- ✅ **证书上传**: 上传外部SSL证书
- ✅ **证书验证**: 验证证书有效性和匹配性
- ✅ **证书管理**: 备份、恢复、续期证书
- ✅ **证书信息**: 查看证书详细信息

#### 使用示例
```bash
# 查看帮助
./scripts/nginx/ssl_manager.sh --help

# 生成证书
./scripts/nginx/ssl_manager.sh generate dev --domain localhost --days 365

# 上传证书
./scripts/nginx/ssl_manager.sh upload dev --cert-file cert.pem --key-file key.pem

# 验证证书
./scripts/nginx/ssl_manager.sh verify dev

# 列出证书
./scripts/nginx/ssl_manager.sh list dev

# 备份证书
./scripts/nginx/ssl_manager.sh backup dev --backup-dir ./backups/ssl
```

## 📁 配置文件结构

### 配置文件结构
```
nginx/
├── conf.d/
│   ├── whalefall-dev.conf          # 开发环境配置（仅HTTP）
│   └── whalefall-prod.conf         # 生产环境配置（HTTP+HTTPS）
├── ssl/                            # SSL证书目录
│   ├── cert.pem                    # 证书文件
│   ├── key.pem                     # 私钥文件
│   └── cert.csr                    # 证书签名请求
└── error_pages/                    # 错误页面
    ├── 404.html
    └── 50x.html
```

### 容器内配置路径
```
/etc/nginx/
├── nginx.conf                      # 主配置文件
├── conf.d/
│   └── default.conf                # 站点配置文件
└── ssl/                            # SSL证书目录
    ├── cert.pem
    ├── key.pem
    └── chain.pem
```

## 🔄 配置更新流程

### 1. 准备配置文件
```bash
# 编辑开发环境配置
vim nginx/conf.d/whalefall-dev.conf

# 编辑生产环境配置
vim nginx/conf.d/whalefall-prod.conf
```

### 2. 上传配置
```bash
# 开发环境（自动使用whalefall-dev.conf）
make dev nginx-upload-config

# 生产环境（自动使用whalefall-prod.conf）
make prod nginx-upload-config

# 使用指定配置文件
./scripts/nginx/nginx_manager.sh upload-config dev --config-file nginx/conf.d/my-config.conf
```

### 3. 验证配置
```bash
# 测试配置语法
make dev nginx-status

# 重载配置
make dev nginx-reload
```

## 🔐 SSL证书配置流程

### 1. 生成自签名证书
```bash
# 开发环境
make dev ssl-generate --domain localhost

# 生产环境
make prod ssl-generate --domain example.com --days 730
```

### 2. 上传外部证书
```bash
# 准备证书文件
cp /path/to/cert.pem ./nginx/ssl/
cp /path/to/key.pem ./nginx/ssl/

# 上传证书
make dev ssl-upload --cert-file ./nginx/ssl/cert.pem --key-file ./nginx/ssl/key.pem
```

### 3. 验证证书
```bash
# 验证证书
make dev ssl-verify

# 查看证书信息
make dev ssl-list
```

## 🚨 故障排除

### 常见问题

1. **配置上传失败**
   ```bash
   # 检查配置文件语法
   nginx -t -c nginx/conf.d/whalefall-default.conf
   
   # 检查容器状态
   make dev nginx-status
   ```

2. **SSL证书问题**
   ```bash
   # 验证证书
   make dev ssl-verify
   
   # 重新生成证书
   make dev ssl-generate
   ```

3. **Nginx无法启动**
   ```bash
   # 查看日志
   make dev nginx-logs
   
   # 检查配置
   make dev nginx-config
   ```

4. **配置重载失败**
   ```bash
   # 测试配置语法
   ./scripts/nginx/nginx_manager.sh test-config dev
   
   # 重启服务
   make dev nginx-restart
   ```

### 调试命令
```bash
# 进入容器调试
make dev nginx-shell

# 查看Nginx进程
docker exec whalefall_nginx_dev ps aux | grep nginx

# 查看配置文件
docker exec whalefall_nginx_dev cat /etc/nginx/conf.d/default.conf

# 测试配置语法
docker exec whalefall_nginx_dev nginx -t
```

## 📊 监控和维护

### 日志监控
```bash
# 实时查看日志
make dev nginx-logs

# 查看访问日志
docker exec whalefall_nginx_dev tail -f /var/log/nginx/access.log

# 查看错误日志
docker exec whalefall_nginx_dev tail -f /var/log/nginx/error.log
```

### 性能监控
```bash
# 查看Nginx状态
make dev nginx-status

# 查看容器资源使用
docker stats whalefall_nginx_dev

# 查看Nginx连接数
docker exec whalefall_nginx_dev netstat -an | grep :80 | wc -l
```

## 🔒 安全考虑

### 配置文件安全
- ✅ 配置文件上传前进行语法检查
- ✅ 自动备份现有配置
- ✅ 支持配置回滚
- ✅ 权限控制

### SSL证书安全
- ✅ 私钥文件权限设置为600
- ✅ 证书文件权限设置为644
- ✅ 支持证书验证
- ✅ 自动备份证书

## 📚 相关文档

- [Docker卷管理](DOCKER_VOLUMES.md)
- [Makefile使用指南](MAKEFILE_USAGE.md)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [SSL证书管理](SSL_CERTIFICATE_MANAGEMENT.md)

## 🎯 最佳实践

1. **配置管理**: 使用版本控制管理配置文件
2. **证书管理**: 定期备份和更新SSL证书
3. **监控告警**: 设置Nginx状态监控
4. **日志分析**: 定期分析访问日志
5. **安全更新**: 及时更新Nginx版本

## ⚠️ 注意事项

1. **配置备份**: 上传新配置前会自动备份
2. **证书验证**: 上传证书后会自动验证
3. **权限设置**: 确保脚本有执行权限
4. **容器状态**: 确保Nginx容器正在运行
5. **网络连接**: 确保容器间网络连通
