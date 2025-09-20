#!/bin/bash

# 鲸落 SSL 证书管理脚本
# 提供SSL证书生成、上传、管理等功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
SSL_DIR="./nginx/ssl"
NGINX_CONTAINER_DEV="whalefall_nginx_dev"
NGINX_CONTAINER_PROD="whalefall_nginx_prod"
NGINX_SSL_PATH="/etc/nginx/ssl"

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

# 显示使用说明
show_usage() {
    echo "鲸落 SSL 证书管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  generate [dev|prod]       生成自签名SSL证书"
    echo "  upload [dev|prod]         上传SSL证书到容器"
    echo "  download [dev|prod]       从容器下载SSL证书"
    echo "  list [dev|prod]           列出SSL证书"
    echo "  verify [dev|prod]         验证SSL证书"
    echo "  renew [dev|prod]          续期SSL证书"
    echo "  backup [dev|prod]         备份SSL证书"
    echo "  restore [dev|prod]        恢复SSL证书"
    echo ""
    echo "选项:"
    echo "  --domain DOMAIN           域名 (默认: localhost)"
    echo "  --days DAYS               证书有效期天数 (默认: 365)"
    echo "  --key-size SIZE           密钥长度 (默认: 2048)"
    echo "  --cert-file FILE          证书文件路径"
    echo "  --key-file FILE           私钥文件路径"
    echo "  --backup-dir DIR          备份目录 (默认: ./backups/ssl)"
    echo "  --force                   强制操作"
    echo "  --help                    显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 generate dev --domain localhost"
    echo "  $0 upload prod --cert-file cert.pem --key-file key.pem"
    echo "  $0 generate prod --domain example.com --days 730"
}

# 获取容器名称
get_container_name() {
    local env=$1
    if [ "$env" = "dev" ]; then
        echo "$NGINX_CONTAINER_DEV"
    elif [ "$env" = "prod" ]; then
        echo "$NGINX_CONTAINER_PROD"
    else
        log_error "请指定环境: dev 或 prod"
        exit 1
    fi
}

# 检查容器是否运行
check_container() {
    local container_name=$1
    if ! docker ps | grep -q "$container_name"; then
        log_error "容器 $container_name 未运行"
        exit 1
    fi
}

# 创建SSL目录
create_ssl_dir() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "创建SSL目录..."
    check_container "$container_name"
    
    docker exec "$container_name" mkdir -p "$NGINX_SSL_PATH"
    docker exec "$container_name" chmod 755 "$NGINX_SSL_PATH"
    
    log_success "SSL目录创建成功"
}

# 生成自签名SSL证书
generate_ssl() {
    local env=$1
    local domain=${DOMAIN:-"localhost"}
    local days=${DAYS:-365}
    local key_size=${KEY_SIZE:-2048}
    local container_name=$(get_container_name "$env")
    
    log_info "生成自签名SSL证书 ($env)..."
    log_info "域名: $domain"
    log_info "有效期: $days 天"
    log_info "密钥长度: $key_size 位"
    
    check_container "$container_name"
    create_ssl_dir "$env"
    
    # 生成私钥
    log_info "生成私钥..."
    docker exec "$container_name" openssl genrsa -out "$NGINX_SSL_PATH/key.pem" "$key_size"
    
    # 生成证书签名请求
    log_info "生成证书签名请求..."
    docker exec "$container_name" openssl req -new -key "$NGINX_SSL_PATH/key.pem" -out "$NGINX_SSL_PATH/cert.csr" -subj "/C=CN/ST=State/L=City/O=Organization/CN=$domain"
    
    # 生成自签名证书
    log_info "生成自签名证书..."
    docker exec "$container_name" openssl x509 -req -in "$NGINX_SSL_PATH/cert.csr" -signkey "$NGINX_SSL_PATH/key.pem" -out "$NGINX_SSL_PATH/cert.pem" -days "$days"
    
    # 设置权限
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.pem"
    docker exec "$container_name" chmod 600 "$NGINX_SSL_PATH/key.pem"
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.csr"
    
    # 生成证书链文件（与证书相同）
    docker exec "$container_name" cp "$NGINX_SSL_PATH/cert.pem" "$NGINX_SSL_PATH/chain.pem"
    
    log_success "自签名SSL证书生成成功"
    log_info "证书文件: $NGINX_SSL_PATH/cert.pem"
    log_info "私钥文件: $NGINX_SSL_PATH/key.pem"
    log_info "证书请求: $NGINX_SSL_PATH/cert.csr"
    log_warning "这是自签名证书，浏览器会显示安全警告"
}

