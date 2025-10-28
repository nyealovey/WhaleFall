"""
鲸落 - 同步实例记录模型
"""

from app import db
from app.utils.time_utils import time_utils


class SyncInstanceRecord(db.Model):
    """同步实例记录模型 - 记录每个实例的同步详情
    
    支持多种同步类型：
    - account: 账户同步
    - capacity: 容量同步  
    - aggregation: 聚合统计
    - config: 配置同步
    - other: 其他同步类型
    """

    __tablename__ = "sync_instance_records"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.String(36),
        db.ForeignKey("sync_sessions.session_id"),
        nullable=False,
        index=True,
    )
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    instance_name = db.Column(db.String(255))
    sync_category = db.Column(
        db.String(20),
        nullable=False,
        default="account",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    # 通用同步统计字段
    items_synced = db.Column(db.Integer, default=0)  # 同步的项目数量
    items_created = db.Column(db.Integer, default=0)  # 创建的项目数量
    items_updated = db.Column(db.Integer, default=0)  # 更新的项目数量
    items_deleted = db.Column(db.Integer, default=0)  # 删除的项目数量

    # 通用字段
    error_message = db.Column(db.Text)
    sync_details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)

    def __init__(
        self,
        session_id: str,
        instance_id: int,
        instance_name: str | None = None,
        sync_category: str = "account",
    ) -> None:
        """
        初始化同步实例记录

        Args:
            session_id: 同步会话ID
            instance_id: 实例ID
            instance_name: 实例名称
            sync_category: 同步分类
        """
        self.session_id = session_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.sync_category = sync_category
        self.status = "pending"

    def to_dict(self) -> dict[str, any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "sync_category": self.sync_category,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "items_synced": self.items_synced,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_deleted": self.items_deleted,
            "error_message": self.error_message,
            "sync_details": self.sync_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def start_sync(self) -> None:
        """开始同步"""
        self.status = "running"
        self.started_at = time_utils.now()

    def complete_sync(
        self,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_deleted: int = 0,
        sync_details: dict | None = None,
    ) -> None:
        """完成同步"""
        self.status = "completed"
        self.completed_at = time_utils.now()
        self.items_synced = items_synced
        self.items_created = items_created
        self.items_updated = items_updated
        self.items_deleted = items_deleted
        self.sync_details = sync_details

    def fail_sync(self, error_message: str, sync_details: dict | None = None) -> None:
        """同步失败"""
        self.status = "failed"
        self.completed_at = time_utils.now()
        self.error_message = error_message
        self.sync_details = sync_details

    def get_duration_seconds(self) -> float | None:
        """获取同步持续时间（秒）"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    def get_sync_summary(self) -> dict[str, any]:
        """获取同步摘要信息"""
        return {
            "status": self.status,
            "duration_seconds": self.get_duration_seconds(),
            "items_synced": self.items_synced,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_deleted": self.items_deleted,
            "has_error": bool(self.error_message),
            "error_message": self.error_message,
            "is_successful": self.is_successful(),
            "is_failed": self.is_failed(),
            "failure_reason": self.get_failure_reason(),
            "sync_category_display": self.get_sync_category_display(),
        }
    
    def is_successful(self) -> bool:
        """判断同步是否成功"""
        if self.status != "completed" or self.error_message:
            return False
        
        # 根据同步分类判断是否有实际数据
        return self._has_meaningful_data()
    
    def is_failed(self) -> bool:
        """判断同步是否失败"""
        return self.status == "failed" or bool(self.error_message) or not self._has_meaningful_data()
    
    def _has_meaningful_data(self) -> bool:
        """根据同步分类判断是否有有意义的数据"""
        if self.sync_category == "account":
            # 账户同步：至少要有同步的账户数据且包含账户信息
            return self.items_synced > 0 and self._has_account_data()
        elif self.sync_category == "capacity":
            # 容量同步：至少要有容量数据
            return self.items_synced > 0 and self._has_capacity_data()
        elif self.sync_category == "aggregation":
            # 聚合统计：至少要有聚合数据
            return self.items_synced > 0 and self._has_aggregation_data()
        elif self.sync_category == "config":
            # 配置同步：至少要有配置数据
            return self.items_synced > 0 and self._has_config_data()
        else:
            # 其他类型：至少要有同步的项目
            return self.items_synced > 0
    
    def _has_capacity_data(self) -> bool:
        """检查是否有容量数据"""
        if not self.sync_details:
            return False
        
        # 检查sync_details中是否包含容量相关信息
        capacity_indicators = [
            'total_size_mb', 'database_count', 'avg_size_mb', 
            'max_size_mb', 'min_size_mb', 'capacity_data'
        ]
        
        return any(
            key in self.sync_details and self.sync_details[key] is not None
            for key in capacity_indicators
        )
    
    def _has_aggregation_data(self) -> bool:
        """检查是否有聚合数据"""
        if not self.sync_details:
            return False
        
        # 检查sync_details中是否包含聚合相关信息
        aggregation_indicators = [
            'aggregation_count', 'period_type', 'calculated_at',
            'aggregation_data', 'statistics_generated'
        ]
        
        return any(
            key in self.sync_details and self.sync_details[key] is not None
            for key in aggregation_indicators
        )
    
    def _has_account_data(self) -> bool:
        """检查是否有账户数据"""
        if not self.sync_details:
            return False
        
        # 检查sync_details中是否包含账户相关信息
        account_indicators = [
            'account_count', 'account_types', 'account_list', 'accounts',
            'user_count', 'admin_count', 'account_data', 'permissions',
            'account_details', 'sync_result', 'account_info'
        ]
        
        return any(
            key in self.sync_details and self.sync_details[key] is not None
            for key in account_indicators
        )
    
    def _has_config_data(self) -> bool:
        """检查是否有配置数据"""
        if not self.sync_details:
            return False
        
        # 检查sync_details中是否包含配置相关信息
        config_indicators = [
            'config_count', 'config_items', 'config_data', 'settings',
            'configuration', 'config_details', 'sync_config'
        ]
        
        return any(
            key in self.sync_details and self.sync_details[key] is not None
            for key in config_indicators
        )
    
    def get_sync_category_display(self) -> str:
        """获取同步分类的显示名称"""
        from app.constants.sync_constants import SyncConstants
        return SyncConstants.get_category_display(self.sync_category)
    
    def get_failure_reason(self) -> str | None:
        """获取失败原因"""
        if self.error_message:
            return self.error_message
        
        if self.status == "failed":
            return "同步状态标记为失败"
        
        if not self._has_meaningful_data():
            return self._get_no_data_reason()
        
        return None
    
    def _get_no_data_reason(self) -> str:
        """获取无数据的原因"""
        if self.sync_category == "account":
            if self.items_synced == 0:
                return f"账户同步失败：未同步到任何账户数据 (items_synced={self.items_synced})"
            else:
                return "账户同步失败：未检测到有效的账户数据"
        elif self.sync_category == "capacity":
            if self.items_synced == 0:
                return f"容量同步失败：未同步到任何容量数据 (items_synced={self.items_synced})"
            else:
                return "容量同步失败：未检测到有效的容量数据"
        elif self.sync_category == "aggregation":
            if self.items_synced == 0:
                return f"聚合统计失败：未生成任何聚合数据 (items_synced={self.items_synced})"
            else:
                return "聚合统计失败：未检测到有效的聚合数据"
        elif self.sync_category == "config":
            if self.items_synced == 0:
                return f"配置同步失败：未同步到任何配置数据 (items_synced={self.items_synced})"
            else:
                return "配置同步失败：未检测到有效的配置数据"
        else:
            return f"同步失败：未同步到任何数据 (items_synced={self.items_synced})"
    

    @staticmethod
    def get_records_by_session(session_id: str) -> list["SyncInstanceRecord"]:
        """根据会话ID获取所有实例记录"""
        return (
            SyncInstanceRecord.query.filter_by(session_id=session_id)
            .order_by(SyncInstanceRecord.created_at.asc())
            .all()
        )

    @staticmethod
    def get_records_by_instance(instance_id: int, limit: int = 50) -> list["SyncInstanceRecord"]:
        """根据实例ID获取同步记录"""
        return (
            SyncInstanceRecord.query.filter_by(instance_id=instance_id)
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_records_by_category(sync_category: str, limit: int = 100) -> list["SyncInstanceRecord"]:
        """根据同步分类获取记录"""
        return (
            SyncInstanceRecord.query.filter_by(sync_category=sync_category)
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_failed_records(limit: int = 50) -> list["SyncInstanceRecord"]:
        """获取失败的同步记录"""
        return (
            SyncInstanceRecord.query.filter(
                SyncInstanceRecord.status == "failed"
            )
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_successful_records(limit: int = 50) -> list["SyncInstanceRecord"]:
        """获取成功的同步记录（使用新的成功判断逻辑）"""
        all_records = (
            SyncInstanceRecord.query.filter(
                SyncInstanceRecord.status == "completed",
                SyncInstanceRecord.error_message.is_(None)
            )
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit * 2)  # 多查询一些，因为要过滤
            .all()
        )
        
        # 使用新的成功判断逻辑过滤
        successful_records = [r for r in all_records if r.is_successful()]
        return successful_records[:limit]
    
    @staticmethod
    def get_failure_statistics() -> dict[str, any]:
        """获取失败统计信息"""
        from sqlalchemy import func
        
        # 查询所有记录
        all_records = SyncInstanceRecord.query.all()
        
        total_count = len(all_records)
        failed_count = sum(1 for r in all_records if r.is_failed())
        successful_count = sum(1 for r in all_records if r.is_successful())
        
        # 按分类统计失败原因
        failure_reasons = {}
        for record in all_records:
            if record.is_failed():
                reason = record.get_failure_reason()
                if reason:
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # 按分类统计失败数量
        category_failures = {}
        for record in all_records:
            if record.is_failed():
                category = record.sync_category
                category_failures[category] = category_failures.get(category, 0) + 1
        
        return {
            "total_records": total_count,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "success_rate": (successful_count / total_count * 100) if total_count > 0 else 0,
            "failure_rate": (failed_count / total_count * 100) if total_count > 0 else 0,
            "failure_reasons": failure_reasons,
            "category_failures": category_failures,
        }
    
    @staticmethod
    def get_records_by_instance_and_category(
        instance_id: int, 
        sync_category: str, 
        limit: int = 50
    ) -> list["SyncInstanceRecord"]:
        """根据实例ID和同步分类获取记录"""
        return (
            SyncInstanceRecord.query.filter_by(
                instance_id=instance_id,
                sync_category=sync_category
            )
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self) -> str:
        return f"<SyncInstanceRecord {self.instance_name} ({self.status})>"
