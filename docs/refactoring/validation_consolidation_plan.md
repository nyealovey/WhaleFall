# 验证体系整合与优化方案

## 📋 现状分析

### 当前存在的4个验证相关文件

| 文件 | 主要功能 | 问题 |
|------|---------|------|
| `decorators.py` | 装饰器验证（JSON、权限） | ✅ 功能完整 |
| `data_validator.py` | 实例数据验证 | ✅ 功能完整，但只针对实例 |
| `validation.py` | 通用输入验证（字符串、整数等） | ⚠️ 功能重复 |
| `security.py` | 安全相关验证（密码、用户名） | ⚠️ 功能重复 |

### 🔴 发现的问题

#### 1. 功能重复

**密码验证重复**:
```python
# security.py
def validate_password(password: str):
    if len(password) < 6:
        return "密码长度至少6个字符"

# validation.py 中的 validate_credential_data
if len(password) < 6:
    raise ValueError("密码长度至少6位")
```

**数据库类型验证重复**:
```python
# security.py
def validate_db_type(db_type: str):
    valid_types = ["mysql", "postgresql", "sqlserver", "oracle", "sqlite"]

# validation.py - InputValidator
ALLOWED_DB_TYPES = ["mysql", "postgresql", "sqlserver", "oracle"]

# data_validator.py - DataValidator
SUPPORTED_DB_TYPES = ["mysql", "postgresql", "sqlserver", "oracle"]
```

**数据清理重复**:
```python
# security.py
def sanitize_input(value: Any) -> str:
    # HTML转义 + 危险字符移除

# security.py
def sanitize_form_data(data: dict) -> dict:
    # 批量清理

# data_validator.py
def sanitize_input(data: dict) -> dict:
    # 去除空格
```

**必填字段验证重复**:
```python
# security.py
def validate_required_fields(data, required_fields):
    # 检查必填字段

# decorators.py - @validate_json
if required_fields:
    missing_fields = [field for field in required_fields if field not in data]
```

#### 2. 密码验证太弱

所有地方都只检查长度 >= 6，没有强度要求：
- ❌ 不要求大小写字母
- ❌ 不要求数字
- ❌ 不要求特殊字符

#### 3. IP地址验证不严格

`data_validator.py` 中的 `_is_valid_host()`:
- ❌ 不检查私有IP
- ❌ 不检查保留IP
- ❌ 不检查localhost

## 🎯 整合方案

### 方案：统一到3个文件

```
┌─────────────────────────────────────────────────────────┐
│                  验证体系架构（整合后）                  │
├─────────────────────────────────────────────────────────┤
│ 1️⃣ decorators.py - 装饰器层                            │
│    - @validate_json          (保持不变)                 │
│    - @validate_query_params  (新增)                     │
│    - @login_required         (保持不变)                 │
│    - @permission_required    (保持不变)                 │
├─────────────────────────────────────────────────────────┤
│ 2️⃣ validators.py - 统一验证器（整合后的新文件）         │
│    ├─ DataValidator          (从 data_validator.py)    │
│    │  - validate_instance_data                          │
│    │  - validate_batch_data                             │
│    │  - sanitize_input                                  │
│    │                                                     │
│    ├─ InputValidator          (从 validation.py)        │
│    │  - validate_string                                 │
│    │  - validate_integer                                │
│    │  - validate_email                                  │
│    │  - validate_pagination                             │
│    │                                                     │
│    ├─ SecurityValidator       (从 security.py)          │
│    │  - validate_password     (增强版)                  │
│    │  - validate_username                               │
│    │  - sanitize_html                                   │
│    │  - check_sql_injection                             │
│    │                                                     │
│    └─ NetworkValidator        (新增)                    │
│       - validate_host         (增强版)                  │
│       - validate_port                                   │
│       - validate_url                                    │
├─────────────────────────────────────────────────────────┤
│ 3️⃣ security.py - 安全工具（简化后）                     │
│    - generate_csrf_token     (保留)                     │
│    - verify_csrf_token       (保留)                     │
│    - hash_password           (保留)                     │
│    - verify_password         (保留)                     │
└─────────────────────────────────────────────────────────┘
```

