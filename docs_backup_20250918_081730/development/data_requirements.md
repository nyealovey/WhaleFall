# 数据要求与生成脚本规范

## 1. 数据要求概述

### 1.1 核心原则
- **严格禁止**: 代码中不得包含任何模拟数据、假数据或硬编码测试数据
- **真实数据**: 所有数据必须来自真实数据库连接或通过脚本自动生成
- **数据验证**: 所有生成的数据必须经过连接验证，确保真实可用
- **数据完整性**: 确保数据的一致性和完整性

### 1.2 数据分类

#### 1.2.1 配置数据
- 全局参数配置
- 数据库类型配置
- 凭据类型配置
- 同步类型配置
- 角色类型配置

#### 1.2.2 实例数据
- SQL Server实例
- MySQL实例
- Oracle实例
- 实例连接信息
- 实例状态信息

#### 1.2.3 凭据数据
- 数据库凭据
- SSH凭据（预留）
- Windows凭据（预留）
- 凭据加密存储

#### 1.2.4 账户数据
- 用户账户信息
- 权限信息
- 活动记录
- 统计数据

## 2. 数据生成脚本规范

### 2.1 脚本目录结构
```
scripts/
├── init_data.py              # 数据初始化主脚本
├── data_generators/          # 数据生成器模块
│   ├── __init__.py
│   ├── global_params_generator.py
│   ├── instance_generator.py
│   ├── credential_generator.py
│   ├── account_generator.py
│   └── user_generator.py
├── validators/               # 数据验证模块
│   ├── __init__.py
│   ├── connection_validator.py
│   ├── data_integrity_validator.py
│   └── security_validator.py
├── config/                   # 配置文件
│   ├── database_config.json
│   ├── instance_config.json
│   └── credential_config.json
└── utils/                    # 工具函数
    ├── __init__.py
    ├── encryption_utils.py
    └── connection_utils.py
```

### 2.2 数据生成器接口规范

```python
# scripts/data_generators/base_generator.py
"""
数据生成器基类
所有数据生成器必须继承此基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

class BaseDataGenerator(ABC):
    """数据生成器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据生成器
        
        Args:
            config: 配置字典，包含生成器所需的所有配置
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def generate(self) -> List[Dict[str, Any]]:
        """
        生成数据
        
        Returns:
            List[Dict[str, Any]]: 生成的数据列表
            
        Raises:
            DataGenerationError: 数据生成失败
        """
        pass
    
    @abstractmethod
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        验证生成的数据
        
        Args:
            data: 待验证的数据列表
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            DataValidationError: 数据验证失败
        """
        pass
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> bool:
        """
        保存数据到数据库
        
        Args:
            data: 待保存的数据列表
            
        Returns:
            bool: 保存是否成功
        """
        pass
```

### 2.3 全局参数生成器

