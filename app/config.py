"""
鲸落 - 统一配置管理
支持开发和生产环境，通过环境变量控制

本文件只包含实际使用的配置项。
"""

import os
from datetime import timedelta


class Config:
    """统一配置类 - 支持开发和生产环境
    
    所有配置项优先从环境变量读取，如果环境变量不存在则使用默认值。
    只包含实际被代码使用的配置项。
    """

    # ============================================================================
    # 数据库连接配置（内部使用）
    # ============================================================================
    CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
    MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "20"))

    # ============================================================================
    # 密码配置（内部使用）
    # ============================================================================
    PASSWORD_HASH_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))

    # ============================================================================
    # 文件上传配置（内部使用）
    # ============================================================================
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(16 * 1024 * 1024)))  # 16MB

    # ============================================================================
    # 速率限制配置
    # ============================================================================
    LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))  # 每窗口最多尝试次数
    LOGIN_RATE_WINDOW = int(os.getenv("LOGIN_RATE_WINDOW", "60"))  # 1分钟

    # ============================================================================
    # 日志配置
    # ============================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "userdata/logs/app.log")
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # ============================================================================
    # JWT配置
    # ============================================================================
    # 内部使用的秒数值（用于计算timedelta）
    _JWT_ACCESS_TOKEN_EXPIRES_SECONDS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))  # 1小时
    _JWT_REFRESH_TOKEN_EXPIRES_SECONDS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_SECONDS", "2592000"))  # 30天
    
    # 实际使用的timedelta对象
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=_JWT_ACCESS_TOKEN_EXPIRES_SECONDS)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=_JWT_REFRESH_TOKEN_EXPIRES_SECONDS // 86400)

    # ============================================================================
    # 会话配置
    # ============================================================================
    SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "3600"))  # 1小时

    # ============================================================================
    # Flask基础配置
    # ============================================================================
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")

    # ============================================================================
    # 数据库配置
    # ============================================================================
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable must be set")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": CONNECTION_TIMEOUT,
        "max_overflow": 10,
        "pool_size": MAX_CONNECTIONS,
        "echo": DEBUG,  # 开发环境显示SQL，生产环境不显示
    }

    # ============================================================================
    # Redis缓存配置
    # ============================================================================
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL")
    if not CACHE_REDIS_URL:
        raise ValueError("CACHE_REDIS_URL environment variable must be set")

    # ============================================================================
    # 安全配置
    # ============================================================================
    BCRYPT_LOG_ROUNDS = PASSWORD_HASH_ROUNDS

    # ============================================================================
    # 文件上传配置
    # ============================================================================
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "userdata/uploads")
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE

    # ============================================================================
    # 外部数据库配置
    # ============================================================================
    SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "localhost")
    SQL_SERVER_PORT = int(os.getenv("SQL_SERVER_PORT", "1433"))
    SQL_SERVER_USERNAME = os.getenv("SQL_SERVER_USERNAME", "sa")
    SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    ORACLE_HOST = os.getenv("ORACLE_HOST", "localhost")
    ORACLE_PORT = int(os.getenv("ORACLE_PORT", "1521"))
    ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "ORCL")
    ORACLE_USERNAME = os.getenv("ORACLE_USERNAME", "system")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")

    # ============================================================================
    # 缓存TTL配置（秒）
    # ============================================================================
    CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", str(7 * 24 * 3600)))  # 7天
    CACHE_RULE_EVALUATION_TTL = int(os.getenv("CACHE_RULE_EVALUATION_TTL", str(24 * 3600)))  # 1天  
    CACHE_RULE_TTL = int(os.getenv("CACHE_RULE_TTL", str(2 * 3600)))  # 2小时
    CACHE_ACCOUNT_TTL = int(os.getenv("CACHE_ACCOUNT_TTL", str(1 * 3600)))  # 1小时

    # ============================================================================
    # 任务配置
    # ============================================================================
    # 数据库大小监控配置
    COLLECT_DB_SIZE_ENABLED = os.getenv("COLLECT_DB_SIZE_ENABLED", "true").lower() == "true"
    
    # 统计聚合配置
    AGGREGATION_ENABLED = os.getenv("AGGREGATION_ENABLED", "true").lower() == "true"
    
    # 数据保留配置
    DATABASE_SIZE_RETENTION_MONTHS = int(os.getenv("DATABASE_SIZE_RETENTION_MONTHS", "12"))  # 默认保留12个月


# 统一配置字典 - 支持开发和生产环境
config = {
    "development": Config,
    "production": Config,
    "default": Config,
}
