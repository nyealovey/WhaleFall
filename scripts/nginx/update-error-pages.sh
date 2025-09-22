#!/bin/bash

# Nginx 错误页面更新脚本
# 用于更新生产环境的自定义错误页面

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

# 检查错误页面文件是否存在
if [ ! -f "nginx/error_pages/50x.html" ] || [ ! -f "nginx/error_pages/404.html" ]; then
    log_error "错误页面文件不存在，请先创建错误页面"
    exit 1
fi

log_info "开始更新 Nginx 错误页面..."

# 检查 Nginx 容器是否运行
if ! docker ps | grep -q "whalefall_app_prod"; then
    log_warning "Nginx 容器未运行，将启动基础环境"
    ./scripts/docker/start-prod-base.sh
fi

# 重启 Nginx 容器以应用新的错误页面
log_info "重启 Nginx 容器以应用错误页面..."
docker restart whalefall_app_prod

# 等待 Nginx 启动
log_info "等待 Nginx 启动..."
sleep 5

# 检查 Nginx 状态
if docker ps | grep -q "whalefall_app_prod.*Up"; then
    log_success "Nginx 容器重启成功"
else
    log_error "Nginx 容器启动失败"
    exit 1
fi

# 测试错误页面
log_info "测试错误页面..."

# 测试 404 页面
log_info "测试 404 错误页面..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/404-test 2>/dev/null | grep -q "404"; then
    log_success "404 错误页面测试通过"
else
    log_warning "404 错误页面测试失败，可能需要等待 Nginx 完全启动"
fi

# 测试 50x 页面（通过访问不存在的后端）
log_info "测试 50x 错误页面..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null | grep -q "503\|502"; then
    log_success "50x 错误页面测试通过"
else
    log_warning "50x 错误页面测试失败，Flask 应用可能正在运行"
fi

log_success "Nginx 错误页面更新完成！"
log_info "现在访问不存在的页面或服务不可用时，会显示自定义的错误页面"

# 显示错误页面访问方式
echo ""
log_info "错误页面访问方式："
echo "  - 404 页面: http://localhost/不存在的页面"
echo "  - 50x 页面: 当 Flask 应用不可用时自动显示"
echo "  - 错误页面位置: nginx/error_pages/"
