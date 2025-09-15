#!/usr/bin/env python3
"""
设置PostgreSQL环境配置脚本
"""

import os
from pathlib import Path

def create_env_file():
    """创建环境配置文件"""
    env_content = """# 泰摸鱼吧开发环境配置
# 数据库配置
DATABASE_URL=postgresql://taifish_user:Taifish2024!@localhost:5432/taifish_dev
REDIS_URL=redis://:Taifish2024!@localhost:6379/0

# 应用配置
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=userdata/logs/app.log

# 外部数据库配置（用于测试连接）
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_SERVER_USERNAME=sa
SQL_SERVER_PASSWORD=

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USERNAME=root
MYSQL_PASSWORD=

ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCL
ORACLE_USERNAME=system
ORACLE_PASSWORD=

# 应用信息
APP_NAME=泰摸鱼吧
APP_VERSION=1.0.0
APP_DESCRIPTION=数据同步管理平台

# 监控配置
ENABLE_MONITORING=True
PROMETHEUS_PORT=9090

# 备份配置
BACKUP_ENABLED=True
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
"""
    
    env_file = Path(".env.dev")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print(f"已创建环境配置文件: {env_file.absolute()}")

def update_docker_compose():
    """更新Docker Compose文件以使用开发环境初始化脚本"""
    docker_compose_file = Path("docker-compose.dev.yml")
    
    if docker_compose_file.exists():
        content = docker_compose_file.read_text(encoding="utf-8")
        
        # 替换初始化脚本路径
        updated_content = content.replace(
            "./docker/postgres/init.sql",
            "./docker/postgres/init_dev.sql"
        )
        
        docker_compose_file.write_text(updated_content, encoding="utf-8")
        print(f"已更新Docker Compose文件: {docker_compose_file.absolute()}")

def main():
    """主函数"""
    print("设置PostgreSQL环境配置...")
    
    # 创建环境配置文件
    create_env_file()
    
    # 更新Docker Compose文件
    update_docker_compose()
    
    print("\n环境配置完成!")
    print("\n下一步:")
    print("1. 启动PostgreSQL和Redis容器:")
    print("   docker-compose -f docker-compose.dev.yml up -d")
    print("\n2. 运行数据库迁移:")
    print("   python scripts/simple_migrate.py")
    print("\n3. 启动应用:")
    print("   python app.py")

if __name__ == "__main__":
    main()
