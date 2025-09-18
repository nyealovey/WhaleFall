# 鲸落 - Docker 生产环境部署指南

## 概述

本文档详细说明如何在Debian生产环境中使用Docker部署鲸落系统。系统采用微服务架构，主程序打包为Docker镜像，其他服务使用公共镜像。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   Taifish App   │    │   PostgreSQL    │
│   (反向代理)     │◄──►│   (主程序)      │◄──►│   (数据库)      │
│   Port: 80/443  │    │   Port: 5000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SSL证书        │    │   Redis缓存     │    │   数据持久化     │
│   (Let's Encrypt)│    │   Port: 6379    │    │   (Docker Volumes)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 环境要求

### 服务器配置
- **操作系统**: Debian 12 (Bookworm) 或更高版本
- **CPU**: 2核心以上
- **内存**: 4GB以上
- **存储**: 50GB以上SSD
- **网络**: 公网IP，开放80/443端口

### 软件依赖
- Docker 24.0+
- Docker Compose 2.0+
- Git 2.0+

## 部署步骤

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo apt install docker-compose-plugin -y

# 验证安装
docker --version
docker compose version
```

### 2. 项目部署

```bash
# 创建部署目录
sudo mkdir -p /opt/taifish
cd /opt/taifish

# 克隆项目代码
sudo git clone https://github.com/your-username/TaifishingV4.git .

# 设置权限
sudo chown -R $USER:$USER /opt/taifish
```

### 3. 环境配置

```bash
# 复制环境配置文件
cp env.example .env

# 编辑环境配置
nano .env
```

**生产环境配置示例**:
```ini
# 应用配置
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here

# 数据库配置
DATABASE_URL=postgresql://taifish_user:your-db-password@postgres:5432/taifish_prod
POSTGRES_DB=taifish_prod
POSTGRES_USER=taifish_user
POSTGRES_PASSWORD=your-super-secure-db-password

# Redis配置
REDIS_URL=redis://:your-redis-password@redis:6379/0
REDIS_PASSWORD=your-redis-password

# 安全配置
BCRYPT_LOG_ROUNDS=12
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# 默认管理员密码
DEFAULT_ADMIN_PASSWORD=your-secure-admin-password

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/app/userdata/logs/app.log

# 文件上传配置
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=/app/userdata/uploads

# 缓存配置
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:your-redis-password@redis:6379/1
```

### 4. 构建主程序镜像

```bash
# 构建Docker镜像
docker build -t taifish:latest .

# 验证镜像构建
docker images | grep taifish
```

### 5. 配置Nginx

```bash
# 创建Nginx配置目录
mkdir -p nginx/conf.d

# 创建Nginx配置文件
cat > nginx/conf.d/taifish.conf << 'EOF'
upstream taifish_backend {
    server taifish:5000;
}

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
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # 客户端最大请求体大小
    client_max_body_size 16M;
    
    # 代理配置
    location / {
        proxy_pass http://taifish_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 静态文件缓存
    location /static/ {
        proxy_pass http://taifish_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 健康检查
    location /health {
        proxy_pass http://taifish_backend;
        access_log off;
    }
}
EOF
```

### 6. 创建Docker Compose配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # 主程序
  taifish:
    image: taifish:latest
    container_name: taifish_app
    restart: unless-stopped
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://taifish_user:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    env_file:
      - .env
    volumes:
      - taifish_data:/app/userdata
      - taifish_logs:/app/userdata/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - taifish_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    container_name: taifish_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init_postgresql.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - taifish_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c pg_stat_statements.track=all
      -c log_statement=all
      -c log_min_duration_statement=1000
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: taifish_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - taifish_network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: taifish_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - taifish
    networks:
      - taifish_network

volumes:
  taifish_data:
    driver: local
  taifish_logs:
    driver: local
  postgres_data:
    driver: local
  redis_data:
    driver: local
  nginx_logs:
    driver: local

networks:
  taifish_network:
    driver: bridge
```

### 7. SSL证书配置

#### 使用Let's Encrypt (推荐)

```bash
# 安装Certbot
sudo apt install certbot -y

# 获取SSL证书
sudo certbot certonly --standalone -d your-domain.com

# 创建证书目录
mkdir -p nginx/ssl

# 复制证书文件
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# 设置权限
sudo chown -R $USER:$USER nginx/ssl
chmod 644 nginx/ssl/cert.pem
chmod 600 nginx/ssl/key.pem
```

#### 使用自签名证书 (测试环境)

```bash
# 创建SSL证书目录
mkdir -p nginx/ssl

# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=CN/ST=State/L=City/O=Organization/CN=your-domain.com"
```

### 8. 启动服务

```bash
# 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

### 9. 数据库初始化

```bash
# 等待数据库启动
sleep 30

# 运行数据库迁移
docker compose -f docker-compose.prod.yml exec taifish python -m flask db upgrade

# 创建管理员用户
docker compose -f docker-compose.prod.yml exec taifish python scripts/show_admin_password.py
```

### 10. 验证部署

```bash
# 检查服务健康状态
curl -f http://localhost/health

# 检查HTTPS
curl -f https://your-domain.com/health

# 查看容器状态
docker ps

# 查看资源使用情况
docker stats
```

## 生产环境优化

### 1. 系统优化

```bash
# 编辑系统限制
sudo nano /etc/security/limits.conf

# 添加以下内容
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536

# 编辑系统参数
sudo nano /etc/sysctl.conf

# 添加以下内容
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 10

# 应用配置
sudo sysctl -p
```

### 2. Docker优化

```bash
# 编辑Docker配置
sudo nano /etc/docker/daemon.json

# 添加以下内容
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}

# 重启Docker
sudo systemctl restart docker
```

### 3. 监控配置

```bash
# 安装监控工具
sudo apt install htop iotop nethogs -y

# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== 系统资源使用情况 ==="
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}'

