#!/bin/bash

# 生产环境配置验证脚本
# 验证生产环境配置与测试环境一致

set -e

# 颜色定义
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

# 验证环境配置文件
verify_env_files() {
    log_info "验证环境配置文件..."
    
    # 检查必要文件
    if [ ! -f "env.development" ]; then
        log_error "缺少 env.development 文件"
        return 1
    fi
    
    if [ ! -f "env.production" ]; then
        log_error "缺少 env.production 文件"
        return 1
    fi
    
    # 检查关键配置项
    local dev_cache_type=$(grep "^CACHE_TYPE=" env.development | cut -d'=' -f2)
    local prod_cache_type=$(grep "^CACHE_TYPE=" env.production | cut -d'=' -f2)
    
    if [ "$dev_cache_type" != "$prod_cache_type" ]; then
        log_error "CACHE_TYPE 配置不一致: dev=$dev_cache_type, prod=$prod_cache_type"
        return 1
    fi
    
    local dev_cache_url=$(grep "^CACHE_REDIS_URL=" env.development | cut -d'=' -f2)
    local prod_cache_url=$(grep "^CACHE_REDIS_URL=" env.production | cut -d'=' -f2)
    
    if [ -z "$dev_cache_url" ] || [ -z "$prod_cache_url" ]; then
        log_error "CACHE_REDIS_URL 配置缺失"
        return 1
    fi
    
    log_success "环境配置文件验证通过"
    return 0
}

# 验证Docker Compose文件
verify_docker_compose() {
    log_info "验证Docker Compose文件..."
    
    # 检查必要文件
    if [ ! -f "docker compose.dev.yml" ]; then
        log_error "缺少 docker compose.dev.yml 文件"
        return 1
    fi
    
    if [ ! -f "docker compose.prod.yml" ]; then
        log_error "缺少 docker compose.prod.yml 文件"
        return 1
    fi
    
    # 检查关键环境变量
    local dev_env_vars=$(grep -A 20 "environment:" docker compose.dev.yml | grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL|FLASK_HOST|FLASK_PORT" | wc -l)
    local prod_env_vars=$(grep -A 20 "environment:" docker compose.prod.yml | grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL|FLASK_HOST|FLASK_PORT" | wc -l)
    
    if [ "$dev_env_vars" != "$prod_env_vars" ]; then
        log_error "Docker Compose 环境变量数量不一致: dev=$dev_env_vars, prod=$prod_env_vars"
        return 1
    fi
    
    # 检查FLASK_HOST和FLASK_PORT
    local dev_flask_host=$(grep "FLASK_HOST=" docker compose.dev.yml | cut -d'=' -f2)
    local prod_flask_host=$(grep "FLASK_HOST=" docker compose.prod.yml | cut -d'=' -f2)
    
    if [ "$dev_flask_host" != "$prod_flask_host" ]; then
        log_error "FLASK_HOST 配置不一致: dev=$dev_flask_host, prod=$prod_flask_host"
        return 1
    fi
    
    local dev_flask_port=$(grep "FLASK_PORT=" docker compose.dev.yml | cut -d'=' -f2)
    local prod_flask_port=$(grep "FLASK_PORT=" docker compose.prod.yml | cut -d'=' -f2)
    
    if [ "$dev_flask_port" != "$prod_flask_port" ]; then
        log_error "FLASK_PORT 配置不一致: dev=$dev_flask_port, prod=$prod_flask_port"
        return 1
    fi
    
    log_success "Docker Compose文件验证通过"
    return 0
}

# 验证缓存系统配置
verify_cache_system() {
    log_info "验证缓存系统配置..."
    
    # 检查缓存相关文件
    local cache_files=(
        "app/services/cache_manager.py"
        "app/services/cache_manager_simple.py"
        "app/utils/rate_limiter.py"
    )
    
    for file in "${cache_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "缺少缓存文件: $file"
            return 1
        fi
        
        # 检查是否还有直接Redis连接
        if grep -q "redis_client\|redis\.Redis\|redis\.from_url" "$file"; then
            log_error "文件 $file 中仍有直接Redis连接"
            return 1
        fi
    done
    
    log_success "缓存系统配置验证通过"
    return 0
}

# 显示配置对比
show_config_comparison() {
    log_info "配置对比:"
    echo ""
    echo "测试环境 (env.development):"
    grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL" env.development | sed 's/^/  /'
    echo ""
    echo "生产环境 (env.production):"
    grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL" env.production | sed 's/^/  /'
    echo ""
    echo "Docker Compose 环境变量:"
    echo "  测试环境:"
    grep -A 10 "environment:" docker compose.dev.yml | grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL|FLASK_HOST|FLASK_PORT" | sed 's/^/    /'
    echo "  生产环境:"
    grep -A 10 "environment:" docker compose.prod.yml | grep -E "CACHE_TYPE|CACHE_REDIS_URL|DATABASE_URL|FLASK_HOST|FLASK_PORT" | sed 's/^/    /'
}

# 主函数
main() {
    log_info "开始验证生产环境配置..."
    echo ""
    
    local all_passed=true
    
    if ! verify_env_files; then
        all_passed=false
    fi
    
    if ! verify_docker_compose; then
        all_passed=false
    fi
    
    if ! verify_cache_system; then
        all_passed=false
    fi
    
    echo ""
    show_config_comparison
    
    if [ "$all_passed" = true ]; then
        log_success "所有配置验证通过！生产环境配置与测试环境一致"
    else
        log_error "配置验证失败，请检查上述错误"
        exit 1
    fi
}

# 执行主函数
main "$@"
