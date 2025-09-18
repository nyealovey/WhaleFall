"""
鲸落 - 输入验证和清理工具
"""

import html
import re
from typing import Any

import bleach
from flask import request


class InputValidator:
    """输入验证器"""

    # 数据库类型白名单
    # 注意：ALLOWED_DB_TYPES 已废弃，现在使用数据库类型配置管理
    # 保留此常量用于向后兼容，但建议使用 get_allowed_db_types() 方法
    ALLOWED_DB_TYPES = ["mysql", "postgresql", "sqlserver", "oracle"]

    # 任务类型白名单
    ALLOWED_TASK_TYPES = ["sync_accounts", "sync_version", "sync_size", "custom"]

    # 用户角色白名单
    ALLOWED_ROLES = ["admin", "user", "viewer"]

    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # JavaScript
        r"javascript:",  # JavaScript协议
        r"vbscript:",  # VBScript协议
        r"on\w+\s*=",  # 事件处理器
        r"<iframe[^>]*>",  # iframe
        r"<object[^>]*>",  # object
        r"<embed[^>]*>",  # embed
        r"<link[^>]*>",  # link
        r"<meta[^>]*>",  # meta
        r"<style[^>]*>",  # style
    ]

    @staticmethod
    def validate_string(
        value: Any,
        min_length: int = 0,
        max_length: int = 255,
        *,
        allow_empty: bool = True,
        pattern: str | None = None,
    ) -> str | None:
        """
        验证字符串输入

        Args:
            value: 输入值
            min_length: 最小长度
            max_length: 最大长度
            allow_empty: 是否允许空值
            pattern: 正则表达式模式

        Returns:
            str: 清理后的字符串，验证失败返回None
        """
        if value is None:
            return None if not allow_empty else ""

        # 转换为字符串
        str_value = str(value).strip()

        # 检查空值
        if not str_value and not allow_empty:
            return None

        # 检查长度
        if len(str_value) < min_length or len(str_value) > max_length:
            return None

        # 检查正则表达式
        if pattern and not re.match(pattern, str_value):
            return None

        # HTML转义
        return html.escape(str_value)

    @staticmethod
    def validate_integer(value: Any, min_val: int | None = None, max_val: int | None = None) -> int | None:
        """
        验证整数输入

        Args:
            value: 输入值
            min_val: 最小值
            max_val: 最大值

        Returns:
            int: 验证后的整数，验证失败返回None
        """
        try:
            int_value = int(value)
            if min_val is not None and int_value < min_val:
                return None
            if max_val is not None and int_value > max_val:
                return None
            return int_value
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_boolean(value: Any) -> bool | None:
        """
        验证布尔值输入

        Args:
            value: 输入值

        Returns:
            bool: 验证后的布尔值，验证失败返回None
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes", "on"]
        if isinstance(value, int):
            return bool(value)
        return None

    @staticmethod
    def validate_email(email: str) -> str | None:
        """
        验证邮箱地址

        Args:
            email: 邮箱地址

        Returns:
            str: 验证后的邮箱，验证失败返回None
        """
        if not email:
            return None

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return None

        return email.lower().strip()

    @staticmethod
    def validate_url(url: str) -> str | None:
        """
        验证URL

        Args:
            url: URL地址

        Returns:
            str: 验证后的URL，验证失败返回None
        """
        if not url:
            return None

        url_pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
        if not re.match(url_pattern, url):
            return None

        return url.strip()

    @staticmethod
    def get_allowed_db_types() -> list[str]:
        """
        获取允许的数据库类型列表（从数据库类型配置中动态获取）

        Returns:
            List[str]: 启用的数据库类型名称列表
        """
        try:
            from app.utils.database_type_utils import DatabaseTypeUtils

            active_types = DatabaseTypeUtils.get_all_active_types()
            return [config.name for config in active_types]
        except Exception:
            # 如果获取失败，回退到硬编码列表
            return InputValidator.ALLOWED_DB_TYPES

    @staticmethod
    def validate_db_type(db_type: str) -> str | None:
        """
        验证数据库类型

        Args:
            db_type: 数据库类型

        Returns:
            str: 验证后的数据库类型，验证失败返回None
        """
        if not db_type:
            return None

        # 使用动态获取的数据库类型列表
        allowed_types = InputValidator.get_allowed_db_types()
        db_type_lower = db_type.lower()

        if db_type_lower not in allowed_types:
            return None
        return db_type_lower

    @staticmethod
    def validate_task_type(task_type: str) -> str | None:
        """
        验证任务类型

        Args:
            task_type: 任务类型

        Returns:
            str: 验证后的任务类型，验证失败返回None
        """
        if not task_type or task_type.lower() not in InputValidator.ALLOWED_TASK_TYPES:
            return None
        return task_type.lower()

    @staticmethod
    def validate_role(role: str) -> str | None:
        """
        验证用户角色

        Args:
            role: 用户角色

        Returns:
            str: 验证后的角色，验证失败返回None
        """
        if not role or role.lower() not in InputValidator.ALLOWED_ROLES:
            return None
        return role.lower()

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        清理HTML内容，移除危险标签和属性

        Args:
            html_content: HTML内容

        Returns:
            str: 清理后的HTML内容
        """
        if not html_content:
            return ""

        # 允许的标签和属性
        allowed_tags = [
            "p",
            "br",
            "strong",
            "em",
            "u",
            "b",
            "i",
            "ul",
            "ol",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]
        allowed_attributes = {}

        # 使用bleach清理HTML
        return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes)

    @staticmethod
    def validate_sql_query(query: str) -> bool:
        """
        验证SQL查询是否安全

        Args:
            query: SQL查询语句

        Returns:
            bool: 是否安全
        """
        if not query:
            return False

        # 危险SQL关键词
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "EXEC",
            "EXECUTE",
            "UNION",
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
        ]

        query_upper = query.upper()
        return all(keyword not in query_upper for keyword in dangerous_keywords)

    @staticmethod
    def validate_json(json_data: str | dict) -> dict | None:
        """
        验证JSON数据

        Args:
            json_data: JSON数据

        Returns:
            dict: 验证后的字典，验证失败返回None
        """
        if isinstance(json_data, dict):
            return json_data

        if isinstance(json_data, str):
            try:
                import json

                return json.loads(json_data)
            except (json.JSONDecodeError, TypeError):
                return None

        return None

    @staticmethod
    def validate_pagination(page: Any, per_page: Any, max_per_page: int = 100) -> tuple[int, int]:
        """
        验证分页参数

        Args:
            page: 页码
            per_page: 每页数量
            max_per_page: 最大每页数量

        Returns:
            tuple: (page, per_page) 验证后的分页参数
        """
        page = InputValidator.validate_integer(page, min_val=1) or 1
        per_page = InputValidator.validate_integer(per_page, min_val=1, max_val=max_per_page) or 10

        return page, per_page

    @staticmethod
    def validate_request_data(required_fields: list[str], optional_fields: list[str] | None = None) -> dict[str, Any]:
        """
        验证请求数据

        Args:
            required_fields: 必需字段列表
            optional_fields: 可选字段列表

        Returns:
            dict: 验证后的数据字典
        """
        data = {}
        errors = []

        # 验证必需字段
        for field in required_fields:
            value = request.form.get(field) or request.json.get(field) if request.is_json else request.form.get(field)
            if not value:
                errors.append(f"缺少必需字段: {field}")
            else:
                data[field] = value

        # 验证可选字段
        if optional_fields:
            for field in optional_fields:
                value = (
                    request.form.get(field) or request.json.get(field) if request.is_json else request.form.get(field)
                )
                if value:
                    data[field] = value

        if errors:
            raise ValueError("; ".join(errors))

        return data