# 上传SSL证书
upload_ssl() {
    local env=$1
    local cert_file=${CERT_FILE:-""}
    local key_file=${KEY_FILE:-""}
    local container_name=$(get_container_name "$env")
    
    if [ -z "$cert_file" ] || [ -z "$key_file" ]; then
        log_error "请指定证书文件和私钥文件"
        echo "示例: $0 upload $env --cert-file cert.pem --key-file key.pem"
        exit 1
    fi
    
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        log_error "证书文件或私钥文件不存在"
        exit 1
    fi
    
    log_info "上传SSL证书 ($env)..."
    check_container "$container_name"
    create_ssl_dir "$env"
    
    # 备份现有证书
    if docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
        log_info "备份现有证书..."
        docker exec "$container_name" cp "$NGINX_SSL_PATH/cert.pem" "$NGINX_SSL_PATH/cert.pem.backup.$(date +%Y%m%d_%H%M%S)"
        docker exec "$container_name" cp "$NGINX_SSL_PATH/key.pem" "$NGINX_SSL_PATH/key.pem.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 上传证书文件
    log_info "上传证书文件..."
    docker cp "$cert_file" "$container_name:$NGINX_SSL_PATH/cert.pem"
    docker cp "$key_file" "$container_name:$NGINX_SSL_PATH/key.pem"
    
    # 设置权限
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.pem"
    docker exec "$container_name" chmod 600 "$NGINX_SSL_PATH/key.pem"
    
    # 验证证书
    if verify_ssl "$env"; then
        log_success "SSL证书上传成功"
    else
        log_error "SSL证书验证失败，已恢复备份"
        docker exec "$container_name" cp "$NGINX_SSL_PATH/cert.pem.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_SSL_PATH/cert.pem"
        docker exec "$container_name" cp "$NGINX_SSL_PATH/key.pem.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_SSL_PATH/key.pem"
        exit 1
    fi
}

# 下载SSL证书
download_ssl() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "下载SSL证书 ($env)..."
    check_container "$container_name"
    
    # 创建本地SSL目录
    mkdir -p "$SSL_DIR"
    
    # 下载证书文件
    if docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
        docker cp "$container_name:$NGINX_SSL_PATH/cert.pem" "$SSL_DIR/cert.pem"
        docker cp "$container_name:$NGINX_SSL_PATH/key.pem" "$SSL_DIR/key.pem"
        log_success "SSL证书下载成功"
        log_info "证书文件: $SSL_DIR/cert.pem"
        log_info "私钥文件: $SSL_DIR/key.pem"
    else
        log_error "容器中未找到SSL证书"
        exit 1
    fi
}

# 列出SSL证书
list_ssl() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "列出SSL证书 ($env)..."
    check_container "$container_name"
    
    if docker exec "$container_name" test -d "$NGINX_SSL_PATH"; then
        echo "SSL证书文件:"
        docker exec "$container_name" ls -la "$NGINX_SSL_PATH"
        
        echo ""
        echo "证书信息:"
        if docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
            docker exec "$container_name" openssl x509 -in "$NGINX_SSL_PATH/cert.pem" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"
        else
            log_warning "未找到证书文件"
        fi
    else
        log_warning "SSL目录不存在"
    fi
}

# 验证SSL证书
verify_ssl() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "验证SSL证书 ($env)..."
    check_container "$container_name"
    
    if ! docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
        log_error "证书文件不存在"
        return 1
    fi
    
    if ! docker exec "$container_name" test -f "$NGINX_SSL_PATH/key.pem"; then
        log_error "私钥文件不存在"
        return 1
    fi
    
    # 验证证书格式
    if ! docker exec "$container_name" openssl x509 -in "$NGINX_SSL_PATH/cert.pem" -text -noout >/dev/null 2>&1; then
        log_error "证书格式错误"
        return 1
    fi
    
    # 验证私钥格式
    if ! docker exec "$container_name" openssl rsa -in "$NGINX_SSL_PATH/key.pem" -check >/dev/null 2>&1; then
        log_error "私钥格式错误"
        return 1
    fi
    
    # 验证证书和私钥匹配
    local cert_hash=$(docker exec "$container_name" openssl x509 -noout -modulus -in "$NGINX_SSL_PATH/cert.pem" | openssl md5)
    local key_hash=$(docker exec "$container_name" openssl rsa -noout -modulus -in "$NGINX_SSL_PATH/key.pem" | openssl md5)
    
    if [ "$cert_hash" = "$key_hash" ]; then
        log_success "SSL证书验证成功"
        return 0
    else
        log_error "证书和私钥不匹配"
        return 1
    fi
}

