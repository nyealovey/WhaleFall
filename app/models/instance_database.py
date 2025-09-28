"""
鲸落 - 实例数据库关系模型
用于维护实例包含哪些数据库，以及数据库的状态变化
"""

from datetime import datetime, date
from app import db
from app.utils.timezone import now


class InstanceDatabase(db.Model):
    """实例-数据库关系模型"""

    __tablename__ = "instance_databases"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    database_name = db.Column(db.String(255), nullable=False, comment="数据库名称")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="数据库是否活跃（未删除）")
    first_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="首次发现日期")
    last_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="最后发现日期")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, nullable=False)

    # 关系
    instance = db.relationship("Instance", back_populates="instance_databases")

    __table_args__ = (
        db.UniqueConstraint("instance_id", "database_name", name="uq_instance_database_instance_name"),
        db.Index("ix_instance_databases_database_name", "database_name"),
        db.Index("ix_instance_databases_active", "is_active"),
        db.Index("ix_instance_databases_last_seen", "last_seen_date"),
        {
            "comment": "实例-数据库关系表，维护数据库的存在状态",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<InstanceDatabase(id={self.id}, instance_id={self.instance_id}, "
            f"database_name='{self.database_name}', is_active={self.is_active})>"
        )

    @classmethod
    def mark_as_deleted(cls, instance_id: int, database_name: str) -> bool:
        """
        标记数据库为已删除
        
        Args:
            instance_id: 实例ID
            database_name: 数据库名称
            
        Returns:
            bool: 是否成功标记
        """
        try:
            instance_db = cls.query.filter_by(
                instance_id=instance_id,
                database_name=database_name
            ).first()
            
            if instance_db:
                instance_db.is_active = False
                instance_db.deleted_at = now()
                instance_db.updated_at = now()
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def detect_deleted_databases(cls, instance_id: int) -> int:
        """
        检测并标记已删除的数据库
        
        Args:
            instance_id: 实例ID
            
        Returns:
            int: 标记为已删除的数据库数量
        """
        try:
            from app.models.database_size_stat import DatabaseSizeStat
            from sqlalchemy import func
            
            # 获取该实例最新的数据采集日期
            latest_collection_date = db.session.query(
                func.max(DatabaseSizeStat.collected_date)
            ).filter_by(instance_id=instance_id).scalar()
            
            if not latest_collection_date:
                return 0
            
            # 查找在最新采集日期没有数据的活跃数据库
            active_databases = cls.query.filter(
                cls.instance_id == instance_id,
                cls.is_active == True
            ).all()
            
            deleted_count = 0
            for instance_db in active_databases:
                # 检查该数据库在最新采集日期是否有数据
                has_recent_data = DatabaseSizeStat.query.filter(
                    DatabaseSizeStat.instance_id == instance_id,
                    DatabaseSizeStat.database_name == instance_db.database_name,
                    DatabaseSizeStat.collected_date == latest_collection_date
                ).first() is not None
                
                if not has_recent_data:
                    # 标记为已删除
                    instance_db.is_active = False
                    instance_db.deleted_at = now()
                    instance_db.updated_at = now()
                    deleted_count += 1
            
            db.session.commit()
            return deleted_count
            
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def update_database_status(cls, instance_id: int, database_name: str, collected_date: date) -> None:
        """
        更新数据库状态（当有新的数据采集时调用）
        
        Args:
            instance_id: 实例ID
            database_name: 数据库名称
            collected_date: 采集日期
        """
        try:
            instance_db = cls.query.filter_by(
                instance_id=instance_id,
                database_name=database_name
            ).first()
            
            if instance_db:
                # 更新最后发现日期
                instance_db.last_seen_date = collected_date
                instance_db.updated_at = now()
                
                # 如果之前被标记为删除，现在重新激活
                if not instance_db.is_active:
                    instance_db.is_active = True
                    instance_db.deleted_at = None
            else:
                # 创建新记录
                instance_db = cls(
                    instance_id=instance_id,
                    database_name=database_name,
                    first_seen_date=collected_date,
                    last_seen_date=collected_date,
                    is_active=True
                )
                db.session.add(instance_db)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise e