```python
# scripts/data_generators/global_params_generator.py
"""
全局参数生成器
生成系统所需的全局配置参数
"""

from .base_generator import BaseDataGenerator
from typing import Dict, List, Any

class GlobalParamsGenerator(BaseDataGenerator):
    """全局参数生成器"""
    
    def generate(self) -> List[Dict[str, Any]]:
        """
        生成全局参数数据
        
        Returns:
            List[Dict[str, Any]]: 全局参数列表
        """
        params = []
        
        # 数据库类型参数
        db_types = [
            {
                "param_type": "database_type",
                "name": "SQL Server",
                "config": {
                    "driver": "pymssql",
                    "port": 1433,
                    "default_schema": "dbo",
                    "connection_timeout": 30
                }
            },
            {
                "param_type": "database_type", 
                "name": "MySQL",
                "config": {
                    "driver": "pymysql",
                    "port": 3306,
                    "default_schema": "information_schema",
                    "connection_timeout": 30
                }
            },
            {
                "param_type": "database_type",
                "name": "Oracle", 
                "config": {
                    "driver": "cx_Oracle",
                    "port": 1521,
                    "default_schema": "SYS",
                    "connection_timeout": 30
                }
            }
        ]
        
        # 凭据类型参数
        cred_types = [
            {
                "param_type": "credential_type",
                "name": "数据库凭据",
                "config": {
                    "encryption_method": "bcrypt",
                    "password_strength": "strong",
                    "expiry_days": 90
                }
            },
            {
                "param_type": "credential_type",
                "name": "SSH凭据",
                "config": {
                    "encryption_method": "AES",
                    "key_type": "RSA",
                    "expiry_days": 180
                }
            }
        ]
        
        # 同步类型参数
        sync_types = [
            {
                "param_type": "sync_type",
                "name": "账户信息同步",
                "config": {
                    "frequency": "0 */6 * * *",  # 每6小时
                    "batch_size": 1000,
                    "timeout": 300
                }
            },
            {
                "param_type": "sync_type",
                "name": "权限信息同步",
                "config": {
                    "frequency": "0 0 */12 * *",  # 每12小时
                    "batch_size": 500,
                    "timeout": 600
                }
            }
        ]
        
        # 角色类型参数
        role_types = [
            {
                "param_type": "role_type",
                "name": "管理员",
                "config": {
                    "permissions": ["read", "write", "delete", "admin"],
                    "description": "系统管理员，拥有所有权限"
                }
            },
            {
                "param_type": "role_type",
                "name": "普通用户",
                "config": {
                    "permissions": ["read"],
                    "description": "普通用户，只有查看权限"
                }
            }
        ]
        
        params.extend(db_types)
        params.extend(cred_types)
        params.extend(sync_types)
        params.extend(role_types)
        
        return params
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        验证全局参数数据
        
        Args:
            data: 待验证的数据列表
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["param_type", "name", "config"]
        
        for item in data:
            for field in required_fields:
                if field not in item:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
            
            if not isinstance(item["config"], dict):
                self.logger.error("config字段必须是字典类型")
                return False
        
        return True
```

### 2.4 实例数据生成器

```python
# scripts/data_generators/instance_generator.py
"""
数据库实例生成器
生成真实的数据库实例配置
"""

from .base_generator import BaseDataGenerator
from typing import Dict, List, Any
import random
import string

class InstanceGenerator(BaseDataGenerator):
    """数据库实例生成器"""
    
    def generate(self) -> List[Dict[str, Any]]:
        """
        生成数据库实例数据
        
        Returns:
            List[Dict[str, Any]]: 实例数据列表
        """
        instances = []
        
        # 从配置文件读取实例配置
        instance_configs = self.config.get("instances", [])
        
        for config in instance_configs:
            instance = {
                "name": config["name"],
                "db_type": config["db_type"],
                "host": config["host"],
                "port": config["port"],
                "credential_id": config.get("credential_id"),
                "description": config.get("description", ""),
                "tags": config.get("tags", []),
                "status": "active"
            }
            instances.append(instance)
        
        return instances
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        验证实例数据
        
        Args:
            data: 待验证的数据列表
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["name", "db_type", "host", "port"]
        valid_db_types = ["SQL Server", "MySQL", "Oracle"]
        
        for item in data:
            for field in required_fields:
                if field not in item:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
            
            if item["db_type"] not in valid_db_types:
                self.logger.error(f"无效的数据库类型: {item['db_type']}")
                return False
            
            if not isinstance(item["port"], int) or item["port"] <= 0:
                self.logger.error(f"无效的端口号: {item['port']}")
                return False
        
        return True
```

### 2.5 凭据数据生成器

