#!/bin/bash

# 鲸落 - 生产环境启动脚本
# 使用Gunicorn + Gevent + Supervisor

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量..."
    
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL 环境变量未设置"
        exit 1
    fi
    
    if [ -z "$REDIS_URL" ]; then
        log_error "REDIS_URL 环境变量未设置"
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY 环境变量未设置"
        exit 1
    fi
    
    log_success "环境变量检查通过"
}

# 等待数据库启动
wait_for_database() {
    log_info "等待数据库启动..."
    
    # 从DATABASE_URL提取数据库信息
    DB_URL=${DATABASE_URL#*://}
    DB_USER=${DB_URL%%:*}
    DB_PASS=${DB_URL#*:}
    DB_PASS=${DB_PASS%%@*}
    DB_HOST=${DB_PASS#*@}
    DB_HOST=${DB_HOST%%:*}
    DB_PORT=${DB_HOST#*:}
    DB_HOST=${DB_HOST%%:*}
    DB_NAME=${DB_URL##*/}
    
    # 等待数据库连接
    until python3 -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port='$DB_PORT',
        user='$DB_USER',
        password='$DB_PASS',
        database='$DB_NAME'
    )
    conn.close()
    print('Database is ready')
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
"; do
        log_info "等待数据库启动..."
        sleep 2
    done
    
    log_success "数据库已就绪"
}

# 等待Redis启动
wait_for_redis() {
    log_info "等待Redis启动..."
    
    # 从REDIS_URL提取Redis信息
    REDIS_URL=${REDIS_URL#*://}
    REDIS_PASS=${REDIS_URL%%@*}
    REDIS_HOST=${REDIS_URL#*@}
    REDIS_HOST=${REDIS_HOST%%:*}
    REDIS_PORT=${REDIS_HOST#*:}
    REDIS_HOST=${REDIS_HOST%%:*}
    
    # 等待Redis连接
    until python3 -c "
import redis
import sys
try:
    r = redis.Redis(
        host='$REDIS_HOST',
        port='$REDIS_PORT',
        password='$REDIS_PASS' if '$REDIS_PASS' != '$REDIS_URL' else None,
        decode_responses=True
    )
    r.ping()
    print('Redis is ready')
except Exception as e:
    print(f'Redis not ready: {e}')
    sys.exit(1)
"; do
        log_info "等待Redis启动..."
        sleep 2
    done
    
    log_success "Redis已就绪"
}

# 数据库迁移
migrate_database() {
    log_info "执行数据库迁移..."
    
    python3 -m flask db upgrade
    
    log_success "数据库迁移完成"
}

# 创建管理员用户
create_admin() {
    log_info "检查管理员用户..."
    
    python3 -c "
from app import create_app
from app.models.user import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User.create_admin()
        print('管理员用户已创建')
    else:
        print('管理员用户已存在')
"
    
    log_success "管理员用户检查完成"
}

# 启动应用
start_application() {
    log_info "启动生产环境应用..."
    
    # 使用Gunicorn启动
    exec gunicorn \
        --config /app/gunicorn.conf.py \
        --bind 0.0.0.0:5000 \
        --workers 4 \
        --worker-class gevent \
        --worker-connections 1000 \
        --timeout 30 \
        --keepalive 2 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --preload \
        --access-logfile /app/userdata/logs/gunicorn_access.log \
        --error-logfile /app/userdata/logs/gunicorn_error.log \
        --log-level info \
        --user whalefall \
        --group whalefall \
        wsgi:application
}

# 主函数
main() {
    log_info "启动鲸落生产环境..."
    
    # 检查环境
    check_environment
    
    # 等待依赖服务
    wait_for_database
    wait_for_redis
    
    # 初始化数据库
    migrate_database
    create_admin
    
    # 启动应用
    start_application
}

# 执行主函数
main "$@"
