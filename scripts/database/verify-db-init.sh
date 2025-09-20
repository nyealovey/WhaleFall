#!/bin/bash

# 数据库初始化验证脚本
# 用于验证PostgreSQL数据库是否正确初始化

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

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."
    
    if docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U whalefall_user -d whalefall_prod > /dev/null 2>&1; then
        log_success "数据库连接正常"
        return 0
    else
        log_error "数据库连接失败"
        return 1
    fi
}

# 检查表结构
check_table_structure() {
    log_info "检查数据库表结构..."
    
    local table_count
    table_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$table_count" -gt 0 ]; then
        log_success "数据库包含 $table_count 个表"
    else
        log_error "数据库未包含任何表"
        return 1
    fi
    
    # 检查关键表
    local key_tables=("users" "instances" "credentials" "account_classifications" "current_account_sync_data")
    
    for table in "${key_tables[@]}"; do
        local exists
        exists=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table';" 2>/dev/null | tr -d ' \n' || echo "0")
        
        if [ "$exists" = "1" ]; then
            log_success "表 $table 存在"
        else
            log_error "表 $table 不存在"
            return 1
        fi
    done
}

# 检查初始数据
check_initial_data() {
    log_info "检查初始数据..."
    
    # 检查用户数据
    local user_count
    user_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$user_count" -gt 0 ]; then
        log_success "用户数据: $user_count 条记录"
    else
        log_warning "用户数据为空"
    fi
    
    # 检查数据库类型配置
    local db_type_count
    db_type_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM database_type_configs;" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$db_type_count" -gt 0 ]; then
        log_success "数据库类型配置: $db_type_count 条记录"
    else
        log_warning "数据库类型配置为空"
    fi
    
    # 检查账户分类数据
    local classification_count
    classification_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM account_classifications;" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$classification_count" -gt 0 ]; then
        log_success "账户分类数据: $classification_count 条记录"
    else
        log_warning "账户分类数据为空"
    fi
    
    # 检查权限配置数据
    local permission_count
    permission_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM permission_configs;" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$permission_count" -gt 0 ]; then
        log_success "权限配置数据: $permission_count 条记录"
    else
        log_warning "权限配置数据为空"
    fi
}

# 检查索引
check_indexes() {
    log_info "检查数据库索引..."
    
    local index_count
    index_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$index_count" -gt 0 ]; then
        log_success "数据库索引: $index_count 个"
    else
        log_warning "数据库索引为空"
    fi
}

# 检查触发器
check_triggers() {
    log_info "检查数据库触发器..."
    
    local trigger_count
    trigger_count=$(docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -t -c "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$trigger_count" -gt 0 ]; then
        log_success "数据库触发器: $trigger_count 个"
    else
        log_warning "数据库触发器为空"
    fi
}

# 显示数据库统计信息
show_database_stats() {
    log_info "数据库统计信息:"
    
    echo ""
    echo "表统计:"
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -c "
    SELECT 
        schemaname,
        tablename,
        n_tup_ins as inserts,
        n_tup_upd as updates,
        n_tup_del as deletes,
        n_live_tup as live_tuples,
        n_dead_tup as dead_tuples
    FROM pg_stat_user_tables 
    ORDER BY tablename;
    "
    
    echo ""
    echo "索引统计:"
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whalefall_user -d whalefall_prod -c "
    SELECT 
        schemaname,
        tablename,
        indexname,
        idx_tup_read,
        idx_tup_fetch
    FROM pg_stat_user_indexes 
    ORDER BY tablename, indexname;
    "
}

# 主函数
main() {
    echo -e "${BLUE}🔍 数据库初始化验证脚本${NC}"
    echo "=================================="
    
    check_database_connection || exit 1
    check_table_structure || exit 1
    check_initial_data
    check_indexes
    check_triggers
    show_database_stats
    
    echo ""
    log_success "数据库初始化验证完成！"
}

# 执行主函数
main "$@"
