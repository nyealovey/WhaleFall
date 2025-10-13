# 鲸落 (TaifishV4) 生产环境部署指南

## 📋 部署概览

本指南将帮助您在生产环境中部署鲸落系统。系统支持多种部署方式，包括Docker容器化部署、传统服务器部署等。

### 系统要求

#### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 50GB SSD
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

#### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 100GB SSD
- **操作系统**: Ubuntu 22.04 LTS

### 软件依赖
- **Python**: 3.11+
- **PostgreSQL**: 13+
- **Redis**: 6.0+
- **Nginx**: 1.18+
- **Docker**: 20.10+ (可选)

## 🐳 Docker 容器化部署 (推荐)

### 1. 环境准备

#### 创建部署目录
```bash
mkdir -p /opt/whalefalling
cd /opt/whalefalling
```

#### 克隆代码
```bash
git clone https://github.com/nyealovey/TaifishingV4.git .
```

### 2. 配置文件

#### 环境变量配置
```bash
# 复制环境配置文件
cp env.production .env

# 编辑环境配置
nano .env
```

#### 环境变量示例
```bash
# 应用配置
APP_NAME=鲸落
APP_VERSION=1.1.2
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# 数据库配置
DATABASE_URL=postgresql://user:password@postgres:5432/whalefalling
REDIS_URL=redis://redis:6379/0

# 安全配置
JWT_SECRET_KEY=your-jwt-secret-key
CSRF_SECRET_KEY=your-csrf-secret-key

# 邮件配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password

# 监控配置
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
```

### 3. Docker Compose 部署

#### 启动服务
```bash
# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

#### 服务组件
- **app**: Flask应用容器
- **postgres**: PostgreSQL数据库
- **redis**: Redis缓存
- **nginx**: Nginx反向代理

### 4. 数据库初始化

#### 运行数据库迁移
```bash
# 进入应用容器
docker-compose -f docker-compose.prod.yml exec app bash

# 运行数据库迁移
flask db upgrade

# 初始化数据
python scripts/init_data.py
```

## 🖥️ 传统服务器部署

### 1. 系统准备

#### 更新系统包
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

#### 安装基础软件
```bash
# Ubuntu/Debian
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    postgresql-13 postgresql-client-13 redis-server nginx \
    build-essential libpq-dev

# CentOS/RHEL
sudo yum install -y python3.11 python3.11-pip postgresql13-server \
    redis nginx gcc postgresql13-devel
```

### 2. 数据库配置

#### PostgreSQL 配置
```bash
# 启动PostgreSQL服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql
```

```sql
-- 创建数据库
CREATE DATABASE whalefalling;

-- 创建用户
CREATE USER whalefalling_user WITH PASSWORD 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE whalefalling TO whalefalling_user;
\q
```

#### Redis 配置
```bash
# 启动Redis服务
sudo systemctl start redis
sudo systemctl enable redis

# 配置Redis
sudo nano /etc/redis/redis.conf
```

```conf
# Redis配置
bind 127.0.0.1
port 6379
requirepass your_redis_password
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### 3. 应用部署

#### 创建应用用户
```bash
sudo useradd -m -s /bin/bash whalefalling
sudo usermod -aG sudo whalefalling
```

#### 部署应用代码
```bash
# 切换到应用用户
sudo su - whalefalling

# 创建应用目录
mkdir -p /home/whalefalling/app
cd /home/whalefalling/app

# 克隆代码
git clone https://github.com/nyealovey/TaifishingV4.git .

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements-prod.txt
```

#### 配置应用
```bash
# 复制配置文件
cp env.production .env

# 编辑配置
nano .env
```

### 4. 数据库迁移

#### 运行迁移
```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=production

# 运行迁移
flask db upgrade

# 初始化数据
python scripts/init_data.py
```

### 5. Web服务器配置

