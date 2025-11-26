"""
鲸落 - 标签模型
"""

from app import db
from app.utils.time_utils import time_utils
from app.constants.colors import ThemeColors


class Tag(db.Model):
    """标签模型。

    用于对实例进行分类和标记，支持多种分类（地区、环境、项目等）。

    Attributes:
        id: 标签主键。
        name: 标签代码（如 wenzhou），唯一。
        display_name: 显示名称（如 温州）。
        category: 标签分类（如 location、environment）。
        color: 标签颜色（如 primary、success）。
        description: 描述信息。
        sort_order: 排序顺序。
        is_active: 是否激活。
        created_at: 创建时间。
        updated_at: 更新时间。
    """

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # 标签分类
    color = db.Column(db.String(20), default="primary", nullable=False)  # 标签颜色
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

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
        """初始化标签。

        Args:
            name: 标签代码（如 wenzhou），必须唯一。
            display_name: 显示名称（如 温州）。
            category: 标签分类（如 location=地区、environment=环境）。
            color: 标签颜色（如 primary=蓝色、success=绿色），默认为 primary。
            description: 描述信息，可选。
            sort_order: 排序顺序，默认为 0。
            is_active: 是否激活，默认为 True。
        """
        self.name = name
        self.display_name = display_name
        self.category = category
        self.color = color
        self.description = description
        self.sort_order = sort_order
        self.is_active = is_active

    @property
    def color_value(self):
        """获取实际颜色值。

        Returns:
            颜色的十六进制值。
        """
        return ThemeColors.get_color_value(self.color)
    
    @property
    def color_name(self):
        """获取颜色名称。

        Returns:
            颜色的中文名称。
        """
        return ThemeColors.get_color_name(self.color)
    
    @property
    def css_class(self):
        """获取 CSS 类名。

        Returns:
            Bootstrap 颜色类名。
        """
        return ThemeColors.get_css_class(self.color)
    
    def to_dict(self) -> dict:
        """转换为字典格式。

        Returns:
            包含标签完整信息的字典。
        """
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "color": self.color,
            "color_value": self.color_value,
            "color_name": self.color_name,
            "css_class": self.css_class,
            "description": self.description,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


    @staticmethod
    def get_active_tags() -> list:
        """获取所有活跃标签。

        Returns:
            按分类、排序顺序和名称排序的活跃标签列表。
        """
        return Tag.query.filter_by(is_active=True).order_by(Tag.category, Tag.sort_order, Tag.name).all()

    @staticmethod
    def get_tags_by_category(category: str) -> list:
        """根据分类获取标签。

        Args:
            category: 标签分类名称。

        Returns:
            指定分类的活跃标签列表。
        """
        return Tag.query.filter_by(category=category, is_active=True).order_by(Tag.sort_order, Tag.name).all()

    @staticmethod
    def get_tag_by_name(name: str) -> "Tag | None":
        """根据名称获取标签。

        Args:
            name: 标签代码。

        Returns:
            匹配的标签对象，不存在时返回 None。
        """
        return Tag.query.filter_by(name=name).first()

    @staticmethod
    def get_category_choices() -> list:
        """获取标签分类选项。

        Returns:
            标签分类的选项列表，每项包含分类代码和显示名称。
        """
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

    def __repr__(self) -> str:
        """返回标签的调试字符串。

        Returns:
            str: 展示标签代码的文本。
        """
        return f"<Tag {self.name}>"


# 实例标签关联表
instance_tags = db.Table(
    'instance_tags',
    db.Column('instance_id', db.Integer, db.ForeignKey('instances.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('created_at', db.DateTime(timezone=True), default=time_utils.now),
)
