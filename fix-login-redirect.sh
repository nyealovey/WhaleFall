#!/bin/bash

# 修复登录跳转问题的脚本

echo "开始修复登录跳转问题..."

# 1. 检查当前 Flask 应用状态
echo "检查 Flask 应用状态..."
docker ps | grep whalefall_app_prod

if [ $? -ne 0 ]; then
    echo "❌ Flask 应用未运行，请先启动应用"
    exit 1
fi

# 2. 检查 Nginx 配置
echo "检查 Nginx 配置..."
docker exec whalefall_nginx_prod nginx -t

if [ $? -ne 0 ]; then
    echo "❌ Nginx 配置有误"
    exit 1
fi

# 3. 重启 Flask 应用以应用新配置
echo "重启 Flask 应用..."
docker restart whalefall_app_prod

# 等待应用启动
echo "等待应用启动..."
sleep 10

# 4. 检查应用健康状态
echo "检查应用健康状态..."
docker exec whalefall_app_prod curl -f http://localhost:5001/health

if [ $? -eq 0 ]; then
    echo "✅ Flask 应用健康检查通过"
else
    echo "❌ Flask 应用健康检查失败"
    echo "查看应用日志："
    docker logs whalefall_app_prod --tail 20
    exit 1
fi

# 5. 测试登录重定向
echo "测试登录重定向..."
echo "请在浏览器中访问："
echo "  - https://dbinfo.whalefall.local/auth/login"
echo "  - 输入用户名和密码进行登录"
echo "  - 检查是否成功跳转到仪表板"

echo ""
echo "🎉 修复完成！"
echo ""
echo "如果问题仍然存在，请检查："
echo "1. 浏览器开发者工具中的网络请求"
echo "2. Flask 应用日志：docker logs whalefall_app_prod --tail 50"
echo "3. Nginx 访问日志：docker logs whalefall_nginx_prod --tail 20"
