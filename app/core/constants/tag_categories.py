"""标签分类常量.

说明:
- 将标签分类选项从 model 中抽离,避免在非数据访问场景引入 `app.models.*` 依赖.
- 该列表用于 UI 下拉选项与分类标签展示.
"""

TAG_CATEGORY_CHOICES: list[tuple[str, str]] = [
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

__all__ = ["TAG_CATEGORY_CHOICES"]

