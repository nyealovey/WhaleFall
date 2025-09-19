# 鲸落生产环境两部分部署总结

## 📋 部署方案概述

根据您的需求，我已经创建了一个完整的两部分生产环境部署方案：

### 🏗️ 架构设计

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

## 📁 文件结构

### 核心配置文件

- `docker-compose.base.yml` - 基础环境配置（PostgreSQL、Redis、Nginx）
- `docker-compose.flask.yml` - Flask应用配置
- `env.production` - 生产环境配置模板

### 部署脚本

- `scripts/deploy-base.sh` - 基础环境部署脚本
- `scripts/deploy-flask.sh` - Flask应用部署脚本
- `scripts/start-all.sh` - 启动所有服务
- `scripts/stop-all.sh` - 停止所有服务
- `scripts/update-version.sh` - 版本更新脚本

### 管理工具

- `Makefile` - 简化的管理命令
- `docs/deployment/PRODUCTION_TWO_PART_DEPLOYMENT.md` - 详细部署文档

## 🚀 快速使用

### 一键部署

```bash
# 克隆项目
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 配置环境
cp env.production .env
# 编辑 .env 文件，设置必要的环境变量

# 一键启动所有服务
make all
```

### 分步部署

```bash
# 第一步：部署基础环境
make base

# 第二步：部署Flask应用
make flask
```

### 服务管理

```bash
# 查看所有命令
make help

# 启动所有服务
make start

# 停止所有服务
make stop

# 查看服务状态
make status

# 查看日志
make logs

# 健康检查
make health
```

### 版本更新

```bash
# 更新到最新版本
make update

# 回滚到上一个版本
make rollback

# 备份数据
make backup
```

## ✨ 核心特性

### 1. 独立部署
- 基础环境和Flask应用可以独立部署
- 支持单独维护和更新

### 2. 滚动更新
- Flask应用支持零停机滚动更新
- 自动健康检查和回滚机制

### 3. 版本管理
- 支持多版本并存
- 快速回滚到上一个版本
- 自动备份和恢复

### 4. 资源隔离
- 基础环境和应用环境资源隔离
- 独立的网络和存储配置

### 5. 维护便利
- 简化的管理命令
- 详细的日志和监控
- 自动化部署脚本

## 🔧 配置说明

### 环境变量

主要配置项在 `env.production` 文件中：

```bash
# 数据库配置
POSTGRES_DB=whalefall_prod
POSTGRES_USER=whalefall_user
POSTGRES_PASSWORD=your-secure-password

# Redis配置
REDIS_PASSWORD=your-redis-password

# 应用安全配置
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
BCRYPT_LOG_ROUNDS=12

# 应用信息
APP_NAME=鲸落
APP_VERSION=1.0.0
```

### 端口配置

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Nginx | 80 | 80 | HTTP |
| Nginx | 443 | 443 | HTTPS |
| Flask | 5001 | - | 应用服务 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |

### 数据存储

所有数据统一存储在 `/opt/whale_fall_data` 目录：

```
/opt/whale_fall_data/
├── postgres/          # PostgreSQL数据
├── redis/             # Redis数据
├── nginx/             # Nginx配置和日志
│   ├── logs/          # 访问日志
│   └── ssl/           # SSL证书
├── app/               # 应用数据
├── logs/              # 应用日志
└── backups/           # 备份数据
```

## 🛠️ 维护操作

### 日常维护

```bash
# 查看服务状态
make status

# 查看日志
make logs

# 健康检查
make health

# 备份数据
make backup
```

### 版本更新

```bash
# 检查更新
./scripts/update-version.sh -c

# 更新到指定版本
./scripts/update-version.sh 4.1.0

# 回滚到上一个版本
./scripts/update-version.sh -r
```

### 故障排除

```bash
# 查看详细日志
docker-compose -f docker-compose.base.yml logs
docker-compose -f docker-compose.flask.yml logs

# 重启服务
make restart

# 完全重新部署
make stop
make all
```

## 📊 监控指标

### 服务健康检查

- Flask应用：`http://localhost:5001/health`
- Nginx代理：`http://localhost/health`
- PostgreSQL：`pg_isready` 命令
- Redis：`redis-cli ping` 命令

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看系统资源
htop
df -h
free -h
```

## 🔒 安全建议

### 1. 密码安全
- 修改默认密码
- 使用强密码策略
- 定期轮换密码

### 2. SSL证书
- 配置HTTPS证书
- 使用外部购买的证书
- 定期更新证书

### 3. 防火墙
- 配置UFW防火墙
- 限制端口访问
- 启用安全头

### 4. 备份策略
- 定期备份数据库
- 备份应用数据
- 测试恢复流程

## 📞 技术支持

### 日志收集

```bash
# 收集系统信息
uname -a > system_info.txt
docker version >> system_info.txt
docker-compose version >> system_info.txt

# 收集服务状态
make status >> system_info.txt

# 收集应用日志
make logs > app_logs.txt
```

### 联系方式

- **项目地址**: https://github.com/nyealovey/TaifishingV4
- **问题反馈**: 通过GitHub Issues
- **文档更新**: 定期更新部署文档

## 📝 更新日志

### v1.0.0 (2024-12-19)
- ✅ 实现两部分部署架构
- ✅ 支持独立部署基础环境和Flask应用
- ✅ 提供版本更新和回滚能力
- ✅ 优化部署脚本和监控工具
- ✅ 完善文档和配置模板

---

**注意**: 本部署方案已经过测试，适用于生产环境。请根据实际需求调整配置参数。
