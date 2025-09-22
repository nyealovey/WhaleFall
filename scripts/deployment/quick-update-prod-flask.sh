#!/bin/bash

# 鲸落项目Flask快速更新脚本
# 功能：热更新Flask应用，适用于生产环境
# 特点：拷贝代码到运行中容器、最小化停机时间、自动验证、保留数据库
# 注意：仅更新Flask应用代码，不重建容器，保留所有数据

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
    echo "║                    鲸落项目热更新                           ║"
    echo "║                    TaifishV4 Hot Update                     ║"
    echo "║                   (代码热更新模式)                          ║"
    echo "║                (拷贝代码到运行中容器)                        ║"
    echo "║                (保留数据库和Redis)                          ║"
    echo "║                (最小化停机时间)                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统要求
check_requirements() {
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
    
    # 检查生产环境配置
    if [ ! -f "docker-compose.prod.yml" ]; then
        log_error "未找到docker-compose.prod.yml文件"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_error "未找到.env文件，请先配置环境变量"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 检查当前服务状态
check_current_status() {
    log_step "检查当前服务状态..."
    
    # 检查Flask容器状态
    local flask_status
    flask_status=$(docker compose -f docker-compose.prod.yml ps whalefall --format "table {{.Status}}" | tail -n +2)
    
    if echo "$flask_status" | grep -q "Up"; then
        log_success "Flask容器正在运行: $flask_status"
        export FLASK_CONTAINER_RUNNING=true
    else
        log_error "Flask容器未运行: $flask_status"
        log_error "请先运行完整部署脚本启动Flask容器"
        exit 1
    fi
    
    # 检查数据库和Redis状态
    local postgres_status
    postgres_status=$(docker compose -f docker-compose.prod.yml ps postgres --format "table {{.Status}}" | tail -n +2)
    
    if echo "$postgres_status" | grep -q "Up"; then
        log_success "PostgreSQL正在运行: $postgres_status"
    else
        log_error "PostgreSQL未运行: $postgres_status"
        log_error "请先运行完整部署脚本启动依赖服务"
        exit 1
    fi
    
    local redis_status
    redis_status=$(docker compose -f docker-compose.prod.yml ps redis --format "table {{.Status}}" | tail -n +2)
    
    if echo "$redis_status" | grep -q "Up"; then
        log_success "Redis正在运行: $redis_status"
    else
        log_error "Redis未运行: $redis_status"
        log_error "请先运行完整部署脚本启动依赖服务"
        exit 1
    fi
    
    log_success "当前服务状态检查通过"
}

# 拉取最新代码
pull_latest_code() {
    log_step "拉取最新代码..."
    
    # 检查Git状态
    if ! git status &> /dev/null; then
        log_error "当前目录不是Git仓库"
        exit 1
    fi
    
    # 暂存当前更改
    if ! git diff --quiet; then
        log_info "暂存当前更改..."
        git stash push -m "Auto-stash before quick update $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    if git pull origin main; then
        log_success "代码更新成功"
    else
        log_error "代码更新失败"
        exit 1
    fi
}

# 拷贝代码到容器
copy_code_to_container() {
    log_step "拷贝最新代码到Flask容器..."
    
    # 获取Flask容器ID
    local flask_container_id
    flask_container_id=$(docker compose -f docker-compose.prod.yml ps -q whalefall)
    
    if [ -z "$flask_container_id" ]; then
        log_error "未找到Flask容器"
        exit 1
    fi
    
    log_info "Flask容器ID: $flask_container_id"
    
    # 创建临时目录用于拷贝
    local temp_dir
    temp_dir="/tmp/whalefall_update_$(date +%s)"
    mkdir -p "$temp_dir"
    
    # 拷贝应用代码到临时目录
    log_info "准备应用代码..."
    
    # 拷贝目录（检查是否存在）
    [ -d "app" ] && cp -r app "$temp_dir/" || log_warning "app目录不存在，跳过"
    [ -d "migrations" ] && cp -r migrations "$temp_dir/" || log_warning "migrations目录不存在，跳过"
    [ -d "sql" ] && cp -r sql "$temp_dir/" || log_warning "sql目录不存在，跳过"
    [ -d "docs" ] && cp -r docs "$temp_dir/" || log_warning "docs目录不存在，跳过"
    [ -d "tests" ] && cp -r tests "$temp_dir/" || log_warning "tests目录不存在，跳过"
    [ -d "scripts" ] && cp -r scripts "$temp_dir/" || log_warning "scripts目录不存在，跳过"
    
    # 拷贝根目录文件（静默处理不存在的文件）
    cp *.py "$temp_dir/" 2>/dev/null || true
    cp *.md "$temp_dir/" 2>/dev/null || true
    cp *.txt "$temp_dir/" 2>/dev/null || true
    cp *.toml "$temp_dir/" 2>/dev/null || true
    cp *.yml "$temp_dir/" 2>/dev/null || true
    cp *.yaml "$temp_dir/" 2>/dev/null || true
    cp *.sh "$temp_dir/" 2>/dev/null || true
    cp *.ini "$temp_dir/" 2>/dev/null || true
    cp *.lock "$temp_dir/" 2>/dev/null || true
    
    # 检查是否有文件被拷贝
    local file_count
    file_count=$(find "$temp_dir" -type f | wc -l)
    
    if [ "$file_count" -eq 0 ]; then
        log_error "没有找到任何文件需要拷贝"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    log_info "找到 $file_count 个文件，开始拷贝到容器..."
    
    # 拷贝代码到容器
    if docker cp "$temp_dir/." "$flask_container_id:/app/"; then
        log_success "代码拷贝成功"
    else
        log_error "代码拷贝失败"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # 清理临时目录
    rm -rf "$temp_dir"
    
    # 设置正确的权限
    log_info "设置文件权限..."
    
    # 检查容器内的用户
    local container_user
    container_user=$(docker exec "$flask_container_id" whoami 2>/dev/null || echo "root")
    log_info "容器内当前用户: $container_user"
    
    # 尝试设置文件所有者（如果用户存在）
    if docker exec "$flask_container_id" id app >/dev/null 2>&1; then
        if docker exec "$flask_container_id" chown -R app:app /app; then
            log_success "文件所有者设置为app:app成功"
        else
            log_warning "文件所有者设置失败，但继续执行"
        fi
    else
        log_info "容器内没有app用户，跳过所有者设置"
    fi
    
    # 设置文件权限
    if docker exec "$flask_container_id" chmod -R 755 /app; then
        log_success "文件权限设置成功"
    else
        log_warning "文件权限设置失败，但继续执行"
    fi
    
    log_success "代码拷贝完成"
}

# 重启Flask服务
restart_flask_service() {
    log_step "重启Flask服务..."
    
    # 获取Flask容器ID
    local flask_container_id
    flask_container_id=$(docker compose -f docker-compose.prod.yml ps -q whalefall)
    
    if [ -z "$flask_container_id" ]; then
        log_error "未找到Flask容器"
        exit 1
    fi
    
    # 重启Flask容器
    log_info "重启Flask容器..."
    docker compose -f docker-compose.prod.yml restart whalefall
    
    # 等待容器重启
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.prod.yml ps whalefall | grep -q "Up"; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Flask容器重启超时"
        docker compose -f docker-compose.prod.yml logs whalefall
        exit 1
    fi
    
    log_success "Flask服务已重启"
}

# 等待服务就绪
wait_for_service_ready() {
    log_step "等待服务就绪..."
    
    # 等待Flask应用完全启动
    log_info "等待Flask应用完全启动..."
    local count=0
    while [ $count -lt 60 ]; do
        if curl -f http://localhost:5001/health > /dev/null 2>&1; then
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

# 验证更新
verify_update() {
    log_step "验证更新..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker compose -f docker-compose.prod.yml ps whalefall
    
    # 健康检查
    log_info "执行健康检查..."
    local health_response
    health_response=$(curl -s http://localhost:5001/health)
    
    if echo "$health_response" | grep -q "healthy"; then
        log_success "健康检查通过"
        log_info "健康检查响应: $health_response"
    else
        log_warning "健康检查响应异常，尝试通过Nginx检查..."
        # 通过Nginx检查
        local nginx_health_response
        nginx_health_response=$(curl -s http://localhost/health)
        
        if echo "$nginx_health_response" | grep -q "healthy"; then
            log_success "通过Nginx健康检查通过"
            log_info "Nginx健康检查响应: $nginx_health_response"
        else
            log_error "健康检查失败"
            log_error "直接访问响应: $health_response"
            log_error "Nginx访问响应: $nginx_health_response"
            return 1
        fi
    fi
    
    # 测试数据库和Redis连接（通过健康检查已验证）
    log_info "数据库和Redis连接已通过健康检查验证"
    
    log_success "更新验证通过"
    return 0
}


# 清理资源
cleanup_resources() {
    log_step "清理资源..."
    
    # 清理悬空镜像
    docker image prune -f
    
    # 清理未使用的容器
    docker container prune -f
    
    log_success "资源清理完成"
}

# 显示更新结果
show_update_result() {
    echo ""
    echo -e "${GREEN}🎉 热更新完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 更新信息：${NC}"
    echo "  - 更新版本: $(git rev-parse --short HEAD)"
    echo "  - 更新时间: $(date)"
    echo "  - 更新模式: 代码热更新"
    echo "  - 停机时间: 约30-60秒"
    echo "  - 数据保留: 完全保留"
    echo ""
    echo -e "${BLUE}🌐 访问地址：${NC}"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health"
    echo "  - 直接访问: http://localhost:5001"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.prod.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.prod.yml logs -f whalefall"
    echo "  - 重启服务: docker compose -f docker-compose.prod.yml restart whalefall"
    echo "  - 进入容器: docker compose -f docker-compose.prod.yml exec whalefall bash"
    echo ""
    echo -e "${BLUE}📊 监控信息：${NC}"
    echo "  - 容器资源: docker stats whalefall_app_prod"
    echo "  - 应用日志: docker compose -f docker-compose.prod.yml logs whalefall"
    echo "  - 健康状态: curl http://localhost:5001/health"
    echo ""
    echo -e "${YELLOW}⚠️  注意事项：${NC}"
    echo "  - 本次更新为代码热更新模式，数据完全保留"
    echo "  - 仅更新Flask应用代码，不重建容器"
    echo "  - 数据库和Redis服务保持不变"
    echo "  - 如有问题，请手动检查服务状态和日志"
    echo "  - 建议定期备份重要数据"
    echo "  - 监控应用运行状态"
}

# 主函数
main() {
    show_banner
    
    log_info "开始热更新Flask应用（代码拷贝模式）..."
    
    # 执行更新流程
    check_requirements
    check_current_status
    pull_latest_code
    copy_code_to_container
    restart_flask_service
    wait_for_service_ready
    
    # 验证更新
    if verify_update; then
        cleanup_resources
        show_update_result
        log_success "热更新完成！"
    else
        log_error "更新验证失败，请手动检查服务状态"
        log_info "容器状态："
        docker compose -f docker-compose.prod.yml ps
        log_info "Flask应用日志："
        docker compose -f docker-compose.prod.yml logs whalefall --tail 50
        exit 1
    fi
}

# 执行主函数
main "$@"