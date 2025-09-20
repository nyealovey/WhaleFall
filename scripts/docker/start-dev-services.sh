#!/bin/bash
# 开发环境服务启动脚本

set -e

echo "🚀 启动开发环境服务..."

# 启动Nginx
echo "📡 启动Nginx..."
service nginx start

# 检查Nginx状态
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx启动成功"
else
    echo "❌ Nginx启动失败"
    exit 1
fi

# 启动Supervisor管理Gunicorn+Flask应用
echo "🐍 启动Gunicorn+Flask应用..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
