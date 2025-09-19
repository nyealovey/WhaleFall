#!/bin/bash

# 停止所有服务脚本
# 停止：Flask应用、基础环境

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

# 停止Flask应用
stop_flask_application() {
    log_info "停止Flask应用..."
    
    if docker-compose -f docker-compose.flask.yml ps | grep -q "Up"; then
        docker-compose -f docker-compose.flask.yml down
        log_success "Flask应用已停止"
    else
        log_info "Flask应用未运行"
    fi
}

# 停止基础环境
stop_base_environment() {
    log_info "停止基础环境..."
    
    if docker-compose -f docker-compose.base.yml ps | grep -q "Up"; then
        docker-compose -f docker-compose.base.yml down
        log_success "基础环境已停止"
    else
        log_info "基础环境未运行"
    fi
}

# 清理网络
cleanup_networks() {
    log_info "清理网络..."
    
    if docker network ls | grep -q whalefall_network; then
        docker network rm whalefall_network
        log_success "网络已清理"
    else
        log_info "网络不存在"
    fi
}

# 显示停止结果
show_stop_result() {
    log_info "停止结果："
    echo "=================================="
    
    # 检查服务状态
    echo "基础环境服务："
    docker-compose -f docker-compose.base.yml ps
    echo ""
    echo "Flask应用服务："
    docker-compose -f docker-compose.flask.yml ps
    echo "=================================="
    
    log_info "数据保留："
    echo "  - 数据库数据: /opt/whale_fall_data/postgres"
    echo "  - Redis数据: /opt/whale_fall_data/redis"
    echo "  - 应用数据: /opt/whale_fall_data/app"
    echo "  - 日志文件: /opt/whale_fall_data/logs"
    echo ""
    
    log_info "重启命令："
    echo "  启动基础环境: ./scripts/deploy-base.sh"
    echo "  启动Flask应用: ./scripts/deploy-flask.sh"
    echo "  启动所有服务: ./scripts/start-all.sh"
}

# 主函数
main() {
    echo "🐟 鲸落停止所有服务脚本"
    echo "=================================="
    
    stop_flask_application
    stop_base_environment
    cleanup_networks
    show_stop_result
    
    echo "=================================="
    log_success "所有服务已停止！"
    echo "=================================="
}

# 运行主函数
main "$@"
