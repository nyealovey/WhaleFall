"""
数据验证工具类
提供严格的数据验证功能，防止无效数据进入系统
"""

import html
import re
from collections.abc import Mapping
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

from app.utils.structlog_config import get_system_logger
from app.constants import DatabaseType

logger = get_system_logger()


class DataValidator:
    """数据验证器。

    提供严格的数据验证功能，防止无效数据进入系统。
    支持实例数据、批量数据、表单数据的验证和清理。

    Attributes:
        SUPPORTED_DB_TYPES: 支持的数据库类型列表。
        SUPPORTED_CREDENTIAL_TYPES: 支持的凭据类型列表。
        MIN_PORT: 最小端口号。
        MAX_PORT: 最大端口号。
        MAX_NAME_LENGTH: 名称最大长度。
        MAX_HOST_LENGTH: 主机地址最大长度。
        MAX_DATABASE_LENGTH: 数据库名称最大长度。
        MAX_DESCRIPTION_LENGTH: 描述最大长度。
    """
    
    # 支持的数据库类型
    SUPPORTED_DB_TYPES = ["mysql", "postgresql", "sqlserver", "oracle", "sqlite"]

    # 支持的凭据类型
    SUPPORTED_CREDENTIAL_TYPES = ["database", "ssh", "windows", "api", "ldap"]
    _custom_db_types: set[str] | None = None
    
    # 端口号范围
    MIN_PORT = 1
    MAX_PORT = 65535
    
    # 字符串长度限制
    MAX_NAME_LENGTH = 100
    MAX_HOST_LENGTH = 255
    MAX_DATABASE_LENGTH = 64
    MAX_DESCRIPTION_LENGTH = 500
    
    @classmethod
    def validate_instance_data(cls, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证实例数据。

        验证实例的所有必填字段和可选字段，包括名称、数据库类型、
        主机地址、端口号、数据库名称、描述和凭据ID。

        Args:
            data: 实例数据字典，包含实例的各项配置信息。

        Returns:
            包含两个元素的元组：
            - 是否有效（True/False）
            - 错误信息（验证失败时返回具体错误，成功时返回 None）
        """
        try:
            # 验证必填字段
            required_fields = ["name", "db_type", "host", "port"]
            for field in required_fields:
                if not data.get(field):
                    return False, f"字段 '{field}' 是必填的"
            
            # 验证实例名称
            name_error = cls._validate_name(data.get("name"))
            if name_error:
                return False, name_error
            
            # 验证数据库类型
            db_type_error = cls._validate_db_type(data.get("db_type"))
            if db_type_error:
                return False, db_type_error
            
            # 验证主机地址
            host_error = cls._validate_host(data.get("host"))
            if host_error:
                return False, host_error
            
            # 验证端口号
            port_error = cls._validate_port(data.get("port"))
            if port_error:
                return False, port_error
            
            # 验证数据库名称（可选）
            if data.get("database_name"):
                db_name_error = cls._validate_database_name(data.get("database_name"))
                if db_name_error:
                    return False, db_name_error
            
            # 验证描述（可选）
            if data.get("description"):
                desc_error = cls._validate_description(data.get("description"))
                if desc_error:
                    return False, desc_error
            
            # 验证凭据ID（可选）
            if data.get("credential_id"):
                cred_error = cls._validate_credential_id(data.get("credential_id"))
                if cred_error:
                    return False, cred_error
            
            return True, None
            
        except Exception as e:
            logger.error(f"数据验证过程中发生错误: {str(e)}")
            return False, f"数据验证失败: {str(e)}"
    
    @classmethod
    def _validate_name(cls, name: Any) -> Optional[str]:
        """验证实例名称并返回错误信息。

        Args:
            name: 前端提交的实例名称，可能为空或包含非法字符。

        Returns:
            字符串错误提示；若名称合法则返回 None。
        """
        if not isinstance(name, str):
            return "实例名称必须是字符串"
        
        name = name.strip()
        if not name:
            return "实例名称不能为空"
        
        if len(name) > cls.MAX_NAME_LENGTH:
            return f"实例名称长度不能超过{cls.MAX_NAME_LENGTH}个字符"
        
        # 检查是否包含特殊字符
        if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$', name):
            return "实例名称只能包含字母、数字、下划线、连字符和中文字符"
        
        return None
    
    @classmethod
    def _validate_db_type(cls, db_type: Any) -> Optional[str]:
        """验证数据库类型是否在受支持范围。

        Args:
            db_type: 用户选择的数据库类型值。

        Returns:
            字符串错误提示；若数据库类型有效则返回 None。
        """
        if not isinstance(db_type, str):
            return "数据库类型必须是字符串"

        db_type = db_type.strip().lower()
        allowed = cls._resolve_allowed_db_types()
        if db_type not in allowed:
            return f"不支持的数据库类型: {db_type}。支持的类型: {', '.join(sorted(allowed))}"

        return None
    
    @classmethod
    def _validate_host(cls, host: Any) -> Optional[str]:
        """验证主机地址格式。

        Args:
            host: 可能为 IP、域名或其他值的主机输入。

        Returns:
            字符串错误提示；若主机格式正确则返回 None。
        """
        if not isinstance(host, str):
            return "主机地址必须是字符串"
        
        host = host.strip()
        if not host:
            return "主机地址不能为空"
        
        if len(host) > cls.MAX_HOST_LENGTH:
            return f"主机地址长度不能超过{cls.MAX_HOST_LENGTH}个字符"
        
        # 验证IP地址或域名格式
        if not cls._is_valid_host(host):
            return "主机地址格式无效，请输入有效的IP地址或域名"
        
        return None
    
    @classmethod
    def _validate_port(cls, port: Any) -> Optional[str]:
        """验证端口号是否处于允许范围。

        Args:
            port: 可为字符串或数字的端口输入。

        Returns:
            字符串错误提示；若端口合法则返回 None。
        """
        try:
            port = int(port)
        except (ValueError, TypeError):
            return "端口号必须是整数"
        
        if not (cls.MIN_PORT <= port <= cls.MAX_PORT):
            return f"端口号必须在{cls.MIN_PORT}-{cls.MAX_PORT}之间"
        
        return None
    
    @classmethod
    def _validate_database_name(cls, db_name: Any) -> Optional[str]:
        """验证数据库名称长度与字符集合。

        Args:
            db_name: 用户输入的数据库名称。

        Returns:
            字符串错误提示；若名称满足规范则返回 None。
        """
        if not isinstance(db_name, str):
            return "数据库名称必须是字符串"
        
        db_name = db_name.strip()
        if not db_name:
            return "数据库名称不能为空"
        
        if len(db_name) > cls.MAX_DATABASE_LENGTH:
            return f"数据库名称长度不能超过{cls.MAX_DATABASE_LENGTH}个字符"
        
        # 检查是否包含特殊字符
        if not re.match(r'^[a-zA-Z0-9_\-]+$', db_name):
            return "数据库名称只能包含字母、数字、下划线和连字符"
        
        return None
    
    @classmethod
    def _validate_description(cls, description: Any) -> Optional[str]:
        """验证描述字段长度。

        Args:
            description: 可选描述内容。

        Returns:
            字符串错误提示；若描述合法则返回 None。
        """
        if not isinstance(description, str):
            return "描述必须是字符串"
        
        description = description.strip()
        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            return f"描述长度不能超过{cls.MAX_DESCRIPTION_LENGTH}个字符"
        
        return None
    
    @classmethod
    def _validate_credential_id(cls, credential_id: Any) -> Optional[str]:
        """验证凭据 ID 是否为正整数。

        Args:
            credential_id: 表单中的凭据 ID 字段。

        Returns:
            字符串错误提示；若 ID 有效则返回 None。
        """
        try:
            cred_id = int(credential_id)
            if cred_id <= 0:
                return "凭据ID必须是正整数"
        except (ValueError, TypeError):
            return "凭据ID必须是整数"
        
        return None
    
    @classmethod
    def _is_valid_host(cls, host: str) -> bool:
        """检查主机地址是否是合法 IP 或域名。

        Args:
            host: 已去除首尾空白的主机字符串。

        Returns:
            True 表示格式匹配 IP/域名规范，否则为 False。
        """
        # 检查IP地址格式
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, host):
            parts = host.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        
        # 检查域名格式
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, host))
    
    @classmethod
    def validate_batch_data(cls, data_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """验证批量数据。

        对数据列表中的每一项进行验证，返回有效数据和错误信息。

        Args:
            data_list: 待验证的数据列表。

        Returns:
            包含两个元素的元组：
            - 有效数据列表
            - 错误信息列表（包含每条无效数据的错误描述）
        """
        valid_data = []
        errors = []
        
        for i, data in enumerate(data_list):
            is_valid, error = cls.validate_instance_data(data)
            if is_valid:
                valid_data.append(data)
            else:
                errors.append(f"第{i+1}条数据: {error}")
        
        return valid_data, errors
    
    @classmethod
    def sanitize_string(cls, value: Any) -> str:
        """清理字符串，移除潜在的危险内容。

        对输入字符串进行 HTML 转义，并移除常见的 XSS 攻击模式。

        Args:
            value: 原始值，可以是任意类型。

        Returns:
            清理后的安全字符串。
        """
        if value is None:
            return ""

        string_value = str(value)
        escaped = html.escape(string_value)

        dangerous_patterns = ["<script", "</script", "javascript:", "onload=", "onerror="]
        for pattern in dangerous_patterns:
            escaped = escaped.replace(pattern, "")

        return escaped.strip()

    @classmethod
    def sanitize_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理输入数据
        
        Args:
            data: 原始数据
            
        Returns:
            清理后的数据
        """
        sanitized = {}
        
        for key, value in (data or {}).items():
            if isinstance(value, str):
                sanitized[key] = value.strip()
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            else:
                # 转换为字符串并清理
                sanitized[key] = str(value).strip()
        
        return sanitized

    @classmethod
    def sanitize_form_data(cls, data: Mapping[str, Any]) -> Dict[str, Any]:
        """清理表单提交的数据结构。

        处理 MultiDict 和普通字典，支持同名字段多值（如 checkbox）。
        对所有字符串值进行安全清理。

        Args:
            data: 表单或 JSON 数据，可以是 MultiDict 或普通字典。

        Returns:
            清理后的数据字典。
        """
        sanitized: Dict[str, Any] = {}
        if hasattr(data, "getlist"):
            # MultiDict 支持同名字段多值（如 checkbox + hidden），需要保留全部值
            for key in data.keys():
                values = data.getlist(key)
                if not values:
                    sanitized[key] = None
                    continue

                cleaned_values = []
                for value in values:
                    if isinstance(value, str):
                        cleaned_values.append(cls.sanitize_string(value))
                    elif isinstance(value, (int, float, bool)):
                        cleaned_values.append(value)
                    elif value is None:
                        cleaned_values.append(None)
                    else:
                        cleaned_values.append(cls.sanitize_string(str(value)))

                # 只有一个值时保持原有标量行为，多个值返回列表供后续解析
                sanitized[key] = cleaned_values[0] if len(cleaned_values) == 1 else cleaned_values
        else:
            for key, value in (data or {}).items():
                if isinstance(value, str):
                    sanitized[key] = cls.sanitize_string(value)
                elif isinstance(value, (int, float, bool)):
                    sanitized[key] = value
                elif value is None:
                    sanitized[key] = None
                else:
                    sanitized[key] = cls.sanitize_string(str(value))
        return sanitized

    @staticmethod
    def validate_required_fields(data: Mapping[str, Any], required_fields: List[str]) -> Optional[str]:
        """验证必填字段是否存在。

        检查数据中是否包含所有必填字段，且字段值不为空。

        Args:
            data: 数据字典。
            required_fields: 必填字段名称列表。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        for field in required_fields:
            value = data.get(field) if hasattr(data, "get") else None
            if value is None or (isinstance(value, str) and not value.strip()):
                return f"{field}不能为空"
        return None

    @classmethod
    def validate_db_type(cls, db_type: Any) -> Optional[str]:
        """验证数据库类型是否受支持。

        Args:
            db_type: 待验证的数据库类型。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        if db_type in (None, ""):
            return None

        if not isinstance(db_type, str):
            return "数据库类型必须是字符串"

        normalized = db_type.strip().lower()
        if not normalized:
            return "数据库类型不能为空"

        if normalized not in cls._resolve_allowed_db_types():
            return f"不支持的数据库类型: {db_type}"

        return None

    @classmethod
    def set_custom_db_types(cls, db_types: Sequence[str] | None) -> None:
        """在测试场景中自定义受支持的数据库类型集合。"""

        if db_types is None:
            cls._custom_db_types = None
        else:
            cls._custom_db_types = {item.strip().lower() for item in db_types if item}

    @classmethod
    def _resolve_allowed_db_types(cls) -> set[str]:
        """获取允许的数据库类型集合，优先使用数据库配置。"""

        if cls._custom_db_types is not None:
            return cls._custom_db_types

        try:
            from app.services.database_type_service import DatabaseTypeService

            configs = DatabaseTypeService.get_active_types()
            dynamic_types = {config.name.lower() for config in configs if getattr(config, "name", None)}
            if dynamic_types:
                return dynamic_types
        except Exception as exc:  # noqa: BLE001
            logger.warning("获取数据库类型配置失败，回退到静态白名单: %s", exc)

        return {item.lower() for item in cls.SUPPORTED_DB_TYPES}

    @classmethod
    def validate_credential_type(cls, credential_type: Any) -> Optional[str]:
        """验证凭据类型。

        Args:
            credential_type: 凭据类型。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        if credential_type in (None, ""):
            return None

        if not isinstance(credential_type, str):
            return "凭据类型必须是字符串"

        normalized = credential_type.strip().lower()
        if not normalized:
            return "凭据类型不能为空"

        if normalized not in cls.SUPPORTED_CREDENTIAL_TYPES:
            return f"不支持的凭据类型: {credential_type}"

        return None

    @staticmethod
    def validate_username(username: Any) -> Optional[str]:
        """验证用户名格式。

        用户名必须是 3-50 个字符，只能包含字母、数字、下划线、连字符和点。

        Args:
            username: 待验证的用户名。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        if not username:
            return "用户名不能为空"

        if not isinstance(username, str):
            return "用户名必须是字符串"

        normalized = username.strip()
        if len(normalized) < 3:
            return "用户名长度至少3个字符"

        if len(normalized) > 50:
            return "用户名长度不能超过50个字符"

        if not re.match(r"^[a-zA-Z0-9_.-]+$", normalized):
            return "用户名只能包含字母、数字、下划线、连字符和点"

        return None

    @staticmethod
    def validate_password(password: Any) -> Optional[str]:
        """验证密码强度。

        密码必须是 6-128 个字符。

        Args:
            password: 待验证的密码。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        if not password:
            return "密码不能为空"

        if not isinstance(password, str):
            return "密码必须是字符串"

        if len(password) < 6:
            return "密码长度至少6个字符"

        if len(password) > 128:
            return "密码长度不能超过128个字符"

        return None


# 兼容旧的函数式调用方式 ----------------------------------------------------

def sanitize_form_data(data: Mapping[str, Any]) -> Dict[str, Any]:
    """函数式入口，委托给 `DataValidator.sanitize_form_data`。

    Args:
        data: 任意映射对象，包含需要清洗的实例字段。

    Returns:
        归一化后的表单字典，字段值已去除空白并转换为基础类型。
    """

    return DataValidator.sanitize_form_data(data)


def validate_required_fields(data: Mapping[str, Any], required_fields: List[str]) -> Optional[str]:
    """函数式入口校验必填字段。

    Args:
        data: 需要校验的表单数据。
        required_fields: 必填字段列表。

    Returns:
        第一个缺失字段的错误信息；若全部存在则返回 None。
    """

    return DataValidator.validate_required_fields(data, required_fields)


def validate_db_type(db_type: Any) -> Optional[str]:
    """函数式入口校验数据库类型。

    Args:
        db_type: 表单提交的数据库类型。

    Returns:
        字符串错误描述；当类型有效时返回 None。
    """

    return DataValidator.validate_db_type(db_type)


def validate_credential_type(credential_type: Any) -> Optional[str]:
    """函数式入口校验凭据类型。

    Args:
        credential_type: 表单提交的凭据类型。

    Returns:
        字符串错误描述；当类型有效时返回 None。
    """

    return DataValidator.validate_credential_type(credential_type)


def validate_username(username: Any) -> Optional[str]:
    """函数式入口校验用户名。

    Args:
        username: 用户输入的账号名。

    Returns:
        字符串错误描述；当用户名合法时返回 None。
    """

    return DataValidator.validate_username(username)


def validate_password(password: Any) -> Optional[str]:
    """函数式入口校验密码。

    Args:
        password: 待校验的明文密码。

    Returns:
        字符串错误描述；当密码满足长度和字符要求时返回 None。
    """

    return DataValidator.validate_password(password)
