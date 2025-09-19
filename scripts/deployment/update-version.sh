#!/bin/bash

# 版本更新脚本
# 用于更新Flask应用版本，支持滚动更新

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

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项] [版本号]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示此帮助信息"
    echo "  -b, --backup        更新前备份数据"
    echo "  -f, --force         强制更新（跳过确认）"
    echo "  -r, --rollback      回滚到上一个版本"
    echo "  -s, --status        显示当前版本状态"
    echo "  -c, --check         检查更新可用性"
    echo ""
    echo "示例:"
    echo "  $0 4.1.0            # 更新到版本4.1.0"
    echo "  $0 -b 4.1.0         # 备份后更新到版本4.1.0"
    echo "  $0 -r                # 回滚到上一个版本"
    echo "  $0 -s                # 显示当前版本状态"
    echo "  $0 -c                # 检查更新可用性"
}

# 检查当前版本状态
check_current_status() {
    log_info "检查当前版本状态..."
    
    # 检查基础环境
    if ! docker-compose -f docker-compose.base.yml ps | grep -q "Up"; then
        log_error "基础环境未运行，请先启动基础环境"
        exit 1
    fi
    
    # 检查Flask应用
    if ! docker-compose -f docker-compose.flask.yml ps | grep -q "Up"; then
        log_warning "Flask应用未运行"
        return 1
    fi
    
    # 获取当前版本
    local current_version=$(docker-compose -f docker-compose.flask.yml exec whalefall python -c "
from app import create_app
app = create_app()
with app.app_context():
    print(app.config.get('APP_VERSION', 'unknown'))
" 2>/dev/null || echo "unknown")
    
    log_info "当前版本: $current_version"
    return 0
}

# 备份数据
backup_data() {
    log_info "备份数据..."
    
    local backup_dir="/opt/whale_fall_data/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 备份数据库
    log_info "备份PostgreSQL数据库..."
    docker-compose -f docker-compose.base.yml exec postgres pg_dump -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} > "$backup_dir/database.sql"
    
    # 备份Redis数据
    log_info "备份Redis数据..."
    docker-compose -f docker-compose.base.yml exec redis redis-cli --rdb /data/dump.rdb
    docker cp whalefall_redis:/data/dump.rdb "$backup_dir/redis.rdb"
    
    # 备份应用数据
    log_info "备份应用数据..."
    cp -r /opt/whale_fall_data/app "$backup_dir/"
    
    # 备份配置文件
    log_info "备份配置文件..."
    cp .env "$backup_dir/"
    cp docker-compose.*.yml "$backup_dir/"
    
    log_success "数据备份完成: $backup_dir"
    echo "$backup_dir" > /tmp/whalefall_backup_path
}

# 检查更新可用性
check_updates() {
    log_info "检查更新可用性..."
    
    # 检查Git状态
    if [ -d ".git" ]; then
        git fetch origin
        local current_branch=$(git branch --show-current)
        local remote_commits=$(git rev-list HEAD..origin/$current_branch --count)
        
        if [ "$remote_commits" -gt 0 ]; then
            log_info "发现 $remote_commits 个新提交"
            git log --oneline HEAD..origin/$current_branch
        else
            log_info "当前分支已是最新"
        fi
    else
        log_warning "非Git仓库，无法检查更新"
    fi
    
    # 检查Docker镜像更新
    log_info "检查Docker镜像更新..."
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    docker pull nginx:alpine
    
    log_success "更新检查完成"
}

# 更新代码
update_code() {
    local version=$1
    
    log_info "更新代码到版本 $version..."
    
    if [ -d ".git" ]; then
        # Git仓库更新
        git fetch origin
        git checkout main || git checkout master
        git pull origin main || git pull origin master
        
        if [ -n "$version" ] && [ "$version" != "latest" ]; then
            git checkout "v$version" 2>/dev/null || git checkout "$version" 2>/dev/null || {
                log_warning "未找到版本标签 $version，使用最新代码"
            }
        fi
    else
        log_warning "非Git仓库，请手动更新代码"
    fi
    
    log_success "代码更新完成"
}

