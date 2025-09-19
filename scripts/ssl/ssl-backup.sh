#!/bin/bash

# SSL证书备份和恢复脚本
# 用于管理SSL证书的备份和恢复

set -e

# 配置变量
SSL_DIR="nginx/local/ssl"
BACKUP_DIR="nginx/local/ssl/backup"
CONTAINER_NAME="whalefall_nginx_local"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "💾 SSL证书备份和恢复脚本"
    echo "=================================="
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  backup        备份当前证书"
    echo "  restore       恢复备份证书"
    echo "  list          列出所有备份"
    echo "  clean         清理旧备份"
    echo "  export        导出证书到指定目录"
    echo "  import        从指定目录导入证书"
    echo "  sync          同步证书到容器"
    echo "  status        显示备份状态"
    echo "  help          显示此帮助信息"
    echo ""
    echo "选项:"
    echo "  -d, --dir DIR     指定备份目录 (默认: $BACKUP_DIR)"
    echo "  -n, --name NAME   指定备份名称"
    echo "  -k, --keep NUM    保留备份数量 (默认: 5)"
    echo "  -f, --force       强制操作，不询问确认"
    echo "  -v, --verbose     详细输出"
    echo ""
    echo "示例:"
    echo "  $0 backup                    # 备份当前证书"
    echo "  $0 restore                   # 恢复最新备份"
    echo "  $0 list                      # 列出所有备份"
    echo "  $0 clean -k 3                # 清理旧备份，保留3个"
    echo "  $0 export -d /backup/certs   # 导出证书到指定目录"
    echo "  $0 import -d /backup/certs   # 从指定目录导入证书"
}

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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

log_verbose() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}🔍 $1${NC}"
    fi
}

# 创建备份目录
create_backup_dir() {
    local backup_dir="$1"
    mkdir -p "$backup_dir"
    log_verbose "创建备份目录: $backup_dir"
}

# 生成备份名称
generate_backup_name() {
    local name="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -n "$name" ]; then
        echo "${name}_${timestamp}"
    else
        echo "backup_${timestamp}"
    fi
}

# 备份证书
backup_certificates() {
    local backup_name="$1"
    local backup_dir="$2"
    local force="$3"
    
    log_info "开始备份SSL证书..."
    echo "=================================="
    
    # 检查证书文件是否存在
    if [ ! -f "$SSL_DIR/cert.pem" ] || [ ! -f "$SSL_DIR/key.pem" ]; then
        log_error "证书文件不存在，无法备份"
        return 1
    fi
    
    # 创建备份目录
    create_backup_dir "$backup_dir"
    
    # 生成备份名称
    local backup_name=$(generate_backup_name "$backup_name")
    local backup_path="$backup_dir/$backup_name"
    
    # 创建备份子目录
    mkdir -p "$backup_path"
    
    # 备份证书文件
    log_verbose "备份证书文件..."
    cp "$SSL_DIR/cert.pem" "$backup_path/cert.pem"
    cp "$SSL_DIR/key.pem" "$backup_path/key.pem"
    
    # 备份其他相关文件
    if [ -f "$SSL_DIR/cert.csr" ]; then
        cp "$SSL_DIR/cert.csr" "$backup_path/cert.csr"
    fi
    
    if [ -f "$SSL_DIR/openssl.conf" ]; then
        cp "$SSL_DIR/openssl.conf" "$backup_path/openssl.conf"
    fi
    
    # 创建备份信息文件
    cat > "$backup_path/backup_info.txt" << EOF
备份时间: $(date)
备份名称: $backup_name
证书文件: cert.pem
私钥文件: key.pem
证书大小: $(du -h "$SSL_DIR/cert.pem" | cut -f1)
私钥大小: $(du -h "$SSL_DIR/key.pem" | cut -f1)
证书有效期: $(openssl x509 -in "$SSL_DIR/cert.pem" -noout -enddate | cut -d= -f2)
证书主题: $(openssl x509 -in "$SSL_DIR/cert.pem" -noout -subject | cut -d= -f2-)
EOF
    
    # 设置权限
    chmod 644 "$backup_path/cert.pem"
    chmod 600 "$backup_path/key.pem"
    chmod 644 "$backup_path/backup_info.txt"
    
    log_success "证书备份完成: $backup_path"
    
    # 显示备份信息
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        log_info "备份信息:"
        cat "$backup_path/backup_info.txt" | sed 's/^/  /'
    fi
}

