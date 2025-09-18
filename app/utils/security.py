"""
泰摸鱼吧 - 安全工具模块
"""

import hmac
import html
import re
from typing import Any


def sanitize_input(value: Any) -> str:
    """
    清理用户输入，防止XSS攻击

    Args:
        value: 输入值

    Returns:
        str: 清理后的字符串
    """
    if value is None:
        return ""

    # 转换为字符串
    value = str(value)

    # HTML转义
    value = html.escape(value)

    # 移除危险字符
    dangerous_chars = ["<script", "</script", "javascript:", "onload=", "onerror="]
    for char in dangerous_chars:
        value = value.replace(char, "")

    return value.strip()


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> str | None:
    """
    验证必填字段

    Args:
        data: 表单数据
        required_fields: 必填字段列表

    Returns:
        Optional[str]: 错误信息，None表示验证通过
    """
    for field in required_fields:
        if not data.get(field) or not str(data.get(field)).strip():
            return f"{field}不能为空"
    return None


def validate_username(username: str) -> str | None:
    """
    验证用户名格式

    Args:
        username: 用户名

    Returns:
        Optional[str]: 错误信息，None表示验证通过
    """
    if not username:
        return "用户名不能为空"

    if len(username) < 3:
        return "用户名长度至少3个字符"

    if len(username) > 50:
        return "用户名长度不能超过50个字符"

    # 只允许字母、数字、下划线、连字符
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return "用户名只能包含字母、数字、下划线和连字符"

    return None


def validate_password(password: str) -> str | None:
    """
    验证密码强度

    Args:
        password: 密码

    Returns:
        Optional[str]: 错误信息，None表示验证通过
    """
    if not password:
        return "密码不能为空"

    if len(password) < 6:
        return "密码长度至少6个字符"

    if len(password) > 128:
        return "密码长度不能超过128个字符"

    return None


def validate_db_type(db_type: str) -> str | None:
    """
    验证数据库类型

    Args:
        db_type: 数据库类型

    Returns:
        Optional[str]: 错误信息，None表示验证通过
    """
    valid_types = ["mysql", "postgresql", "sqlserver", "oracle", "sqlite"]

    if db_type and db_type.lower() not in valid_types:
        return f"不支持的数据库类型: {db_type}"

    return None


def validate_credential_type(credential_type: str) -> str | None:
    """
    验证凭据类型

    Args:
        credential_type: 凭据类型

    Returns:
        Optional[str]: 错误信息，None表示验证通过
    """
    valid_types = ["database", "ssh", "windows", "api"]

    if credential_type and credential_type.lower() not in valid_types:
        return f"不支持的凭据类型: {credential_type}"

    return None


def sanitize_form_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    清理表单数据

    Args:
        data: 原始表单数据

    Returns:
        Dict[str, Any]: 清理后的数据
    """
    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, (bool, int, float)):
            sanitized[key] = value
        else:
            sanitized[key] = sanitize_input(str(value))

    return sanitized


def check_sql_injection(query: str) -> bool:
    """
    检查SQL注入风险

    Args:
        query: SQL查询语句

    Returns:
        bool: True表示有风险，False表示安全
    """
    dangerous_patterns = [
        r"union\s+select",
        r"drop\s+table",
        r"delete\s+from",
        r"insert\s+into",
        r"update\s+set",
        r"exec\s*\(",
        r"execute\s*\(",
        r"--",
        r"/\*.*\*/",
        r"xp_",
        r"sp_",
    ]

    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in dangerous_patterns)


def generate_csrf_token() -> str:
    """
    生成CSRF令牌

    Returns:
        str: CSRF令牌
    """
    import secrets

    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """
    验证CSRF令牌

    Args:
        token: 提交的令牌
        session_token: 会话中的令牌

    Returns:
        bool: 验证结果
    """
    if not token or not session_token:
        return False

    # 使用hmac.compare_digest进行安全比较
    return hmac.compare_digest(token, session_token)
