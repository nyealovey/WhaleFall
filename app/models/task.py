"""
泰摸鱼吧 - 任务模型
"""

from datetime import datetime

from app import db


class Task(db.Model):
    """任务模型"""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    task_type = db.Column(db.String(50), nullable=False, index=True)  # sync_accounts, sync_version, sync_size等
    db_type = db.Column(db.String(50), nullable=False, index=True)  # postgresql, mysql, sqlserver, oracle
    schedule = db.Column(db.String(100), nullable=True)  # cron表达式
    description = db.Column(db.Text, nullable=True)
    python_code = db.Column(db.Text, nullable=True)  # 可执行的Python代码
    config = db.Column(db.JSON, nullable=True)  # 任务配置参数
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)  # 是否为内置任务
    last_run = db.Column(db.DateTime, nullable=True)
    last_run_at = db.Column(db.DateTime, nullable=True)  # 兼容字段
    last_status = db.Column(db.String(20), nullable=True)
    last_message = db.Column(db.Text, nullable=True)
    run_count = db.Column(db.Integer, default=0)  # 运行次数
    success_count = db.Column(db.Integer, default=0)  # 成功次数
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    # 关系 - 移除instance_id，任务按数据库类型匹配实例

    def __init__(
        self,
        name: str,
        task_type: str,
        db_type: str,
        schedule: str | None = None,
        description: str | None = None,
        python_code: str | None = None,
        config: str | None = None,
        is_active: bool = True,
        is_builtin: bool = False,
    ) -> None:
        """
        初始化任务

        Args:
            name: 任务名称
            task_type: 任务类型 (sync_accounts, sync_version, sync_size等)
            db_type: 数据库类型 (postgresql, mysql, sqlserver, oracle)
            schedule: 调度表达式
            description: 描述
            python_code: Python执行代码
            config: 任务配置参数
            is_active: 是否启用
            is_builtin: 是否为内置任务
        """
        self.name = name
        self.task_type = task_type
        self.db_type = db_type
        self.schedule = schedule
        self.description = description
        self.python_code = python_code
        self.config = config or {}
        self.is_active = is_active
        self.is_builtin = is_builtin

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            Dict: 任务信息字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "db_type": self.db_type,
            "schedule": self.schedule,
            "description": self.description,
            "python_code": self.python_code,
            "config": self.config,
            "is_active": self.is_active,
            "is_builtin": self.is_builtin,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "last_message": self.last_message,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "success_rate": round(
                ((self.success_count / self.run_count * 100) if self.run_count > 0 else 0),
                2,
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_active_tasks() -> list:
        """获取所有活跃任务"""
        return Task.query.filter_by(is_active=True).all()

    @staticmethod
    def get_by_type(task_type: str) -> list:
        """根据任务类型获取任务"""
        return Task.query.filter_by(task_type=task_type, is_active=True).all()

    @staticmethod
    def get_by_db_type(db_type: str) -> list:
        """根据数据库类型获取任务"""
        return Task.query.filter_by(db_type=db_type, is_active=True).all()

    @staticmethod
    def get_builtin_tasks() -> list:
        """获取所有内置任务"""
        return Task.query.filter_by(is_builtin=True).all()

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.run_count == 0:
            return 0.0
        return round((self.success_count / self.run_count * 100), 2)

    def get_matching_instances(self) -> list:
        """获取匹配的实例列表"""
        from app.models.instance import Instance

        return Instance.query.filter_by(db_type=self.db_type, is_active=True).all()

    def __repr__(self) -> str:
        return f"<Task {self.name}>"
