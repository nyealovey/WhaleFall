"""
数据验证工具类
提供严格的数据验证功能，防止无效数据进入系统
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


class DataValidator:
    """数据验证器"""
    
    # 支持的数据库类型
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
    def _validate_host(cls, host: Any) -> Optional[str]:
        """验证主机地址"""
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
        """验证端口号"""
        try:
            port = int(port)
        except (ValueError, TypeError):
            return "端口号必须是整数"
        
        if not (cls.MIN_PORT <= port <= cls.MAX_PORT):
            return f"端口号必须在{cls.MIN_PORT}-{cls.MAX_PORT}之间"
        
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
    def _is_valid_host(cls, host: str) -> bool:
        """检查主机地址是否有效"""
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
