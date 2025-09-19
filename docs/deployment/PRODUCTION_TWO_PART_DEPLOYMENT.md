# 鲸落生产环境两部分部署指南

## 📋 概述

本文档详细说明鲸落生产环境的两部分部署方案：

1. **基础环境部署**：Docker、PostgreSQL、Redis、Nginx + 数据库初始化
2. **Flask应用部署**：Flask应用打包部署 + 版本更新能力

## 🏗️ 架构设计

### 两部分部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    基础环境层                                │
├─────────────────┬─────────────────┬─────────────────────────┤
│   PostgreSQL    │     Redis       │        Nginx            │
│   (Port 5432)   │   (Port 6379)   │    (Port 80/443)       │
│   数据库服务     │    缓存服务      │     反向代理            │
└─────────────────┴─────────────────┴─────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Flask应用层                              │
├─────────────────────────────────────────────────────────────┤
│              Flask应用 + APScheduler                       │
│                (Port 5001)                                 │
│               Web服务 + 定时任务                            │
└─────────────────────────────────────────────────────────────┘
```

### 部署优势

- **独立部署**：基础环境和Flask应用可以独立部署和更新
- **滚动更新**：Flask应用支持零停机滚动更新
- **版本管理**：支持多版本并存和快速回滚
- **资源隔离**：基础环境和应用环境资源隔离
- **维护便利**：可以单独维护基础环境或应用环境

## 🚀 快速部署

### 一键部署所有服务

```bash
# 克隆项目
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 配置环境
cp env.prod .env
# 编辑 .env 文件，设置必要的环境变量