# 续期SSL证书
renew_ssl() {
    local env=$1
    local days=${DAYS:-365}
    local container_name=$(get_container_name "$env")
    
    log_info "续期SSL证书 ($env)..."
    check_container "$container_name"
    
    if ! docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
        log_error "证书文件不存在，无法续期"
        exit 1
    fi
    
    # 获取当前证书信息
    local subject=$(docker exec "$container_name" openssl x509 -in "$NGINX_SSL_PATH/cert.pem" -noout -subject | sed 's/^subject=//')
    
    # 备份现有证书
    docker exec "$container_name" cp "$NGINX_SSL_PATH/cert.pem" "$NGINX_SSL_PATH/cert.pem.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 生成新证书
    docker exec "$container_name" openssl x509 -req -in "$NGINX_SSL_PATH/cert.csr" -signkey "$NGINX_SSL_PATH/key.pem" -out "$NGINX_SSL_PATH/cert.pem" -days "$days"
    
    # 验证新证书
    if verify_ssl "$env"; then
        log_success "SSL证书续期成功"
    else
        log_error "SSL证书续期失败，已恢复备份"
        docker exec "$container_name" cp "$NGINX_SSL_PATH/cert.pem.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_SSL_PATH/cert.pem"
        exit 1
    fi
}

# 备份SSL证书
backup_ssl() {
    local env=$1
    local backup_dir=${BACKUP_DIR:-"./backups/ssl"}
    local container_name=$(get_container_name "$env")
    
    log_info "备份SSL证书 ($env)..."
    check_container "$container_name"
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    # 备份证书文件
    if docker exec "$container_name" test -f "$NGINX_SSL_PATH/cert.pem"; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        docker cp "$container_name:$NGINX_SSL_PATH/cert.pem" "$backup_dir/cert_${env}_${timestamp}.pem"
        docker cp "$container_name:$NGINX_SSL_PATH/key.pem" "$backup_dir/key_${env}_${timestamp}.pem"
        log_success "SSL证书备份成功"
        log_info "备份目录: $backup_dir"
    else
        log_error "未找到SSL证书文件"
        exit 1
    fi
}

# 恢复SSL证书
restore_ssl() {
    local env=$1
    local backup_dir=${BACKUP_DIR:-"./backups/ssl"}
    local container_name=$(get_container_name "$env")
    
    log_info "恢复SSL证书 ($env)..."
    check_container "$container_name"
    
    if [ ! -d "$backup_dir" ]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi
    
    # 查找最新的备份文件
    local cert_file=$(ls -t "$backup_dir"/cert_${env}_*.pem 2>/dev/null | head -n1)
    local key_file=$(ls -t "$backup_dir"/key_${env}_*.pem 2>/dev/null | head -n1)
    
    if [ -z "$cert_file" ] || [ -z "$key_file" ]; then
        log_error "未找到备份文件"
        exit 1
    fi
    
    log_info "恢复证书文件: $cert_file"
    log_info "恢复私钥文件: $key_file"
    
    # 上传证书文件
    docker cp "$cert_file" "$container_name:$NGINX_SSL_PATH/cert.pem"
    docker cp "$key_file" "$container_name:$NGINX_SSL_PATH/key.pem"
    
    # 设置权限
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.pem"
    docker exec "$container_name" chmod 600 "$NGINX_SSL_PATH/key.pem"
    
    # 验证证书
    if verify_ssl "$env"; then
        log_success "SSL证书恢复成功"
    else
        log_error "SSL证书恢复失败"
        exit 1
    fi
}

# 主函数
main() {
    local command=$1
    local env=$2
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --days)
                DAYS="$2"
                shift 2
                ;;
            --key-size)
                KEY_SIZE="$2"
                shift 2
                ;;
            --cert-file)
                CERT_FILE="$2"
                shift 2
                ;;
            --key-file)
                KEY_FILE="$2"
                shift 2
                ;;
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
        generate)
            generate_ssl "$env"
            ;;
        upload)
            upload_ssl "$env"
            ;;
        download)
            download_ssl "$env"
            ;;
        list)
            list_ssl "$env"
            ;;
        verify)
            verify_ssl "$env"
            ;;
        renew)
            renew_ssl "$env"
            ;;
        backup)
            backup_ssl "$env"
            ;;
        restore)
            restore_ssl "$env"
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
