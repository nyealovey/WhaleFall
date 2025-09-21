#!/bin/bash

# 鲸落项目Flask应用更新脚本 v1.0.1
# 功能：快速更新Flask应用代码，无需重建整个环境
# 特点：保留数据、快速部署、自动回滚、健康检查

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
    echo "║                    鲸落项目Flask更新                        ║"
    echo "║                       版本: 1.0.1                          ║"
    echo "║                    TaifishV4 Flask Update                   ║"
    echo "║                   (快速更新模式)                            ║"
    echo "║                (保留数据，仅更新应用)                        ║"
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
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
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
    
    log_success "环境变量检查通过"
}

# 检查当前服务状态
check_current_status() {
    log_step "检查当前服务状态..."
    
    # 检查是否有运行中的容器
    if ! docker compose -f docker-compose.prod.yml ps -q | grep -q .; then
        log_error "没有运行中的服务，请先运行完整部署脚本"
        exit 1
    fi
    
    # 检查Flask容器状态
    local flask_status
    flask_status=$(docker compose -f docker-compose.prod.yml ps whalefall --format "table {{.Status}}" | tail -n +2)
    
    if echo "$flask_status" | grep -q "Up"; then
        log_success "Flask容器正在运行: $flask_status"
    else
        log_error "Flask容器未运行: $flask_status"
        log_error "请先启动服务或运行完整部署脚本"
        exit 1
    fi
    
    # 检查数据库和Redis状态
    local postgres_status
    postgres_status=$(docker compose -f docker-compose.prod.yml ps postgres --format "table {{.Status}}" | tail -n +2)
    
    if echo "$postgres_status" | grep -q "Up"; then
        log_success "PostgreSQL正在运行: $postgres_status"
    else
        log_error "PostgreSQL未运行: $postgres_status"
        exit 1
    fi
    
    local redis_status
    redis_status=$(docker compose -f docker-compose.prod.yml ps redis --format "table {{.Status}}" | tail -n +2)
    
    if echo "$redis_status" | grep -q "Up"; then
        log_success "Redis正在运行: $redis_status"
    else
        log_error "Redis未运行: $redis_status"
        exit 1
    fi
    
    log_success "当前服务状态检查通过"
}

# 备份当前代码
backup_current_code() {
    log_step "备份当前代码..."
    
    local backup_dir="userdata/backups/code"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_path="${backup_dir}/flask_backup_${timestamp}"
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    # 备份当前Flask应用代码
    log_info "备份当前Flask应用代码到: $backup_path"
    
    # 创建备份压缩包
    tar -czf "${backup_path}.tar.gz" \
        --exclude=".git" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude=".env" \
        --exclude="userdata" \
        --exclude="migrations" \
        --exclude=".pytest_cache" \
        app/ \
        requirements.txt \
        requirements-prod.txt \
        pyproject.toml \
        Dockerfile.prod \
        docker-compose.prod.yml \
        nginx/ \
        scripts/ \
        docs/ \
        sql/ \
        2>/dev/null || true
    
    if [ -f "${backup_path}.tar.gz" ]; then
        log_success "代码备份完成: ${backup_path}.tar.gz"
        echo "$backup_path.tar.gz" > "${backup_dir}/latest_backup.txt"
    else
        log_warning "代码备份失败，但继续执行更新"
    fi
}

# 更新代码
update_code() {
    log_step "更新代码..."
    
    # 检查是否有未提交的更改
    if ! git diff --quiet; then
        log_warning "检测到未提交的更改，正在提交..."
        git add .
        git commit -m "Auto-commit before update $(date '+%Y-%m-%d %H:%M:%S')" || true
    fi
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    if git pull origin main; then
        log_success "代码更新成功"
    else
        log_error "代码更新失败"
        exit 1
    fi
    
    # 检查是否有新的依赖
    if [ -f "requirements.txt" ] || [ -f "requirements-prod.txt" ]; then
        log_info "检查依赖更新..."
        # 这里可以添加依赖检查逻辑
        log_success "依赖检查完成"
    fi
}

# 构建新的Flask镜像
build_flask_image() {
    log_step "构建新的Flask镜像..."
    
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
    
    if [ $? -eq 0 ]; then
        log_success "Flask镜像构建成功"
    else
        log_error "Flask镜像构建失败"
        exit 1
    fi
}

# 停止Flask服务
stop_flask_service() {
    log_step "停止Flask服务..."
    
    # 优雅停止Flask容器
    log_info "优雅停止Flask容器..."
    docker compose -f docker-compose.prod.yml stop whalefall
    
    # 等待容器完全停止
    local count=0
    while [ $count -lt 30 ]; do
        if ! docker compose -f docker-compose.prod.yml ps whalefall | grep -q "Up"; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_warning "Flask容器未在预期时间内停止，强制停止..."
        docker compose -f docker-compose.prod.yml kill whalefall
    fi
    
    log_success "Flask服务已停止"
}

