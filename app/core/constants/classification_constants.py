"""账户分类相关常量.

说明:
- 该模块用于 Service 与 API 共享选项常量,避免跨层反向依赖.
- 页面渲染如需注入选项,应由对应 route/service 读取本模块并传入模板.
"""

RISK_LEVEL_OPTIONS = [
    {"value": 1, "label": "1级(最高)"},
    {"value": 2, "label": "2级"},
    {"value": 3, "label": "3级"},
    {"value": 4, "label": "4级(默认)"},
    {"value": 5, "label": "5级"},
    {"value": 6, "label": "6级(最低)"},
]

ICON_OPTIONS = [
    {"value": "fa-crown", "label": "皇冠"},
    {"value": "fa-shield-alt", "label": "盾牌"},
    {"value": "fa-exclamation-triangle", "label": "警告"},
    {"value": "fa-user", "label": "用户"},
    {"value": "fa-eye", "label": "眼睛"},
    {"value": "fa-tag", "label": "标签"},
]

OPERATOR_OPTIONS = [
    {"value": "OR", "label": "OR (任一条件满足)"},
    {"value": "AND", "label": "AND (全部条件满足)"},
]
