"""
泰摸鱼吧 - 数据库同步适配器基类
定义数据库同步的通用接口和流程
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple

from app.models import Instance
from app.utils.database_batch_manager import DatabaseBatchManager
from app.utils.structlog_config import get_sync_logger


class BaseSyncAdapter(ABC):
    """数据库同步适配器基类"""

    def __init__(self):
        self.sync_logger = get_sync_logger()

    @abstractmethod
    def get_database_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:
        """
        获取数据库中的所有账户信息
        
        Args:
            instance: 数据库实例
            connection: 数据库连接
            
        Returns:
            List[Dict]: 账户信息列表
        """
        raise NotImplementedError("子类必须实现get_database_accounts方法")

    @abstractmethod
    def extract_permissions(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从账户数据中提取权限信息
        
        Args:
            account_data: 原始账户数据
            
        Returns:
            Dict: 格式化的权限数据
        """
        raise NotImplementedError("子类必须实现extract_permissions方法")

    @abstractmethod
    def format_account_data(self, raw_account: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化账户数据为统一格式
        
        Args:
            raw_account: 原始账户数据
            
        Returns:
            Dict: 格式化后的账户数据
        """
        raise NotImplementedError("子类必须实现format_account_data方法")

    def sync_accounts(self, instance: Instance, connection: Any, session_id: str) -> Dict[str, Any]:
        """
        同步账户的统一流程
        
        Args:
            instance: 数据库实例
            connection: 数据库连接
            session_id: 会话ID
            
        Returns:
            Dict: 同步结果
        """
        try:
            self.sync_logger.info(
                f"开始{instance.db_type}账户同步",
                module="sync_adapter",
                instance_name=instance.name,
                db_type=instance.db_type,
                session_id=session_id
            )

            # 1. 获取数据库账户信息
            raw_accounts = self.get_database_accounts(instance, connection)
            
            if not raw_accounts:
                self.sync_logger.warning(
                    "未获取到账户信息",
                    module="sync_adapter",
                    instance_name=instance.name,
                    db_type=instance.db_type
                )
                return {
                    "success": True,
                    "synced_count": 0,
                    "added_count": 0,
                    "modified_count": 0,
                    "removed_count": 0,
                }

            # 2. 格式化账户数据
            formatted_accounts = []
            for raw_account in raw_accounts:
                try:
                    formatted_account = self.format_account_data(raw_account)
                    formatted_accounts.append(formatted_account)
                except Exception as e:
                    self.sync_logger.error(
                        f"格式化账户数据失败: {raw_account.get('username', 'unknown')}",
                        module="sync_adapter",
                        instance_name=instance.name,
                        error=str(e)
                    )

            # 3. 同步账户到本地数据库
            result = self._sync_accounts_to_local(
                instance, formatted_accounts, session_id
            )

            self.sync_logger.info(
                f"{instance.db_type}账户同步完成",
                module="sync_adapter",
                instance_name=instance.name,
                synced_count=result.get("synced_count", 0),
                added_count=result.get("added_count", 0),
                modified_count=result.get("modified_count", 0),
                removed_count=result.get("removed_count", 0),
            )

            return result

        except Exception as e:
            self.sync_logger.error(
                f"{instance.db_type}账户同步失败",
                module="sync_adapter",
                instance_name=instance.name,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "added_count": 0,
                "modified_count": 0,
                "removed_count": 0,
            }

    def _sync_accounts_to_local(self, instance: Instance, accounts: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """
        将账户同步到本地数据库 - 批量提交优化版
        
        1. 先确保账户一致性（新增/删除）
        2. 再检查权限变更  
        3. 使用批量提交机制，提高性能和可靠性
        
        Args:
            instance: 数据库实例
            accounts: 格式化的账户列表
            session_id: 会话ID
            
        Returns:
            Dict: 同步结果
        """
        from app import db
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.utils.time_utils import time_utils

        self.sync_logger.info(
            "开始账户一致性检查与权限同步",
            module="sync_adapter",
            instance_name=instance.name,
            remote_account_count=len(accounts)
        )

        # 使用批量提交管理器
        batch_manager = DatabaseBatchManager(
            batch_size=100,  # 每批次处理100个账户
            logger=self.sync_logger,
            instance_name=instance.name
        )

        try:
            # 第一步：账户一致性检查（批量处理）
            sync_result = self._ensure_account_consistency_batch(instance, accounts, session_id, batch_manager)
            
            # 第二步：权限变更检查（批量处理）
            permission_result = self._check_permission_changes_batch(instance, accounts, session_id, batch_manager)
            
            # 最终提交剩余的操作
            batch_manager.flush_remaining()
            
            # 合并结果
            final_result = {
                "success": True,
                "synced_count": sync_result["synced_count"] + permission_result["updated_count"],
                "added_count": sync_result["added_count"],
                "modified_count": permission_result["updated_count"],
                "removed_count": sync_result["removed_count"],
            }

            self.sync_logger.info(
                "账户同步完成",
                module="sync_adapter",
                instance_name=instance.name,
                **final_result
            )

            return final_result
            
        except Exception as e:
            # 发生错误时回滚所有未提交的操作
            batch_manager.rollback()
            self.sync_logger.error(
                "账户同步失败，已回滚所有操作",
                module="sync_adapter",
                instance_name=instance.name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"同步失败: {str(e)}",
                "synced_count": 0,
                "added_count": 0,
                "modified_count": 0,
                "removed_count": 0,
            }

    def _ensure_account_consistency_batch(self, instance: Instance, accounts: List[Dict[str, Any]], session_id: str, batch_manager: DatabaseBatchManager) -> Dict[str, Any]:
        """
        确保账户一致性 - 批量处理版本
        
        Args:
            instance: 数据库实例
            accounts: 远程账户列表
            session_id: 会话ID
            batch_manager: 批量管理器
            
        Returns:
            Dict: 一致性检查结果
        """
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.utils.time_utils import time_utils

        # 获取远程账户用户名集合
        remote_usernames = {account["username"] for account in accounts}
        
        # 获取本地所有未删除的账户
        local_accounts = CurrentAccountSyncData.query.filter_by(
            instance_id=instance.id,
            db_type=instance.db_type,
            is_deleted=False
        ).all()
        
        local_usernames = {account.username for account in local_accounts}
        
        # 找出需要新增的账户
        accounts_to_add = remote_usernames - local_usernames
        
        # 找出需要删除的账户
        accounts_to_remove = local_usernames - remote_usernames
        
        self.sync_logger.info(
            "账户一致性分析",
            module="sync_adapter",
            instance_name=instance.name,
            remote_count=len(remote_usernames),
            local_count=len(local_usernames),
            to_add=len(accounts_to_add),
            to_remove=len(accounts_to_remove)
        )

        added_count = 0
        removed_count = 0

        # 批量新增账户
        for account_data in accounts:
            if account_data["username"] in accounts_to_add:
                try:
                    new_account = self._create_new_account(
                        instance.id, instance.db_type, account_data["username"],
                        account_data["permissions"], account_data.get("is_superuser", False),
                        session_id
                    )
                    
                    # 使用批量管理器添加操作
                    batch_manager.add_operation(
                        "add", 
                        new_account, 
                        f"新增账户: {account_data['username']}"
                    )
                    added_count += 1
                    
                    self.sync_logger.debug(
                        f"准备新增账户: {account_data['username']}",
                        module="sync_adapter",
                        instance_name=instance.name
                    )
                except Exception as e:
                    self.sync_logger.error(
                        f"创建账户对象失败: {account_data['username']}",
                        module="sync_adapter",
                        instance_name=instance.name,
                        error=str(e)
                    )

        # 批量标记删除账户
        for local_account in local_accounts:
            if local_account.username in accounts_to_remove:
                local_account.is_deleted = True
                local_account.deleted_time = time_utils.now()
                local_account.last_change_type = "delete"
                local_account.last_change_time = time_utils.now()
                
                # 使用批量管理器添加更新操作
                batch_manager.add_operation(
                    "update", 
                    local_account, 
                    f"标记删除账户: {local_account.username}"
                )
                removed_count += 1
                
                self.sync_logger.debug(
                    f"准备标记删除账户: {local_account.username}",
                    module="sync_adapter",
                    instance_name=instance.name
                )

        return {
            "synced_count": added_count,
            "added_count": added_count,
            "removed_count": removed_count
        }

    def _check_permission_changes_batch(self, instance: Instance, accounts: List[Dict[str, Any]], session_id: str, batch_manager: DatabaseBatchManager) -> Dict[str, Any]:
        """
        检查权限变更 - 批量处理版本
        
        Args:
            instance: 数据库实例 
            accounts: 远程账户列表
            session_id: 会话ID
            batch_manager: 批量管理器
            
        Returns:
            Dict: 权限变更结果
        """
        from app.models.current_account_sync_data import CurrentAccountSyncData

        # 获取本地现有账户（排除刚刚标记删除的）
        existing_accounts = CurrentAccountSyncData.query.filter_by(
            instance_id=instance.id,
            db_type=instance.db_type,
            is_deleted=False
        ).all()
        
        # 建立本地账户映射
        local_account_map = {account.username: account for account in existing_accounts}
        
        updated_count = 0
        
        # 检查每个远程账户的权限变更
        for account_data in accounts:
            username = account_data["username"]
            local_account = local_account_map.get(username)
            
            if local_account:
                # 检测权限变更
                changes = self._detect_changes(
                    local_account, 
                    account_data["permissions"], 
                    account_data.get("is_superuser", False)
                )
                
                if changes:
                    # 有变更才更新
                    self._update_account_permissions(
                        local_account,
                        account_data["permissions"],
                        account_data.get("is_superuser", False)
                    )
                    
                    # 使用批量管理器添加更新操作
                    batch_manager.add_operation(
                        "update", 
                        local_account, 
                        f"更新账户权限: {username}"
                    )
                    
                    # 记录变更日志
                    self._log_changes_batch(
                        instance.id, instance.db_type, username, changes, session_id, batch_manager
                    )
                    
                    updated_count += 1
                    
                    self.sync_logger.debug(
                        f"准备更新账户权限: {username}",
                        module="sync_adapter",
                        instance_name=instance.name,
                        changes=list(changes.keys())
                    )
                else:
                    # 无变更，只更新同步时间
                    from app.utils.time_utils import time_utils
                    local_account.last_sync_time = time_utils.now()
                    
                    # 使用批量管理器添加更新操作
                    batch_manager.add_operation(
                        "update", 
                        local_account, 
                        f"更新同步时间: {username}"
                    )
                    
                    updated_count += 1  # 即使无变更也要计数
                    
                    self.sync_logger.debug(
                        f"账户无变更，更新同步时间: {username}",
                        module="sync_adapter",
                        instance_name=instance.name
                    )

        return {
            "updated_count": updated_count
        }

    def _log_changes_batch(self, instance_id: int, db_type: str, username: str,
                          changes: Dict[str, Any], session_id: str, batch_manager: DatabaseBatchManager) -> None:
        """
        记录变更日志 - 批量处理版本
        """
        from app.models.account_change_log import AccountChangeLog

        # 生成变更描述
        change_descriptions = self._generate_change_description(db_type, changes)
        change_description = "; ".join(change_descriptions) if change_descriptions else "权限已更新"
        
        # 判断变更类型
        change_type = self._determine_change_type(changes)

        change_log = AccountChangeLog(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            change_type=change_type,
            session_id=session_id,
            privilege_diff=changes,
            message=change_description,
            status="success",
        )
        
        # 使用批量管理器添加日志记录
        batch_manager.add_operation(
            "add", 
            change_log, 
            f"记录变更日志: {username}"
        )

    def _ensure_account_consistency(self, instance: Instance, accounts: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """
        确保账户一致性 - 处理账户的新增和删除
        
        Args:
            instance: 数据库实例
            accounts: 远程账户列表
            session_id: 会话ID
            
        Returns:
            Dict: 一致性检查结果
        """
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.utils.time_utils import time_utils

        # 获取远程账户用户名集合
        remote_usernames = {account["username"] for account in accounts}
        
        # 获取本地所有未删除的账户
        local_accounts = CurrentAccountSyncData.query.filter_by(
            instance_id=instance.id,
            db_type=instance.db_type,
            is_deleted=False
        ).all()
        
        local_usernames = {account.username for account in local_accounts}
        
        # 找出需要新增的账户
        accounts_to_add = remote_usernames - local_usernames
        
        # 找出需要删除的账户
        accounts_to_remove = local_usernames - remote_usernames
        
        self.sync_logger.info(
            "账户一致性分析",
            module="sync_adapter",
            instance_name=instance.name,
            remote_count=len(remote_usernames),
            local_count=len(local_usernames),
            to_add=len(accounts_to_add),
            to_remove=len(accounts_to_remove)
        )

        added_count = 0
        removed_count = 0

        # 新增账户
        for account_data in accounts:
            if account_data["username"] in accounts_to_add:
                try:
                    new_account = self._create_new_account(
                        instance.id, instance.db_type, account_data["username"],
                        account_data["permissions"], account_data.get("is_superuser", False),
                        session_id
                    )
                    from app import db
                    db.session.add(new_account)
                    added_count += 1
                    
                    self.sync_logger.info(
                        f"新增账户: {account_data['username']}",
                        module="sync_adapter",
                        instance_name=instance.name
                    )
                except Exception as e:
                    self.sync_logger.error(
                        f"新增账户失败: {account_data['username']}",
                        module="sync_adapter",
                        instance_name=instance.name,
                        error=str(e)
                    )

        # 标记删除账户
        for local_account in local_accounts:
            if local_account.username in accounts_to_remove:
                local_account.is_deleted = True
                local_account.deleted_time = time_utils.now()
                local_account.last_change_type = "delete"
                local_account.last_change_time = time_utils.now()
                removed_count += 1
                
                self.sync_logger.info(
                    f"标记删除账户: {local_account.username}",
                    module="sync_adapter",
                    instance_name=instance.name
                )

        return {
            "synced_count": added_count,
            "added_count": added_count,
            "removed_count": removed_count
        }

    def _check_permission_changes(self, instance: Instance, accounts: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """
        检查权限变更 - 只对现有账户进行权限比较
        
        Args:
            instance: 数据库实例 
            accounts: 远程账户列表
            session_id: 会话ID
            
        Returns:
            Dict: 权限变更结果
        """
        from app.models.current_account_sync_data import CurrentAccountSyncData

        # 获取本地现有账户（排除刚刚标记删除的）
        existing_accounts = CurrentAccountSyncData.query.filter_by(
            instance_id=instance.id,
            db_type=instance.db_type,
            is_deleted=False
        ).all()
        
        # 建立本地账户映射
        local_account_map = {account.username: account for account in existing_accounts}
        
        updated_count = 0
        
        # 检查每个远程账户的权限变更
        for account_data in accounts:
            username = account_data["username"]
            local_account = local_account_map.get(username)
            
            if local_account:
                # 检测权限变更
                changes = self._detect_changes(
                    local_account, 
                    account_data["permissions"], 
                    account_data.get("is_superuser", False)
                )
                
                if changes:
                    # 有变更才更新
                    self._update_account_permissions(
                        local_account,
                        account_data["permissions"],
                        account_data.get("is_superuser", False)
                    )
                    
                    # 记录变更日志
                    self._log_changes(
                        instance.id, instance.db_type, username, changes, session_id
                    )
                    
                    updated_count += 1
                    
                    self.sync_logger.info(
                        f"更新账户权限: {username}",
                        module="sync_adapter",
                        instance_name=instance.name,
                        changes=list(changes.keys())
                    )
                else:
                    # 无变更，只更新同步时间
                    from app.utils.time_utils import time_utils
                    local_account.last_sync_time = time_utils.now()
                    
                    self.sync_logger.debug(
                        f"账户无变更: {username}",
                        module="sync_adapter",
                        instance_name=instance.name
                    )

        return {
            "updated_count": updated_count
        }


    @abstractmethod
    def _detect_changes(self, existing_account: Any, new_permissions: Dict[str, Any], 
                       is_superuser: bool) -> Dict[str, Any]:
        """
        检测账户变更
        
        Args:
            existing_account: 现有账户对象
            new_permissions: 新的权限数据
            is_superuser: 是否超级用户
            
        Returns:
            Dict: 变更详情
        """
        raise NotImplementedError("子类必须实现_detect_changes方法")

    @abstractmethod
    def _update_account_permissions(self, account: Any, permissions_data: Dict[str, Any], 
                                   is_superuser: bool) -> None:
        """
        更新账户权限信息
        
        Args:
            account: 账户对象
            permissions_data: 权限数据
            is_superuser: 是否超级用户
        """
        raise NotImplementedError("子类必须实现_update_account_permissions方法")

    @abstractmethod
    def _create_new_account(self, instance_id: int, db_type: str, username: str,
                           permissions_data: Dict[str, Any], is_superuser: bool,
                           session_id: str) -> Any:
        """
        创建新账户
        
        Args:
            instance_id: 实例ID
            db_type: 数据库类型
            username: 用户名
            permissions_data: 权限数据
            is_superuser: 是否超级用户
            session_id: 会话ID
            
        Returns:
            新创建的账户对象
        """
        raise NotImplementedError("子类必须实现_create_new_account方法")

    def _log_changes(self, instance_id: int, db_type: str, username: str,
                    changes: Dict[str, Any], session_id: str) -> None:
        """
        记录变更日志
        
        Args:
            instance_id: 实例ID
            db_type: 数据库类型
            username: 用户名
            changes: 变更详情
            session_id: 会话ID
        """
        from app import db
        from app.models.account_change_log import AccountChangeLog

        # 生成变更描述
        change_descriptions = self._generate_change_description(db_type, changes)
        change_description = "; ".join(change_descriptions) if change_descriptions else "权限已更新"
        
        # 判断变更类型
        change_type = self._determine_change_type(changes)

        change_log = AccountChangeLog(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            change_type=change_type,
            session_id=session_id,
            privilege_diff=changes,
            message=change_description,
            status="success",
        )
        db.session.add(change_log)

    @abstractmethod
    def _generate_change_description(self, db_type: str, changes: Dict[str, Any]) -> List[str]:
        """
        生成变更描述
        
        Args:
            db_type: 数据库类型
            changes: 变更数据
            
        Returns:
            List[str]: 变更描述列表
        """
        raise NotImplementedError("子类必须实现_generate_change_description方法")

    def _determine_change_type(self, changes: Dict[str, Any]) -> str:
        """确定变更类型"""
        # 检查是否只有type_specific变更
        if len(changes) == 1 and "type_specific" in changes:
            return "modify_other"
        
        # 检查是否包含权限相关变更
        permission_fields = [
            "is_superuser",  # 超级用户状态是权限相关
            "global_privileges", "database_privileges", "predefined_roles",
            "role_attributes", "server_roles", "server_permissions",
            "database_roles", "database_permissions", "roles",
            "system_privileges", "tablespace_privileges"
        ]
        
        has_permission_changes = any(field in changes for field in permission_fields)
        
        return "modify_privilege" if has_permission_changes else "modify_other"
