# 泰摸鱼吧生产环境部署指南

## 📋 概述

本文档详细说明如何在Debian/Ubuntu系统上使用Docker部署泰摸鱼吧生产环境。部署方案包括：

- **Flask应用**: 基于Ubuntu 22.04的Python应用
- **PostgreSQL**: 生产级数据库
- **Redis**: 缓存和消息队列
- **Nginx**: 反向代理和负载均衡
- **APScheduler**: 定时任务调度

## 🏗️ 架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Flask App     │    │   PostgreSQL    │
│   (Port 80/443) │────│   (Port 5000)   │────│   (Port 5432)   │
│   Load Balancer │    │   Web Server    │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  APScheduler    │    │     Redis       │
                       │   Background    │────│   (Port 6379)   │
                       │     Tasks       │    │ Cache & Queue   │
                       └─────────────────┘    └─────────────────┘
```

## 🔧 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **操作系统**: Debian 11+ 或 Ubuntu 20.04+

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **网络**: 100Mbps 带宽

## 🚀 快速部署

### 1. 一键部署脚本

```bash
# 下载项目
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 2. 手动部署步骤

#### 步骤1: 安装Docker

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo apt install docker-compose-plugin -y

# 将用户添加到docker组
sudo usermod -aG docker $USER
newgrp docker
```

#### 步骤2: 配置环境

```bash
# 创建项目目录
sudo mkdir -p /opt/taifish
sudo chown $USER:$USER /opt/taifish

# 复制项目文件
cp -r . /opt/taifish/
cd /opt/taifish

# 创建环境配置
cp env.production .env
```

#### 步骤3: 修改配置

编辑 `.env` 文件，修改以下关键配置：

```bash
# 修改密码
POSTGRES_PASSWORD=your-secure-password
REDIS_PASSWORD=your-redis-password
SECRET_KEY=your-secret-key

# 修改应用信息
APP_NAME=泰摸鱼吧
APP_VERSION=1.0.0
```

#### 步骤4: 启动服务

```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 检查状态
docker compose ps
```

#### 步骤5: 初始化数据库

```bash
# 等待数据库启动
sleep 30

# 初始化数据库
docker compose exec app python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
"

# 初始化权限配置
docker compose exec app python scripts/init_permission_config.py

# 初始化分类规则
docker compose exec app python scripts/init_default_classification_rules.py

# 创建管理员用户
docker compose exec app python scripts/create_admin_user.py
```

## 🔧 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `POSTGRES_PASSWORD` | PostgreSQL密码 | `Taifish2024!` | ✅ |
| `REDIS_PASSWORD` | Redis密码 | `Taifish2024!` | ✅ |
| `SECRET_KEY` | Flask密钥 | 随机生成 | ✅ |
| `APP_NAME` | 应用名称 | `泰摸鱼吧` | ❌ |
| `APP_VERSION` | 应用版本 | `1.0.0` | ❌ |

### 端口配置

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Nginx | 80 | 80 | HTTP |
| Nginx | 443 | 443 | HTTPS |
| Flask | 5000 | - | 应用服务 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |

### 数据卷配置

| 卷名 | 挂载点 | 说明 |
|------|--------|------|
| `postgres_data` | `/var/lib/postgresql/data` | 数据库数据 |
| `redis_data` | `/data` | Redis数据 |
| `app_data` | `/app/userdata` | 应用数据 |

## 🛠️ 管理命令

### 使用Makefile

```bash
# 查看所有命令
make help

# 启动服务
make up

# 停止服务
make down

# 重启服务
make restart

# 查看日志
make logs

# 进入容器
make shell

# 备份数据库
make backup

# 恢复数据库
make restore FILE=backups/backup.sql
```

### 使用Docker Compose

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 查看日志
docker compose logs -f

# 进入应用容器
docker compose exec app bash

# 进入数据库容器
docker compose exec postgres psql -U taifish_user -d taifish_prod
```

### 使用系统服务

