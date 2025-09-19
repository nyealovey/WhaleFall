#!/bin/bash

# 快速导出Docker镜像脚本
# 用于快速将镜像导出到其他服务器

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 快速导出Docker镜像...${NC}"

# 检查镜像是否存在
if ! docker images | grep -q "whalefall.*latest"; then
    echo "❌ 镜像 whalefall:latest 不存在，请先构建镜像"
    echo "构建命令: docker build -t whalefall:latest ."
    exit 1
fi

# 导出镜像
echo "📤 导出镜像..."
docker save whalefall:latest | gzip > whalefall-$(date +%Y%m%d_%H%M%S).tar.gz

echo -e "${GREEN}✅ 镜像导出完成！${NC}"
echo ""
echo "🚀 部署到其他服务器:"
echo "1. 将 whalefall-*.tar.gz 文件复制到目标服务器"
echo "2. 在目标服务器执行:"
echo "   gunzip -c whalefall-*.tar.gz | docker load"
echo "   docker images | grep whalefall"
echo ""
echo "📋 还需要复制以下文件到目标服务器:"
echo "   - docker-compose.base.yml"
echo "   - docker-compose.flask.yml" 
echo "   - env.production"
echo "   - nginx/conf.d/whalefall.conf"
echo "   - sql/init_postgresql.sql"
