"""鲸落 - Flask 应用初始化.

基于Flask的DBA数据库管理Web应用.
"""

import logging
from datetime import datetime
from functools import lru_cache
from importlib import import_module
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Union

from flask import Blueprint, Flask, jsonify, request
from flask.typing import ResponseReturnValue
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.constants import HttpHeaders
from app.scheduler import init_scheduler
from app.services.cache_service import init_cache_service
from app.settings import Settings
from app.types.extensions import WhaleFallFlask, WhaleFallLoginManager
from app.utils.cache_utils import init_cache_manager
from app.utils.rate_limiter import init_rate_limiter
from app.utils.response_utils import unified_error_response
from app.utils.structlog_config import (
    ErrorContext,
    configure_structlog,
    enhanced_error_handler,
    get_system_logger,
)
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.models.user import User

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
jwt = JWTManager()
bcrypt = Bcrypt()
login_manager: WhaleFallLoginManager = WhaleFallLoginManager()
cors = CORS()
csrf = CSRFProtect()

# 记录应用启动时间
app_start_time = time_utils.now_china()


@lru_cache(maxsize=1)
def get_user_model() -> type["User"]:
    """延迟加载 User 模型,避免循环导入."""
    return import_module("app.models.user").User


def create_app(
    *,
    init_scheduler_on_start: bool = True,
    settings: Settings | None = None,
) -> WhaleFallFlask:
    """创建Flask应用实例.

    Args:
        init_scheduler_on_start: 是否在创建应用时初始化调度器
        settings: 可选的配置对象,用于测试或多环境启动.

    Returns:
        WhaleFallFlask: Flask应用实例

    """
    resolved_settings = settings or Settings.load()
    app = WhaleFallFlask(__name__)

    # 配置应用
    configure_app(app, resolved_settings)

    # 配置会话安全
    configure_security(app, resolved_settings)

    # 初始化扩展
    initialize_extensions(app, resolved_settings)

    # 注册蓝图
    configure_blueprints(app)

    # 配置日志
    configure_logging(app)

    # 配置统一日志系统
    configure_structlog(app)

    # 设置全局日志级别
    log_level_name = str(app.config.get("LOG_LEVEL", "INFO"))
    logging.getLogger().setLevel(getattr(logging, log_level_name, logging.INFO))

    # 注册增强的错误处理器
    app.enhanced_error_handler = enhanced_error_handler

    # 注册全局错误处理器
    @app.errorhandler(Exception)
    def handle_global_exception(error: Exception) -> ResponseReturnValue:
        """全局错误处理."""
        payload, status_code = unified_error_response(error, context=ErrorContext(error, request))
        return jsonify(payload), status_code

    # 性能监控已移除

    # 配置模板过滤器
    configure_template_filters(app)

    if init_scheduler_on_start:
        try:
            init_scheduler(app)
        except Exception:
            # 调度器初始化失败不影响应用启动
            scheduler_logger = get_system_logger()
            scheduler_logger.exception("调度器初始化失败,应用将继续启动")

    return app


def configure_app(app: Flask, settings: Settings) -> None:
    """写入 Settings 提供的配置并注册基础钩子.

    Args:
        app: Flask 应用实例.
        settings: 统一配置对象,包含环境变量解析、默认值与校验结果.

    Returns:
        None: 写入 `app.config` 后返回.

    """
    app.config.from_mapping(settings.to_flask_config())
    app.config.setdefault("APPLICATION_ROOT", "/")
    _register_protocol_detector(app)


def _register_protocol_detector(app: Flask) -> None:
    """注册请求协议检测钩子,适配代理或直连模式.

    Args:
        app: Flask 应用实例.

    Returns:
        None: 钩子注册到 app.before_request 后返回.

    """

    @app.before_request
    def detect_protocol() -> None:
        """动态检测请求协议."""
        if request.headers.get(HttpHeaders.X_FORWARDED_PROTO) == "https":
            app.config["PREFERRED_URL_SCHEME"] = "https"
            return

        if request.is_secure or request.headers.get(HttpHeaders.X_FORWARDED_SSL) == "on":
            app.config["PREFERRED_URL_SCHEME"] = "https"


