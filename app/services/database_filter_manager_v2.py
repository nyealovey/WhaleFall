"""
泰摸鱼吧 - 数据库过滤规则管理器 V2
使用独立的数据库过滤规则类，从配置文件加载数据
"""

import logging
import os
import yaml
from typing import Any, Dict, List, Tuple

from .database_filters import (
    MySQLDatabaseFilter,
    PostgreSQLDatabaseFilter, 
    SQLServerDatabaseFilter,
    OracleDatabaseFilter
)

logger = logging.getLogger(__name__)


class DatabaseFilterManagerV2:
    """数据库过滤规则管理器 V2"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", "database_filters.yaml"
        )
        self.config_data = self._load_config()
        self.filters = self._create_filters()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('database_filters', {})
        except Exception as e:
            logger.error(f"加载过滤规则配置文件失败: {str(e)}")
            return {}
    
    def _create_filters(self) -> Dict[str, Any]:
        """创建过滤规则实例"""
        return {
            "mysql": MySQLDatabaseFilter(self.config_data.get("mysql", {})),
            "postgresql": PostgreSQLDatabaseFilter(self.config_data.get("postgresql", {})),
            "sqlserver": SQLServerDatabaseFilter(self.config_data.get("sqlserver", {})),
            "oracle": OracleDatabaseFilter(self.config_data.get("oracle", {}))
        }
    
    def get_filter(self, db_type: str):
        """获取指定数据库类型的过滤规则"""
        return self.filters.get(db_type)
    
    def should_include_user(self, db_type: str, username: str) -> bool:
        """
        判断是否应该包含指定用户
        
        Args:
            db_type: 数据库类型
            username: 用户名
            
        Returns:
            bool: True表示应该包含，False表示应该排除
        """
        filter_instance = self.get_filter(db_type)
        if not filter_instance:
            logger.warning(f"未找到数据库类型 {db_type} 的过滤规则")
            return True
        
        return filter_instance.should_include_user(username)
    
    def build_where_clause(self, db_type: str, username_field: str) -> Tuple[str, List[Any]]:
        """
        构建WHERE子句
        
        Args:
            db_type: 数据库类型
            username_field: 用户名字段名
            
        Returns:
            Tuple[str, List[Any]]: WHERE子句和参数列表
        """
        filter_instance = self.get_filter(db_type)
        if not filter_instance:
            logger.warning(f"未找到数据库类型 {db_type} 的过滤规则")
            return "1=1", []
        
        return filter_instance.build_where_clause(username_field)
    
    def get_filter_rules(self, db_type: str = None) -> Dict[str, Any]:
        """
        获取过滤规则信息
        
        Args:
            db_type: 数据库类型，None表示获取所有规则
            
        Returns:
            Dict[str, Any]: 过滤规则信息
        """
        if db_type:
            filter_instance = self.get_filter(db_type)
            if filter_instance:
                return filter_instance.get_filter_info()
            return {}
        else:
            return {
                db_type: filter_instance.get_filter_info()
                for db_type, filter_instance in self.filters.items()
            }
    
    def get_supported_database_types(self) -> List[str]:
        """获取支持的数据库类型列表"""
        return list(self.filters.keys())
