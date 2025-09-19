#!/bin/bash

# 本地Nginx启动脚本
# 用于在本地开发环境中启动Nginx代理服务

set -e

echo "🐟 启动本地Nginx代理服务..."
echo "=================================="

# 检查Flask应用是否运行
echo "📡 检查Flask应用状态..."
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Flask应用正在运行 (localhost:5001)"
else
    echo "❌ Flask应用未运行，请先启动Flask应用："
    echo "   python app.py"
    echo "   或"
    echo "   uv run python app.py"
    exit 1
fi

# 检查SSL证书
echo "🔐 检查SSL证书状态..."
if [ -f "nginx/local/ssl/cert.pem" ] && [ -f "nginx/local/ssl/key.pem" ]; then
    echo "✅ SSL证书已存在"
    # 检查证书是否有效
    if openssl x509 -in nginx/local/ssl/cert.pem -checkend 0 > /dev/null 2>&1; then
        echo "✅ SSL证书有效"
    else
        echo "⚠️  SSL证书已过期，正在重新生成..."
        ./scripts/ssl-manager.sh generate
    fi
else
    echo "⚠️  SSL证书不存在，正在生成..."
    ./scripts/ssl-manager.sh generate
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p userdata/nginx/logs
mkdir -p nginx/local/ssl

# 启动Nginx容器
echo "🚀 启动Nginx容器..."
docker-compose -f docker-compose.local.yml up -d

# 等待Nginx启动
echo "⏳ 等待Nginx启动..."
sleep 5

# 检查Nginx状态
echo "🔍 检查Nginx状态..."
if docker ps | grep -q whalefall_nginx_local; then
    echo "✅ Nginx容器已启动"
else
    echo "❌ Nginx容器启动失败"
    docker-compose -f docker-compose.local.yml logs nginx
    exit 1
fi

# 测试代理功能
echo "🧪 测试代理功能..."

# 测试HTTP代理（应该重定向到HTTPS）
echo "   - 测试HTTP重定向..."
if curl -s -I http://localhost/health | grep -q "301\|302"; then
    echo "   ✅ HTTP重定向正常"
else
    echo "   ⚠️  HTTP重定向异常（可能正常）"
fi

# 测试HTTPS代理
echo "   - 测试HTTPS代理..."
if curl -s -k https://localhost/health > /dev/null 2>&1; then
    echo "   ✅ HTTPS代理正常"
else
    echo "   ❌ HTTPS代理异常"
    echo "请检查Nginx日志："
    echo "docker-compose -f docker-compose.local.yml logs nginx"
    exit 1
fi

echo "=================================="
echo "🎉 本地Nginx代理服务启动成功！"
echo ""
echo "🌐 访问地址："
echo "   https://localhost"
echo "   https://localhost/admin"
echo "   https://whalefall.local (需要配置hosts文件)"
echo ""
echo "📊 管理命令："
echo "   查看日志: docker-compose -f docker-compose.local.yml logs nginx"
echo "   停止服务: docker-compose -f docker-compose.local.yml down"
echo "   重启服务: docker-compose -f docker-compose.local.yml restart"
echo "=================================="
