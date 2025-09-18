#!/bin/bash

# 鲸落 - 统一部署脚本
# 使用方法: ./scripts/deploy.sh [操作]
# 示例: ./scripts/deploy.sh start

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
    
    if [ ! -f "$env_file" ]; then
        log_error "环境配置文件 $env_file 不存在"
        log_info "请复制 env.example 为 $env_file 并配置相关参数"
        exit 1
    fi
    
    log_success "环境配置文件检查通过"
}

# 初始化数据目录
init_data_directories() {
    log_info "初始化数据目录..."
    
    # 运行数据目录初始化脚本
    ./scripts/init-data-dirs.sh init
    
    log_success "数据目录初始化完成"
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    
    docker build -t whalefall:latest .
    
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    docker compose up -d
    
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    docker compose down
    
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    
    docker compose restart
    
    log_success "服务重启完成"
}

# 查看服务状态
status_services() {
    log_info "查看服务状态..."
    
    docker compose ps
}

# 查看日志
view_logs() {
    local service=$1
    
    if [ -n "$service" ]; then
        log_info "查看 $service 服务日志..."
        docker compose logs -f "$service"
    else
        log_info "查看所有服务日志..."
        docker compose logs -f
    fi
}

# 数据库迁移
migrate_database() {
    log_info "执行数据库迁移..."
    
    docker compose exec whalefall python -m flask db upgrade
    
    log_success "数据库迁移完成"
}

# 创建管理员用户
create_admin() {
    log_info "创建管理员用户..."
    
    docker compose exec whalefall python scripts/show_admin_password.py
    
    log_success "管理员用户创建完成"
}

# 备份数据
backup_data() {
    local backup_dir="/opt/whale_fall_data/backups"
    local date=$(date +%Y%m%d_%H%M%S)
    
    log_info "备份数据..."
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    # 备份数据库
    docker compose exec postgres pg_dump -U whalefall_user whalefall_prod > "$backup_dir/database_$date.sql"
    
    # 备份应用数据
    docker compose exec whalefall tar -czf - /app/userdata > "$backup_dir/userdata_$date.tar.gz"
    
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
    echo "  $0 [操作] [服务名]"
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
    echo "  $0 start"
    echo "  $0 logs whalefall"
    echo "  $0 backup"
}

# 主函数
main() {
    local action=${1:-help}
    local service=$2
    
    case $action in
        start)
            check_dependencies
            check_env_file
            init_data_directories
            build_image
            start_services
            sleep 10
            migrate_database
            create_admin
            status_services
            ;;
        stop)
            check_dependencies
            stop_services
            ;;
        restart)
            check_dependencies
            restart_services
            status_services
            ;;
        status)
            check_dependencies
            status_services
            ;;
        logs)
            check_dependencies
            view_logs "$service"
            ;;
        build)
            check_dependencies
            build_image
            ;;
        migrate)
            check_dependencies
            migrate_database
            ;;
        admin)
            check_dependencies
            create_admin
            ;;
        backup)
            check_dependencies
            backup_data
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
