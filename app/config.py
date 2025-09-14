"""
泰摸鱼吧 - 应用配置
"""

import os
from datetime import timedelta

from app.constants import DefaultConfig, SystemConstants


class Config:
    """基础配置类"""

    # 基础配置

    SECRET_KEY = os.getenv("SECRET_KEY", DefaultConfig.SECRET_KEY)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DefaultConfig.JWT_SECRET_KEY)
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

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DefaultConfig.DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": SystemConstants.CONNECTION_TIMEOUT,
        "max_overflow": 10,
        "pool_size": SystemConstants.MAX_CONNECTIONS,
        "echo": False,  # 生产环境设为False
    }

    # Redis配置
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.getenv("REDIS_URL", DefaultConfig.REDIS_URL)
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", SystemConstants.DEFAULT_CACHE_TIMEOUT))

    # 安全配置
    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", SystemConstants.PASSWORD_HASH_ROUNDS))

    # 临时禁用CSRF用于测试
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
    APP_NAME = os.getenv("APP_NAME", "泰摸鱼吧")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

    # 监控配置
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "True").lower() == "true"
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 9090))

    # 备份配置
    BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "True").lower() == "true"
    BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", 30))


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://taifish_user:taifish_pass@localhost:5432/taifish_dev",
    )
    CACHE_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://taifish_user:taifish_pass@localhost:5432/taifish_prod",
    )
    CACHE_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 生产环境安全配置
    BCRYPT_LOG_ROUNDS = 15
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)


class TestingConfig(Config):
    """测试环境配置"""

    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://taifish_user:taifish_pass@localhost:5432/taifish_test",
    )
    CACHE_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

    # 测试环境配置
    WTF_CSRF_ENABLED = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


# 配置字典
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
