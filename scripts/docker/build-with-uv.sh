#!/bin/bash

# 使用uv构建Docker镜像脚本
# 支持开发环境和生产环境，支持代理配置

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}📊 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查参数
if [ $# -eq 0 ]; then
    log_error "用法: $0 {dev|prod} [代理URL]"
    log_error "  dev: 构建开发环境镜像"
    log_error "  prod: 构建生产环境镜像"
    log_error "  代理URL: 可选，如 http://proxy.company.com:8080"
    exit 1
fi

ENVIRONMENT="$1"
PROXY_URL="$2"

# 检查环境
if [ "$ENVIRONMENT" != "dev" ] && [ "$ENVIRONMENT" != "prod" ]; then
    log_error "环境参数必须是 'dev' 或 'prod'"
    exit 1
fi

# 检查uv.lock文件
if [ ! -f "uv.lock" ]; then
    log_error "uv.lock 文件不存在。请先运行 'uv lock' 生成锁定文件。"
    exit 1
fi

# 检查pyproject.toml文件
if [ ! -f "pyproject.toml" ]; then
    log_error "pyproject.toml 文件不存在。"
    exit 1
fi

log_info "开始构建 $ENVIRONMENT 环境镜像..."

# 设置镜像标签
if [ "$ENVIRONMENT" = "dev" ]; then
    IMAGE_TAG="dev"
    DOCKERFILE="Dockerfile"
    TARGET="development"
else
    IMAGE_TAG="prod"
    DOCKERFILE="Dockerfile.proxy"
    TARGET="production"
fi

# 构建命令
BUILD_CMD="docker build -t whalefall:$IMAGE_TAG -f $DOCKERFILE --target $TARGET ."

# 如果有代理，添加代理参数
if [ -n "$PROXY_URL" ]; then
    log_info "使用代理构建: $PROXY_URL"
    BUILD_CMD="docker build \
        --build-arg HTTP_PROXY=\"$PROXY_URL\" \
        --build-arg HTTPS_PROXY=\"$PROXY_URL\" \
        --build-arg NO_PROXY=\"localhost,127.0.0.1,::1\" \
        -t whalefall:$IMAGE_TAG \
        -f $DOCKERFILE \
        --target $TARGET ."
else
    log_info "使用直连模式构建"
fi

# 执行构建
log_info "执行构建命令..."
eval $BUILD_CMD

if [ $? -eq 0 ]; then
    log_success "镜像构建完成: whalefall:$IMAGE_TAG"
    log_info "运行镜像: docker run -d -p 5001:5001 whalefall:$IMAGE_TAG"
else
    log_error "镜像构建失败"
    exit 1
fi

log_success "操作完成。"
