#!/bin/bash

# 外部SSL证书更新脚本
# 用于将外部购买的SSL证书更新到Nginx容器中

set -e

# 配置变量
CERT_NAME="whalefall.local"
CERT_FILE="${CERT_NAME}.pem"
KEY_FILE="${CERT_NAME}.key"
CONTAINER_NAME="whalefall_nginx_local"
SSL_DIR="nginx/local/ssl"
BACKUP_DIR="nginx/local/ssl/backup"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "🔐 外部SSL证书更新脚本"
    echo "=================================="
    echo "用法: $0 [选项] [证书文件路径]"
    echo ""
    echo "选项:"
    echo "  -c, --cert FILE     证书文件路径 (默认: whalefall.local.pem)"
    echo "  -k, --key FILE      私钥文件路径 (默认: whalefall.local.key)"
    echo "  -n, --name NAME     证书名称 (默认: whalefall.local)"
    echo "  -f, --force         强制更新，不进行备份"
    echo "  -v, --verify        仅验证证书，不更新"
    echo "  -b, --backup        仅备份当前证书"
    echo "  -r, --restore       恢复备份的证书"
    echo "  -h, --help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                                    # 使用默认文件名"
    echo "  $0 -c mycert.pem -k mykey.key        # 指定证书文件"
    echo "  $0 -n mydomain.com                   # 指定证书名称"
    echo "  $0 -v                                # 仅验证证书"
    echo "  $0 -b                                # 备份当前证书"
    echo "  $0 -r                                # 恢复备份证书"
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

# 检查文件是否存在
check_file_exists() {
    local file_path="$1"
    local file_name="$2"
    
    if [ ! -f "$file_path" ]; then
        log_error "$file_name 文件不存在: $file_path"
        return 1
    fi
    return 0
}

# 验证证书文件
verify_certificate() {
    local cert_file="$1"
    local key_file="$2"
    
    log_info "验证证书文件..."
    
    # 验证证书格式
    if ! openssl x509 -in "$cert_file" -text -noout > /dev/null 2>&1; then
        log_error "证书文件格式无效: $cert_file"
        return 1
    fi
    
    # 验证私钥格式
    if ! openssl rsa -in "$key_file" -check -noout > /dev/null 2>&1; then
        log_error "私钥文件格式无效: $key_file"
        return 1
    fi
    
    # 验证证书和私钥是否匹配
    local cert_mod=$(openssl x509 -noout -modulus -in "$cert_file" | openssl md5)
    local key_mod=$(openssl rsa -noout -modulus -in "$key_file" | openssl md5)
    
    if [ "$cert_mod" != "$key_mod" ]; then
        log_error "证书和私钥不匹配"
        return 1
    fi
    
    # 检查证书有效期
    if ! openssl x509 -in "$cert_file" -checkend 0 > /dev/null 2>&1; then
        log_warning "证书已过期"
    fi
    
    log_success "证书验证通过"
    return 0
}

# 显示证书信息
show_cert_info() {
    local cert_file="$1"
    
    log_info "证书信息:"
    echo "=================================="
    
    # 证书详情
    openssl x509 -in "$cert_file" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)" | sed 's/^/  /'
    
    echo ""
    log_info "文件信息:"
    echo "  证书文件: $cert_file"
    echo "  文件大小: $(du -h "$cert_file" | cut -f1)"
    echo "  修改时间: $(stat -c %y "$cert_file" 2>/dev/null || stat -f %Sm "$cert_file")"
}

# 备份当前证书
backup_current_cert() {
    log_info "备份当前证书..."
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 备份证书文件
    if [ -f "$SSL_DIR/cert.pem" ]; then
        cp "$SSL_DIR/cert.pem" "$BACKUP_DIR/cert.pem.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "证书文件已备份"
    fi
    
    if [ -f "$SSL_DIR/key.pem" ]; then
        cp "$SSL_DIR/key.pem" "$BACKUP_DIR/key.pem.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "私钥文件已备份"
    fi
    
    # 清理旧备份（保留最近5个）
    find "$BACKUP_DIR" -name "*.backup.*" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null || true
    
    log_success "备份完成"
}

# 恢复备份证书
restore_backup_cert() {
    log_info "恢复备份证书..."
    
    # 查找最新的备份文件
    local latest_cert=$(find "$BACKUP_DIR" -name "cert.pem.backup.*" -type f | sort -r | head -n 1)
    local latest_key=$(find "$BACKUP_DIR" -name "key.pem.backup.*" -type f | sort -r | head -n 1)
    
    if [ -z "$latest_cert" ] || [ -z "$latest_key" ]; then
        log_error "未找到备份证书文件"
        return 1
    fi
    
    # 恢复证书文件
    cp "$latest_cert" "$SSL_DIR/cert.pem"
    cp "$latest_key" "$SSL_DIR/key.pem"
    
    log_success "证书已恢复: $(basename "$latest_cert")"
    return 0
}

