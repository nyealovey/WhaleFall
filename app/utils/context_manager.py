"""
泰摸鱼吧 - 上下文管理器
统一管理各功能模块的日志上下文信息
"""

from datetime import datetime
from typing import Any, Dict, Optional

from flask import g, has_request_context
from flask_login import current_user

from app.utils.timezone import now


class ContextManager:
    """上下文管理器 - 统一管理各模块的日志上下文"""
    
    # 各模块的上下文字段定义
    MODULE_CONTEXT_FIELDS = {
        "auth": {
            "user_id": int,
            "username": str,
            "role": str,
            "is_active": bool,
            "last_login": datetime,
            "auth_method": str,
            "session_id": str,
            "login_time": datetime,
            "ip_address": str,
            "user_agent": str,
            "login_attempts": int,
        },
        "instances": {
            "instance_id": int,
            "instance_name": str,
            "db_type": str,
            "host": str,
            "port": int,
            "database_name": str,
            "database_version": str,
            "environment": str,
            "status": str,
            "is_active": bool,
            "credential_id": int,
            "credential_name": str,
            "description": str,
            "tags": list,
            "last_connected": datetime,
            "connection_status": str,
            "connection_error": str,
            "sync_count": int,
            "created_at": datetime,
            "updated_at": datetime,
        },
        "credentials": {
            "credential_id": int,
            "credential_name": str,
            "credential_type": str,
            "db_type": str,
            "username": str,
            "is_active": bool,
            "instance_ids": list,
            "category_id": int,
            "description": str,
            "password_encrypted": bool,
            "password_masked": str,
            "created_at": datetime,
            "updated_at": datetime,
        },
        "accounts": {
            "account_id": int,
            "username": str,
            "db_type": str,
            "instance_id": int,
            "instance_name": str,
            "is_superuser": bool,
            "global_privileges": list,
            "database_privileges": list,
            "predefined_roles": list,
            "role_attributes": list,
            "server_roles": list,
            "server_permissions": list,
            "oracle_roles": list,
            "system_privileges": list,
            "is_deleted": bool,
            "last_sync_time": datetime,
            "last_change_type": str,
            "last_change_time": datetime,
            "deleted_time": datetime,
        },
        "account_sync": {
            "sync_id": int,
            "sync_type": str,
            "sync_status": str,
            "sync_mode": str,
            "instance_id": int,
            "instance_name": str,
            "db_type": str,
            "host": str,
            "port": int,
            "database_name": str,
            "environment": str,
            "status": str,
            "credential_id": int,
            "credential_name": str,
            "credential_type": str,
            "username": str,
            "total_accounts": int,
            "synced_accounts": int,
            "failed_accounts": int,
            "new_accounts": int,
            "updated_accounts": int,
            "deleted_accounts": int,
            "permissions_synced": int,
            "permissions_failed": int,
            "roles_synced": int,
            "roles_failed": int,
            "start_time": datetime,
            "end_time": datetime,
            "duration": int,
            "last_sync": datetime,
            "error_count": int,
            "error_messages": list,
            "last_error": str,
            "retry_count": int,
        },
        "account_classification": {
            "classification_id": int,
            "classification_name": str,
            "risk_level": str,
            "color": str,
            "priority": int,
            "is_system": bool,
            "is_active": bool,
            "rule_id": int,
            "rule_name": str,
            "db_type": str,
            "rule_expression": dict,
            "rule_is_active": bool,
            "account_id": int,
            "account_username": str,
            "instance_id": int,
            "instance_name": str,
            "classification_result": str,
            "confidence_score": float,
            "matched_permissions": list,
            "matched_roles": list,
            "classification_reason": str,
            "classified_at": datetime,
            "rule_created_at": datetime,
            "rule_updated_at": datetime,
            "classification_created_at": datetime,
        },
        "tasks": {
            "task_id": int,
            "task_name": str,
            "task_type": str,
            "db_type": str,
            "schedule": str,
            "description": str,
            "is_active": bool,
            "is_builtin": bool,
            "last_run": datetime,
            "last_status": str,
            "last_message": str,
            "run_count": int,
            "success_count": int,
            "success_rate": float,
            "config": dict,
            "python_code": str,
            "target_instances": list,
            "target_database_types": list,
            "created_at": datetime,
            "updated_at": datetime,
            "next_run": datetime,
        },
        "sync_sessions": {
            "session_id": str,
            "sync_type": str,
            "sync_category": str,
            "status": str,
            "created_by": int,
            "started_at": datetime,
            "completed_at": datetime,
            "created_at": datetime,
            "updated_at": datetime,
            "total_instances": int,
            "successful_instances": int,
            "failed_instances": int,
            "progress_percentage": float,
            "target_instances": list,
            "target_database_types": list,
            "duration": int,
            "records_per_second": float,
            "instances_per_minute": float,
        },
        "admin": {
            "operation_type": str,
            "operation_name": str,
            "admin_user_id": int,
            "admin_username": str,
            "admin_role": str,
            "config_key": str,
            "config_value": str,
            "config_category": str,
            "old_value": str,
            "new_value": str,
            "target_user_id": int,
            "target_username": str,
            "target_role": str,
            "target_is_active": bool,
            "system_status": str,
            "memory_usage": int,
            "cpu_usage": float,
            "disk_usage": float,
            "active_connections": int,
            "cleanup_type": str,
            "cleanup_target": str,
            "records_cleaned": int,
            "space_freed": int,
        },
        "unified_logs": {
            "query_type": str,
            "query_params": dict,
            "search_term": str,
            "filters": dict,
            "export_format": str,
            "export_size": int,
            "export_path": str,
            "export_status": str,
            "total_logs": int,
            "error_logs": int,
            "warning_logs": int,
            "info_logs": int,
            "time_range": str,
            "query_duration": float,
            "result_count": int,
            "memory_usage": int,
        },
        "health": {
            "check_type": str,
            "check_name": str,
            "check_status": str,
            "system_status": str,
            "uptime": int,
            "memory_usage": float,
            "cpu_usage": float,
            "disk_usage": float,
            "load_average": list,
            "database_status": str,
            "active_instances": int,
            "total_instances": int,
            "instance_errors": int,
            "service_status": str,
            "response_time": float,
            "error_rate": float,
            "throughput": float,
            "alert_level": str,
            "alert_message": str,
            "alert_count": int,
            "last_alert": datetime,
        }
    }
    
    @staticmethod
    def build_base_context() -> Dict[str, Any]:
        """构建基础上下文"""
        context = {
            "timestamp": now(),
        }
        
        # 添加请求上下文
        if has_request_context():
            context.update({
                "request_id": getattr(g, "request_id", None),
                "ip_address": getattr(g, "ip_address", None),
                "user_agent": getattr(g, "user_agent", None),
                "url": getattr(g, "url", None),
                "method": getattr(g, "method", None),
            })
        
        # 添加用户上下文
        if current_user and hasattr(current_user, "id"):
            context.update({
                "user_id": current_user.id,
                "username": getattr(current_user, "username", None),
                "role": getattr(current_user, "role", None),
                "is_admin": getattr(current_user, "is_admin", lambda: False)(),
            })
        
        return context
    
    @staticmethod
    def build_business_context(module: str, **kwargs) -> Dict[str, Any]:
        """根据模块构建业务上下文"""
        base_context = ContextManager.build_base_context()
        
        # 获取模块的上下文字段定义
        module_fields = ContextManager.MODULE_CONTEXT_FIELDS.get(module, {})
        
        # 过滤和验证传入的参数
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if key in module_fields:
                # 类型验证（简单验证）
                expected_type = module_fields[key]
                if expected_type in [int, str, bool, float, list, dict, datetime]:
                    if value is not None:
                        filtered_kwargs[key] = value
                else:
                    filtered_kwargs[key] = value
        
        return {**base_context, **filtered_kwargs}
    
    @staticmethod
    def extract_instance_context(instance_data: Any) -> Dict[str, Any]:
        """从实例数据中提取上下文"""
        if hasattr(instance_data, 'to_dict'):
            data = instance_data.to_dict()
        elif isinstance(instance_data, dict):
            data = instance_data
        else:
            return {}
        
        return {
            "instance_id": data.get("id"),
            "instance_name": data.get("name"),
            "db_type": data.get("db_type"),
            "host": data.get("host"),
            "port": data.get("port"),
            "database_name": data.get("database_name"),
            "database_version": data.get("database_version"),
            "environment": data.get("environment"),
            "status": data.get("status"),
            "is_active": data.get("is_active"),
            "credential_id": data.get("credential_id"),
            "description": data.get("description"),
            "tags": data.get("tags"),
            "sync_count": data.get("sync_count"),
        }
    
    @staticmethod
    def extract_credential_context(credential_data: Any) -> Dict[str, Any]:
        """从凭据数据中提取上下文"""
        if hasattr(credential_data, 'to_dict'):
            data = credential_data.to_dict()
        elif isinstance(credential_data, dict):
            data = credential_data
        else:
            return {}
        
        return {
            "credential_id": data.get("id"),
            "credential_name": data.get("name"),
            "credential_type": data.get("credential_type"),
            "db_type": data.get("db_type"),
            "username": data.get("username"),
            "is_active": data.get("is_active"),
            "instance_ids": data.get("instance_ids"),
            "category_id": data.get("category_id"),
            "description": data.get("description"),
        }
    
    @staticmethod
    def extract_account_context(account_data: Any) -> Dict[str, Any]:
        """从账户数据中提取上下文"""
        if hasattr(account_data, 'to_dict'):
            data = account_data.to_dict()
        elif isinstance(account_data, dict):
            data = account_data
        else:
            return {}
        
        return {
            "account_id": data.get("id"),
            "username": data.get("username"),
            "db_type": data.get("db_type"),
            "instance_id": data.get("instance_id"),
            "is_superuser": data.get("is_superuser"),
            "global_privileges": data.get("global_privileges"),
            "database_privileges": data.get("database_privileges"),
            "predefined_roles": data.get("predefined_roles"),
            "role_attributes": data.get("role_attributes"),
            "server_roles": data.get("server_roles"),
            "server_permissions": data.get("server_permissions"),
            "oracle_roles": data.get("oracle_roles"),
            "system_privileges": data.get("system_privileges"),
            "is_deleted": data.get("is_deleted"),
            "last_sync_time": data.get("last_sync_time"),
            "last_change_type": data.get("last_change_type"),
            "last_change_time": data.get("last_change_time"),
        }
    
    @staticmethod
    def extract_classification_context(classification_data: Any) -> Dict[str, Any]:
        """从分类数据中提取上下文"""
        if hasattr(classification_data, 'to_dict'):
            data = classification_data.to_dict()
        elif isinstance(classification_data, dict):
            data = classification_data
        else:
            return {}
        
        return {
            "classification_id": data.get("id"),
            "classification_name": data.get("name"),
            "risk_level": data.get("risk_level"),
            "color": data.get("color"),
            "priority": data.get("priority"),
            "is_system": data.get("is_system"),
            "is_active": data.get("is_active"),
        }
    
    @staticmethod
    def extract_task_context(task_data: Any) -> Dict[str, Any]:
        """从任务数据中提取上下文"""
        if hasattr(task_data, 'to_dict'):
            data = task_data.to_dict()
        elif isinstance(task_data, dict):
            data = task_data
        else:
            return {}
        
        return {
            "task_id": data.get("id"),
            "task_name": data.get("name"),
            "task_type": data.get("task_type"),
            "db_type": data.get("db_type"),
            "schedule": data.get("schedule"),
            "description": data.get("description"),
            "is_active": data.get("is_active"),
            "is_builtin": data.get("is_builtin"),
            "last_run": data.get("last_run"),
            "last_status": data.get("last_status"),
            "last_message": data.get("last_message"),
            "run_count": data.get("run_count"),
            "success_count": data.get("success_count"),
            "success_rate": data.get("success_rate"),
            "config": data.get("config"),
        }
    
    @staticmethod
    def extract_sync_session_context(session_data: Any) -> Dict[str, Any]:
        """从同步会话数据中提取上下文"""
        if hasattr(session_data, 'to_dict'):
            data = session_data.to_dict()
        elif isinstance(session_data, dict):
            data = session_data
        else:
            return {}
        
        return {
            "session_id": data.get("session_id"),
            "sync_type": data.get("sync_type"),
            "sync_category": data.get("sync_category"),
            "status": data.get("status"),
            "created_by": data.get("created_by"),
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
            "total_instances": data.get("total_instances"),
            "successful_instances": data.get("successful_instances"),
            "failed_instances": data.get("failed_instances"),
            "progress_percentage": data.get("progress_percentage"),
        }
