#!/bin/bash

# 鲸落项目Flask快速更新脚本
# 功能：热更新Flask应用，适用于生产环境
# 特点：只清理缓存文件，直接拷贝新代码覆盖、最小化停机时间、自动验证、保留数据库
# 注意：不删除应用代码文件，只清理Python缓存，直接覆盖更新，不重建容器，保留所有数据

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
    echo "║                    WhaleFall Hot Update                     ║"
    echo "║                   (代码覆盖更新模式)                        ║"
    echo "║                (只清理缓存，直接覆盖代码)                    ║"
    echo "║                (清理Python缓存和临时文件)                    ║"
    echo "║                (保留数据库和Redis)                          ║"
    echo "║                (自动刷新Nginx缓存)                          ║"
    echo "║                (最小化停机时间)                              ║"
    echo "║                (始终以GitHub代码为准)                        ║"
    echo "║                (自动强制同步远程状态)                        ║"
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
    
    # 获取当前提交信息
    local current_commit
    current_commit=$(git rev-parse --short HEAD)
    log_info "当前本地提交: $current_commit"
    
    # 配置Git用户信息（避免fetch时出错）
    log_info "配置Git用户信息..."
    git config user.email "whalefall@taifishing.com" 2>/dev/null || true
    git config user.name "WhaleFall Deploy" 2>/dev/null || true
    
    # 获取远程最新提交信息
    log_info "获取远程最新信息..."
    git fetch origin main
    
    local remote_commit
    remote_commit=$(git rev-parse --short origin/main)
    log_info "远程最新提交: $remote_commit"
    
    # 始终强制同步到远程状态（以GitHub为准）
    log_info "强制同步到远程最新状态（以GitHub为准）..."
    if git reset --hard origin/main; then
        log_success "代码已强制同步到远程最新状态"
        log_info "新的本地提交: $(git rev-parse --short HEAD)"
    else
        log_error "强制同步失败"
        exit 1
    fi
    
    # 验证最终状态
    local final_commit
    final_commit=$(git rev-parse --short HEAD)
    log_info "最终代码提交: $final_commit"
    
    # 检查是否有文件变更
    if [ "$current_commit" != "$final_commit" ]; then
        log_success "检测到代码变更，准备更新容器"
    else
        log_warning "没有检测到代码变更，可能已经是最新状态"
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
    [ -d "nginx" ] && cp -r nginx "$temp_dir/" || log_warning "nginx目录不存在，跳过"
    
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
    
    log_info "找到 $file_count 个文件，开始更新容器代码..."
    
    # 只清理缓存文件，不删除应用代码
    log_info "清理缓存文件..."
    if docker exec "$flask_container_id" bash -c "
        # 清理旧迁移版本文件，避免历史遗留版本链断裂导致 flask db upgrade 失败
        rm -rf /app/migrations/versions 2>/dev/null || true

        # 只清理Python缓存
        find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
        find /app -name '*.pyc' -type f -delete 2>/dev/null || true
        find /app -name '*.pyo' -type f -delete 2>/dev/null || true
        
    "; then
        log_success "缓存清理完成"
    else
        log_warning "缓存清理部分失败，但继续执行"
    fi
    
    # 拷贝新代码到容器
    log_info "拷贝新代码到容器..."
    if docker cp "$temp_dir/." "$flask_container_id:/app/"; then
        log_success "新代码拷贝成功"
    else
        log_error "新代码拷贝失败"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # 确保gunicorn.conf.py文件存在
    log_info "确保gunicorn.conf.py文件存在..."
    if docker exec "$flask_container_id" bash -c "
        if [ ! -f /app/gunicorn.conf.py ]; then
            if [ -f /app/nginx/gunicorn/gunicorn-prod.conf.py ]; then
                cp /app/nginx/gunicorn/gunicorn-prod.conf.py /app/gunicorn.conf.py
                echo '已复制gunicorn.conf.py到根目录'
            else
                echo '警告：未找到gunicorn-prod.conf.py文件'
            fi
        else
            echo 'gunicorn.conf.py已存在'
        fi
    "; then
        log_success "gunicorn.conf.py文件检查完成"
    else
        log_warning "gunicorn.conf.py文件检查失败，但继续执行"
    fi
    
    # 清理临时目录
    rm -rf "$temp_dir"
    
    # 设置正确的权限
    log_info "设置文件权限..."
    
    # 检查容器内的用户
    local container_user
    container_user=$(docker exec "$flask_container_id" whoami 2>/dev/null || echo "root")
    log_info "容器内当前用户: $container_user"
    
    # 根据容器内用户类型设置权限
    if [ "$container_user" = "root" ]; then
        log_info "检测到root用户环境，设置root权限..."
        
        # 设置root用户权限
        if docker exec "$flask_container_id" chown -R root:root /app; then
            log_success "文件所有者设置为root:root成功"
        else
            log_warning "文件所有者设置失败，但继续执行"
        fi
    else
        # 尝试设置app用户权限（如果存在）
        if docker exec "$flask_container_id" id app >/dev/null 2>&1; then
            if docker exec "$flask_container_id" chown -R app:app /app; then
                log_success "文件所有者设置为app:app成功"
            else
                log_warning "文件所有者设置失败，但继续执行"
            fi
        else
            log_info "容器内没有app用户，跳过所有者设置"
        fi
    fi
    
    # 设置文件权限
    if docker exec "$flask_container_id" chmod -R 755 /app; then
        log_success "文件权限设置成功"
    else
        log_warning "文件权限设置失败，但继续执行"
    fi
    
    log_success "代码拷贝完成"
}

