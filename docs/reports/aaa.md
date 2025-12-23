III. “模型设计问题清单”（按 P0/P1/P2 分组；每条包含：标题/证据/影响/根因/建议/验证）

P0（必须优先修复）

分区事实表 database_size_stats 缺失主键与 id 索引，且业务查询强依赖 id 回表
证据：
database_size_stats 仅有 UNIQUE(instance_id,database_name,collected_date)，无 PRIMARY KEY：migrations/versions/20251219161048_baseline_production_schema.py (line 1453)、migrations/versions/20251219161048_baseline_production_schema.py (line 3954)
业务“最新值”查询通过 DatabaseSizeStat.id join：app/routes/instances/detail.py (line 627)、app/routes/instances/detail.py (line 651)
父表索引清单不含 id：migrations/versions/20251219161048_baseline_production_schema.py (line 3932)
影响：
最坏：容量页面“最新值/历史”在库数大、分区多时显著变慢；未来若需要别表引用 database_size_stats 行，无法建立 FK。
最可能：窗口函数/回表 join 走 hash/seq scan，单实例库数上千时明显卡顿。
根因：
分区表 PK 必须包含分区键，可能为避免 (id, collected_date) 而“干脆不建 PK”，但代码仍把 id 当主键使用。
建议：
短期（1~3 天）：为父表增加 PRIMARY KEY (id, collected_date)（与 instance_size_stats 对齐）并在父表补齐必要索引；同时评估把“最新值”查询改成 DISTINCT ON（Postgres）减少回表。
中期（1~2 周）：将“最新库容量”改为单独的 current 表（例如 database_size_current）或物化视图，写入时维护，读路径 O(库数) 且无需窗口扫描历史。
长期：把容量事实表的主键/外键/索引策略形成 ADR，统一治理四张分区表。
验证：
SQL：检查是否存在 PK：select conname, contype from pg_constraint where conrelid='database_size_stats'::regclass;
SQL：检查 id 是否可用于索引扫描：explain analyze ... join ranked on id ... 对比变更前后。
迁移演练：在非生产复制库上跑变更，观察锁时间（对分区表添加 PK 需谨慎拆分/按分区逐步）。
分区事实表 database_size_aggregations 缺失主键，且缺失 instance_id 外键（ORM 与 DB 不一致）
证据：
ORM 声明 instance_id = ForeignKey(\"instances.id\")：app/models/database_size_aggregation.py (line 60)
DB 仅有 uq_database_size_aggregation(...)，无 PK、无 FK：migrations/versions/20251219161048_baseline_production_schema.py (line 1369)、migrations/versions/20251219161048_baseline_production_schema.py (line 3927)
影响：
最坏：出现 orphan 聚合记录（instance 已删/不存在）；清理实例数据需要应用层兜底，容易漏删导致数据膨胀。
最可能：长期运维复杂度升高（无法依赖 FK 做一致性与级联策略）。
根因：
基线从生产导出时遗漏了 FK；同时 PK 设计未统一（对比 instance_size_aggregations 已有 PK/FK）。
建议：
短期：补 FK database_size_aggregations.instance_id -> instances.id（ON DELETE 策略需决策：多数场景建议 CASCADE 或统一 RESTRICT + 软删）；补 PRIMARY KEY (id, period_start)（对齐 instance_size_aggregations）。
中期：把“容量聚合/统计”四表的 FK/PK 统一起来，避免每张表各自为政。
长期：若未来要引用聚合行（如报表快照、告警），考虑稳定主键设计（UUID 或复合键）。
验证：
SQL：select count(*) from database_size_aggregations a left join instances i on a.instance_id=i.id where i.id is null;
Alembic 演练：先 add FK NOT VALID → validate（尽量降低锁影响）。
account_permission.instance_account_id 在 DB 缺失索引，但同步与列表强依赖该字段查找/Join
证据：
代码大量按 instance_account_id 查找：app/services/accounts_sync/permission_manager.py (line 242)
ORM 标注 index=True：app/models/account_permission.py (line 46)
DB account_permission 索引清单不含 instance_account_id：migrations/versions/20251219161048_baseline_production_schema.py (line 2284)
影响：
最坏：账户数上万时，权限同步每个账户查找都会退化为全表扫描，导致同步任务不可用。
最可能：实例账户列表 join 变慢，UI 卡顿。
根因：
基线 schema 与 ORM 定义漂移（缺索引）；且 account_permission 的“当前态”表会随同步增长。
建议：
短期：增加索引 CREATE INDEX CONCURRENTLY ix_account_permission_instance_account_id ON account_permission(instance_account_id);
中期：增加一致性约束（见 P1-2），减少冗余键导致的额外查找。
验证：
SQL：explain analyze select * from account_permission where instance_account_id = ? limit 1; 观察是否走 index scan。
同步压测：以 1 万账户模拟，比较同步耗时曲线。
sync_sessions.status：ORM 默认值为 pending，但 DB 默认/Check 不允许 pending（存在写入失败风险）
证据：
ORM：SyncSession.status 默认 pending：app/models/sync_session.py (line 47)
DB：status 默认 running：migrations/versions/20251219161048_baseline_production_schema.py (line 1308)
DB：check 仅允许 running/completed/failed/cancelled：migrations/versions/20251219161048_baseline_production_schema.py (line 3816)
影响：
最坏：某些创建会话的代码路径若未显式覆盖 status，会直接触发 DB check 失败，导致同步流程中断。
最可能：未来重构/新入口复用 model 默认值时踩雷（隐性 bug）。
根因：
ORM 与生产 schema 漂移；且 check 约束在 DB 端更强。
建议：
短期：把 ORM 默认值改为与 DB 一致（running），或改为 server_default 以跟随 DB。
中期：将 status/sync_type/sync_category 统一用 Enum/小表，并让 ORM 与 DB 单一来源。
验证：
单测/演练：创建 SyncSession(sync_type=...) 不显式赋 status，确认 insert 不触发 check。
SQL：insert into sync_sessions (...) values (...) 走默认值时应通过。
instance_size_stats_partition_trigger() 在写入路径执行 DDL（创建分区），存在锁与稳定性风险
证据：
触发器函数包含 EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_stats ...')：migrations/versions/20251219161048_baseline_production_schema.py (line 1953)
父表/子表均挂载该触发器：migrations/versions/20251219161048_baseline_production_schema.py (line 4009)、migrations/versions/20251219161048_baseline_production_schema.py (line 3392)
影响：
最坏：月初/跨月写入时，写请求触发建表 DDL，导致锁等待、事务抖动，甚至阻塞其他 DDL/写入。
最可能：在高并发采集时偶发尖刺，且难以定位（表现为 DB 端锁争用）。
根因：
“分区自动化”与“业务写入”耦合；且你们已有 PartitionManagementService，两套机制叠加。
建议：
短期：移除“写入建分区”触发器，改为调度任务/服务在写入前创建未来 N 个月分区（已有 app/services/partition_management_service.py (line 104)）。
中期：统一分区策略：所有四张分区表都由同一条链路创建分区、创建索引，避免触发器/脚本/服务三套并存。
验证：
SQL：select * from pg_trigger where tgrelid='instance_size_stats'::regclass; 确认触发器移除。
运维演练：跨月当天压测写入，观察锁图（pg_locks）是否消失。
P1（重要但可分期）

分区表/普通表存在大量重复索引与重复唯一（写放大明显，未来越用越慢）
证据：
tags 同时有 ix_tags_name + UNIQUE(name)：migrations/versions/20251219161048_baseline_production_schema.py (line 3831)、migrations/versions/20251219161048_baseline_production_schema.py (line 3845)
database_size_stats_2025_07 对 collected_date 有两套索引：database_size_stats_2025_07_collected_date_idx vs idx_database_size_stats_2025_07_date：migrations/versions/20251219161048_baseline_production_schema.py (line 2656)、migrations/versions/20251219161048_baseline_production_schema.py (line 2672)
instance_size_stats_* 分区每表 9 个索引（且有多组同列索引）citemigrations/versions/20251219161048_baseline_production_schema.py:3358
影响：
最坏：容量采集/聚合写入 QPS 上来后，索引维护成本成为瓶颈；VACUUM/膨胀加剧。
最可能：写入耗时随历史分区增多而上升，慢慢变“越来越卡”。
根因：
多来源创建索引（导出 DDL + 分区脚本 + PartitionManagementService._create_partition_indexes app/services/partition_management_service.py (line 711)）叠加未治理。
建议：
短期：先做“索引盘点 → 以 Top 查询为准裁剪”，优先在分区大表上去重（保留最小集合）。
中期：改为在父表创建 partitioned index（或由服务只创建一套索引），并建立“新分区必须一致”的校验脚本。
验证：
SQL：统计每分区索引数量/重复度；对比写入耗时与 bloat（pg_stat_user_indexes、pg_relation_size）。
account_permission 存在“冗余身份键”但缺少一致性约束，未来易产生脏数据
证据：
列同时存在：instance_account_id + instance_id/db_type/username：migrations/versions/20251219161048_baseline_production_schema.py (line 317)
唯一性由 uq_current_account_sync(instance_id,db_type,username) 保证，但 instance_account_id 与该三元组未被约束绑定 citemigrations/versions/20251219161048_baseline_production_schema.py:2300
影响：
最坏：出现“instance_account_id 指向 A，但 username 是 B”的不一致，分类/权限展示错乱且难排查。
最可能：后续补数据/修复脚本写错时产生隐性脏数据。
根因：
为查询便利保留冗余列，但 DB 未强制一致性。
建议：
短期：新增校验 SQL + 定期巡检；在写入路径强制从 InstanceAccount 派生三元组（单一来源）。
中期（推荐）：去冗余：只保留 instance_account_id，并通过 join 获得 username/db_type/instance_id；或改成复合 FK FOREIGN KEY(instance_id, db_type, username) REFERENCES instance_accounts(instance_id, db_type, username)。
验证：
SQL：找不一致行：select ap.id from account_permission ap join instance_accounts ia on ap.instance_account_id=ia.id where ap.username<>ia.username or ap.instance_id<>ia.instance_id;
credentials.instance_ids(jsonb) 与 instances.credential_id 双向冗余，难以保证一致
证据：
DB：credentials.instance_ids jsonb：migrations/versions/20251219161048_baseline_production_schema.py (line 363)
DB：instances.credential_id：migrations/versions/20251219161048_baseline_production_schema.py (line 1247)
ORM：Instance.credential_id + Credential.instance_ids 同时存在：app/models/instance.py (line 94)、app/models/credential.py (line 85)
影响：
最坏：同一实例的凭据关系出现分裂（UI 显示/同步逻辑基于不同来源）。
最可能：运维/修复时只改一边，久而久之漂移。
根因：
关系模型未定稿：是“凭据被多个实例引用”（应由 instances FK 推导），还是“凭据主动维护实例集合”（应有中间表并强约束）。
建议：
短期：明确 source of truth（建议以 instances.credential_id 为准，instance_ids 只做缓存/冗余并加定期校验）。
中期：用中间表 credential_instances(credential_id, instance_id) 替代 jsonb，或彻底移除 instance_ids 字段。
验证：
SQL：交叉校验一致性（jsonb 与实例 FK 的集合差）。
account_classification_assignments 的唯一约束包含可空 batch_id，NULL 可绕过唯一性
证据：
batch_id 可空：migrations/versions/20251219161048_baseline_production_schema.py (line 287)
UNIQUE(account_id, classification_id, batch_id)：migrations/versions/20251219161048_baseline_production_schema.py (line 2257)
影响：
最坏：同一账户/分类在“无 batch_id”场景下被重复分配多次，统计与 UI 混乱。
最可能：手动分配（batch_id 为空）时产生重复。
根因：
未显式定义“批次为空时的唯一性语义”。
建议：
短期：约束 batch_id 非空（若业务允许）；或使用 UNIQUE(account_id, classification_id) WHERE is_active=true（更贴近“当前有效分配”）。
中期：把“分配历史”与“当前归属”拆表：history 表允许多条，current 表强唯一。
验证：
SQL：查重复：select account_id, classification_id, count(*) from ... where batch_id is null group by 1,2 having count(*)>1;
聚合表时间字段时区语义不一致（timestamp vs timestamptz），易引发跨时区/夏令时问题
证据：
DB：database_size_aggregations.calculated_at/created_at 为 timestamp(6)：migrations/versions/20251219161048_baseline_production_schema.py (line 1393)
ORM：DateTime(timezone=True)：app/models/database_size_aggregation.py (line 95)
同类问题也存在于 instance_size_aggregations：migrations/versions/20251219161048_baseline_production_schema.py (line 1543)、app/models/instance_size_aggregation.py (line 88)
影响：
最坏：同一时间被解释为不同 UTC 时刻，聚合窗口/展示错位。
最可能：展示层与统计计算出现“差一天/差 8 小时”的疑难 bug。
根因：
历史 DDL 导出与 ORM 设计未统一“时间统一用 UTC+timestamptz”。
建议：
短期：先统一 ORM 的 timezone 标记与 DB 一致（或反过来改 DB）；并在服务层明确写入使用 UTC。
中期：迁移 DB 到 timestamptz 并回填/校验。
验证：
SQL：检查列类型与写入值时区；对比应用序列化输出。
P2（优化/长期演进）

db_type 缺少跨表强一致性（未 FK 到 database_type_configs），扩展新类型时容易写入非法值
证据：database_type_configs 存在但未被 FK 引用：migrations/versions/20251219161048_baseline_production_schema.py (line 785)；instances.db_type 等多表为 varchar：migrations/versions/20251219161048_baseline_production_schema.py (line 1239)
影响：新增 db_type 时可能出现“配置存在但业务写入不同拼写”的脏数据。
建议：以 database_type_configs(name) 为中心做 FK 或枚举约束，并统一长度与大小写策略。
验证：SQL 检查异常值：select distinct db_type from instances except select name from database_type_configs;
日志检索 LIKE 在大数据量下不可扩展（尤其是 context 搜索）
证据：UnifiedLog.message/context 使用 LIKE：app/routes/history/logs.py (line 199)
建议：pg_trgm trigram index（message/text）或 JSONB GIN + 结构化检索；或者引入外部日志系统（长期）。
验证：explain analyze 对比索引前后。
回滚/演进策略缺口：基线迁移不可 downgrade，且大量 schema 对象（触发器/函数/分区）集中在一个版本
证据：downgrade() 直接 NotImplementedError：migrations/versions/20251219161048_baseline_production_schema.py (line 4211)
建议：为关键变更提供可回滚迁移（至少“前滚补丁”策略），并将分区/函数/触发器拆分为可演进模块。
验证：演练“上线失败 → 回滚/前滚”流程（含锁评估与数据一致性检查）。
路线图（最多 8 条行动项，按最小可执行）

先修 P0：给 database_size_stats/database_size_aggregations 补齐 PK（含分区键）与必要索引、并补 database_size_aggregations.instance_id FK（Not Valid → Validate）。
先修 P0：为 account_permission(instance_account_id) 增加索引（并回归权限同步与实例账户列表性能）。
先修 P0：移除/下线“写入建分区”触发器，统一改由 PartitionManagementService 预创建未来分区（至少提前 2~3 个月）。
修复 ORM/DB 漂移：SyncSession.status 默认值与 DB check 对齐；梳理其它“代码兼容旧 schema”的残留分支。
索引治理专项（P1）：对四张分区表做索引去重与标准化（以 Top10 查询为基准），并建立“新分区索引一致性”校验。
约束治理（P1）：修正 account_classification_assignments 的唯一性语义（NULL batch_id），并明确“当前归属 vs 历史记录”的建模。
关系去冗余（P1）：明确 credentials.instance_ids 的定位（移除/中间表/只做缓存并校验），避免双写漂移。
ADR/规范落地（P2）：补齐 db_type、时间字段、软删除、触发器策略、迁移零停机的建模规范与演练清单。
