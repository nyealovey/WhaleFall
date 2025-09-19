#!/bin/bash

# 鲸落 (TaifishV4) - 快速数据库初始化脚本
# 使用Docker容器执行数据库初始化

set -e

# 配置变量
DB_NAME=${DB_NAME:-whalefall_dev}
DB_USER=${DB_USER:-whalefall_user}
DB_PASSWORD=${DB_PASSWORD}
CONTAINER_NAME=${CONTAINER_NAME:-whalefall_postgres_dev}

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
SQL_DIR="$PROJECT_DIR/sql"

# 检查密码
if [ -z "$DB_PASSWORD" ]; then
    echo "错误: 请设置环境变量 DB_PASSWORD"
    echo "示例: DB_PASSWORD=mypassword $0"
    exit 1
fi

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