### 文件职责划分

#### `decorators.py` - 装饰器层
**职责**: 请求级别的验证  
**保留**: 所有现有装饰器  
**新增**: `@validate_query_params` (可选)

#### `validators.py` - 统一验证器（新文件）
**职责**: 数据验证和清理  
**整合自**:
- `data_validator.py` → `DataValidator`
- `validation.py` → `InputValidator`
- `security.py` 的验证函数 → `SecurityValidator`
- 新增 → `NetworkValidator`

#### `security.py` - 安全工具（简化）
**职责**: 加密、令牌、哈希  
**保留**: CSRF、密码哈希相关  
**移除**: 所有验证函数（移到 validators.py）

## 📝 具体实施步骤

### 步骤1：创建统一的 validators.py

<function_calls>
<invoke name="fsWrite">
<parameter name="path">app/utils/validators.py""
鲸落 - 统一验证器模块
整合所有数据验证功能
"""

import html
import ipaddress
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import bleach

from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


# ============================================================================
# DataValidator - 领域数据验证（从 data_validator.py 迁移）
# ============================================================================

class DataValidator:
    """领域数据验证器 - 用于验证业务实体数据"""
    
    # 支持的数据库类型（统一定义）
    SUPPORTED_DB_TYPES = ["mysql", "postgresql", "sqlserver", "oracle"]
    
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
        """
        验证实例数据
        
        Args:
            data: 实例数据字典
            
        Returns:
            (是否有效, 错误信息)
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
            
            # 验证主机地址（使用增强版）
            host_error = NetworkValidator.validate_host(
                data.get("host"),
                allow_private=True,  # 允许私有IP
                allow_localhost=True  # 允许localhost
            )
            if host_error:
                return False, host_error
            
            # 验证端口号
            port_error = NetworkValidator.validate_port(data.get("port"))
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
        """验证实例名称"""
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
        """验证数据库类型"""
        if not isinstance(db_type, str):
            return "数据库类型必须是字符串"
        
        db_type = db_type.strip().lower()
        if db_type not in cls.SUPPORTED_DB_TYPES:
            return f"不支持的数据库类型: {db_type}。支持的类型: {', '.join(cls.SUPPORTED_DB_TYPES)}"
        
        return None
    
    @classmethod
    def _validate_database_name(cls, db_name: Any) -> Optional[str]:
        """验证数据库名称"""
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
        """验证描述"""
        if not isinstance(description, str):
            return "描述必须是字符串"
        
        description = description.strip()
        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            return f"描述长度不能超过{cls.MAX_DESCRIPTION_LENGTH}个字符"
        
        return None
    
    @classmethod
    def _validate_credential_id(cls, credential_id: Any) -> Optional[str]:
        """验证凭据ID"""
        try:
            cred_id = int(credential_id)
            if cred_id <= 0:
                return "凭据ID必须是正整数"
        except (ValueError, TypeError):
            return "凭据ID必须是整数"
        
        return None
    
    @classmethod
    def validate_batch_data(cls, data_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        验证批量数据
        
        Args:
            data_list: 数据列表
            
        Returns:
            (有效数据列表, 错误信息列表)
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
    def sanitize_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理输入数据
        
        Args:
            data: 原始数据
            
        Returns:
            清理后的数据
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # 去除首尾空格
                sanitized[key] = value.strip()
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            else:
                # 转换为字符串并清理
                sanitized[key] = str(value).strip()
        
        return sanitized


# ============================================================================
# InputValidator - 通用输入验证（从 validation.py 迁移）
# ============================================================================

class InputValidator:
    """通用输入验证器 - 用于验证基础数据类型"""
    
    @staticmethod
    def validate_string(
        value: Any,
        min_length: int = 0,
        max_length: int = 255,
        allow_empty: bool = True,
        pattern: Optional[str] = None,
    ) -> Optional[str]:
        """
        验证字符串输入
        
        Args:
            value: 输入值
            min_length: 最小长度
            max_length: 最大长度
            allow_empty: 是否允许空值
            pattern: 正则表达式模式
            
        Returns:
            清理后的字符串，验证失败返回None
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
    def validate_integer(
        value: Any,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None
    ) -> Optional[int]:
        """
        验证整数输入
        
        Args:
            value: 输入值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            验证后的整数，验证失败返回None
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
    def validate_boolean(value: Any) -> Optional[bool]:
        """验证布尔值输入"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes", "on"]
        if isinstance(value, int):
            return bool(value)
        return None
    
    @staticmethod
    def validate_email(email: str) -> Optional[str]:
        """验证邮箱地址"""
        if not email:
            return None
        
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return None
        
        return email.lower().strip()
    
    @staticmethod
    def validate_pagination(
        page: Any,
        per_page: Any,
        max_per_page: int = 100
    ) -> Tuple[int, int]:
        """
        验证分页参数
        
        Args:
            page: 页码
            per_page: 每页数量
            max_per_page: 最大每页数量
            
        Returns:
            (page, per_page) 验证后的分页参数
        """
        page = InputValidator.validate_integer(page, min_val=1) or 1
        per_page = InputValidator.validate_integer(
            per_page,
            min_val=1,
            max_val=max_per_page
        ) or 20  # 统一默认值为20
        
        return page, per_page


# ============================================================================
# SecurityValidator - 安全验证（从 security.py 迁移）
# ============================================================================

class SecurityValidator:
    """安全验证器 - 用于验证安全相关数据"""
    
    @staticmethod
    def validate_username(username: str) -> Optional[str]:
        """
        验证用户名格式
        
        Args:
            username: 用户名
            
        Returns:
            错误信息，None表示验证通过
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
    
    @staticmethod
    def validate_password(
        password: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False
    ) -> Optional[str]:
        """
        验证密码强度（增强版）
        
        Args:
            password: 密码
            min_length: 最小长度（默认8）
            require_uppercase: 是否要求大写字母
            require_lowercase: 是否要求小写字母
            require_digit: 是否要求数字
            require_special: 是否要求特殊字符
            
        Returns:
            错误信息，None表示验证通过
        """
        if not password:
            return "密码不能为空"
        
        if len(password) < min_length:
            return f"密码长度至少{min_length}个字符"
        
        if len(password) > 128:
            return "密码长度不能超过128个字符"
        
        if require_uppercase and not re.search(r'[A-Z]', password):
            return "密码必须包含大写字母"
        
        if require_lowercase and not re.search(r'[a-z]', password):
            return "密码必须包含小写字母"
        
        if require_digit and not re.search(r'\d', password):
            return "密码必须包含数字"
        
        if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return "密码必须包含特殊字符"
        
        return None
    
    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        清理HTML内容，移除危险标签和属性
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的HTML内容
        """
        if not html_content:
            return ""
        
        # 允许的标签和属性
        allowed_tags = [
            "p", "br", "strong", "em", "u", "b", "i",
            "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6"
        ]
        allowed_attributes = {}
        
        # 使用bleach清理HTML
        return bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes
        )
    
    @staticmethod
    def check_sql_injection(query: str) -> bool:
        """
        检查SQL注入风险
        
        Args:
            query: SQL查询语句
            
        Returns:
            True表示有风险，False表示安全
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


# ============================================================================
# NetworkValidator - 网络验证（新增）
# ============================================================================

class NetworkValidator:
    """网络验证器 - 用于验证网络相关数据"""
    
    MIN_PORT = 1
    MAX_PORT = 65535
    
    @staticmethod
    def validate_host(
        host: str,
        allow_private: bool = True,
        allow_localhost: bool = True
    ) -> Optional[str]:
        """
        验证主机地址（增强版）
        
        Args:
            host: 主机地址
            allow_private: 是否允许私有IP
            allow_localhost: 是否允许localhost
            
        Returns:
            错误信息，None表示验证通过
        """
        if not isinstance(host, str):
            return "主机地址必须是字符串"
        
        host = host.strip()
        if not host:
            return "主机地址不能为空"
        
        if len(host) > 255:
            return "主机地址长度不能超过255个字符"
        
        # 检查IP地址格式
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, host):
            try:
                ip = ipaddress.ip_address(host)
                
                # 检查是否为私有IP
                if not allow_private and ip.is_private:
                    return "不允许使用私有IP地址"
                
                # 检查是否为localhost
                if not allow_localhost and ip.is_loopback:
                    return "不允许使用localhost地址"
                
                # 检查是否为保留IP
                if ip.is_reserved:
                    return "不允许使用保留IP地址"
                
                # 检查IP范围
                parts = host.split('.')
                if not all(0 <= int(part) <= 255 for part in parts):
                    return "IP地址格式无效"
                
                return None
            except ValueError:
                return "IP地址格式无效"
        
        # 检查域名格式
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(domain_pattern, host):
            return "主机地址格式无效，请输入有效的IP地址或域名"
        
        return None
    
    @staticmethod
    def validate_port(port: Any) -> Optional[str]:
        """
        验证端口号
        
        Args:
            port: 端口号
            
        Returns:
            错误信息，None表示验证通过
        """
        try:
            port = int(port)
        except (ValueError, TypeError):
            return "端口号必须是整数"
        
        if not (NetworkValidator.MIN_PORT <= port <= NetworkValidator.MAX_PORT):
            return f"端口号必须在{NetworkValidator.MIN_PORT}-{NetworkValidator.MAX_PORT}之间"
        
        return None
    
    @staticmethod
    def validate_url(url: str) -> Optional[str]:
        """
        验证URL
        
        Args:
            url: URL地址
            
        Returns:
            错误信息，None表示验证通过
        """
        if not url:
            return "URL不能为空"
        
        url_pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
        if not re.match(url_pattern, url):
            return "URL格式无效"
        
        return None