# 一键启动所有服务
chmod +x scripts/*.sh
./scripts/start-all.sh
```

### 分步部署

#### 第一步：部署基础环境

```bash
# 部署基础环境（PostgreSQL、Redis、Nginx）
./scripts/deploy-base.sh
```

#### 第二步：部署Flask应用

```bash
# 部署Flask应用
./scripts/deploy-flask.sh
```

## 🔧 详细部署步骤

### 1. 基础环境部署

#### 1.1 系统要求

- **操作系统**：Debian 11+ 或 Ubuntu 20.04+
- **Docker**：20.10+
- **Docker Compose**：2.0+
- **内存**：最少2GB，推荐4GB+
- **存储**：最少20GB，推荐50GB+

#### 1.2 环境配置

```bash
# 创建环境配置文件
cp env.prod .env

# 编辑配置文件
nano .env
```

关键配置项：

```bash
# 数据库配置
POSTGRES_DB=whalefall_prod
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=your-secure-password

# Redis配置
REDIS_PASSWORD=your-redis-password

# 应用配置
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
BCRYPT_LOG_ROUNDS=12
LOG_LEVEL=INFO

# 应用信息
APP_NAME=鲸落
APP_VERSION=4.0.0
```

#### 1.3 启动基础环境

```bash
# 运行基础环境部署脚本
./scripts/deploy-base.sh
```

部署过程包括：
- 检查系统依赖
- 创建数据目录
- 启动PostgreSQL、Redis、Nginx
- 初始化数据库
- 验证服务状态

#### 1.4 验证基础环境

```bash
# 检查服务状态
docker-compose -f docker-compose.base.yml ps

# 检查PostgreSQL
docker-compose -f docker-compose.base.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod

# 检查Redis
docker-compose -f docker-compose.base.yml exec redis redis-cli ping

# 检查Nginx
curl http://localhost/health
```

### 2. Flask应用部署

#### 2.1 构建应用镜像

```bash
# 构建Flask应用镜像
docker build -t whalefall:latest .

# 或指定版本
docker build -t whalefall:4.0.0 .
```

#### 2.2 部署Flask应用

```bash
# 运行Flask应用部署脚本
./scripts/deploy-flask.sh
```

部署过程包括：
- 检查基础环境
- 构建应用镜像
- 启动Flask应用
- 初始化数据库
- 创建管理员用户
- 验证应用状态

#### 2.3 验证Flask应用

```bash
# 检查应用状态
docker-compose -f docker-compose.flask.yml ps

# 检查应用健康
curl http://localhost:5001/health

# 检查Nginx代理
curl http://localhost/health

# 访问管理界面
curl http://localhost/admin
```

## 🔄 版本更新

### 滚动更新

```bash
# 更新到指定版本
./scripts/update-version.sh 4.1.0

# 备份后更新
./scripts/update-version.sh -b 4.1.0

# 强制更新（跳过确认）
./scripts/update-version.sh -f 4.1.0
```

### 版本管理

```bash
# 检查当前版本
./scripts/update-version.sh -s

# 检查更新可用性
./scripts/update-version.sh -c

# 回滚到上一个版本
./scripts/update-version.sh -r
```

### 更新流程

1. **代码更新**：从Git仓库拉取最新代码
2. **镜像构建**：构建新版本Docker镜像
3. **滚动更新**：零停机更新Flask应用
4. **健康检查**：验证新版本应用状态
5. **清理资源**：清理旧版本镜像

## 🛠️ 服务管理

### 启动服务

```bash
# 启动所有服务
./scripts/start-all.sh

# 仅启动基础环境
docker-compose -f docker-compose.base.yml up -d

# 仅启动Flask应用
docker-compose -f docker-compose.flask.yml up -d
```

### 停止服务

```bash
# 停止所有服务
./scripts/stop-all.sh

# 仅停止Flask应用
docker-compose -f docker-compose.flask.yml down

# 仅停止基础环境
docker-compose -f docker-compose.base.yml down
```

### 重启服务

```bash
# 重启Flask应用
docker-compose -f docker-compose.flask.yml restart

# 重启基础环境
docker-compose -f docker-compose.base.yml restart

# 重启所有服务
./scripts/stop-all.sh && ./scripts/start-all.sh
```

### 查看日志

```bash
# 查看所有日志
docker-compose -f docker-compose.base.yml logs -f
docker-compose -f docker-compose.flask.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.flask.yml logs -f whalefall
docker-compose -f docker-compose.base.yml logs -f postgres
```

## 📊 监控和维护

### 健康检查

```bash
# 检查所有服务健康状态
curl http://localhost/health

# 检查Flask应用健康
curl http://localhost:5001/health

# 检查数据库连接
docker-compose -f docker-compose.base.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod

# 检查Redis连接
docker-compose -f docker-compose.base.yml exec redis redis-cli ping
```

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看服务状态
docker-compose -f docker-compose.base.yml ps
docker-compose -f docker-compose.flask.yml ps

# 查看系统资源
htop
df -h
free -h
```

### 日志管理

```bash
# 查看应用日志
tail -f /opt/whale_fall_data/logs/whalefall.log

# 查看Nginx日志
tail -f /opt/whale_fall_data/nginx/logs/access.log
tail -f /opt/whale_fall_data/nginx/logs/error.log

# 查看数据库日志
docker-compose -f docker-compose.base.yml logs postgres
```

## 🔒 安全配置

### SSL证书配置

```bash
# 生成自签名证书（开发环境）
./scripts/generate-ssl-cert.sh

# 更新外部证书
./scripts/update-external-ssl.sh -c whalefall.local.pem -k whalefall.local.key

# 管理SSL证书
./scripts/ssl-manager.sh help
```

### 防火墙配置

```bash
# 配置UFW防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 数据库安全

```bash
# 修改数据库密码
docker-compose -f docker-compose.base.yml exec postgres psql -U whalefall_user -d whalefall_prod -c "
ALTER USER whalefall_user PASSWORD 'new-secure-password';
"

# 限制数据库连接
# 编辑 docker-compose.base.yml 中的 postgres 服务配置
```

## 📈 扩展和优化

### 水平扩展

```bash
# 扩展Flask应用实例
docker-compose -f docker-compose.flask.yml up -d --scale whalefall=3

# 配置Nginx负载均衡
# 编辑 nginx/conf.d/whalefall.conf
```

### 性能优化

#### 数据库优化

```bash
# 编辑PostgreSQL配置
# 在 docker-compose.base.yml 中添加环境变量
environment:
  - POSTGRES_SHARED_BUFFERS=256MB
  - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
  - POSTGRES_WORK_MEM=4MB
```

#### Redis优化

```bash
# 编辑Redis配置
# 在 docker-compose.base.yml 中修改command
command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

#### Nginx优化

```bash
# 编辑Nginx配置
# 在 nginx/conf.d/whalefall.conf 中添加
worker_processes auto;
worker_connections 1024;
```

## 🚨 故障排除

### 常见问题

#### 1. 基础环境启动失败

```bash
# 检查端口占用
sudo netstat -tlnp | grep -E ':(80|443|5432|6379) '

# 检查Docker状态
docker version
docker-compose version

# 查看详细日志
docker-compose -f docker-compose.base.yml logs
```

#### 2. Flask应用启动失败

```bash
# 检查基础环境
docker-compose -f docker-compose.base.yml ps

# 检查镜像构建
docker images | grep whalefall

# 查看应用日志
docker-compose -f docker-compose.flask.yml logs whalefall
```

#### 3. 数据库连接失败

```bash
# 检查数据库状态
docker-compose -f docker-compose.base.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod

# 检查网络连接
docker network ls
docker network inspect whalefall_network

# 重置数据库
docker-compose -f docker-compose.base.yml down -v
docker-compose -f docker-compose.base.yml up -d
```

#### 4. 版本更新失败

```bash
# 检查备份
ls -la /opt/whale_fall_data/backups/

# 回滚到上一个版本
./scripts/update-version.sh -r

# 手动回滚
docker-compose -f docker-compose.flask.yml down
docker tag whalefall:previous whalefall:latest
docker-compose -f docker-compose.flask.yml up -d
```

### 性能问题

#### 1. 内存不足

```bash
# 检查内存使用
free -h
docker stats

# 清理Docker资源
docker system prune -a

# 调整服务资源限制
# 编辑 docker-compose.*.yml 中的 deploy.resources
```

#### 2. 磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 清理日志文件
sudo find /opt/whale_fall_data/logs -name "*.log" -mtime +7 -delete

# 清理Docker数据
docker system prune -a --volumes
```

## 📞 技术支持

### 日志收集

```bash
# 收集系统信息
uname -a > system_info.txt
docker version >> system_info.txt
docker-compose version >> system_info.txt

# 收集服务状态
docker-compose -f docker-compose.base.yml ps >> system_info.txt
docker-compose -f docker-compose.flask.yml ps >> system_info.txt

# 收集应用日志
docker-compose -f docker-compose.flask.yml logs > app_logs.txt
docker-compose -f docker-compose.base.yml logs > base_logs.txt
```

### 联系方式

- **项目地址**: https://github.com/nyealovey/TaifishingV4
- **问题反馈**: 通过GitHub Issues
- **文档更新**: 定期更新部署文档

## 📝 更新日志

### v4.0.0 (2024-12-19)
- 实现两部分部署架构
- 支持独立部署基础环境和Flask应用
- 提供版本更新和回滚能力
- 优化部署脚本和监控工具

---

**注意**: 本部署方案适用于生产环境，请根据实际需求调整配置参数。
