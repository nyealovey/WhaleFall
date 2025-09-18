#!/bin/bash

# 鲸落 - 生产环境部署脚本
# 使用方法: ./scripts/deploy.sh [环境] [操作]
# 示例: ./scripts/deploy.sh prod start

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查环境配置文件
check_env_file() {
    local env_file=".env"
    if [ "$1" = "prod" ]; then
        env_file="env.prod"
    fi
    
    if [ ! -f "$env_file" ]; then
        log_error "环境配置文件 $env_file 不存在"
        log_info "请复制 env.example 为 $env_file 并配置相关参数"
        exit 1
    fi
    
    log_success "环境配置文件检查通过"
}

# 构建Docker镜像
build_image() {
    local env=$1
    log_info "构建Docker镜像..."
    
    if [ "$env" = "prod" ]; then
        docker build -f Dockerfile -t whalefall:latest .
    else
        docker build -t whalefall:latest .
    fi
    
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    local env=$1
    log_info "启动服务..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml up -d
    else
        docker compose up -d
    fi
    
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    local env=$1
    log_info "停止服务..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml down
    else
        docker compose down
    fi
    
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    local env=$1
    log_info "重启服务..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml restart
    else
        docker compose restart
    fi
    
    log_success "服务重启完成"
}

# 查看服务状态
status_services() {
    local env=$1
    log_info "查看服务状态..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml ps
    else
        docker compose ps
    fi
}

# 查看日志
view_logs() {
    local env=$1
    local service=$2
    
    if [ -n "$service" ]; then
        log_info "查看 $service 服务日志..."
        if [ "$env" = "prod" ]; then
            docker compose -f docker-compose.yml logs -f "$service"
        else
            docker compose logs -f "$service"
        fi
    else
        log_info "查看所有服务日志..."
        if [ "$env" = "prod" ]; then
            docker compose -f docker-compose.yml logs -f
        else
            docker compose logs -f
        fi
    fi
}

# 数据库迁移
migrate_database() {
    local env=$1
    log_info "执行数据库迁移..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml exec whalefall python -m flask db upgrade
    else
        docker compose exec whalefall python -m flask db upgrade
    fi
    
    log_success "数据库迁移完成"
}

# 创建管理员用户
create_admin() {
    local env=$1
    log_info "创建管理员用户..."
    
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml exec whalefall python scripts/show_admin_password.py
    else
        docker compose exec whalefall python scripts/show_admin_password.py
    fi
    
    log_success "管理员用户创建完成"
}

# 备份数据
backup_data() {
    local env=$1
    local backup_dir="/opt/whalefall/backups"
    local date=$(date +%Y%m%d_%H%M%S)
    
    log_info "备份数据..."
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    # 备份数据库
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml exec postgres pg_dump -U whalefall_user whalefall_prod > "$backup_dir/database_$date.sql"
    else
        docker compose exec postgres pg_dump -U whalefall_user whalefall_dev > "$backup_dir/database_$date.sql"
    fi
    
    # 备份应用数据
    if [ "$env" = "prod" ]; then
        docker compose -f docker-compose.yml exec whalefall tar -czf - /app/userdata > "$backup_dir/userdata_$date.tar.gz"
    else
        docker compose exec whalefall tar -czf - /app/userdata > "$backup_dir/userdata_$date.tar.gz"
    fi
    
    log_success "数据备份完成: $backup_dir"
}

# 清理资源
cleanup() {
    log_info "清理Docker资源..."
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的容器
    docker container prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的卷
    docker volume prune -f
    
    log_success "资源清理完成"
}

# 显示帮助信息
show_help() {
    echo "鲸落 - 部署脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [环境] [操作] [服务名]"
    echo ""
    echo "环境:"
    echo "  dev     开发环境"
    echo "  prod    生产环境"
    echo ""
    echo "操作:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看状态"
    echo "  logs        查看日志"
    echo "  build       构建镜像"
    echo "  migrate     数据库迁移"
    echo "  admin       创建管理员"
    echo "  backup      备份数据"
    echo "  cleanup     清理资源"
    echo "  help        显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 prod start"
    echo "  $0 dev logs whalefall"
    echo "  $0 prod backup"
}

# 主函数
main() {
    local env=${1:-dev}
    local action=${2:-help}
    local service=$3
    
    case $action in
        start)
            check_dependencies
            check_env_file "$env"
            build_image "$env"
            start_services "$env"
            sleep 10
            migrate_database "$env"
            create_admin "$env"
            status_services "$env"
            ;;
        stop)
            check_dependencies
            stop_services "$env"
            ;;
        restart)
            check_dependencies
            restart_services "$env"
            status_services "$env"
            ;;
        status)
            check_dependencies
            status_services "$env"
            ;;
        logs)
            check_dependencies
            view_logs "$env" "$service"
            ;;
        build)
            check_dependencies
            build_image "$env"
            ;;
        migrate)
            check_dependencies
            migrate_database "$env"
            ;;
        admin)
            check_dependencies
            create_admin "$env"
            ;;
        backup)
            check_dependencies
            backup_data "$env"
            ;;
        cleanup)
            check_dependencies
            cleanup
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
