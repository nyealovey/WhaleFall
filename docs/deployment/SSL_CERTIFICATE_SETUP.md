# SSL证书设置指南

## 🎯 概述

本指南介绍如何为本地开发环境设置SSL证书，实现HTTPS访问，让开发环境更接近生产环境。

## 🔐 SSL证书类型

### 1. 自签名证书（推荐用于开发）
- **优点**: 免费、快速生成、支持本地域名
- **缺点**: 浏览器会显示安全警告
- **适用场景**: 本地开发、测试环境

### 2. Let's Encrypt证书（生产环境）
- **优点**: 免费、浏览器信任、自动续期
- **缺点**: 需要公网域名、定期续期
- **适用场景**: 生产环境、公网访问

### 3. 商业证书（企业环境）
- **优点**: 高信任度、技术支持
- **缺点**: 费用较高、需要验证
- **适用场景**: 企业生产环境

## 🚀 快速开始

### 1. 生成自签名证书

```bash
# 生成SSL证书
./scripts/generate-ssl-cert.sh

# 或使用证书管理器
./scripts/ssl-manager.sh generate
```

### 2. 启动HTTPS服务

```bash
# 启动Nginx代理（自动检查证书）
./scripts/start-local-nginx.sh
```

### 3. 访问HTTPS应用

- **HTTPS访问**: https://localhost
- **管理界面**: https://localhost/admin
- **自定义域名**: https://whalefall.local

## 📁 证书文件结构

```
nginx/local/ssl/
├── cert.pem          # SSL证书文件
├── key.pem           # 私钥文件
├── cert.csr          # 证书签名请求
└── openssl.conf      # OpenSSL配置文件
```

## ⚙️ 证书配置详情

### 证书信息

- **证书类型**: 自签名证书
- **有效期**: 365天
- **密钥长度**: 2048位RSA
- **签名算法**: SHA256
- **支持的域名**:
  - `localhost`
  - `*.localhost`
  - `whalefall.local`
  - `*.whalefall.local`
  - `127.0.0.1`
  - `::1`

### SSL配置

```nginx
# SSL协议版本
ssl_protocols TLSv1.2 TLSv1.3;

# 加密套件
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;

# 会话配置
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;
```

## 🔧 证书管理

### 生成证书

```bash
# 生成新证书
./scripts/ssl-manager.sh generate

# 检查证书状态
./scripts/ssl-manager.sh check

# 显示证书信息
./scripts/ssl-manager.sh info
```

### 续期证书

```bash
# 续期证书
./scripts/ssl-manager.sh renew

# 清理旧证书
./scripts/ssl-manager.sh clean
```

### 安装到系统信任库

```bash
# 安装证书到系统信任库
./scripts/ssl-manager.sh install
```

## 🌐 域名配置

### 1. 配置hosts文件

#### macOS/Linux
```bash
# 编辑hosts文件
sudo vim /etc/hosts

# 添加以下行
127.0.0.1 localhost
127.0.0.1 whalefall.local
```

#### Windows
```cmd
# 以管理员身份运行记事本
notepad C:\Windows\System32\drivers\etc\hosts

# 添加以下行
127.0.0.1 localhost
127.0.0.1 whalefall.local
```

### 2. 验证域名解析

```bash
# 测试域名解析
ping localhost
ping whalefall.local

# 测试HTTPS访问
curl -k https://localhost/health
curl -k https://whalefall.local/health
```

## 🔒 安全配置

### 1. 安全头设置

```nginx
# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# 防止点击劫持
add_header X-Frame-Options DENY always;

# 防止MIME类型嗅探
add_header X-Content-Type-Options nosniff always;

# XSS保护
add_header X-XSS-Protection "1; mode=block" always;

# 引用者策略
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 2. 证书安全

```bash
# 设置正确的文件权限
chmod 600 nginx/local/ssl/key.pem
chmod 644 nginx/local/ssl/cert.pem

# 定期检查证书有效期
./scripts/ssl-manager.sh check
```

## 🧪 测试和验证

### 1. 证书验证

```bash
# 验证证书格式
openssl x509 -in nginx/local/ssl/cert.pem -text -noout

