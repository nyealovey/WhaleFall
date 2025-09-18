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

# 启动应用
echo "🚀 启动应用..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止应用"
echo ""

# 使用 uv 运行应用
uv run python app.py
