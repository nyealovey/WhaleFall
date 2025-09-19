#!/bin/bash

# 服务器正式环境停止脚本
# 停止：Flask应用 + 基础环境

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

# 停止Flask应用
stop_flask() {
    log_info "停止Flask应用..."
    docker-compose -f docker-compose.prod.yml stop whalefall 2>/dev/null || true
    log_success "Flask应用已停止"
}

# 停止基础环境
stop_base() {
    log_info "停止基础环境..."
    docker-compose -f docker-compose.prod.yml stop postgres redis nginx 2>/dev/null || true
    log_success "基础环境已停止"
}

# 清理数据卷（谨慎操作）
cleanup_volumes() {
    if [ "$1" = "--volumes" ]; then
        log_warning "⚠️  即将删除所有未使用的数据卷，这将导致数据丢失！"
        read -p "确认删除数据卷？输入 'yes' 确认: " -r
        if [[ $REPLY = "yes" ]]; then
            log_warning "清理数据卷..."
            docker volume prune -f
            log_success "数据卷已清理"
        else
            log_info "取消数据卷清理"
        fi
    fi
}

# 清理镜像（谨慎操作）
cleanup_images() {
    if [ "$1" = "--images" ]; then
        log_warning "⚠️  即将删除Flask应用镜像！"
        read -p "确认删除镜像？输入 'yes' 确认: " -r
        if [[ $REPLY = "yes" ]]; then
            log_warning "清理镜像..."
            docker rmi whalefall:prod 2>/dev/null || true
            log_success "镜像已清理"
        else
            log_info "取消镜像清理"
        fi
    fi
}

# 显示帮助信息
show_help() {
    echo "服务器正式环境停止脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -v, --volumes  停止服务并清理数据卷（谨慎使用）"
    echo "  -i, --images   停止服务并清理镜像（谨慎使用）"
    echo ""
    echo "示例:"
    echo "  $0             停止所有服务（推荐）"
    echo "  $0 -v          停止服务并清理数据卷（会删除数据）"
    echo "  $0 -i          停止服务并清理镜像（会删除镜像）"
    echo ""
    echo "⚠️  警告："
    echo "  --volumes 会删除所有未使用的数据卷，包括数据库数据"
    echo "  --images  会删除Flask应用镜像，需要重新构建"
}

# 主函数
main() {
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
    esac
    
    log_info "开始停止生产环境..."
    
    stop_flask
    stop_base
    cleanup_volumes "$1"
    cleanup_images "$1"
    
    log_success "生产环境已停止！"
}

# 执行主函数
main "$@"
