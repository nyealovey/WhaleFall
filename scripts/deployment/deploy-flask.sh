#!/bin/bash

# Flask应用部署脚本
# 部署：Flask应用、APScheduler
# 依赖：基础环境（PostgreSQL、Redis、Nginx）

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

# 检查基础环境
check_base_environment() {
    log_info "检查基础环境..."
    
    # 检查网络
    if ! docker network ls | grep -q whalefall_network; then
        log_error "基础环境未启动，请先运行 ./scripts/deploy-base.sh"
        exit 1
    fi
    
    # 检查PostgreSQL
    if ! docker-compose -f docker-compose.base.yml exec postgres pg_isready -U ${POSTGRES_USER:-whalefall_user} -d ${POSTGRES_DB:-whalefall_prod} &>/dev/null; then
        log_error "PostgreSQL未就绪，请检查基础环境"
        exit 1
    fi
    
    # 检查Redis
    if ! docker-compose -f docker-compose.base.yml exec redis redis-cli ping &>/dev/null; then
        log_error "Redis未就绪，请检查基础环境"
        exit 1
    fi
    
    log_success "基础环境检查通过"
}

# 构建Flask镜像
build_flask_image() {
    log_info "构建Flask应用镜像..."
    
    # 检查Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile不存在"
        exit 1
    fi
    
    # 构建镜像
    docker build -t whalefall:latest .
    
    log_success "Flask应用镜像构建完成"
}

# 检查环境配置
check_env_config() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        log_error "环境配置文件.env不存在"
        exit 1
    fi
    
    source .env
    
    # 检查必要的环境变量
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "环境变量 $var 未设置"
            exit 1
        fi
    done
    
    log_success "环境配置检查通过"
}

# 启动Flask应用
start_flask_application() {
    log_info "启动Flask应用..."
    
    # 启动Flask服务
    docker-compose -f docker-compose.flask.yml up -d
    
    log_success "Flask应用启动完成"
}

# 等待Flask应用就绪
wait_for_flask() {
    log_info "等待Flask应用就绪..."
    
    local timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:5001/health &>/dev/null; then
            log_success "Flask应用已就绪"
            break
        fi
        sleep 3
        timeout=$((timeout - 3))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "Flask应用启动超时"
        log_info "查看Flask应用日志："
        docker-compose -f docker-compose.flask.yml logs whalefall
        exit 1
    fi
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    
    # 等待数据库完全就绪
    sleep 10
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose -f docker-compose.flask.yml exec whalefall python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表创建完成')
"
    
    # 初始化权限配置
    log_info "初始化权限配置..."
    docker-compose -f docker-compose.flask.yml exec whalefall python -c "
from app import create_app
from app.models.permission_config import PermissionConfig
app = create_app()
with app.app_context():
    PermissionConfig.init_default_permissions()
    print('权限配置初始化完成')
"
    
    # 创建管理员用户
    log_info "创建管理员用户..."
    docker-compose -f docker-compose.flask.yml exec whalefall python -c "
from app import create_app
from app.models.user import User
from werkzeug.security import generate_password_hash
app = create_app()
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@whalefall.com',
            password_hash=generate_password_hash('admin123'),
            is_active=True,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('管理员用户创建完成 (用户名: admin, 密码: admin123)')
    else:
        print('管理员用户已存在')
"
    
    log_success "数据库初始化完成"
}

# 验证Flask应用
verify_flask_application() {
    log_info "验证Flask应用..."
    
    # 检查健康状态
    if curl -s http://localhost:5001/health | grep -q "healthy"; then
        log_success "Flask应用健康检查通过"
    else
        log_error "Flask应用健康检查失败"
        exit 1
    fi
    
    # 检查Nginx代理
    if curl -s http://localhost/health | grep -q "healthy"; then
        log_success "Nginx代理正常"
    else
        log_warning "Nginx代理异常（可能正常，需要配置SSL）"
    fi
    
    log_success "Flask应用验证通过"
}

# 显示部署结果
show_deployment_result() {
    log_info "部署结果："
    echo "=================================="
    
    # 显示所有服务状态
    echo "基础环境服务："
    docker-compose -f docker-compose.base.yml ps
    echo ""
    echo "Flask应用服务："
    docker-compose -f docker-compose.flask.yml ps
    echo "=================================="
    
    log_info "访问地址："
    echo "  - 主应用: http://localhost"
    echo "  - 管理界面: http://localhost/admin"
    echo "  - 健康检查: http://localhost/health"
    echo "  - API文档: http://localhost/api/docs"
    echo ""
    
    log_info "默认管理员账户："
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo "  （请及时修改密码）"
    echo ""
    
    log_info "管理命令："
    echo "  查看所有日志: docker-compose -f docker-compose.base.yml logs -f && docker-compose -f docker-compose.flask.yml logs -f"
    echo "  查看Flask日志: docker-compose -f docker-compose.flask.yml logs -f whalefall"
    echo "  停止所有服务: ./scripts/stop-all.sh"
    echo "  重启Flask应用: docker-compose -f docker-compose.flask.yml restart"
    echo "  进入Flask容器: docker-compose -f docker-compose.flask.yml exec whalefall bash"
    echo ""
    
    log_warning "安全提醒："
    echo "  1. 请立即修改默认管理员密码"
    echo "  2. 配置SSL证书启用HTTPS"
    echo "  3. 配置防火墙规则"
    echo "  4. 定期备份数据库"
}

# 主函数
main() {
    echo "🐟 鲸落Flask应用部署脚本"
    echo "=================================="
    
    check_base_environment
    check_env_config
    build_flask_image
    start_flask_application
    wait_for_flask
    init_database
    verify_flask_application
    show_deployment_result
    
    echo "=================================="
    log_success "Flask应用部署完成！"
    echo "=================================="
}

# 运行主函数
main "$@"
