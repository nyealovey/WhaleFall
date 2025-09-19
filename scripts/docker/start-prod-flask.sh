#!/bin/bash

# 服务器正式环境 - Flask应用启动脚本（x86，有代理）
# 启动：Flask应用（依赖基础环境）

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查基础环境是否运行
check_base_environment() {
    log_info "检查基础环境状态..."
    
    # 检查PostgreSQL
    if ! docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod > /dev/null 2>&1; then
        log_error "PostgreSQL未运行，请先运行 ./scripts/docker/start-prod-base.sh"
        exit 1
    fi
    
    # 检查Redis
    if ! docker-compose -f docker-compose.prod.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_error "Redis未运行，请先运行 ./scripts/docker/start-prod-base.sh"
        exit 1
    fi
    
    # 检查Nginx
    if ! curl -f http://localhost > /dev/null 2>&1; then
        log_error "Nginx未运行，请先运行 ./scripts/docker/start-prod-base.sh"
        exit 1
    fi
    
    log_success "基础环境检查通过"
}

# 检查代理配置
check_proxy() {
    if [ -n "$HTTP_PROXY" ]; then
        log_info "检测到代理配置: $HTTP_PROXY"
        log_info "将使用代理构建Flask镜像"
    else
        log_warning "未设置代理，将使用直连模式构建"
    fi
}

# 构建生产镜像
build_prod_image() {
    log_info "构建生产环境Flask镜像..."
    
    if [ -n "$HTTP_PROXY" ]; then
        # 使用代理构建
        log_info "使用代理构建镜像..."
        docker build \
            --build-arg HTTP_PROXY="$HTTP_PROXY" \
            --build-arg HTTPS_PROXY="$HTTPS_PROXY" \
            --build-arg NO_PROXY="$NO_PROXY" \
            -t whalefall:prod \
            -f Dockerfile.proxy \
            --target production .
    else
        # 直连构建
        log_info "使用直连构建镜像..."
        docker build \
            -t whalefall:prod \
            -f Dockerfile \
            --target production .
    fi
    
    log_success "生产环境Flask镜像构建完成"
}

# 启动Flask应用
start_flask_application() {
    log_info "启动Flask应用..."
    
    # 停止可能存在的Flask容器（不删除）
    docker-compose -f docker-compose.prod.yml stop whalefall 2>/dev/null || true
    
    # 启动Flask应用
    docker-compose -f docker-compose.prod.yml up -d whalefall
    
    log_success "Flask应用启动完成"
}

# 等待Flask应用就绪
wait_for_flask() {
    log_info "等待Flask应用启动..."
    
    # 等待Flask应用
    timeout 120 bash -c 'until curl -f http://localhost/health > /dev/null 2>&1; do sleep 5; done'
    log_success "Flask应用已就绪"
}

# 显示完整环境状态
show_complete_status() {
    log_info "完整环境状态:"
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    log_info "访问地址:"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health"
    
    echo ""
    log_info "管理命令:"
    echo "  - 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  - 停止Flask: docker-compose -f docker-compose.prod.yml stop whalefall"
    echo "  - 重启Flask: docker-compose -f docker-compose.prod.yml restart whalefall"
    echo "  - 停止所有: ./scripts/docker/stop-prod.sh"
}

# 主函数
main() {
    log_info "开始启动生产环境Flask应用..."
    
    check_base_environment
    check_proxy
    build_prod_image
    start_flask_application
    wait_for_flask
    show_complete_status
    
    log_success "Flask应用启动完成！"
}

# 执行主函数
main "$@"
