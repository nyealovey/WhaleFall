"""
鲸落 - 日志配置管理
统一管理所有日志相关配置
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogType(Enum):
    """日志类型枚举"""

    APP = "app"
    ERROR = "error"
    ACCESS = "access"
    SECURITY = "security"
    DATABASE = "database"
    TASK = "task"
    STRUCTURED = "structured"


@dataclass
class LogConfig:
    """日志配置类"""

    # 基础配置
    app_name: str = "whalefall"
    log_dir: str = "userdata/logs"
    level: LogLevel = LogLevel.INFO

    # 文件配置
    max_file_size: str = "10 MB"
    retention_days: int = 30
    compression: str = "zip"

    # 性能配置
    enqueue: bool = True  # 异步写入
    backtrace: bool = True
    diagnose: bool = True

    # 格式配置
    console_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    file_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"

    # 各类型日志配置
    log_types: dict[LogType, dict[str, Any]] = None

    def __post_init__(self):
        if self.log_types is None:
            self.log_types = {
                LogType.APP: {
                    "rotation": "10 MB",
                    "retention": "30 days",
                    "level": "INFO",
                    "enqueue": True,
                },
                LogType.ERROR: {
                    "rotation": "5 MB",
                    "retention": "60 days",
                    "level": "ERROR",
                    "enqueue": True,
                },
                LogType.ACCESS: {
                    "rotation": "50 MB",
                    "retention": "7 days",
                    "level": "INFO",
                    "enqueue": True,
                },
                LogType.SECURITY: {
                    "rotation": "5 MB",
                    "retention": "90 days",
                    "level": "INFO",
                    "enqueue": True,
                },
                LogType.DATABASE: {
                    "rotation": "20 MB",
                    "retention": "14 days",
                    "level": "INFO",
                    "enqueue": True,
                },
                LogType.TASK: {
                    "rotation": "10 MB",
                    "retention": "30 days",
                    "level": "INFO",
                    "enqueue": True,
                },
                LogType.STRUCTURED: {
                    "rotation": "10 MB",
                    "retention": "7 days",
                    "level": "INFO",
                    "enqueue": True,
                    "serialize": True,
                },
            }


class LoggingConfigManager:
    """日志配置管理器"""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> LogConfig:
        """从环境变量加载配置"""
        return LogConfig(
            app_name=os.getenv("LOG_APP_NAME", "whalefall"),
            log_dir=os.getenv("LOG_DIR", "userdata/logs"),
            level=LogLevel(os.getenv("LOG_LEVEL", "INFO")),
            max_file_size=os.getenv("LOG_MAX_FILE_SIZE", "10 MB"),
            retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30")),
            compression=os.getenv("LOG_COMPRESSION", "zip"),
            enqueue=os.getenv("LOG_ENQUEUE", "true").lower() == "true",
            backtrace=os.getenv("LOG_BACKTRACE", "true").lower() == "true",
            diagnose=os.getenv("LOG_DIAGNOSE", "true").lower() == "true",
        )

    def get_log_file_path(self, log_type: LogType) -> Path:
        """获取日志文件路径"""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        file_mapping = {
            LogType.APP: "app.log",
            LogType.ERROR: "error.log",
            LogType.ACCESS: "access.log",
            LogType.SECURITY: "security.log",
            LogType.DATABASE: "database.log",
            LogType.TASK: "tasks.log",
            LogType.STRUCTURED: "structured.log",
        }

        return log_dir / file_mapping[log_type]

    def get_log_config(self, log_type: LogType) -> dict[str, Any]:
        """获取指定类型的日志配置"""
        base_config = {
            "format": self.config.file_format,
            "level": self.config.level.value,
            "enqueue": self.config.enqueue,
            "backtrace": self.config.backtrace,
            "diagnose": self.config.diagnose,
        }

        type_config = self.config.log_types.get(log_type, {})
        base_config.update(type_config)

        return base_config

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return os.getenv("FLASK_ENV", "production") == "development"

    def is_debug(self) -> bool:
        """判断是否为调试模式"""
        return os.getenv("FLASK_DEBUG", "false").lower() == "true"

    def get_console_level(self) -> str:
        """获取控制台日志级别"""
        if self.is_debug():
            return "DEBUG"
        if self.is_development():
            return "INFO"
        return "WARNING"

    def should_log_to_console(self) -> bool:
        """是否应该输出到控制台"""
        return self.is_development() or self.is_debug()

    def get_retention_policy(self) -> dict[str, str]:
        """获取日志保留策略"""
        return {
            "app": f"{self.config.retention_days} days",
            "error": f"{self.config.retention_days * 2} days",
            "access": "7 days",
            "security": f"{self.config.retention_days * 3} days",
            "database": f"{self.config.retention_days // 2} days",
            "task": f"{self.config.retention_days} days",
            "structured": "7 days",
        }


# 全局配置管理器实例
config_manager = LoggingConfigManager()


def get_logging_config() -> LogConfig:
    """获取日志配置"""
    return config_manager.config


def get_log_file_path(log_type: LogType) -> Path:
    """获取日志文件路径"""
    return config_manager.get_log_file_path(log_type)


def get_log_config(log_type: LogType) -> dict[str, Any]:
    """获取日志配置"""
    return config_manager.get_log_config(log_type)


def is_development() -> bool:
    """判断是否为开发环境"""
    return config_manager.is_development()


def is_debug() -> bool:
    """判断是否为调试模式"""
    return config_manager.is_debug()
