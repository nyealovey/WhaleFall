"""账户分类相关常量.

说明:
- 该模块用于 Service / Forms 共享选项常量,避免 Service 依赖 Forms 层定义.
- 表单层如需使用,请直接从本模块导入或通过 forms/definitions 的 re-export 导入.
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