def validate_instance_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    验证实例数据

    Args:
        data: 实例数据

    Returns:
        dict: 验证后的数据
    """
    validated = {}

    # 验证名称
    name = InputValidator.validate_string(data.get("name"), min_length=1, max_length=100, allow_empty=False)
    if not name:
        error_msg = "实例名称无效"
        raise ValueError(error_msg)
    validated["name"] = name

    # 验证数据库类型
    db_type = InputValidator.validate_db_type(data.get("db_type"))
    if not db_type:
        error_msg = "不支持的数据库类型"
        raise ValueError(error_msg)
    validated["db_type"] = db_type

    # 验证主机地址
    host = InputValidator.validate_string(
        data.get("host"),
        min_length=1,
        max_length=255,
        allow_empty=False,
        pattern=r"^[a-zA-Z0-9.-]+$",
    )
    if not host:
        error_msg = "主机地址无效"
        raise ValueError(error_msg)
    validated["host"] = host

    # 验证端口
    port = InputValidator.validate_integer(data.get("port"), min_val=1, max_val=65535)
    if not port:
        error_msg = "端口号无效"
        raise ValueError(error_msg)
    validated["port"] = port

    # 验证数据库名
    database_name = InputValidator.validate_string(
        data.get("database_name"),
        min_length=1,
        max_length=100,
        allow_empty=False,
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    if not database_name:
        error_msg = "数据库名无效"
        raise ValueError(error_msg)
    validated["database_name"] = database_name

    # 验证描述
    description = InputValidator.validate_string(data.get("description"), max_length=500, allow_empty=True)
    validated["description"] = description or ""

    # 验证是否激活
    is_active = InputValidator.validate_boolean(data.get("is_active"))
    validated["is_active"] = is_active if is_active is not None else True

    return validated


def validate_credential_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    验证凭据数据

    Args:
        data: 凭据数据

    Returns:
        dict: 验证后的数据
    """
    validated = {}

    # 验证名称
    name = InputValidator.validate_string(data.get("name"), min_length=1, max_length=100, allow_empty=False)
    if not name:
        error_msg = "凭据名称无效"
        raise ValueError(error_msg)
    validated["name"] = name

    # 验证用户名
    username = InputValidator.validate_string(
        data.get("username"),
        min_length=1,
        max_length=100,
        allow_empty=False,
        pattern=r"^[a-zA-Z0-9_@.-]+$",
    )
    if not username:
        error_msg = "用户名无效"
        raise ValueError(error_msg)
    validated["username"] = username

    # 验证密码
    password = data.get("password")
    if not password or len(password) < 6:
        error_msg = "密码长度至少6位"
        raise ValueError(error_msg)
    validated["password"] = password

    # 验证描述
    description = InputValidator.validate_string(data.get("description"), max_length=500, allow_empty=True)
    validated["description"] = description or ""

    # 验证是否激活
    is_active = InputValidator.validate_boolean(data.get("is_active"))
    validated["is_active"] = is_active if is_active is not None else True

    return validated