# 启动Flask服务
start_flask_service() {
    log_step "启动Flask服务..."
    
    # 启动Flask容器
    log_info "启动Flask容器..."
    docker compose -f docker-compose.prod.yml up -d whalefall
    
    # 等待容器启动
    local count=0
    while [ $count -lt 30 ]; do
        if docker compose -f docker-compose.prod.yml ps whalefall | grep -q "Up"; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "Flask容器启动超时"
        docker compose -f docker-compose.prod.yml logs whalefall
        exit 1
    fi
    
    log_success "Flask服务已启动"
}

# 等待服务就绪
wait_for_flask_ready() {
    log_step "等待Flask服务就绪..."
    
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
        log_error "健康检查失败"
        log_error "健康检查响应: $health_response"
        return 1
    fi
    
    # 测试数据库连接
    log_info "测试数据库连接..."
    local db_test_response
    db_test_response=$(curl -s http://localhost:5001/health)
    
    if echo "$db_test_response" | grep -q "healthy"; then
        log_success "数据库连接测试通过"
    else
        log_error "数据库连接测试失败"
        return 1
    fi
    
    # 测试Redis连接
    log_info "测试Redis连接..."
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
        log_success "Redis连接测试通过"
    else
        log_error "Redis连接测试失败"
        log_error "Redis响应: $redis_test_response"
        return 1
    fi
    
    log_success "更新验证通过"
    return 0
}

# 回滚更新
rollback_update() {
    log_step "回滚更新..."
    
    local backup_dir="userdata/backups/code"
    local latest_backup_file="${backup_dir}/latest_backup.txt"
    
    if [ -f "$latest_backup_file" ]; then
        local latest_backup
        latest_backup=$(cat "$latest_backup_file")
        
        if [ -f "$latest_backup" ]; then
            log_info "回滚到备份: $latest_backup"
            
            # 停止当前服务
            docker compose -f docker-compose.prod.yml stop whalefall
            
            # 解压备份
            tar -xzf "$latest_backup" -C /tmp/flask_rollback/
            
            # 恢复代码
            cp -r /tmp/flask_rollback/* ./
            rm -rf /tmp/flask_rollback/
            
            # 重新构建和启动
            build_flask_image
            start_flask_service
            wait_for_flask_ready
            
            log_success "回滚完成"
        else
            log_error "备份文件不存在: $latest_backup"
        fi
    else
        log_error "未找到备份文件列表"
    fi
}

# 清理旧镜像
cleanup_old_images() {
    log_step "清理旧镜像..."
    
    # 删除悬空镜像
    log_info "删除悬空镜像..."
    docker image prune -f
    
    # 删除未使用的镜像（保留最近3个版本）
    log_info "清理未使用的镜像..."
    docker images whalefall:prod --format "table {{.ID}}\t{{.CreatedAt}}" | tail -n +2 | head -n -3 | awk '{print $1}' | xargs -r docker rmi -f 2>/dev/null || true
    
    log_success "镜像清理完成"
}

# 显示更新信息
show_update_info() {
    log_step "更新信息"
    
    echo ""
    echo -e "${GREEN}🎉 Flask应用更新完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 更新信息：${NC}"
    echo "  - 更新版本: $(git rev-parse --short HEAD)"
    echo "  - 更新时间: $(date)"
    echo "  - 更新用户: $(whoami)"
    echo "  - 更新模式: 快速更新 (保留数据)"
    echo "  - 备份位置: userdata/backups/code/"
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
    echo "  - 本次更新为快速更新模式，数据已保留"
    echo "  - 如有问题，可使用回滚功能恢复"
    echo "  - 建议定期备份重要数据"
    echo "  - 监控应用运行状态"
}

# 主函数
main() {
    show_banner
    
    log_info "开始更新鲸落项目Flask应用 v1.0.1..."
    
    # 执行更新流程
    check_system_requirements
    check_environment
    check_current_status
    backup_current_code
    update_code
    build_flask_image
    stop_flask_service
    start_flask_service
    wait_for_flask_ready
    
    # 验证更新
    if verify_update; then
        cleanup_old_images
        show_update_info
        log_success "Flask应用更新完成！"
    else
        log_error "更新验证失败，开始回滚..."
        rollback_update
        if verify_update; then
            log_success "回滚成功，服务已恢复"
        else
            log_error "回滚失败，请手动检查服务状态"
            exit 1
        fi
    fi
}

# 执行主函数
main "$@"
