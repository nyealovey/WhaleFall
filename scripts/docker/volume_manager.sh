#!/bin/bash

# 鲸落 Docker 卷管理脚本
# 提供卷的创建、备份、恢复、清理等功能

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

# 卷名称定义
DEV_VOLUMES=(
    "whalefall_postgres_data"
    "whalefall_redis_data"
    "whalefall_app_logs"
    "whalefall_app_ssl"
    "whalefall_app_data"
)

PROD_VOLUMES=(
    "whalefall_postgres_data"
    "whalefall_redis_data"
    "whalefall_app_logs"
    "whalefall_app_ssl"
    "whalefall_app_data"
)

# 显示使用说明
show_usage() {
    echo "鲸落 Docker 卷管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  list                   列出所有卷"
    echo "  create [dev|prod]      创建卷"
    echo "  backup [dev|prod]      备份卷"
    echo "  restore [dev|prod]     恢复卷"
    echo "  clean [dev|prod]       清理卷"
    echo "  migrate [dev|prod]     从userdata迁移到卷"
    echo "  inspect [volume_name]  检查卷详情"
    echo "  size [dev|prod]        查看卷大小"
    echo ""
    echo "选项:"
    echo "  --backup-dir DIR       备份目录 (默认: ./backups)"
    echo "  --force                 强制操作"
    echo "  --help                 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 list"
    echo "  $0 create dev"
    echo "  $0 backup prod --backup-dir /opt/backups"
    echo "  $0 migrate dev --force"
}

# 列出所有卷
list_volumes() {
    log_info "列出所有Docker卷..."
    echo ""
    echo "开发环境卷:"
    for volume in "${DEV_VOLUMES[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            echo "  ✅ $volume"
        else
            echo "  ❌ $volume (不存在)"
        fi
    done
    echo ""
    echo "生产环境卷:"
    for volume in "${PROD_VOLUMES[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            echo "  ✅ $volume"
        else
            echo "  ❌ $volume (不存在)"
        fi
    done
}

# 创建卷
create_volumes() {
    local env=$1
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "创建开发环境卷..."
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "创建生产环境卷..."
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            log_warning "卷 $volume 已存在"
        else
            docker volume create "$volume"
            log_success "创建卷: $volume"
        fi
    done
}

# 备份卷
backup_volumes() {
    local env=$1
    local backup_dir=${BACKUP_DIR:-./backups}
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "备份开发环境卷到: $backup_dir"
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "备份生产环境卷到: $backup_dir"
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            local backup_file="${backup_dir}/${volume}_$(date +%Y%m%d_%H%M%S).tar"
            log_info "备份卷: $volume"
            docker run --rm -v "$volume":/source -v "$(pwd)/$backup_dir":/backup alpine tar czf "/backup/$(basename "$backup_file")" -C /source .
            log_success "备份完成: $backup_file"
        else
            log_warning "卷 $volume 不存在，跳过"
        fi
    done
}

# 恢复卷
restore_volumes() {
    local env=$1
    local backup_dir=${BACKUP_DIR:-./backups}
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "从 $backup_dir 恢复开发环境卷"
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "从 $backup_dir 恢复生产环境卷"
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    if [ ! -d "$backup_dir" ]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi
    
    for volume in "${volumes[@]}"; do
        local backup_file=$(ls -t "$backup_dir"/${volume}_*.tar 2>/dev/null | head -n1)
        if [ -n "$backup_file" ]; then
            log_info "恢复卷: $volume"
            docker run --rm -v "$volume":/target -v "$(pwd)/$backup_dir":/backup alpine sh -c "cd /target && tar xzf /backup/$(basename "$backup_file")"
            log_success "恢复完成: $volume"
        else
            log_warning "未找到卷 $volume 的备份文件"
        fi
    done
}

# 清理卷
clean_volumes() {
    local env=$1
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "清理开发环境卷..."
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "清理生产环境卷..."
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    if [ "$FORCE" != "true" ]; then
        log_warning "这将删除所有数据，请确认！"
        read -p "输入 'yes' 确认: " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            docker volume rm "$volume"
            log_success "删除卷: $volume"
        else
            log_warning "卷 $volume 不存在"
        fi
    done
}

