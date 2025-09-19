#!/bin/bash

# 鲸落 (TaifishV4) - 快速数据库初始化脚本
# 使用Docker容器执行数据库初始化

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SQL_DIR="$PROJECT_DIR/sql"

# 加载.env文件
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
    echo "✅ 已加载 .env 文件"
else
    echo "❌ 错误: .env 文件不存在"
    echo "请先复制 env.template 为 .env 并配置相应的环境变量"
    echo "示例: cp env.template .env"
    exit 1
fi

# 从.env文件获取配置变量
DB_NAME=${POSTGRES_DB}
DB_USER=${POSTGRES_USER}
DB_PASSWORD=${POSTGRES_PASSWORD}
CONTAINER_NAME=${CONTAINER_NAME:-whalefall_postgres_dev}

# 验证必需的环境变量
if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ 错误: 缺少必需的环境变量"
    echo "请在 .env 文件中设置以下变量:"
    echo "  POSTGRES_DB=数据库名"
    echo "  POSTGRES_USER=数据库用户名"
    echo "  POSTGRES_PASSWORD=数据库密码"
    exit 1
fi

echo "📋 数据库配置:"
echo "  数据库名: $DB_NAME"
echo "  用户名: $DB_USER"
echo "  容器名: $CONTAINER_NAME"

# 检查Docker容器是否运行
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "错误: PostgreSQL容器 '$CONTAINER_NAME' 未运行"
    echo "请先启动数据库服务:"
    echo "  docker-compose -f docker-compose.dev.yml up -d postgres"
    exit 1
fi

echo "开始初始化数据库: $CONTAINER_NAME/$DB_NAME"

# 执行初始化脚本
echo "执行数据库结构初始化..."
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_DIR/init_postgresql.sql"

echo "导入权限配置..."
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_DIR/permission_configs.sql"

echo "初始化调度任务..."
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_DIR/init_scheduler_tasks.sql"

echo "数据库初始化完成！"
