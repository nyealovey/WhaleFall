版本,新增权限类型,描述
Oracle 11g Release 1 (11.1),无新增,-
Oracle 11g Release 2 (11.2),SYSASM,新的行政权限，用于 Oracle ASM 管理，支持分离职责。
Oracle 12c Release 1 (12.1),"SYSBACKUP
SYSDG
SYSKM
READ
READ ANY TABLE","SYSBACKUP：用于备份和恢复操作。
SYSDG：用于 Oracle Data Guard 管理。
SYSKM：用于加密密钥管理。
READ：对象权限，用于表/视图的只读访问（不锁定行）。
READ ANY TABLE：系统权限，用于任何表的只读访问。"
Oracle 12c Release 2 (12.2),无新增,-
Oracle 18c,无新增,18c 是 12.2.0.2 的重命名版本，无新权限。
Oracle 19c,无新增,19c 是长期支持版本，无新权限。
Oracle 21c,DIAGNOSTICS_CONTROL,新的系统权限，用于控制诊断事件（events 和 error-numbers）的设置，通过 ALTER SESSION/ALTER SYSTEM 操作，提高安全控制。
Oracle 23c (23ai),"Schema-level privileges (e.g., SELECT ANY TABLE ON SCHEMA)
GRANT ANY SCHEMA PRIVILEGE","Schema-level privileges：新的权限授予方式，允许在特定 schema 上授予 ANY 风格的权限（如 SELECT ANY TABLE ON SCHEMA schema_name），适用于当前和未来对象，提高授权简化但需注意最小权限原则。
GRANT ANY SCHEMA PRIVILEGE：系统权限，用于在其他 schema 上授予 schema-level 权限。"


版本,新增预定义角色,描述
Oracle 11g Release 1 (11.1),无新增,-
Oracle 11g Release 2 (11.2),无新增,-
Oracle 12c Release 1 (12.1),无新增,-
Oracle 12c Release 2 (12.2),无新增,-
Oracle 18c,SODA_APP,用于 Simple Oracle Document Access (SODA) APIs，提供管理 JSON 文档集合的权限。
Oracle 19c,无新增,19c 是长期支持版本，无新角色。
Oracle 21c,无新增,-
Oracle 23c (23ai),DB_DEVELOPER_ROLE,为开发者提供常用权限集合，如 DEBUG CONNECT SESSION 等。



版本新增权限类型描述MySQL 5.7无新增-MySQL 8.0BACKUP_ADMIN
CLONE_ADMIN
CONNECTION_ADMIN
ENCRYPTION_KEY_ADMIN
GROUP_REPLICATION_ADMIN
PERSIST_RO_SYSTEM_VARIABLE_ADMIN
RESOURCE_GROUP_ADMIN
RESOURCE_GROUP_USER
ROLE_ADMIN
SESSION_VARIABLES_ADMIN
SET_USER_ID
SYSTEM_USER
SYSTEM_VARIABLES_ADMIN
TABLE_ENCRYPTION_ADMIN
XA_RECOVER_ADMIN
INNODB_REDO_LOG_ENABLE
SKIP_QUERY_REWRITEBACKUP_ADMIN：用于 LOCK INSTANCE FOR BACKUP 和 UNLOCK INSTANCE。
CLONE_ADMIN：用于克隆操作。
CONNECTION_ADMIN：用于连接管理。
ENCRYPTION_KEY_ADMIN：用于加密密钥管理。
GROUP_REPLICATION_ADMIN：用于 Group Replication。
PERSIST_RO_SYSTEM_VARIABLE_ADMIN：用于持久化只读变量。
RESOURCE_GROUP_ADMIN/RESOURCE_GROUP_USER：用于资源组管理。
ROLE_ADMIN：用于角色管理。
SESSION_VARIABLES_ADMIN：用于会话变量。
SET_USER_ID：用于设置用户 ID。
SYSTEM_USER：区分系统用户。
SYSTEM_VARIABLES_ADMIN：用于系统变量。
TABLE_ENCRYPTION_ADMIN：用于表加密。
XA_RECOVER_ADMIN：用于 XA 事务恢复。
INNODB_REDO_LOG_ENABLE：用于控制重做日志。
SKIP_QUERY_REWRITE：用于跳过查询重写。MySQL 8.1无新增-MySQL 8.2无新增-MySQL 8.3无新增-MySQL 8.4TRANSACTION_GTID_TAG
FLUSH_PRIVILEGES
OPTIMIZE_LOCAL_TABLE
SET_ANY_DEFINER
ALLOW_NONEXISTENT_DEFINERTRANSACTION_GTID_TAG：用于设置 GTID 标签。
FLUSH_PRIVILEGES：专用于 FLUSH PRIVILEGES 语句。
OPTIMIZE_LOCAL_TABLE：用于执行 OPTIMIZE LOCAL TABLE。
SET_ANY_DEFINER：用于定义者对象创建。
ALLOW_NONEXISTENT_DEFINER：用于孤立对象保护。