def configure_security(app: Flask, settings: Settings) -> None:
    """配置会话安全参数与 Cookie 选项.

    Args:
        app: Flask 应用实例.
        settings: 统一配置对象,提供会话超时等参数.

    Returns:
        None: 安全相关配置写入后返回.

    """
    app.config["PERMANENT_SESSION_LIFETIME"] = settings.session_lifetime_seconds
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_NAME"] = "whalefall_session"
    app.config["SESSION_TIMEOUT"] = settings.session_lifetime_seconds


def initialize_extensions(app: Flask, settings: Settings) -> None:
    """初始化数据库、缓存、登录等 Flask 扩展.

    Args:
        app: Flask 应用实例.
        settings: 统一配置对象,用于扩展初始化参数注入.

    Returns:
        None: 所有扩展完成初始化后返回.

    """
    # 初始化数据库
    db.init_app(app)
    migrate.init_app(app, db)

    # 初始化缓存
    cache.init_app(app)

    # 初始化缓存工具与缓存服务
    init_cache_manager(cache)
    init_cache_service(
        cache,
        default_ttl=settings.cache_default_ttl_seconds,
        rule_evaluation_ttl=settings.cache_rule_evaluation_ttl_seconds,
        rule_ttl=settings.cache_rule_ttl_seconds,
        account_ttl=settings.cache_account_ttl_seconds,
    )

    # 初始化CSRF保护
    csrf.init_app(app)

    # 初始化JWT
    jwt.init_app(app)

    # 初始化密码加密
    bcrypt.init_app(app)

    # 初始化登录管理
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"
    login_manager.login_message_category = "info"

    # 会话安全配置
    login_manager.session_protection = "basic"  # 基础会话保护
    login_manager.remember_cookie_duration = settings.session_lifetime_seconds  # 记住我功能过期时间
    login_manager.remember_cookie_secure = not app.debug  # 生产环境使用HTTPS
    login_manager.remember_cookie_httponly = True  # 防止XSS攻击

    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id: str) -> "User | None":
        user_model = get_user_model()
        return user_model.query.get(int(user_id))

    # 初始化CORS
    allowed_origins = list(settings.cors_origins)
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [HttpHeaders.CONTENT_TYPE, HttpHeaders.AUTHORIZATION, HttpHeaders.X_CSRF_TOKEN],
                "supports_credentials": True,
            },
        },
    )

    init_rate_limiter(cache)