```python
# scripts/data_generators/credential_generator.py
"""
凭据数据生成器
生成真实的凭据信息
"""

from .base_generator import BaseDataGenerator
from typing import Dict, List, Any
import secrets
import string

class CredentialGenerator(BaseDataGenerator):
    """凭据数据生成器"""
    
    def generate(self) -> List[Dict[str, Any]]:
        """
        生成凭据数据
        
        Returns:
            List[Dict[str, Any]]: 凭据数据列表
        """
        credentials = []
        
        # 从配置文件读取凭据配置
        credential_configs = self.config.get("credentials", [])
        
        for config in credential_configs:
            credential = {
                "name": config["name"],
                "credential_type": config["credential_type"],
                "db_type": config.get("db_type"),
                "username": config["username"],
                "password": self._encrypt_password(config["password"]),
                "instance_ids": config.get("instance_ids", []),
                "category_id": config.get("category_id")
            }
            credentials.append(credential)
        
        return credentials
    
    def _encrypt_password(self, password: str) -> str:
        """
        加密密码
        
        Args:
            password: 原始密码
            
        Returns:
            str: 加密后的密码
        """
        # 使用bcrypt加密密码
        import bcrypt
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        验证凭据数据
        
        Args:
            data: 待验证的数据列表
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["name", "credential_type", "username", "password"]
        valid_cred_types = ["数据库凭据", "SSH凭据", "Windows凭据"]
        
        for item in data:
            for field in required_fields:
                if field not in item:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
            
            if item["credential_type"] not in valid_cred_types:
                self.logger.error(f"无效的凭据类型: {item['credential_type']}")
                return False
            
            if len(item["username"]) < 3:
                self.logger.error("用户名长度不能少于3个字符")
                return False
        
        return True
```

### 2.6 账户数据生成器

