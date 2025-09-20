#!/bin/bash

# 开发环境数据库服务启动脚本
# 功能：启动PostgreSQL和Redis容器，Flask应用手动启动

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}📊 [INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}❌ [ERROR]${NC} $1"
}

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    开发环境数据库服务                        ║"
    echo "║                    PostgreSQL + Redis                       ║"
    echo "║                   Flask应用需手动启动                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量配置..."
    
    if [ ! -f ".env" ]; then
        log_warning "未找到.env文件，正在创建..."
        if [ -f "env.development" ]; then
            cp env.development .env
            log_success "已从env.development创建.env文件"
        else
            log_error "未找到env.development文件，请先配置环境变量"
            exit 1
        fi
    fi
    
    # 加载环境变量
    source .env
    
    log_success "环境变量检查通过"
}

# 启动数据库服务
start_database_services() {
    log_info "启动数据库服务..."
    
    # 启动PostgreSQL和Redis
    docker compose -f docker-compose.dev.yml up -d postgres redis
    
    log_success "数据库服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待数据库服务就绪..."
    
    # 等待PostgreSQL
    log_info "等待PostgreSQL启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.dev.yml exec postgres pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} > /dev/null 2>&1; then
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
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.dev.yml exec redis redis-cli ping > /dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    log_success "Redis已就绪"
}

# 显示服务信息
show_service_info() {
    log_info "服务信息"
    
    echo ""
    echo -e "${GREEN}🎉 开发环境数据库服务启动完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 服务信息：${NC}"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - 数据库名: ${POSTGRES_DB}"
    echo "  - 数据库用户: ${POSTGRES_USER}"
    echo ""
    echo -e "${BLUE}🚀 启动Flask应用：${NC}"
    echo "  - 命令: python app.py"
    echo "  - 访问地址: http://localhost:5001"
    echo "  - 环境变量: 已从.env文件加载"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.dev.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.dev.yml logs -f"
    echo "  - 停止服务: docker compose -f docker-compose.dev.yml down"
    echo "  - 重启服务: docker compose -f docker-compose.dev.yml restart"
    echo ""
    echo -e "${YELLOW}⚠️  注意事项：${NC}"
    echo "  - Flask应用需要手动启动"
    echo "  - 确保已安装Python依赖：uv sync"
    echo "  - 数据库连接使用Docker网络中的服务名"
}

# 主函数
main() {
    show_banner
    
    check_environment
    start_database_services
    wait_for_services
    show_service_info
    
    log_success "开发环境数据库服务启动完成！"
}

# 执行主函数
main "$@"
