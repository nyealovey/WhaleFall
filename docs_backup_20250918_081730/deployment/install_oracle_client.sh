#!/bin/bash
# 泰摸鱼吧 - Oracle Instant Client安装脚本

echo "🔧 安装Oracle Instant Client..."

# 检查系统架构
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ORACLE_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ORACLE_ARCH="arm64"
else
    echo "❌ 不支持的架构: $ARCH"
    exit 1
fi

echo "📋 检测到架构: $ARCH ($ORACLE_ARCH)"

# 创建Oracle目录
ORACLE_HOME="/opt/oracle"
mkdir -p $ORACLE_HOME

# 下载Oracle Instant Client
echo "📥 下载Oracle Instant Client..."
cd /tmp

# 基础包
if [ ! -f "instantclient-basic-linux.${ORACLE_ARCH}-21.1.0.0.0dbru.zip" ]; then
    echo "⚠️  请手动下载Oracle Instant Client:"
    echo "   1. 访问: https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html"
    echo "   2. 下载: instantclient-basic-linux.${ORACLE_ARCH}-21.1.0.0.0dbru.zip"
    echo "   3. 将文件放到: /tmp/instantclient-basic-linux.${ORACLE_ARCH}-21.1.0.0.0dbru.zip"
    echo "   4. 重新运行此脚本"
    exit 1
fi

# 解压
echo "📦 解压Oracle Instant Client..."
unzip -q "instantclient-basic-linux.${ORACLE_ARCH}-21.1.0.0.0dbru.zip"
mv instantclient_21_1/* $ORACLE_HOME/

# 配置环境变量
echo "⚙️ 配置环境变量..."
echo "export ORACLE_HOME=$ORACLE_HOME" >> /etc/environment
echo "export LD_LIBRARY_PATH=\$ORACLE_HOME:\$LD_LIBRARY_PATH" >> /etc/environment
echo "export PATH=\$ORACLE_HOME:\$PATH" >> /etc/environment

# 创建符号链接
ln -sf $ORACLE_HOME/libclntsh.so.21.1 $ORACLE_HOME/libclntsh.so
ln -sf $ORACLE_HOME/libocci.so.21.1 $ORACLE_HOME/libocci.so

# 设置权限
chmod -R 755 $ORACLE_HOME

echo "✅ Oracle Instant Client安装完成！"
echo "📍 安装路径: $ORACLE_HOME"
echo "🔧 环境变量已配置"

# 安装Python驱动
echo "🐍 安装cx_Oracle..."
pip install cx_Oracle==8.3.0

echo "🎉 Oracle支持安装完成！"