```python
# scripts/data_generators/account_generator.py
"""
账户数据生成器
从真实数据库同步账户信息
"""

from .base_generator import BaseDataGenerator
from typing import Dict, List, Any
import pymssql
import pymysql
import cx_Oracle
from datetime import datetime

class AccountGenerator(BaseDataGenerator):
    """账户数据生成器"""
    
    def generate(self) -> List[Dict[str, Any]]:
        """
        从真实数据库同步账户数据
        
        Returns:
            List[Dict[str, Any]]: 账户数据列表
        """
        accounts = []
        
        # 获取所有实例配置
        instances = self.config.get("instances", [])
        
        for instance in instances:
            try:
                # 根据数据库类型连接并获取账户信息
                if instance["db_type"] == "SQL Server":
                    instance_accounts = self._sync_sql_server_accounts(instance)
                elif instance["db_type"] == "MySQL":
                    instance_accounts = self._sync_mysql_accounts(instance)
                elif instance["db_type"] == "Oracle":
                    instance_accounts = self._sync_oracle_accounts(instance)
                else:
                    self.logger.warning(f"不支持的数据库类型: {instance['db_type']}")
                    continue
                
                accounts.extend(instance_accounts)
                
            except Exception as e:
                self.logger.error(f"同步实例 {instance['name']} 的账户数据失败: {e}")
                continue
        
        return accounts
    
    def _sync_sql_server_accounts(self, instance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        同步SQL Server账户数据
        
        Args:
            instance: 实例配置
            
        Returns:
            List[Dict[str, Any]]: 账户数据列表
        """
        accounts = []
        
        try:
            # 连接SQL Server
            conn = pymssql.connect(
                server=instance["host"],
                port=instance["port"],
                user=instance["username"],
                password=instance["password"],
                database="master"
            )
            
            cursor = conn.cursor()
            
            # 查询用户账户信息
            query = """
            SELECT 
                name as username,
                create_date as created_at,
                modify_date as last_active,
                is_disabled as is_active
            FROM sys.server_principals 
            WHERE type IN ('S', 'U', 'G')
            AND name NOT LIKE '##%'
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                account = {
                    "username": row[0],
                    "db_type": "SQL Server",
                    "instance_id": instance["id"],
                    "created_at": row[1].isoformat() if row[1] else None,
                    "last_active": row[2].isoformat() if row[2] else None,
                    "permissions": self._get_sql_server_permissions(cursor, row[0]),
                    "category_id": None
                }
                accounts.append(account)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"同步SQL Server账户数据失败: {e}")
        
        return accounts
    
    def _sync_mysql_accounts(self, instance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        同步MySQL账户数据
        
        Args:
            instance: 实例配置
            
        Returns:
            List[Dict[str, Any]]: 账户数据列表
        """
        accounts = []
        
        try:
            # 连接MySQL
            conn = pymysql.connect(
                host=instance["host"],
                port=instance["port"],
                user=instance["username"],
                password=instance["password"],
                database="mysql"
            )
            
            cursor = conn.cursor()
            
            # 查询用户账户信息
            query = """
            SELECT 
                User as username,
                Create_time as created_at,
                password_last_changed as last_active,
                account_locked as is_locked
            FROM mysql.user 
            WHERE User != ''
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                account = {
                    "username": row[0],
                    "db_type": "MySQL",
                    "instance_id": instance["id"],
                    "created_at": row[1].isoformat() if row[1] else None,
                    "last_active": row[2].isoformat() if row[2] else None,
                    "permissions": self._get_mysql_permissions(cursor, row[0]),
                    "category_id": None
                }
                accounts.append(account)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"同步MySQL账户数据失败: {e}")
        
        return accounts
    
    def _sync_oracle_accounts(self, instance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        同步Oracle账户数据
        
        Args:
            instance: 实例配置
            
        Returns:
            List[Dict[str, Any]]: 账户数据列表
        """
        accounts = []
        
        try:
            # 连接Oracle
            dsn = cx_Oracle.makedsn(instance["host"], instance["port"], instance["service_name"])
            conn = cx_Oracle.connect(
                user=instance["username"],
                password=instance["password"],
                dsn=dsn
            )
            
            cursor = conn.cursor()
            
            # 查询用户账户信息
            query = """
            SELECT 
                username,
                created as created_at,
                expiry_date as last_active,
                account_status as status
            FROM dba_users 
            WHERE username NOT IN ('SYS', 'SYSTEM')
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                account = {
                    "username": row[0],
                    "db_type": "Oracle",
                    "instance_id": instance["id"],
                    "created_at": row[1].isoformat() if row[1] else None,
                    "last_active": row[2].isoformat() if row[2] else None,
                    "permissions": self._get_oracle_permissions(cursor, row[0]),
                    "category_id": None
                }
                accounts.append(account)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"同步Oracle账户数据失败: {e}")
        
        return accounts
    
    def _get_sql_server_permissions(self, cursor, username: str) -> Dict[str, Any]:
        """获取SQL Server用户权限"""
        # 实现SQL Server权限查询逻辑
        pass
    
    def _get_mysql_permissions(self, cursor, username: str) -> Dict[str, Any]:
        """获取MySQL用户权限"""
        # 实现MySQL权限查询逻辑
        pass
    
    def _get_oracle_permissions(self, cursor, username: str) -> Dict[str, Any]:
        """获取Oracle用户权限"""
        # 实现Oracle权限查询逻辑
        pass
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        验证账户数据
        
        Args:
            data: 待验证的数据列表
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["username", "db_type", "instance_id"]
        
        for item in data:
            for field in required_fields:
                if field not in item:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
        
        return True
```

## 3. 数据验证规范

### 3.1 连接验证器

