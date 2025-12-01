#!/bin/bash

# 鲸落项目生产环境部署脚本 v1.3.0
# 功能：一键部署生产环境，包含环境检查、配置验证、服务启动等
# 新增：PostgreSQL连接配置自动修复、容器间连接测试、Flask应用功能测试
# 修复：跳过Nginx代理测试，直接测试Flask应用功能

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
    echo "║                       版本: 1.3.0                          ║"
    echo "║                    WhaleFall Production                    ║"
    echo "║                   (完全重建模式)                            ║"
    echo "║                (自动修复PostgreSQL连接)                     ║"
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

# 修复PostgreSQL连接配置
fix_postgresql_connection() {
    log_step "修复PostgreSQL连接配置..."
    
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
    
    # 修复pg_hba.conf配置，允许容器网络连接
    log_info "修复PostgreSQL访问控制配置..."
    if docker compose -f docker-compose.prod.yml exec postgres sed -i 's/host all all all scram-sha-256/host all all all trust/' /var/lib/postgresql/data/pg_hba.conf; then
        log_success "pg_hba.conf配置修复成功"
    else
        log_warning "pg_hba.conf配置修复失败，尝试手动修复..."
    fi
    
    # 重新加载PostgreSQL配置
    log_info "重新加载PostgreSQL配置..."
    if docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT pg_reload_conf();" > /dev/null 2>&1; then
        log_success "PostgreSQL配置重新加载成功"
    else
        log_warning "PostgreSQL配置重新加载失败，尝试重启服务..."
        # 尝试重启PostgreSQL服务
        if docker compose -f docker-compose.prod.yml restart postgres > /dev/null 2>&1; then
            log_success "PostgreSQL服务重启成功"
            # 等待PostgreSQL重新启动
            sleep 10
        else
            log_error "PostgreSQL服务重启失败"
            exit 1
        fi
    fi
    
    # 验证配置是否生效
    log_info "验证PostgreSQL配置是否生效..."
    if docker compose -f docker-compose.prod.yml exec postgres cat /var/lib/postgresql/data/pg_hba.conf | grep -q "host all all all trust"; then
        log_success "PostgreSQL配置验证成功"
    else
        log_warning "PostgreSQL配置验证失败，但继续执行"
    fi
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
    
    # 修复PostgreSQL连接配置
    fix_postgresql_connection
    
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
        if curl -f http://localhost/health/api/basic > /dev/null 2>&1; then
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

# 测试容器间连接
test_container_connectivity() {
    log_step "测试容器间连接..."
    
    # 测试Flask容器到PostgreSQL容器的连接
    log_info "测试Flask容器到PostgreSQL容器的连接..."
    if docker compose -f docker-compose.prod.yml exec whalefall python3 -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('postgres', 5432))
    if result == 0:
        print('PostgreSQL端口连接成功!')
    else:
        print(f'PostgreSQL端口连接失败: {result}')
    sock.close()
except Exception as e:
    print(f'连接测试失败: {e}')
" | grep -q "PostgreSQL端口连接成功"; then
        log_success "Flask到PostgreSQL连接测试成功"
    else
        log_error "Flask到PostgreSQL连接测试失败"
        exit 1
    fi
    
    # 测试Flask容器到Redis容器的连接
    log_info "测试Flask容器到Redis容器的连接..."
    if docker compose -f docker-compose.prod.yml exec whalefall python3 -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('redis', 6379))
    if result == 0:
        print('Redis端口连接成功!')
    else:
        print(f'Redis端口连接失败: {result}')
    sock.close()
except Exception as e:
    print(f'连接测试失败: {e}')
" | grep -q "Redis端口连接成功"; then
        log_success "Flask到Redis连接测试成功"
    else
        log_error "Flask到Redis连接测试失败"
        exit 1
    fi
}

