#!/bin/bash

# 修复代理配置脚本
# 用于修复生产环境代理配置问题

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}📊 [INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}❌ [ERROR]${NC} $1"
}

# 检查当前环境配置
check_current_config() {
    log_info "检查当前环境配置..."
    
    if [ -f ".env" ]; then
        log_info "当前.env文件内容:"
        echo "----------------------------------------"
        cat .env | grep -E "PROXY|proxy" || echo "未找到代理配置"
        echo "----------------------------------------"
    else
        log_warning "未找到.env文件"
    fi
}

# 修复代理配置
fix_proxy_config() {
    log_info "修复代理配置..."
    
    # 备份现有配置
    if [ -f ".env" ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        log_info "已备份现有配置到 .env.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 从env.production创建.env
    if [ -f "env.production" ]; then
        cp env.production .env
        log_success "已从env.production创建.env文件"
    else
        log_error "未找到env.production文件"
        exit 1
    fi
    
    # 显示修复后的配置
    log_info "修复后的.env文件代理配置:"
    echo "----------------------------------------"
    cat .env | grep -E "PROXY|proxy"
    echo "----------------------------------------"
}

# 测试代理配置
test_proxy_config() {
    log_info "测试代理配置..."
    
    # 加载环境变量
    source .env
    
    # 检查代理配置
    if [ -n "$HTTP_PROXY" ] && [ "$HTTP_PROXY" != "" ]; then
        log_success "代理配置正确: $HTTP_PROXY"
        
        # 测试代理连接
        log_info "测试代理连接..."
        if curl -s --connect-timeout 10 --proxy "$HTTP_PROXY" http://www.google.com > /dev/null 2>&1; then
            log_success "代理连接测试成功"
        else
            log_warning "代理连接测试失败，请检查代理服务器"
        fi
    else
        log_warning "未设置代理配置"
    fi
}

# 显示使用说明
show_usage() {
    log_info "使用说明:"
    echo "1. 运行此脚本修复代理配置"
    echo "2. 根据需要修改.env文件中的代理设置"
    echo "3. 重新运行 ./scripts/docker/start-prod-base.sh"
    echo ""
    echo "代理配置示例:"
    echo "HTTP_PROXY=http://proxy.company.com:8080"
    echo "HTTPS_PROXY=http://proxy.company.com:8080"
    echo "NO_PROXY=localhost,127.0.0.1,::1,internal.company.com"
}

# 主函数
main() {
    echo "🔧 代理配置修复脚本"
    echo "===================="
    
    check_current_config
    fix_proxy_config
    test_proxy_config
    show_usage
    
    log_success "代理配置修复完成！"
}

# 执行主函数
main "$@"
