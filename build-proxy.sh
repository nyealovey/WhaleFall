#!/bin/bash

# 简单的代理构建脚本
# 用法: ./build-proxy.sh [代理地址]

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}📊 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <代理地址>"
    echo "示例: $0 http://proxy.company.com:8080"
    echo "示例: $0 http://user:pass@proxy.company.com:8080"
    exit 1
fi

PROXY_URL="$1"
IMAGE_NAME="whalefall"
IMAGE_TAG="latest"

log_info "使用代理构建Docker镜像..."
log_info "代理地址: $PROXY_URL"

# 构建镜像
docker build \
  --build-arg HTTP_PROXY="$PROXY_URL" \
  --build-arg HTTPS_PROXY="$PROXY_URL" \
  --build-arg NO_PROXY="localhost,127.0.0.1,::1" \
  -t "$IMAGE_NAME:$IMAGE_TAG" \
  -f Dockerfile.proxy .

if [ $? -eq 0 ]; then
    log_success "构建完成！"
    log_info "镜像: $IMAGE_NAME:$IMAGE_TAG"
    log_info "运行: docker run -d -p 5001:5001 $IMAGE_NAME:$IMAGE_TAG"
else
    log_error "构建失败！"
    exit 1
fi