def configure_blueprints(app: Flask) -> None:
    """注册所有蓝图以暴露路由.

    Args:
        app: Flask 应用实例.

    Returns:
        None: 蓝图全部注册后返回.

    """
    blueprint_specs: list[tuple[str, str, str | None]] = [
        ("app.routes.main", "main_bp", None),
        ("app.routes.auth", "auth_bp", "/auth"),
        ("app.routes.common", "common_bp", "/common"),
        ("app.routes.dashboard", "dashboard_bp", "/dashboard"),
        ("app.routes.health", "health_bp", "/health"),
        ("app.routes.cache", "cache_bp", "/cache"),
        ("app.routes.instances.manage", "instances_bp", "/instances"),
        ("app.routes.instances.detail", "instances_detail_bp", None),
        ("app.routes.credentials", "credentials_bp", "/credentials"),
        ("app.routes.accounts.statistics", "accounts_statistics_bp", "/accounts"),
        ("app.routes.accounts.classifications", "accounts_classifications_bp", None),
        ("app.routes.accounts.sync", "accounts_sync_bp", "/accounts/sync"),
        ("app.routes.accounts.ledgers", "accounts_ledgers_bp", "/accounts"),
        ("app.routes.tags.manage", "tags_bp", "/tags"),
        ("app.routes.tags.bulk", "tags_bulk_bp", "/tags/bulk"),
        ("app.routes.history.logs", "history_logs_bp", "/history/logs"),
        ("app.routes.history.sessions", "history_sessions_bp", "/history/sessions"),
        ("app.routes.capacity.aggregations", "capacity_aggregations_bp", "/capacity"),
        ("app.routes.capacity.databases", "capacity_databases_bp", "/capacity"),
        ("app.routes.capacity.instances", "capacity_instances_bp", "/capacity"),
        ("app.routes.databases.ledgers", "databases_ledgers_bp", "/databases"),
        ("app.routes.databases.capacity_sync", "databases_capacity_bp", "/databases"),
        ("app.routes.partition", "partition_bp", "/partition"),
        ("app.routes.connections", "connections_bp", "/connections"),
        ("app.routes.instances.batch", "instances_batch_bp", None),
        ("app.routes.users", "users_bp", "/users"),
        ("app.routes.scheduler", "scheduler_bp", "/scheduler"),
        ("app.routes.files", "files_bp", "/files"),
    ]

    blueprints: list[tuple[Blueprint, str | None]] = []
    for module_path, attr_name, prefix in blueprint_specs:
        module = import_module(module_path)
        blueprint = getattr(module, attr_name)
        blueprints.append((blueprint, prefix))

    for blueprint, prefix in blueprints:
        if prefix:
            app.register_blueprint(blueprint, url_prefix=prefix)
        else:
            app.register_blueprint(blueprint)


def configure_logging(app: Flask) -> None:
    """配置日志系统与文件处理器.

    Args:
        app: Flask 应用实例.

    Returns:
        None: 日志处理器挂载完毕后返回.

    """
    if not app.debug and not app.testing:
        # 创建日志目录
        log_path = Path(app.config["LOG_FILE"])
        log_dir = log_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置文件日志处理器
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=app.config["LOG_MAX_SIZE"],
            backupCount=app.config["LOG_BACKUP_COUNT"],
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"),
        )
        file_handler.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.addHandler(file_handler)

        app.logger.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.info("鲸落应用启动")


def configure_error_handlers(app: Flask) -> None:
    """配置错误处理器(保留占位,统一错误处理中使用).

    Args:
        app: Flask 应用实例.

    Returns:
        None: 当前实现不做额外操作.

    """


def configure_template_filters(app: Flask) -> None:
    """注册时间与日期相关的模板过滤器.

    Args:
        app: Flask 应用实例.

    Returns:
        None: 过滤器注册后返回.

    """

    @app.template_filter("china_time")
    def china_time_filter(dt: str | datetime, format_str: str = "%H:%M:%S") -> str:
        """东八区时间格式化过滤器."""
        return time_utils.format_china_time(dt, format_str)

    @app.template_filter("china_date")
    def china_date_filter(dt: str | datetime) -> str:
        """东八区日期格式化过滤器."""
        return time_utils.format_china_time(dt, "%Y-%m-%d")

    @app.template_filter("china_datetime")
    def china_datetime_filter(dt: str | datetime) -> str:
        """东八区日期时间格式化过滤器."""
        return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")

    @app.template_filter("relative_time")
    def relative_time_filter(dt: str | datetime) -> str:
        """相对时间过滤器."""
        return time_utils.get_relative_time(dt)

    @app.template_filter("is_today")
    def is_today_filter(dt: Union[str, "datetime"]) -> bool:
        """判断是否为今天."""
        return time_utils.is_today(dt)

    @app.template_filter("smart_time")
    def smart_time_filter(dt: Union[str, "datetime"]) -> str:
        """智能时间显示过滤器."""
        if time_utils.is_today(dt):
            return time_utils.format_china_time(dt, "%H:%M:%S")
        return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")


from app.models import (  # noqa: F401, E402
    credential,
    database_size_aggregation,
    database_size_stat,
    database_type_config,
    instance,
    instance_size_aggregation,
    instance_size_stat,
    user,
)
