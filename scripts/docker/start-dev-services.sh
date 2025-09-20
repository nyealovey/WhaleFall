#!/bin/bash
# 开发环境服务启动脚本

set -e

echo "🚀 启动开发环境服务..."

# 启动Supervisor管理Nginx和Gunicorn+Flask应用
echo "📡 启动Supervisor管理所有服务..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
