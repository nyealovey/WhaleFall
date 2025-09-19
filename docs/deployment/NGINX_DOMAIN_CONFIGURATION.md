# Nginx 域名配置指南

本文档详细介绍了鲸落数据管理平台的 Nginx 域名配置，包括多域名支持、HTTPS 重定向和日志管理。

## 1. 支持的域名

### 1.1. 主要域名
- `localhost` - 本地开发访问
- `domain.com` - 生产环境主域名
- `*.domain.com` - 通配符域名支持

### 1.2. 协议支持
- **localhost**: 支持 HTTP 和 HTTPS 双协议
- **域名**: 仅支持 HTTPS，HTTP 自动重定向到 HTTPS

## 2. 配置结构

### 2.1. HTTP 配置
```nginx
# HTTP 重定向到 HTTPS (仅对域名)
server {
    listen 80;
    server_name domain.com *.domain.com;
    
    # 重定向所有 HTTP 请求到 HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTP 配置 (localhost 保持 HTTP 访问)
server {
    listen 80;
    server_name localhost;
    
    # ... 其他配置
}
```

### 2.2. HTTPS 配置
```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name localhost domain.com *.domain.com;
    
    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/whale.pem;
    ssl_certificate_key /etc/nginx/ssl/whale.key;
    
    # ... 其他配置
}
```

## 3. SSL 证书配置

### 3.1. 证书文件位置
- 证书文件: `/etc/nginx/ssl/whale.pem`
- 私钥文件: `/etc/nginx/ssl/whale.key`
- 本地映射: `./userdata/nginx/ssl/`

### 3.2. 证书更新
```bash
# 停止 Nginx
docker stop whalefall_nginx_prod

# 更新证书文件
cp new_cert.pem ./userdata/nginx/ssl/whale.pem
cp new_key.key ./userdata/nginx/ssl/whale.key

# 重启 Nginx
docker start whalefall_nginx_prod
```

## 4. 日志管理

### 4.1. 日志文件分类
- **通用访问日志**: `/var/log/nginx/access.log`
- **通用错误日志**: `/var/log/nginx/error.log`
- **HTTPS 访问日志**: `/var/log/nginx/ssl_access.log`
- **HTTPS 错误日志**: `/var/log/nginx/ssl_error.log`
- **域名特定日志**: `/var/log/nginx/domain_access.log`

### 4.2. 日志轮转配置
```bash
# 查看日志
docker exec whalefall_nginx_prod tail -f /var/log/nginx/access.log

# 清理旧日志
docker exec whalefall_nginx_prod find /var/log/nginx -name "*.log" -mtime +7 -delete
```

## 5. 域名配置更新

### 5.1. 使用脚本更新
```bash
# 更新域名配置
./scripts/nginx/update-domain-config.sh
```

### 5.2. 手动更新
```bash
# 1. 编辑配置文件
vim nginx/conf.d/whalefall-docker.conf

# 2. 重启 Nginx 容器
docker restart whalefall_nginx_prod

# 3. 验证配置
docker exec whalefall_nginx_prod nginx -t
```

## 6. 访问测试

### 6.1. 本地访问测试
```bash
# HTTP 访问
curl -I http://localhost/health

# HTTPS 访问
curl -I -k https://localhost/health
```

### 6.2. 域名访问测试
```bash
# 测试 HTTP 重定向
curl -I http://domain.com/health

# 测试 HTTPS 访问
curl -I https://domain.com/health
```

## 7. 故障排查

### 7.1. 常见问题

#### 域名无法访问
- 检查 DNS 解析是否正确
- 确认防火墙端口 80/443 已开放
- 验证 SSL 证书是否有效

#### HTTPS 证书错误
- 检查证书文件是否存在
- 验证证书是否过期
- 确认证书与域名匹配

#### 重定向循环
- 检查 server_name 配置
- 验证 proxy_set_header 设置
- 确认 upstream 配置正确

### 7.2. 调试命令
```bash
# 检查 Nginx 配置语法
docker exec whalefall_nginx_prod nginx -t

# 查看 Nginx 错误日志
docker exec whalefall_nginx_prod tail -f /var/log/nginx/error.log

# 检查端口监听
docker exec whalefall_nginx_prod netstat -tlnp

# 测试 SSL 证书
openssl s_client -connect domain.com:443 -servername domain.com
```

## 8. 安全配置

### 8.1. SSL 安全设置
- 仅支持 TLS 1.2 和 TLS 1.3
- 使用强加密套件
- 启用 HSTS (可选)

### 8.2. 访问控制
- 限制请求大小: `client_max_body_size 16M`
- 设置超时时间: `proxy_connect_timeout 5s`
- 启用错误页面: 自定义 404/50x 页面

## 9. 性能优化

### 9.1. 缓存配置
- 静态文件缓存: `expires 1y`
- 启用 gzip 压缩
- 设置适当的缓冲区大小

### 9.2. 连接优化
- 启用 HTTP/2
- 设置 keepalive 连接
- 优化 worker 进程数

## 10. 监控和维护

### 10.1. 健康检查
```bash
# 检查 Nginx 状态
docker ps | grep whalefall_nginx_prod

# 检查端口监听
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

### 10.2. 定期维护
- 定期更新 SSL 证书
- 清理旧日志文件
- 监控访问日志异常
- 检查错误日志

## 11. 配置示例

### 11.1. 添加新域名
```nginx
server {
    listen 80;
    server_name newdomain.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name newdomain.example.com;
    
    ssl_certificate /etc/nginx/ssl/whale.pem;
    ssl_certificate_key /etc/nginx/ssl/whale.key;
    
    # ... 其他配置
}
```

### 11.2. 自定义错误页面
```nginx
error_page 404 /404.html;
error_page 500 502 503 504 /50x.html;

location = /404.html {
    root /etc/nginx/error_pages;
    internal;
}
```

---

**注意**: 修改域名配置后，需要重启 Nginx 容器才能生效。建议使用提供的脚本进行配置更新，以确保配置正确性和服务可用性。
