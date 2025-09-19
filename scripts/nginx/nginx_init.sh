#!/bin/bash
# Nginx初始化脚本
# 在容器启动时自动写入配置

set -e

# 日志函数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
}

# 获取环境变量
NGINX_ENV=${NGINX_ENV:-"dev"}
NGINX_CONFIG_PATH="/etc/nginx/conf.d/default.conf"

log_info "开始初始化Nginx配置 (环境: $NGINX_ENV)"

# 根据环境选择配置文件
case "$NGINX_ENV" in
    "dev")
        log_info "使用开发环境配置"
        cat > "$NGINX_CONFIG_PATH" << 'EOF'
# 鲸落开发环境 Nginx 配置
# 仅支持HTTP，不启用HTTPS

upstream whalefall_backend {
    server whalefall_app_dev:5001;
}

server {
    listen 80;
    server_name localhost;

    # 客户端最大请求体大小
    client_max_body_size 16M;

    # 日志配置
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # 主应用代理
    location / {
        proxy_pass http://whalefall_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;

        # 当后端不可用时，返回503状态
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }

    # 静态文件缓存
    location /static/ {
        proxy_pass http://whalefall_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }

    # 健康检查
    location /health {
        access_log off;
        return 200 "Nginx is running (Dev)\n";
        add_header Content-Type text/plain;
    }

    # 回退页面（当Flask应用不可用时）
    location @fallback {
        return 503 "Service temporarily unavailable. Please wait for Flask application to start.\n";
        add_header Content-Type text/plain;
    }
}
EOF
        ;;
    "prod")
        log_info "使用生产环境配置"
        cat > "$NGINX_CONFIG_PATH" << 'EOF'
# 鲸落生产环境 Nginx 配置
# 支持HTTP和HTTPS，HTTP重定向到HTTPS

upstream whalefall_backend {
    server whalefall_app_prod:5001;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name localhost; # 可以替换为你的域名，例如 example.com *.example.com

    return 301 https://$host$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name localhost; # 可以替换为你的域名，例如 example.com *.example.com

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # 客户端最大请求体大小
    client_max_body_size 16M;

    # 日志配置
    access_log /var/log/nginx/ssl_access.log;
    error_log /var/log/nginx/ssl_error.log;

    # 主应用代理
    location / {
        proxy_pass http://whalefall_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;

        # 当后端不可用时，返回503状态
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }

    # 静态文件缓存
    location /static/ {
        proxy_pass http://whalefall_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }

    # 健康检查
    location /health {
        access_log off;
        return 200 "Nginx is running (Prod HTTPS)\n";
        add_header Content-Type text/plain;
    }

    # 回退页面（当Flask应用不可用时）
    location @fallback {
        return 503 "Service temporarily unavailable. Please wait for Flask application to start.\n";
        add_header Content-Type text/plain;
    }
}
EOF
        ;;
    *)
        log_warning "未知环境 '$NGINX_ENV'，使用默认配置"
        # 保持默认配置不变
        ;;
esac

# 测试Nginx配置
log_info "测试Nginx配置语法..."
if nginx -t; then
    log_success "Nginx配置语法正确"
else
    log_error "Nginx配置语法错误"
    exit 1
fi

log_success "Nginx初始化完成"