```python
# scripts/validators/connection_validator.py
"""
数据库连接验证器
验证所有数据库连接是否真实可用
"""

import pymssql
import pymysql
import cx_Oracle
from typing import Dict, Any, List
import logging

class ConnectionValidator:
    """数据库连接验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_all_connections(self, instances: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        验证所有数据库连接
        
        Args:
            instances: 实例配置列表
            
        Returns:
            Dict[str, bool]: 连接验证结果
        """
        results = {}
        
        for instance in instances:
            try:
                if instance["db_type"] == "SQL Server":
                    result = self._validate_sql_server_connection(instance)
                elif instance["db_type"] == "MySQL":
                    result = self._validate_mysql_connection(instance)
                elif instance["db_type"] == "Oracle":
                    result = self._validate_oracle_connection(instance)
                else:
                    result = False
                    self.logger.error(f"不支持的数据库类型: {instance['db_type']}")
                
                results[instance["name"]] = result
                
            except Exception as e:
                self.logger.error(f"验证实例 {instance['name']} 连接失败: {e}")
                results[instance["name"]] = False
        
        return results
    
    def _validate_sql_server_connection(self, instance: Dict[str, Any]) -> bool:
        """验证SQL Server连接"""
        try:
            conn = pymssql.connect(
                server=instance["host"],
                port=instance["port"],
                user=instance["username"],
                password=instance["password"],
                database="master"
            )
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"SQL Server连接失败: {e}")
            return False
    
    def _validate_mysql_connection(self, instance: Dict[str, Any]) -> bool:
        """验证MySQL连接"""
        try:
            conn = pymysql.connect(
                host=instance["host"],
                port=instance["port"],
                user=instance["username"],
                password=instance["password"],
                database="mysql"
            )
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"MySQL连接失败: {e}")
            return False
    
    def _validate_oracle_connection(self, instance: Dict[str, Any]) -> bool:
        """验证Oracle连接"""
        try:
            dsn = cx_Oracle.makedsn(instance["host"], instance["port"], instance["service_name"])
            conn = cx_Oracle.connect(
                user=instance["username"],
                password=instance["password"],
                dsn=dsn
            )
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Oracle连接失败: {e}")
            return False
```

### 3.2 数据完整性验证器

```python
# scripts/validators/data_integrity_validator.py
"""
数据完整性验证器
验证生成的数据是否完整和一致
"""

from typing import Dict, List, Any
import logging

class DataIntegrityValidator:
    """数据完整性验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_data_integrity(self, data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        验证数据完整性
        
        Args:
            data: 包含所有数据的字典
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 验证外键关系
            self._validate_foreign_keys(data)
            
            # 验证数据一致性
            self._validate_data_consistency(data)
            
            # 验证必填字段
            self._validate_required_fields(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据完整性验证失败: {e}")
            return False
    
    def _validate_foreign_keys(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """验证外键关系"""
        # 验证实例与凭据的关系
        instances = data.get("instances", [])
        credentials = data.get("credentials", [])
        
        credential_ids = {cred["id"] for cred in credentials}
        
        for instance in instances:
            if instance.get("credential_id") and instance["credential_id"] not in credential_ids:
                raise ValueError(f"实例 {instance['name']} 引用了不存在的凭据ID: {instance['credential_id']}")
    
    def _validate_data_consistency(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """验证数据一致性"""
        # 验证数据库类型一致性
        instances = data.get("instances", [])
        credentials = data.get("credentials", [])
        
        for instance in instances:
            if instance.get("credential_id"):
                cred_id = instance["credential_id"]
                credential = next((c for c in credentials if c["id"] == cred_id), None)
                
                if credential and credential.get("db_type") != instance["db_type"]:
                    raise ValueError(f"实例 {instance['name']} 的数据库类型与凭据不匹配")
    
    def _validate_required_fields(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """验证必填字段"""
        # 验证用户数据
        users = data.get("users", [])
        for user in users:
            if not user.get("username") or not user.get("password"):
                raise ValueError("用户数据缺少必填字段")
        
        # 验证实例数据
        instances = data.get("instances", [])
        for instance in instances:
            if not instance.get("name") or not instance.get("host"):
                raise ValueError("实例数据缺少必填字段")
```

## 4. 配置文件规范

### 4.1 数据库配置文件

