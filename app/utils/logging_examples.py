"""
泰摸鱼吧 - 日志记录使用示例
展示如何使用新的上下文日志系统
"""

from app.utils.module_loggers import module_loggers
from app.models.instance import Instance
from app.models.credential import Credential
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.account_classification import AccountClassification, ClassificationRule


class LoggingExamples:
    """日志记录使用示例"""
    
    @staticmethod
    def example_auth_logging():
        """认证模块日志示例"""
        # 用户登录成功
        module_loggers.log_auth_info(
            "用户登录成功",
            user_id=1,
            username="admin",
            role="admin",
            auth_method="password",
            login_time="2025-09-15T10:00:00",
            ip_address="192.168.1.100"
        )
        
        # 用户登录失败
        module_loggers.log_auth_error(
            "用户登录失败",
            username="admin",
            auth_method="password",
            login_attempts=3,
            ip_address="192.168.1.100",
            exception=Exception("密码错误")
        )
    
    @staticmethod
    def example_instance_logging():
        """实例管理模块日志示例"""
        # 创建实例对象
        instance = Instance(
            name="生产MySQL-01",
            db_type="MySQL",
            host="192.168.1.100",
            port=3306,
            database_name="production",
            environment="production"
        )
        
        # 实例创建成功
        module_loggers.log_instance_info(
            "数据库实例创建成功",
            instance_data=instance,
            operation_type="create"
        )
        
        # 实例连接测试失败
        module_loggers.log_instance_error(
            "数据库连接测试失败",
            instance_data=instance,
            connection_status="failed",
            connection_error="Connection refused",
            exception=Exception("无法连接到数据库")
        )
    
    @staticmethod
    def example_credential_logging():
        """凭据管理模块日志示例"""
        # 创建凭据对象
        credential = Credential(
            name="MySQL生产凭据",
            credential_type="database",
            username="root",
            password="password123",
            db_type="MySQL"
        )
        
        # 凭据创建成功
        module_loggers.log_credential_info(
            "数据库凭据创建成功",
            credential_data=credential,
            operation_type="create"
        )
        
        # 凭据验证失败
        module_loggers.log_credential_error(
            "凭据验证失败",
            credential_data=credential,
            operation_type="verify",
            exception=Exception("密码不正确")
        )
    
    @staticmethod
    def example_account_logging():
        """账户管理模块日志示例"""
        # 创建账户对象
        account = CurrentAccountSyncData(
            instance_id=1,
            db_type="MySQL",
            username="app_user",
            is_superuser=False
        )
        
        # 账户同步成功
        module_loggers.log_account_info(
            "账户信息同步成功",
            account_data=account,
            operation_type="sync",
            permissions_count=5
        )
        
        # 账户权限获取失败
        module_loggers.log_account_error(
            "获取账户权限失败",
            account_data=account,
            operation_type="get_permissions",
            exception=Exception("权限查询超时")
        )
    
    @staticmethod
    def example_sync_logging():
        """账户同步模块日志示例"""
        # 创建实例和凭据对象
        instance = Instance(
            name="生产MySQL-01",
            db_type="MySQL",
            host="192.168.1.100",
            port=3306
        )
        
        credential = Credential(
            name="MySQL生产凭据",
            credential_type="database",
            username="root",
            password="password123",
            db_type="MySQL"
        )
        
        # 同步开始
        module_loggers.log_sync_info(
            "开始账户同步",
            instance_data=instance,
            credential_data=credential,
            sync_type="scheduled",
            sync_mode="full",
            total_accounts=100
        )
        
        # 同步成功
        module_loggers.log_sync_info(
            "账户同步完成",
            instance_data=instance,
            credential_data=credential,
            sync_type="scheduled",
            sync_status="completed",
            total_accounts=100,
            synced_accounts=95,
            failed_accounts=5,
            new_accounts=10,
            updated_accounts=85,
            duration=120
        )
        
        # 同步失败
        module_loggers.log_sync_error(
            "账户同步失败",
            instance_data=instance,
            credential_data=credential,
            sync_type="scheduled",
            sync_status="failed",
            error_count=5,
            last_error="连接超时",
            retry_count=3,
            exception=Exception("数据库连接超时")
        )
    
    @staticmethod
    def example_classification_logging():
        """账户分类模块日志示例"""
        # 创建分类对象
        classification = AccountClassification(
            name="特权账户",
            risk_level="high",
            priority=1
        )
        
        # 创建规则对象
        rule = ClassificationRule(
            classification_id=1,
            db_type="MySQL",
            rule_name="MySQL特权权限规则",
            rule_expression='{"permissions": ["GRANT", "SUPER"], "min_count": 1}'
        )
        
        # 创建账户对象
        account = CurrentAccountSyncData(
            instance_id=1,
            db_type="MySQL",
            username="admin_user",
            is_superuser=True
        )
        
        # 分类成功
        module_loggers.log_classification_info(
            "账户分类成功",
            classification_data=classification,
            rule_data=rule,
            account_data=account,
            classification_result="特权账户",
            confidence_score=0.95,
            matched_permissions=["GRANT", "SUPER"],
            classification_reason="匹配特权权限规则"
        )
        
        # 分类失败
        module_loggers.log_classification_error(
            "账户分类失败",
            classification_data=classification,
            rule_data=rule,
            account_data=account,
            classification_result="unknown",
            confidence_score=0.0,
            exception=Exception("规则评估异常")
        )
    
    @staticmethod
    def example_task_logging():
        """任务管理模块日志示例"""
        # 创建任务对象
        task = {
            "id": 1,
            "name": "账户同步任务",
            "task_type": "sync_accounts",
            "db_type": "MySQL",
            "schedule": "0 */6 * * *",
            "is_active": True,
            "run_count": 10,
            "success_count": 8
        }
        
        # 任务执行成功
        module_loggers.log_task_info(
            "任务执行成功",
            task_data=task,
            execution_status="completed",
            duration=300,
            records_processed=1000
        )
        
        # 任务执行失败
        module_loggers.log_task_error(
            "任务执行失败",
            task_data=task,
            execution_status="failed",
            error_count=5,
            last_error="数据库连接失败",
            exception=Exception("连接超时")
        )
    
    @staticmethod
    def example_sync_session_logging():
        """同步会话模块日志示例"""
        # 创建会话对象
        session = {
            "session_id": "sync_123456",
            "sync_type": "manual_batch",
            "sync_category": "account",
            "status": "running",
            "total_instances": 10,
            "successful_instances": 7,
            "failed_instances": 1
        }
        
        # 会话开始
        module_loggers.log_sync_session_info(
            "同步会话开始",
            session_data=session,
            target_instances=[1, 2, 3, 4, 5],
            target_database_types=["MySQL", "PostgreSQL"]
        )
        
        # 会话完成
        module_loggers.log_sync_session_info(
            "同步会话完成",
            session_data=session,
            status="completed",
            progress_percentage=100.0,
            duration=1800
        )
    
    @staticmethod
    def example_admin_logging():
        """系统管理模块日志示例"""
        # 配置更新
        module_loggers.log_admin_info(
            "系统配置更新",
            operation_type="config",
            operation_name="update_config",
            config_key="sync_interval",
            old_value="3600",
            new_value="1800",
            admin_user_id=1,
            admin_username="admin"
        )
        
        # 用户管理
        module_loggers.log_admin_info(
            "用户角色更新",
            operation_type="user",
            operation_name="update_user_role",
            target_user_id=2,
            target_username="user1",
            old_value="user",
            new_value="admin",
            admin_user_id=1,
            admin_username="admin"
        )
        
        # 系统清理
        module_loggers.log_admin_info(
            "系统数据清理",
            operation_type="cleanup",
            operation_name="cleanup_old_logs",
            cleanup_type="logs",
            cleanup_target="unified_logs",
            records_cleaned=10000,
            space_freed=1024000,
            admin_user_id=1,
            admin_username="admin"
        )
    
    @staticmethod
    def example_health_logging():
        """健康监控模块日志示例"""
        # 系统健康检查
        module_loggers.log_health_info(
            "系统健康检查完成",
            check_type="system",
            check_name="system_health",
            check_status="healthy",
            memory_usage=75.5,
            cpu_usage=45.2,
            disk_usage=60.8
        )
        
        # 数据库健康检查
        module_loggers.log_health_info(
            "数据库健康检查完成",
            check_type="database",
            check_name="database_health",
            check_status="healthy",
            active_instances=8,
            total_instances=10,
            instance_errors=0
        )
        
        # 服务异常
        module_loggers.log_health_error(
            "服务响应异常",
            check_type="service",
            check_name="api_response",
            check_status="critical",
            response_time=5000.0,
            error_rate=15.5,
            exception=Exception("服务响应超时")
        )


# 使用示例
if __name__ == "__main__":
    examples = LoggingExamples()
    
    # 运行所有示例
    examples.example_auth_logging()
    examples.example_instance_logging()
    examples.example_credential_logging()
    examples.example_account_logging()
    examples.example_sync_logging()
    examples.example_classification_logging()
    examples.example_task_logging()
    examples.example_sync_session_logging()
    examples.example_admin_logging()
    examples.example_health_logging()
    
    print("所有日志示例已执行完成！")