# 更新证书到容器
update_cert_in_container() {
    local cert_file="$1"
    local key_file="$2"
    
    log_info "更新证书到容器..."
    
    # 检查容器是否运行
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "Nginx容器未运行: $CONTAINER_NAME"
        log_info "请先启动Nginx容器: docker-compose -f docker-compose.local.yml up -d"
        return 1
    fi
    
    # 复制证书文件到容器
    docker cp "$cert_file" "$CONTAINER_NAME:/etc/nginx/ssl/cert.pem"
    docker cp "$key_file" "$CONTAINER_NAME:/etc/nginx/ssl/key.pem"
    
    # 设置正确的权限
    docker exec "$CONTAINER_NAME" chmod 644 /etc/nginx/ssl/cert.pem
    docker exec "$CONTAINER_NAME" chmod 600 /etc/nginx/ssl/key.pem
    docker exec "$CONTAINER_NAME" chown root:root /etc/nginx/ssl/cert.pem
    docker exec "$CONTAINER_NAME" chown root:root /etc/nginx/ssl/key.pem
    
    log_success "证书已更新到容器"
}

# 重启Nginx容器
restart_nginx() {
    log_info "重启Nginx容器..."
    
    # 测试Nginx配置
    if ! docker exec "$CONTAINER_NAME" nginx -t; then
        log_error "Nginx配置测试失败"
        return 1
    fi
    
    # 重新加载Nginx配置
    docker exec "$CONTAINER_NAME" nginx -s reload
    
    log_success "Nginx已重新加载"
}

# 测试HTTPS连接
test_https_connection() {
    log_info "测试HTTPS连接..."
    
    # 等待Nginx重新加载
    sleep 2
    
    # 测试HTTPS连接
    if curl -s -k https://localhost/health > /dev/null 2>&1; then
        log_success "HTTPS连接测试通过"
    else
        log_warning "HTTPS连接测试失败，请检查配置"
    fi
}

# 主更新函数
update_certificate() {
    local cert_file="$1"
    local key_file="$2"
    local force_update="$3"
    
    log_info "开始更新SSL证书..."
    echo "=================================="
    
    # 检查文件是否存在
    if ! check_file_exists "$cert_file" "证书文件"; then
        return 1
    fi
    
    if ! check_file_exists "$key_file" "私钥文件"; then
        return 1
    fi
    
    # 验证证书
    if ! verify_certificate "$cert_file" "$key_file"; then
        return 1
    fi
    
    # 显示证书信息
    show_cert_info "$cert_file"
    
    # 备份当前证书（除非强制更新）
    if [ "$force_update" != "true" ]; then
        backup_current_cert
    fi
    
    # 复制证书文件到本地目录
    log_info "复制证书文件到本地目录..."
    mkdir -p "$SSL_DIR"
    cp "$cert_file" "$SSL_DIR/cert.pem"
    cp "$key_file" "$SSL_DIR/key.pem"
    
    # 设置正确的权限
    chmod 644 "$SSL_DIR/cert.pem"
    chmod 600 "$SSL_DIR/key.pem"
    
    # 更新容器中的证书
    if ! update_cert_in_container "$cert_file" "$key_file"; then
        return 1
    fi
    
    # 重启Nginx
    if ! restart_nginx; then
        return 1
    fi
    
    # 测试连接
    test_https_connection
    
    log_success "SSL证书更新完成！"
    echo ""
    log_info "访问地址:"
    echo "  https://localhost"
    echo "  https://localhost/admin"
    echo ""
    log_info "管理命令:"
    echo "  查看日志: docker-compose -f docker-compose.local.yml logs nginx"
    echo "  重启服务: docker-compose -f docker-compose.local.yml restart"
}

# 解析命令行参数
parse_arguments() {
    local cert_file="$CERT_FILE"
    local key_file="$KEY_FILE"
    local cert_name="$CERT_NAME"
    local force_update="false"
    local verify_only="false"
    local backup_only="false"
    local restore_only="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--cert)
                cert_file="$2"
                shift 2
                ;;
            -k|--key)
                key_file="$2"
                shift 2
                ;;
            -n|--name)
                cert_name="$2"
                shift 2
                ;;
            -f|--force)
                force_update="true"
                shift
                ;;
            -v|--verify)
                verify_only="true"
                shift
                ;;
            -b|--backup)
                backup_only="true"
                shift
                ;;
            -r|--restore)
                restore_only="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                # 如果没有指定选项，将参数作为证书文件路径
                if [ -z "$cert_file" ] || [ "$cert_file" = "$CERT_FILE" ]; then
                    cert_file="$1"
                    key_file="${1%.*}.key"
                fi
                shift
                ;;
        esac
    done
    
    # 执行相应操作
    if [ "$verify_only" = "true" ]; then
        if check_file_exists "$cert_file" "证书文件" && check_file_exists "$key_file" "私钥文件"; then
            verify_certificate "$cert_file" "$key_file"
            show_cert_info "$cert_file"
        fi
    elif [ "$backup_only" = "true" ]; then
        backup_current_cert
    elif [ "$restore_only" = "true" ]; then
        restore_backup_cert
    else
        update_certificate "$cert_file" "$key_file" "$force_update"
    fi
}

# 主函数
main() {
    echo "🔐 外部SSL证书更新脚本"
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
