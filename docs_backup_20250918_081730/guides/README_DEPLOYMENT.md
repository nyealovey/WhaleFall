# 🐟 泰摸鱼吧生产环境部署

## 📋 快速开始

### 一键部署

```bash
# 克隆项目
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 访问应用

- **应用地址**: http://your-server-ip
- **默认登录**: admin / Admin123
- **管理界面**: http://your-server-ip/admin

## 🏗️ 架构组件

| 组件 | 版本 | 端口 | 说明 |
|------|------|------|------|
| **Nginx** | Alpine | 80/443 | 反向代理和负载均衡 |
| **Flask** | Ubuntu 22.04 | 5000 | Web应用服务 |
| **PostgreSQL** | 15 | 5432 | 主数据库 |
| **Redis** | 7 | 6379 | 缓存和消息队列 |
| **Celery** | - | - | 异步任务处理 |

## 🚀 部署方式

### 方式1: 自动部署脚本

```bash
# 运行一键部署脚本
./deploy.sh
```

### 方式2: Docker Compose

```bash
# 复制环境配置
cp env.production .env

# 构建和启动
docker compose up -d

# 初始化数据库
make init-db
```

### 方式3: Make命令

```bash
# 查看所有命令
make help

# 生产环境部署
make deploy-prod

# 开发环境部署
make deploy-dev
```

## 🔧 管理命令

### 服务管理

```bash
# 启动服务
make up

# 停止服务
make down

# 重启服务
make restart

# 查看状态
make status
```

### 日志管理

```bash
# 查看所有日志
make logs

# 查看应用日志
make logs-app

# 查看数据库日志
make logs-db
```

### 数据管理

```bash
# 备份数据库
make backup

# 恢复数据库
make restore FILE=backups/backup.sql

# 初始化数据库
make init-db
```

## 📊 监控和维护

### 健康检查

```bash
# 检查服务健康状态
make health

# 检查应用健康
curl http://localhost/health
```

### 性能监控

```bash
# 查看资源使用
make stats

# 查看服务状态
docker compose ps
```

## 🔒 安全配置

### SSL证书

```bash
# 使用Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com

# 配置HTTPS
# 编辑 docker/nginx/nginx.conf
```

### 防火墙

```bash
# 配置UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查日志
   docker compose logs
   
   # 检查端口占用
   sudo netstat -tlnp | grep :80
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker compose exec postgres pg_isready -U taifish_user -d taifish_prod
   ```

3. **内存不足**
   ```bash
   # 清理Docker数据
   docker system prune -a
   ```

### 日志收集

```bash
# 收集系统信息
uname -a > system_info.txt
docker version >> system_info.txt
docker compose ps >> system_info.txt
```

## 📈 扩展和升级

### 水平扩展

```bash
# 扩展应用实例
docker compose up -d --scale app=3

# 扩展Celery Worker
docker compose up -d --scale celery_worker=3
```

### 版本升级

```bash
# 拉取最新代码
git pull

# 重新构建
docker compose build --no-cache

# 滚动更新
docker compose up -d --no-deps app
```

## 📚 详细文档

- [生产环境部署指南](doc/deployment/PRODUCTION_DEPLOYMENT.md)
- [Docker架构设计](doc/deployment/DOCKER_ARCHITECTURE.md)
- [系统配置管理](doc/CONFIG_MANAGEMENT_FEATURES.md)

## 🆘 技术支持

- **项目地址**: https://github.com/nyealovey/TaifishingV4
- **问题反馈**: 通过GitHub Issues
- **文档更新**: 定期更新部署文档

## 📝 更新日志

### v1.0.0 (2024-09-12)
- ✅ 完整的Docker化部署方案
- ✅ 支持Debian/Ubuntu系统
- ✅ 包含Nginx + PostgreSQL + Redis
- ✅ 自动化部署脚本
- ✅ 完整的监控和维护工具

---

**注意**: 生产环境部署前请仔细阅读详细文档，并根据实际需求调整配置。
