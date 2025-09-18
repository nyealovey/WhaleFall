# 泰摸鱼吧Docker架构设计

## 🏗️ 整体架构

泰摸鱼吧采用微服务架构，通过Docker容器化部署，实现高可用、可扩展的生产环境。

```
┌─────────────────────────────────────────────────────────────────┐
│                        宿主机 (Debian)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Nginx     │  │ Flask App   │  │ PostgreSQL  │  │ Redis   │ │
│  │ 反向代理    │  │ Web应用     │  │ 数据库      │  │ 缓存    │ │
│  │ Port 80/443 │  │ Port 5000   │  │ Port 5432   │  │ Port 6379│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│         │                │                │              │      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Celery      │  │ Celery Beat │  │ 数据卷      │             │
│  │ Worker      │  │ 定时任务    │  │ 持久化存储  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## 🐳 容器设计

### 1. Flask应用容器

**基础镜像**: `ubuntu:22.04`

**特点**:
- 基于Ubuntu 22.04 LTS
- Python 3.11+ 环境
- 非root用户运行
- 健康检查机制
- 资源限制

**Dockerfile关键配置**:
```dockerfile
FROM ubuntu:22.04
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
WORKDIR /app
USER taifish
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

### 2. PostgreSQL数据库容器

**基础镜像**: `postgres:15-alpine`

**特点**:
- 基于PostgreSQL 15
- Alpine Linux轻量级
- 数据持久化
- 自动初始化
- 性能优化配置

**配置优化**:
```sql
-- 内存配置
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB

-- 连接配置
max_connections = 200
```

### 3. Redis缓存容器

**基础镜像**: `redis:7-alpine`

**特点**:
- Redis 7最新版本
- 内存优化配置
- 持久化支持
- 安全认证

**配置优化**:
```conf
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
requirepass Taifish2024!
```

### 4. Nginx反向代理容器

**基础镜像**: `nginx:alpine`

**特点**:
- 轻量级Alpine Linux
- 反向代理配置
- 负载均衡
- SSL终止
- 静态文件服务

## 🔗 网络架构

### Docker网络设计

```yaml
networks:
  taifish_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 服务间通信

| 服务 | 内部IP | 端口 | 协议 | 用途 |
|------|--------|------|------|------|
| Nginx | 172.20.0.10 | 80/443 | HTTP/HTTPS | 外部访问 |
| Flask | 172.20.0.20 | 5000 | HTTP | 应用服务 |
| PostgreSQL | 172.20.0.30 | 5432 | TCP | 数据库 |
| Redis | 172.20.0.40 | 6379 | TCP | 缓存 |

### 端口映射

| 内部端口 | 外部端口 | 服务 | 说明 |
|----------|----------|------|------|
| 80 | 80 | Nginx | HTTP |
| 443 | 443 | Nginx | HTTPS |
| 5432 | 5432 | PostgreSQL | 数据库管理 |
| 6379 | 6379 | Redis | 缓存管理 |

## 💾 存储架构

### 数据卷设计

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/taifish/data/postgres
  
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/taifish/data/redis
  
  app_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/taifish/data/app
```

### 目录结构

```
/opt/taifish/
├── data/
│   ├── postgres/          # PostgreSQL数据
│   ├── redis/             # Redis数据
│   └── app/               # 应用数据
│       ├── logs/          # 日志文件
│       ├── uploads/       # 上传文件
│       ├── exports/       # 导出文件
│       └── backups/       # 备份文件
├── ssl/                   # SSL证书
├── logs/                  # 系统日志
└── backups/               # 数据库备份
```

## 🔄 服务依赖关系

### 启动顺序

```mermaid
graph TD
    A[PostgreSQL] --> B[Redis]
    B --> C[Flask App]
    C --> D[Celery Worker]
    C --> E[Celery Beat]
    C --> F[Nginx]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#fce4ec
```

### 健康检查

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🚀 扩展性设计

### 水平扩展

```bash
# 扩展应用实例
docker compose up -d --scale app=3

# 扩展Celery Worker
docker compose up -d --scale celery_worker=3
```

### 负载均衡配置

```nginx
upstream taifish_app {
    server app:5000;
    server app_2:5000;
    server app_3:5000;
    keepalive 32;
}
```

## 🔒 安全架构

### 网络安全

```yaml
# 网络隔离
networks:
  taifish_network:
    driver: bridge
    internal: false  # 允许外部访问
```

### 容器安全

```dockerfile
# 非root用户
USER taifish

# 只读文件系统
# 资源限制
# 安全扫描
```

### 数据安全

```yaml
# 数据加密
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: crypt
      device: /dev/mapper/encrypted-volume
```

## 📊 监控架构

### 日志收集

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 指标收集

```yaml
# Prometheus配置
labels:
  - "prometheus.io/scrape=true"
  - "prometheus.io/port=5000"
  - "prometheus.io/path=/metrics"
```

## 🔧 配置管理

### 环境变量

```yaml
environment:
  - FLASK_ENV=production
  - DATABASE_URL=postgresql://user:pass@postgres:5432/db
  - REDIS_URL=redis://:pass@redis:6379/0
```

### 配置文件

```yaml
volumes:
  - ./configs/nginx.conf:/etc/nginx/nginx.conf:ro
  - ./configs/postgresql.conf:/etc/postgresql/postgresql.conf:ro
  - ./configs/redis.conf:/usr/local/etc/redis/redis.conf:ro
```

## 🚨 故障恢复

### 自动重启

```yaml
restart: unless-stopped
```

### 数据备份

```bash
# 自动备份脚本
0 2 * * * /opt/taifish/backup.sh
```

### 故障转移

```yaml
# 多实例部署
deploy:
  replicas: 3
  update_config:
    parallelism: 1
    delay: 10s
  restart_policy:
    condition: on-failure
```

## 📈 性能优化

### 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### 缓存策略

```nginx
# 静态文件缓存
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🔄 CI/CD集成

### 构建流程

```yaml
# GitHub Actions
- name: Build Docker Image
  run: docker build -t taifish:${{ github.sha }} .
  
- name: Deploy to Production
  run: |
    docker tag taifish:${{ github.sha }} taifish:latest
    docker compose up -d
```

### 滚动更新

```bash
# 零停机更新
docker compose up -d --no-deps app
```

---

这个Docker架构设计确保了泰摸鱼吧在生产环境中的高可用性、可扩展性和安全性。