版本,新增权限类型,描述
SQL Server 2008,无新增,-
SQL Server 2008 R2,无新增,-
SQL Server 2012,无新增（权限总数从 195 增至 214，但无具体新增列表）,-
SQL Server 2014,无新增,-
SQL Server 2016,UNMASK,用于查看动态数据屏蔽下的完整数据。
SQL Server 2017,"ADMINISTER DATABASE BULK OPERATIONS
CONTROL, ALTER, REFERENCES, TAKE OWNERSHIP, VIEW DEFINITION (on DATABASE SCOPED CREDENTIAL)","ADMINISTER DATABASE BULK OPERATIONS：用于数据库批量操作。
其他：用于 DATABASE SCOPED CREDENTIAL 安全对象。"
SQL Server 2019,无新增,-
SQL Server 2022,ADMINISTER DATABASE LEDGER 等（粒度权限）,改进最小权限原则，包括 ledger 相关权限。



版本,新增预定义角色,描述
SQL Server 2008,无新增,-
SQL Server 2008 R2,无新增,-
SQL Server 2012,无新增（引入用户定义服务器角色支持）,用户定义服务器角色允许自定义服务器级角色。
SQL Server 2014,无新增,-
SQL Server 2016,ssis_logreader,用于 Integration Services 日志读取（数据库级）。
SQL Server 2017,无新增,-
SQL Server 2019,无新增,-
SQL Server 2022,##MS_DatabaseConnector## 等（内置服务器级角色）,"##MS_DatabaseConnector##：授予所有数据库的 CONNECT 权限。
其他：最小权限原则的内置角色，如 ##MS_ServerStateReader##。"


版本,新增权限类型,描述
PostgreSQL 11,无新增,-
PostgreSQL 12,无新增,-
PostgreSQL 13,MAINTAIN,用于 pg_maintain 函数，允许维护操作如 VACUUM、ANALYZE。
PostgreSQL 14,EXECUTE (on FOREIGN SERVER),用于 FOREIGN SERVER 的 EXECUTE 权限。
PostgreSQL 15,无新增,-
PostgreSQL 16,无新增,-
PostgreSQL 17,无新增,-



版本,新增预定义角色,描述
PostgreSQL 11,无新增,-
PostgreSQL 12,无新增,-
PostgreSQL 13,pg_signal_backend,允许发送信号到其他后端进程。
PostgreSQL 14,"pg_read_server_files
pg_write_server_files
pg_execute_server_program","pg_read_server_files：读取服务器文件。
pg_write_server_files：写入服务器文件。
pg_execute_server_program：执行服务器程序。"
PostgreSQL 15,pg_database_owner,隐式包含当前数据库所有者，提供数据库级访问。
PostgreSQL 16,无新增,-
PostgreSQL 17,无新增,-