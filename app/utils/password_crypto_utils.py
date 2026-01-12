"""密码管理工具.

用于安全地存储和获取数据库密码.
"""

from __future__ import annotations

import base64
import binascii

from cryptography.fernet import Fernet, InvalidToken

from app.utils.structlog_config import get_system_logger


class PasswordManager:
    """密码管理器.

    使用 Fernet 对称加密算法安全地加密和解密数据库密码.
    密钥由 Settings 统一解析并在应用启动时注入.

    Attributes:
        key: 加密密钥(bytes).
        cipher: Fernet 加密器实例.

    Example:
        >>> manager = PasswordManager()
        >>> encrypted = manager.encrypt_password("my_password")
        >>> decrypted = manager.decrypt_password(encrypted)
        >>> decrypted == "my_password"
        True

    """

    def __init__(self, *, key: bytes) -> None:
        """初始化密码加密工具.

        Args:
            key: Fernet key(bytes).
        """
        self.key = key
        self.cipher = Fernet(self.key)

    def encrypt_password(self, password: str) -> str:
        """加密密码.

        Args:
            password: 原始密码

        Returns:
            str: 加密后的密码

        """
        if not password:
            return ""

        encrypted = self.cipher.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码.

        Args:
            encrypted_password: 加密后的密码

        Returns:
            str: 原始密码

        """
        if not encrypted_password:
            return ""

        try:
            encrypted = base64.b64decode(encrypted_password.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except (InvalidToken, binascii.Error, ValueError) as decryption_error:
            system_logger = get_system_logger()
            system_logger.exception(
                "密码解密失败",
                module="password_manager",
                exception=decryption_error,
            )
            return ""

    def is_encrypted(self, password: str) -> bool:
        """检查密码是否已加密.

        Args:
            password: 密码字符串

        Returns:
            bool: 是否已加密

        """
        if not password:
            return False

        # 检查是否是bcrypt哈希
        if password.startswith("$2b$"):
            return False

        # 检查是否是我们的加密格式
        try:
            base64.b64decode(password.encode())
        except (binascii.Error, ValueError):
            return False
        else:
            return True


_PASSWORD_MANAGER: PasswordManager | None = None


def init_password_manager(*, key: str) -> None:
    """初始化全局 PasswordManager(由 create_app 调用).

    Args:
        key: Fernet key 字符串.
    """
    global _PASSWORD_MANAGER
    _PASSWORD_MANAGER = PasswordManager(key=key.encode())


def get_password_manager() -> PasswordManager:
    """获取密码管理器实例(延迟初始化).

    Returns:
        PasswordManager: 全局复用的管理器实例.

    """
    if _PASSWORD_MANAGER is None:
        raise RuntimeError("PasswordManager 未初始化,请先在 create_app 阶段调用 init_password_manager()")
    return _PASSWORD_MANAGER
