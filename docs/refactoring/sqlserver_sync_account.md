SQL Server 账户同步性能分析
一、整体流程
sync_accounts (定时任务)
  └── 遍历所有活跃实例
       └── AccountSyncCoordinator.sync_all()
            ├── synchronize_inventory()  # 清单阶段
            │    └── fetch_remote_accounts()
            │         └── _fetch_raw_accounts() → _fetch_logins()
            └── synchronize_permissions() # 权限阶段
                 └── enrich_permissions()
                      ├── _get_server_roles_bulk()
                      ├── _get_server_permissions_bulk()
                      └── _get_all_users_database_permissions_batch()
二、性能瓶颈分析
1. 数据库权限批量查询 (_get_all_users_database_permissions_batch)
这是最大的性能瓶颈。代码逻辑：

def _get_all_users_database_permissions_batch(self, connection, usernames):
    # 1. 获取可访问数据库列表
    database_list = self._get_accessible_databases(connection)
    
    # 2. 构建 SID 映射
    sid_to_logins, sid_payload = self._map_sids_to_logins(connection, usernames)
    
    # 3. 为每个数据库生成 UNION ALL 查询
    principal_sql, roles_sql, perms_sql = self._build_database_permission_queries(database_list)
    
    # 4. 执行三个大查询
    principal_rows, role_rows, permission_rows = self._fetch_principal_data(...)
问题：

如果有 N 个数据库，会生成 N 个 SELECT ... UNION ALL 的巨型 SQL
每个数据库都要查询 sys.database_principals、sys.database_role_members、sys.database_permissions
SQL Server 需要切换数据库上下文执行每个子查询
当数据库数量多（如 50+）时，SQL 语句可能达到数万字符
2. 串行执行模式
# accounts_sync_tasks.py
for i, instance in enumerate(instances):
    synced, failed = _sync_single_instance(...)  # 串行处理每个实例
所有实例是串行同步的，如果有 10 个 SQL Server 实例，每个需要 30 秒，总耗时就是 5 分钟。

3. 连接超时配置
# sqlserver_adapter.py (连接适配器)
self.connection = pymssql.connect(
    ...
    timeout=300,        # 查询超时 5 分钟
    login_timeout=20,   # 登录超时 20 秒
)
超时设置较长，如果查询慢会一直等待。

4. 权限查询的 COLLATE 开销
-- 每个 JOIN 都带 COLLATE 转换
JOIN target_logins ON member.name COLLATE SQL_Latin1_General_CP1_CI_AS = target_logins.login_name
COLLATE 转换会阻止索引使用，导致全表扫描。

5. 回退机制的双重查询
# 如果 SID 路径未返回结果，会回退到用户名查询
if self._is_permissions_empty(result):
    result = self._get_database_permissions_by_name(...)  # 再执行一遍类似查询
某些情况下会执行两轮完整查询。

三、具体慢点定位
| 阶段 | 操作 | 预估耗时 | 原因 | |------|------|----------|------| | 清单 | _fetch_logins() | 1-2s | 单表查询，较快 | | 权限 | _get_server_roles_bulk() | 1-3s | 服务器级，数据量小 | | 权限 | _get_server_permissions_bulk() | 1-3s | 服务器级，数据量小 | | 权限 | _get_all_users_database_permissions_batch() | 10-60s+ | 多库 UNION ALL，主要瓶颈 |

四、优化建议
短期优化（代码层面）
分批查询数据库权限

不要一次 UNION ALL 所有数据库
按 10-20 个数据库分批查询，减少单次 SQL 复杂度
并行处理实例

使用 ThreadPoolExecutor 并行同步多个实例
注意控制并发数，避免数据库连接池耗尽
移除不必要的 COLLATE

如果数据库排序规则一致，可以省略 COLLATE
或者在 CTE 中预先转换，避免 JOIN 时转换
增量同步

记录上次同步时间
只查询有变更的账户/权限
中期优化（架构层面）
异步任务队列

使用 Celery/RQ 将每个实例的同步作为独立任务
支持重试、超时控制、并行执行
缓存机制

缓存数据库列表（变化不频繁）
缓存 SID 映射（登录账户变化不频繁）
分离查询连接

权限查询使用只读副本
减少对主库的压力
五、日志分析建议
当前代码已有耗时日志：

self.logger.info(
    "sqlserver_batch_database_permissions_completed",
    ...
    elapsed_time=f"{elapsed:.2f}s",
)
建议检查生产日志中 elapsed_time 的实际值，确认瓶颈位置。