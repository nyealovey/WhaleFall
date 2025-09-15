#!/bin/bash

# 泰摸鱼吧PostgreSQL完整设置脚本

echo "=========================================="
echo "泰摸鱼吧PostgreSQL完整设置脚本"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查必要文件
if [ ! -f "docker-compose.dev.yml" ]; then
    echo "错误: docker-compose.dev.yml 文件不存在"
    exit 1
fi

if [ ! -f "scripts/accurate_migrate.py" ]; then
    echo "错误: 迁移脚本不存在"
    exit 1
fi

echo "1. 设置环境配置..."
source .venv/bin/activate
python scripts/setup_postgresql_env.py

echo ""
echo "2. 启动PostgreSQL和Redis容器..."
docker-compose -f docker-compose.dev.yml up -d

# 等待容器启动
echo ""
echo "3. 等待容器启动..."
sleep 15

# 检查容器状态
echo ""
echo "4. 检查容器状态..."
docker-compose -f docker-compose.dev.yml ps

# 检查PostgreSQL连接
echo ""
echo "5. 检查PostgreSQL连接..."
for i in {1..10}; do
    if docker exec taifish_postgres_dev pg_isready -U taifish_user -d taifish_dev > /dev/null 2>&1; then
        echo "   ✓ PostgreSQL连接正常"
        break
    else
        echo "   等待PostgreSQL启动... ($i/10)"
        sleep 3
    fi
done

# 检查Redis连接
echo ""
echo "6. 检查Redis连接..."
for i in {1..5}; do
    if docker exec taifish_redis_dev redis-cli -a Taifish2024! ping > /dev/null 2>&1; then
        echo "   ✓ Redis连接正常"
        break
    else
        echo "   等待Redis启动... ($i/5)"
        sleep 2
    fi
done

echo ""
echo "7. 创建PostgreSQL表结构..."
# 激活虚拟环境并运行Flask应用来创建表结构
source .venv/bin/activate
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('   ✓ 表结构创建完成')
"

echo ""
echo "8. 迁移数据..."
python scripts/accurate_migrate.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "设置完成!"
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
echo "1. 启动应用: python app.py"
echo "2. 访问: http://localhost:5000"
echo ""
echo "性能监控工具:"
echo "1. 查看数据库统计: python scripts/monitor_postgresql.py"
echo "2. 持续监控: python scripts/monitor_postgresql.py --continuous"
echo "3. 查看慢查询: python scripts/monitor_postgresql.py --slow-threshold 500"
echo "4. 查看日志: python scripts/view_postgresql_logs.py"
echo "5. 实时跟踪日志: python scripts/view_postgresql_logs.py --follow"
echo ""
else
    echo ""
    echo "=========================================="
    echo "设置失败!"
    echo "=========================================="
    echo "请检查错误信息并重试"
    exit 1
fi