echo "内存使用率:"
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'

echo "磁盘使用率:"
df -h | grep -E '^/dev/'

echo "=== Docker容器状态 ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "=== 容器资源使用 ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
EOF

chmod +x monitor.sh
```

## 维护操作

### 1. 日常维护

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f taifish

# 重启服务
docker compose -f docker-compose.prod.yml restart taifish

# 更新镜像
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 2. 备份操作

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/taifish/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U taifish_user taifish_prod > $BACKUP_DIR/database_$DATE.sql

# 备份应用数据
docker compose -f docker-compose.prod.yml exec taifish tar -czf - /app/userdata > $BACKUP_DIR/userdata_$DATE.tar.gz

# 清理旧备份 (保留7天)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $DATE"
EOF

chmod +x backup.sh

# 设置定时备份
crontab -e
# 添加: 0 2 * * * /opt/taifish/backup.sh
```

### 3. 日志管理

```bash
# 查看应用日志
docker compose -f docker-compose.prod.yml logs -f taifish

# 查看Nginx日志
docker compose -f docker-compose.prod.yml logs -f nginx

# 清理日志
docker system prune -f
docker volume prune -f
```

### 4. 更新部署

```bash
# 拉取最新代码
cd /opt/taifish
git pull origin main

# 重新构建镜像
docker build -t taifish:latest .

# 滚动更新
docker compose -f docker-compose.prod.yml up -d --no-deps taifish

# 验证更新
curl -f https://your-domain.com/health
```

## 故障排除

### 1. 常见问题

#### 服务无法启动
```bash
# 检查容器状态
docker ps -a

# 查看错误日志
docker compose -f docker-compose.prod.yml logs taifish

# 检查端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

#### 数据库连接失败
```bash
# 检查数据库状态
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U taifish_user

# 检查网络连接
docker compose -f docker-compose.prod.yml exec taifish ping postgres
```

#### SSL证书问题
```bash
# 检查证书文件
ls -la nginx/ssl/

# 验证证书
openssl x509 -in nginx/ssl/cert.pem -text -noout

# 测试SSL连接
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### 2. 性能优化

#### 数据库优化
```sql
-- 连接PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres psql -U taifish_user -d taifish_prod

-- 查看慢查询
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 创建索引
CREATE INDEX CONCURRENTLY idx_accounts_username ON accounts(username);
CREATE INDEX CONCURRENTLY idx_instances_name ON instances(name);
```

#### Redis优化
```bash
# 连接Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli

# 查看内存使用
INFO memory

# 查看键空间
INFO keyspace
```

## 安全建议

### 1. 网络安全
- 使用防火墙限制端口访问
- 配置fail2ban防止暴力攻击
- 定期更新SSL证书

### 2. 应用安全
- 定期更新依赖包
- 使用强密码策略
- 启用审计日志

### 3. 数据安全
- 定期备份数据
- 加密敏感数据
- 限制数据库访问

## 监控告警

### 1. 系统监控
```bash
# 安装监控工具
sudo apt install prometheus-node-exporter -y

# 配置告警
# 可以集成Prometheus + Grafana进行监控
```

### 2. 应用监控
- 使用健康检查端点
- 监控日志文件
- 设置资源使用告警

## 总结

本部署指南提供了完整的Docker生产环境部署方案，包括：

1. **容器化部署**: 主程序打包为Docker镜像
2. **微服务架构**: 使用公共镜像部署数据库和缓存
3. **反向代理**: Nginx处理SSL和负载均衡
4. **数据持久化**: 使用Docker Volumes保存数据
5. **监控维护**: 提供完整的运维工具和脚本

按照本指南部署后，您将获得一个稳定、安全、可扩展的鲸落生产环境。

## 联系支持

如有问题，请参考：
- 项目文档: `/docs/`
- 故障排除: 本文档故障排除部分
- 技术支持: 提交GitHub Issue
