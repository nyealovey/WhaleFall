#!/bin/bash

# Nginx 配置补丁脚本
# 用于添加 dbinfo.whalefall.local 域名支持

echo "开始应用 Nginx 配置补丁..."

# 备份原始配置文件
cp /opt/whalefall/nginx/conf.d/whalefall-docker.conf /opt/whalefall/nginx/conf.d/whalefall-docker.conf.backup
echo "✅ 已备份原始配置文件"

# 创建新的配置文件
cat > /opt/whalefall/nginx/conf.d/whalefall-docker.conf << 'EOF'
# Nginx配置 - Docker环境
# 用于Flask应用在Docker容器中运行的情况

# 定义upstream，包含fallback机制
upstream whalefall_backend {
    server whalefall:5001 max_fails=3 fail_timeout=30s;
    # 当whalefall不可用时，使用backup服务器
    server 127.0.0.1:8080 backup;
}

# HTTP 重定向到 HTTPS (仅对 dbinfo.whalefall.local)
server {
    listen 80;
    server_name dbinfo.whalefall.local;
    
    # HTTP 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTP 配置 (仅对 localhost)
server {
    listen 80;
    server_name localhost;
    
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
        
        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # 当后端不可用时，返回503状态
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 静态文件代理
    location /static/ {
        proxy_pass http://whalefall_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://whalefall_backend;
        access_log off;
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 回退页面（当Flask应用不可用时）
    location @fallback {
        return 503 "Service temporarily unavailable. Please wait for Flask application to start.\n";
        add_header Content-Type text/plain;
    }
}

# HTTPS配置
server {
    listen 443 ssl;
    http2 on;
    server_name localhost dbinfo.whalefall.local;
    
    # SSL证书配置
    ssl_certificate /etc/nginx/ssl/whale.pem;
    ssl_certificate_key /etc/nginx/ssl/whale.key;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
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
        
        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # 当后端不可用时，返回503状态
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 静态文件代理
    location /static/ {
        proxy_pass http://whalefall_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://whalefall_backend;
        access_log off;
        proxy_intercept_errors on;
        error_page 502 503 504 = @fallback;
    }
    
    # 回退页面（当Flask应用不可用时）
    location @fallback {
        return 503 "Service temporarily unavailable. Please wait for Flask application to start.\n";
        add_header Content-Type text/plain;
    }
}
EOF

echo "✅ 已更新 Nginx 配置文件"

# 测试 Nginx 配置
echo "测试 Nginx 配置..."
docker exec whalefall_nginx_prod nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置测试通过"
    
    # 重新加载 Nginx 配置
    echo "重新加载 Nginx 配置..."
    docker exec whalefall_nginx_prod nginx -s reload
    
    if [ $? -eq 0 ]; then
        echo "✅ Nginx 配置重新加载成功"
        echo ""
        echo "🎉 配置完成！现在可以使用以下方式访问："
        echo "  - https://dbinfo.whalefall.local/ (HTTPS)"
        echo "  - http://dbinfo.whalefall.local/ (自动重定向到 HTTPS)"
        echo "  - http://localhost/ (本地访问)"
    else
        echo "❌ Nginx 配置重新加载失败"
        echo "正在恢复备份配置..."
        cp /opt/whalefall/nginx/conf.d/whalefall-docker.conf.backup /opt/whalefall/nginx/conf.d/whalefall-docker.conf
        docker exec whalefall_nginx_prod nginx -s reload
        exit 1
    fi
else
    echo "❌ Nginx 配置测试失败"
    echo "正在恢复备份配置..."
    cp /opt/whalefall/nginx/conf.d/whalefall-docker.conf.backup /opt/whalefall/nginx/conf.d/whalefall-docker.conf
    exit 1
fi

echo ""
echo "📋 配置文件位置："
echo "  - 主配置：/opt/whalefall/nginx/conf.d/whalefall-docker.conf"
echo "  - 备份：/opt/whalefall/nginx/conf.d/whalefall-docker.conf.backup"
