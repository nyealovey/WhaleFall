#!/bin/bash

# 鲸落项目生产环境部署脚本 v1.0.1
# 功能：一键部署生产环境，包含环境检查、配置验证、服务启动等

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}🚀 [STEP]${NC} $1"
}

# 显示横幅
show_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    鲸落项目生产环境部署                      ║"
    echo "║                       版本: 1.0.1                          ║"
    echo "║                    TaifishV4 Production                    ║"
    echo "║                   (完全重建模式)                            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统要求
check_system_requirements() {
    log_step "检查系统要求..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 检查环境变量
check_environment() {
    log_step "检查环境变量配置..."
    
    if [ ! -f ".env" ]; then
        log_warning "未找到.env文件，正在创建..."
        if [ -f "env.production" ]; then
            cp env.production .env
            log_success "已从env.production创建.env文件"
        else
            log_error "未找到env.production文件，请先配置环境变量"
            exit 1
        fi
    fi
    
    # 加载环境变量
    source .env
    
    # 检查关键环境变量
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY" "POSTGRES_DB" "POSTGRES_USER")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "以下必需的环境变量未设置："
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        log_error "请在.env文件中设置这些变量"
        exit 1
    fi
    
    # 验证数据库配置
    log_info "验证数据库配置..."
    log_info "数据库名称: ${POSTGRES_DB}"
    log_info "数据库用户: ${POSTGRES_USER}"
    log_info "数据库密码: ${POSTGRES_PASSWORD:0:8}***"
    
    # 检查DATABASE_URL配置
    if [ -n "$DATABASE_URL" ]; then
        log_info "DATABASE_URL: $DATABASE_URL"
        # 验证DATABASE_URL格式
        if echo "$DATABASE_URL" | grep -q "postgresql"; then
            log_success "DATABASE_URL格式正确"
        else
            log_warning "DATABASE_URL格式可能不正确，建议使用postgresql+psycopg://"
        fi
    else
        log_warning "DATABASE_URL未设置，将使用默认配置"
    fi
    
    log_success "环境变量检查通过"
}

# 清理旧环境
cleanup_old_environment() {
    log_step "清理旧环境..."
    
    # 停止现有容器
    if docker compose -f docker-compose.prod.yml ps -q | grep -q .; then
        log_info "停止现有容器..."
        docker compose -f docker-compose.prod.yml down
    fi
    
    # 删除持久化卷
    log_info "删除持久化卷..."
    if docker volume ls -q | grep -q whalefall; then
        log_warning "⚠️  即将删除所有whalefall持久化卷！"
        log_warning "⚠️  这将删除所有数据库数据和Redis缓存！"
        echo ""
        read -p "确认删除所有持久化数据？输入 'DELETE ALL DATA' 确认: " confirm
        if [ "$confirm" = "DELETE ALL DATA" ]; then
            log_info "删除whalefall相关卷..."
            docker volume ls -q | grep whalefall | xargs -r docker volume rm
            log_success "持久化卷删除完成"
        else
            log_error "用户取消操作，退出部署"
            exit 1
        fi
    else
        log_info "未找到whalefall相关卷"
    fi
    
    # 清理未使用的镜像
    log_info "清理未使用的Docker镜像..."
    docker image prune -f
    
    # 清理未使用的网络
    log_info "清理未使用的Docker网络..."
    docker network prune -f
    
    log_success "旧环境清理完成"
}

# 构建生产镜像
build_production_image() {
    log_step "构建生产环境镜像..."
    
    # 检查代理配置
    if [ -n "$HTTP_PROXY" ]; then
        log_info "使用代理构建镜像: $HTTP_PROXY"
        docker build \
            --build-arg HTTP_PROXY="$HTTP_PROXY" \
            --build-arg HTTPS_PROXY="$HTTPS_PROXY" \
            --build-arg NO_PROXY="$NO_PROXY" \
            -t whalefall:prod \
            -f Dockerfile.prod \
            --target production .
    else
        log_info "使用直连模式构建镜像..."
        docker build \
            -t whalefall:prod \
            -f Dockerfile.prod \
            --target production .
    fi
    
    log_success "生产环境镜像构建完成"
}

# 启动生产环境
start_production_environment() {
    log_step "启动生产环境服务..."
    
    # 启动所有服务
    docker compose -f docker-compose.prod.yml up -d
    
    log_success "生产环境服务启动完成"
}

# 验证数据库连接
verify_database_connection() {
    log_step "验证数据库连接..."
    
    # 等待PostgreSQL完全启动
    log_info "等待PostgreSQL完全启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.prod.yml exec postgres pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "PostgreSQL启动超时"
        exit 1
    fi
    log_success "PostgreSQL已就绪"
    
    # 验证数据库连接和认证
    log_info "验证数据库连接和认证..."
    if docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "数据库连接和认证成功"
    else
        log_error "数据库连接或认证失败"
        log_error "请检查以下配置："
        log_error "  - 数据库名称: ${POSTGRES_DB}"
        log_error "  - 数据库用户: ${POSTGRES_USER}"
        log_error "  - 数据库密码: ${POSTGRES_PASSWORD:0:8}***"
        exit 1
    fi
    
    # 验证数据库权限
    log_info "验证数据库权限..."
    local table_count
    table_count=$(docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$table_count" -ge 0 ]; then
        log_success "数据库权限验证成功，当前表数量: $table_count"
    else
        log_error "数据库权限验证失败"
        exit 1
    fi
}

# 等待服务就绪
wait_for_services() {
    log_step "等待服务就绪..."
    
    # 验证数据库连接
    verify_database_connection
    
    # 等待Redis
    log_info "等待Redis启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.prod.yml exec redis redis-cli ping > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    log_success "Redis已就绪"
    
    # 等待Flask应用
    log_info "等待Flask应用启动..."
    count=0
    while [ $count -lt 60 ]; do
        if curl -f http://localhost/health > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 60 ]; then
        log_error "Flask应用启动超时"
        docker compose -f docker-compose.prod.yml logs whalefall
        exit 1
    fi
    log_success "Flask应用已就绪"
}

# 初始化数据库
initialize_database() {
    log_step "初始化PostgreSQL数据库..."
    
    # 检查数据库是否已初始化
    local table_count
    table_count=$(docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$table_count" -gt 0 ]; then
        log_warning "数据库已包含 $table_count 个表，跳过初始化"
        return 0
    fi
    
    log_info "开始初始化数据库结构..."
    log_info "使用数据库: ${POSTGRES_DB}"
    log_info "使用用户: ${POSTGRES_USER}"
    
    # 执行PostgreSQL初始化脚本
    if [ -f "sql/init_postgresql.sql" ]; then
        log_info "执行PostgreSQL初始化脚本..."
        docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/init_postgresql.sql
        
        if [ $? -eq 0 ]; then
            log_success "PostgreSQL初始化脚本执行成功"
        else
            log_error "PostgreSQL初始化脚本执行失败"
            exit 1
        fi
    else
        log_warning "未找到sql/init_postgresql.sql文件，跳过数据库初始化"
    fi
    
    # 执行权限配置脚本
    if [ -f "sql/permission_configs.sql" ]; then
        log_info "导入权限配置数据..."
        docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/permission_configs.sql
        
        if [ $? -eq 0 ]; then
            log_success "权限配置数据导入成功"
        else
            log_warning "权限配置数据导入失败，但不影响系统运行"
        fi
    else
        log_warning "未找到sql/permission_configs.sql文件，跳过权限配置导入"
    fi
    
    # 执行调度器任务初始化脚本
    if [ -f "sql/init_scheduler_tasks.sql" ]; then
        log_info "初始化调度器任务..."
        docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < sql/init_scheduler_tasks.sql
        
        if [ $? -eq 0 ]; then
            log_success "调度器任务初始化成功"
        else
            log_warning "调度器任务初始化失败，但不影响系统运行"
        fi
    else
        log_warning "未找到sql/init_scheduler_tasks.sql文件，跳过调度器任务初始化"
    fi
    
    # 验证数据库初始化结果
    log_info "验证数据库初始化结果..."
    local final_table_count
    final_table_count=$(docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$final_table_count" -gt 0 ]; then
        log_success "数据库初始化完成，共创建 $final_table_count 个表"
    else
        log_error "数据库初始化失败，未创建任何表"
        exit 1
    fi
}

# 验证Flask应用数据库连接
verify_flask_database_connection() {
    log_step "验证Flask应用数据库连接..."
    
    # 等待Flask应用完全启动
    log_info "等待Flask应用完全启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.prod.yml exec whalefall python -c "
import os
os.environ['DATABASE_URL'] = '${DATABASE_URL}'
from app import create_app
app = create_app()
with app.app_context():
    from app.models import db
    db.engine.execute('SELECT 1')
print('Database connection successful')
" > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Flask应用数据库连接验证超时"
        log_error "请检查以下配置："
        log_error "  - DATABASE_URL: ${DATABASE_URL}"
        log_error "  - 数据库服务是否正常运行"
        log_error "  - 网络连接是否正常"
        exit 1
    fi
    
    log_success "Flask应用数据库连接验证成功"
}

# 验证部署
verify_deployment() {
    log_step "验证部署状态..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker compose -f docker-compose.prod.yml ps
    
    # 验证Flask应用数据库连接
    verify_flask_database_connection
    
    # 健康检查
    log_info "执行健康检查..."
    local health_response
    health_response=$(curl -s http://localhost/health)
    
    if echo "$health_response" | grep -q "healthy"; then
        log_success "健康检查通过"
    else
        log_error "健康检查失败"
        echo "响应: $health_response"
        exit 1
    fi
    
    # 检查端口
    log_info "检查端口监听..."
    if netstat -tlnp 2>/dev/null | grep -q ":80 "; then
        log_success "端口80监听正常"
    else
        log_warning "端口80未监听，请检查Nginx配置"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_step "部署信息"
    
    echo ""
    echo -e "${GREEN}🎉 生产环境部署完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 服务信息：${NC}"
    echo "  - 应用版本: 1.0.1"
    echo "  - 部署时间: $(date)"
    echo "  - 部署用户: $(whoami)"
    echo "  - 部署模式: 完全重建 (所有数据已重置)"
    echo "  - 数据库: PostgreSQL (已重新初始化)"
    echo "  - 缓存: Redis (已清空)"
    echo ""
    echo -e "${BLUE}🌐 访问地址：${NC}"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health"
    echo "  - 静态文件: http://localhost/static/"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.prod.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.prod.yml logs -f"
    echo "  - 停止服务: docker compose -f docker-compose.prod.yml down"
    echo "  - 重启服务: docker compose -f docker-compose.prod.yml restart"
    echo "  - 进入容器: docker compose -f docker-compose.prod.yml exec whalefall bash"
    echo ""
    echo -e "${BLUE}📊 监控信息：${NC}"
    echo "  - 容器资源: docker stats"
    echo "  - 系统资源: htop"
    echo "  - 日志文件: /var/log/nginx/whalefall_*.log"
    echo ""
    echo -e "${YELLOW}⚠️  注意事项：${NC}"
    echo "  - 本次部署为完全重建模式，所有历史数据已删除"
    echo "  - 请重新配置管理员账户和系统设置"
    echo "  - 请定期备份数据库数据"
    echo "  - 监控系统资源使用情况"
    echo "  - 定期更新安全补丁"
    echo "  - 查看应用日志排查问题"
}

# 主函数
main() {
    show_banner
    
    log_info "开始部署鲸落项目生产环境 v1.0.1..."
    
    check_system_requirements
    check_environment
    cleanup_old_environment
    build_production_image
    start_production_environment
    wait_for_services
    initialize_database
    verify_deployment
    show_deployment_info
    
    log_success "生产环境部署完成！"
}

# 执行主函数
main "$@"