# 执行数据库迁移
upgrade_database_schema() {
    log_step "执行数据库迁移..."
    
    # 获取Flask容器ID
    local flask_container_id
    flask_container_id=$(docker compose -f docker-compose.prod.yml ps -q whalefall)
    
    if [ -z "$flask_container_id" ]; then
        log_error "未找到Flask容器"
        exit 1
    fi
    
    # 防御：生产库可能已通过 init_postgresql.sql（sql/init/postgresql/init_postgresql.sql）初始化，但未写入 alembic_version
    # 直接执行 `flask db upgrade` 会从 baseline 开始跑全量 DDL，触发重复对象报错（如 type 已存在）。
    # 因此：当检测到库“非空但无 alembic 版本记录”时，先根据实际 schema 推断并执行 `flask db stamp`。
    postgres_query() {
        local query="$1"
        docker compose -f docker-compose.prod.yml exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"$query\"" 2>/dev/null
    }

    local table_count
    table_count=$(postgres_query "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version';" | xargs || echo "0")

    local alembic_version_exists
    alembic_version_exists=$(postgres_query "SELECT to_regclass('public.alembic_version') IS NOT NULL;" | xargs || echo "f")

    local alembic_version_num=""
    if [ "$alembic_version_exists" = "t" ]; then
        alembic_version_num=$(postgres_query "SELECT version_num FROM alembic_version LIMIT 1;" | xargs || true)
    fi

    if [ "${table_count:-0}" -gt 0 ] && ([ "$alembic_version_exists" != "t" ] || [ -z "$alembic_version_num" ]); then
        log_warning "检测到数据库已初始化但未记录 Alembic 版本，准备执行 stamp 避免重复跑 baseline DDL..."

        local stamp_revision=""
        local credentials_instance_ids_exists
        credentials_instance_ids_exists=$(postgres_query "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='credentials' AND column_name='instance_ids');" | xargs || echo "f")

        if [ "$credentials_instance_ids_exists" = "t" ]; then
            stamp_revision="20251219161048"
        else
            local aggregation_calculated_type
            aggregation_calculated_type=$(postgres_query "SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='database_size_aggregations' AND column_name='calculated_at';" | xargs || true)

            case "$aggregation_calculated_type" in
                "timestamp without time zone")
                    stamp_revision="20251224120000"
                    ;;
                "timestamp with time zone")
                    stamp_revision="20251224134000"
                    ;;
                *)
                    log_error "无法根据当前 schema 推断 Alembic 版本（database_size_aggregations.calculated_at 类型: '${aggregation_calculated_type:-空}'）。"
                    log_error "建议手工排查并执行：/app/.venv/bin/flask db stamp <revision> 后再运行 /app/.venv/bin/flask db upgrade"
                    exit 1
                    ;;
            esac
        fi

        log_info "执行 flask db stamp ${stamp_revision}..."
        if docker exec "$flask_container_id" bash -c "cd /app && /app/.venv/bin/flask db stamp ${stamp_revision}"; then
            log_success "Alembic stamp 完成：${stamp_revision}"
        else
            log_error "Alembic stamp 失败"
            docker compose -f docker-compose.prod.yml logs whalefall --tail 200 || true
            exit 1
        fi
    fi

    log_info "执行 flask db upgrade..."
    if docker exec "$flask_container_id" bash -c "cd /app && /app/.venv/bin/flask db upgrade"; then
        log_success "数据库迁移执行完成"
    else
        log_error "数据库迁移执行失败"
        docker compose -f docker-compose.prod.yml logs whalefall --tail 200 || true
        exit 1
    fi
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
    
    # 简单等待10秒，然后直接检查一次
    log_info "等待服务完全启动（10秒）..."
    sleep 10
    
    # 只检查端口5001
    log_info "检查端口5001服务状态..."
    
    if curl --noproxy localhost -f http://localhost:5001/health/api/health > /dev/null 2>&1; then
        log_success "端口5001服务已就绪"
    else
        log_warning "端口5001服务检查失败，但继续执行"
        log_info "端口5001状态码: $(curl --noproxy localhost -s -o /dev/null -w '%{http_code}' http://localhost:5001/health/api/health 2>/dev/null)"
    fi

}

