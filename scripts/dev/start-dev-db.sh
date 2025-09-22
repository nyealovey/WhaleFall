#!/bin/bash

# 开发环境数据库服务启动脚本
# 功能：启动PostgreSQL和Redis容器，Flask应用手动启动

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

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    开发环境数据库服务                        ║"
    echo "║                    PostgreSQL + Redis                       ║"
    echo "║                   Flask应用需手动启动                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量配置..."
    
    if [ ! -f ".env" ]; then
        log_warning "未找到.env文件，正在创建..."
        if [ -f "env.development" ]; then
            cp env.development .env
            log_success "已从env.development创建.env文件"
        else
            log_error "未找到env.development文件，请先配置环境变量"
            exit 1
        fi
    fi
    
    # 加载环境变量
    source .env
    
    log_success "环境变量检查通过"
}

# 启动数据库服务
start_database_services() {
    log_info "启动数据库服务..."
    
    # 启动PostgreSQL和Redis
    docker compose -f docker-compose.dev.yml up -d postgres redis
    
    log_success "数据库服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待数据库服务就绪..."
    
    # 等待PostgreSQL
    log_info "等待PostgreSQL启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.dev.yml exec postgres pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} > /dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "PostgreSQL启动超时"
        exit 1
    fi
    log_success "PostgreSQL已就绪"
    
    # 等待Redis
    log_info "等待Redis启动..."
    count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.dev.yml exec redis redis-cli ping > /dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    log_success "Redis已就绪"
}

# 初始化数据库
initialize_database() {
    log_info "初始化数据库..."
    
    # 检查数据库是否已初始化
    local table_count=$(docker compose -f docker-compose.dev.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$table_count" -gt 0 ]; then
        log_warning "数据库已包含 $table_count 个表，跳过初始化"
        return 0
    fi
    
    log_info "执行数据库初始化脚本..."
    
    # 执行主初始化脚本
    if [ -f "sql/init_postgresql.sql" ]; then
        log_info "执行 init_postgresql.sql..."
        docker compose -f docker-compose.dev.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/init_postgresql.sql
        if [ $? -eq 0 ]; then
            log_success "init_postgresql.sql 执行成功"
        else
            log_error "init_postgresql.sql 执行失败"
            return 1
        fi
    else
        log_warning "未找到 sql/init_postgresql.sql 文件"
    fi
    
    # 执行权限配置脚本
    if [ -f "sql/permission_configs.sql" ]; then
        log_info "执行 permission_configs.sql..."
        docker compose -f docker-compose.dev.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/permission_configs.sql
        if [ $? -eq 0 ]; then
            log_success "permission_configs.sql 执行成功"
        else
            log_warning "permission_configs.sql 执行失败，但继续执行"
        fi
    else
        log_warning "未找到 sql/permission_configs.sql 文件"
    fi
    
    # 执行调度器任务初始化脚本
    if [ -f "sql/init_scheduler_tasks.sql" ]; then
        log_info "执行 init_scheduler_tasks.sql..."
        docker compose -f docker-compose.dev.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/init_scheduler_tasks.sql
        if [ $? -eq 0 ]; then
            log_success "init_scheduler_tasks.sql 执行成功"
        else
            log_warning "init_scheduler_tasks.sql 执行失败，但继续执行"
        fi
    else
        log_warning "未找到 sql/init_scheduler_tasks.sql 文件"
    fi
    
    # 验证初始化结果
    local final_table_count=$(docker compose -f docker-compose.dev.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$final_table_count" -gt 0 ]; then
        log_success "数据库初始化完成，共创建 $final_table_count 个表"
    else
        log_error "数据库初始化失败，未创建任何表"
        return 1
    fi
}

# 显示服务信息
show_service_info() {
    log_info "服务信息"
    
    echo ""
    echo -e "${GREEN}🎉 开发环境数据库服务启动完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 服务信息：${NC}"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - 数据库名: ${POSTGRES_DB}"
    echo "  - 数据库用户: ${POSTGRES_USER}"
    echo "  - 数据库状态: 已初始化"
    echo ""
    echo -e "${BLUE}🚀 启动Flask应用：${NC}"
    echo "  - 命令: python app.py"
    echo "  - 访问地址: http://localhost:5001"
    echo "  - 环境变量: 已从.env文件加载"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.dev.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.dev.yml logs -f"
    echo "  - 停止服务: docker compose -f docker-compose.dev.yml down"
    echo "  - 重启服务: docker compose -f docker-compose.dev.yml restart"
    echo ""
    echo -e "${YELLOW}⚠️  注意事项：${NC}"
    echo "  - Flask应用需要手动启动"
    echo "  - 确保已安装Python依赖：uv sync"
    echo "  - 数据库连接使用Docker网络中的服务名"
}

# 主函数
main() {
    show_banner
    
    check_environment
    start_database_services
    wait_for_services
    initialize_database
    show_service_info
    
    log_success "开发环境数据库服务启动完成！"
}

# 执行主函数
main "$@"