# 恢复证书
restore_certificates() {
    local backup_name="$1"
    local backup_dir="$2"
    local force="$3"
    
    log_info "开始恢复SSL证书..."
    echo "=================================="
    
    # 查找备份
    local backup_path=""
    if [ -n "$backup_name" ]; then
        backup_path="$backup_dir/$backup_name"
        if [ ! -d "$backup_path" ]; then
            log_error "指定的备份不存在: $backup_name"
            return 1
        fi
    else
        # 查找最新的备份
        backup_path=$(find "$backup_dir" -name "backup_*" -type d | sort -r | head -n 1)
        if [ -z "$backup_path" ]; then
            log_error "未找到任何备份"
            return 1
        fi
        backup_name=$(basename "$backup_path")
    fi
    
    log_info "恢复备份: $backup_name"
    
    # 检查备份文件
    if [ ! -f "$backup_path/cert.pem" ] || [ ! -f "$backup_path/key.pem" ]; then
        log_error "备份文件不完整"
        return 1
    fi
    
    # 确认恢复操作
    if [ "$force" != "true" ]; then
        echo -e "${YELLOW}⚠️  这将覆盖当前证书，是否继续？${NC}"
        read -p "输入 y 继续，其他键取消: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            return 0
        fi
    fi
    
    # 备份当前证书
    log_verbose "备份当前证书..."
    backup_certificates "current_before_restore" "$backup_dir" "true" > /dev/null 2>&1 || true
    
    # 恢复证书文件
    log_verbose "恢复证书文件..."
    cp "$backup_path/cert.pem" "$SSL_DIR/cert.pem"
    cp "$backup_path/key.pem" "$SSL_DIR/key.pem"
    
    # 恢复其他文件
    if [ -f "$backup_path/cert.csr" ]; then
        cp "$backup_path/cert.csr" "$SSL_DIR/cert.csr"
    fi
    
    if [ -f "$backup_path/openssl.conf" ]; then
        cp "$backup_path/openssl.conf" "$SSL_DIR/openssl.conf"
    fi
    
    # 设置权限
    chmod 644 "$SSL_DIR/cert.pem"
    chmod 600 "$SSL_DIR/key.pem"
    
    log_success "证书恢复完成"
    
    # 显示恢复信息
    if [ -f "$backup_path/backup_info.txt" ]; then
        echo ""
        log_info "恢复的证书信息:"
        cat "$backup_path/backup_info.txt" | sed 's/^/  /'
    fi
}

