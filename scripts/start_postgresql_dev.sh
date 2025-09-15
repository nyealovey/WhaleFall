#!/bin/bash

# 泰摸鱼吧PostgreSQL开发环境启动脚本

echo "=========================================="
echo "泰摸鱼吧PostgreSQL开发环境启动脚本"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查docker-compose文件是否存在
if [ ! -f "docker-compose.dev.yml" ]; then
    echo "错误: docker-compose.dev.yml 文件不存在"
    exit 1
fi

echo "1. 启动PostgreSQL和Redis容器..."
docker-compose -f docker-compose.dev.yml up -d

# 等待容器启动
echo "2. 等待容器启动..."
sleep 10

# 检查容器状态
echo "3. 检查容器状态..."
docker-compose -f docker-compose.dev.yml ps

# 检查PostgreSQL连接
echo "4. 检查PostgreSQL连接..."
docker exec taifish_postgres_dev pg_isready -U taifish_user -d taifish_dev

if [ $? -eq 0 ]; then
    echo "   ✓ PostgreSQL连接正常"
else
    echo "   ✗ PostgreSQL连接失败"
    exit 1
fi

# 检查Redis连接
echo "5. 检查Redis连接..."
docker exec taifish_redis_dev redis-cli -a Taifish2024! ping

if [ $? -eq 0 ]; then
    echo "   ✓ Redis连接正常"
else
    echo "   ✗ Redis连接失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "容器启动完成!"
echo "=========================================="
echo ""
echo "PostgreSQL信息:"
echo "  主机: localhost"
echo "  端口: 5432"
echo "  数据库: taifish_dev"
echo "  用户: taifish_user"
echo "  密码: Taifish2024!"
echo ""
echo "Redis信息:"
echo "  主机: localhost"
echo "  端口: 6379"
echo "  密码: Taifish2024!"
echo ""
echo "下一步:"
echo "1. 运行数据库迁移: python scripts/simple_migrate.py"
echo "2. 启动应用: python app.py"
echo ""
