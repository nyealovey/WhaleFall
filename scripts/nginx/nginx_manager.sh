#!/bin/bash

# 鲸落 Nginx 管理脚本
# 提供Nginx配置管理、SSL证书上传、配置重载等功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
NGINX_CONTAINER_DEV="whalefall_nginx_dev"
NGINX_CONTAINER_PROD="whalefall_nginx_prod"
NGINX_CONFIG_PATH="/etc/nginx/conf.d/default.conf"
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
    echo "鲸落 Nginx 管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  status [dev|prod]        查看Nginx状态"
    echo "  reload [dev|prod]        重载Nginx配置"
    echo "  restart [dev|prod]       重启Nginx服务"
    echo "  logs [dev|prod]          查看Nginx日志"
    echo "  config [dev|prod]        查看当前配置"
    echo "  reinit-config [dev|prod] 重新初始化配置文件"
    echo "  upload-ssl [dev|prod]    上传SSL证书"
    echo "  generate-ssl [dev|prod]  生成自签名SSL证书"
    echo "  test-config [dev|prod]   测试配置文件"
    echo "  shell [dev|prod]         进入Nginx容器"
    echo ""
    echo "选项:"
    echo "  --config-file FILE       配置文件路径"
    echo "  --cert-file FILE         SSL证书文件路径"
    echo "  --key-file FILE          SSL私钥文件路径"
    echo "  --domain DOMAIN          域名（用于生成SSL证书）"
    echo "  --force                  强制操作"
    echo "  --help                   显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status dev"
    echo "  $0 reinit-config dev"
    echo "  $0 reinit-config prod"
    echo "  $0 upload-ssl prod --cert-file cert.pem --key-file key.pem"
    echo "  $0 generate-ssl dev --domain localhost"
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

# 查看Nginx状态
show_status() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "查看Nginx状态 ($env)..."
    check_container "$container_name"
    
    echo "容器状态:"
    docker ps --filter "name=$container_name" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Nginx进程状态:"
    docker exec "$container_name" ps aux | grep nginx
    
    echo ""
    echo "Nginx配置测试:"
    if docker exec "$container_name" nginx -t 2>/dev/null; then
        log_success "Nginx配置语法正确"
    else
        log_error "Nginx配置语法错误"
    fi
}

# 重载Nginx配置
reload_nginx() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "重载Nginx配置 ($env)..."
    check_container "$container_name"
    
    if docker exec "$container_name" nginx -s reload; then
        log_success "Nginx配置重载成功"
    else
        log_error "Nginx配置重载失败"
        exit 1
    fi
}

# 重启Nginx服务
restart_nginx() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "重启Nginx服务 ($env)..."
    check_container "$container_name"
    
    if docker restart "$container_name"; then
        log_success "Nginx服务重启成功"
    else
        log_error "Nginx服务重启失败"
        exit 1
    fi
}

# 查看Nginx日志
show_logs() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "查看Nginx日志 ($env)..."
    check_container "$container_name"
    
    docker logs -f "$container_name"
}

# 查看当前配置
show_config() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "查看Nginx配置 ($env)..."
    check_container "$container_name"
    
    echo "主配置文件:"
    docker exec "$container_name" cat /etc/nginx/nginx.conf
    
    echo ""
    echo "站点配置:"
    docker exec "$container_name" cat "$NGINX_CONFIG_PATH"
}

# 重新初始化配置（通过环境变量）
reinit_config() {
    local env=$1
    local container_name=$(get_container_name "$env")

    log_info "重新初始化Nginx配置 ($env)..."
    check_container "$container_name"

    # 备份当前配置
    docker exec "$container_name" cp "$NGINX_CONFIG_PATH" "${NGINX_CONFIG_PATH}.backup.$(date +%Y%m%d_%H%M%S)"

    # 设置环境变量并重新运行初始化脚本
    docker exec -e NGINX_ENV="$env" "$container_name" /docker-entrypoint.d/10-nginx-init.sh

    # 测试配置
    if docker exec "$container_name" nginx -t; then
        log_success "配置重新初始化成功"
        if [ "$FORCE" = "true" ]; then
            reload_nginx "$env"
        else
            log_info "请手动重载配置: $0 reload $env"
        fi
    else
        log_error "配置语法错误，已恢复备份"
        docker exec "$container_name" cp "${NGINX_CONFIG_PATH}.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG_PATH"
        exit 1
    fi
}

