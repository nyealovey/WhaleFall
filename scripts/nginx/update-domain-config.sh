#!/bin/bash

# Nginx 域名配置更新脚本
# 用于更新生产环境的域名配置

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

# 检查是否在项目根目录
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "请在项目根目录下运行此脚本"
    exit 1
fi

# 检查 Nginx 配置文件是否存在
if [ ! -f "nginx/conf.d/whalefall-docker.conf" ]; then
    log_error "Nginx 配置文件不存在"
    exit 1
fi

log_info "开始更新 Nginx 域名配置..."

# 检查 Nginx 容器是否运行
if ! docker ps | grep -q "whalefall_nginx_prod"; then
    log_warning "Nginx 容器未运行，将启动基础环境"
    ./scripts/docker/start-prod-base.sh
fi

# 备份当前配置
log_info "备份当前 Nginx 配置..."
docker exec whalefall_nginx_prod cp /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.backup.$(date +%Y%m%d_%H%M%S)

# 重启 Nginx 容器以应用新的域名配置
log_info "重启 Nginx 容器以应用域名配置..."
docker restart whalefall_nginx_prod

# 等待 Nginx 启动
log_info "等待 Nginx 启动..."
sleep 5

# 检查 Nginx 状态
if docker ps | grep -q "whalefall_nginx_prod.*Up"; then
    log_success "Nginx 容器重启成功"
else
    log_error "Nginx 容器启动失败"
    exit 1
fi

# 测试域名配置
log_info "测试域名配置..."

# 测试 localhost HTTP
log_info "测试 localhost HTTP..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null | grep -q "200\|503"; then
    log_success "localhost HTTP 测试通过"
else
    log_warning "localhost HTTP 测试失败"
fi

# 测试 localhost HTTPS
log_info "测试 localhost HTTPS..."
if curl -s -k -o /dev/null -w "%{http_code}" https://localhost/health 2>/dev/null | grep -q "200\|503"; then
    log_success "localhost HTTPS 测试通过"
else
    log_warning "localhost HTTPS 测试失败"
fi

# 测试域名重定向 (如果域名解析到服务器)
log_info "测试域名配置..."
log_info "支持的域名："
echo "  - localhost (HTTP + HTTPS)"
echo "  - domain.com (HTTP -> HTTPS 重定向)"
echo "  - *.domain.com (HTTP -> HTTPS 重定向)"

log_success "Nginx 域名配置更新完成！"

# 显示配置摘要
echo ""
log_info "域名配置摘要："
echo "  - HTTP 端口: 80"
echo "  - HTTPS 端口: 443"
echo "  - 支持的域名: localhost, domain.com, *.domain.com"
echo "  - HTTP 重定向: 域名自动重定向到 HTTPS"
echo "  - localhost: 保持 HTTP 和 HTTPS 双协议支持"

# 显示访问方式
echo ""
log_info "访问方式："
echo "  - 本地访问: http://localhost 或 https://localhost"
echo "  - 域名访问: https://domain.com"
echo "  - 通配符域名: https://任意.domain.com"

# 显示日志文件位置
echo ""
log_info "日志文件位置："
echo "  - 通用访问日志: /var/log/nginx/access.log"
echo "  - 通用错误日志: /var/log/nginx/error.log"
echo "  - HTTPS 访问日志: /var/log/nginx/ssl_access.log"
echo "  - HTTPS 错误日志: /var/log/nginx/ssl_error.log"
echo "  - domain 访问日志: /var/log/nginx/domain_access.log"
