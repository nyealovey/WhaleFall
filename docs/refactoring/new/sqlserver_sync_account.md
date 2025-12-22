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
实现是通过三段式名称引用（如 [db].sys.database_permissions）拼接 UNION ALL，而非显式 USE 切换数据库上下文。
但跨库片段会随着数据库数量线性增长，SQL 文本长度、编译/优化成本、执行成本都会被放大。
当数据库数量多（如 50+）时，SQL 语句可能达到数万字符
2. 串行执行模式
# app/tasks/accounts_sync_tasks.py
for i, instance in enumerate(instances):
    synced, failed = _sync_single_instance(...)  # 串行处理每个实例
所有实例是串行同步的，如果有 10 个 SQL Server 实例，每个需要 30 秒，总耗时就是 5 分钟。

3. 连接超时配置
# app/services/connection_adapters/adapters/sqlserver_adapter.py (连接适配器)
self.connection = pymssql.connect(
    ...
    timeout=300,        # 单条语句查询超时 5 分钟
    login_timeout=20,   # 登录超时 20 秒
)
注意：权限阶段至少会执行 3 条“大 SQL”（principals/roles/perms），若触发回退机制还会再执行 3 条同类查询。
因此单实例最坏等待时间可能远超 5 分钟（且慢但未超时的查询会一直等待完成）。

4. 权限查询的 COLLATE 开销
-- 每个 JOIN 都带 COLLATE 转换
JOIN target_logins ON member.name COLLATE SQL_Latin1_General_CP1_CI_AS = target_logins.login_name
COLLATE 会引入额外的字符集/排序规则转换开销，并可能影响可索引性（需要结合实际执行计划验证）。
另外，直接移除 COLLATE 可能触发 collation conflict，需要确保比较两侧排序规则一致（例如改为 COLLATE DATABASE_DEFAULT）。

5. 回退机制的双重查询
# SID 映射不可用时会直接回退到用户名查询
# 若 SID 路径未返回任何角色/权限，也会再回退到用户名查询
if self._is_permissions_empty(result):
    result = self._get_database_permissions_by_name(...)  # 再执行一遍类似查询
某些情况下会执行两轮完整查询。

三、具体慢点定位
| 阶段 | 操作 | 预估耗时 | 原因 | |------|------|----------|------| | 清单 | _fetch_logins() | 1-2s | 单表查询，较快 | | 权限 | _get_server_roles_bulk() | 1-3s | 服务器级，数据量小 | | 权限 | _get_server_permissions_bulk() | 1-3s | 服务器级，数据量小 | | 权限 | _get_all_users_database_permissions_batch() | 10-60s+ | 多库 UNION ALL，主要瓶颈 |

四、最佳优化方案（推荐落地顺序）
目标：在不牺牲权限准确性的前提下，把“单实例权限阶段”从 10-60s+ 降到可控区间，并把“多实例总耗时”从串行累加降到接近单实例耗时。

1) 优先缩小扫描范围（成本最低，收益最大）
- 对 `_get_accessible_databases()` 返回的库列表套用统一过滤规则（建议复用 `app/config/database_filters.yaml` 的 sqlserver 规则），默认排除 master/model/msdb/tempdb 及 ReportServer%。
- 支持实例级 allowlist/exclude（当业务只关心少数业务库时，直接把 N 从 50+ 降到 10-20，后续所有优化都线性受益）。
- 同步日志中输出最终 `database_count`，便于验证过滤生效。

2) 消除“全量回退导致双重查询”（兼顾正确性与性能）
现状：SID 路径结果全空时，会整套回退到按用户名查询，导致同一轮同步对同一批库执行两轮 principals/roles/perms 查询。
推荐做法（二选一，优先 A）：
A. 单次查询同时支持 SID + 用户名匹配：
   - 在 principals/roles/perms 的 WHERE 条件中同时支持 `sid IN target_sids OR name IN target_logins`，从根上消除二次扫描。
   - 适用于包含用户(contained user)或 SID 不可用场景，避免“结果为空再重跑”的昂贵回退。
B. 仅对缺失用户做补偿回退：
   - 先跑 SID 路径，计算缺失用户名集合，再对缺失用户调用 `_get_database_permissions_by_name()`（而不是全量重跑）。

3) 将“全库一次 UNION ALL”改为“分批 UNION + 循环聚合”（避免超长 SQL 与高编译成本）
- 将数据库按 batch_size 分批构造 UNION ALL（先使用 20），并循环执行 principals/roles/perms 三条查询，再把结果 merge 聚合。
- 关注指标：单批 SQL 字符长度、单批耗时、总批次数；用生产日志回推 batch_size 的最优区间。

4) 并行化实例同步（把总耗时从累加改为并发）
- 最稳妥方案：使用 Celery/RQ，把“单实例同步”作为独立任务；并发数建议从 4 起步，根据 SQL Server 连接上限/网络/CPU 调整到 4-8。
- 线程池仅作为临时方案：需要每个线程独立 app_context + 独立 db.session 生命周期（避免跨线程复用会话导致上下文/连接问题）。
- 配套策略：为单实例设置硬超时（例如 8-10 分钟）+ 失败隔离（一个实例失败不阻塞整轮）。

5) 观测与验收（没有指标就无法证明“最佳”）
- 在现有 `sqlserver_batch_database_permissions_completed` 基础上补充：
  - 分项耗时：principals/roles/perms 各自耗时
  - SQL 体积：单批 SQL 字符长度、批次数
  - 回退信息：是否触发回退、触发原因（SID 映射不可用 vs 结果为空）
- 验收建议：按实例维度统计 P50/P95（按 `database_count` 分桶），验证过滤与分批是否让耗时随库数增长更平滑。

五、日志分析建议
当前代码已有耗时日志：

self.logger.info(
    "sqlserver_batch_database_permissions_completed",
    ...
    elapsed_time=f"{elapsed:.2f}s",
)
建议检查生产日志中 elapsed_time 的实际值，确认瓶颈位置。