# 从userdata迁移到卷
migrate_volumes() {
    local env=$1
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "从userdata迁移到开发环境卷..."
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "从userdata迁移到生产环境卷..."
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    # 检查userdata目录是否存在
    if [ ! -d "./userdata" ]; then
        log_warning "userdata目录不存在，跳过迁移"
        return
    fi
    
    # 迁移PostgreSQL数据
    if [ -d "./userdata/postgres" ]; then
        log_info "迁移PostgreSQL数据..."
        docker run --rm -v whalefall_postgres_data:/target -v "$(pwd)/userdata/postgres":/source alpine sh -c "cp -r /source/* /target/"
        log_success "PostgreSQL数据迁移完成"
    fi
    
    # 迁移Redis数据
    if [ -d "./userdata/redis" ]; then
        log_info "迁移Redis数据..."
        docker run --rm -v whalefall_redis_data:/target -v "$(pwd)/userdata/redis":/source alpine sh -c "cp -r /source/* /target/"
        log_success "Redis数据迁移完成"
    fi
    
    # 迁移Nginx日志
    if [ -d "./userdata/nginx/logs" ]; then
        log_info "迁移Nginx日志..."
        docker run --rm -v whalefall_app_logs:/target -v "$(pwd)/userdata/nginx/logs":/source alpine sh -c "cp -r /source/* /target/"
        log_success "Nginx日志迁移完成"
    fi
    
    # 迁移Nginx SSL
    if [ -d "./userdata/nginx/ssl" ]; then
        log_info "迁移Nginx SSL证书..."
        docker run --rm -v whalefall_app_ssl:/target -v "$(pwd)/userdata/nginx/ssl":/source alpine sh -c "cp -r /source/* /target/"
        log_success "Nginx SSL证书迁移完成"
    fi
    
    # 迁移应用数据
    if [ -d "./userdata" ]; then
        log_info "迁移应用数据..."
        docker run --rm -v whalefall_app_data:/target -v "$(pwd)/userdata":/source alpine sh -c "cp -r /source/* /target/"
        log_success "应用数据迁移完成"
    fi
}

# 检查卷详情
inspect_volume() {
    local volume_name=$1
    
    if [ -z "$volume_name" ]; then
        log_error "请指定卷名称"
        exit 1
    fi
    
    if docker volume ls -q | grep -q "^${volume_name}$"; then
        log_info "卷详情: $volume_name"
        docker volume inspect "$volume_name"
    else
        log_error "卷 $volume_name 不存在"
        exit 1
    fi
}

# 查看卷大小
show_volume_size() {
    local env=$1
    local volumes=()
    
    if [ "$env" = "dev" ]; then
        volumes=("${DEV_VOLUMES[@]}")
        log_info "开发环境卷大小:"
    elif [ "$env" = "prod" ]; then
        volumes=("${PROD_VOLUMES[@]}")
        log_info "生产环境卷大小:"
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            local size=$(docker run --rm -v "$volume":/source alpine du -sh /source | cut -f1)
            echo "  $volume: $size"
        else
            echo "  $volume: 不存在"
        fi
    done
}

# 主函数
main() {
    local command=$1
    local env=$2
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                if [ -z "$command" ]; then
                    command=$1
                elif [ -z "$env" ]; then
                    env=$1
                fi
                shift
                ;;
        esac
    done
    
    case $command in
        list)
            list_volumes
            ;;
        create)
            create_volumes "$env"
            ;;
        backup)
            backup_volumes "$env"
            ;;
        restore)
            restore_volumes "$env"
            ;;
        clean)
            clean_volumes "$env"
            ;;
        migrate)
            migrate_volumes "$env"
            ;;
        inspect)
            inspect_volume "$env"
            ;;
        size)
            show_volume_size "$env"
            ;;
        *)
            log_error "未知命令: $command"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