# ============================================================================
# 向后兼容的函数（保持旧代码可用）
# ============================================================================

def validate_instance_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """向后兼容函数"""
    is_valid, error = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValueError(error)
    return data


def validate_credential_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """向后兼容函数"""
    validated = {}
    
    # 验证名称
    name = InputValidator.validate_string(
        data.get("name"),
        min_length=1,
        max_length=100,
        allow_empty=False
    )
    if not name:
        raise ValueError("凭据名称无效")
    validated["name"] = name
    
    # 验证用户名
    username = InputValidator.validate_string(
        data.get("username"),
        min_length=1,
        max_length=100,
        allow_empty=False,
        pattern=r"^[a-zA-Z0-9_@.-]+$"
    )
    if not username:
        raise ValueError("用户名无效")
    validated["username"] = username
    
    # 验证密码（使用增强版）
    password = data.get("password")
    password_error = SecurityValidator.validate_password(
        password,
        min_length=8,  # 提高到8位
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
        require_special=False
    )
    if password_error:
        raise ValueError(password_error)
    validated["password"] = password
    
    # 验证描述
    description = InputValidator.validate_string(
        data.get("description"),
        max_length=500,
        allow_empty=True
    )
    validated["description"] = description or ""
    
    # 验证是否激活
    is_active = InputValidator.validate_boolean(data.get("is_active"))
    validated["is_active"] = is_active if is_active is not None else True
    
    return validated


__all__ = [
    "DataValidator",
    "InputValidator",
    "SecurityValidator",
    "NetworkValidator",
    "validate_instance_data",
    "validate_credential_data",
]
