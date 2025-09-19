#!/bin/bash

# 部署方案测试脚本
# 用于验证两部分部署方案的功能

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 测试环境配置
test_environment_config() {
    log_info "测试环境配置..."
    
    # 检查环境文件
    if [ ! -f ".env" ]; then
        if [ -f "env.production" ]; then
            log_info "复制生产环境配置文件..."
            cp env.production .env
        else
            log_error "未找到环境配置文件"
            return 1
        fi
    fi
    
    # 检查必要的环境变量
    source .env
    
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "缺少必要的环境变量: ${missing_vars[*]}"
        return 1
    fi
    
    log_success "环境配置测试通过"
}

# 测试Docker配置
test_docker_config() {
    log_info "测试Docker配置..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        return 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装"
        return 1
    fi
    
    # 检查配置文件
    if [ ! -f "docker-compose.base.yml" ]; then
        log_error "docker-compose.base.yml不存在"
        return 1
    fi
    
    if [ ! -f "docker-compose.flask.yml" ]; then
        log_error "docker-compose.flask.yml不存在"
        return 1
    fi
    
    # 验证配置文件语法
    if ! docker-compose -f docker-compose.base.yml config &>/dev/null; then
        log_error "docker-compose.base.yml配置语法错误"
        return 1
    fi
    
    if ! docker-compose -f docker-compose.flask.yml config &>/dev/null; then
        log_error "docker-compose.flask.yml配置语法错误"
        return 1
    fi
    
    log_success "Docker配置测试通过"
}

# 测试部署脚本
test_deployment_scripts() {
    log_info "测试部署脚本..."
    
    local scripts=(
        "scripts/deploy-base.sh"
        "scripts/deploy-flask.sh"
        "scripts/start-all.sh"
        "scripts/stop-all.sh"
        "scripts/update-version.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_error "脚本不存在: $script"
            return 1
        fi
        
        if [ ! -x "$script" ]; then
            log_warning "脚本没有执行权限: $script"
            chmod +x "$script"
        fi
        
        # 检查脚本语法
        if ! bash -n "$script"; then
            log_error "脚本语法错误: $script"
            return 1
        fi
    done
    
    log_success "部署脚本测试通过"
}

# 测试Makefile
test_makefile() {
    log_info "测试Makefile..."
    
    if [ ! -f "Makefile" ]; then
        log_error "Makefile不存在"
        return 1
    fi
    
    # 检查Makefile语法
    if ! make -n help &>/dev/null; then
        log_error "Makefile语法错误"
        return 1
    fi
    
    log_success "Makefile测试通过"
}

# 测试文档
test_documentation() {
    log_info "测试文档..."
    
    local docs=(
        "docs/deployment/PRODUCTION_TWO_PART_DEPLOYMENT.md"
        "docs/deployment/DEPLOYMENT_SUMMARY.md"
        "README.md"
    )
    
    for doc in "${docs[@]}"; do
        if [ ! -f "$doc" ]; then
            log_error "文档不存在: $doc"
            return 1
        fi
    done
    
    log_success "文档测试通过"
}

# 测试基础环境配置
test_base_environment() {
    log_info "测试基础环境配置..."
    
    # 检查端口占用
    local ports=(80 443 5432 6379)
    for port in "${ports[@]}"; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            log_warning "端口 $port 已被占用"
        fi
    done
    
    # 检查数据目录权限
    if [ ! -d "/opt/whale_fall_data" ]; then
        log_warning "数据目录不存在，将在部署时创建"
    else
        log_info "数据目录已存在"
    fi
    
    # 验证配置文件语法
    if ! docker-compose -f docker-compose.base.yml config &>/dev/null; then
        log_error "基础环境配置语法错误"
        return 1
    fi
    
    log_success "基础环境配置测试通过"
    log_warning "注意：在macOS上需要配置Docker Desktop文件共享路径"
}

# 显示测试结果
show_test_results() {
    log_info "测试结果："
    echo "=================================="
    echo "✅ 环境配置测试通过"
    echo "✅ Docker配置测试通过"
    echo "✅ 部署脚本测试通过"
    echo "✅ Makefile测试通过"
    echo "✅ 文档测试通过"
    echo "✅ 基础环境测试通过"
    echo "=================================="
    
    log_info "部署方案验证完成！"
    echo ""
    log_info "下一步操作："
    echo "  1. 编辑 .env 文件设置必要的环境变量"
    echo "  2. 运行 make all 启动所有服务"
    echo "  3. 访问 http://localhost 查看应用"
    echo ""
    log_warning "注意事项："
    echo "  - 请确保端口80、443、5432、6379未被占用"
    echo "  - 请设置强密码保护数据库和Redis"
    echo "  - 生产环境请配置SSL证书"
}

# 主函数
main() {
    echo "🧪 鲸落部署方案测试脚本"
    echo "=================================="
    
    test_environment_config
    test_docker_config
    test_deployment_scripts
    test_makefile
    test_documentation
    test_base_environment
    show_test_results
    
    echo "=================================="
    log_success "所有测试通过！"
    echo "=================================="
}

# 运行主函数
main "$@"
