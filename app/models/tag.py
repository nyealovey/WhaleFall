"""
鲸落 - 标签模型
"""

from app import db
from app.utils.timezone import now


class Tag(db.Model):
    """标签模型"""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # 标签分类
    color = db.Column(db.String(20), default="primary", nullable=False)  # 标签颜色
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)

    # 关系
    instances = db.relationship("Instance", secondary="instance_tags", back_populates="tags")

    def __init__(
        self,
        name: str,
        display_name: str,
        category: str,
        color: str = "primary",
        description: str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> None:
        """
        初始化标签

        Args:
            name: 标签代码（如：wenzhou）
            display_name: 显示名称（如：温州）
            category: 标签分类（如：location, company_type, environment）
            color: 标签颜色（如：primary, success, info, warning, danger）
            description: 描述
            sort_order: 排序顺序
            is_active: 是否激活
        """
        self.name = name
        self.display_name = display_name
        self.category = category
        self.color = color
        self.description = description
        self.sort_order = sort_order
        self.is_active = is_active

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "color": self.color,
            "description": self.description,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


    @staticmethod
    def get_active_tags() -> list:
        """获取所有活跃标签"""
        return Tag.query.filter_by(is_active=True).order_by(Tag.category, Tag.sort_order, Tag.name).all()

    @staticmethod
    def get_tags_by_category(category: str) -> list:
        """根据分类获取标签"""
        return Tag.query.filter_by(category=category, is_active=True).order_by(Tag.sort_order, Tag.name).all()

    @staticmethod
    def get_tag_choices() -> list:
        """获取标签选项（用于表单）"""
        tags = Tag.get_active_tags()
        return [(tag.name, tag.display_name) for tag in tags]

    @staticmethod
    def get_tag_by_name(name: str) -> "Tag | None":
        """根据名称获取标签"""
        return Tag.query.filter_by(name=name).first()

    @staticmethod
    def get_category_choices() -> list:
        """获取标签分类选项"""
        return [
            ("location", "地区标签"),
            ("company_type", "公司类型"),
            ("environment", "环境标签"),
            ("department", "部门标签"),
            ("project", "项目标签"),
            ("virtualization", "虚拟化类型"),
            ("deployment", "部署方式"),
            ("architecture", "架构类型"),
            ("other", "其他标签"),
        ]

    @staticmethod
    def get_color_choices() -> list:
        """获取颜色选项"""
        return [
            ("primary", "蓝色"),
            ("success", "绿色"),
            ("info", "青色"),
            ("warning", "黄色"),
            ("danger", "红色"),
            ("secondary", "灰色"),
            ("dark", "深色"),
            ("light", "浅色"),
        ]

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


# 实例标签关联表
instance_tags = db.Table(
    'instance_tags',
    db.Column('instance_id', db.Integer, db.ForeignKey('instances.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('created_at', db.DateTime(timezone=True), default=now),
)
