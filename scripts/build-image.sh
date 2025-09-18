#!/bin/bash

# 鲸落 - Docker镜像构建脚本
# 使用方法: ./scripts/build-image.sh [标签] [推送]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取参数
TAG=${1:-latest}
PUSH=${2:-false}
REGISTRY=${3:-""}

# 构建镜像
build_image() {
    local tag=$1
    local dockerfile="Dockerfile"
    
    # 检查是否存在生产环境Dockerfile
    if [ -f "Dockerfile.prod" ]; then
        dockerfile="Dockerfile.prod"
        log_info "使用生产环境Dockerfile"
    fi
    
    log_info "构建Docker镜像: taifish:$tag"
    
    # 构建镜像
    docker build -f "$dockerfile" -t "taifish:$tag" .
    
    if [ $? -eq 0 ]; then
        log_success "镜像构建成功: taifish:$tag"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 推送镜像
push_image() {
    local tag=$1
    local registry=$2
    
    if [ "$PUSH" = "true" ]; then
        if [ -n "$registry" ]; then
            local full_tag="$registry/taifish:$tag"
            log_info "标记镜像: $full_tag"
            docker tag "taifish:$tag" "$full_tag"
            
            log_info "推送镜像到: $full_tag"
            docker push "$full_tag"
            
            if [ $? -eq 0 ]; then
                log_success "镜像推送成功: $full_tag"
            else
                log_error "镜像推送失败"
                exit 1
            fi
        else
            log_warning "未指定镜像仓库，跳过推送"
        fi
    fi
}

# 清理本地镜像
cleanup_local() {
    log_info "清理本地镜像..."
    
    # 删除未使用的镜像
    docker image prune -f
    
    log_success "本地镜像清理完成"
}

# 显示镜像信息
show_image_info() {
    local tag=$1
    
    log_info "镜像信息:"
    docker images | grep "taifish" | grep "$tag"
    
    log_info "镜像大小:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep "taifish"
}

# 显示帮助信息
show_help() {
    echo "鲸落 - Docker镜像构建脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [标签] [推送] [仓库]"
    echo ""
    echo "参数:"
    echo "  标签      镜像标签 (默认: latest)"
    echo "  推送      是否推送到仓库 (true/false, 默认: false)"
    echo "  仓库      镜像仓库地址 (可选)"
    echo ""
    echo "示例:"
    echo "  $0 latest false"
    echo "  $0 v1.0.0 true"
    echo "  $0 v1.0.0 true registry.example.com"
    echo ""
    echo "环境变量:"
    echo "  DOCKER_REGISTRY  默认镜像仓库"
    echo "  DOCKER_USERNAME  仓库用户名"
    echo "  DOCKER_PASSWORD  仓库密码"
}

# 主函数
main() {
    log_info "开始构建Docker镜像..."
    log_info "标签: $TAG"
    log_info "推送: $PUSH"
    log_info "仓库: ${REGISTRY:-未指定}"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    # 构建镜像
    build_image "$TAG"
    
    # 推送镜像
    push_image "$TAG" "$REGISTRY"
    
    # 显示镜像信息
    show_image_info "$TAG"
    
    # 清理本地镜像
    cleanup_local
    
    log_success "Docker镜像构建完成！"
}

# 检查参数
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# 执行主函数
main
