"""
鲸落 - 数据库发现服务
用于发现和更新实例中的数据库列表
"""

from typing import List, Dict, Any
from datetime import date, datetime
from app import db
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.utils.structlog_config import get_logger


class DatabaseDiscoveryService:
    """数据库发现服务"""
    
    def __init__(self, instance: Instance):
        self.instance = instance
        self.logger = get_logger(__name__)
        self.db_connection = None
    
    def discover_databases(self) -> List[str]:
        """
        发现实例中的所有数据库
        
        Returns:
            List[str]: 数据库名称列表
        """
        try:
            if self.instance.db_type == 'mysql':
                return self._discover_mysql_databases()
            elif self.instance.db_type == 'postgresql':
                return self._discover_postgresql_databases()
            elif self.instance.db_type == 'sqlserver':
                return self._discover_sqlserver_databases()
            elif self.instance.db_type == 'oracle':
                return self._discover_oracle_databases()
            else:
                raise ValueError(f"不支持的数据库类型: {self.instance.db_type}")
        except Exception as e:
            self.logger.error(f"发现实例 {self.instance.name} 数据库失败: {str(e)}")
            raise
    
    def _discover_mysql_databases(self) -> List[str]:
        """发现 MySQL 数据库"""
        query = "SHOW DATABASES"
        result = self.db_connection.execute_query(query)
        
        if not result:
            self.logger.warning(f"MySQL 实例 {self.instance.name} 未查询到任何数据库")
            return []
        
        databases = [row[0] for row in result]
        self.logger.info(f"MySQL 实例 {self.instance.name} 发现 {len(databases)} 个数据库")
        return databases
    
    def _discover_postgresql_databases(self) -> List[str]:
        """发现 PostgreSQL 数据库"""
        query = """
            SELECT datname 
            FROM pg_database 
            ORDER BY datname
        """
        result = self.db_connection.execute_query(query)
        
        if not result:
            self.logger.warning(f"PostgreSQL 实例 {self.instance.name} 未查询到任何数据库")
            return []
        
        databases = [row[0] for row in result]
        self.logger.info(f"PostgreSQL 实例 {self.instance.name} 发现 {len(databases)} 个数据库")
        return databases
    
    def _discover_sqlserver_databases(self) -> List[str]:
        """发现 SQL Server 数据库"""
        query = """
            SELECT name 
            FROM sys.databases 
            ORDER BY name
        """
        result = self.db_connection.execute_query(query)
        
        if not result:
            self.logger.warning(f"SQL Server 实例 {self.instance.name} 未查询到任何数据库")
            return []
        
        databases = [row[0] for row in result]
        self.logger.info(f"SQL Server 实例 {self.instance.name} 发现 {len(databases)} 个数据库")
        return databases
    
    def _discover_oracle_databases(self) -> List[str]:
        """发现 Oracle 数据库"""
        # Oracle 通常一个实例对应一个数据库，这里返回实例名
        databases = [self.instance.name]
        self.logger.info(f"Oracle 实例 {self.instance.name} 发现 1 个数据库")
        return databases
    
    def update_database_list(self, discovered_databases: List[str]) -> Dict[str, int]:
        """
        更新数据库列表到 instance_databases 表
        
        Args:
            discovered_databases: 发现的数据库列表
            
        Returns:
            Dict[str, int]: 统计信息
        """
        try:
            # 获取当前活跃的数据库列表
            current_databases = db.session.query(InstanceDatabase.database_name).filter(
                InstanceDatabase.instance_id == self.instance.id,
                InstanceDatabase.is_active == True
            ).all()
            current_db_names = {row[0] for row in current_databases}
            
            discovered_db_names = set(discovered_databases)
            
            # 计算新增和删除的数据库
            new_databases = discovered_db_names - current_db_names
            deleted_databases = current_db_names - discovered_db_names
            
            # 添加新发现的数据库
            for db_name in new_databases:
                instance_db = InstanceDatabase(
                    instance_id=self.instance.id,
                    database_name=db_name,
                    first_seen_date=date.today(),
                    last_seen_date=date.today(),
                    is_active=True
                )
                db.session.add(instance_db)
                self.logger.info(f"发现新数据库: {db_name}")
            
            # 标记已删除的数据库
            for db_name in deleted_databases:
                InstanceDatabase.mark_as_deleted(self.instance.id, db_name)
                self.logger.info(f"标记数据库为已删除: {db_name}")
            
            # 更新现有数据库的最后发现时间
            for db_name in discovered_db_names & current_db_names:
                InstanceDatabase.update_database_status(
                    self.instance.id, 
                    db_name, 
                    date.today()
                )
            
            db.session.commit()
            
            result = {
                'databases_found': len(discovered_databases),
                'databases_added': len(new_databases),
                'databases_deleted': len(deleted_databases),
                'databases_updated': len(discovered_db_names & current_db_names)
            }
            
            self.logger.info(f"实例 {self.instance.name} 数据库列表更新完成: {result}")
            return result
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"更新实例 {self.instance.name} 数据库列表失败: {str(e)}")
            raise
    
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            from app.services.database_connection_service import DatabaseConnectionService
            
            if not self.db_connection:
                self.db_connection = DatabaseConnectionService(self.instance)
            return self.db_connection.connect()
            
        except Exception as e:
            self.logger.error(f"连接实例 {self.instance.name} 失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.db_connection:
            self.db_connection.disconnect()
            self.db_connection = None
