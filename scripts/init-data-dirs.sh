#!/bin/bash

# 鲸落 - 数据目录初始化脚本
# 创建统一的数据存储目录结构

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

# 主数据目录
DATA_ROOT="/opt/whale_fall_data"

# 创建目录结构
create_directories() {
    log_info "创建数据目录结构..."
    
    # 创建主目录
    sudo mkdir -p "$DATA_ROOT"
    
    # 应用数据目录
    sudo mkdir -p "$DATA_ROOT/app"
    sudo mkdir -p "$DATA_ROOT/app/logs"
    sudo mkdir -p "$DATA_ROOT/app/exports"
    sudo mkdir -p "$DATA_ROOT/app/backups"
    sudo mkdir -p "$DATA_ROOT/app/uploads"
    
    # 数据库目录
    sudo mkdir -p "$DATA_ROOT/postgres"
    
    # Redis目录
    sudo mkdir -p "$DATA_ROOT/redis"
    
    # Nginx目录
    sudo mkdir -p "$DATA_ROOT/nginx/logs"
    sudo mkdir -p "$DATA_ROOT/nginx/ssl"
    
    # 备份目录
    sudo mkdir -p "$DATA_ROOT/backups"
    
    log_success "目录结构创建完成"
}

# 设置权限
set_permissions() {
    log_info "设置目录权限..."
    
    # 设置主目录权限
    sudo chown -R 1000:1000 "$DATA_ROOT"
    sudo chmod -R 755 "$DATA_ROOT"
    
    # 设置PostgreSQL目录权限（PostgreSQL容器使用postgres用户）
    sudo chown -R 999:999 "$DATA_ROOT/postgres"
    sudo chmod -R 700 "$DATA_ROOT/postgres"
    
    # 设置Redis目录权限（Redis容器使用redis用户）
    sudo chown -R 999:999 "$DATA_ROOT/redis"
    sudo chmod -R 755 "$DATA_ROOT/redis"
    
    log_success "权限设置完成"
}

# 显示目录结构
show_structure() {
    log_info "数据目录结构:"
    echo ""
    echo "$DATA_ROOT/"
    echo "├── app/                    # 应用数据"
    echo "│   ├── logs/              # 应用日志"
    echo "│   ├── exports/           # 导出文件"
    echo "│   ├── backups/           # 应用备份"
    echo "│   └── uploads/           # 上传文件"
    echo "├── postgres/              # PostgreSQL数据"
    echo "├── redis/                 # Redis数据"
    echo "├── nginx/                 # Nginx数据"
    echo "│   ├── logs/              # Nginx日志"
    echo "│   └── ssl/               # SSL证书"
    echo "└── backups/               # 系统备份"
    echo ""
}

# 检查目录是否存在
check_directories() {
    log_info "检查目录状态..."
    
    if [ -d "$DATA_ROOT" ]; then
        log_success "数据目录已存在: $DATA_ROOT"
        show_structure
    else
        log_warning "数据目录不存在，将创建..."
        create_directories
        set_permissions
        show_structure
    fi
}

# 显示帮助信息
show_help() {
    echo "鲸落 - 数据目录初始化脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [操作]"
    echo ""
    echo "操作:"
    echo "  init        初始化数据目录"
    echo "  check       检查目录状态"
    echo "  structure   显示目录结构"
    echo "  help        显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 init"
    echo "  $0 check"
}

# 主函数
main() {
    local action=${1:-help}
    
    case $action in
        init)
            create_directories
            set_permissions
            show_structure
            ;;
        check)
            check_directories
            ;;
        structure)
            show_structure
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
