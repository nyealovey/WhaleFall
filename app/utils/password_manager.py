"""
密码管理工具
用于安全地存储和获取数据库密码
"""

import base64
import os

from cryptography.fernet import Fernet


class PasswordManager:
    """密码管理器"""

    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)

    def _get_or_create_key(self):
        """获取或创建加密密钥"""
        key = os.getenv("PASSWORD_ENCRYPTION_KEY")
        if not key:
            # 如果没有设置密钥，生成一个新的
            key = Fernet.generate_key()
            from app.utils.structlog_config import get_system_logger

            system_logger = get_system_logger()
            system_logger.warning("没有设置PASSWORD_ENCRYPTION_KEY环境变量", module="password_manager")
            system_logger.info("生成的临时密钥", module="password_manager", key=key.decode())
            system_logger.info(
                "请设置环境变量",
                module="password_manager",
                env_var=f"export PASSWORD_ENCRYPTION_KEY='{key.decode()}'",
            )
        else:
            key = key.encode()

        return key

    def encrypt_password(self, password: str) -> str:
        """
        加密密码

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
        """
        解密密码

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
        except Exception as e:
            from app.utils.structlog_config import get_system_logger

            system_logger = get_system_logger()
            system_logger.error("密码解密失败", module="password_manager", exception=e)
            return ""

    def is_encrypted(self, password: str) -> bool:
        """
        检查密码是否已加密

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
            return True
        except Exception:
            return False


# 全局密码管理器实例
password_manager = PasswordManager()
