"""
泰摸鱼吧 - Flask应用初始化
基于Flask的DBA数据库管理Web应用
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Union
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.constants import SystemConstants

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
from app.utils.time_utils import now_china
app_start_time = now_china()


def create_app(config_name: str | None = None) -> Flask:
    """
    创建Flask应用实例

    Args:
        config_name: 配置名称，默认为None

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
    
    # 设置全局日志级别为INFO，过滤DEBUG日志
    import logging
    from app.utils.debug_log_filter import configure_debug_filter
    
    # 配置DEBUG日志过滤器
    configure_debug_filter()
    
    # 设置全局日志级别
    logging.getLogger().setLevel(logging.INFO)

    # 注册全局错误处理器
    from app.utils.error_handler import register_error_handlers

    register_error_handlers(app)

    # 注册高级错误处理器
    from app.utils.advanced_error_handler import advanced_error_handler

    app.advanced_error_handler = advanced_error_handler


    # 注册高级错误处理器到Flask应用
    @app.errorhandler(Exception)
    def handle_advanced_exception(error: Exception) -> tuple[str, int]:
        """全局高级错误处理"""
        from app.utils.advanced_error_handler import ErrorContext

        context = ErrorContext(error)
        error_response = advanced_error_handler.handle_error(error, context)

        # 根据错误类型返回适当的响应
        status_code = error.code if hasattr(error, "code") else 500

        return jsonify(error_response), status_code

    # 性能监控已移除

    # 配置模板过滤器
    configure_template_filters(app)

    return app


def configure_app(app: Flask, config_name: str | None = None) -> None:
    """
    配置Flask应用

    Args:
        app: Flask应用实例
        config_name: 配置名称
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
        db_path = project_root / "userdata" / "taifish_dev.db"
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
        app.config["CACHE_REDIS_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    app.config["CACHE_DEFAULT_TIMEOUT"] = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 300))

    # 安全配置
    app.config["BCRYPT_LOG_ROUNDS"] = int(os.getenv("BCRYPT_LOG_ROUNDS", 12))

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
    """
    配置会话安全

    Args:
        app: Flask应用实例
    """
    # 会话配置
    app.config["PERMANENT_SESSION_LIFETIME"] = SystemConstants.SESSION_LIFETIME  # 会话1小时过期
    app.config["SESSION_COOKIE_SECURE"] = not app.debug  # 生产环境使用HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # 防止XSS攻击
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF保护

    # 防止会话固定攻击
    app.config["SESSION_COOKIE_NAME"] = "taifish_session"

    # 会话超时配置
    app.config["SESSION_TIMEOUT"] = SystemConstants.SESSION_LIFETIME  # 1小时


def initialize_extensions(app: Flask) -> None:
    """
    初始化Flask扩展

    Args:
        app: Flask应用实例
    """
    # 初始化数据库
    db.init_app(app)
    migrate.init_app(app, db)

    # 初始化缓存
    cache.init_app(app)

    # 缓存管理器已在services/cache_manager.py中初始化

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
    login_manager.remember_cookie_duration = SystemConstants.SESSION_LIFETIME  # 记住我功能1小时过期
    login_manager.remember_cookie_secure = not app.debug  # 生产环境使用HTTPS
    login_manager.remember_cookie_httponly = True  # 防止XSS攻击

    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id: str):
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
                "allow_headers": ["Content-Type", "Authorization", "X-CSRFToken"],
                "supports_credentials": True,
            }
        },
    )

    # 初始化CSRF保护
    csrf.init_app(app)

    # 初始化Redis (用于缓存和速率限制)
    redis_url = app.config.get("CACHE_REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis

        redis_client = redis.from_url(redis_url, decode_responses=True)

        # 初始化速率限制器
        from app.utils.rate_limiter import init_rate_limiter

        init_rate_limiter(redis_client)
        redis_client.ping()
        app.logger.info("Redis连接成功")
    except Exception as e:
        app.logger.warning(f"Redis不可用: {str(e)}")
        redis_client = None

    # 将redis_client添加到应用上下文
    app.redis_client = redis_client


def register_blueprints(app: Flask) -> None:
    """
    注册Flask蓝图

    Args:
        app: Flask应用实例
    """
    # 导入蓝图
    from app.routes.account_classification import account_classification_bp
    from app.routes.account_list import account_list_bp
    from app.routes.account_static import account_static_bp
    from app.routes.account_sync import account_sync_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.cache_management import cache_bp
    from app.routes.credentials import credentials_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.database_types import database_types_bp
    from app.routes.health import health_bp
    from app.routes.instance_accounts import instance_accounts_bp
    from app.routes.instances import instances_bp
    # from app.routes.logs import logs_bp  # 已停用，使用unified_logs替代
    from app.routes.main import main_bp
    from app.routes.unified_logs import unified_logs_bp

    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(instances_bp, url_prefix="/instances")
    app.register_blueprint(instance_accounts_bp, url_prefix="/instance_accounts")
    app.register_blueprint(credentials_bp, url_prefix="/credentials")

    # 新的账户相关蓝图
    app.register_blueprint(account_list_bp, url_prefix="/account-list")
    app.register_blueprint(account_sync_bp, url_prefix="/account-sync")
    app.register_blueprint(account_static_bp, url_prefix="/account-static")
    
    # 缓存管理蓝图
    app.register_blueprint(cache_bp, url_prefix="/cache")

    # 保留旧的accounts_bp，等测试通过后删除
    # app.register_blueprint(accounts_bp, url_prefix="/accounts")

    # app.register_blueprint(logs_bp, url_prefix="/logs")  # 已停用，使用unified_logs替代
    app.register_blueprint(unified_logs_bp)  # unified_logs_bp already has url_prefix="/unified-logs"
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(health_bp, url_prefix="/health")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(account_classification_bp, url_prefix="/account-classification")

    # 注册数据库类型管理蓝图
    app.register_blueprint(database_types_bp)

    # 注册用户管理蓝图
    from app.routes.user_management import user_management_bp

    app.register_blueprint(user_management_bp)

    # 注册定时任务管理蓝图
    from app.routes.scheduler import scheduler_bp

    app.register_blueprint(scheduler_bp)

    # 注册同步会话管理蓝图
    from app.routes.sync_sessions import sync_sessions_bp

    app.register_blueprint(sync_sessions_bp)

    # 初始化定时任务调度器
    from app.scheduler import init_scheduler

    init_scheduler(app)


def configure_logging(app: Flask) -> None:
    """
    配置日志系统

    Args:
        app: Flask应用实例
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
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
        )
        file_handler.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.addHandler(file_handler)

        app.logger.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.info("泰摸鱼吧应用启动")


