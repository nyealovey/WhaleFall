"""账户分类相关常量.

说明:
- 该模块用于 Service / Forms 共享选项常量,避免 Service 依赖 Forms 层定义.
- 表单层如需使用,请直接从本模块导入或通过 forms/definitions 的 re-export 导入.
"""

RISK_LEVEL_OPTIONS = [
    {"value": "low", "label": "低风险"},
    {"value": "medium", "label": "中风险"},
    {"value": "high", "label": "高风险"},
    {"value": "critical", "label": "极高风险"},
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
