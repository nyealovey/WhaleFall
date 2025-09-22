#!/bin/bash

# 本地开发环境 - Flask应用启动脚本（macOS，无代理）
# 启动：Flask应用（包含Nginx，依赖基础环境）

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
    if ! docker compose -f docker-compose.dev.yml exec postgres pg_isready -U whalefall_user -d whalefall_dev > /dev/null 2>&1; then
        log_error "PostgreSQL未运行，请先运行 ./scripts/docker/start-dev-base.sh"
        exit 1
    fi
    
    # 检查Redis
    if ! docker compose -f docker-compose.dev.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_error "Redis未运行，请先运行 ./scripts/docker/start-dev-base.sh"
        exit 1
    fi
    
    log_success "基础环境检查通过"
}

# 构建开发镜像
build_dev_image() {
    log_info "构建开发环境Flask镜像（包含Nginx）..."
    
    docker compose -f docker-compose.dev.yml build whalefall
    
    log_success "开发环境Flask镜像构建完成"
}

# 启动Flask应用
start_flask_application() {
    log_info "启动Flask应用（包含Nginx）..."
    
    # 停止可能存在的Flask容器（不删除）
    docker compose -f docker-compose.dev.yml stop whalefall 2>/dev/null || true
    
    # 启动Flask应用
    docker compose -f docker-compose.dev.yml up -d whalefall
    
    log_success "Flask应用启动完成"
}

# 等待Flask应用就绪
wait_for_flask() {
    log_info "等待Flask应用启动..."
    
    # 等待Flask应用（通过Nginx代理）
    local count=0
    while [ $count -lt 30 ]; do
        if curl -f http://localhost/health > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_warning "Flask应用启动超时，请检查日志"
        docker compose -f docker-compose.dev.yml logs whalefall
        exit 1
    fi
    
    log_success "Flask应用已就绪"
}

# 显示完整环境状态
show_complete_status() {
    log_info "完整环境状态:"
    docker compose -f docker-compose.dev.yml ps
    
    echo ""
    log_info "访问地址:"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health"
    echo "  - 静态文件: http://localhost/static/"
    
    echo ""
    log_info "管理命令:"
    echo "  - 查看日志: docker compose -f docker-compose.dev.yml logs -f"
    echo "  - 查看Flask日志: docker compose -f docker-compose.dev.yml logs -f whalefall"
    echo "  - 停止Flask: docker compose -f docker-compose.dev.yml stop whalefall"
    echo "  - 重启Flask: docker compose -f docker-compose.dev.yml restart whalefall"
    echo "  - 停止所有: ./scripts/docker/stop-dev.sh"
    echo "  - 进入容器: docker compose -f docker-compose.dev.yml exec whalefall bash"
}

# 主函数
main() {
    log_info "开始启动本地开发Flask应用（包含Nginx）..."
    
    check_base_environment
    build_dev_image
    start_flask_application
    wait_for_flask
    show_complete_status
    
    log_success "Flask应用启动完成！"
}

# 执行主函数
main "$@"
