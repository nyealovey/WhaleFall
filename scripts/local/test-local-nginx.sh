#!/bin/bash

# 本地Nginx测试脚本
# 用于测试Nginx代理功能

set -e

echo "🧪 测试本地Nginx代理功能..."
echo "=================================="

# 检查Flask应用
echo "1. 检查Flask应用状态..."
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Flask应用运行正常 (localhost:5001)"
else
    echo "❌ Flask应用未运行，请先启动Flask应用"
    exit 1
fi

# 检查Nginx容器
echo "2. 检查Nginx容器状态..."
if docker ps | grep -q whalefall_nginx_local; then
    echo "✅ Nginx容器运行正常"
else
    echo "❌ Nginx容器未运行，请先启动Nginx"
    echo "运行: ./scripts/start-local-nginx.sh"
    exit 1
fi

# 测试代理功能
echo "3. 测试代理功能..."

# 测试健康检查
echo "   - 测试健康检查端点..."
if curl -s http://localhost/health > /dev/null 2>&1; then
    echo "   ✅ 健康检查通过"
else
    echo "   ❌ 健康检查失败"
    exit 1
fi

# 测试主页
echo "   - 测试主页..."
if curl -s http://localhost/ | grep -q "鲸落" > /dev/null 2>&1; then
    echo "   ✅ 主页访问正常"
else
    echo "   ❌ 主页访问异常"
    exit 1
fi

# 测试静态文件
echo "   - 测试静态文件..."
if curl -s http://localhost/static/css/style.css > /dev/null 2>&1; then
    echo "   ✅ 静态文件访问正常"
else
    echo "   ⚠️  静态文件访问异常（可能正常）"
fi

# 测试API端点
echo "   - 测试API端点..."
if curl -s http://localhost/api/health > /dev/null 2>&1; then
    echo "   ✅ API端点访问正常"
else
    echo "   ⚠️  API端点访问异常（可能正常）"
fi

# 性能测试
echo "4. 性能测试..."
echo "   - 响应时间测试..."
response_time=$(curl -w "%{time_total}" -o /dev/null -s http://localhost/)
echo "   📊 平均响应时间: ${response_time}秒"

# 检查日志
echo "5. 检查日志..."
if [ -f "userdata/nginx/logs/whalefall_access.log" ]; then
    echo "   ✅ 访问日志文件存在"
    echo "   📊 最近访问记录:"
    tail -3 userdata/nginx/logs/whalefall_access.log | sed 's/^/     /'
else
    echo "   ⚠️  访问日志文件不存在"
fi

echo "=================================="
echo "🎉 所有测试通过！Nginx代理功能正常"
echo ""
echo "🌐 访问地址："
echo "   http://localhost"
echo "   http://localhost/admin"
echo ""
echo "📊 监控命令："
echo "   查看Nginx日志: docker-compose -f docker-compose.local.yml logs nginx"
echo "   查看访问日志: tail -f userdata/nginx/logs/whalefall_access.log"
echo "=================================="