```bash
# 启动服务
sudo systemctl start taifish

# 停止服务
sudo systemctl stop taifish

# 重启服务
sudo systemctl restart taifish

# 查看状态
sudo systemctl status taifish

# 开机自启
sudo systemctl enable taifish
```

## 📊 监控和维护

### 健康检查

```bash
# 检查服务状态
make health

# 检查应用健康
curl http://localhost/health

# 检查数据库连接
docker compose exec postgres pg_isready -U taifish_user -d taifish_prod

# 检查Redis连接
docker compose exec redis redis-cli ping
```

### 日志管理

```bash
# 查看所有日志
make logs

# 查看应用日志
make logs-app

# 查看数据库日志
make logs-db

# 实时查看日志
docker compose logs -f app
```

### 备份和恢复

```bash
# 备份数据库
make backup

# 恢复数据库
make restore FILE=backups/taifish_backup_20240912_120000.sql

# 自动备份脚本
echo "0 2 * * * /opt/taifish/backup.sh" | crontab -
```

## 🔒 安全配置

### SSL证书配置

1. **获取SSL证书**:
   ```bash
   # 使用Let's Encrypt
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **配置Nginx**:
   ```bash
   # 复制证书到项目目录
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/taifish/ssl/cert.pem
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/taifish/ssl/key.pem
   
   # 修改Nginx配置启用HTTPS
   # 编辑 docker/nginx/nginx.conf
   ```

3. **重启服务**:
   ```bash
   make restart
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
# 修改默认密码
docker compose exec postgres psql -U taifish_user -d taifish_prod -c "
ALTER USER taifish_user PASSWORD 'new-secure-password';
"

# 限制连接
# 编辑 docker/postgres/postgresql.conf
max_connections = 100
```

## 🚨 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查日志
docker compose logs

# 检查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5432

# 重启服务
docker compose down && docker compose up -d
```

#### 2. 数据库连接失败

```bash
# 检查数据库状态
docker compose exec postgres pg_isready -U taifish_user -d taifish_prod

# 检查数据库日志
docker compose logs postgres

# 重置数据库
docker compose down -v
docker compose up -d
```

#### 3. 内存不足

```bash
# 检查内存使用
docker stats

# 清理未使用的镜像
docker system prune -a

# 调整Redis内存限制
# 编辑 docker/redis/redis.conf
maxmemory 128mb
```

#### 4. 磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 清理Docker数据
docker system prune -a --volumes

# 清理日志文件
sudo find /opt/taifish/logs -name "*.log" -mtime +7 -delete
```

### 性能优化

#### 1. 数据库优化

```bash
# 编辑PostgreSQL配置
# docker/postgres/postgresql.conf
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB
```

#### 2. Redis优化

```bash
# 编辑Redis配置
# docker/redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

#### 3. Nginx优化

```bash
# 编辑Nginx配置
# docker/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
```

## 📈 扩展和升级

### 水平扩展

```bash
# 扩展应用实例
docker compose up -d --scale app=3

# 扩展APScheduler任务处理
# APScheduler已集成在Flask应用中，无需单独扩展
```

### 版本升级

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker compose build --no-cache

# 滚动更新
docker compose up -d --no-deps app
```

### 数据迁移

```bash
# 备份当前数据
make backup

# 停止服务
make down

# 更新代码
git pull

# 启动新版本
make up

# 运行数据迁移
docker compose exec app python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
"
```

## 📞 技术支持

### 日志收集

```bash
# 收集系统信息
uname -a > system_info.txt
docker version >> system_info.txt
docker compose ps >> system_info.txt

# 收集应用日志
docker compose logs > app_logs.txt

# 收集数据库日志
docker compose logs postgres > db_logs.txt
```

### 联系方式

- **项目地址**: https://github.com/nyealovey/TaifishingV4
- **问题反馈**: 通过GitHub Issues
- **文档更新**: 定期更新部署文档

## 📝 更新日志

### v1.0.0 (2024-09-12)
- 初始生产环境部署方案
- 支持Docker Compose部署
- 包含完整的监控和维护工具
- 提供自动化部署脚本

---

**注意**: 本部署方案适用于生产环境，请根据实际需求调整配置参数。