#### Nginx 配置
```bash
# 创建Nginx配置
sudo nano /etc/nginx/sites-available/whalefalling
```

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL证书配置
    ssl_certificate /etc/ssl/certs/whalefalling.crt;
    ssl_certificate_key /etc/ssl/private/whalefalling.key;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 静态文件
    location /static {
        alias /home/whalefalling/app/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 应用代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 启用站点
```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/whalefalling /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 6. 进程管理

#### Supervisor 配置
```bash
# 安装Supervisor
sudo apt install supervisor

# 创建应用配置
sudo nano /etc/supervisor/conf.d/whalefalling.conf
```

```ini
[program:whalefalling]
command=/home/whalefalling/app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 wsgi:app
directory=/home/whalefalling/app
user=whalefalling
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/whalefalling/app.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
```

#### 启动服务
```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动应用
sudo supervisorctl start whalefalling

# 查看状态
sudo supervisorctl status whalefalling
```

## 🔒 SSL证书配置

### Let's Encrypt 证书

#### 安装 Certbot
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

#### 获取证书
```bash
# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
```

```cron
# 自动续期SSL证书
0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 监控配置

### 系统监控

#### 安装监控工具
```bash
# 安装htop, iotop等监控工具
sudo apt install htop iotop nethogs

# 安装Prometheus和Grafana (可选)
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
```

#### 配置日志轮转
```bash
# 配置logrotate
sudo nano /etc/logrotate.d/whalefalling
```

```
/var/log/whalefalling/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 whalefalling whalefalling
    postrotate
        supervisorctl restart whalefalling
    endscript
}
```

### 应用监控

#### 健康检查
```bash
# 创建健康检查脚本
nano /home/whalefalling/health_check.sh
```

```bash
#!/bin/bash
# 健康检查脚本
curl -f http://localhost:5000/api/health || exit 1
```

```bash
# 设置执行权限
chmod +x /home/whalefalling/health_check.sh

# 添加到crontab
crontab -e
```

```cron
# 每5分钟检查一次
*/5 * * * * /home/whalefalling/health_check.sh
```

## 🔧 维护和更新

### 应用更新

#### 更新代码
```bash
# 切换到应用目录
cd /home/whalefalling/app

# 拉取最新代码
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements-prod.txt

# 运行数据库迁移
flask db upgrade

# 重启应用
sudo supervisorctl restart whalefalling
```

#### 数据库备份
```bash
# 创建备份脚本
nano /home/whalefalling/backup.sh
```

```bash
#!/bin/bash
# 数据库备份脚本
BACKUP_DIR="/home/whalefalling/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U whalefalling_user whalefalling > $BACKUP_DIR/whalefalling_$DATE.sql
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

```bash
# 设置执行权限
chmod +x /home/whalefalling/backup.sh

# 添加到crontab (每天凌晨2点备份)
crontab -e
```

```cron
# 数据库备份
0 2 * * * /home/whalefalling/backup.sh
```

### 性能优化

#### 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_instances_status ON instances(status);
CREATE INDEX idx_logs_timestamp ON unified_logs(timestamp);
CREATE INDEX idx_sync_sessions_status ON sync_sessions(status);

-- 分析表统计信息
ANALYZE;
```

#### 应用优化
```bash
# 调整Gunicorn配置
nano /etc/supervisor/conf.d/whalefalling.conf
```

```ini
[program:whalefalling]
command=/home/whalefalling/app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 8 --worker-class gevent --worker-connections 1000 --timeout 120 wsgi:app
```

## 🚨 故障排除

### 常见问题

#### 1. 应用无法启动
```bash
# 检查日志
sudo supervisorctl tail -f whalefalling

# 检查端口占用
netstat -tlnp | grep :5000

# 检查权限
ls -la /home/whalefalling/app
```

#### 2. 数据库连接失败
```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U whalefalling_user -d whalefalling

# 检查配置文件
cat /home/whalefalling/app/.env | grep DATABASE
```

#### 3. Redis连接失败
```bash
# 检查Redis状态
sudo systemctl status redis

# 测试连接
redis-cli ping

# 检查配置
cat /etc/redis/redis.conf | grep requirepass
```

### 日志分析

#### 应用日志
```bash
# 查看应用日志
tail -f /var/log/whalefalling/app.log

# 查看Nginx日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 查看系统日志
journalctl -u whalefalling -f
```

## 📋 部署检查清单

### 部署前检查
- [ ] 服务器配置满足要求
- [ ] 域名解析配置正确
- [ ] SSL证书准备就绪
- [ ] 数据库用户和权限配置
- [ ] 环境变量配置完整

### 部署后检查
- [ ] 应用服务正常运行
- [ ] 数据库连接正常
- [ ] Redis连接正常
- [ ] Nginx配置正确
- [ ] SSL证书有效
- [ ] 监控配置生效
- [ ] 备份脚本运行正常

### 性能检查
- [ ] 响应时间 < 2秒
- [ ] 内存使用 < 80%
- [ ] CPU使用 < 70%
- [ ] 磁盘空间 > 20%
- [ ] 数据库连接数正常

## 📞 技术支持

如果在部署过程中遇到问题，请：

1. 查看相关日志文件
2. 检查系统资源使用情况
3. 验证配置文件正确性
4. 参考故障排除部分
5. 提交Issue到GitHub仓库

---

**最后更新**: 2025-09-25  
**文档版本**: v1.1.2  
**维护团队**: TaifishingV4 Team
