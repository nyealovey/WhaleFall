#!/bin/bash
# 泰摸鱼吧 - 环境变量设置脚本

echo "🐟 设置泰摸鱼吧环境变量..."

# 检查 .env.dev 文件
if [ ! -f .env.dev ]; then
    echo "📝 创建 .env.dev 文件..."
    cp env.example .env.dev
    echo "✅ .env.dev 文件已创建"
else
    echo "✅ .env.dev 文件已存在"
fi

# 设置环境变量
export REDIS_URL="redis://:Taifish2024!@localhost:6379/0"
export CACHE_REDIS_URL="redis://:Taifish2024!@localhost:6379/0"
export DATABASE_URL="postgresql://taifish_user:Taifish2024!@localhost:5432/taifish_dev"

echo "✅ 环境变量已设置"
echo "🔴 Redis URL: $REDIS_URL"
echo "🗄️  Database URL: $DATABASE_URL"

# 测试Redis连接
echo "🔍 测试Redis连接..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -a "Taifish2024!" ping &> /dev/null; then
        echo "✅ Redis连接正常"
    else
        echo "❌ Redis连接失败"
    fi
else
    echo "⚠️  redis-cli 未安装，无法测试连接"
fi

echo "🎉 环境设置完成！"
