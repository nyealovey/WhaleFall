"""Alembic 环境脚本.

负责在命令行执行 `alembic` 时注入 Flask 上下文,并提供在线/离线两种模式的迁移入口.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig
from typing import TYPE_CHECKING, Any

from alembic import context
from flask import current_app

if TYPE_CHECKING:
    from alembic.runtime.environment import MigrationContext
    from sqlalchemy.engine import Engine
    from sqlalchemy.sql.schema import MetaData

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_engine() -> Engine:
    """获取当前 Flask 应用绑定的 SQLAlchemy Engine.

    函数首先尝试兼容 Flask-SQLAlchemy < 3 的 get_engine 写法,若失败则回退到
    v3 及以上版本提供的 engine 属性.

    Returns:
        Engine: 供 Alembic 使用的 SQLAlchemy Engine 实例.

    Raises:
        RuntimeError: 当 Flask 应用尚未初始化迁移扩展时可能抛出.

    """
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions["migrate"].db.engine


def get_engine_url() -> str:
    """生成数据库连接串,供 Alembic 配置使用.

    优先使用 SQLAlchemy 2.0 的 render_as_string 保留密码,否则退化为 str(url).

    Returns:
        str: 经过百分号转义的数据库连接串.

    Raises:
        RuntimeError: 当获取 Engine 失败时抛出.

    """
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            "%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())
target_db = current_app.extensions["migrate"].db

def get_metadata() -> MetaData:
    """获取迁移需要的元数据对象.

    当项目维护多个 metadata 时,优先选择默认键 None 对应的 metadata.

    Returns:
        MetaData: 用于自动生成迁移脚本的 SQLAlchemy MetaData.

    Raises:
        RuntimeError: 当 Flask 应用未正确初始化数据库扩展时抛出.

    """
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline() -> None:
    """以离线模式运行数据库迁移.

    离线模式仅依赖数据库 URL,不需要真实 Engine/DBAPI,适合在 CI 中生成 SQL.

    Returns:
        None: 迁移命令执行完毕即可返回.

    Raises:
        SQLAlchemyError: 当 Alembic 配置失败时抛出.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以在线模式运行数据库迁移.

    在线模式会创建 Engine 并获取连接,适合直接对数据库执行变更.

    Returns:
        None: 迁移执行完成后返回.

    Raises:
        SQLAlchemyError: 当数据库连接或迁移执行失败时抛出.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(
        _context: MigrationContext,
        _revision: tuple[str, str] | str | None,
        directives: list[Any],
    ) -> None:
        """在自动迁移期间剔除空的升级操作."""
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    conf_args = current_app.extensions["migrate"].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
