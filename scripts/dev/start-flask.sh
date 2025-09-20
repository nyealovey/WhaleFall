#!/bin/bash

# 开发环境Flask应用启动脚本
# 功能：手动启动Flask应用，连接Docker中的数据库服务

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
    echo "║                    开发环境Flask应用                         ║"
    echo "║                    手动启动模式                              ║"
    echo "║                  连接Docker数据库服务                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查环境
check_environment() {
    log_info "检查开发环境..."
    
    # 检查.env文件
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
    
    # 检查Python环境
    if ! command -v python &> /dev/null; then
        log_error "Python未安装，请先安装Python"
        exit 1
    fi
    
    # 检查uv
    if ! command -v uv &> /dev/null; then
        log_warning "uv未安装，建议安装uv进行依赖管理"
    fi
    
    log_success "环境检查通过"
}

# 检查数据库服务
check_database_services() {
    log_info "检查数据库服务状态..."
    
    # 检查PostgreSQL
    if ! docker compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        log_error "PostgreSQL服务未运行，请先启动数据库服务："
        log_error "  ./scripts/dev/start-dev-db.sh"
        exit 1
    fi
    
    # 检查Redis
    if ! docker compose -f docker-compose.dev.yml ps redis | grep -q "Up"; then
        log_error "Redis服务未运行，请先启动数据库服务："
        log_error "  ./scripts/dev/start-dev-db.sh"
        exit 1
    fi
    
    log_success "数据库服务检查通过"
}

# 安装依赖
install_dependencies() {
    log_info "检查Python依赖..."
    
    if command -v uv &> /dev/null; then
        log_info "使用uv安装依赖..."
        uv sync
    else
        log_warning "uv未安装，请手动安装依赖："
        log_warning "  pip install -r requirements.txt"
    fi
}

# 启动Flask应用
start_flask_app() {
    log_info "启动Flask应用..."
    
    # 设置环境变量
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    
    # 修改数据库连接为本地连接
    export DATABASE_URL="postgresql+psycopg://whalefall_user:Dev2024!@localhost:5432/whalefall_dev"
    export CACHE_REDIS_URL="redis://:RedisDev2024!@localhost:6379/0"
    
    log_info "Flask应用配置："
    log_info "  - 应用文件: app.py"
    log_info "  - 环境: development"
    log_info "  - 调试模式: 启用"
    log_info "  - 数据库: ${DATABASE_URL}"
    log_info "  - Redis: ${CACHE_REDIS_URL}"
    echo ""
    
    log_success "启动Flask应用..."
    log_info "访问地址: http://localhost:5001"
    log_info "按 Ctrl+C 停止应用"
    echo ""
    
    # 启动Flask应用
    python app.py
}

# 主函数
main() {
    show_banner
    
    check_environment
    check_database_services
    install_dependencies
    start_flask_app
}

# 执行主函数
main "$@"
