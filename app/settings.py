"""鲸落 - 统一配置读取与校验.

目标:
- 将环境变量读取、默认值、校验集中到单一入口,避免散落在各模块中重复解析.
- `create_app(settings=...)` 只消费 Settings,不再直接 `os.getenv`.

说明:
- Settings 会在 `load()` 时调用 `python-dotenv` 的 `load_dotenv()` 以支持本地 `.env`.
- 生产环境默认更严格: 缺失关键密钥/连接串会直接抛出 ValueError.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_ENVIRONMENT = "development"
APP_VERSION = "1.3.6"
DEFAULT_JWT_ACCESS_TOKEN_EXPIRES_SECONDS = 3600
DEFAULT_JWT_REFRESH_TOKEN_EXPIRES_SECONDS = 30 * 24 * 3600

DEFAULT_DB_CONNECTION_TIMEOUT_SECONDS = 30
DEFAULT_DB_MAX_CONNECTIONS = 20
DEFAULT_SQLALCHEMY_POOL_RECYCLE_SECONDS = 300
DEFAULT_SQLALCHEMY_MAX_OVERFLOW = 10

DEFAULT_CACHE_TYPE = "simple"
DEFAULT_CACHE_DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_CACHE_DEFAULT_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_CACHE_RULE_EVALUATION_TTL_SECONDS = 24 * 3600
DEFAULT_CACHE_RULE_TTL_SECONDS = 2 * 3600
DEFAULT_CACHE_ACCOUNT_TTL_SECONDS = 3600
DEFAULT_CACHE_REDIS_URL = "redis://localhost:6379/0"

DEFAULT_BCRYPT_LOG_ROUNDS = 12

DEFAULT_MAX_CONTENT_LENGTH_BYTES = 16 * 1024 * 1024

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "userdata/logs/app.log"
DEFAULT_LOG_MAX_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 5

DEFAULT_SESSION_LIFETIME_SECONDS = 3600

DEFAULT_CORS_ORIGINS = ("http://localhost:5001", "http://127.0.0.1:5001")

DEFAULT_DATABASE_SIZE_RETENTION_MONTHS = 12
DEFAULT_AGGREGATION_ENABLED = True
DEFAULT_AGGREGATION_HOUR = 4
DEFAULT_COLLECT_DB_SIZE_ENABLED = True
DEFAULT_DB_SIZE_COLLECTION_INTERVAL_HOURS = 24
DEFAULT_DB_SIZE_COLLECTION_TIMEOUT_SECONDS = 300

DEFAULT_PROXY_FIX_TRUSTED_IPS = ("127.0.0.1", "::1")

DEFAULT_API_V1_DOCS_ENABLED = True


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"无法解析布尔值: {raw!r}")


def _parse_int(raw: str | None, *, default: int, name: str) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - 防御性
        raise ValueError(f"{name} 必须是整数,当前值为 {raw!r}") from exc


def _parse_csv(raw: str | None, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _is_valid_fernet_key(value: str) -> bool:
    try:
        Fernet(value.encode())
    except ValueError:
        return False
    return True


def _resolve_sqlite_fallback_url() -> str:
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "userdata" / "whalefall_dev.db"
    return f"sqlite:///{db_path.absolute()}"


def _bootstrap_oracle_instant_client_environment() -> None:
    """兼容 macOS 本地 Oracle Instant Client 的 DYLD_LIBRARY_PATH.

    仅在该环境变量存在且目录可用时做一次性补全.
    """
    oracle_instant_client_path = os.getenv("DYLD_LIBRARY_PATH")
    if not oracle_instant_client_path:
        return
    instant_client_dir = Path(oracle_instant_client_path)
    if not instant_client_dir.exists():
        return
    current_value = os.environ.get("DYLD_LIBRARY_PATH", "")
    if oracle_instant_client_path not in current_value:
        os.environ["DYLD_LIBRARY_PATH"] = f"{oracle_instant_client_path}:{current_value}".rstrip(":")
        logger.info("🔧 已设置Oracle Instant Client环境变量: %s", oracle_instant_client_path)


def _load_environment() -> tuple[str, str, bool]:
    """读取运行环境与 debug 标志.

    Returns:
        tuple: (environment 原始值, environment 归一化值, debug)

    """
    environment = os.environ.get("FLASK_ENV", DEFAULT_ENVIRONMENT)
    normalized = environment.strip().lower()
    debug_default = normalized != "production"
    debug = _parse_bool(os.environ.get("FLASK_DEBUG"), default=debug_default)
    return environment, normalized, debug


def _load_app_identity() -> tuple[str, str]:
    """读取应用名称与版本号."""
    app_name = os.environ.get("APP_NAME", "鲸落")
    return app_name, APP_VERSION


def _load_secret_keys(*, debug: bool) -> tuple[str, str]:
    """读取并生成 SECRET_KEY / JWT_SECRET_KEY."""
    secret_key = os.environ.get("SECRET_KEY") or ""
    jwt_secret_key = os.environ.get("JWT_SECRET_KEY") or ""

    if not secret_key:
        if debug:
            secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️  开发环境使用随机生成的SECRET_KEY,生产环境请设置环境变量")
        else:
            raise ValueError("SECRET_KEY environment variable must be set in production")

    if not jwt_secret_key:
        if debug:
            jwt_secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️  开发环境使用随机生成的JWT_SECRET_KEY,生产环境请设置环境变量")
        else:
            raise ValueError("JWT_SECRET_KEY environment variable must be set in production")

    return secret_key, jwt_secret_key


def _load_jwt_expiration_seconds() -> tuple[int, int]:
    """读取 JWT 访问/刷新令牌有效期(秒)."""
    access_seconds = _parse_int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES"),
        default=DEFAULT_JWT_ACCESS_TOKEN_EXPIRES_SECONDS,
        name="JWT_ACCESS_TOKEN_EXPIRES",
    )

    refresh_raw = os.environ.get("JWT_REFRESH_TOKEN_EXPIRES") or os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_SECONDS")
    refresh_seconds = _parse_int(
        refresh_raw,
        default=DEFAULT_JWT_REFRESH_TOKEN_EXPIRES_SECONDS,
        name="JWT_REFRESH_TOKEN_EXPIRES",
    )
    return access_seconds, refresh_seconds


def _load_database_settings(environment_normalized: str) -> tuple[str, int, int]:
    """读取主库连接串与连接池参数."""
    database_url_raw = os.environ.get("DATABASE_URL")
    if environment_normalized == "production" and not database_url_raw:
        raise ValueError("DATABASE_URL environment variable must be set in production")

    database_url = database_url_raw or _resolve_sqlite_fallback_url()
    connection_timeout_seconds = _parse_int(
        os.environ.get("DB_CONNECTION_TIMEOUT"),
        default=DEFAULT_DB_CONNECTION_TIMEOUT_SECONDS,
        name="DB_CONNECTION_TIMEOUT",
    )
    max_connections = _parse_int(
        os.environ.get("DB_MAX_CONNECTIONS"),
        default=DEFAULT_DB_MAX_CONNECTIONS,
        name="DB_MAX_CONNECTIONS",
    )
    return database_url, connection_timeout_seconds, max_connections


def _load_cache_settings(environment_normalized: str) -> tuple[str, str | None, int, int, int, int, int]:
    """读取缓存配置与业务缓存 TTL."""
    cache_type = os.environ.get("CACHE_TYPE", DEFAULT_CACHE_TYPE).strip().lower()
    cache_default_timeout_seconds = _parse_int(
        os.environ.get("CACHE_DEFAULT_TIMEOUT"),
        default=DEFAULT_CACHE_DEFAULT_TIMEOUT_SECONDS,
        name="CACHE_DEFAULT_TIMEOUT",
    )

    cache_redis_url_raw = os.environ.get("CACHE_REDIS_URL")
    cache_redis_url: str | None = None
    if cache_type == "redis":
        if cache_redis_url_raw:
            cache_redis_url = cache_redis_url_raw
        elif environment_normalized != "production":
            cache_redis_url = DEFAULT_CACHE_REDIS_URL
        else:
            raise ValueError("CACHE_REDIS_URL must be set when CACHE_TYPE=redis in production")

    cache_default_ttl_seconds = _parse_int(
        os.environ.get("CACHE_DEFAULT_TTL"),
        default=DEFAULT_CACHE_DEFAULT_TTL_SECONDS,
        name="CACHE_DEFAULT_TTL",
    )
    cache_rule_evaluation_ttl_seconds = _parse_int(
        os.environ.get("CACHE_RULE_EVALUATION_TTL"),
        default=DEFAULT_CACHE_RULE_EVALUATION_TTL_SECONDS,
        name="CACHE_RULE_EVALUATION_TTL",
    )
    cache_rule_ttl_seconds = _parse_int(
        os.environ.get("CACHE_RULE_TTL"),
        default=DEFAULT_CACHE_RULE_TTL_SECONDS,
        name="CACHE_RULE_TTL",
    )
    cache_account_ttl_seconds = _parse_int(
        os.environ.get("CACHE_ACCOUNT_TTL"),
        default=DEFAULT_CACHE_ACCOUNT_TTL_SECONDS,
        name="CACHE_ACCOUNT_TTL",
    )
    return (
        cache_type,
        cache_redis_url,
        cache_default_timeout_seconds,
        cache_default_ttl_seconds,
        cache_rule_evaluation_ttl_seconds,
        cache_rule_ttl_seconds,
        cache_account_ttl_seconds,
    )


def _load_web_settings() -> tuple[int, bool, int, str, str, int, int, int, int, int, tuple[str, ...]]:
    """读取 Web/日志/会话等基础配置."""
    bcrypt_log_rounds = _parse_int(
        os.environ.get("BCRYPT_LOG_ROUNDS"),
        default=DEFAULT_BCRYPT_LOG_ROUNDS,
        name="BCRYPT_LOG_ROUNDS",
    )
    force_https = _parse_bool(os.environ.get("FORCE_HTTPS"), default=False)
    max_content_length_bytes = _parse_int(
        os.environ.get("MAX_CONTENT_LENGTH"),
        default=DEFAULT_MAX_CONTENT_LENGTH_BYTES,
        name="MAX_CONTENT_LENGTH",
    )

    log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    log_file = os.environ.get("LOG_FILE", DEFAULT_LOG_FILE)
    log_max_size_bytes = _parse_int(
        os.environ.get("LOG_MAX_SIZE"),
        default=DEFAULT_LOG_MAX_SIZE_BYTES,
        name="LOG_MAX_SIZE",
    )
    log_backup_count = _parse_int(
        os.environ.get("LOG_BACKUP_COUNT"),
        default=DEFAULT_LOG_BACKUP_COUNT,
        name="LOG_BACKUP_COUNT",
    )

    session_lifetime_seconds = _parse_int(
        os.environ.get("PERMANENT_SESSION_LIFETIME"),
        default=DEFAULT_SESSION_LIFETIME_SECONDS,
        name="PERMANENT_SESSION_LIFETIME",
    )
    login_rate_limit = _parse_int(
        os.environ.get("LOGIN_RATE_LIMIT"),
        default=10,
        name="LOGIN_RATE_LIMIT",
    )
    login_rate_window_seconds = _parse_int(
        os.environ.get("LOGIN_RATE_WINDOW"),
        default=60,
        name="LOGIN_RATE_WINDOW",
    )
    cors_origins = _parse_csv(os.environ.get("CORS_ORIGINS"), default=DEFAULT_CORS_ORIGINS)

    return (
        bcrypt_log_rounds,
        force_https,
        max_content_length_bytes,
        log_level,
        log_file,
        log_max_size_bytes,
        log_backup_count,
        session_lifetime_seconds,
        login_rate_limit,
        login_rate_window_seconds,
        cors_origins,
    )


def _load_proxy_fix_settings(environment_normalized: str) -> tuple[int, int, int, int, int, tuple[str, ...]]:
    """读取反向代理头部解析(ProxyFix)相关配置.

    说明:
    - `ProxyFix` 的信任层数参数必须与上游代理链一致,否则会导致 `remote_addr` 等信息解析错误.
    - 默认策略: 生产环境启用 `x_for/x_proto=1` 以适配内置 Nginx 反代; 其他环境默认关闭.

    Args:
        environment_normalized: 归一化后的环境名称(如 production/development).

    Returns:
        tuple: (x_for, x_proto, x_host, x_port, x_prefix, trusted_ips)

    """
    default_x = 1 if environment_normalized == "production" else 0
    proxy_fix_x_for = _parse_int(
        os.environ.get("PROXY_FIX_X_FOR"),
        default=default_x,
        name="PROXY_FIX_X_FOR",
    )
    proxy_fix_x_proto = _parse_int(
        os.environ.get("PROXY_FIX_X_PROTO"),
        default=default_x,
        name="PROXY_FIX_X_PROTO",
    )
    proxy_fix_x_host = _parse_int(
        os.environ.get("PROXY_FIX_X_HOST"),
        default=0,
        name="PROXY_FIX_X_HOST",
    )
    proxy_fix_x_port = _parse_int(
        os.environ.get("PROXY_FIX_X_PORT"),
        default=0,
        name="PROXY_FIX_X_PORT",
    )
    proxy_fix_x_prefix = _parse_int(
        os.environ.get("PROXY_FIX_X_PREFIX"),
        default=0,
        name="PROXY_FIX_X_PREFIX",
    )
    trusted_ips = _parse_csv(os.environ.get("PROXY_FIX_TRUSTED_IPS"), default=DEFAULT_PROXY_FIX_TRUSTED_IPS)
    return (
        proxy_fix_x_for,
        proxy_fix_x_proto,
        proxy_fix_x_host,
        proxy_fix_x_port,
        proxy_fix_x_prefix,
        trusted_ips,
    )


def _load_feature_flags() -> tuple[bool, int, bool, int, int, int]:
    """读取任务相关功能开关与参数."""
    aggregation_enabled = _parse_bool(os.environ.get("AGGREGATION_ENABLED"), default=DEFAULT_AGGREGATION_ENABLED)
    aggregation_hour = _parse_int(
        os.environ.get("AGGREGATION_HOUR"),
        default=DEFAULT_AGGREGATION_HOUR,
        name="AGGREGATION_HOUR",
    )
    collect_db_size_enabled = _parse_bool(
        os.environ.get("COLLECT_DB_SIZE_ENABLED"),
        default=DEFAULT_COLLECT_DB_SIZE_ENABLED,
    )
    database_size_retention_months = _parse_int(
        os.environ.get("DATABASE_SIZE_RETENTION_MONTHS"),
        default=DEFAULT_DATABASE_SIZE_RETENTION_MONTHS,
        name="DATABASE_SIZE_RETENTION_MONTHS",
    )
    db_size_collection_interval_hours = _parse_int(
        os.environ.get("DB_SIZE_COLLECTION_INTERVAL"),
        default=DEFAULT_DB_SIZE_COLLECTION_INTERVAL_HOURS,
        name="DB_SIZE_COLLECTION_INTERVAL",
    )
    db_size_collection_timeout_seconds = _parse_int(
        os.environ.get("DB_SIZE_COLLECTION_TIMEOUT"),
        default=DEFAULT_DB_SIZE_COLLECTION_TIMEOUT_SECONDS,
        name="DB_SIZE_COLLECTION_TIMEOUT",
    )
    return (
        aggregation_enabled,
        aggregation_hour,
        collect_db_size_enabled,
        database_size_retention_months,
        db_size_collection_interval_hours,
        db_size_collection_timeout_seconds,
    )


def _load_api_settings(environment_normalized: str) -> bool:
    """读取 RestX/OpenAPI 相关开关.

    Phase 4 策略:
    - `/api/v1/**` 始终启用
    - 生产环境默认关闭 Swagger UI,仅保留 OpenAPI JSON 导出能力
    """
    docs_default = DEFAULT_API_V1_DOCS_ENABLED
    if environment_normalized == "production":
        docs_default = False
    return _parse_bool(os.environ.get("API_V1_DOCS_ENABLED"), default=docs_default)


@dataclass(frozen=True, slots=True)
class Settings:
    """应用运行时设置集合."""

    environment: str
    debug: bool

    app_name: str
    app_version: str

    secret_key: str
    jwt_secret_key: str

    jwt_access_token_expires_seconds: int
    jwt_refresh_token_expires_seconds: int

    database_url: str
    db_connection_timeout_seconds: int
    db_max_connections: int

    cache_type: str
    cache_redis_url: str | None
    cache_default_timeout_seconds: int
    cache_default_ttl_seconds: int
    cache_rule_evaluation_ttl_seconds: int
    cache_rule_ttl_seconds: int
    cache_account_ttl_seconds: int

    bcrypt_log_rounds: int
    force_https: bool
    proxy_fix_x_for: int
    proxy_fix_x_proto: int
    proxy_fix_x_host: int
    proxy_fix_x_port: int
    proxy_fix_x_prefix: int
    proxy_fix_trusted_ips: tuple[str, ...]

    max_content_length_bytes: int

    log_level: str
    log_file: str
    log_max_size_bytes: int
    log_backup_count: int

    session_lifetime_seconds: int
    login_rate_limit: int
    login_rate_window_seconds: int

    cors_origins: tuple[str, ...]

    api_v1_docs_enabled: bool

    aggregation_enabled: bool
    aggregation_hour: int
    collect_db_size_enabled: bool
    database_size_retention_months: int
    db_size_collection_interval_hours: int
    db_size_collection_timeout_seconds: int

    @property
    def is_production(self) -> bool:
        """当前是否为生产环境."""
        return self.environment.strip().lower() == "production"

    @property
    def preferred_url_scheme(self) -> str:
        """构造绝对 URL 时优先使用的 scheme."""
        return "https" if self.force_https else "http"

    @property
    def sqlalchemy_engine_options(self) -> dict[str, object]:
        """生成 SQLAlchemy Engine 配置选项."""
        if self.database_url.startswith("sqlite"):
            return {"pool_pre_ping": True, "connect_args": {"check_same_thread": False}}
        return {
            "pool_pre_ping": True,
            "pool_recycle": DEFAULT_SQLALCHEMY_POOL_RECYCLE_SECONDS,
            "pool_timeout": self.db_connection_timeout_seconds,
            "max_overflow": DEFAULT_SQLALCHEMY_MAX_OVERFLOW,
            "pool_size": self.db_max_connections,
            "echo": bool(self.debug),
        }

    def to_flask_config(self) -> dict[str, object]:
        """转换为 Flask app.config 可写入的配置字典."""
        payload: dict[str, object] = {
            "ENV": self.environment,
            "DEBUG": self.debug,
            "APP_NAME": self.app_name,
            "APP_VERSION": self.app_version,
            "SECRET_KEY": self.secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "JWT_ACCESS_TOKEN_EXPIRES": self.jwt_access_token_expires_seconds,
            "JWT_REFRESH_TOKEN_EXPIRES": self.jwt_refresh_token_expires_seconds,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": dict(self.sqlalchemy_engine_options),
            "CACHE_TYPE": self.cache_type,
            "CACHE_DEFAULT_TIMEOUT": self.cache_default_timeout_seconds,
            "CACHE_DEFAULT_TTL": self.cache_default_ttl_seconds,
            "CACHE_RULE_EVALUATION_TTL": self.cache_rule_evaluation_ttl_seconds,
            "CACHE_RULE_TTL": self.cache_rule_ttl_seconds,
            "CACHE_ACCOUNT_TTL": self.cache_account_ttl_seconds,
            "BCRYPT_LOG_ROUNDS": self.bcrypt_log_rounds,
            "PREFERRED_URL_SCHEME": self.preferred_url_scheme,
            "PROXY_FIX_X_FOR": self.proxy_fix_x_for,
            "PROXY_FIX_X_PROTO": self.proxy_fix_x_proto,
            "PROXY_FIX_X_HOST": self.proxy_fix_x_host,
            "PROXY_FIX_X_PORT": self.proxy_fix_x_port,
            "PROXY_FIX_X_PREFIX": self.proxy_fix_x_prefix,
            "PROXY_FIX_TRUSTED_IPS": ",".join(self.proxy_fix_trusted_ips),
            "MAX_CONTENT_LENGTH": self.max_content_length_bytes,
            "LOG_LEVEL": self.log_level,
            "LOG_FILE": self.log_file,
            "LOG_MAX_SIZE": self.log_max_size_bytes,
            "LOG_BACKUP_COUNT": self.log_backup_count,
            "PERMANENT_SESSION_LIFETIME": self.session_lifetime_seconds,
            "LOGIN_RATE_LIMIT": self.login_rate_limit,
            "LOGIN_RATE_WINDOW": self.login_rate_window_seconds,
            "CORS_ORIGINS": ",".join(self.cors_origins),
            "API_V1_DOCS_ENABLED": self.api_v1_docs_enabled,
            "AGGREGATION_ENABLED": self.aggregation_enabled,
            "AGGREGATION_HOUR": self.aggregation_hour,
            "COLLECT_DB_SIZE_ENABLED": self.collect_db_size_enabled,
            "DATABASE_SIZE_RETENTION_MONTHS": self.database_size_retention_months,
            "DB_SIZE_COLLECTION_INTERVAL": self.db_size_collection_interval_hours,
            "DB_SIZE_COLLECTION_TIMEOUT": self.db_size_collection_timeout_seconds,
        }
        if self.cache_type == "redis" and self.cache_redis_url:
            payload["CACHE_REDIS_URL"] = self.cache_redis_url
        return payload

    @classmethod
    def load(cls) -> Settings:
        """从环境变量加载设置并执行必要校验.

        Returns:
            Settings: 已解析并校验后的设置对象.

        Raises:
            ValueError: 当生产环境缺失关键配置或配置值非法时抛出.

        """
        load_dotenv()
        _bootstrap_oracle_instant_client_environment()

        environment, environment_normalized, debug = _load_environment()
        app_name, app_version = _load_app_identity()
        secret_key, jwt_secret_key = _load_secret_keys(debug=debug)
        jwt_access_seconds, jwt_refresh_seconds = _load_jwt_expiration_seconds()
        database_url, db_connection_timeout_seconds, db_max_connections = _load_database_settings(
            environment_normalized
        )
        (
            cache_type,
            cache_redis_url,
            cache_default_timeout_seconds,
            cache_default_ttl_seconds,
            cache_rule_evaluation_ttl_seconds,
            cache_rule_ttl_seconds,
            cache_account_ttl_seconds,
        ) = _load_cache_settings(environment_normalized)

        (
            bcrypt_log_rounds,
            force_https,
            max_content_length_bytes,
            log_level,
            log_file,
            log_max_size_bytes,
            log_backup_count,
            session_lifetime_seconds,
            login_rate_limit,
            login_rate_window_seconds,
            cors_origins,
        ) = _load_web_settings()

        (
            proxy_fix_x_for,
            proxy_fix_x_proto,
            proxy_fix_x_host,
            proxy_fix_x_port,
            proxy_fix_x_prefix,
            proxy_fix_trusted_ips,
        ) = _load_proxy_fix_settings(environment_normalized)

        api_v1_docs_enabled = _load_api_settings(environment_normalized)

        (
            aggregation_enabled,
            aggregation_hour,
            collect_db_size_enabled,
            database_size_retention_months,
            db_size_collection_interval_hours,
            db_size_collection_timeout_seconds,
        ) = _load_feature_flags()

        settings = cls(
            environment=environment,
            debug=debug,
            app_name=app_name,
            app_version=app_version,
            secret_key=secret_key,
            jwt_secret_key=jwt_secret_key,
            jwt_access_token_expires_seconds=jwt_access_seconds,
            jwt_refresh_token_expires_seconds=jwt_refresh_seconds,
            database_url=database_url,
            db_connection_timeout_seconds=db_connection_timeout_seconds,
            db_max_connections=db_max_connections,
            cache_type=cache_type,
            cache_redis_url=cache_redis_url,
            cache_default_timeout_seconds=cache_default_timeout_seconds,
            cache_default_ttl_seconds=cache_default_ttl_seconds,
            cache_rule_evaluation_ttl_seconds=cache_rule_evaluation_ttl_seconds,
            cache_rule_ttl_seconds=cache_rule_ttl_seconds,
            cache_account_ttl_seconds=cache_account_ttl_seconds,
            bcrypt_log_rounds=bcrypt_log_rounds,
            force_https=force_https,
            proxy_fix_x_for=proxy_fix_x_for,
            proxy_fix_x_proto=proxy_fix_x_proto,
            proxy_fix_x_host=proxy_fix_x_host,
            proxy_fix_x_port=proxy_fix_x_port,
            proxy_fix_x_prefix=proxy_fix_x_prefix,
            proxy_fix_trusted_ips=proxy_fix_trusted_ips,
            max_content_length_bytes=max_content_length_bytes,
            log_level=log_level,
            log_file=log_file,
            log_max_size_bytes=log_max_size_bytes,
            log_backup_count=log_backup_count,
            session_lifetime_seconds=session_lifetime_seconds,
            login_rate_limit=login_rate_limit,
            login_rate_window_seconds=login_rate_window_seconds,
            cors_origins=cors_origins,
            api_v1_docs_enabled=api_v1_docs_enabled,
            aggregation_enabled=aggregation_enabled,
            aggregation_hour=aggregation_hour,
            collect_db_size_enabled=collect_db_size_enabled,
            database_size_retention_months=database_size_retention_months,
            db_size_collection_interval_hours=db_size_collection_interval_hours,
            db_size_collection_timeout_seconds=db_size_collection_timeout_seconds,
        )
        settings._validate()
        return settings

    def _validate(self) -> None:
        """执行跨字段校验,统一抛出可读的 ValueError."""
        errors: list[str] = []
        password_encryption_key = (os.environ.get("PASSWORD_ENCRYPTION_KEY") or "").strip()
        password_encryption_key_present = bool(password_encryption_key)
        checks: list[tuple[str, bool]] = [
            ("DB_CONNECTION_TIMEOUT 必须为正整数", self.db_connection_timeout_seconds <= 0),
            ("DB_MAX_CONNECTIONS 必须为正整数", self.db_max_connections <= 0),
            ("BCRYPT_LOG_ROUNDS 不应小于 4", self.bcrypt_log_rounds < 4),
            ("PERMANENT_SESSION_LIFETIME 必须为正整数(秒)", self.session_lifetime_seconds <= 0),
            ("PROXY_FIX_X_FOR 必须为非负整数", self.proxy_fix_x_for < 0),
            ("PROXY_FIX_X_PROTO 必须为非负整数", self.proxy_fix_x_proto < 0),
            ("PROXY_FIX_X_HOST 必须为非负整数", self.proxy_fix_x_host < 0),
            ("PROXY_FIX_X_PORT 必须为非负整数", self.proxy_fix_x_port < 0),
            ("PROXY_FIX_X_PREFIX 必须为非负整数", self.proxy_fix_x_prefix < 0),
            ("CACHE_TYPE 仅支持 simple/redis", self.cache_type not in {"simple", "redis"}),
            ("CACHE_TYPE=redis 时必须提供 CACHE_REDIS_URL", self.cache_type == "redis" and not self.cache_redis_url),
            (
                "生产环境必须设置 PASSWORD_ENCRYPTION_KEY(用于凭据加/解密)",
                self.is_production and not password_encryption_key_present,
            ),
            (
                "PASSWORD_ENCRYPTION_KEY 格式非法,请先使用 Fernet.generate_key() 生成并设置",
                password_encryption_key_present and not _is_valid_fernet_key(password_encryption_key),
            ),
            ("DATABASE_SIZE_RETENTION_MONTHS 必须为正整数(月)", self.database_size_retention_months <= 0),
            ("AGGREGATION_HOUR 必须为 0-23 的整数", self.aggregation_hour < 0 or self.aggregation_hour > 23),
            ("DB_SIZE_COLLECTION_INTERVAL 必须为正整数(小时)", self.db_size_collection_interval_hours <= 0),
            ("DB_SIZE_COLLECTION_TIMEOUT 必须为正整数(秒)", self.db_size_collection_timeout_seconds <= 0),
        ]
        for message, condition in checks:
            if condition:
                errors.append(message)

        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"配置校验失败: {joined}")
