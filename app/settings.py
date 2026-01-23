"""鲸落 - 统一配置读取与校验.

目标:
- 将环境变量读取、默认值、校验集中到单一入口,避免散落在各模块中重复解析.
- `create_app(settings=...)` 只消费 Settings,不再直接读取环境变量.

说明:
- Settings 使用 `pydantic-settings` 的 `BaseSettings` 从环境变量与本地 `.env`(可选)读取配置.
- 生产环境默认更严格: 缺失关键密钥/连接串会直接抛出 ValueError.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import socket
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants.validation_limits import BCRYPT_LOG_ROUNDS_MIN, HOUR_OF_DAY_MAX, HOUR_OF_DAY_MIN

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_ENVIRONMENT = "development"
APP_VERSION = "1.4.0"
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
DEFAULT_REMEMBER_COOKIE_DURATION_SECONDS = 7 * 24 * 3600

DEFAULT_CORS_ORIGINS = ("http://localhost:5001", "http://127.0.0.1:5001")

DEFAULT_DATABASE_SIZE_RETENTION_MONTHS = 12
DEFAULT_AGGREGATION_ENABLED = True
DEFAULT_AGGREGATION_HOUR = 4
DEFAULT_COLLECT_DB_SIZE_ENABLED = True
DEFAULT_DB_SIZE_COLLECTION_INTERVAL_HOURS = 24
DEFAULT_DB_SIZE_COLLECTION_TIMEOUT_SECONDS = 300

DEFAULT_PROXY_FIX_TRUSTED_IPS = ("127.0.0.1", "::1")

DEFAULT_API_V1_DOCS_ENABLED = True
DEFAULT_ENABLE_SCHEDULER = True

_BUILD_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _resolve_last_build_hash() -> str | None:
    """读取仓库/镜像内的 `.last_build_hash`，用于注入可观测字段.

    说明：
    - `.last_build_hash` 在本仓库已存在，通常由构建流程写入。
    - 环境变量 `BUILD_HASH` 优先级更高；该文件仅作为“缺省填充”，避免生产日志缺少部署维度。
    """
    candidate = PROJECT_ROOT / ".last_build_hash"
    if not candidate.exists():
        return None
    try:
        content = candidate.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content:
        return None
    if not _BUILD_HASH_PATTERN.match(content):
        return None
    return content


def _parse_csv(raw: str) -> tuple[str, ...]:
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _is_valid_fernet_key(value: str) -> bool:
    try:
        Fernet(value.encode())
    except ValueError:
        return False
    return True


def _resolve_sqlite_fallback_url() -> str:
    db_path = _resolve_sqlite_fallback_path()
    return f"sqlite:///{db_path.absolute()}"


def _resolve_sqlite_fallback_path() -> Path:
    return PROJECT_ROOT / "userdata" / "whalefall_dev.db"


class Settings(BaseSettings):
    """应用运行时设置集合."""

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        # 允许使用 env.example 里的 CSV（如 "a,b,c"），由 field_validator 做解析。
        # 同时兼容 JSON 数组格式（如 '["a","b"]'）。
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
        # 对 tuple/list/dict 等字段，pydantic-settings 默认会尝试把环境变量当 JSON 解析。
        # 本仓库约定 `CORS_ORIGINS` / `PROXY_FIX_TRUSTED_IPS` 使用逗号分隔（见 env.example / 文档）。
        # 因此关闭自动 JSON 解码，统一交由 schema validator 解析。
        enable_decoding=False,
    )

    environment: str = Field(default=DEFAULT_ENVIRONMENT, validation_alias="FLASK_ENV")
    debug: bool = Field(default=False, validation_alias="FLASK_DEBUG")

    app_name: str = Field(default="鲸落", validation_alias="APP_NAME")
    app_version: str = APP_VERSION

    # Observability / Deployment characteristics
    # 说明：
    # - 这些字段用于日志的“环境特征维度”，便于关联发布与定位节点问题。
    # - 值来源：优先环境变量；若缺失可使用仓库内 `.last_build_hash`/hostname 作为缺省填充。
    build_hash: str = Field(default="", validation_alias="BUILD_HASH")
    deploy_region: str = Field(default="", validation_alias="DEPLOY_REGION")
    # 注意：业务域中已大量使用 `instance_id` 表示“数据库实例 ID”，因此运行时实例标识使用更明确的命名避免冲突。
    runtime_instance_id: str = Field(default="", validation_alias="RUNTIME_INSTANCE_ID")

    secret_key: str = Field(default="", validation_alias="SECRET_KEY")
    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    password_encryption_key: str = Field(default="", validation_alias="PASSWORD_ENCRYPTION_KEY")

    jwt_access_token_expires_seconds: int = Field(
        default=DEFAULT_JWT_ACCESS_TOKEN_EXPIRES_SECONDS,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRES",
    )
    jwt_refresh_token_expires_seconds: int = Field(
        default=DEFAULT_JWT_REFRESH_TOKEN_EXPIRES_SECONDS,
        validation_alias="JWT_REFRESH_TOKEN_EXPIRES",
    )

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    db_connection_timeout_seconds: int = Field(
        default=DEFAULT_DB_CONNECTION_TIMEOUT_SECONDS,
        validation_alias="DB_CONNECTION_TIMEOUT",
    )
    db_max_connections: int = Field(default=DEFAULT_DB_MAX_CONNECTIONS, validation_alias="DB_MAX_CONNECTIONS")

    oracle_client_lib_dir: str | None = Field(default=None, validation_alias="ORACLE_CLIENT_LIB_DIR")
    oracle_home: str | None = Field(default=None, validation_alias="ORACLE_HOME")

    cache_type: str = Field(default=DEFAULT_CACHE_TYPE, validation_alias="CACHE_TYPE")
    cache_redis_url: str | None = Field(default=None, validation_alias="CACHE_REDIS_URL")
    cache_default_timeout_seconds: int = Field(
        default=DEFAULT_CACHE_DEFAULT_TIMEOUT_SECONDS,
        validation_alias="CACHE_DEFAULT_TIMEOUT",
    )
    cache_default_ttl_seconds: int = Field(
        default=DEFAULT_CACHE_DEFAULT_TTL_SECONDS, validation_alias="CACHE_DEFAULT_TTL"
    )
    cache_rule_evaluation_ttl_seconds: int = Field(
        default=DEFAULT_CACHE_RULE_EVALUATION_TTL_SECONDS,
        validation_alias="CACHE_RULE_EVALUATION_TTL",
    )
    cache_rule_ttl_seconds: int = Field(default=DEFAULT_CACHE_RULE_TTL_SECONDS, validation_alias="CACHE_RULE_TTL")
    cache_account_ttl_seconds: int = Field(
        default=DEFAULT_CACHE_ACCOUNT_TTL_SECONDS, validation_alias="CACHE_ACCOUNT_TTL"
    )

    bcrypt_log_rounds: int = Field(default=DEFAULT_BCRYPT_LOG_ROUNDS, validation_alias="BCRYPT_LOG_ROUNDS")
    force_https: bool = Field(default=False, validation_alias="FORCE_HTTPS")

    proxy_fix_x_for: int = Field(default=0, validation_alias="PROXY_FIX_X_FOR")
    proxy_fix_x_proto: int = Field(default=0, validation_alias="PROXY_FIX_X_PROTO")
    proxy_fix_x_host: int = Field(default=0, validation_alias="PROXY_FIX_X_HOST")
    proxy_fix_x_port: int = Field(default=0, validation_alias="PROXY_FIX_X_PORT")
    proxy_fix_x_prefix: int = Field(default=0, validation_alias="PROXY_FIX_X_PREFIX")
    proxy_fix_trusted_ips: tuple[str, ...] = Field(
        default=DEFAULT_PROXY_FIX_TRUSTED_IPS,
        validation_alias="PROXY_FIX_TRUSTED_IPS",
    )

    max_content_length_bytes: int = Field(
        default=DEFAULT_MAX_CONTENT_LENGTH_BYTES, validation_alias="MAX_CONTENT_LENGTH"
    )

    log_level: str = Field(default=DEFAULT_LOG_LEVEL, validation_alias="LOG_LEVEL")
    log_file: str = Field(default=DEFAULT_LOG_FILE, validation_alias="LOG_FILE")
    log_max_size_bytes: int = Field(default=DEFAULT_LOG_MAX_SIZE_BYTES, validation_alias="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=DEFAULT_LOG_BACKUP_COUNT, validation_alias="LOG_BACKUP_COUNT")

    session_lifetime_seconds: int = Field(
        default=DEFAULT_SESSION_LIFETIME_SECONDS,
        validation_alias="PERMANENT_SESSION_LIFETIME",
    )
    remember_cookie_duration_seconds: int = Field(
        default=DEFAULT_REMEMBER_COOKIE_DURATION_SECONDS,
        validation_alias="REMEMBER_COOKIE_DURATION",
    )

    login_rate_limit: int = Field(default=10, validation_alias="LOGIN_RATE_LIMIT")
    login_rate_window_seconds: int = Field(default=60, validation_alias="LOGIN_RATE_WINDOW")

    cors_origins: tuple[str, ...] = Field(default=DEFAULT_CORS_ORIGINS, validation_alias="CORS_ORIGINS")

    api_v1_docs_enabled: bool = Field(default=DEFAULT_API_V1_DOCS_ENABLED, validation_alias="API_V1_DOCS_ENABLED")

    enable_scheduler: bool = Field(default=DEFAULT_ENABLE_SCHEDULER, validation_alias="ENABLE_SCHEDULER")
    server_software: str = Field(default="", validation_alias="SERVER_SOFTWARE")
    flask_run_from_cli: bool = Field(default=False, validation_alias="FLASK_RUN_FROM_CLI")
    werkzeug_run_main: bool = Field(default=False, validation_alias="WERKZEUG_RUN_MAIN")

    aggregation_enabled: bool = Field(default=DEFAULT_AGGREGATION_ENABLED, validation_alias="AGGREGATION_ENABLED")
    aggregation_hour: int = Field(default=DEFAULT_AGGREGATION_HOUR, validation_alias="AGGREGATION_HOUR")
    collect_db_size_enabled: bool = Field(
        default=DEFAULT_COLLECT_DB_SIZE_ENABLED, validation_alias="COLLECT_DB_SIZE_ENABLED"
    )
    database_size_retention_months: int = Field(
        default=DEFAULT_DATABASE_SIZE_RETENTION_MONTHS,
        validation_alias="DATABASE_SIZE_RETENTION_MONTHS",
    )
    db_size_collection_interval_hours: int = Field(
        default=DEFAULT_DB_SIZE_COLLECTION_INTERVAL_HOURS,
        validation_alias="DB_SIZE_COLLECTION_INTERVAL",
    )
    db_size_collection_timeout_seconds: int = Field(
        default=DEFAULT_DB_SIZE_COLLECTION_TIMEOUT_SECONDS,
        validation_alias="DB_SIZE_COLLECTION_TIMEOUT",
    )

    @field_validator("cache_type")
    @classmethod
    def _normalize_cache_type(cls, value: str) -> str:
        return value.lower()

    @field_validator("oracle_client_lib_dir", "oracle_home", "cache_redis_url", mode="before")
    @classmethod
    def _strip_blank_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("cors_origins", "proxy_fix_trusted_ips", mode="before")
    @classmethod
    def _parse_csv_values(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ()
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("must be a JSON array or a comma-separated string")
                return tuple(item for item in (str(v).strip() for v in parsed) if item)
            return _parse_csv(raw)
        if isinstance(value, (list, tuple, set)):
            items = []
            for item in value:
                text = str(item).strip()
                if text:
                    items.append(text)
            return tuple(items)
        return value

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
            "BUILD_HASH": self.build_hash,
            "DEPLOY_REGION": self.deploy_region,
            "RUNTIME_INSTANCE_ID": self.runtime_instance_id,
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
            "REMEMBER_COOKIE_DURATION": self.remember_cookie_duration_seconds,
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
        """从环境变量加载 Settings 并执行必要校验."""
        load_dotenv(dotenv_path=DOTENV_PATH if DOTENV_PATH.exists() else None, override=False)
        return cls()

    @model_validator(mode="after")
    def _apply_migrations_and_validate(self) -> Settings:
        environment_normalized = self.environment.strip().lower()

        debug = self._resolve_debug(environment_normalized)
        self._ensure_secret_keys(debug)
        self._ensure_password_encryption_key(debug, environment_normalized)
        self._apply_observability_defaults(environment_normalized)
        self._ensure_database_url(environment_normalized)
        self._normalize_cache_redis_url(environment_normalized)
        self._apply_proxy_fix_defaults(environment_normalized)
        self._apply_api_docs_default(environment_normalized)

        self._validate()
        return self

    def _apply_observability_defaults(self, environment_normalized: str) -> None:
        """为日志系统填充部署维度缺省值（不引入强制门禁）."""
        if "build_hash" not in self.model_fields_set:
            resolved = _resolve_last_build_hash()
            object.__setattr__(self, "build_hash", resolved or "unknown")

        if "deploy_region" not in self.model_fields_set:
            default_region = "local" if environment_normalized in {"development", "testing", "test"} else "unknown"
            object.__setattr__(self, "deploy_region", default_region)

        if "runtime_instance_id" not in self.model_fields_set:
            hostname = socket.gethostname().strip() or "unknown"
            object.__setattr__(self, "runtime_instance_id", hostname)

    def _resolve_debug(self, environment_normalized: str) -> bool:
        if "debug" in self.model_fields_set:
            return bool(self.debug)
        debug = environment_normalized != "production"
        object.__setattr__(self, "debug", debug)
        return debug

    def _ensure_secret_keys(self, debug: bool) -> None:
        if not self.secret_key:
            if not debug:
                raise ValueError("SECRET_KEY environment variable must be set in production")
            object.__setattr__(self, "secret_key", secrets.token_urlsafe(32))
            logger.warning("⚠️  开发环境使用随机生成的SECRET_KEY,生产环境请设置环境变量")

        if not self.jwt_secret_key:
            if not debug:
                raise ValueError("JWT_SECRET_KEY environment variable must be set in production")
            object.__setattr__(self, "jwt_secret_key", secrets.token_urlsafe(32))
            logger.warning("⚠️  开发环境使用随机生成的JWT_SECRET_KEY,生产环境请设置环境变量")

    def _ensure_password_encryption_key(self, debug: bool, environment_normalized: str) -> None:
        if self.password_encryption_key:
            return
        if environment_normalized == "production":
            return

        generated = Fernet.generate_key().decode()
        object.__setattr__(self, "password_encryption_key", generated)
        if debug:
            logger.warning("⚠️  未设置 PASSWORD_ENCRYPTION_KEY,将使用临时密钥(重启后无法解密已存储凭据)")
            logger.info(
                '请生成并设置 PASSWORD_ENCRYPTION_KEY(示例: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")'
            )

    def _ensure_database_url(self, environment_normalized: str) -> None:
        if self.database_url:
            return
        if environment_normalized == "production":
            raise ValueError("DATABASE_URL environment variable must be set in production")

        database_url = _resolve_sqlite_fallback_url()
        object.__setattr__(self, "database_url", database_url)
        if environment_normalized not in {"testing", "test"}:
            sqlite_db_file = _resolve_sqlite_fallback_path().name
            logger.warning(
                "⚠️  未设置 DATABASE_URL, 非 production 环境将回退 SQLite "
                "(fallback_sqlite_enabled=true, sqlite_db_file=%s)",
                sqlite_db_file,
            )

    def _normalize_cache_redis_url(self, environment_normalized: str) -> None:
        cache_type = self.cache_type
        cache_redis_url = self.cache_redis_url

        if cache_type != "redis":
            if cache_redis_url is not None:
                object.__setattr__(self, "cache_redis_url", None)
            return

        if cache_redis_url:
            return
        if environment_normalized == "production":
            raise ValueError("CACHE_REDIS_URL must be set when CACHE_TYPE=redis in production")
        object.__setattr__(self, "cache_redis_url", DEFAULT_CACHE_REDIS_URL)

    def _apply_proxy_fix_defaults(self, environment_normalized: str) -> None:
        default_x = 1 if environment_normalized == "production" else 0
        if "proxy_fix_x_for" not in self.model_fields_set:
            object.__setattr__(self, "proxy_fix_x_for", default_x)
        if "proxy_fix_x_proto" not in self.model_fields_set:
            object.__setattr__(self, "proxy_fix_x_proto", default_x)

    def _apply_api_docs_default(self, environment_normalized: str) -> None:
        if environment_normalized != "production":
            return
        if "api_v1_docs_enabled" in self.model_fields_set:
            return
        object.__setattr__(self, "api_v1_docs_enabled", False)

    def _validate(self) -> None:
        """执行跨字段校验,统一抛出可读的 ValueError."""
        errors: list[str] = []
        password_encryption_key = self.password_encryption_key.strip()
        password_encryption_key_present = bool(password_encryption_key)
        checks: list[tuple[str, bool]] = [
            ("DB_CONNECTION_TIMEOUT 必须为正整数", self.db_connection_timeout_seconds <= 0),
            ("DB_MAX_CONNECTIONS 必须为正整数", self.db_max_connections <= 0),
            (f"BCRYPT_LOG_ROUNDS 不应小于 {BCRYPT_LOG_ROUNDS_MIN}", self.bcrypt_log_rounds < BCRYPT_LOG_ROUNDS_MIN),
            ("PERMANENT_SESSION_LIFETIME 必须为正整数(秒)", self.session_lifetime_seconds <= 0),
            ("REMEMBER_COOKIE_DURATION 必须为正整数(秒)", self.remember_cookie_duration_seconds <= 0),
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
            (
                f"AGGREGATION_HOUR 必须为 {HOUR_OF_DAY_MIN}-{HOUR_OF_DAY_MAX} 的整数",
                self.aggregation_hour < HOUR_OF_DAY_MIN or self.aggregation_hour > HOUR_OF_DAY_MAX,
            ),
            ("DB_SIZE_COLLECTION_INTERVAL 必须为正整数(小时)", self.db_size_collection_interval_hours <= 0),
            ("DB_SIZE_COLLECTION_TIMEOUT 必须为正整数(秒)", self.db_size_collection_timeout_seconds <= 0),
        ]
        for message, condition in checks:
            if condition:
                errors.append(message)

        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"配置校验失败: {joined}")
