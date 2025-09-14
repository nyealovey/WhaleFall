"""
泰摸鱼吧 - 高级错误处理系统
提供更精细的错误分类、处理和恢复机制
"""

import logging
import traceback
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app import db
from app.constants import ErrorMessages, LogLevel
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class ErrorCategory:
    """错误分类"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity:
    """错误严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext:
    """错误上下文信息"""

    def __init__(self, error: Exception, request_data: dict[str, Any] | None = None) -> None:
        self.error_id = str(uuid.uuid4())
        self.timestamp = now()
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.stack_trace = traceback.format_exc()
        self.request_data = request_data or {}
        self.user_id = getattr(request, "user_id", None)
        self.ip_address = request.remote_addr if request else None
        self.user_agent = request.headers.get("User-Agent") if request else None
        self.endpoint = request.endpoint if request else None
        self.method = request.method if request else None
        self.url = request.url if request else None


class AdvancedErrorHandler:
    """高级错误处理器"""

    def __init__(self) -> None:
        self.error_handlers = {}
        self.recovery_strategies = {}
        self.error_metrics = {}
        self._register_default_handlers()

    def register_error_handler(self, error_type: type, handler: Callable) -> None:
        """注册错误处理器"""
        self.error_handlers[error_type] = handler

    def register_recovery_strategy(self, error_category: str, strategy: Callable) -> None:
        """注册恢复策略"""
        self.recovery_strategies[error_category] = strategy

    def handle_error(self, error: Exception, context: ErrorContext = None) -> dict[str, Any]:
        """处理错误"""
        if context is None:
            context = ErrorContext(error)

        # 记录错误
        self._log_error(error, context)

        # 更新错误指标
        self._update_error_metrics(error, context)

        # 尝试恢复
        recovery_result = self._attempt_recovery(error, context)

        # 生成错误响应
        return self._generate_error_response(error, context, recovery_result)

    def _register_default_handlers(self) -> None:
        """注册默认错误处理器"""
        # 数据库错误处理器
        self.register_error_handler(IntegrityError, self._handle_integrity_error)
        self.register_error_handler(OperationalError, self._handle_operational_error)
        self.register_error_handler(SQLAlchemyError, self._handle_sqlalchemy_error)

        # HTTP错误处理器
        self.register_error_handler(HTTPException, self._handle_http_exception)

        # 通用错误处理器
        self.register_error_handler(Exception, self._handle_generic_error)

    def _handle_integrity_error(self, error: IntegrityError, context: ErrorContext) -> dict[str, Any]:
        """处理完整性错误"""
        error_message = str(error.orig) if hasattr(error, "orig") else str(error)

        if "UNIQUE constraint failed" in error_message:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "message": "数据已存在，请检查唯一性约束",
                "user_message": "该数据已存在，请使用不同的值",
                "recoverable": True,
                "suggestions": ["检查数据是否重复", "使用不同的唯一标识符"],
            }
        if "FOREIGN KEY constraint failed" in error_message:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "message": "外键约束失败",
                "user_message": "相关数据不存在，请检查关联关系",
                "recoverable": True,
                "suggestions": ["检查关联数据是否存在", "先创建关联数据"],
            }
        return {
            "category": ErrorCategory.DATABASE,
            "severity": ErrorSeverity.HIGH,
            "message": "数据完整性错误",
            "user_message": ErrorMessages.CONSTRAINT_VIOLATION,
            "recoverable": False,
            "suggestions": ["检查数据格式", "联系管理员"],
        }

    def _handle_operational_error(self, error: OperationalError, context: ErrorContext) -> dict[str, Any]:
        """处理操作错误"""
        error_message = str(error.orig) if hasattr(error, "orig") else str(error)

        if "connection" in error_message.lower():
            return {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "message": "数据库连接错误",
                "user_message": ErrorMessages.DATABASE_CONNECTION_ERROR,
                "recoverable": True,
                "suggestions": ["检查数据库连接", "稍后重试"],
            }
        if "timeout" in error_message.lower():
            return {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.MEDIUM,
                "message": "数据库操作超时",
                "user_message": ErrorMessages.DATABASE_TIMEOUT,
                "recoverable": True,
                "suggestions": ["稍后重试", "检查查询复杂度"],
            }
        return {
            "category": ErrorCategory.DATABASE,
            "severity": ErrorSeverity.HIGH,
            "message": "数据库操作错误",
            "user_message": ErrorMessages.DATABASE_QUERY_ERROR,
            "recoverable": False,
            "suggestions": ["检查SQL语句", "联系管理员"],
        }

    def _handle_sqlalchemy_error(self, error: SQLAlchemyError, context: ErrorContext) -> dict[str, Any]:
        """处理SQLAlchemy错误"""
        return {
            "category": ErrorCategory.DATABASE,
            "severity": ErrorSeverity.HIGH,
            "message": "数据库操作错误",
            "user_message": ErrorMessages.DATABASE_QUERY_ERROR,
            "recoverable": False,
            "suggestions": ["检查数据库状态", "联系管理员"],
        }

    def _handle_http_exception(self, error: HTTPException, context: ErrorContext) -> dict[str, Any]:
        """处理HTTP异常"""
        status_code = error.code

        if status_code == 400:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "message": "请求参数错误",
                "user_message": ErrorMessages.INVALID_REQUEST,
                "recoverable": True,
                "suggestions": ["检查请求参数", "查看API文档"],
            }
        if status_code == 401:
            return {
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "message": "未授权访问",
                "user_message": ErrorMessages.INVALID_CREDENTIALS,
                "recoverable": True,
                "suggestions": ["重新登录", "检查认证信息"],
            }
        if status_code == 403:
            return {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "message": "权限不足",
                "user_message": ErrorMessages.PERMISSION_DENIED,
                "recoverable": False,
                "suggestions": ["联系管理员", "检查权限设置"],
            }
        if status_code == 404:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "message": "资源不存在",
                "user_message": ErrorMessages.RESOURCE_NOT_FOUND,
                "recoverable": True,
                "suggestions": ["检查URL", "查看资源列表"],
            }
        return {
            "category": ErrorCategory.SYSTEM,
            "severity": ErrorSeverity.MEDIUM,
            "message": f"HTTP错误 {status_code}",
            "user_message": ErrorMessages.INTERNAL_ERROR,
            "recoverable": False,
            "suggestions": ["稍后重试", "联系管理员"],
        }

    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> dict[str, Any]:
        """处理通用错误"""
        return {
            "category": ErrorCategory.UNKNOWN,
            "severity": ErrorSeverity.HIGH,
            "message": "未知错误",
            "user_message": ErrorMessages.INTERNAL_ERROR,
            "recoverable": False,
            "suggestions": ["联系管理员", "查看错误日志"],
        }

    def _log_error(self, error: Exception, context: ErrorContext) -> None:
        """记录错误日志"""
        log_level = self._get_log_level(context)

        log_data = {
            "error_id": context.error_id,
            "error_type": context.error_type,
            "error_message": context.error_message,
            "user_id": context.user_id,
            "ip_address": context.ip_address,
            "endpoint": context.endpoint,
            "method": context.method,
            "url": context.url,
            "stack_trace": context.stack_trace,
            "timestamp": context.timestamp.isoformat(),
        }

        if log_level == LogLevel.CRITICAL:
            logger.critical(f"严重错误: {context.error_id}", extra=log_data)
        elif log_level == LogLevel.ERROR:
            logger.error(f"错误: {context.error_id}", extra=log_data)
        elif log_level == LogLevel.WARNING:
            logger.warning(f"警告: {context.error_id}", extra=log_data)
        else:
            logger.info(f"信息: {context.error_id}", extra=log_data)

    def _get_log_level(self, context: ErrorContext) -> str:
        """根据错误类型确定日志级别"""
        error_type = context.error_type

        if error_type in ["IntegrityError", "OperationalError"]:
            return LogLevel.ERROR
        if error_type in ["HTTPException"]:
            return LogLevel.WARNING
        return LogLevel.ERROR

    def _update_error_metrics(self, error: Exception, context: ErrorContext) -> None:
        """更新错误指标"""
        error_type = context.error_type
        endpoint = context.endpoint or "unknown"

        if error_type not in self.error_metrics:
            self.error_metrics[error_type] = {}

        if endpoint not in self.error_metrics[error_type]:
            self.error_metrics[error_type][endpoint] = {
                "count": 0,
                "last_occurrence": None,
                "first_occurrence": None,
            }

        metrics = self.error_metrics[error_type][endpoint]
        metrics["count"] += 1
        metrics["last_occurrence"] = context.timestamp

        if metrics["first_occurrence"] is None:
            metrics["first_occurrence"] = context.timestamp

    def _attempt_recovery(self, error: Exception, context: ErrorContext) -> dict[str, Any]:
        """尝试错误恢复"""
        error_info = self._get_error_info(error, context)

        if not error_info.get("recoverable", False):
            return {"success": False, "message": "错误不可恢复"}

        category = error_info.get("category", ErrorCategory.UNKNOWN)

        if category in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[category]
                result = strategy(error, context)
                return {"success": True, "result": result}
            except Exception as recovery_error:
                logger.error(f"恢复策略执行失败: {recovery_error}")
                return {"success": False, "message": "恢复策略执行失败"}

        return {"success": False, "message": "无可用恢复策略"}

    def _get_error_info(self, error: Exception, context: ErrorContext) -> dict[str, Any]:
        """获取错误信息"""
        error_type = type(error)

        if error_type in self.error_handlers:
            handler = self.error_handlers[error_type]
            return handler(error, context)
        return self._handle_generic_error(error, context)

    def _generate_error_response(
        self, error: Exception, context: ErrorContext, recovery_result: dict[str, Any]
    ) -> dict[str, Any]:
        """生成错误响应"""
        error_info = self._get_error_info(error, context)

        response = {
            "error": True,
            "error_id": context.error_id,
            "message": error_info.get("user_message", ErrorMessages.INTERNAL_ERROR),
            "category": error_info.get("category", ErrorCategory.UNKNOWN),
            "severity": error_info.get("severity", ErrorSeverity.HIGH),
            "timestamp": context.timestamp.isoformat(),
            "recoverable": error_info.get("recoverable", False),
            "suggestions": error_info.get("suggestions", []),
        }

        if recovery_result.get("success"):
            response["recovery"] = recovery_result.get("result")

        # 开发环境包含更多调试信息
        if current_app.debug:
            response["debug"] = {
                "error_type": context.error_type,
                "error_message": context.error_message,
                "stack_trace": context.stack_trace,
                "request_data": context.request_data,
            }

        return response

    def get_error_metrics(self) -> dict[str, Any]:
        """获取错误指标"""
        return self.error_metrics

    def clear_error_metrics(self) -> None:
        """清除错误指标"""
        self.error_metrics.clear()


