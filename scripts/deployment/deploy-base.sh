#!/bin/bash

# 基础环境部署脚本
# 部署：PostgreSQL、Redis、Nginx
# 不包含：Flask应用

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

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查系统依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "系统依赖检查通过"
}

# 检查环境配置文件
check_env_file() {
    log_info "检查环境配置文件..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.prod" ]; then
            log_info "复制生产环境配置文件..."
            cp env.prod .env
        else
            log_error "未找到环境配置文件，请创建.env文件"
            exit 1
        fi
    fi
    
    # 检查必要的环境变量
    source .env
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD未设置"
        exit 1
    fi
    
    if [ -z "$REDIS_PASSWORD" ]; then
        log_error "REDIS_PASSWORD未设置"
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY未设置"
        exit 1
    fi
    
    log_success "环境配置文件检查通过"
}

# 创建数据目录
create_data_directories() {
    log_info "创建数据目录..."
    
    sudo mkdir -p /opt/whale_fall_data/{postgres,redis,nginx/{logs,ssl},app,logs}
    sudo chown -R $USER:$USER /opt/whale_fall_data
    
    log_success "数据目录创建完成"
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用..."
    
    local ports=(80 443 5432 6379)
    
    for port in "${ports[@]}"; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            log_warning "端口 $port 已被占用"
            read -p "是否继续？(y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    done
    
    log_success "端口检查完成"
}

# 启动基础环境
start_base_environment() {
    log_info "启动基础环境..."
    
    # 创建网络
    docker network create whalefall_network 2>/dev/null || true
    
    # 启动基础服务
    docker-compose -f docker-compose.base.yml up -d
    
    log_success "基础环境启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待PostgreSQL
    log_info "等待PostgreSQL启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose -f docker-compose.base.yml exec postgres pg_isready -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} &>/dev/null; then
            log_success "PostgreSQL已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "PostgreSQL启动超时"
        exit 1
    fi
    
    # 等待Redis
    log_info "等待Redis启动..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker-compose -f docker-compose.base.yml exec redis redis-cli ping &>/dev/null; then
            log_success "Redis已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    
    # 等待Nginx
    log_info "等待Nginx启动..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost/health &>/dev/null; then
            log_success "Nginx已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        log_warning "Nginx健康检查失败（可能正常，因为Flask应用未启动）"
    fi
}

# 验证基础环境
verify_base_environment() {
    log_info "验证基础环境..."
    
    # 检查PostgreSQL
    if docker-compose -f docker-compose.base.yml exec postgres pg_isready -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} &>/dev/null; then
        log_success "PostgreSQL连接正常"
    else
        log_error "PostgreSQL连接失败"
        exit 1
    fi
    
    # 检查Redis
    if docker-compose -f docker-compose.base.yml exec redis redis-cli ping &>/dev/null; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        exit 1
    fi
    
    # 检查Nginx
    if docker-compose -f docker-compose.base.yml ps nginx | grep -q "Up"; then
        log_success "Nginx运行正常"
    else
        log_error "Nginx运行异常"
        exit 1
    fi
    
    log_success "基础环境验证通过"
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    echo "=================================="
    docker-compose -f docker-compose.base.yml ps
    echo "=================================="
    
    log_info "访问地址："
    echo "  - Nginx: http://localhost"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo ""
    
    log_info "管理命令："
    echo "  查看日志: docker-compose -f docker-compose.base.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.base.yml down"
    echo "  重启服务: docker-compose -f docker-compose.base.yml restart"
    echo "  进入容器: docker-compose -f docker-compose.base.yml exec <service> sh"
    echo ""
    
    log_warning "注意：基础环境已启动，但Flask应用尚未部署"
    log_info "下一步：运行 ./scripts/deploy-flask.sh 部署Flask应用"
}

# 主函数
main() {
    echo "🐟 鲸落基础环境部署脚本"
    echo "=================================="
    
    check_dependencies
    check_env_file
    create_data_directories
    check_ports
    start_base_environment
    wait_for_services
    verify_base_environment
    show_status
    
    echo "=================================="
    log_success "基础环境部署完成！"
    echo "=================================="
}

# 运行主函数
main "$@"
