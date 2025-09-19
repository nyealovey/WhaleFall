#!/bin/bash

# 启动所有服务脚本
# 启动：基础环境 + Flask应用

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

# 检查环境配置
check_environment() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        log_error "环境配置文件.env不存在"
        exit 1
    fi
    
    source .env
    
    # 检查必要的环境变量
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "环境变量 $var 未设置"
            exit 1
        fi
    done
    
    log_success "环境配置检查通过"
}

# 启动基础环境
start_base_environment() {
    log_info "启动基础环境..."
    
    # 检查基础环境是否已运行
    if docker-compose -f docker-compose.base.yml ps | grep -q "Up"; then
        log_info "基础环境已在运行"
        return 0
    fi
    
    # 启动基础环境
    docker-compose -f docker-compose.base.yml up -d
    
    # 等待基础环境就绪
    log_info "等待基础环境就绪..."
    local timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose -f docker-compose.base.yml exec postgres pg_isready -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} &>/dev/null; then
            log_success "基础环境已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "基础环境启动超时"
        exit 1
    fi
}

# 启动Flask应用
start_flask_application() {
    log_info "启动Flask应用..."
    
    # 检查Flask应用是否已运行
    if docker-compose -f docker-compose.flask.yml ps | grep -q "Up"; then
        log_info "Flask应用已在运行"
        return 0
    fi
    
    # 检查Flask镜像是否存在
    if ! docker images | grep -q "whalefall"; then
        log_info "Flask镜像不存在，正在构建..."
        docker build -t whalefall:latest .
    fi
    
    # 启动Flask应用
    docker-compose -f docker-compose.flask.yml up -d
    
    # 等待Flask应用就绪
    log_info "等待Flask应用就绪..."
    local timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:5001/health &>/dev/null; then
            log_success "Flask应用已就绪"
            break
        fi
        sleep 3
        timeout=$((timeout - 3))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "Flask应用启动超时"
        log_info "查看Flask应用日志："
        docker-compose -f docker-compose.flask.yml logs whalefall
        exit 1
    fi
}

# 验证所有服务
verify_all_services() {
    log_info "验证所有服务..."
    
    # 检查PostgreSQL
    if docker-compose -f docker-compose.base.yml exec postgres pg_isready -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} &>/dev/null; then
        log_success "PostgreSQL运行正常"
    else
        log_error "PostgreSQL运行异常"
        exit 1
    fi
    
    # 检查Redis
    if docker-compose -f docker-compose.base.yml exec redis redis-cli ping &>/dev/null; then
        log_success "Redis运行正常"
    else
        log_error "Redis运行异常"
        exit 1
    fi
    
    # 检查Nginx
    if docker-compose -f docker-compose.base.yml ps nginx | grep -q "Up"; then
        log_success "Nginx运行正常"
    else
        log_error "Nginx运行异常"
        exit 1
    fi
    
    # 检查Flask应用
    if curl -s http://localhost:5001/health | grep -q "healthy"; then
        log_success "Flask应用运行正常"
    else
        log_error "Flask应用运行异常"
        exit 1
    fi
    
    log_success "所有服务验证通过"
}

# 显示启动结果
show_start_result() {
    log_info "启动结果："
    echo "=================================="
    
    # 显示所有服务状态
    echo "基础环境服务："
    docker-compose -f docker-compose.base.yml ps
    echo ""
    echo "Flask应用服务："
    docker-compose -f docker-compose.flask.yml ps
    echo "=================================="
    
    log_info "访问地址："
    echo "  - 主应用: http://localhost"
    echo "  - 管理界面: http://localhost/admin"
    echo "  - 健康检查: http://localhost/health"
    echo "  - API文档: http://localhost/api/docs"
    echo ""
    
    log_info "管理命令："
    echo "  查看所有日志: docker-compose -f docker-compose.base.yml logs -f && docker-compose -f docker-compose.flask.yml logs -f"
    echo "  查看Flask日志: docker-compose -f docker-compose.flask.yml logs -f whalefall"
    echo "  停止所有服务: ./scripts/stop-all.sh"
    echo "  重启Flask应用: docker-compose -f docker-compose.flask.yml restart"
    echo "  进入Flask容器: docker-compose -f docker-compose.flask.yml exec whalefall bash"
    echo ""
    
    log_warning "安全提醒："
    echo "  1. 请修改默认管理员密码"
    echo "  2. 配置SSL证书启用HTTPS"
    echo "  3. 配置防火墙规则"
    echo "  4. 定期备份数据库"
}

# 主函数
main() {
    echo "🐟 鲸落启动所有服务脚本"
    echo "=================================="
    
    check_environment
    start_base_environment
    start_flask_application
    verify_all_services
    show_start_result
    
    echo "=================================="
    log_success "所有服务启动完成！"
    echo "=================================="
}

# 运行主函数
main "$@"
