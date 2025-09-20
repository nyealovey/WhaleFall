#!/bin/bash

# 鲸落 (TaifishV4) - 手动初始化数据库脚本
# 用于手动导入数据库结构和初始数据

set -e

# 加载.env文件
if [ -f ".env" ]; then
    source .env
    echo "已加载.env文件"
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
DB_NAME=${POSTGRES_DB:-${DB_NAME:-whalefall_dev}}
DB_USER=${POSTGRES_USER:-${DB_USER:-whalefall_user}}
DB_PASSWORD=${POSTGRES_PASSWORD:-${DB_PASSWORD}}
CONTAINER_NAME=${CONTAINER_NAME:-whalefall_postgres_dev}

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
SQL_DIR="$PROJECT_DIR/sql"

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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "docker 命令未找到，请安装 Docker"
        exit 1
    fi
    
    if [ -z "$DB_PASSWORD" ]; then
        log_error "请设置环境变量 DB_PASSWORD"
        exit 1
    fi
    
    # 检查Docker容器是否运行
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "PostgreSQL容器 '$CONTAINER_NAME' 未运行"
        log_info "请先启动数据库服务:"
        log_info "  docker-compose -f docker-compose.dev.yml up -d postgres"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."
    
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "数据库连接成功"
    else
        log_error "无法连接到数据库，请检查容器状态"
        exit 1
    fi
}

# 执行SQL文件
execute_sql_file() {
    local sql_file="$1"
    local description="$2"
    
    if [ ! -f "$sql_file" ]; then
        log_warning "SQL文件不存在: $sql_file"
        return 1
    fi
    
    log_info "执行: $description"
    log_info "文件: $sql_file"
    
    if docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$sql_file"; then
        log_success "完成: $description"
        return 0
    else
        log_error "失败: $description"
        return 1
    fi
}

# 显示使用说明
show_usage() {
    echo "鲸落 (TaifishV4) - 数据库初始化脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  --database DATABASE     数据库名称 (默认: whalefall_dev)"
    echo "  --user USER             数据库用户 (默认: whalefall_user)"
    echo "  --password PASSWORD     数据库密码 (必需)"
    echo "  --container CONTAINER   PostgreSQL容器名称 (默认: whalefall_postgres_dev)"
    echo "  --init-only             仅初始化数据库结构"
    echo "  --data-only             仅导入数据"
    echo "  --all                   初始化结构并导入数据 (默认)"
    echo ""
    echo "环境变量:"
    echo "  DB_NAME                 数据库名称"
    echo "  DB_USER                 数据库用户"
    echo "  DB_PASSWORD             数据库密码 (必需)"
    echo "  CONTAINER_NAME          PostgreSQL容器名称"
    echo ""
    echo "示例:"
    echo "  $0 --password mypassword"
    echo "  $0 --database whalefall_dev --user whalefall_user --password mypassword"
    echo "  $0 --container whalefall_postgres_dev --password mypassword"
    echo "  DB_PASSWORD=mypassword $0"
}

# 主函数
main() {
    local init_only=false
    local data_only=false
    local all=true
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --database)
                DB_NAME="$2"
                shift 2
                ;;
            --user)
                DB_USER="$2"
                shift 2
                ;;
            --password)
                DB_PASSWORD="$2"
                shift 2
                ;;
            --container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --init-only)
                init_only=true
                all=false
                shift
                ;;
            --data-only)
                data_only=true
                all=false
                shift
                ;;
            --all)
                all=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "开始初始化数据库..."
    log_info "容器: $CONTAINER_NAME"
    log_info "数据库: $DB_NAME"
    log_info "用户: $DB_USER"
    
    # 检查依赖和连接
    check_dependencies
    check_database_connection
    
    # 执行初始化
    local success_count=0
    local total_count=0
    
    if [ "$all" = true ] || [ "$init_only" = true ]; then
        log_info "=== 初始化数据库结构 ==="
        
        # 执行基础结构初始化
        if execute_sql_file "$SQL_DIR/init_postgresql.sql" "初始化PostgreSQL数据库结构"; then
            ((success_count++))
        fi
        ((total_count++))
        
        # 执行权限配置
        if execute_sql_file "$SQL_DIR/permission_configs.sql" "导入权限配置"; then
            ((success_count++))
        fi
        ((total_count++))
        
        # 执行调度任务初始化
        if execute_sql_file "$SQL_DIR/init_scheduler_tasks.sql" "初始化调度任务"; then
            ((success_count++))
        fi
        ((total_count++))
    fi
    
    if [ "$all" = true ] || [ "$data_only" = true ]; then
        log_info "=== 导入初始数据 ==="
        
        # 执行导出的权限配置
        if execute_sql_file "$SQL_DIR/exported_permission_configs.sql" "导入导出的权限配置"; then
            ((success_count++))
        fi
        ((total_count++))
    fi
    
    # 显示结果
    log_info "=== 初始化完成 ==="
    log_info "成功: $success_count/$total_count"
    
    if [ $success_count -eq $total_count ]; then
        log_success "数据库初始化完全成功！"
        exit 0
    else
        log_warning "数据库初始化部分成功，请检查失败的步骤"
        exit 1
    fi
}

# 运行主函数
main "$@"
