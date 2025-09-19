#!/bin/bash

# 服务器正式环境清理脚本
# 提供安全的清理选项

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

# 清理未使用的容器
cleanup_containers() {
    log_info "清理未使用的容器..."
    docker container prune -f
    log_success "容器清理完成"
}

# 清理未使用的镜像
cleanup_unused_images() {
    log_info "清理未使用的镜像..."
    docker image prune -f
    log_success "镜像清理完成"
}

# 清理未使用的数据卷
cleanup_unused_volumes() {
    log_warning "⚠️  即将清理未使用的数据卷！"
    read -p "确认清理？输入 'yes' 确认: " -r
    if [[ $REPLY = "yes" ]]; then
        log_info "清理未使用的数据卷..."
        docker volume prune -f
        log_success "数据卷清理完成"
    else
        log_info "取消数据卷清理"
    fi
}

# 清理Flask应用镜像
cleanup_flask_image() {
    log_warning "⚠️  即将删除Flask应用镜像！"
    read -p "确认删除？输入 'yes' 确认: " -r
    if [[ $REPLY = "yes" ]]; then
        log_info "删除Flask应用镜像..."
        docker rmi whalefall:prod 2>/dev/null || true
        log_success "Flask应用镜像已删除"
    else
        log_info "取消镜像删除"
    fi
}

# 清理所有生产环境数据
cleanup_all_prod_data() {
    log_warning "⚠️  即将删除所有生产环境数据！"
    log_warning "这将删除："
    log_warning "  - 所有容器"
    log_warning "  - 所有镜像"
    log_warning "  - 所有数据卷"
    log_warning "  - 所有网络"
    echo ""
    read -p "确认删除所有数据？输入 'DELETE ALL' 确认: " -r
    if [[ $REPLY = "DELETE ALL" ]]; then
        log_info "停止所有服务..."
        ./scripts/docker/stop-prod.sh
        
        log_info "清理所有Docker资源..."
        docker system prune -a -f --volumes
        
        log_success "所有生产环境数据已清理"
    else
        log_info "取消数据清理"
    fi
}

# 显示帮助信息
show_help() {
    echo "服务器正式环境清理脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -c, --containers    清理未使用的容器"
    echo "  -i, --images        清理未使用的镜像"
    echo "  -v, --volumes       清理未使用的数据卷"
    echo "  -f, --flask         清理Flask应用镜像"
    echo "  -a, --all           清理所有生产环境数据"
    echo ""
    echo "示例:"
    echo "  $0 -c               清理未使用的容器"
    echo "  $0 -i               清理未使用的镜像"
    echo "  $0 -v               清理未使用的数据卷"
    echo "  $0 -f               清理Flask应用镜像"
    echo "  $0 -a               清理所有数据（危险操作）"
    echo ""
    echo "⚠️  警告："
    echo "  --volumes 会删除未使用的数据卷"
    echo "  --flask   会删除Flask应用镜像"
    echo "  --all     会删除所有Docker数据（包括数据库数据）"
}

# 主函数
main() {
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--containers)
            cleanup_containers
            ;;
        -i|--images)
            cleanup_unused_images
            ;;
        -v|--volumes)
            cleanup_unused_volumes
            ;;
        -f|--flask)
            cleanup_flask_image
            ;;
        -a|--all)
            cleanup_all_prod_data
            ;;
        "")
            log_error "请指定清理选项"
            show_help
            exit 1
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
