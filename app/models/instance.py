"""
泰摸鱼吧 - 实例模型
"""

from datetime import datetime

from app import db
from app.utils.timezone import now


class Instance(db.Model):
    """数据库实例模型"""

    __tablename__ = "instances"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database_name = db.Column(db.String(255), nullable=True)
    database_version = db.Column(db.String(1000), nullable=True)  # 原始版本字符串
    main_version = db.Column(db.String(20), nullable=True)  # 主版本号 (如 8.0, 13.4, 14.0)
    detailed_version = db.Column(db.String(50), nullable=True)  # 详细版本号 (如 8.0.32, 13.4, 14.0.3465.1)
    environment = db.Column(
        db.String(20), default="production", nullable=False, index=True
    )  # 环境：production, development, testing
    sync_count = db.Column(db.Integer, default=0, nullable=False)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default="active", index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_connected = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # 关系
    credential = db.relationship("Credential", backref="instances")
    # accounts关系已移除，因为Account模型已废弃，使用CurrentAccountSyncData
    # sync_data关系已移除，因为SyncData表已删除

    def __init__(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database_name: str | None = None,
        credential_id: int | None = None,
        description: str | None = None,
        tags: str | None = None,
        environment: str = "production",
    ) -> None:
        """
        初始化实例

        Args:
            name: 实例名称
            db_type: 数据库类型
            host: 主机地址
            port: 端口号
            database_name: 数据库名称
            credential_id: 凭据ID
            description: 描述
            tags: 标签
            environment: 环境类型（production, development, testing）
        """
        self.name = name
        self.db_type = db_type
        self.host = host
        self.port = port
        self.database_name = database_name
        self.credential_id = credential_id
        self.description = description
        self.tags = tags or []
        self.environment = environment

    def test_connection(self) -> dict:
        """
        测试数据库连接

        Returns:
            dict: 连接测试结果
        """
        try:
            from app.services.connection_test_service import connection_test_service
            from app.utils.timezone import now
            
            # 使用连接测试服务
            result = connection_test_service.test_connection(self)
            
            # 无论连接成功还是失败，都更新最后连接时间
            self.last_connected = now()
            
            # 如果连接成功，解析版本信息
            if result.get('success') and result.get('version'):
                version_info = result['version']
                parsed = DatabaseVersionParser.parse_version(self.db_type.lower(), version_info)
                
                # 更新实例的版本信息
                self.database_version = parsed['original']
                self.main_version = parsed['main_version']
                self.detailed_version = parsed['detailed_version']
                
                # 更新返回结果中的版本信息
                result['version'] = DatabaseVersionParser.format_version_display(self.db_type.lower(), version_info)
                result['main_version'] = parsed['main_version']
                result['detailed_version'] = parsed['detailed_version']
            
            # 保存到数据库
            db.session.commit()
            
            return result
            
        except Exception as e:
            # 即使出现异常，也尝试更新最后连接时间
            try:
                from app.utils.timezone import now
                self.last_connected = now()
                db.session.commit()
            except Exception as update_error:
                pass  # 忽略更新时间的错误
            
            return {"status": "error", "message": f"连接测试失败: {str(e)}"}

    def _test_sql_server_connection(self) -> dict:
        """测试SQL Server连接"""
        import pymssql

        try:
            conn = pymssql.connect(
                server=self.host,
                port=self.port,
                user=self.credential.username if self.credential else "",
                password=self.credential.password if self.credential else "",
                database="master",
            )
            conn.close()
            return {"status": "success", "message": "SQL Server连接成功"}
        except Exception as e:
            return {"status": "error", "message": f"SQL Server连接失败: {str(e)}"}

    def _test_mysql_connection(self) -> dict:
        """测试MySQL连接"""
        import pymysql

        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.credential.username if self.credential else "",
                password=self.credential.password if self.credential else "",
                database="mysql",
            )
            conn.close()
            return {"status": "success", "message": "MySQL连接成功"}
        except Exception as e:
            return {"status": "error", "message": f"MySQL连接失败: {str(e)}"}

    def _test_oracle_connection(self) -> dict:
        """测试Oracle连接"""
        import oracledb

        try:
            dsn = f"{self.host}:{self.port}/ORCL"

            # 优先使用Thick模式连接（适用于所有Oracle版本，包括11g）
            try:
                # 初始化Thick模式（需要Oracle Instant Client）
                oracledb.init_oracle_client()
                conn = oracledb.connect(
                    user=self.credential.username if self.credential else "",
                    password=self.credential.password if self.credential else "",
                    dsn=dsn,
                )
                conn.close()
                return {"status": "success", "message": "Oracle连接成功 (Thick模式)"}
            except oracledb.DatabaseError as e:
                # 如果Thick模式失败，尝试Thin模式（适用于Oracle 12c+）
                if "DPI-1047" in str(e) or "Oracle Client library" in str(e):
                    # Thick模式失败，尝试Thin模式
                    try:
                        conn = oracledb.connect(
                            user=self.credential.username if self.credential else "",
                            password=(self.credential.password if self.credential else ""),
                            dsn=dsn,
                        )
                        conn.close()
                        return {
                            "status": "success",
                            "message": "Oracle连接成功 (Thin模式)",
                        }
                    except oracledb.DatabaseError:
                        # 如果Thin模式也失败，抛出原始错误
                        raise e
                else:
                    raise
        except Exception as e:
            return {"status": "error", "message": f"Oracle连接失败: {str(e)}"}

    def to_dict(self, include_password: bool = False) -> dict:
        """
        转换为字典格式

        Args:
            include_password: 是否包含密码（默认False，安全考虑）

        Returns:
            dict: 实例信息字典
        """
        data = {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "database_version": self.database_version,
            "main_version": self.main_version,
            "detailed_version": self.detailed_version,
            "environment": self.environment,
            "credential_id": self.credential_id,
            "description": self.description,
            "tags": self.tags,
            "status": self.status,
            "is_active": self.is_active,
            "last_connected": (self.last_connected.isoformat() if self.last_connected else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if self.credential:
            if include_password:
                data["credential"] = {
                    "id": self.credential.id,
                    "name": self.credential.name,
                    "username": self.credential.username,
                    "password": self.credential.password,
                    "credential_type": self.credential.credential_type,
                }
            else:
                data["credential"] = {
                    "id": self.credential.id,
                    "name": self.credential.name,
                    "username": self.credential.username,
                    "password": self.credential.get_password_masked(),
                    "credential_type": self.credential.credential_type,
                }

        return data

    def soft_delete(self) -> None:
        """软删除实例"""
        self.deleted_at = now()
        self.status = "deleted"
        db.session.commit()
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.info(
            "实例删除",
            module="model",
            operation="instance_delete",
            instance_id=self.id,
            name=self.name,
        )

    def restore(self) -> None:
        """恢复实例"""
        self.deleted_at = None
        self.status = "active"
        db.session.commit()
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.info(
            "实例恢复",
            module="model",
            operation="instance_restore",
            instance_id=self.id,
            name=self.name,
        )

    @staticmethod
    def get_active_instances() -> list:
        """获取所有活跃实例"""
        return Instance.query.filter_by(deleted_at=None, status="active").all()

    @staticmethod
    def get_by_db_type(db_type: str) -> list:
        """根据数据库类型获取实例"""
        return Instance.query.filter_by(db_type=db_type, deleted_at=None).all()

    @staticmethod
    def get_by_environment(environment: str) -> list:
        """根据环境类型获取实例"""
        return Instance.query.filter_by(environment=environment, deleted_at=None).all()

    @staticmethod
    def get_by_db_type_and_environment(db_type: str, environment: str) -> list:
        """根据数据库类型和环境类型获取实例"""
        return Instance.query.filter_by(db_type=db_type, environment=environment, deleted_at=None).all()

    @staticmethod
    def get_environment_choices() -> list:
        """获取环境类型选项"""
        return [
            ("production", "生产环境"),
            ("development", "开发环境"),
            ("testing", "测试环境"),
        ]

    def __repr__(self) -> str:
        return f"<Instance {self.name}>"