# 构建新镜像
build_new_image() {
    local version=$1
    
    log_info "构建新版本镜像..."
    
    # 构建Flask镜像
    if [ -n "$version" ]; then
        docker build -t whalefall:$version .
        docker tag whalefall:$version whalefall:latest
    else
        docker build -t whalefall:latest .
    fi
    
    log_success "镜像构建完成"
}

# 滚动更新Flask应用
rolling_update() {
    local version=$1
    
    log_info "执行滚动更新..."
    
    # 停止Flask应用
    docker-compose -f docker-compose.flask.yml down
    
    # 启动新版本
    docker-compose -f docker-compose.flask.yml up -d
    
    # 等待应用就绪
    local timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:5001/health &>/dev/null; then
            log_success "新版本应用已就绪"
            break
        fi
        sleep 3
        timeout=$((timeout - 3))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "新版本应用启动超时"
        return 1
    fi
    
    log_success "滚动更新完成"
}

# 回滚到上一个版本
rollback() {
    log_info "回滚到上一个版本..."
    
    # 检查备份
    local backup_path=$(cat /tmp/whalefall_backup_path 2>/dev/null || echo "")
    if [ -z "$backup_path" ] || [ ! -d "$backup_path" ]; then
        log_error "未找到备份，无法回滚"
        exit 1
    fi
    
    # 停止当前应用
    docker-compose -f docker-compose.flask.yml down
    
    # 恢复数据库
    log_info "恢复数据库..."
    docker-compose -f docker-compose.base.yml exec -T postgres psql -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} < "$backup_path/database.sql"
    
    # 恢复应用数据
    log_info "恢复应用数据..."
    rm -rf /opt/whale_fall_data/app
    cp -r "$backup_path/app" /opt/whale_fall_data/
    
    # 启动应用
    docker-compose -f docker-compose.flask.yml up -d
    
    log_success "回滚完成"
}

# 验证更新结果
verify_update() {
    log_info "验证更新结果..."
    
    # 检查应用健康状态
    if curl -s http://localhost:5001/health | grep -q "healthy"; then
        log_success "应用健康检查通过"
    else
        log_error "应用健康检查失败"
        return 1
    fi
    
    # 检查新版本
    local new_version=$(docker-compose -f docker-compose.flask.yml exec whalefall python -c "
from app import create_app
app = create_app()
with app.app_context():
    print(app.config.get('APP_VERSION', 'unknown'))
" 2>/dev/null || echo "unknown")
    
    log_info "更新后版本: $new_version"
    log_success "更新验证通过"
}

# 清理旧镜像
cleanup_old_images() {
    log_info "清理旧镜像..."
    
    # 删除悬空镜像
    docker image prune -f
    
    # 删除未使用的镜像
    docker image prune -a -f --filter "until=24h"
    
    log_success "镜像清理完成"
}

# 主函数
main() {
    local version=""
    local backup=false
    local force=false
    local rollback_mode=false
    local status_only=false
    local check_only=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -b|--backup)
                backup=true
                shift
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -r|--rollback)
                rollback_mode=true
                shift
                ;;
            -s|--status)
                status_only=true
                shift
                ;;
            -c|--check)
                check_only=true
                shift
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                version="$1"
                shift
                ;;
        esac
    done
    
    # 状态检查
    if $status_only; then
        check_current_status
        exit 0
    fi
    
    # 更新检查
    if $check_only; then
        check_updates
        exit 0
    fi
    
    # 回滚模式
    if $rollback_mode; then
        rollback
        exit 0
    fi
    
    # 确认更新
    if [ -z "$version" ]; then
        log_error "请指定版本号"
        show_help
        exit 1
    fi
    
    if ! $force; then
        echo "即将更新到版本: $version"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    echo "🐟 鲸落版本更新脚本"
    echo "=================================="
    
    # 检查当前状态
    check_current_status
    
    # 备份数据
    if $backup; then
        backup_data
    fi
    
    # 检查更新
    check_updates
    
    # 更新代码
    update_code "$version"
    
    # 构建新镜像
    build_new_image "$version"
    
    # 滚动更新
    rolling_update "$version"
    
    # 验证更新
    verify_update
    
    # 清理旧镜像
    cleanup_old_images
    
    echo "=================================="
    log_success "版本更新完成！"
    echo "=================================="
}

# 运行主函数
main "$@"