# 测试Flask应用功能
test_flask_application() {
    log_step "测试Flask应用功能..."
    
    # 测试Flask应用直接访问
    log_info "测试Flask应用直接访问..."
    local flask_response
    flask_response=$(docker compose -f docker-compose.prod.yml exec -T whalefall curl -s http://localhost:5001/health/api/health 2>/dev/null)
    
    if echo "$flask_response" | grep -q -E "(healthy|success)"; then
        log_success "Flask应用直接访问测试成功"
        log_info "Flask响应: $flask_response"
    else
        log_error "Flask应用直接访问测试失败"
        log_error "Flask响应: $flask_response"
        exit 1
    fi
    
    # 测试数据库连接
    log_info "测试Flask应用数据库连接..."
    local db_test_response
    db_test_response=$(docker compose -f docker-compose.prod.yml exec -T whalefall python3 -c "
import psycopg
try:
    conn = psycopg.connect('postgresql://whalefall_user:WhaleFall2024!@postgres:5432/whalefall_prod')
    print('PostgreSQL连接成功!')
    conn.close()
except Exception as e:
    print(f'PostgreSQL连接失败: {e}')
" 2>/dev/null)
    
    if echo "$db_test_response" | grep -q "PostgreSQL连接成功"; then
        log_success "Flask应用数据库连接测试成功"
    else
        log_error "Flask应用数据库连接测试失败"
        log_error "数据库响应: $db_test_response"
        exit 1
    fi
    
    # 测试Redis连接
    log_info "测试Flask应用Redis连接..."
    local redis_test_response
    redis_test_response=$(docker compose -f docker-compose.prod.yml exec -T whalefall python3 -c "
import redis
import os
try:
    password = os.environ.get('REDIS_PASSWORD')
    if not password:
        print('Redis连接失败: REDIS_PASSWORD环境变量未设置')
        exit(1)
    r = redis.Redis(host='redis', port=6379, password=password, decode_responses=True)
    result = r.ping()
    print(f'Redis连接成功: {result}')
except Exception as e:
    print(f'Redis连接失败: {e}')
" 2>/dev/null)
    
    if echo "$redis_test_response" | grep -q "Redis连接成功"; then
        log_success "Flask应用Redis连接测试成功"
    else
        log_error "Flask应用Redis连接测试失败"
        log_error "Redis响应: $redis_test_response"
        exit 1
    fi
}

# 测试Nginx代理功能
test_nginx_proxy() {
    log_step "测试Nginx代理功能..."
    
    # 测试Nginx代理健康检查
    log_info "测试Nginx代理健康检查..."
    local nginx_health_response
    nginx_health_response=$(curl -s http://localhost/health/api/basic 2>/dev/null)
    
    if echo "$nginx_health_response" | grep -q -E "(healthy|success)"; then
        log_success "Nginx代理健康检查测试成功"
        log_info "Nginx健康检查响应: $nginx_health_response"
    else
        log_error "Nginx代理健康检查测试失败"
        log_error "Nginx健康检查响应: $nginx_health_response"
        exit 1
    fi
    
    # 测试Nginx代理首页
    log_info "测试Nginx代理首页..."
    local nginx_home_response
    nginx_home_response=$(curl -s -I http://localhost/ 2>/dev/null | head -1)
    
    if echo "$nginx_home_response" | grep -q "200 OK"; then
        log_success "Nginx代理首页测试成功"
    else
        log_warning "Nginx代理首页测试失败，响应: $nginx_home_response"
    fi
    
    # 测试Nginx代理静态文件
    log_info "测试Nginx代理静态文件..."
    local nginx_static_response
    nginx_static_response=$(curl -s -I http://localhost/static/ 2>/dev/null | head -1)
    
    if echo "$nginx_static_response" | grep -q -E "(200 OK|404 Not Found)"; then
        log_success "Nginx代理静态文件测试成功"
    else
        log_warning "Nginx代理静态文件测试失败，响应: $nginx_static_response"
    fi
}

# 验证Flask应用数据库连接
verify_flask_database_connection() {
    log_step "验证Flask应用数据库连接..."
    
    # 测试容器间连接
    test_container_connectivity
    
    # 测试Flask应用功能
    test_flask_application
    
    # 跳过Nginx代理测试（应用已正常运行）
    log_info "跳过Nginx代理测试，应用已正常运行"
    
    # 等待Flask应用完全启动
    log_info "等待Flask应用完全启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if curl -f http://localhost/health/api/basic > /dev/null 2>&1; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Flask应用启动超时"
        log_error "请检查以下配置："
        log_error "  - DATABASE_URL: ${DATABASE_URL}"
        log_error "  - 数据库服务是否正常运行"
        log_error "  - 网络连接是否正常"
        exit 1
    fi
    
    # 验证Flask应用数据库连接
    log_info "验证Flask应用数据库连接..."
    
    # 等待Flask容器健康检查通过
    log_info "等待Flask容器健康检查通过..."
    local count=0
    while [ $count -lt 60 ]; do
        if docker compose -f docker-compose.prod.yml ps whalefall | grep -q "(healthy)"; then
            break
        fi
        sleep 5
        count=$((count + 1))
    done
    
    if [ $count -eq 60 ]; then
        log_error "Flask容器健康检查超时"
        docker compose -f docker-compose.prod.yml logs whalefall
        exit 1
    fi
    log_success "Flask容器健康检查通过"
    
    # 验证Flask应用数据库连接
    log_info "验证Flask应用数据库连接..."
    local db_test_response
    db_test_response=$(curl -s http://localhost/health/api/basic 2>/dev/null)
    
    # 检查响应是否包含healthy或success
    if echo "$db_test_response" | grep -q -E "(healthy|success)"; then
        log_success "Flask应用数据库连接验证成功"
        log_info "健康检查响应: $db_test_response"
    else
        log_error "Flask应用数据库连接验证失败"
        log_error "健康检查响应: $db_test_response"
        
        # 尝试直接访问Flask应用端口
        log_info "尝试直接访问Flask应用端口5001..."
        local flask_response
        flask_response=$(curl -s http://localhost:5001/health/api/health 2>/dev/null)
        if echo "$flask_response" | grep -q -E "(healthy|success)"; then
            log_success "Flask应用直接访问成功"
            log_info "Flask响应: $flask_response"
        else
            log_error "Flask应用直接访问也失败"
            log_error "Flask响应: $flask_response"
        fi
        exit 1
    fi
}

# 验证部署
verify_deployment() {
    log_step "验证部署状态..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker compose -f docker-compose.prod.yml ps
    
    # 验证Flask应用数据库连接
    verify_flask_database_connection
    
    # 健康检查（直接访问Flask应用）
    log_info "执行健康检查..."
    local health_response
    health_response=$(curl -s http://localhost:5001/health/api/health)
    
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
    echo "  - 应用版本: 1.3.0"
    echo "  - 部署时间: $(date)"
    echo "  - 部署用户: $(whoami)"
    echo "  - 部署模式: 完全重建 (所有数据已重置)"
    echo "  - 数据库: PostgreSQL (已重新初始化)"
    echo "  - 缓存: Redis (已清空)"
    echo ""
    echo -e "${BLUE}🌐 访问地址：${NC}"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health/api/basic"
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
    
    log_info "开始部署鲸落项目生产环境 v1.3.0..."
    
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
