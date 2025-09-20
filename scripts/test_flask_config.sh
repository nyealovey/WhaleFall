#!/bin/bash

# 测试Flask、Gunicorn和Supervisord配置的脚本

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

# 检查环境配置
check_env() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        log_error "未找到.env文件"
        exit 1
    fi
    
    # 加载环境变量
    source .env
    
    # 检查关键环境变量
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL未设置"
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY未设置"
        exit 1
    fi
    
    # 检查数据库配置
    if [ -z "$POSTGRES_DB" ]; then
        log_warning "POSTGRES_DB未设置，使用默认值"
    fi
    
    if [ -z "$POSTGRES_USER" ]; then
        log_warning "POSTGRES_USER未设置，使用默认值"
    fi
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD未设置"
        exit 1
    fi
    
    log_success "环境配置检查通过"
    log_info "数据库配置: $POSTGRES_DB/$POSTGRES_USER"
}

# 启动基础环境
start_base() {
    log_info "启动基础环境..."
    
    # 启动PostgreSQL和Redis
    docker compose -f docker-compose.dev.yml up -d postgres redis
    
    # 等待服务就绪
    log_info "等待PostgreSQL启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.dev.yml exec postgres pg_isready -U whalefall_user -d whalefall_dev >/dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "PostgreSQL启动超时"
        exit 1
    fi
    
    log_success "PostgreSQL已就绪"
    
    # 等待Redis
    log_info "等待Redis启动..."
    count=0
    while [ $count -lt 15 ]; do
        if docker compose -f docker-compose.dev.yml exec redis redis-cli ping >/dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 15 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    
    log_success "Redis已就绪"
}

# 构建Flask镜像
build_flask() {
    log_info "构建Flask镜像..."
    
    docker compose -f docker-compose.dev.yml build whalefall
    
    log_success "Flask镜像构建完成"
}

# 启动Flask应用
start_flask() {
    log_info "启动Flask应用..."
    
    # 停止可能存在的容器
    docker compose -f docker-compose.dev.yml stop whalefall 2>/dev/null || true
    
    # 启动Flask应用
    docker compose -f docker-compose.dev.yml up -d whalefall
    
    log_success "Flask应用启动完成"
}

# 测试应用
test_application() {
    log_info "测试应用..."
    
    # 等待应用启动
    log_info "等待应用启动..."
    local count=0
    while [ $count -lt 60 ]; do
        if curl -f http://localhost/health/ >/dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 60 ]; then
        log_error "应用启动超时"
        show_logs
        exit 1
    fi
    
    log_success "应用已就绪"
    
    # 测试健康检查
    log_info "测试健康检查..."
    if curl -f http://localhost/health/ >/dev/null 2>&1; then
        log_success "健康检查通过"
    else
        log_error "健康检查失败"
        show_logs
        exit 1
    fi
    
    # 测试主页
    log_info "测试主页..."
    if curl -f http://localhost/ >/dev/null 2>&1; then
        log_success "主页访问正常"
    else
        log_warning "主页访问失败"
    fi
}

# 显示日志
show_logs() {
    log_info "显示应用日志..."
    
    echo ""
    log_info "=== Flask应用日志 ==="
    docker compose -f docker-compose.dev.yml logs whalefall --tail=50
    
    echo ""
    log_info "=== 容器内进程状态 ==="
    docker compose -f docker-compose.dev.yml exec whalefall ps aux
    
    echo ""
    log_info "=== 端口监听状态 ==="
    docker compose -f docker-compose.dev.yml exec whalefall ss -tlnp
    
    echo ""
    log_info "=== Supervisor状态 ==="
    docker compose -f docker-compose.dev.yml exec whalefall supervisorctl status
}

# 清理
cleanup() {
    log_info "清理环境..."
    docker compose -f docker-compose.dev.yml down
    log_success "清理完成"
}

# 主函数
main() {
    log_info "开始测试Flask配置..."
    
    check_env
    start_base
    build_flask
    start_flask
    test_application
    
    log_success "所有测试通过！"
    
    echo ""
    log_info "访问地址:"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health/"
    
    echo ""
    log_info "管理命令:"
    echo "  - 查看日志: docker compose -f docker-compose.dev.yml logs -f whalefall"
    echo "  - 进入容器: docker compose -f docker-compose.dev.yml exec whalefall bash"
    echo "  - 停止应用: docker compose -f docker-compose.dev.yml stop whalefall"
    echo "  - 清理环境: ./scripts/test_flask_config.sh cleanup"
}

# 处理参数
if [ "$1" = "cleanup" ]; then
    cleanup
    exit 0
fi

# 执行主函数
main "$@"