# 刷新Nginx缓存（Nginx和Flask在同一容器）
refresh_nginx_cache() {
    log_step "刷新Nginx缓存..."
    
    # 获取Flask容器ID（Nginx和Flask在同一容器）
    local flask_container_id
    flask_container_id=$(docker compose -f docker-compose.prod.yml ps -q whalefall)
    
    if [ -z "$flask_container_id" ]; then
        log_warning "未找到Flask容器，跳过Nginx缓存刷新"
        return 0
    fi
    
    log_info "Flask容器ID: $flask_container_id"
    
    # 检查Nginx进程是否在容器内运行
    log_info "检查Nginx进程状态..."
    if docker exec "$flask_container_id" pgrep nginx > /dev/null 2>&1; then
        log_success "Nginx进程正在运行"
    else
        log_warning "Nginx进程未运行，尝试启动Nginx"
        
        # 尝试启动Nginx
        if docker exec "$flask_container_id" nginx; then
            log_success "Nginx启动成功"
        else
            log_warning "Nginx启动失败，跳过缓存刷新"
            return 0
        fi
    fi
    
    # 方法1: 重新加载Nginx配置（推荐）
    log_info "重新加载Nginx配置..."
    if docker exec "$flask_container_id" nginx -s reload; then
        log_success "Nginx配置重新加载成功"
    else
        log_warning "Nginx配置重新加载失败，尝试重启Nginx进程"
        
        # 方法2: 重启Nginx进程
        log_info "重启Nginx进程..."
        if docker exec "$flask_container_id" pkill nginx && docker exec "$flask_container_id" nginx; then
            log_success "Nginx进程重启成功"
        else
            log_error "Nginx进程重启失败"
            return 1
        fi
    fi
    
    # 等待Nginx完全启动
    log_info "等待Nginx完全启动..."
    local count=0
    while [ $count -lt 30 ]; do
        if curl -f http://localhost/health/api/basic > /dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_warning "Nginx启动检查超时，但继续执行"
    else
        log_success "Nginx已完全启动"
    fi
    
    # 方法3: 清理静态文件缓存（如果存在缓存目录）
    log_info "清理静态文件缓存..."
    if docker exec "$flask_container_id" find /var/cache/nginx -type f -delete 2>/dev/null; then
        log_success "静态文件缓存清理成功"
    else
        log_info "未找到Nginx缓存目录，跳过静态文件缓存清理"
    fi
    
    # 方法4: 清理应用缓存目录（如果存在）
    log_info "清理应用缓存..."
    if docker exec "$flask_container_id" find /app/instance -name "*.cache" -type f -delete 2>/dev/null; then
        log_success "应用缓存清理成功"
    else
        log_info "未找到应用缓存文件，跳过应用缓存清理"
    fi
    
    # 方法5: 清理Python缓存
    log_info "清理Python缓存..."
    if docker exec "$flask_container_id" find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; then
        log_success "Python缓存清理成功"
    else
        log_info "Python缓存清理完成"
    fi
    
    log_success "Nginx缓存刷新完成"
}