# 列出备份
list_backups() {
    local backup_dir="$1"
    
    log_info "列出所有备份..."
    echo "=================================="
    
    if [ ! -d "$backup_dir" ]; then
        log_warning "备份目录不存在: $backup_dir"
        return 0
    fi
    
    local backups=($(find "$backup_dir" -name "backup_*" -type d | sort -r))
    
    if [ ${#backups[@]} -eq 0 ]; then
        log_warning "未找到任何备份"
        return 0
    fi
    
    printf "%-20s %-20s %-15s %-30s\n" "备份名称" "备份时间" "证书大小" "证书主题"
    echo "------------------------------------------------------------------------------------------------"
    
    for backup in "${backups[@]}"; do
        local backup_name=$(basename "$backup")
        local backup_time=$(stat -c %y "$backup" 2>/dev/null || stat -f %Sm "$backup" | cut -d' ' -f1)
        local cert_size="N/A"
        local cert_subject="N/A"
        
        if [ -f "$backup/cert.pem" ]; then
            cert_size=$(du -h "$backup/cert.pem" | cut -f1)
            cert_subject=$(openssl x509 -in "$backup/cert.pem" -noout -subject | cut -d= -f2- | cut -c1-30)
        fi
        
        printf "%-20s %-20s %-15s %-30s\n" "$backup_name" "$backup_time" "$cert_size" "$cert_subject"
    done
}

# 清理旧备份
clean_backups() {
    local backup_dir="$1"
    local keep_count="$2"
    local force="$3"
    
    log_info "清理旧备份..."
    echo "=================================="
    
    if [ ! -d "$backup_dir" ]; then
        log_warning "备份目录不存在: $backup_dir"
        return 0
    fi
    
    local backups=($(find "$backup_dir" -name "backup_*" -type d | sort -r))
    local total_backups=${#backups[@]}
    
    if [ $total_backups -le $keep_count ]; then
        log_info "备份数量 ($total_backups) 不超过保留数量 ($keep_count)，无需清理"
        return 0
    fi
    
    local to_delete=$((total_backups - keep_count))
    
    if [ "$force" != "true" ]; then
        echo -e "${YELLOW}⚠️  将删除 $to_delete 个旧备份，是否继续？${NC}"
        read -p "输入 y 继续，其他键取消: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            return 0
        fi
    fi
    
    # 删除旧备份
    for ((i=keep_count; i<total_backups; i++)); do
        local backup_to_delete="${backups[$i]}"
        log_verbose "删除备份: $(basename "$backup_to_delete")"
        rm -rf "$backup_to_delete"
    done
    
    log_success "已删除 $to_delete 个旧备份"
}

# 导出证书
export_certificates() {
    local export_dir="$1"
    local force="$2"
    
    log_info "导出证书..."
    echo "=================================="
    
    if [ ! -d "$export_dir" ]; then
        log_error "导出目录不存在: $export_dir"
        return 1
    fi
    
    if [ ! -f "$SSL_DIR/cert.pem" ] || [ ! -f "$SSL_DIR/key.pem" ]; then
        log_error "证书文件不存在，无法导出"
        return 1
    fi
    
    # 检查导出目录中的文件
    if [ -f "$export_dir/cert.pem" ] || [ -f "$export_dir/key.pem" ]; then
        if [ "$force" != "true" ]; then
            echo -e "${YELLOW}⚠️  导出目录中已存在证书文件，是否覆盖？${NC}"
            read -p "输入 y 继续，其他键取消: " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "操作已取消"
                return 0
            fi
        fi
    fi
    
    # 导出证书文件
    cp "$SSL_DIR/cert.pem" "$export_dir/"
    cp "$SSL_DIR/key.pem" "$export_dir/"
    
    # 导出其他文件
    if [ -f "$SSL_DIR/cert.csr" ]; then
        cp "$SSL_DIR/cert.csr" "$export_dir/"
    fi
    
    if [ -f "$SSL_DIR/openssl.conf" ]; then
        cp "$SSL_DIR/openssl.conf" "$export_dir/"
    fi
    
    # 设置权限
    chmod 644 "$export_dir/cert.pem"
    chmod 600 "$export_dir/key.pem"
    
    log_success "证书已导出到: $export_dir"
}

# 导入证书
import_certificates() {
    local import_dir="$1"
    local force="$2"
    
    log_info "导入证书..."
    echo "=================================="
    
    if [ ! -d "$import_dir" ]; then
        log_error "导入目录不存在: $import_dir"
        return 1
    fi
    
    if [ ! -f "$import_dir/cert.pem" ] || [ ! -f "$import_dir/key.pem" ]; then
        log_error "导入目录中缺少证书文件"
        return 1
    fi
    
    # 验证证书
    if ! openssl x509 -in "$import_dir/cert.pem" -text -noout > /dev/null 2>&1; then
        log_error "证书文件格式无效"
        return 1
    fi
    
    if ! openssl rsa -in "$import_dir/key.pem" -check -noout > /dev/null 2>&1; then
        log_error "私钥文件格式无效"
        return 1
    fi
    
    # 确认导入操作
    if [ "$force" != "true" ]; then
        echo -e "${YELLOW}⚠️  这将覆盖当前证书，是否继续？${NC}"
        read -p "输入 y 继续，其他键取消: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            return 0
        fi
    fi
    
    # 备份当前证书
    backup_certificates "current_before_import" "$BACKUP_DIR" "true" > /dev/null 2>&1 || true
    
    # 导入证书文件
    cp "$import_dir/cert.pem" "$SSL_DIR/"
    cp "$import_dir/key.pem" "$SSL_DIR/"
    
    # 导入其他文件
    if [ -f "$import_dir/cert.csr" ]; then
        cp "$import_dir/cert.csr" "$SSL_DIR/"
    fi
    
    if [ -f "$import_dir/openssl.conf" ]; then
        cp "$import_dir/openssl.conf" "$SSL_DIR/"
    fi
    
    # 设置权限
    chmod 644 "$SSL_DIR/cert.pem"
    chmod 600 "$SSL_DIR/key.pem"
    
    log_success "证书已导入"
}

# 同步证书到容器
sync_to_container() {
    log_info "同步证书到容器..."
    echo "=================================="
    
    # 检查容器是否运行
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "Nginx容器未运行: $CONTAINER_NAME"
        return 1
    fi
    
    # 检查证书文件
    if [ ! -f "$SSL_DIR/cert.pem" ] || [ ! -f "$SSL_DIR/key.pem" ]; then
        log_error "证书文件不存在，无法同步"
        return 1
    fi
    
    # 复制证书到容器
    docker cp "$SSL_DIR/cert.pem" "$CONTAINER_NAME:/etc/nginx/ssl/cert.pem"
    docker cp "$SSL_DIR/key.pem" "$CONTAINER_NAME:/etc/nginx/ssl/key.pem"
    
    # 设置权限
    docker exec "$CONTAINER_NAME" chmod 644 /etc/nginx/ssl/cert.pem
    docker exec "$CONTAINER_NAME" chmod 600 /etc/nginx/ssl/key.pem
    docker exec "$CONTAINER_NAME" chown root:root /etc/nginx/ssl/cert.pem
    docker exec "$CONTAINER_NAME" chown root:root /etc/nginx/ssl/key.pem
    
    # 重新加载Nginx
    if docker exec "$CONTAINER_NAME" nginx -t; then
        docker exec "$CONTAINER_NAME" nginx -s reload
        log_success "证书已同步到容器并重新加载"
    else
        log_error "Nginx配置测试失败"
        return 1
    fi
}

# 显示备份状态
show_status() {
    log_info "备份状态..."
    echo "=================================="
    
    echo "📁 备份目录: $BACKUP_DIR"
    echo "📁 证书目录: $SSL_DIR"
    echo ""
    
    # 检查当前证书
    if [ -f "$SSL_DIR/cert.pem" ]; then
        echo "📜 当前证书:"
        echo "  文件: $SSL_DIR/cert.pem"
        echo "  大小: $(du -h "$SSL_DIR/cert.pem" | cut -f1)"
        echo "  有效期: $(openssl x509 -in "$SSL_DIR/cert.pem" -noout -enddate | cut -d= -f2)"
        echo "  主题: $(openssl x509 -in "$SSL_DIR/cert.pem" -noout -subject | cut -d= -f2-)"
    else
        echo "📜 当前证书: 无"
    fi
    
    echo ""
    
    # 检查备份
    if [ -d "$BACKUP_DIR" ]; then
        local backup_count=$(find "$BACKUP_DIR" -name "backup_*" -type d | wc -l)
        echo "💾 备份状态:"
        echo "  备份数量: $backup_count"
        echo "  备份目录: $BACKUP_DIR"
        
        if [ $backup_count -gt 0 ]; then
            echo "  最新备份: $(find "$BACKUP_DIR" -name "backup_*" -type d | sort -r | head -n 1 | xargs basename)"
        fi
    else
        echo "💾 备份状态: 无备份"
    fi
}

# 解析命令行参数
parse_arguments() {
    local command="$1"
    shift
    
    local backup_dir="$BACKUP_DIR"
    local backup_name=""
    local keep_count="5"
    local force="false"
    local verbose="false"
    local export_dir=""
    local import_dir=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                backup_dir="$2"
                shift 2
                ;;
            -n|--name)
                backup_name="$2"
                shift 2
                ;;
            -k|--keep)
                keep_count="$2"
                shift 2
                ;;
            -f|--force)
                force="true"
                shift
                ;;
            -v|--verbose)
                verbose="true"
                shift
                ;;
            *)
                if [ -z "$export_dir" ] && [ -z "$import_dir" ]; then
                    if [ "$command" = "export" ]; then
                        export_dir="$1"
                    elif [ "$command" = "import" ]; then
                        import_dir="$1"
                    fi
                fi
                shift
                ;;
        esac
    done
    
    # 设置全局变量
    VERBOSE="$verbose"
    
    # 执行相应命令
    case "$command" in
        backup)
            backup_certificates "$backup_name" "$backup_dir" "$force"
            ;;
        restore)
            restore_certificates "$backup_name" "$backup_dir" "$force"
            ;;
        list)
            list_backups "$backup_dir"
            ;;
        clean)
            clean_backups "$backup_dir" "$keep_count" "$force"
            ;;
        export)
            if [ -z "$export_dir" ]; then
                log_error "请指定导出目录"
                exit 1
            fi
            export_certificates "$export_dir" "$force"
            ;;
        import)
            if [ -z "$import_dir" ]; then
                log_error "请指定导入目录"
                exit 1
            fi
            import_certificates "$import_dir" "$force"
            ;;
        sync)
            sync_to_container
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 主函数
main() {
    echo "💾 SSL证书备份和恢复脚本"
    echo "=================================="
    
    # 检查依赖
    if ! command -v openssl > /dev/null 2>&1; then
        log_error "OpenSSL未安装，请先安装OpenSSL"
        exit 1
    fi
    
    if ! command -v docker > /dev/null 2>&1; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 解析参数并执行
    parse_arguments "$@"
}

# 运行主函数
main "$@"
