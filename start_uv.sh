#!/bin/bash

# 鲸落 - UV 启动脚本
# 使用 uv 管理 Python 环境和依赖

echo "🚀 启动鲸落 (TaifishV4) - UV 版本"
echo "=================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: uv 未安装"
    echo "正在尝试安装 uv..."
    
    # 尝试使用 Homebrew 安装
    if command -v brew &> /dev/null; then
        echo "📦 使用 Homebrew 安装 uv..."
        brew install uv
    else
        echo "📦 使用官方安装脚本安装 uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # 添加到 PATH
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # 再次检查
    if ! command -v uv &> /dev/null; then
        echo "❌ 安装失败，请手动安装 uv"
        echo "方法1: brew install uv"
        echo "方法2: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

# 检查 Python 版本
echo "🐍 Python 版本:"
uv python list

# 同步依赖
echo "📦 同步依赖..."
uv sync

# 检查并启动Docker服务
echo "🐳 检查Docker服务..."
if ! docker ps | grep -q "postgres"; then
    echo "📦 启动Docker数据库服务..."
    docker-compose -f docker-compose.dev.yml up -d postgres redis
    echo "⏳ 等待数据库启动..."
    sleep 5
fi

# 检查端口是否被占用
if lsof -ti:5001 > /dev/null 2>&1; then
    echo "⚠️  端口5001被占用，正在停止现有进程..."
    lsof -ti:5001 | xargs kill -9
    sleep 2
fi

# 启动应用
echo "🚀 启动应用..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止应用"
echo ""

# 使用 uv 运行应用，确保加载环境变量
uv run --env-file .env python app.py