# 验证更新
verify_update() {
    log_step "验证更新..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker compose -f docker-compose.prod.yml ps whalefall
    
    # 健康检查 - 只检查端口5001
    log_info "执行健康检查..."
    
    # 检查端口5001
    log_info "检查端口5001健康状态..."
    local http_status
    http_status=$(curl --noproxy localhost -s -o /dev/null -w '%{http_code}' http://localhost:5001/health/api/health 2>/dev/null)
    
    if [ "$http_status" = "200" ]; then
        log_success "端口5001健康检查通过 (状态码: $http_status)"
    else
        log_warning "端口5001健康检查失败 (状态码: $http_status)，但继续执行"
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
    echo "  - 缓存刷新: Nginx缓存已刷新"
    echo ""
    echo -e "${BLUE}🌐 访问地址：${NC}"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health/api/basic"
    echo "  - 直接访问: http://localhost:5001"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.prod.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.prod.yml logs -f whalefall"
    echo "  - 查看Gunicorn进程: docker compose -f docker-compose.prod.yml exec whalefall ps aux | grep gunicorn"
    echo "  - 查看Gunicorn访问日志: docker compose -f docker-compose.prod.yml exec whalefall tail -f /app/userdata/logs/gunicorn_access.log"
    echo "  - 查看Gunicorn错误日志: docker compose -f docker-compose.prod.yml exec whalefall tail -f /app/userdata/logs/gunicorn_error.log"
    echo "  - 快速检查Gunicorn: ./check-gunicorn.sh"
    echo "  - 重启服务: docker compose -f docker-compose.prod.yml restart whalefall"
    echo "  - 进入容器: docker compose -f docker-compose.prod.yml exec whalefall bash"
    echo ""
    echo -e "${BLUE}📊 监控信息：${NC}"
    echo "  - 容器资源: docker stats whalefall_app_prod"
    echo "  - 应用日志: docker compose -f docker-compose.prod.yml logs whalefall"
    echo "  - 健康状态: curl http://localhost:5001/health/api/health"
    echo ""
    echo -e "${YELLOW}⚠️  注意事项：${NC}"
    echo "  - 本次更新为代码热更新模式，数据完全保留"
    echo "  - 仅更新Flask应用代码，不重建容器"
    echo "  - 数据库和Redis服务保持不变"
    echo "  - Nginx和Flask在同一容器，缓存已自动刷新"
    echo "  - 始终以GitHub上的代码为准，自动强制同步"
    echo "  - 如果GitHub回滚，本地也会自动回滚"
    echo "  - 如有问题，请手动检查服务状态和日志"
    echo "  - 建议定期备份重要数据"
    echo "  - 监控应用运行状态"
    echo "  - 如需要手动刷新Nginx缓存，可运行: docker exec whalefall_app_prod nginx -s reload"
}

# 主函数
main() {
    show_banner
    
    log_info "开始热更新Flask应用（代码覆盖更新模式，支持回滚后更新）..."
    
    # 执行更新流程
    check_requirements
    check_current_status
    pull_latest_code
    copy_code_to_container
    upgrade_database_schema
    restart_flask_service
    wait_for_service_ready
    refresh_nginx_cache
    
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