# 上传SSL证书
upload_ssl() {
    local env=$1
    local cert_file=${CERT_FILE:-""}
    local key_file=${KEY_FILE:-""}
    local container_name=$(get_container_name "$env")
    
    if [ -z "$cert_file" ] || [ -z "$key_file" ]; then
        log_error "请指定证书文件和私钥文件"
        echo "示例: $0 upload-ssl $env --cert-file cert.pem --key-file key.pem"
        exit 1
    fi
    
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        log_error "证书文件或私钥文件不存在"
        exit 1
    fi
    
    log_info "上传SSL证书 ($env)..."
    check_container "$container_name"
    
    # 创建SSL目录
    docker exec "$container_name" mkdir -p "$NGINX_SSL_PATH"
    
    # 上传证书文件
    docker cp "$cert_file" "$container_name:$NGINX_SSL_PATH/cert.pem"
    docker cp "$key_file" "$container_name:$NGINX_SSL_PATH/key.pem"
    
    # 设置权限
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.pem"
    docker exec "$container_name" chmod 600 "$NGINX_SSL_PATH/key.pem"
    
    log_success "SSL证书上传成功"
    log_info "证书文件: $NGINX_SSL_PATH/cert.pem"
    log_info "私钥文件: $NGINX_SSL_PATH/key.pem"
}

# 生成自签名SSL证书
generate_ssl() {
    local env=$1
    local domain=${DOMAIN:-"localhost"}
    local container_name=$(get_container_name "$env")
    
    log_info "生成自签名SSL证书 ($env)..."
    check_container "$container_name"
    
    # 创建SSL目录
    docker exec "$container_name" mkdir -p "$NGINX_SSL_PATH"
    
    # 生成私钥
    docker exec "$container_name" openssl genrsa -out "$NGINX_SSL_PATH/key.pem" 2048
    
    # 生成证书
    docker exec "$container_name" openssl req -new -x509 -key "$NGINX_SSL_PATH/key.pem" -out "$NGINX_SSL_PATH/cert.pem" -days 365 -subj "/C=CN/ST=State/L=City/O=Organization/CN=$domain"
    
    # 设置权限
    docker exec "$container_name" chmod 644 "$NGINX_SSL_PATH/cert.pem"
    docker exec "$container_name" chmod 600 "$NGINX_SSL_PATH/key.pem"
    
    log_success "自签名SSL证书生成成功"
    log_info "域名: $domain"
    log_info "证书文件: $NGINX_SSL_PATH/cert.pem"
    log_info "私钥文件: $NGINX_SSL_PATH/key.pem"
    log_warning "这是自签名证书，浏览器会显示安全警告"
}

# 测试配置文件
test_config() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "测试Nginx配置 ($env)..."
    check_container "$container_name"
    
    if docker exec "$container_name" nginx -t; then
        log_success "Nginx配置语法正确"
    else
        log_error "Nginx配置语法错误"
        exit 1
    fi
}

# 进入Nginx容器
enter_shell() {
    local env=$1
    local container_name=$(get_container_name "$env")
    
    log_info "进入Nginx容器 ($env)..."
    check_container "$container_name"
    
    docker exec -it "$container_name" sh
}

# 主函数
main() {
    local command=$1
    local env=$2
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config-file)
                CONFIG_FILE="$2"
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
            --domain)
                DOMAIN="$2"
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
        status)
            show_status "$env"
            ;;
        reload)
            reload_nginx "$env"
            ;;
        restart)
            restart_nginx "$env"
            ;;
        logs)
            show_logs "$env"
            ;;
        config)
            show_config "$env"
            ;;
        reinit-config)
            reinit_config "$env"
            ;;
        upload-ssl)
            upload_ssl "$env"
            ;;
        generate-ssl)
            generate_ssl "$env"
            ;;
        test-config)
            test_config "$env"
            ;;
        shell)
            enter_shell "$env"
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
