"""鲸落 - 凭据模型."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, TypedDict, Unpack

from app import bcrypt, db
from app.utils.password_crypto_utils import get_password_manager
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    class CredentialOrmFields(TypedDict, total=False):
        """凭据 ORM 字段映射.

        说明 SQLAlchemy 反序列化或构造函数在 kwargs 中可用的字段集合.

        """

        id: int
        name: str
        credential_type: str
        db_type: str | None
        username: str
        password: str
        description: str | None
        instance_ids: list[int] | None
        category_id: int | None
        is_active: bool
        created_at: Any
        updated_at: Any
        deleted_at: Any

MIN_MASK_LENGTH = 8
MASK_VISIBLE_TAIL = 4


@dataclass(slots=True)
class CredentialCreateParams:
    """凭据初始化参数载体."""

    name: str
    credential_type: str
    username: str
    password: str
    db_type: str | None = None
    instance_ids: list[int] | None = None
    category_id: int | None = None
    description: str | None = None


class Credential(db.Model):
    """凭据模型.

    存储数据库连接凭据,支持密码加密存储.

    Attributes:
        id: 凭据主键.
        name: 凭据名称,唯一.
        credential_type: 凭据类型(database、ssh、windows等).
        db_type: 数据库类型,可选.
        username: 用户名.
        password: 加密后的密码.
        description: 描述信息.
        instance_ids: 关联的实例ID列表.
        category_id: 分类ID.
        is_active: 是否激活.
        created_at: 创建时间.
        updated_at: 更新时间.
        deleted_at: 删除时间.

    """

    __tablename__ = "credentials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    credential_type = db.Column(db.String(50), nullable=False, index=True)
    db_type = db.Column(db.String(50), nullable=True, index=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instance_ids = db.Column(db.JSON, nullable=True)
    category_id = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __init__(
        self,
        params: CredentialCreateParams | None = None,
        **orm_fields: Unpack[CredentialOrmFields],
    ) -> None:
        """初始化凭据并处理密码加密.

        Args:
            params: 结构化的初始化参数,常用于创建流程.
            **orm_fields: SQLAlchemy 反序列化或测试场景写入的原始字段.

        """
        filtered_fields = self._filter_model_fields(orm_fields)
        raw_password = filtered_fields.pop("password", None)
        super().__init__(**filtered_fields)
        if params is None:
            if isinstance(raw_password, str):
                self.set_password(raw_password)
            return

        self.name = params.name
        self.credential_type = params.credential_type
        self.username = params.username
        self.set_password(params.password)
        self.db_type = params.db_type
        self.instance_ids = list(params.instance_ids) if params.instance_ids else []
        self.category_id = params.category_id
        self.description = params.description

    def set_password(self, password: str) -> None:
        """设置密码(加密存储).

        使用加密管理器对密码进行加密后存储.

        Args:
            password: 原始明文密码.

        Returns:
            None: 无返回值,方法执行完成即表示密码已加密存储.

        """
        # 使用新的加密方式存储密码
        self.password = get_password_manager().encrypt_password(password)

    @classmethod
    def _filter_model_fields(cls, payload: Mapping[str, object]) -> dict[str, object]:
        """过滤模型定义字段,避免解包未知键."""
        allowed_keys = {
            "id",
            "name",
            "credential_type",
            "db_type",
            "username",
            "password",
            "description",
            "instance_ids",
            "category_id",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        return {key: value for key, value in payload.items() if key in allowed_keys}

    def check_password(self, password: str) -> bool:
        """验证密码.

        支持多种密码格式:bcrypt 哈希(旧格式)、加密格式和明文.

        Args:
            password: 待验证的原始密码.

        Returns:
            密码正确返回 True,否则返回 False.

        """
        # 旧版本凭据使用 bcrypt 哈希,需要调用 bcrypt 校验
        if self.password.startswith("$2b$"):
            return bcrypt.check_password_hash(self.password, password)

        # 加密格式统一走密码管理器解密再比较
        if get_password_manager().is_encrypted(self.password):
            decrypted_password = get_password_manager().decrypt_password(self.password)
            return decrypted_password == password

        # NOTE: 明文密码兜底处理,仅用于兼容历史数据
        return self.password == password

    def get_password_masked(self) -> str:
        """获取掩码密码.

        Returns:
            str: 掩码后的密码

        """
        password_length = len(self.password)
        if password_length > MIN_MASK_LENGTH:
            masked_length = max(password_length - MASK_VISIBLE_TAIL, 0)
            return "*" * masked_length + self.password[-MASK_VISIBLE_TAIL:]
        return "*" * len(self.password)

    def get_plain_password(self) -> str:
        """获取原始密码(用于数据库连接).

        解密存储的密码并返回明文.对于旧格式的 bcrypt 哈希,
        尝试从环境变量获取默认密码.

        Returns:
            解密后的原始密码,失败时返回空字符串.

        """
        # 旧格式( bcrypt 哈希 )无法直接解密,需通过环境变量提供默认密码
        if self.password.startswith("$2b$"):
            env_key = f"DEFAULT_{(self.db_type or '').upper()}_PASSWORD"
            default_password = os.getenv(env_key)
            if default_password:
                return default_password
            system_logger = get_system_logger()
            system_logger.warning(
                "未设置默认数据库密码环境变量,无法解密旧格式凭据",
                module="credential_model",
                env_key=env_key,
                db_type=self.db_type,
            )
            return ""

        # 正常加密格式直接解密返回
        if get_password_manager().is_encrypted(self.password):
            return get_password_manager().decrypt_password(self.password)

        # 明文存储(历史遗留)直接回传
        return self.password

    def to_dict(self, *, include_password: bool = False) -> dict:
        """转换为字典.

        Args:
            include_password: 是否包含密码

        Returns:
            dict: 凭据信息字典

        """
        data = {
            "id": self.id,
            "name": self.name,
            "credential_type": self.credential_type,
            "db_type": self.db_type,
            "username": self.username,
            "instance_ids": self.instance_ids,
            "category_id": self.category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_password:
            data["password"] = self.password
        else:
            data["password"] = self.get_password_masked()

        return data

    def __repr__(self) -> str:
        """返回模型的可读字符串表示.

        Returns:
            str: 便于调试的凭据概览信息.

        """
        return f"<Credential {self.name}>"

    if TYPE_CHECKING:
        id: Any
        name: Any
        credential_type: Any
        db_type: Any
        username: Any
        password: Any
        description: Any
        instance_ids: Any
        category_id: Any
        is_active: Any
        created_at: Any
        updated_at: Any
        deleted_at: Any
