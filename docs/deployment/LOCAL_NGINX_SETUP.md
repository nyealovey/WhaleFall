# 本地Nginx代理设置指南

## 🎯 概述

本指南介绍如何在本地开发环境中设置Nginx Docker服务，用于代理本地运行的Flask应用，使开发环境更接近生产环境。

## 🏗️ 架构图

```
┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   Flask App     │
│   (Docker)      │◄──►│   (本地运行)     │
│   Port: 80      │    │   Port: 5001    │
│   localhost     │    │   localhost     │
└─────────────────┘    └─────────────────┘
```

## 📋 前置条件

1. **Docker已安装** - 用于运行Nginx容器
2. **Flask应用运行中** - 在localhost:5001端口运行
3. **数据库服务** - PostgreSQL和Redis服务运行中

## 🚀 快速开始

### 1. 启动Flask应用

```bash
# 方式1：直接运行
python app.py

# 方式2：使用uv
uv run python app.py

# 方式3：使用环境变量
FLASK_PORT=5001 python app.py
```

### 2. 启动Nginx代理

```bash
# 使用启动脚本（推荐）
./scripts/start-local-nginx.sh

# 或手动启动
docker-compose -f docker-compose.local.yml up -d
```

### 3. 访问应用

- **通过Nginx代理**: http://localhost
- **直接访问Flask**: http://localhost:5001
- **管理界面**: http://localhost/admin

## 📁 文件结构

```
TaifishV4/
├── docker-compose.local.yml          # 本地Nginx Docker配置
├── nginx/local/conf.d/whalefall.conf # Nginx配置文件
├── scripts/start-local-nginx.sh      # 启动脚本
└── userdata/nginx/logs/              # Nginx日志目录
```

## ⚙️ 配置说明

### Nginx配置特点

- **代理目标**: `host.docker.internal:5001`
- **备用服务器**: `127.0.0.1:5001`
- **静态文件缓存**: 1年过期时间
- **API超时**: 30秒
- **访问日志**: 记录到 `userdata/nginx/logs/`

### 关键配置项

```nginx
upstream whalefall_backend {
    server host.docker.internal:5001;
    server 127.0.0.1:5001 backup;
}
```

## 🔧 管理命令

### 启动服务

```bash
# 启动Nginx
docker-compose -f docker-compose.local.yml up -d

# 查看状态
docker-compose -f docker-compose.local.yml ps
```

### 查看日志

```bash
# 查看Nginx日志
docker-compose -f docker-compose.local.yml logs nginx

# 实时查看日志
docker-compose -f docker-compose.local.yml logs -f nginx

# 查看访问日志
tail -f userdata/nginx/logs/whalefall_access.log
```

### 停止服务

```bash
# 停止Nginx
docker-compose -f docker-compose.local.yml down

# 停止并删除数据卷
docker-compose -f docker-compose.local.yml down -v
```

### 重启服务

```bash
# 重启Nginx
docker-compose -f docker-compose.local.yml restart

# 重新构建并启动
docker-compose -f docker-compose.local.yml up -d --build
```

## 🧪 测试功能

### 1. 健康检查

```bash
# 检查Flask应用
curl http://localhost:5001/health

# 检查Nginx代理
curl http://localhost/health
```

### 2. 功能测试

```bash
# 测试主页
curl http://localhost/

# 测试API
curl http://localhost/api/health

# 测试管理界面
curl http://localhost/admin
```

### 3. 性能测试

```bash
# 使用ab进行简单压力测试
ab -n 100 -c 10 http://localhost/

# 使用curl测试响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/
```

## 🐛 故障排除

### 常见问题

#### 1. Nginx无法连接到Flask应用

**症状**: 502 Bad Gateway 或 503 Service Unavailable

**解决方案**:
```bash
# 检查Flask应用是否运行
curl http://localhost:5001/health

# 检查Docker网络
docker network ls
docker network inspect taifishv4_whalefall_local_network
```

#### 2. 端口冲突

**症状**: Port already in use

**解决方案**:
```bash
# 检查端口占用
lsof -i :80
lsof -i :443

# 停止占用端口的服务
sudo lsof -ti:80 | xargs kill -9
```

#### 3. 权限问题

**症状**: Permission denied

**解决方案**:
```bash
# 修复脚本权限
chmod +x scripts/start-local-nginx.sh

# 修复目录权限
sudo chown -R $USER:$USER userdata/nginx/
```

### 日志分析

```bash
# 查看Nginx错误日志
docker-compose -f docker-compose.local.yml logs nginx | grep error

# 查看访问日志
tail -f userdata/nginx/logs/whalefall_access.log

# 查看Flask应用日志
tail -f userdata/logs/app.log
```

## 🔒 安全配置

### 1. 限制访问

```nginx
# 限制特定IP访问管理界面
location /admin {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://whalefall_backend;
}
```

### 2. 启用HTTPS

```bash
# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/local/ssl/key.pem \
    -out nginx/local/ssl/cert.pem

# 取消注释HTTPS配置
# 编辑 nginx/local/conf.d/whalefall.conf
```

## 📊 监控和性能

### 1. 资源监控

```bash
# 查看容器资源使用
docker stats whalefall_nginx_local

# 查看系统资源
htop
```

### 2. 性能优化

- **启用gzip压缩**
- **配置静态文件缓存**
- **调整worker进程数**
- **优化proxy缓冲设置**

## 🎯 生产环境对比

| 特性 | 本地开发 | 生产环境 |
|------|----------|----------|
| Nginx | Docker容器 | Docker容器 |
| Flask | 本地进程 | Docker容器 |
| 数据库 | 本地/远程 | Docker容器 |
| 缓存 | 本地/远程 | Docker容器 |
| 日志 | 本地文件 | 集中日志 |

## 📚 相关文档

- [生产环境部署指南](PRODUCTION_DEPLOYMENT.md)
- [Docker生产环境部署](DOCKER_PRODUCTION_DEPLOYMENT.md)
- [Nginx配置最佳实践](NGINX_BEST_PRACTICES.md)

## 🤝 贡献

如果您发现任何问题或有改进建议，请：

1. 创建Issue描述问题
2. 提交Pull Request
3. 更新相关文档

---

**注意**: 本配置仅用于本地开发环境，生产环境请使用完整的Docker Compose配置。
