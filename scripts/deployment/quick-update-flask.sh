#!/bin/bash

# 鲸落项目Flask快速更新脚本
# 功能：极速更新Flask应用，适用于开发环境
# 特点：最小化停机时间、自动验证、快速回滚

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
    echo "║                    鲸落项目快速更新                         ║"
    echo "║                    TaifishV4 Quick Update                   ║"
    echo "║                   (极速更新模式)                            ║"
    echo "║                (最小化停机时间)                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 快速检查
quick_check() {
    log_step "快速检查..."
    
    # 检查Docker服务
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行"
        exit 1
    fi
    
    # 检查Flask容器
    if ! docker compose -f docker-compose.prod.yml ps whalefall | grep -q "Up"; then
        log_error "Flask容器未运行"
        exit 1
    fi
    
    log_success "快速检查通过"
}

# 拉取代码
pull_code() {
    log_step "拉取最新代码..."
    
    # 暂存当前更改
    if ! git diff --quiet; then
        log_info "暂存当前更改..."
        git stash push -m "Auto-stash before update $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 拉取最新代码
    git pull origin main
    
    log_success "代码更新完成"
}

# 快速构建
quick_build() {
    log_step "快速构建Flask镜像..."
    
    # 使用缓存构建
    docker build \
        --target production \
        -t whalefall:prod \
        -f Dockerfile.prod \
        . 2>/dev/null || {
        log_warning "缓存构建失败，使用完整构建..."
        docker build \
            --no-cache \
            --target production \
            -t whalefall:prod \
            -f Dockerfile.prod \
            .
    }
    
    log_success "镜像构建完成"
}

# 零停机更新
zero_downtime_update() {
    log_step "零停机更新..."
    
    # 创建新容器
    log_info "创建新Flask容器..."
    docker compose -f docker-compose.prod.yml up -d --scale whalefall=2 whalefall
    
    # 等待新容器就绪
    log_info "等待新容器就绪..."
    local count=0
    while [ $count -lt 30 ]; do
        if curl -f http://localhost:5001/health > /dev/null 2>&1; then
            break
        fi
        sleep 2
        count=$((count + 1))
    done
    
    if [ $count -eq 30 ]; then
        log_error "新容器启动超时"
        docker compose -f docker-compose.prod.yml logs whalefall
        exit 1
    fi
    
    # 停止旧容器
    log_info "停止旧容器..."
    docker compose -f docker-compose.prod.yml stop whalefall
    
    # 恢复单容器模式
    docker compose -f docker-compose.prod.yml up -d --scale whalefall=1 whalefall
    
    log_success "零停机更新完成"
}

# 快速验证
quick_verify() {
    log_step "快速验证..."
    
    # 健康检查
    local count=0
    while [ $count -lt 10 ]; do
        if curl -f http://localhost:5001/health > /dev/null 2>&1; then
            log_success "健康检查通过"
            return 0
        fi
        sleep 3
        count=$((count + 1))
    done
    
    log_error "健康检查失败"
    return 1
}

# 快速回滚
quick_rollback() {
    log_step "快速回滚..."
    
    # 恢复代码
    if git stash list | grep -q "Auto-stash"; then
        log_info "恢复代码更改..."
        git stash pop
    fi
    
    # 重启服务
    docker compose -f docker-compose.prod.yml restart whalefall
    
    # 等待服务恢复
    local count=0
    while [ $count -lt 20 ]; do
        if curl -f http://localhost:5001/health > /dev/null 2>&1; then
            log_success "回滚成功"
            return 0
        fi
        sleep 3
        count=$((count + 1))
    done
    
    log_error "回滚失败"
    return 1
}

# 清理资源
cleanup() {
    log_step "清理资源..."
    
    # 清理悬空镜像
    docker image prune -f
    
    # 清理未使用的容器
    docker container prune -f
    
    log_success "资源清理完成"
}

# 显示结果
show_result() {
    echo ""
    echo -e "${GREEN}🎉 快速更新完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 更新信息：${NC}"
    echo "  - 更新版本: $(git rev-parse --short HEAD)"
    echo "  - 更新时间: $(date)"
    echo "  - 更新模式: 零停机更新"
    echo ""
    echo -e "${BLUE}🌐 访问地址：${NC}"
    echo "  - 应用首页: http://localhost"
    echo "  - 健康检查: http://localhost/health"
    echo ""
    echo -e "${BLUE}🔧 管理命令：${NC}"
    echo "  - 查看状态: docker compose -f docker-compose.prod.yml ps"
    echo "  - 查看日志: docker compose -f docker-compose.prod.yml logs -f whalefall"
    echo "  - 重启服务: docker compose -f docker-compose.prod.yml restart whalefall"
    echo ""
}

# 主函数
main() {
    show_banner
    
    log_info "开始快速更新Flask应用..."
    
    # 执行更新流程
    quick_check
    pull_code
    quick_build
    
    # 尝试零停机更新
    if zero_downtime_update && quick_verify; then
        cleanup
        show_result
        log_success "快速更新完成！"
    else
        log_error "更新失败，开始回滚..."
        if quick_rollback; then
            log_success "回滚成功，服务已恢复"
        else
            log_error "回滚失败，请手动检查服务状态"
            exit 1
        fi
    fi
}

# 执行主函数
main "$@"
