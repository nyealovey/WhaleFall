#!/bin/bash

# 本地开发环境 - 基础环境启动脚本（macOS，无代理）
# 启动：PostgreSQL + Redis + Nginx

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

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，请先启动Docker Desktop"
        exit 1
    fi
    log_success "Docker运行正常"
}

# 检查环境配置文件
check_env() {
    if [ ! -f ".env" ]; then
        log_warning "未找到.env文件，从env.development创建"
        cp env.development .env
        log_info "请根据需要修改.env文件中的配置"
    fi
    log_success "环境配置文件检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p userdata/{postgres,redis,nginx/{logs,ssl},logs,exports,backups,uploads}
    log_success "目录创建完成"
}

# 启动基础环境
start_base_environment() {
    log_info "启动基础环境（PostgreSQL + Redis + Nginx）..."
    
    # 停止可能存在的容器（不删除）
    docker-compose -f docker-compose.dev.yml stop postgres redis nginx 2>/dev/null || true
    
    # 启动基础服务
    docker-compose -f docker-compose.dev.yml up -d postgres redis nginx
    
    log_success "基础环境启动完成"
}

# 等待基础服务就绪
wait_for_base_services() {
    log_info "等待基础服务就绪..."
    
    # 等待PostgreSQL
    log_info "等待PostgreSQL启动..."
    timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U whalefall_user -d whalefall_dev; do sleep 2; done'
    log_success "PostgreSQL已就绪"
    
    # 等待Redis
    log_info "等待Redis启动..."
    timeout 30 bash -c 'until docker-compose -f docker-compose.dev.yml exec redis redis-cli ping; do sleep 2; done'
    log_success "Redis已就绪"
    
    # 等待Nginx
    log_info "等待Nginx启动..."
    timeout 30 bash -c 'until curl -f http://localhost > /dev/null 2>&1; do sleep 2; done'
    log_success "Nginx已就绪"
}

# 显示基础环境状态
show_base_status() {
    log_info "基础环境状态:"
    docker-compose -f docker-compose.dev.yml ps postgres redis nginx
    
    echo ""
    log_info "服务信息:"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - Nginx: http://localhost"
    
    echo ""
    log_info "下一步:"
    echo "  运行 ./scripts/docker/start-dev-flask.sh 启动Flask应用"
}

# 主函数
main() {
    log_info "开始启动本地开发基础环境..."
    
    check_docker
    check_env
    create_directories
    start_base_environment
    wait_for_base_services
    show_base_status
    
    log_success "基础环境启动完成！"
}

# 执行主函数
main "$@"