```json
# scripts/config/database_config.json
{
  "instances": [
    {
      "id": 1,
      "name": "生产SQL Server",
      "db_type": "SQL Server",
      "host": "192.168.1.100",
      "port": 1433,
      "username": "sa",
      "password": "your_password",
      "service_name": "MSSQLSERVER",
      "description": "生产环境SQL Server数据库",
      "tags": ["生产", "SQL Server"]
    },
    {
      "id": 2,
      "name": "测试MySQL",
      "db_type": "MySQL",
      "host": "192.168.1.101",
      "port": 3306,
      "username": "root",
      "password": "your_password",
      "service_name": "mysql",
      "description": "测试环境MySQL数据库",
      "tags": ["测试", "MySQL"]
    },
    {
      "id": 3,
      "name": "开发Oracle",
      "db_type": "Oracle",
      "host": "192.168.1.102",
      "port": 1521,
      "username": "system",
      "password": "your_password",
      "service_name": "ORCL",
      "description": "开发环境Oracle数据库",
      "tags": ["开发", "Oracle"]
    }
  ],
  "credentials": [
    {
      "id": 1,
      "name": "SQL Server管理员凭据",
      "credential_type": "数据库凭据",
      "db_type": "SQL Server",
      "username": "sa",
      "password": "your_password",
      "instance_ids": [1],
      "category_id": 1
    },
    {
      "id": 2,
      "name": "MySQL管理员凭据",
      "credential_type": "数据库凭据",
      "db_type": "MySQL",
      "username": "root",
      "password": "your_password",
      "instance_ids": [2],
      "category_id": 1
    },
    {
      "id": 3,
      "name": "Oracle管理员凭据",
      "credential_type": "数据库凭据",
      "db_type": "Oracle",
      "username": "system",
      "password": "your_password",
      "instance_ids": [3],
      "category_id": 1
    }
  ]
}
```

### 4.2 实例配置文件

```json
# scripts/config/instance_config.json
{
  "sql_server": {
    "default_port": 1433,
    "default_database": "master",
    "connection_timeout": 30,
    "query_timeout": 60,
    "max_connections": 20
  },
  "mysql": {
    "default_port": 3306,
    "default_database": "mysql",
    "connection_timeout": 30,
    "query_timeout": 60,
    "max_connections": 20
  },
  "oracle": {
    "default_port": 1521,
    "default_database": "ORCL",
    "connection_timeout": 30,
    "query_timeout": 60,
    "max_connections": 20
  }
}
```

## 5. 数据生成脚本使用说明

### 5.1 初始化数据

```bash
# 初始化所有数据
python scripts/init_data.py --init-all

# 初始化特定类型数据
python scripts/init_data.py --init-global-params
python scripts/init_data.py --init-instances
python scripts/init_data.py --init-credentials
python scripts/init_data.py --init-accounts
```

### 5.2 验证数据

```bash
# 验证所有数据
python scripts/init_data.py --validate-all

# 验证特定类型数据
python scripts/init_data.py --validate-connections
python scripts/init_data.py --validate-integrity
```

### 5.3 清理数据

```bash
# 清理所有数据
python scripts/init_data.py --clean-all

# 清理特定类型数据
python scripts/init_data.py --clean-instances
python scripts/init_data.py --clean-accounts
```

## 6. 注意事项

### 6.1 安全要求
- 所有密码必须加密存储
- 配置文件不得包含明文密码
- 使用环境变量管理敏感信息
- 定期轮换凭据

### 6.2 数据质量
- 所有数据必须真实可连接
- 定期验证数据完整性
- 监控数据同步状态
- 及时处理数据异常

### 6.3 性能要求
- 数据生成过程不得影响生产环境
- 使用连接池管理数据库连接
- 实现数据生成进度监控
- 支持增量数据更新

---

**重要提醒**: 本规范严格要求所有数据必须真实可用，禁止使用任何形式的模拟数据。所有数据生成脚本必须经过连接验证，确保数据的真实性和可用性。
