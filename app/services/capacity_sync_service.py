"""
数据库大小采集服务
支持 MySQL、SQL Server、PostgreSQL、Oracle 数据库大小采集
"""

import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from app.models.instance import Instance
from app.constants import TaskStatus
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_size_stat import InstanceSizeStat
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_system_logger
from app import db

logger = get_system_logger()


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
            # 如果已经有连接对象，直接使用
            if self.db_connection:
                self.logger.info(f"使用现有连接实例 {self.instance.name} ({self.instance.db_type})")
                return True
            
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
            
            self.logger.info(
                "mysql_schema_access_verified",
                instance=self.instance.name,
                schema_count=test_result[0][0],
            )
            
            tablespace_stats = self._collect_mysql_tablespace_sizes()
            if not tablespace_stats:
                error_msg = (
                    "MySQL 表空间统计未返回任何数据，请检查实例版本、权限或视图可用性"
                )
                self.logger.error(error_msg, instance=self.instance.name, main_version=self.instance.main_version)
                raise ValueError(error_msg)
            
            data = self._build_mysql_stats_from_tablespaces(tablespace_stats)
            if not data:
                error_msg = "MySQL 表空间统计返回结果无法解析，请检查数据格式"
                self.logger.error(error_msg, instance=self.instance.name)
                raise ValueError(error_msg)
            
            self.logger.info("mysql_tablespace_collection_success", instance=self.instance.name, database_count=len(data))
            return data
            
        except Exception as e:
            self.logger.error(f"MySQL 数据库大小采集失败: {str(e)}", exc_info=True)
            raise ValueError(f"MySQL 采集失败: {str(e)}")
    
    def _collect_mysql_tablespace_sizes(self) -> List[Dict[str, Any]]:
        """
        基于 InnoDB 表空间统计 MySQL 数据库大小
        
        Returns:
            List[Dict[str, Any]]: [{'database_name': str, 'total_bytes': int}, ...]
        """
        normalized_version = (self.instance.main_version or "").strip().lower()
        
        # 先尝试与版本匹配的视图，不存在时回退
        queries: List[Tuple[str, str]] = []
        query_innodb_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_TABLESPACES ts
        """
        query_innodb_sys_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_SYS_TABLESPACES ts
        """
        
        if normalized_version.startswith("8"):
            queries = [
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
            ]
        elif normalized_version.startswith("5"):
            queries = [
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
            ]
        else:
            queries = [
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
            ]
        
        aggregated: Dict[str, int] = {}
        
        for label, query in queries:
            try:
                result = self.db_connection.execute_query(query)
                if result:
                    self.logger.info(
                        "mysql_tablespace_query_success",
                        instance=self.instance.name,
                        view=label,
                        record_count=len(result),
                    )
                    for row in result:
                        if not row:
                            continue
                        raw_name = row[0]
                        if not raw_name:
                            continue
                        raw_name_str = str(raw_name)
                        db_name = raw_name_str.split('/', 1)[0] if '/' in raw_name_str else raw_name_str
                        total_bytes = row[1] if len(row) > 1 else None
                        if total_bytes is None:
                            continue
                        try:
                            total_bytes_int = int(total_bytes)
                        except (TypeError, ValueError):
                            total_bytes_int = int(float(total_bytes or 0))
                        aggregated[db_name] = aggregated.get(db_name, 0) + max(total_bytes_int, 0)
                    if aggregated:
                        break
                else:
                    self.logger.info(
                        "mysql_tablespace_query_empty",
                        instance=self.instance.name,
                        view=label,
                    )
            except Exception as e:
                self.logger.warning(
                    "mysql_tablespace_query_failed",
                    instance=self.instance.name,
                    view=label,
                    error=str(e),
                    exc_info=True,
                )
        
        # 确保所有数据库都包含在结果中，即使没有表空间统计数据
        try:
            databases_result = self.db_connection.execute_query("SHOW DATABASES")
            if databases_result:
                for row in databases_result:
                    if not row:
                        continue
                    db_name = str(row[0])
                    if not db_name:
                        continue
                    aggregated.setdefault(db_name, 0)
        except Exception as e:
            self.logger.warning(
                "mysql_show_databases_failed",
                instance=self.instance.name,
                error=str(e),
                exc_info=True,
            )
        
        return [
            {'database_name': name, 'total_bytes': total}
            for name, total in aggregated.items()
        ]
    
    def _build_mysql_stats_from_tablespaces(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将表空间统计结果转换为数据库大小采集结构"""
        if not stats:
            return []
        
        from app.utils.time_utils import time_utils
        
        system_databases = {'information_schema', 'performance_schema', 'mysql', 'sys'}
        china_now = time_utils.now_china()
        collected_at = time_utils.now()
        
        data: List[Dict[str, Any]] = []
        for item in stats:
            db_name = item.get('database_name')
            total_bytes = item.get('total_bytes', 0)
            if not db_name:
                continue
            
            try:
                total_bytes_int = int(total_bytes)
            except (TypeError, ValueError):
                total_bytes_int = int(float(total_bytes or 0))
            
            size_mb = max(total_bytes_int // (1024 * 1024), 0)
            is_system_db = db_name in system_databases
            db_type = "系统数据库" if is_system_db else "用户数据库"
            
            data.append({
                'database_name': db_name,
                'size_mb': size_mb,
                'data_size_mb': size_mb,  # 表空间统计无法区分数据/索引，统一使用总量
                'log_size_mb': None,
                'collected_date': china_now.date(),
                'collected_at': collected_at,
                'is_system': is_system_db
            })
            
            self.logger.debug(
                "mysql_database_tablespace_size",
                instance=self.instance.name,
                database=db_name,
                size_mb=size_mb,
                system_database=is_system_db,
            )
        
        return data
    
    def _collect_mysql_sizes_from_information_schema(self) -> List[Dict[str, Any]]:
        """回退到 information_schema.tables 方式采集 MySQL 大小"""
        query = """
            SELECT
                s.SCHEMA_NAME AS database_name,
                COALESCE(ROUND(SUM(COALESCE(t.data_length, 0) + COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS total_size_mb,
                COALESCE(ROUND(SUM(COALESCE(t.data_length, 0)) / 1024 / 1024, 2), 0) AS data_size_mb,
                COALESCE(ROUND(SUM(COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS index_size_mb
            FROM
                information_schema.SCHEMATA s
            LEFT JOIN
                information_schema.tables t ON s.SCHEMA_NAME = t.table_schema
            GROUP BY
                s.SCHEMA_NAME
            ORDER BY
                total_size_mb DESC
        """
        
        result = self.db_connection.execute_query(query)
        self.logger.info(f"MySQL (information_schema.tables) 查询结果: {len(result) if result else 0} 行数据")
        
        if not result:
            error_msg = "MySQL 未查询到任何数据库大小数据"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        from app.utils.time_utils import time_utils
        china_now = time_utils.now_china()
        
        data = []
        for row in result:
            db_name = row[0]
            total_size = float(row[1] or 0)
            data_size = float(row[2] or 0)
            
            is_system_db = db_name in ('information_schema', 'performance_schema', 'mysql', 'sys')
            db_type = "系统数据库" if is_system_db else "用户数据库"
            
            data.append({
                'database_name': db_name,
                'size_mb': int(total_size),
                'data_size_mb': int(data_size),
                'log_size_mb': None,
                'collected_date': china_now.date(),
                'collected_at': time_utils.now(),
                'is_system': is_system_db
            })
            
            self.logger.info(f"{db_type} {db_name}: 总大小 {total_size:.2f}MB, 数据 {data_size:.2f}MB")
        
        return data
    
    def _collect_sqlserver_sizes(self) -> List[Dict[str, Any]]:
        """采集 SQL Server 数据库大小"""
        # 只采集数据文件大小，不采集日志文件大小
        query = """
            SELECT
                DB_NAME(database_id) AS DatabaseName,
                SUM(CASE WHEN type_desc = 'ROWS' THEN size * 8.0 / 1024 ELSE 0 END) AS DataFileSize_MB
            FROM sys.master_files
            WHERE DB_NAME(database_id) IS NOT NULL
            GROUP BY database_id
            ORDER BY DataFileSize_MB DESC
        """
        
        result = self.db_connection.execute_query(query)
        self.logger.info(f"SQL Server 查询结果: {len(result) if result else 0} 行数据")
        
        if not result:
            error_msg = "SQL Server 未查询到任何数据库大小数据"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        data = []
        
        for row in result:
            database_name = row[0]
            data_size_mb = int(float(row[1] or 0))
            
            # 使用中国时区统一处理日期
            from app.utils.time_utils import time_utils
            china_now = time_utils.now_china()
            
            data.append({
                'database_name': database_name,
                'size_mb': data_size_mb,  # 总大小 = 数据大小
                'data_size_mb': data_size_mb,
                'log_size_mb': None,  # 不采集日志大小
                'collected_date': china_now.date(),  # 使用中国时区的日期
                'collected_at': time_utils.now()  # 使用UTC时间戳
            })
            
            self.logger.info(f"SQL Server 数据库 {database_name}: 数据大小 {data_size_mb} MB")
        
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
        
        if not result:
            error_msg = "PostgreSQL 未查询到任何数据库大小数据"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        data = []
        
        # 使用中国时区统一处理日期
        from app.utils.time_utils import time_utils
        china_now = time_utils.now_china()
        
        for row in result:
            data.append({
                'database_name': row[0],
                'size_mb': int(row[1] or 0),
                'data_size_mb': int(row[2] or 0),
                'log_size_mb': None,  # PostgreSQL 不单独采集日志大小
                'collected_date': china_now.date(),  # 使用中国时区的日期
                'collected_at': time_utils.now()  # 使用UTC时间戳
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
        
        if not result:
            error_msg = "Oracle 未查询到任何数据库大小数据"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        data = []
        
        # 使用中国时区统一处理日期
        from app.utils.time_utils import time_utils
        china_now = time_utils.now_china()
        
        for row in result:
            data.append({
                'database_name': row[0],
                'size_mb': int(row[1] or 0),
                'data_size_mb': int(row[2] or 0),
                'log_size_mb': None,  # Oracle 不单独采集日志大小
                'collected_date': china_now.date(),  # 使用中国时区的日期
                'collected_at': time_utils.now()  # 使用UTC时间戳
            })
        
        self.logger.info(f"Oracle 实例 {self.instance.name} 采集到 {len(data)} 个数据库")
        return data
    
    def save_collected_data(self, data: List[Dict[str, Any]]) -> int:
        """
        保存采集到的数据库大小数据
        
        Args:
            data: 采集到的数据列表
            
        Returns:
            int: 保存的记录数量
        """
        if not data:
            return 0
        
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
                    existing.updated_at = item['collected_at']
                    self.logger.debug(f"更新数据库 {item['database_name']} 大小记录")
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
                        updated_at=item['collected_at'],
                        is_deleted=False
                    )
                    db.session.add(new_stat)
                    self.logger.debug(f"创建数据库 {item['database_name']} 大小记录")
                
                saved_count += 1
                
            except Exception as e:
                self.logger.error(f"保存数据库 {item['database_name']} 大小数据失败: {str(e)}")
                continue
        
        try:
            db.session.commit()
            self.logger.info(f"成功保存 {saved_count} 条数据库大小记录")
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"提交数据库大小数据失败: {str(e)}")
            raise
        
        return saved_count
    
    def save_instance_size_stat(self, data: List[Dict[str, Any]]) -> bool:
        """
        保存实例大小统计数据
        
        Args:
            data: 采集到的数据库大小数据列表
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if not data:
                self.logger.warning(f"实例 {self.instance.name} 没有数据库大小数据，跳过实例统计保存")
                return False
            
            # 计算实例总大小和数据库数量
            total_size = sum(item['size_mb'] for item in data)
            database_count = len(data)
            
            # 使用中国时区统一处理日期
            from app.utils.time_utils import time_utils
            china_now = time_utils.now_china()
            collected_date = china_now.date()
            
            # 检查是否已存在今天的记录
            existing_stat = InstanceSizeStat.query.filter_by(
                instance_id=self.instance.id,
                collected_date=collected_date
            ).first()
            
            if existing_stat:
                # 更新现有记录
                existing_stat.total_size_mb = total_size
                existing_stat.database_count = database_count
                existing_stat.collected_at = time_utils.now()
                existing_stat.updated_at = time_utils.now()
                self.logger.debug(f"更新实例 {self.instance.name} 大小统计记录")
            else:
                # 创建新记录
                new_stat = InstanceSizeStat(
                    instance_id=self.instance.id,
                    total_size_mb=total_size,
                    database_count=database_count,
                    collected_date=collected_date,
                    collected_at=time_utils.now(),
                    is_deleted=False
                )
                db.session.add(new_stat)
                self.logger.debug(f"创建实例 {self.instance.name} 大小统计记录")
            
            self.logger.info(f"实例 {self.instance.name} 大小统计: 总大小 {total_size}MB, 数据库数量 {database_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存实例 {self.instance.name} 大小统计失败: {str(e)}")
            return False
    
    def collect_and_save(self) -> int:
        """
        采集并保存数据库大小数据，同时保存实例大小统计
        
        Returns:
            int: 保存的记录数量
        """
        try:
            # 采集数据
            data = self.collect_database_sizes()
            
            # 保存数据库大小数据
            saved_count = self.save_collected_data(data)
            
            # 保存实例大小统计
            if data:
                self.save_instance_size_stat(data)
                db.session.commit()
                self.logger.info(f"实例 {self.instance.name} 数据采集和统计保存完成")
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"实例 {self.instance.name} 采集和保存数据失败: {str(e)}")
            raise
    
    def update_instance_total_size(self) -> bool:
        """
        根据已保存的数据库大小数据更新实例大小统计
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取今天该实例的所有数据库大小数据（使用中国时区）
            from app.utils.time_utils import time_utils
            today = time_utils.now_china().date()
            stats = DatabaseSizeStat.query.filter_by(
                instance_id=self.instance.id,
                collected_date=today,
                is_deleted=False
            ).all()
            
            if not stats:
                self.logger.warning(f"实例 {self.instance.name} 今天没有数据库大小数据")
                return False
            
            # 计算总大小和数据库数量
            total_size = sum(stat.size_mb for stat in stats)
            database_count = len(stats)
            
            # 保存或更新实例大小统计
            success = self.save_instance_size_stat([
                {'size_mb': stat.size_mb} for stat in stats
            ])
            
            if success:
                db.session.commit()
                self.logger.info(f"实例 {self.instance.name} 大小统计更新为: {total_size} MB (基于 {database_count} 个数据库)")
                return True
            else:
                return False
            
        except Exception as e:
            self.logger.error(f"更新实例 {self.instance.name} 大小统计失败: {str(e)}")
            return False


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
