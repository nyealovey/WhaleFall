"""Accounts 域路由包.

集中导出账户相关蓝图,方便在应用入口统一注册路由. 对外只暴露
accounts_* 名称的蓝图集合,其余模块保持内部实现细节.
"""

from flask import Blueprint

from app.routes.accounts.classification_statistics import accounts_classification_statistics_bp
from app.routes.accounts.classifications import accounts_classifications_bp
from app.routes.accounts.ledgers import accounts_ledgers_bp
from app.routes.accounts.statistics import accounts_statistics_bp

EXPORTED_BLUEPRINTS: tuple[Blueprint, ...] = (
    accounts_classifications_bp,
    accounts_classification_statistics_bp,
    accounts_ledgers_bp,
    accounts_statistics_bp,
)

__all__ = [
    "EXPORTED_BLUEPRINTS",
    "accounts_classification_statistics_bp",
    "accounts_classifications_bp",
    "accounts_ledgers_bp",
    "accounts_statistics_bp",
]
