#!/bin/bash

# 环境变量验证脚本
# 确保所有必需的配置都存在，否则报错退出

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查.env文件是否存在
if [ ! -f ".env" ]; then
    log_error ".env文件不存在！"
    log_error "请复制env.development或env.production为.env并配置相应的环境变量"
    exit 1
fi

# 加载.env文件
set -a
source .env
set +a

log_info "开始验证环境变量..."

# 必需的环境变量列表
REQUIRED_VARS=(
    "POSTGRES_DB"
    "POSTGRES_USER" 
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "SECRET_KEY"
    "JWT_SECRET_KEY"
    "BCRYPT_LOG_ROUNDS"
    "APP_NAME"
    "APP_VERSION"
    "FLASK_ENV"
    "FLASK_DEBUG"
    "LOG_LEVEL"
    "CACHE_TYPE"
    "CACHE_REDIS_URL"
    "DATABASE_URL"
    "PERMANENT_SESSION_LIFETIME"
)

# 可选的环境变量列表（有默认值）
OPTIONAL_VARS=(
    "FLASK_HOST"
    "FLASK_PORT"
    "HTTP_PROXY"
    "HTTPS_PROXY"
    "NO_PROXY"
)

# 验证必需的环境变量
missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

# 如果有缺失的必需变量，报错退出
if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error "以下必需的环境变量未设置："
    for var in "${missing_vars[@]}"; do
        log_error "  - $var"
    done
    log_error ""
    log_error "请在.env文件中设置这些变量"
    exit 1
fi

# 验证可选的环境变量
log_info "检查可选环境变量..."
for var in "${OPTIONAL_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_warning "可选环境变量 $var 未设置，将使用默认值"
    fi
done

# 验证数据库URL格式
log_info "验证数据库URL格式..."

# 验证数据库URL
if [[ ! "$DATABASE_URL" =~ ^postgresql://.*@.*:.*/.*$ ]]; then
    log_error "DATABASE_URL格式错误！"
    log_error "应该是: postgresql://用户名:密码@主机:端口/数据库名"
    log_error "当前值: $DATABASE_URL"
    exit 1
fi

# 验证Redis URL格式
if [[ ! "$CACHE_REDIS_URL" =~ ^redis://.*@redis:6379/.*$ ]]; then
    log_error "CACHE_REDIS_URL格式错误！"
    log_error "应该是: redis://:密码@redis:6379/数据库号"
    log_error "当前值: $CACHE_REDIS_URL"
    exit 1
fi

# 验证数值类型的环境变量
log_info "验证数值类型环境变量..."

# 验证BCRYPT_LOG_ROUNDS
if ! [[ "$BCRYPT_LOG_ROUNDS" =~ ^[0-9]+$ ]] || [ "$BCRYPT_LOG_ROUNDS" -lt 4 ] || [ "$BCRYPT_LOG_ROUNDS" -gt 20 ]; then
    log_error "BCRYPT_LOG_ROUNDS必须是4-20之间的整数"
    log_error "当前值: $BCRYPT_LOG_ROUNDS"
    exit 1
fi

# 验证FLASK_PORT
if [ -n "$FLASK_PORT" ] && (! [[ "$FLASK_PORT" =~ ^[0-9]+$ ]] || [ "$FLASK_PORT" -lt 1024 ] || [ "$FLASK_PORT" -gt 65535 ]); then
    log_error "FLASK_PORT必须是1024-65535之间的整数"
    log_error "当前值: $FLASK_PORT"
    exit 1
fi

# 验证PERMANENT_SESSION_LIFETIME
if ! [[ "$PERMANENT_SESSION_LIFETIME" =~ ^[0-9]+$ ]] || [ "$PERMANENT_SESSION_LIFETIME" -lt 300 ]; then
    log_error "PERMANENT_SESSION_LIFETIME必须是大于等于300的整数（秒）"
    log_error "当前值: $PERMANENT_SESSION_LIFETIME"
    exit 1
fi

# 验证布尔类型的环境变量
log_info "验证布尔类型环境变量..."

# 验证FLASK_DEBUG
if [ "$FLASK_DEBUG" != "0" ] && [ "$FLASK_DEBUG" != "1" ] && [ "$FLASK_DEBUG" != "true" ] && [ "$FLASK_DEBUG" != "false" ]; then
    log_error "FLASK_DEBUG必须是0、1、true或false"
    log_error "当前值: $FLASK_DEBUG"
    exit 1
fi

# 验证DEBUG
if [ -n "$DEBUG" ] && [ "$DEBUG" != "true" ] && [ "$DEBUG" != "false" ]; then
    log_error "DEBUG必须是true或false"
    log_error "当前值: $DEBUG"
    exit 1
fi

# 验证TESTING
if [ -n "$TESTING" ] && [ "$TESTING" != "true" ] && [ "$TESTING" != "false" ]; then
    log_error "TESTING必须是true或false"
    log_error "当前值: $TESTING"
    exit 1
fi

log_success "所有环境变量验证通过！"

# 显示关键配置信息
log_info "关键配置信息："
echo "  数据库: $POSTGRES_DB"
echo "  用户: $POSTGRES_USER"
echo "  应用名称: $APP_NAME"
echo "  应用版本: $APP_VERSION"
echo "  Flask环境: $FLASK_ENV"
echo "  Flask调试: $FLASK_DEBUG"
echo "  日志级别: $LOG_LEVEL"
echo "  缓存类型: $CACHE_TYPE"

log_success "环境变量验证完成！"