# 全局错误处理器实例
advanced_error_handler = AdvancedErrorHandler()


# 错误处理装饰器
def handle_advanced_errors(func: Callable) -> Callable:
    """高级错误处理装饰器"""

    @wraps(func)
    def wrapper(*args: "Any", **kwargs: "Any") -> "Any":
        try:
            return func(*args, **kwargs)
        except Exception as error:
            context = ErrorContext(error)
            error_response = advanced_error_handler.handle_error(error, context)

            # 根据错误严重程度决定是否返回错误响应
            if error_response.get("severity") in [
                ErrorSeverity.CRITICAL,
                ErrorSeverity.HIGH,
            ]:
                return jsonify(error_response), 500
            if error_response.get("severity") == ErrorSeverity.MEDIUM:
                return jsonify(error_response), 400
            return jsonify(error_response), 200

    return wrapper


# 恢复策略
def database_recovery_strategy(error: Exception, context: ErrorContext) -> dict[str, Any]:
    """数据库恢复策略"""
    try:
        # 尝试重新连接数据库
        db.session.rollback()
        db.session.execute("SELECT 1")
        return {"action": "database_reconnected", "success": True}
    except Exception as e:
        return {
            "action": "database_reconnection_failed",
            "success": False,
            "error": str(e),
        }


def validation_recovery_strategy(error: Exception, context: ErrorContext) -> dict[str, Any]:
    """验证恢复策略"""
    return {"action": "validation_retry", "success": True, "message": "请检查输入数据"}


# 注册恢复策略
advanced_error_handler.register_recovery_strategy(ErrorCategory.DATABASE, database_recovery_strategy)
advanced_error_handler.register_recovery_strategy(ErrorCategory.VALIDATION, validation_recovery_strategy)


# 错误监控装饰器
def monitor_errors(func: Callable) -> Callable:
    """错误监控装饰器"""

    @wraps(func)
    def wrapper(*args: "Any", **kwargs: "Any") -> "Any":
        try:
            return func(*args, **kwargs)
        except Exception as error:
            context = ErrorContext(error)
            advanced_error_handler.handle_error(error, context)
            raise

    return wrapper
