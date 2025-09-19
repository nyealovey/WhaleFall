#!/bin/bash

# Nginx配置切换脚本
# 用于在主机Flask和容器Flask之间切换Nginx配置

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

# 显示帮助信息
show_help() {
    echo "Nginx配置切换脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  host     切换到主机Flask配置 (host.docker.internal:5001)"
    echo "  docker   切换到容器Flask配置 (whalefall_app:5001)"
    echo "  status   显示当前配置状态"
    echo "  help     显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 host     # 切换到主机Flask模式"
    echo "  $0 docker   # 切换到容器Flask模式"
    echo "  $0 status   # 查看当前配置"
}

# 检查当前配置
check_current_config() {
    local config_file="nginx/conf.d/whalefall.conf"
    
    if [ ! -f "$config_file" ]; then
        log_error "配置文件不存在: $config_file"
        return 1
    fi
    
    if grep -q "host.docker.internal:5001" "$config_file"; then
        echo "host"
    elif grep -q "whalefall_app:5001" "$config_file"; then
        echo "docker"
    else
        echo "unknown"
    fi
}

# 切换到主机Flask配置
switch_to_host() {
    local config_file="nginx/conf.d/whalefall.conf"
    local backup_file="nginx/conf.d/whalefall.conf.backup"
    
    log_info "切换到主机Flask配置..."
    
    # 备份当前配置
    if [ -f "$config_file" ]; then
        cp "$config_file" "$backup_file"
        log_info "已备份当前配置到: $backup_file"
    fi
    
    # 更新配置
    sed -i.bak 's/server whalefall_app:5001;/server host.docker.internal:5001;/g' "$config_file"
    rm -f "${config_file}.bak"
    
    log_success "已切换到主机Flask配置"
    log_info "upstream服务器: host.docker.internal:5001"
}

# 切换到容器Flask配置
switch_to_docker() {
    local config_file="nginx/conf.d/whalefall.conf"
    local backup_file="nginx/conf.d/whalefall.conf.backup"
    
    log_info "切换到容器Flask配置..."
    
    # 备份当前配置
    if [ -f "$config_file" ]; then
        cp "$config_file" "$backup_file"
        log_info "已备份当前配置到: $backup_file"
    fi
    
    # 更新配置
    sed -i.bak 's/server host.docker.internal:5001;/server whalefall_app:5001;/g' "$config_file"
    rm -f "${config_file}.bak"
    
    log_success "已切换到容器Flask配置"
    log_info "upstream服务器: whalefall_app:5001"
}

# 显示当前状态
show_status() {
    local current_config=$(check_current_config)
    local config_file="nginx/conf.d/whalefall.conf"
    
    echo "当前Nginx配置状态:"
    echo "=================="
    
    if [ "$current_config" = "host" ]; then
        log_info "模式: 主机Flask (host.docker.internal:5001)"
        log_info "说明: Flask应用运行在主机上，Nginx容器通过host.docker.internal访问"
    elif [ "$current_config" = "docker" ]; then
        log_info "模式: 容器Flask (whalefall_app:5001)"
        log_info "说明: Flask应用运行在Docker容器中，Nginx通过容器网络访问"
    else
        log_warning "模式: 未知配置"
        log_warning "请检查配置文件: $config_file"
    fi
    
    echo ""
    echo "当前upstream配置:"
    if [ -f "$config_file" ]; then
        grep -A 3 "upstream whalefall_backend" "$config_file" | head -4
    else
        log_error "配置文件不存在: $config_file"
    fi
}

# 重启Nginx容器
restart_nginx() {
    log_info "重启Nginx容器以应用新配置..."
    
    if docker ps | grep -q "whalefall_nginx"; then
        docker restart whalefall_nginx
        log_success "Nginx容器已重启"
    else
        log_warning "Nginx容器未运行，请先启动基础环境"
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        "host")
            switch_to_host
            restart_nginx
            ;;
        "docker")
            switch_to_docker
            restart_nginx
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
