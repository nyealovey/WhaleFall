#!/bin/bash

# 生产镜像容器入口：负责在容器内启动Supervisor，托管Gunicorn与Nginx
# 主要流程：加载环境 -> 准备日志与运行目录 -> 清理残留PID -> 启动supervisord（前台）

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}📊 $1${NC}"
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

load_env_file() {
    local env_file="/app/.env"
    if [ -f "$env_file" ]; then
        # shellcheck disable=SC1090
        set -a
        source "$env_file"
        set +a
        log_info "已加载容器内 .env 文件"
    else
        log_warning ".env 文件未在镜像内找到，将依赖外部注入的环境变量"
    fi
}

prepare_runtime_dirs() {
    log_info "初始化运行目录..."
    mkdir -p /app/userdata/{logs,exports,backups,uploads} /var/log/nginx /var/run
    touch \
        /var/log/nginx/nginx.log \
        /app/userdata/logs/whalefall_web.log \
        /app/userdata/logs/whalefall_web_error.log \
        /app/userdata/logs/whalefall_scheduler.log \
        /app/userdata/logs/whalefall_scheduler_error.log
    log_success "运行目录准备完成"
}

cleanup_stale_pid() {
    log_info "清理残留 PID 文件..."
    rm -f /var/run/nginx.pid /var/run/supervisord.pid || true
    log_success "残留 PID 已清理"
}

verify_frontend_dist() {
    local index_file="/app/frontend/dist/index.html"
    if [ ! -s "$index_file" ]; then
        log_error "React 默认前端构建产物缺失：$index_file"
        log_error "请重新构建生产镜像，确认 Dockerfile.prod 已执行 frontend-build 阶段"
        exit 1
    fi
    log_success "React 默认前端构建产物存在：$index_file"
}

render_nginx_site_config() {
    local template="/etc/nginx/templates/whalefall-prod.template"
    local rendered="/etc/nginx/sites-available/whalefall"
    local enabled="/etc/nginx/sites-enabled/whalefall"
    local variables='${WHALEFALL_NGINX_SERVER_NAMES} ${WHALEFALL_NGINX_SSL_CERTIFICATE} ${WHALEFALL_NGINX_SSL_CERTIFICATE_KEY}'

    if [ ! -f "$template" ]; then
        log_error "缺少 Nginx 站点模板：$template"
        exit 1
    fi

    export WHALEFALL_NGINX_SERVER_NAMES="${WHALEFALL_NGINX_SERVER_NAMES:-example.com www.example.com}"
    export WHALEFALL_NGINX_SSL_CERTIFICATE="${WHALEFALL_NGINX_SSL_CERTIFICATE:-/etc/nginx/ssl/cert.pem}"
    export WHALEFALL_NGINX_SSL_CERTIFICATE_KEY="${WHALEFALL_NGINX_SSL_CERTIFICATE_KEY:-/etc/nginx/ssl/key.pem}"

    log_info "渲染 Nginx 站点配置：server_name=${WHALEFALL_NGINX_SERVER_NAMES}"
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
    envsubst "$variables" < "$template" > "$rendered"
    ln -sf "$rendered" "$enabled"

    if nginx -t; then
        log_success "Nginx 配置校验通过"
    else
        log_error "Nginx 配置校验失败，请检查 WHALEFALL_NGINX_* 与证书挂载"
        exit 1
    fi
}

verify_supervisor_config() {
    local conf="/etc/supervisor/conf.d/whalefall.conf"
    if [ ! -f "$conf" ]; then
        log_error "缺少 $conf，无法启动服务"
        exit 1
    fi
    log_success "Supervisor 配置存在：$conf"
}

start_supervisor() {
    log_info "启动 Supervisor，托管 Nginx 与 Gunicorn..."
    exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
}

main() {
    log_info "容器入口脚本启动，准备生产服务..."
    load_env_file
    prepare_runtime_dirs
    cleanup_stale_pid
    verify_frontend_dist
    render_nginx_site_config
    verify_supervisor_config
    start_supervisor
}

main "$@"
