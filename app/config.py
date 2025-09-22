"""
鲸落 - 统一配置管理
支持开发和生产环境，通过环境变量控制
"""

import os
from datetime import timedelta

from app.constants import DefaultConfig, SystemConstants


class Config:
    """统一配置类 - 支持开发和生产环境"""

    # 基础配置
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", SystemConstants.JWT_ACCESS_TOKEN_EXPIRES))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(
            os.getenv(
                "JWT_REFRESH_TOKEN_EXPIRES",
                SystemConstants.JWT_REFRESH_TOKEN_EXPIRES // 86400,
            )
        )
    )

    # 数据库配置 - 必须从环境变量获取，不允许硬编码
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable must be set")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": SystemConstants.CONNECTION_TIMEOUT,
        "max_overflow": 10,
        "pool_size": SystemConstants.MAX_CONNECTIONS,
        "echo": DEBUG,  # 开发环境显示SQL，生产环境不显示
    }

    # Redis配置 - 必须从环境变量获取，不允许硬编码
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL")
    if not CACHE_REDIS_URL:
        raise ValueError("CACHE_REDIS_URL environment variable must be set")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", SystemConstants.DEFAULT_CACHE_TIMEOUT))

    # 安全配置
    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", SystemConstants.PASSWORD_HASH_ROUNDS))
    WTF_CSRF_ENABLED = True

    # 文件上传配置
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", DefaultConfig.UPLOAD_FOLDER)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", SystemConstants.MAX_FILE_SIZE))

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", DefaultConfig.LOG_LEVEL)
    LOG_FILE = os.getenv("LOG_FILE", DefaultConfig.LOG_FILE)
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", SystemConstants.LOG_MAX_SIZE))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", SystemConstants.LOG_BACKUP_COUNT))

    # 外部数据库配置
    SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", DefaultConfig.SQL_SERVER_HOST)
    SQL_SERVER_PORT = int(os.getenv("SQL_SERVER_PORT", DefaultConfig.SQL_SERVER_PORT))
    SQL_SERVER_USERNAME = os.getenv("SQL_SERVER_USERNAME", "sa")
    SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "")

    MYSQL_HOST = os.getenv("MYSQL_HOST", DefaultConfig.MYSQL_HOST)
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", DefaultConfig.MYSQL_PORT))
    MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    ORACLE_HOST = os.getenv("ORACLE_HOST", DefaultConfig.ORACLE_HOST)
    ORACLE_PORT = int(os.getenv("ORACLE_PORT", DefaultConfig.ORACLE_PORT))
    ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "ORCL")
    ORACLE_USERNAME = os.getenv("ORACLE_USERNAME", "system")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")

    # 应用配置
    APP_NAME = os.getenv("APP_NAME", "鲸落")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.2")

    # 监控配置
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "True").lower() == "true"
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 9090))

    # 备份配置
    BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "True").lower() == "true"
    BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", 30))


# 统一配置字典 - 支持开发和生产环境
config = {
    "development": Config,
    "production": Config,
    "default": Config,
}
