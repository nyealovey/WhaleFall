"""
泰摸鱼吧 - 模块专用日志记录器
为每个功能模块提供专用的日志记录函数
"""

from typing import Any

from app.utils.context_manager import ContextManager
from app.utils.structlog_config import log_critical, log_error, log_info, log_warning


class ModuleLoggers:
    """模块专用日志记录器"""

    @staticmethod
    def log_auth_info(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录认证信息日志"""
        context = ContextManager.build_business_context("auth", **kwargs)
        log_info(message, module="auth", **context)

    @staticmethod
    def log_auth_error(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录认证错误日志"""
        context = ContextManager.build_business_context("auth", **kwargs)
        log_error(message, module="auth", exception=exception, **context)

    @staticmethod
    def log_auth_warning(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录认证警告日志"""
        context = ContextManager.build_business_context("auth", **kwargs)
        log_warning(message, module="auth", **context)

    @staticmethod
    def log_auth_critical(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录认证严重错误日志"""
        context = ContextManager.build_business_context("auth", **kwargs)
        log_critical(message, module="auth", exception=exception, **context)

    # 实例管理模块
    @staticmethod
    def log_instance_info(message: str, instance_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录实例信息日志"""
        context = ContextManager.build_business_context("instances", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        log_info(message, module="instances", **context)

    @staticmethod
    def log_instance_error(message: str, instance_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录实例错误日志"""
        context = ContextManager.build_business_context("instances", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        log_error(message, module="instances", exception=exception, **context)

    @staticmethod
    def log_instance_warning(message: str, instance_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录实例警告日志"""
        context = ContextManager.build_business_context("instances", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        log_warning(message, module="instances", **context)

    # 凭据管理模块
    @staticmethod
    def log_credential_info(message: str, credential_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录凭据信息日志"""
        context = ContextManager.build_business_context("credentials", **kwargs)
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_info(message, module="credentials", **context)

    @staticmethod
    def log_credential_error(message: str, credential_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录凭据错误日志"""
        context = ContextManager.build_business_context("credentials", **kwargs)
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_error(message, module="credentials", exception=exception, **context)

    @staticmethod
    def log_credential_warning(message: str, credential_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录凭据警告日志"""
        context = ContextManager.build_business_context("credentials", **kwargs)
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_warning(message, module="credentials", **context)

    # 账户管理模块
    @staticmethod
    def log_account_info(message: str, account_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录账户信息日志"""
        context = ContextManager.build_business_context("accounts", **kwargs)
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_info(message, module="accounts", **context)

    @staticmethod
    def log_account_error(message: str, account_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录账户错误日志"""
        context = ContextManager.build_business_context("accounts", **kwargs)
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_error(message, module="accounts", exception=exception, **context)

    @staticmethod
    def log_account_warning(message: str, account_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录账户警告日志"""
        context = ContextManager.build_business_context("accounts", **kwargs)
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_warning(message, module="accounts", **context)

    # 账户同步模块 - 重点模块
    @staticmethod
    def log_sync_info(message: str, instance_data: Any = None, credential_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录同步信息日志"""
        context = ContextManager.build_business_context("account_sync", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_info(message, module="account_sync", **context)

    @staticmethod
    def log_sync_error(
        message: str, instance_data: Any = None, credential_data: Any = None, exception: Exception = None, **kwargs
    ) -> None:
        """记录同步错误日志"""
        context = ContextManager.build_business_context("account_sync", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_error(message, module="account_sync", exception=exception, **context)

    @staticmethod
    def log_sync_warning(message: str, instance_data: Any = None, credential_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录同步警告日志"""
        context = ContextManager.build_business_context("account_sync", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_warning(message, module="account_sync", **context)

    @staticmethod
    def log_sync_critical(
        message: str, instance_data: Any = None, credential_data: Any = None, exception: Exception = None, **kwargs
    ) -> None:
        """记录同步严重错误日志"""
        context = ContextManager.build_business_context("account_sync", **kwargs)
        if instance_data:
            context.update(ContextManager.extract_instance_context(instance_data))
        if credential_data:
            context.update(ContextManager.extract_credential_context(credential_data))
        log_critical(message, module="account_sync", exception=exception, **context)

    # 账户分类模块
    @staticmethod
    def log_classification_info(
        message: str, classification_data: Any = None, rule_data: Any = None, account_data: Any = None, **kwargs
    ) -> None:
        """记录分类信息日志"""
        context = ContextManager.build_business_context("account_classification", **kwargs)
        if classification_data:
            context.update(ContextManager.extract_classification_context(classification_data))
        if rule_data:
            context.update(
                {
                    "rule_id": getattr(rule_data, "id", None),
                    "rule_name": getattr(rule_data, "rule_name", None),
                    "db_type": getattr(rule_data, "db_type", None),
                    "rule_expression": getattr(rule_data, "rule_expression", None),
                    "rule_is_active": getattr(rule_data, "is_active", None),
                }
            )
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_info(message, module="account_classification", **context)

    @staticmethod
    def log_classification_error(
        message: str,
        classification_data: Any = None,
        rule_data: Any = None,
        account_data: Any = None,
        exception: Exception = None,
        **kwargs,
    ) -> None:
        """记录分类错误日志"""
        context = ContextManager.build_business_context("account_classification", **kwargs)
        if classification_data:
            context.update(ContextManager.extract_classification_context(classification_data))
        if rule_data:
            context.update(
                {
                    "rule_id": getattr(rule_data, "id", None),
                    "rule_name": getattr(rule_data, "rule_name", None),
                    "db_type": getattr(rule_data, "db_type", None),
                    "rule_expression": getattr(rule_data, "rule_expression", None),
                    "rule_is_active": getattr(rule_data, "is_active", None),
                }
            )
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_error(message, module="account_classification", exception=exception, **context)

    @staticmethod
    def log_classification_warning(
        message: str, classification_data: Any = None, rule_data: Any = None, account_data: Any = None, **kwargs
    ) -> None:
        """记录分类警告日志"""
        context = ContextManager.build_business_context("account_classification", **kwargs)
        if classification_data:
            context.update(ContextManager.extract_classification_context(classification_data))
        if rule_data:
            context.update(
                {
                    "rule_id": getattr(rule_data, "id", None),
                    "rule_name": getattr(rule_data, "rule_name", None),
                    "db_type": getattr(rule_data, "db_type", None),
                    "rule_expression": getattr(rule_data, "rule_expression", None),
                    "rule_is_active": getattr(rule_data, "is_active", None),
                }
            )
        if account_data:
            context.update(ContextManager.extract_account_context(account_data))
        log_warning(message, module="account_classification", **context)

    # 任务管理模块
    @staticmethod
    def log_task_info(message: str, task_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录任务信息日志"""
        context = ContextManager.build_business_context("tasks", **kwargs)
        if task_data:
            context.update(ContextManager.extract_task_context(task_data))
        log_info(message, module="tasks", **context)

    @staticmethod
    def log_task_error(message: str, task_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录任务错误日志"""
        context = ContextManager.build_business_context("tasks", **kwargs)
        if task_data:
            context.update(ContextManager.extract_task_context(task_data))
        log_error(message, module="tasks", exception=exception, **context)

    @staticmethod
    def log_task_warning(message: str, task_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录任务警告日志"""
        context = ContextManager.build_business_context("tasks", **kwargs)
        if task_data:
            context.update(ContextManager.extract_task_context(task_data))
        log_warning(message, module="tasks", **context)

    @staticmethod
    def log_task_critical(message: str, task_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录任务严重错误日志"""
        context = ContextManager.build_business_context("tasks", **kwargs)
        if task_data:
            context.update(ContextManager.extract_task_context(task_data))
        log_critical(message, module="tasks", exception=exception, **context)

    # 同步会话模块
    @staticmethod
    def log_sync_session_info(message: str, session_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录同步会话信息日志"""
        context = ContextManager.build_business_context("sync_sessions", **kwargs)
        if session_data:
            context.update(ContextManager.extract_sync_session_context(session_data))
        log_info(message, module="sync_sessions", **context)

    @staticmethod
    def log_sync_session_error(message: str, session_data: Any = None, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录同步会话错误日志"""
        context = ContextManager.build_business_context("sync_sessions", **kwargs)
        if session_data:
            context.update(ContextManager.extract_sync_session_context(session_data))
        log_error(message, module="sync_sessions", exception=exception, **context)

    @staticmethod
    def log_sync_session_warning(message: str, session_data: Any = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录同步会话警告日志"""
        context = ContextManager.build_business_context("sync_sessions", **kwargs)
        if session_data:
            context.update(ContextManager.extract_sync_session_context(session_data))
        log_warning(message, module="sync_sessions", **context)

    # 系统管理模块
    @staticmethod
    def log_admin_info(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录系统管理信息日志"""
        context = ContextManager.build_business_context("admin", **kwargs)
        log_info(message, module="admin", **context)

    @staticmethod
    def log_admin_error(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录系统管理错误日志"""
        context = ContextManager.build_business_context("admin", **kwargs)
        log_error(message, module="admin", exception=exception, **context)

    @staticmethod
    def log_admin_warning(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录系统管理警告日志"""
        context = ContextManager.build_business_context("admin", **kwargs)
        log_warning(message, module="admin", **context)

    @staticmethod
    def log_admin_critical(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录系统管理严重错误日志"""
        context = ContextManager.build_business_context("admin", **kwargs)
        log_critical(message, module="admin", exception=exception, **context)

    # 日志管理模块
    @staticmethod
    def log_logs_info(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录日志管理信息日志"""
        context = ContextManager.build_business_context("unified_logs", **kwargs)
        log_info(message, module="unified_logs", **context)

    @staticmethod
    def log_logs_error(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录日志管理错误日志"""
        context = ContextManager.build_business_context("unified_logs", **kwargs)
        log_error(message, module="unified_logs", exception=exception, **context)

    @staticmethod
    def log_logs_warning(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录日志管理警告日志"""
        context = ContextManager.build_business_context("unified_logs", **kwargs)
        log_warning(message, module="unified_logs", **context)

    # 健康监控模块
    @staticmethod
    def log_health_info(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录健康监控信息日志"""
        context = ContextManager.build_business_context("health", **kwargs)
        log_info(message, module="health", **context)

    @staticmethod
    def log_health_error(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录健康监控错误日志"""
        context = ContextManager.build_business_context("health", **kwargs)
        log_error(message, module="health", exception=exception, **context)

    @staticmethod
    def log_health_warning(message: str, **kwargs: Any) -> None:  # noqa: ANN401
        """记录健康监控警告日志"""
        log_warning(message, module="health", **kwargs)

    @staticmethod
    def log_health_critical(message: str, exception: Exception = None, **kwargs: Any) -> None:  # noqa: ANN401
        """记录健康监控严重错误日志"""
        context = ContextManager.build_business_context("health", **kwargs)
        log_critical(message, module="health", exception=exception, **context)


# 创建全局实例
module_loggers = ModuleLoggers()
