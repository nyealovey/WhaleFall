"""
数据库大小采集服务
支持 MySQL、SQL Server、PostgreSQL、Oracle 数据库大小采集
"""

import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
from app.services.connection_factory import ConnectionFactory
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
        self.db_connection = None
        self.logger = logger
    
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
            # 使用连接工厂创建连接
            self.db_connection = ConnectionFactory.create_connection(self.instance)
            if not self.db_connection:
                raise ValueError(f"不支持的数据库类型: {self.instance.db_type}")
            
            # 建立连接
            success = self.db_connection.connect()
            if success:
                self.logger.info(f"成功连接到实例 {self.instance.name} ({self.instance.db_type})")
            else:
                self.logger.error(f"连接实例 {self.instance.name} 失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"连接实例 {self.instance.name} 失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        try:
            if self.db_connection:
                self.db_connection.disconnect()
        except Exception as e:
            self.logger.warning(f"断开连接时出错: {str(e)}")
    
    def collect_database_sizes(self) -> List[Dict[str, Any]]:
        """
        采集数据库大小数据
        
        Returns:
            List[Dict[str, Any]]: 采集到的数据列表
        """
        if not self.db_connection or not self.db_connection.is_connected:
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
            self.logger.error(f"采集实例 {self.instance.name} 数据库大小时出错: {str(e)}")
            raise
    
    def _collect_mysql_sizes(self) -> List[Dict[str, Any]]:
        """采集 MySQL 数据库大小"""
        try:
            # 首先测试权限
            test_query = "SELECT COUNT(*) FROM information_schema.SCHEMATA"
            test_result = self.db_connection.execute_query(test_query)
            if not test_result:
                self.logger.error("MySQL 权限测试失败：无法访问 information_schema.SCHEMATA")
                return []
            
            self.logger.info(f"MySQL 权限测试通过，发现 {test_result[0][0]} 个数据库")
            
            # 使用统计表方式查询所有数据库大小
            query = """
                SELECT
                    s.SCHEMA_NAME AS database_name,
                    COALESCE(ROUND(SUM(COALESCE(t.data_length, 0) + COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS size_mb,
                    COALESCE(ROUND(SUM(COALESCE(t.data_length, 0)) / 1024 / 1024, 2), 0) AS data_size_mb,
                    COALESCE(ROUND(SUM(COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS index_size_mb
                FROM
                    information_schema.SCHEMATA s
                LEFT JOIN
                    information_schema.tables t ON s.SCHEMA_NAME = t.table_schema
                GROUP BY
                    s.SCHEMA_NAME
                ORDER BY
                    size_mb DESC
            """
            
            result = self.db_connection.execute_query(query)
            self.logger.info(f"MySQL 查询结果: {len(result) if result else 0} 行数据")
            
            if not result:
                self.logger.warning("MySQL 未查询到任何数据库大小数据")
                return []
            
            data = []
            for row in result:
                db_name = row[0]
                total_size = float(row[1] or 0)
                data_size = float(row[2] or 0)
                index_size = float(row[3] or 0)
                
                # 判断是否为系统数据库
                is_system_db = db_name in ('information_schema', 'performance_schema', 'mysql', 'sys')
                db_type = "系统数据库" if is_system_db else "用户数据库"
                
                data.append({
                    'database_name': db_name,
                    'size_mb': int(total_size),
                    'data_size_mb': int(data_size),
                    'log_size_mb': None,  # MySQL 没有单独的日志文件大小
                    'collected_date': date.today(),
                    'collected_at': datetime.utcnow(),
                    'is_system': is_system_db
                })
                
                self.logger.info(f"{db_type} {db_name}: 总大小 {total_size:.2f}MB, 数据 {data_size:.2f}MB, 索引 {index_size:.2f}MB")
            
            self.logger.info(f"MySQL 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
            return data
            
        except Exception as e:
            self.logger.error(f"MySQL 数据库大小采集失败: {str(e)}", exc_info=True)
            raise ValueError(f"MySQL 采集失败: {str(e)}")
    
    def _collect_sqlserver_sizes(self) -> List[Dict[str, Any]]:
        """采集 SQL Server 数据库大小"""
        # 使用 sys.master_files 直接查询所有数据库大小，避免使用 USE [database]
        query = """
            WITH DBSize AS (
                SELECT
                    DB_NAME(database_id) AS DatabaseName,
                    SUM(CASE WHEN type_desc = 'ROWS' THEN size * 8.0 / 1024 ELSE 0 END) AS DataFileSize_MB,
                    SUM(CASE WHEN type_desc = 'LOG' THEN size * 8.0 / 1024 ELSE 0 END) AS LogFileSize_MB
                FROM sys.master_files
                WHERE DB_NAME(database_id) IS NOT NULL
                GROUP BY database_id
            )
            SELECT
                DatabaseName,
                DataFileSize_MB,
                LogFileSize_MB,
                (DataFileSize_MB + LogFileSize_MB) AS TotalSize_MB
            FROM DBSize
            ORDER BY TotalSize_MB DESC
        """
        
        result = self.db_connection.execute_query(query)
        self.logger.info(f"SQL Server 查询结果: {len(result) if result else 0} 行数据")
        
        data = []
        
        for row in result:
            database_name = row[0]
            data_size_mb = int(float(row[1] or 0))
            log_size_mb = int(float(row[2] or 0))
            total_size_mb = int(float(row[3] or 0))
            
            data.append({
                'database_name': database_name,
                'size_mb': total_size_mb,
                'data_size_mb': data_size_mb,
                'log_size_mb': log_size_mb,
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
            
            self.logger.info(f"SQL Server 数据库 {database_name}: 总大小 {total_size_mb} MB, 数据大小 {data_size_mb} MB, 日志大小 {log_size_mb} MB")
        
        self.logger.info(f"SQL Server 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def _collect_postgresql_sizes(self) -> List[Dict[str, Any]]:
        """采集 PostgreSQL 数据库大小"""
        query = """
            SELECT
                datname AS database_name,
                pg_database_size(datname) / 1024 / 1024 AS size_mb,
                pg_database_size(datname) / 1024 / 1024 AS data_size_mb
            FROM
                pg_database
            WHERE
                datistemplate = false
            ORDER BY
                size_mb DESC
        """
        
        result = self.db_connection.execute_query(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row[0],
                'size_mb': int(row[1] or 0),
                'data_size_mb': int(row[2] or 0),
                'log_size_mb': None,  # PostgreSQL 不单独采集日志大小
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        self.logger.info(f"PostgreSQL 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def _collect_oracle_sizes(self) -> List[Dict[str, Any]]:
        """采集 Oracle 数据库大小"""
        query = """
            SELECT
                tablespace_name AS database_name,
                SUM(bytes) / 1024 / 1024 AS size_mb,
                SUM(bytes) / 1024 / 1024 AS data_size_mb
            FROM
                dba_data_files
            GROUP BY
                tablespace_name
            ORDER BY
                size_mb DESC
        """
        
        result = self.db_connection.execute_query(query)
        data = []
        
        for row in result:
            data.append({
                'database_name': row[0],
                'size_mb': int(row[1] or 0),
                'data_size_mb': int(row[2] or 0),
                'log_size_mb': None,  # Oracle 不单独采集日志大小
                'collected_date': date.today(),
                'collected_at': datetime.utcnow()
            })
        
        self.logger.info(f"Oracle 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def save_collected_data(self, data: List[Dict[str, Any]]) -> int:
        """
        保存采集到的数据，实现软删除机制
        
        Args:
            data: 采集到的数据列表
            
        Returns:
            int: 保存的记录数量
        """
        if not data:
            return 0
        
        # 获取当前采集到的数据库名称列表
        current_databases = {item['database_name'] for item in data}
        
        # 获取今天已存在的所有数据库记录
        today = date.today()
        existing_records = DatabaseSizeStat.query.filter_by(
            instance_id=self.instance.id,
            collected_date=today
        ).all()
        
        # 标记已删除的数据库
        deleted_count = 0
        for record in existing_records:
            if record.database_name not in current_databases and not record.is_deleted:
                record.is_deleted = True
                record.deleted_at = datetime.utcnow()
                deleted_count += 1
                self.logger.info(f"标记数据库 {record.database_name} 为已删除")
        
        # 保存或更新当前采集的数据
        saved_count = 0
        for item in data:
            try:
                # 检查是否已存在相同日期的记录
                existing = DatabaseSizeStat.query.filter_by(
                    instance_id=self.instance.id,
                    database_name=item['database_name'],
                    collected_date=item['collected_date']
                ).first()
                
                if existing:
                    # 更新现有记录
                    existing.size_mb = item['size_mb']
                    existing.data_size_mb = item['data_size_mb']
                    existing.log_size_mb = item['log_size_mb']
                    existing.collected_at = item['collected_at']
                    # 如果之前被标记为删除，现在恢复
                    if existing.is_deleted:
                        existing.is_deleted = False
                        existing.deleted_at = None
                        self.logger.info(f"恢复数据库 {item['database_name']} 为在线状态")
                else:
                    # 创建新记录
                    new_stat = DatabaseSizeStat(
                        instance_id=self.instance.id,
                        database_name=item['database_name'],
                        size_mb=item['size_mb'],
                        data_size_mb=item['data_size_mb'],
                        log_size_mb=item['log_size_mb'],
                        collected_date=item['collected_date'],
                        collected_at=item['collected_at'],
                        is_deleted=False
                    )
                    db.session.add(new_stat)
                
                saved_count += 1
                
            except Exception as e:
                self.logger.error(f"保存数据库大小数据失败: {str(e)}")
                continue
        
        try:
            db.session.commit()
            self.logger.info(f"成功保存 {saved_count} 条数据库大小记录，标记 {deleted_count} 个数据库为已删除")
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"提交数据库大小数据失败: {str(e)}")
            raise
        
        return saved_count
    
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
            self.logger.error(f"实例 {self.instance.name} 采集和保存数据失败: {str(e)}")
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
    
    return results