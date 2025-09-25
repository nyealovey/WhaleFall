"""
数据库大小采集服务
支持 MySQL、SQL Server、PostgreSQL、Oracle 数据库大小采集
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
from app import db

logger = logging.getLogger(__name__)


class DatabaseSizeCollectorService:
    """数据库大小采集服务"""
    
    def __init__(self, instance: Instance):
        """
        初始化采集服务
        
        Args:
            instance: 数据库实例对象
        """
        self.instance = instance
        self.engine = None
        self.connection = None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
    
    def connect(self) -> bool:
        """
        连接到数据库实例
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 构建连接字符串
            connection_string = self._build_connection_string()
            
            # 创建数据库引擎
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={'connect_timeout': 30}
            )
            
            # 测试连接
            self.connection = self.engine.connect()
            logger.info(f"成功连接到实例 {self.instance.name} ({self.instance.db_type})")
            return True
            
        except Exception as e:
            logger.error(f"连接实例 {self.instance.name} 失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        try:
            if self.connection:
                self.connection.close()
            if self.engine:
                self.engine.dispose()
        except Exception as e:
            logger.warning(f"断开连接时出错: {str(e)}")
    
    def _build_connection_string(self) -> str:
        """
        构建数据库连接字符串
        
        Returns:
            str: 连接字符串
        """
        if not self.instance.credential:
            raise ValueError(f"实例 {self.instance.name} 没有关联的凭据")
        
        credential = self.instance.credential
        
        if self.instance.db_type.lower() == 'mysql':
            return f"mysql+pymysql://{credential.username}:{credential.password}@{self.instance.host}:{self.instance.port}/{self.instance.database_name or 'information_schema'}"
        
        elif self.instance.db_type.lower() == 'sqlserver':
            return f"mssql+pyodbc://{credential.username}:{credential.password}@{self.instance.host}:{self.instance.port}/{self.instance.database_name or 'master'}?driver=ODBC+Driver+17+for+SQL+Server"
        
        elif self.instance.db_type.lower() == 'postgresql':
            return f"postgresql://{credential.username}:{credential.password}@{self.instance.host}:{self.instance.port}/{self.instance.database_name or 'postgres'}"
        
        elif self.instance.db_type.lower() == 'oracle':
            return f"oracle://{credential.username}:{credential.password}@{self.instance.host}:{self.instance.port}/{self.instance.database_name or 'xe'}"
        
        else:
            raise ValueError(f"不支持的数据库类型: {self.instance.db_type}")
    
    def collect_database_sizes(self) -> List[Dict[str, Any]]:
        """
        采集数据库大小数据
        
        Returns:
            List[Dict[str, Any]]: 采集到的数据列表
        """
        if not self.connection:
            raise RuntimeError("数据库连接未建立")
        
        try:
            if self.instance.db_type.lower() == 'mysql':
                return self._collect_mysql_sizes()
            elif self.instance.db_type.lower() == 'sqlserver':
                return self._collect_sqlserver_sizes()
            elif self.instance.db_type.lower() == 'postgresql':
                return self._collect_postgresql_sizes()
            elif self.instance.db_type.lower() == 'oracle':
                return self._collect_oracle_sizes()
            else:
                raise ValueError(f"不支持的数据库类型: {self.instance.db_type}")
                
        except Exception as e:
            logger.error(f"采集实例 {self.instance.name} 数据库大小时出错: {str(e)}")
            raise
    
    def _collect_mysql_sizes(self) -> List[Dict[str, Any]]:
        """采集 MySQL 数据库大小"""
        query = text("""
            SELECT
                table_schema AS database_name,
                SUM(data_length + index_length) / 1024 / 1024 AS size_mb,
                SUM(data_length) / 1024 / 1024 AS data_size_mb
            FROM
                information_schema.TABLES
            WHERE
                table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
            GROUP BY
                table_schema
        """)
        
        result = self.connection.execute(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row.database_name,
                'size_mb': int(row.size_mb or 0),
                'data_size_mb': int(row.data_size_mb or 0),
                'log_size_mb': None,  # MySQL 不采集日志大小
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        logger.info(f"MySQL 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def _collect_sqlserver_sizes(self) -> List[Dict[str, Any]]:
        """采集 SQL Server 数据库大小"""
        query = text("""
            SELECT
                d.name AS database_name,
                SUM(CAST(mf.size AS BIGINT) * 8 / 1024) AS size_mb,
                SUM(CASE WHEN mf.type = 0 THEN CAST(mf.size AS BIGINT) * 8 / 1024 ELSE 0 END) AS data_size_mb,
                SUM(CASE WHEN mf.type = 1 THEN CAST(mf.size AS BIGINT) * 8 / 1024 ELSE 0 END) AS log_size_mb
            FROM
                sys.databases d
                INNER JOIN sys.master_files mf ON d.database_id = mf.database_id
            WHERE
                d.database_id > 4  -- 排除系统数据库
            GROUP BY
                d.name
        """)
        
        result = self.connection.execute(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row.database_name,
                'size_mb': int(row.size_mb or 0),
                'data_size_mb': int(row.data_size_mb or 0),
                'log_size_mb': int(row.log_size_mb or 0),
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        logger.info(f"SQL Server 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def _collect_postgresql_sizes(self) -> List[Dict[str, Any]]:
        """采集 PostgreSQL 数据库大小"""
        query = text("""
            SELECT
                datname AS database_name,
                pg_database_size(datname) / 1024 / 1024 AS size_mb,
                pg_database_size(datname) / 1024 / 1024 AS data_size_mb
            FROM
                pg_database
            WHERE
                datistemplate = false
        """)
        
        result = self.connection.execute(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row.database_name,
                'size_mb': int(row.size_mb or 0),
                'data_size_mb': int(row.data_size_mb or 0),
                'log_size_mb': None,  # PostgreSQL 不单独采集日志大小
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        logger.info(f"PostgreSQL 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def _collect_oracle_sizes(self) -> List[Dict[str, Any]]:
        """采集 Oracle 数据库大小"""
        query = text("""
            SELECT
                tablespace_name AS database_name,
                SUM(bytes) / 1024 / 1024 AS size_mb,
                SUM(bytes) / 1024 / 1024 AS data_size_mb
            FROM
                dba_data_files
            GROUP BY
                tablespace_name
        """)
        
        result = self.connection.execute(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row.database_name,
                'size_mb': int(row.size_mb or 0),
                'data_size_mb': int(row.data_size_mb or 0),
                'log_size_mb': None,  # Oracle 不单独采集日志大小
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        logger.info(f"Oracle 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def save_collected_data(self, data: List[Dict[str, Any]]) -> int:
        """
        保存采集到的数据到数据库
        
        Args:
            data: 采集到的数据列表
            
        Returns:
            int: 保存的记录数量
        """
        if not data:
            return 0
        
        try:
            saved_count = 0
            today = date.today()
            
            for item in data:
                # 先删除今日已有数据（确保每日唯一性）
                DatabaseSizeStat.query.filter(
                    DatabaseSizeStat.instance_id == self.instance.id,
                    DatabaseSizeStat.database_name == item['database_name'],
                    DatabaseSizeStat.collected_date == today
                ).delete()
                
                # 创建新记录
                stat = DatabaseSizeStat(
                    instance_id=self.instance.id,
                    database_name=item['database_name'],
                    size_mb=item['size_mb'],
                    data_size_mb=item['data_size_mb'],
                    log_size_mb=item['log_size_mb'],
                    collected_date=item['collected_date'],
                    collected_at=item['collected_at']
                )
                
                db.session.add(stat)
                saved_count += 1
            
            db.session.commit()
            logger.info(f"实例 {self.instance.name} 保存了 {saved_count} 条数据库大小记录")
            return saved_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"保存实例 {self.instance.name} 数据时出错: {str(e)}")
            raise
    
    def collect_and_save(self) -> int:
        """
        采集并保存数据库大小数据
        
        Returns:
            int: 保存的记录数量
        """
        try:
            # 采集数据
            data = self.collect_database_sizes()
            
            # 保存数据
            saved_count = self.save_collected_data(data)
            
            return saved_count
            
        except Exception as e:
            logger.error(f"实例 {self.instance.name} 采集和保存数据失败: {str(e)}")
            raise


def collect_all_instances_database_sizes() -> Dict[str, Any]:
    """
    采集所有活跃实例的数据库大小数据
    
    Returns:
        Dict[str, Any]: 采集结果统计
    """
    logger.info("开始采集所有实例的数据库大小数据...")
    
    # 获取所有活跃实例
    instances = Instance.query.filter_by(is_active=True).all()
    
    if not instances:
        logger.warning("没有找到活跃的数据库实例")
        return {
            'status': 'success',
            'total_instances': 0,
            'processed_instances': 0,
            'total_records': 0,
            'errors': []
        }
    
    results = {
        'status': 'success',
        'total_instances': len(instances),
        'processed_instances': 0,
        'total_records': 0,
        'errors': []
    }
    
    for instance in instances:
        try:
            logger.info(f"开始采集实例 {instance.name} ({instance.db_type})")
            
            with DatabaseSizeCollectorService(instance) as collector:
                saved_count = collector.collect_and_save()
                results['processed_instances'] += 1
                results['total_records'] += saved_count
                
                logger.info(f"实例 {instance.name} 采集完成，保存了 {saved_count} 条记录")
                
        except Exception as e:
            error_msg = f"实例 {instance.name} 采集失败: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            continue
    
    logger.info(f"数据库大小采集完成: 处理了 {results['processed_instances']}/{results['total_instances']} 个实例，共保存 {results['total_records']} 条记录")
    
    if results['errors']:
        results['status'] = 'partial_success'
        logger.warning(f"采集过程中出现 {len(results['errors'])} 个错误")
    
    return results