# 验证私钥格式
openssl rsa -in nginx/local/ssl/key.pem -check

# 验证证书和私钥匹配
openssl x509 -noout -modulus -in nginx/local/ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in nginx/local/ssl/key.pem | openssl md5
```

### 2. HTTPS功能测试

```bash
# 测试HTTPS连接
curl -k https://localhost/health

# 测试SSL握手
openssl s_client -connect localhost:443 -servername localhost

# 测试证书链
openssl s_client -connect localhost:443 -showcerts
```

### 3. 浏览器测试

1. 打开浏览器访问 https://localhost
2. 点击地址栏的"不安全"警告
3. 点击"高级" -> "继续访问"
4. 验证页面正常加载

## 🐛 故障排除

### 常见问题

#### 1. 证书生成失败

**症状**: `openssl: command not found`

**解决方案**:
```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# CentOS/RHEL
sudo yum install openssl
```

#### 2. 浏览器安全警告

**症状**: "您的连接不是私密连接"

**解决方案**:
1. 点击"高级"
2. 点击"继续访问localhost（不安全）"
3. 或安装证书到系统信任库

#### 3. 证书过期

**症状**: `certificate has expired`

**解决方案**:
```bash
# 检查证书有效期
./scripts/ssl-manager.sh info

# 续期证书
./scripts/ssl-manager.sh renew
```

#### 4. 域名不匹配

**症状**: `certificate doesn't match`

**解决方案**:
1. 检查hosts文件配置
2. 使用正确的域名访问
3. 重新生成包含正确域名的证书

### 日志分析

```bash
# 查看Nginx SSL日志
docker-compose -f docker-compose.local.yml logs nginx | grep ssl

# 查看SSL错误日志
tail -f userdata/nginx/logs/whalefall_ssl_error.log

# 查看SSL访问日志
tail -f userdata/nginx/logs/whalefall_ssl_access.log
```

## 📊 性能优化

### 1. SSL性能优化

```nginx
# 启用SSL会话缓存
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# 启用OCSP装订
ssl_stapling on;
ssl_stapling_verify on;

# 优化SSL缓冲区
ssl_buffer_size 8k;
```

### 2. 证书优化

```bash
# 使用更短的证书链
openssl x509 -in cert.pem -outform PEM -out cert_short.pem

# 启用HTTP/2
listen 443 ssl http2;
```

## 🔄 自动化管理

### 1. 证书自动续期

```bash
# 创建定时任务
crontab -e

# 添加以下行（每月检查一次）
0 0 1 * * /path/to/scripts/ssl-manager.sh check && /path/to/scripts/ssl-manager.sh renew
```

### 2. 监控脚本

```bash
#!/bin/bash
# 证书监控脚本
if ! ./scripts/ssl-manager.sh check; then
    echo "SSL证书异常，正在续期..."
    ./scripts/ssl-manager.sh renew
    docker-compose -f docker-compose.local.yml restart nginx
fi
```

## 🌍 生产环境迁移

### 1. Let's Encrypt证书

```bash
# 安装certbot
sudo apt-get install certbot

# 生成证书
sudo certbot certonly --standalone -d yourdomain.com

# 配置自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. 商业证书

1. 购买SSL证书
2. 生成CSR文件
3. 提交给CA验证
4. 下载证书文件
5. 配置到Nginx

## 📚 相关文档

- [本地Nginx设置指南](LOCAL_NGINX_SETUP.md)
- [生产环境部署指南](PRODUCTION_DEPLOYMENT.md)
- [Docker生产环境部署](DOCKER_PRODUCTION_DEPLOYMENT.md)
- [Nginx配置最佳实践](NGINX_BEST_PRACTICES.md)

## 🤝 贡献

如果您发现任何问题或有改进建议，请：

1. 创建Issue描述问题
2. 提交Pull Request
3. 更新相关文档

---

**注意**: 本配置仅用于本地开发环境，生产环境请使用受信任的SSL证书。
