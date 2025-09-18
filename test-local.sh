#!/bin/bash

echo "🐟 鲸落 - 本地测试脚本"
echo "================================"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

echo "✅ Docker环境检查通过"

# 构建镜像
echo "🔨 构建主程序镜像..."
docker build -f Dockerfile.prod -t taifish:latest .

if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功"
else
    echo "❌ 镜像构建失败"
    exit 1
fi

# 启动服务
echo "🚀 启动测试服务..."
docker compose -f docker-compose.test.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker compose -f docker-compose.test.yml ps

# 检查健康状态
echo "🏥 检查健康状态..."
curl -f http://localhost:8080/health

if [ $? -eq 0 ]; then
    echo "✅ 服务健康检查通过"
else
    echo "❌ 服务健康检查失败"
fi

# 显示管理员密码
echo "🔑 获取管理员密码..."
docker compose -f docker-compose.test.yml exec taifish python scripts/show_admin_password.py

echo "================================"
echo "🌐 访问地址: http://localhost:8080"
echo "📊 管理界面: http://localhost:8080/admin"
echo "================================"
