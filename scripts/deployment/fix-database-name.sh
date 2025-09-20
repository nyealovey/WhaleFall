#!/bin/bash

# 修复生产环境数据库名称问题
# 将 whalefall_dev 数据库重命名为 whalefall_prod

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
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

log_info "开始修复生产环境数据库名称问题..."

# 检查PostgreSQL容器是否运行
if ! docker compose -f docker-compose.prod.yml ps postgres | grep -q "Up"; then
    log_error "PostgreSQL容器未运行，请先启动服务"
    exit 1
fi

# 检查是否存在 whalefall_dev 数据库
if docker compose -f docker-compose.prod.yml exec postgres psql -U whalefall_user -d whalefall_dev -c "SELECT 1;" > /dev/null 2>&1; then
    log_info "发现 whalefall_dev 数据库，开始重命名..."
    
    # 重命名数据库
    docker compose -f docker-compose.prod.yml exec postgres psql -U whalefall_user -d postgres -c "ALTER DATABASE whalefall_dev RENAME TO whalefall_prod;"
    
    if [ $? -eq 0 ]; then
        log_success "数据库重命名成功：whalefall_dev -> whalefall_prod"
    else
        log_error "数据库重命名失败"
        exit 1
    fi
else
    log_info "whalefall_dev 数据库不存在，检查 whalefall_prod 数据库..."
    
    # 检查是否存在 whalefall_prod 数据库
    if docker compose -f docker-compose.prod.yml exec postgres psql -U whalefall_user -d whalefall_prod -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "whalefall_prod 数据库已存在"
    else
        log_error "whalefall_prod 数据库不存在，请检查数据库初始化"
        exit 1
    fi
fi

# 验证修复结果
log_info "验证修复结果..."
if docker compose -f docker-compose.prod.yml exec postgres psql -U whalefall_user -d whalefall_prod -c "SELECT 1;" > /dev/null 2>&1; then
    log_success "数据库连接测试成功"
else
    log_error "数据库连接测试失败"
    exit 1
fi

log_success "数据库名称修复完成！"
