"""
鲸落 - 统一配置管理
支持开发和生产环境，通过环境变量控制
"""

import os
from datetime import timedelta


class Config:
    """统一配置类 - 支持开发和生产环境
    
    所有配置项优先从环境变量读取，如果环境变量不存在则使用默认值。
    """

    # ============================================================================
    # 分页配置
    # ============================================================================
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
    MIN_PAGE_SIZE = int(os.getenv("MIN_PAGE_SIZE", "1"))

    # ============================================================================
    # 密码配置
    # ============================================================================
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_PASSWORD_LENGTH = int(os.getenv("MAX_PASSWORD_LENGTH", "128"))
    PASSWORD_HASH_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))

    # ============================================================================
    # 缓存配置（秒）
    # ============================================================================
    DEFAULT_CACHE_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))  # 5分钟
    LONG_CACHE_TIMEOUT = int(os.getenv("LONG_CACHE_TIMEOUT", "3600"))  # 1小时
    SHORT_CACHE_TIMEOUT = int(os.getenv("SHORT_CACHE_TIMEOUT", "60"))  # 1分钟

    # ============================================================================
    # 文件上传配置
    # ============================================================================
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(16 * 1024 * 1024)))  # 16MB
    ALLOWED_EXTENSIONS = {".txt", ".csv", ".json", ".sql", ".py"}  # 暂不支持环境变量配置

    # ============================================================================
    # 数据库连接配置
    # ============================================================================
    CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
    QUERY_TIMEOUT = int(os.getenv("DB_QUERY_TIMEOUT", "60"))
    MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "20"))
    CONNECTION_RETRY_ATTEMPTS = int(os.getenv("DB_CONNECTION_RETRY_ATTEMPTS", "3"))

    # ============================================================================
    # 速率限制配置
    # ============================================================================
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "300"))  # 5分钟
    LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))  # 每窗口最多尝试次数
    LOGIN_RATE_WINDOW = int(os.getenv("LOGIN_RATE_WINDOW", "60"))  # 1分钟

    # ============================================================================
    # 日志配置
    # ============================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "userdata/logs/app.log")
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    # ============================================================================
    # JWT配置（秒）
    # ============================================================================
    JWT_ACCESS_TOKEN_EXPIRES_SECONDS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))  # 1小时
    JWT_REFRESH_TOKEN_EXPIRES_SECONDS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_SECONDS", "2592000"))  # 30天

    # ============================================================================
    # 会话配置（秒）
    # ============================================================================
    SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "3600"))  # 1小时
    REMEMBER_ME_LIFETIME = int(os.getenv("REMEMBER_ME_LIFETIME", "2592000"))  # 30天

    # ============================================================================
    # 重试配置
    # ============================================================================
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
    RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "60.0"))

    # ============================================================================
    # 性能配置
    # ============================================================================
    SLOW_QUERY_THRESHOLD = float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))  # 1秒
    SLOW_API_THRESHOLD = float(os.getenv("SLOW_API_THRESHOLD", "2.0"))  # 2秒
    MEMORY_WARNING_THRESHOLD = int(os.getenv("MEMORY_WARNING_THRESHOLD", "80"))  # 80%
    CPU_WARNING_THRESHOLD = int(os.getenv("CPU_WARNING_THRESHOLD", "80"))  # 80%

    # ============================================================================
    # 安全配置（秒）
    # ============================================================================
    CSRF_TOKEN_LIFETIME = int(os.getenv("CSRF_TOKEN_LIFETIME", "3600"))
    PASSWORD_RESET_TOKEN_LIFETIME = int(os.getenv("PASSWORD_RESET_TOKEN_LIFETIME", "1800"))  # 30分钟
    EMAIL_VERIFICATION_TOKEN_LIFETIME = int(os.getenv("EMAIL_VERIFICATION_TOKEN_LIFETIME", "3600"))  # 1小时

    # ============================================================================
    # 监控配置（秒）
    # ============================================================================
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # 30秒
    METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "60"))  # 1分钟
    ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "300"))  # 5分钟

    # ============================================================================
    # Flask基础配置
    # ============================================================================

    # 基础配置
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES_SECONDS)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=JWT_REFRESH_TOKEN_EXPIRES_SECONDS // 86400)

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

    # 外部数据库配置
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

    # 应用配置
    APP_VERSION = os.getenv("APP_VERSION", "1.1.4")

    # 数据库大小监控配置
    COLLECT_DB_SIZE_ENABLED = os.getenv("COLLECT_DB_SIZE_ENABLED", "true").lower() == "true"
    
    # 统计聚合配置
    AGGREGATION_ENABLED = os.getenv("AGGREGATION_ENABLED", "true").lower() == "true"
    
    # 分区管理配置
    PARTITION_CLEANUP_ENABLED = os.getenv("PARTITION_CLEANUP_ENABLED", "true").lower() == "true"
    
    # 数据保留配置
    DATABASE_SIZE_RETENTION_DAYS = int(os.getenv("DATABASE_SIZE_RETENTION_DAYS", "365"))  # 默认保留一年
    DATABASE_SIZE_RETENTION_MONTHS = int(os.getenv("DATABASE_SIZE_RETENTION_MONTHS", "12"))  # 默认保留12个月


# 统一配置字典 - 支持开发和生产环境
config = {
    "development": Config,
    "production": Config,
    "default": Config,
}