def configure_error_handlers(app: Flask) -> None:
    """
    配置错误处理器 - 已移除，使用统一的错误处理器
    """


def configure_template_filters(app: Flask) -> None:
    """
    配置模板过滤器

    Args:
        app: Flask应用实例
    """
    from app.utils.time_utils import time_utils

    @app.template_filter("china_time")
    def china_time_filter(dt: Union[str, datetime], format_str: str = "%H:%M:%S") -> str:
        """东八区时间格式化过滤器"""
        return time_utils.format_china_time(dt, format_str)

    @app.template_filter("china_date")
    def china_date_filter(dt: Union[str, datetime]) -> str:
        """东八区日期格式化过滤器"""
        return time_utils.format_china_time(dt, "%Y-%m-%d")

    @app.template_filter("china_datetime")
    def china_datetime_filter(dt: Union[str, datetime]) -> str:
        """东八区日期时间格式化过滤器"""
        return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")

    @app.template_filter("relative_time")
    def relative_time_filter(dt: Union[str, datetime]) -> str:
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
        else:
            return time_utils.format_china_time(dt, "%Y-%m-%d %H:%M:%S")


# 创建应用实例
app = create_app()

# 导入模型（确保模型被注册）
from app.models import (  # noqa: F401; account,  # 已废弃，使用CurrentAccountSyncData
    classification_batch,
    credential,
    database_type_config,
    instance,
    task,
    user,
)

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    host = os.getenv("FLASK_HOST", "127.0.0.1")  # 默认绑定本地接口
    port = int(os.getenv("FLASK_PORT", 8000))
    app.run(debug=debug_mode, host=host, port=port)
