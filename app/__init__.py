"""
鲸落 - Flask应用初始化
基于Flask的DBA数据库管理Web应用
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from app.models.user import User

from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.config import Config
from app.constants import HttpHeaders
from app.utils.time_utils import time_utils

# 加载环境变量
load_dotenv()

# 初始化基础日志记录器（在structlog配置之前）
logger = logging.getLogger(__name__)

# 设置Oracle Instant Client环境变量
oracle_instant_client_path = os.getenv("DYLD_LIBRARY_PATH")
if oracle_instant_client_path and os.path.exists(oracle_instant_client_path):
    current_dyld_path = os.environ.get("DYLD_LIBRARY_PATH", "")
    if oracle_instant_client_path not in current_dyld_path:
        os.environ["DYLD_LIBRARY_PATH"] = f"{oracle_instant_client_path}:{current_dyld_path}"
        logger.info(f"🔧 已设置Oracle Instant Client环境变量: {oracle_instant_client_path}")

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
jwt = JWTManager()
bcrypt = Bcrypt()
login_manager = LoginManager()
cors = CORS()
csrf = CSRFProtect()

# 记录应用启动时间
app_start_time = time_utils.now_china()


def create_app(
    config_name: str | None = None,
    *,
    init_scheduler_on_start: bool = True,
) -> Flask:  # noqa: ARG001
    """
    创建Flask应用实例

    Args:
        config_name: 配置名称，默认为None
        init_scheduler_on_start: 是否在创建应用时初始化调度器

    Returns:
        Flask: Flask应用实例
    """
    app = Flask(__name__)

    # 配置应用
    configure_app(app, config_name)

    # 配置会话安全
    configure_session_security(app)

    # 初始化扩展
    initialize_extensions(app)

    # 注册蓝图
    register_blueprints(app)

    # 配置日志
    configure_logging(app)

    # 配置统一日志系统
    from app.utils.structlog_config import configure_structlog

    configure_structlog(app)

    # 设置全局日志级别
    logging.getLogger().setLevel(logging.INFO)

    # 注册增强的错误处理器
    from app.utils.response_utils import unified_error_response
    from app.utils.structlog_config import ErrorContext, enhanced_error_handler

    app.enhanced_error_handler = enhanced_error_handler

    # 注册全局错误处理器
    @app.errorhandler(Exception)
    def handle_global_exception(error: Exception):
        """全局错误处理"""
        from flask import request

        payload, status_code = unified_error_response(error, context=ErrorContext(error, request))
        return jsonify(payload), status_code

    # 性能监控已移除

    # 配置模板过滤器
    configure_template_filters(app)

    if init_scheduler_on_start:
        from app.scheduler import init_scheduler

        try:
            init_scheduler(app)
        except Exception as e:
            # 调度器初始化失败不影响应用启动
            from app.utils.structlog_config import get_system_logger

            scheduler_logger = get_system_logger()
            scheduler_logger.error(f"调度器初始化失败，应用将继续启动: {e}")

    return app


def configure_app(app: Flask, config_name: str | None = None) -> None:  # noqa: ARG001
    """配置 Flask 应用的核心参数。

    Args:
        app: Flask 应用实例。
        config_name: 配置名称，保留以兼容历史接口。

    Returns:
        None: 配置写入 `app.config` 后立即返回。
    """
    # 基础配置
    secret_key = os.getenv("SECRET_KEY")
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        if app.debug:
            # 开发环境使用随机生成的密钥
            import secrets

            secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️  开发环境使用随机生成的SECRET_KEY，生产环境请设置环境变量")
        else:
            error_msg = "SECRET_KEY environment variable must be set in production"
            raise ValueError(error_msg)

    if not jwt_secret_key:
        if app.debug:
            # 开发环境使用随机生成的密钥
            import secrets

            jwt_secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️  开发环境使用随机生成的JWT_SECRET_KEY，生产环境请设置环境变量")
        else:
            error_msg = "JWT_SECRET_KEY environment variable must be set in production"
            raise ValueError(error_msg)

    app.config["SECRET_KEY"] = secret_key
    app.config["JWT_SECRET_KEY"] = jwt_secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 2592000))

    # 数据库配置
    database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not database_url:
        # 默认使用SQLite，使用绝对路径
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        db_path = project_root / "userdata" / "whalefall_dev.db"
        database_url = f"sqlite:///{db_path.absolute()}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 根据数据库类型设置不同的引擎选项
    if database_url.startswith("sqlite"):
        # SQLite配置
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "connect_args": {"check_same_thread": False},
        }
    else:
        # PostgreSQL/MySQL配置
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_timeout": 20,
            "max_overflow": 0,
        }

    # 缓存配置
    cache_type = os.getenv("CACHE_TYPE", "simple")
    app.config["CACHE_TYPE"] = cache_type

    if cache_type == "redis":
        app.config["CACHE_REDIS_URL"] = os.getenv("CACHE_REDIS_URL", "redis://localhost:6379/0")

    app.config["CACHE_DEFAULT_TIMEOUT"] = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 300))

    # 安全配置
    app.config["BCRYPT_LOG_ROUNDS"] = int(os.getenv("BCRYPT_LOG_ROUNDS", 12))

    # URL 配置 - 动态检测协议
    app.config["APPLICATION_ROOT"] = "/"

    # 设置默认 URL 方案
    force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    if force_https:
        app.config["PREFERRED_URL_SCHEME"] = "https"
    else:
        app.config["PREFERRED_URL_SCHEME"] = "http"

    # 动态设置 URL 方案（基于请求头）
    @app.before_request
    def detect_protocol():
        """动态检测请求协议"""
        # 优先检查 X-Forwarded-Proto 头（Nginx 代理设置）
        if request.headers.get(HttpHeaders.X_FORWARDED_PROTO) == "https":
            app.config["PREFERRED_URL_SCHEME"] = "https"
        # 检查 Flask 的 is_secure 属性
        elif request.is_secure:
            app.config["PREFERRED_URL_SCHEME"] = "https"
        # 检查 X-Forwarded-Ssl 头
        elif request.headers.get(HttpHeaders.X_FORWARDED_SSL) == "on":
            app.config["PREFERRED_URL_SCHEME"] = "https"
        # 其他情况保持默认值

    # 文件上传配置
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "userdata/uploads")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16777216))

    # 日志配置
    app.config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
    app.config["LOG_FILE"] = os.getenv("LOG_FILE", "userdata/logs/app.log")
    app.config["LOG_MAX_SIZE"] = int(os.getenv("LOG_MAX_SIZE", 10485760))
    app.config["LOG_BACKUP_COUNT"] = int(os.getenv("LOG_BACKUP_COUNT", 5))

    # 外部数据库配置
    app.config["SQL_SERVER_HOST"] = os.getenv("SQL_SERVER_HOST", "localhost")
    app.config["SQL_SERVER_PORT"] = int(os.getenv("SQL_SERVER_PORT", 1433))
    app.config["SQL_SERVER_USERNAME"] = os.getenv("SQL_SERVER_USERNAME", "sa")
    app.config["SQL_SERVER_PASSWORD"] = os.getenv("SQL_SERVER_PASSWORD", "")

    app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
    app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", 3306))
    app.config["MYSQL_USERNAME"] = os.getenv("MYSQL_USERNAME", "root")
    app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")

    app.config["ORACLE_HOST"] = os.getenv("ORACLE_HOST", "localhost")
    app.config["ORACLE_PORT"] = int(os.getenv("ORACLE_PORT", 1521))
    app.config["ORACLE_SERVICE_NAME"] = os.getenv("ORACLE_SERVICE_NAME", "ORCL")
    app.config["ORACLE_USERNAME"] = os.getenv("ORACLE_USERNAME", "system")
    app.config["ORACLE_PASSWORD"] = os.getenv("ORACLE_PASSWORD", "")


def configure_session_security(app: Flask) -> None:
    """配置会话安全参数与 Cookie 选项。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 安全相关配置写入后返回。
    """
    # 从环境变量读取会话超时时间，默认为1小时
    from app.config import Config
    session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", Config.SESSION_LIFETIME))

    # 会话配置
    app.config["PERMANENT_SESSION_LIFETIME"] = session_lifetime  # 会话超时时间
    app.config["SESSION_COOKIE_SECURE"] = False  # 暂时禁用HTTPS要求，使用HTTP
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # 防止XSS攻击
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF保护

    # 防止会话固定攻击
    app.config["SESSION_COOKIE_NAME"] = "whalefall_session"

    # 会话超时配置
    app.config["SESSION_TIMEOUT"] = session_lifetime  # 会话超时时间


def initialize_extensions(app: Flask) -> None:
    """初始化数据库、缓存、登录等 Flask 扩展。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 所有扩展完成初始化后返回。
    """
    # 初始化数据库
    db.init_app(app)
    migrate.init_app(app, db)

    # 初始化缓存
    cache.init_app(app)

    # 初始化缓存工具与缓存服务
    from app.services.cache_service import init_cache_service
    from app.utils.cache_utils import init_cache_manager

    init_cache_manager(cache)
    init_cache_service(cache)

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
    # 从环境变量读取会话超时时间，默认为1小时
    session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", Config.SESSION_LIFETIME))
    login_manager.remember_cookie_duration = session_lifetime  # 记住我功能过期时间
    login_manager.remember_cookie_secure = not app.debug  # 生产环境使用HTTPS
    login_manager.remember_cookie_httponly = True  # 防止XSS攻击

    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id: str) -> "User | None":
        from app.models.user import User

        return User.query.get(int(user_id))

    # 初始化CORS
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5001,http://127.0.0.1:5001").split(",")
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

    # 初始化CSRF保护
    csrf.init_app(app)

    # 初始化速率限制器（使用Flask-Caching）
    from app.utils.rate_limiter import init_rate_limiter
    init_rate_limiter(cache)



def register_blueprints(app: Flask) -> None:
    """注册所有蓝图以暴露路由。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 蓝图全部注册后返回。
    """
    from app.routes.accounts.classifications import accounts_classifications_bp
    from app.routes.accounts.ledgers import accounts_ledgers_bp
    from app.routes.accounts.statistics import accounts_statistics_bp
    from app.routes.accounts.sync import accounts_sync_bp
    from app.routes.auth import auth_bp
    from app.routes.cache import cache_bp
    from app.routes.capacity.aggregations import capacity_aggregations_bp
    from app.routes.capacity.databases import capacity_databases_bp
    from app.routes.capacity.instances import capacity_instances_bp
    from app.routes.common import common_bp
    from app.routes.connections import connections_bp
    from app.routes.credentials import credentials_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.databases.capacity_sync import databases_capacity_bp
    from app.routes.databases.ledgers import databases_ledgers_bp
    from app.routes.files import files_bp
    from app.routes.health import health_bp
    from app.routes.history.logs import history_logs_bp, logs_bp
    from app.routes.history.sessions import history_sessions_bp
    from app.routes.instances.batch import instances_batch_bp
    from app.routes.instances.detail import instances_detail_bp
    from app.routes.instances.manage import instances_bp
    from app.routes.main import main_bp
    from app.routes.partition import partition_bp
    from app.routes.scheduler import scheduler_bp
    from app.routes.tags.bulk import tags_bulk_bp
    from app.routes.tags.manage import tags_bp
    from app.routes.users import users_bp

    blueprints: list[tuple[Blueprint, str | None]] = [
        (main_bp, None),
        (auth_bp, "/auth"),
        (common_bp, "/common"),
        (dashboard_bp, "/dashboard"),
        (health_bp, "/health"),
        (cache_bp, "/cache"),
        (instances_bp, "/instances"),
        (instances_detail_bp, None),
        (credentials_bp, "/credentials"),
        (accounts_statistics_bp, "/accounts"),
        (accounts_classifications_bp, None),
        (accounts_sync_bp, "/accounts"),
        (accounts_ledgers_bp, "/accounts"),
        (tags_bp, "/tags"),
        (tags_bulk_bp, "/tags/bulk"),
        (history_logs_bp, "/history/logs"),
        (logs_bp, "/logs"),
        (history_sessions_bp, "/history/sessions"),
        (capacity_aggregations_bp, "/capacity"),
        (capacity_databases_bp, "/capacity"),
        (capacity_instances_bp, "/capacity"),
        (databases_ledgers_bp, "/databases"),
        (databases_capacity_bp, "/databases"),
        (partition_bp, "/partition"),
        (connections_bp, "/connections"),
        (instances_batch_bp, None),
        (users_bp, "/users"),
        (scheduler_bp, "/scheduler"),
        (files_bp, "/files"),
    ]

    for blueprint, prefix in blueprints:
        if prefix:
            app.register_blueprint(blueprint, url_prefix=prefix)
        else:
            app.register_blueprint(blueprint)


def configure_logging(app: Flask) -> None:
    """配置日志系统与文件处理器。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 日志处理器挂载完毕后返回。
    """
    if not app.debug and not app.testing:
        # 创建日志目录
        log_dir = os.path.dirname(app.config["LOG_FILE"])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 配置文件日志处理器
        file_handler = RotatingFileHandler(
            app.config["LOG_FILE"],
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
    """配置错误处理器（保留占位，统一错误处理中使用）。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 当前实现不做额外操作。
    """


def configure_template_filters(app: Flask) -> None:
    """注册时间与日期相关的模板过滤器。

    Args:
        app: Flask 应用实例。

    Returns:
        None: 过滤器注册后返回。
    """
    from app.utils.time_utils import time_utils

    @app.template_filter("china_time")
    def china_time_filter(dt: str | datetime, format_str: str = "%H:%M:%S") -> str:
        """东八区时间格式化过滤器"""
        return time_utils.format_china_time(dt, format_str)

    @app.template_filter("china_date")
    def china_date_filter(dt: str | datetime) -> str:
        """东八区日期格式化过滤器"""
        return time_utils.format_china_time(dt, "%Y-%m-%d")

    @app.template_filter("china_datetime")
    def china_datetime_filter(dt: str | datetime) -> str:
        """东八区日期时间格式化过滤器"""
        return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")

    @app.template_filter("relative_time")
    def relative_time_filter(dt: str | datetime) -> str:
        """相对时间过滤器"""
        return time_utils.get_relative_time(dt)

    @app.template_filter("is_today")
    def is_today_filter(dt: Union[str, "datetime"]) -> bool:
        """判断是否为今天"""
        return time_utils.is_today(dt)

    @app.template_filter("smart_time")
    def smart_time_filter(dt: Union[str, "datetime"]) -> str:
        """智能时间显示过滤器"""
        if time_utils.is_today(dt):
            return time_utils.format_china_time(dt, "%H:%M:%S")
        return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")


# 导入模型（确保模型被注册）
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
