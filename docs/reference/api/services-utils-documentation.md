# WhaleFall 服务与工具函数索引

> 最后更新时间：2025-12-19 15:39:32；列出 `app/services` 与 `app/utils` 目录下所有函数 / 方法的引用概览。`引用情况` 基于代码搜索，若标记为“仅所在文件内部使用”，表示当前仅在声明文件内被调用。`用途` 字段提供简要描述，后续可按需补充详细语义。

## `app/services/account_classification/auto_classify_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AutoClassifyResult.to_payload` | `app/routes/accounts/classifications.py` | 构建对外响应载体 |
| `AutoClassifyService.__init__` | 仅所在文件内部使用 | 初始化自动分类服务 |
| `AutoClassifyService.auto_classify` | `app/routes/accounts/classifications.py` | 执行账户自动分类 |
| `AutoClassifyService._run_engine` | 仅所在文件内部使用 | 调度底层分类引擎 |
| `AutoClassifyService._as_int` | 仅所在文件内部使用 | 安全地将输入转换为整数 |
| `AutoClassifyService._normalize_instance_id` | 仅所在文件内部使用 | 规范化实例 ID |
| `AutoClassifyService._coerce_bool` | 仅所在文件内部使用 | 将输入值转换为布尔型 |
| `AutoClassifyService._normalize_errors` | 仅所在文件内部使用 | 规范化错误结构为字符串列表 |

## `app/services/account_classification/cache.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ClassificationCache.__init__` | 仅所在文件内部使用 | 构造缓存访问器 |
| `ClassificationCache.get_rules` | `app/services/account_classification/orchestrator.py` | 返回缓存中的分类规则数据 |
| `ClassificationCache.set_rules` | 同上 | 写入分类规则缓存 |
| `ClassificationCache.set_rules_by_db_type` | 同上 | 写入指定数据库类型的分类规则缓存 |
| `ClassificationCache.invalidate_all` | 同上 | 清空全部分类缓存数据 |
| `ClassificationCache.invalidate_db_type` | 同上 | 按数据库类型清空规则缓存 |

## `app/services/account_classification/classifiers/base.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `BaseRuleClassifier.evaluate` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py`, `app/services/account_classification/orchestrator.py` | 评估账户是否满足规则表达式 |
| `BaseRuleClassifier.supports` | 仅所在文件内部使用 | 检查是否支持指定的数据库类型 |

## `app/services/account_classification/classifiers/factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ClassifierFactory.__init__` | 仅所在文件内部使用 | 初始化分类器工厂 |
| `ClassifierFactory.get` | 仅所在文件内部使用 | 获取指定数据库类型的分类器 |

## `app/services/account_classification/classifiers/mysql_classifier.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `MySQLRuleClassifier.evaluate` | `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py`, `app/services/account_classification/orchestrator.py` | 评估账户是否满足 MySQL 规则表达式 |
| `MySQLRuleClassifier._resolve_operator` | `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py` | 解析规则组合运算符 |
| `MySQLRuleClassifier._match_global_privileges` | 仅所在文件内部使用 | 校验全局权限要求 |
| `MySQLRuleClassifier._has_excluded_privileges` | 仅所在文件内部使用 | 判断是否命中排除的全局权限 |
| `MySQLRuleClassifier._match_database_privileges` | 仅所在文件内部使用 | 校验数据库级权限 |
| `MySQLRuleClassifier._match_table_privileges` | 仅所在文件内部使用 | 校验表级权限 |
| `MySQLRuleClassifier._table_requirement_met` | 仅所在文件内部使用 | 判断单个表权限要求是否满足 |
| `MySQLRuleClassifier._match_roles` | `app/services/account_classification/classifiers/oracle_classifier.py` | 校验角色要求 |
| `MySQLRuleClassifier._extract_perm_names` | 仅所在文件内部使用 | 从权限数据中提取权限名称集合 |
| `MySQLRuleClassifier._normalize_db_requirement` | 仅所在文件内部使用 | 规范化数据库权限要求 |
| `MySQLRuleClassifier._normalize_table_requirement` | 仅所在文件内部使用 | 规范化表权限要求 |
| `MySQLRuleClassifier._ensure_list` | `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 确保值为列表格式 |

## `app/services/account_classification/classifiers/oracle_classifier.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleRuleClassifier.evaluate` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py`, `app/services/account_classification/orchestrator.py` | 评估账户是否满足 Oracle 规则表达式 |
| `OracleRuleClassifier._resolve_operator` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py` | 解析逻辑运算符 |
| `OracleRuleClassifier._combine_results` | `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py` | 根据 operator 汇总布尔结果 |
| `OracleRuleClassifier._normalize_tablespace_privileges` | 仅所在文件内部使用 | 支持 dict/list 两种结构的表空间权限 |
| `OracleRuleClassifier._normalize_tablespace_requirements` | 仅所在文件内部使用 | 规范化规则中的表空间权限要求 |
| `OracleRuleClassifier._ensure_list` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 确保值为列表 |
| `OracleRuleClassifier._match_roles` | `app/services/account_classification/classifiers/mysql_classifier.py` | 校验角色匹配 |
| `OracleRuleClassifier._match_system_privileges` | 仅所在文件内部使用 | 校验系统权限 |
| `OracleRuleClassifier._match_object_privileges` | 仅所在文件内部使用 | 校验对象权限 |
| `OracleRuleClassifier._object_requirement_satisfied` | 仅所在文件内部使用 | 检查单个对象权限要求是否满足 |
| `OracleRuleClassifier._match_tablespace_privileges` | 仅所在文件内部使用 | 校验表空间权限 |
| `OracleRuleClassifier._tablespace_requirement_satisfied` | 仅所在文件内部使用 | 判断表空间权限是否满足 |

## `app/services/account_classification/classifiers/postgresql_classifier.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLRuleClassifier.evaluate` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py`, `app/services/account_classification/orchestrator.py` | 评估账户是否满足 PostgreSQL 规则表达式 |
| `PostgreSQLRuleClassifier._resolve_operator` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py` | 负责 resolve operator 相关逻辑 |
| `PostgreSQLRuleClassifier._extract_priv_names` | 仅所在文件内部使用 | 提取权限名称集合 |
| `PostgreSQLRuleClassifier._combine_results` | `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py` | 根据 operator 聚合布尔结果 |
| `PostgreSQLRuleClassifier._match_predefined_roles` | 仅所在文件内部使用 | 负责 match predefined roles 相关逻辑 |
| `PostgreSQLRuleClassifier._match_role_attributes` | 仅所在文件内部使用 | 负责 match role attributes 相关逻辑 |
| `PostgreSQLRuleClassifier._match_privileges` | 仅所在文件内部使用 | 负责 match privileges 相关逻辑 |

## `app/services/account_classification/classifiers/sqlserver_classifier.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerRuleClassifier.evaluate` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/orchestrator.py` | 评估账户是否满足 SQL Server 规则表达式 |
| `SQLServerRuleClassifier._resolve_operator` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py` | 负责 resolve operator 相关逻辑 |
| `SQLServerRuleClassifier._combine_results` | `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py` | 根据逻辑运算符合并匹配结果 |
| `SQLServerRuleClassifier._match_server_roles` | 仅所在文件内部使用 | 匹配服务器角色 |
| `SQLServerRuleClassifier._match_database_roles` | 仅所在文件内部使用 | 匹配数据库角色 |
| `SQLServerRuleClassifier._match_server_permissions` | 仅所在文件内部使用 | 匹配服务器权限 |
| `SQLServerRuleClassifier._match_database_permissions` | 仅所在文件内部使用 | 匹配数据库权限 |
| `SQLServerRuleClassifier._ensure_str_sequence` | 仅所在文件内部使用 | 将任意输入规范化为字符串列表 |

## `app/services/account_classification/orchestrator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountClassificationService.__init__` | 仅所在文件内部使用 | 初始化分类编排服务 |
| `AccountClassificationService.auto_classify_accounts` | `app/services/account_classification/auto_classify_service.py` | 执行优化版账户自动分类流程 |
| `AccountClassificationService._perform_auto_classify` | 仅所在文件内部使用 | 执行自动分类并返回摘要 |
| `AccountClassificationService.invalidate_cache` | `app/routes/cache.py`, `app/services/form_service/classification_rule_service.py` | 清空缓存中的全部分类规则数据 |
| `AccountClassificationService.invalidate_db_type_cache` | `app/routes/cache.py`, `app/services/account_classification/cache.py`, `app/services/cache_service.py` | 按数据库类型清理缓存 |
| `AccountClassificationService._get_rules_sorted_by_priority` | 仅所在文件内部使用 | 按优先级获取分类规则列表 |
| `AccountClassificationService._group_accounts_by_db_type` | 仅所在文件内部使用 | 按数据库类型分组账户 |
| `AccountClassificationService._group_rules_by_db_type` | 仅所在文件内部使用 | 按数据库类型分组分类规则 |
| `AccountClassificationService._classify_accounts_by_db_type` | 仅所在文件内部使用 | 基于数据库类型执行分类 |
| `AccountClassificationService._classify_single_db_type` | 仅所在文件内部使用 | 对单一数据库类型执行分类 |
| `AccountClassificationService._find_accounts_matching_rule` | 仅所在文件内部使用 | 筛选匹配指定规则的账户 |
| `AccountClassificationService._evaluate_rule` | 仅所在文件内部使用 | 执行规则评估 |
| `AccountClassificationService._log_performance_stats` | 仅所在文件内部使用 | 输出性能统计日志 |

## `app/services/account_classification/repositories.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ClassificationRepository.fetch_active_rules` | `app/services/account_classification/orchestrator.py` | 获取所有启用的分类规则 |
| `ClassificationRepository.fetch_accounts` | `app/services/account_classification/orchestrator.py`, `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 获取需要分类的账户列表 |
| `ClassificationRepository.cleanup_all_assignments` | `app/services/account_classification/orchestrator.py` | 重新分类前清理所有既有分配关系 |
| `ClassificationRepository.upsert_assignments` | 同上 | 为指定账户集重新写入分类分配记录 |
| `ClassificationRepository.serialize_rules` | 同上 | 序列化规则模型以便写入缓存 |
| `ClassificationRepository.hydrate_rules` | 同上 | 从缓存字典还原规则模型 |

## `app/services/accounts_sync/account_query_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_accounts_by_instance` | `app/routes/instances/detail.py`, `app/routes/instances/manage.py` | 按实例获取账户列表 |

## `app/services/accounts_sync/accounts_sync_filters.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseFilterManager.__init__` | 仅所在文件内部使用 | 加载过滤配置并准备规则字典 |
| `DatabaseFilterManager._load_filter_rules` | 仅所在文件内部使用 | 从配置文件加载过滤规则配置 |
| `DatabaseFilterManager.get_safe_sql_filter_conditions` | 仅所在文件内部使用 | 获取安全的 SQL 过滤条件(参数化查询) |
| `DatabaseFilterManager._match_pattern` | 仅所在文件内部使用 | 模式匹配(支持 SQL LIKE 语法) |
| `DatabaseFilterManager.get_filter_rules` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 获取过滤规则 |

## `app/services/accounts_sync/accounts_sync_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountSyncService.__init__` | 仅所在文件内部使用 | 初始化账户同步服务 |
| `AccountSyncService.sync_accounts` | `app/routes/accounts/sync.py` | 统一账户同步入口 |
| `AccountSyncService._sync_single_instance` | 仅所在文件内部使用 | 单实例同步 - 无会话管理 |
| `AccountSyncService._sync_with_session` | 仅所在文件内部使用 | 带会话管理的同步 - 用于批量同步 |
| `AccountSyncService._sync_with_existing_session` | 仅所在文件内部使用 | 使用现有会话 ID 进行同步 |
| `AccountSyncService._build_result` | 仅所在文件内部使用 | 构建同步结果字典 |
| `AccountSyncService._emit_completion_log` | 仅所在文件内部使用 | 记录同步完成日志 |

## `app/services/accounts_sync/adapters/base_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `BaseAccountAdapter.fetch_remote_accounts` | `app/services/accounts_sync/coordinator.py` | 拉取远端账户信息 |
| `BaseAccountAdapter.enrich_permissions` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py`, `app/services/accounts_sync/coordinator.py` | 为账号列表补全权限信息 |
| `BaseAccountAdapter._fetch_raw_accounts` | `app/services/accounts_sync/adapters/mysql_adapter.py` | 具体数据库实现负责查询账户列表 |
| `BaseAccountAdapter._normalize_account` | 仅所在文件内部使用 | 将原始账户数据转换为标准结构 |

## `app/services/accounts_sync/adapters/factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_account_adapter` | `app/services/accounts_sync/coordinator.py` | 根据数据库类型获取账户同步适配器实例 |

## `app/services/accounts_sync/adapters/mysql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_MySQLConnectionProtocol.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `MySQLAccountAdapter.__init__` | 仅所在文件内部使用 | 初始化 MySQL 账户适配器 |
| `MySQLAccountAdapter._fetch_raw_accounts` | `app/services/accounts_sync/adapters/base_adapter.py` | 拉取 MySQL 原始账户信息 |
| `MySQLAccountAdapter._normalize_account` | 同上 | 规范化 MySQL 账户信息 |
| `MySQLAccountAdapter._build_filter_conditions` | `app/services/accounts_sync/adapters/postgresql_adapter.py` | 构建 MySQL 账户过滤条件 |
| `MySQLAccountAdapter._get_user_permissions` | `app/services/accounts_sync/adapters/oracle_adapter.py` | 获取 MySQL 用户权限详情 |
| `MySQLAccountAdapter.enrich_permissions` | `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py`, `app/services/accounts_sync/coordinator.py` | 丰富 MySQL 账户的权限信息 |
| `MySQLAccountAdapter._parse_grant_statement` | 仅所在文件内部使用 | 解析 MySQL GRANT 语句 |
| `MySQLAccountAdapter._extract_privileges` | 仅所在文件内部使用 | 从权限字符串中提取权限列表 |
| `MySQLAccountAdapter._expand_all_privileges` | 仅所在文件内部使用 | 返回 ALL PRIVILEGES 展开的权限列表 |

## `app/services/accounts_sync/adapters/oracle_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleAccountAdapter.__init__` | 仅所在文件内部使用 | 初始化 Oracle 适配器,配置日志与过滤管理器 |
| `OracleAccountAdapter._fetch_raw_accounts` | `app/services/accounts_sync/adapters/base_adapter.py`, `app/services/accounts_sync/adapters/mysql_adapter.py` | 拉取 Oracle 原始账户信息 |
| `OracleAccountAdapter._normalize_account` | `app/services/accounts_sync/adapters/base_adapter.py` | 规范化 Oracle 账户信息 |
| `OracleAccountAdapter._fetch_users` | 仅所在文件内部使用 | 读取 Oracle 用户列表 |
| `OracleAccountAdapter._get_user_permissions` | `app/services/accounts_sync/adapters/mysql_adapter.py` | 查询单个用户的权限快照 |
| `OracleAccountAdapter.enrich_permissions` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py`, `app/services/accounts_sync/coordinator.py` | 丰富 Oracle 账户的权限信息 |
| `OracleAccountAdapter._get_roles` | 仅所在文件内部使用 | 查询用户拥有的角色 |
| `OracleAccountAdapter._get_system_privileges` | 仅所在文件内部使用 | 查询用户拥有的系统权限 |
| `OracleAccountAdapter._get_tablespace_privileges` | `app/services/accounts_sync/adapters/postgresql_adapter.py` | 查询用户的表空间配额信息 |

## `app/services/accounts_sync/adapters/postgresql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLAccountAdapter.__init__` | 仅所在文件内部使用 | 初始化 PostgreSQL 适配器,挂载日志与过滤器 |
| `PostgreSQLAccountAdapter._get_connection` | `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 将通用连接对象规范为同步协议连接 |
| `PostgreSQLAccountAdapter._to_isoformat` | 仅所在文件内部使用 | 将日期/时间值转换为 ISO 字符串 |
| `PostgreSQLAccountAdapter._fetch_raw_accounts` | `app/services/accounts_sync/adapters/base_adapter.py`, `app/services/accounts_sync/adapters/mysql_adapter.py` | 拉取 PostgreSQL 原始账户信息 |
| `PostgreSQLAccountAdapter._normalize_account` | `app/services/accounts_sync/adapters/base_adapter.py` | 规范化 PostgreSQL 账户信息 |
| `PostgreSQLAccountAdapter._build_filter_conditions` | `app/services/accounts_sync/adapters/mysql_adapter.py` | 根据配置生成账号过滤条件 |
| `PostgreSQLAccountAdapter._get_role_permissions` | 仅所在文件内部使用 | 聚合指定角色的权限信息 |
| `PostgreSQLAccountAdapter.enrich_permissions` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py`, `app/services/accounts_sync/coordinator.py` | 丰富 PostgreSQL 账户的权限信息 |
| `PostgreSQLAccountAdapter._merge_seed_permissions` | 仅所在文件内部使用 | 将已有权限数据与新查询数据合并 |
| `PostgreSQLAccountAdapter._apply_login_flags` | 仅所在文件内部使用 | 根据权限结果更新账户状态 |
| `PostgreSQLAccountAdapter._get_role_attributes` | 仅所在文件内部使用 | 查询角色属性 |
| `PostgreSQLAccountAdapter._get_predefined_roles` | 仅所在文件内部使用 | 查询用户所属的预定义角色 |
| `PostgreSQLAccountAdapter._get_database_privileges` | 仅所在文件内部使用 | 查询用户在各数据库上的权限 |
| `PostgreSQLAccountAdapter._get_tablespace_privileges` | `app/services/accounts_sync/adapters/oracle_adapter.py` | 查询用户在各表空间上的权限 |

## `app/services/accounts_sync/adapters/sqlserver_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerAccountAdapter.__init__` | 仅所在文件内部使用 | 初始化 SQL Server 适配器,配置日志与过滤管理器 |
| `SQLServerAccountAdapter._normalize_str` | 仅所在文件内部使用 | 将输入转换为字符串,非字符串返回 None |
| `SQLServerAccountAdapter._normalize_str_list` | 仅所在文件内部使用 | 将序列转换为字符串列表,忽略非字符串元素 |
| `SQLServerAccountAdapter._get_connection` | `app/services/accounts_sync/adapters/postgresql_adapter.py` | 将泛型连接对象转换为同步查询协议 |
| `SQLServerAccountAdapter._fetch_raw_accounts` | `app/services/accounts_sync/adapters/base_adapter.py`, `app/services/accounts_sync/adapters/mysql_adapter.py` | 拉取 SQL Server 原始账户信息 |
| `SQLServerAccountAdapter._normalize_account` | `app/services/accounts_sync/adapters/base_adapter.py` | 规范化 SQL Server 账户信息 |
| `SQLServerAccountAdapter.enrich_permissions` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/coordinator.py` | 丰富 SQL Server 账户的权限信息 |
| `SQLServerAccountAdapter._fetch_logins` | 仅所在文件内部使用 | 查询服务器登录账户 |
| `SQLServerAccountAdapter._compile_like_patterns` | 仅所在文件内部使用 | 将 SQL LIKE 模式编译为正则表达式 |
| `SQLServerAccountAdapter._get_login_permissions` | 仅所在文件内部使用 | 组装登录账户的权限快照 |
| `SQLServerAccountAdapter._deduplicate_preserve_order` | 仅所在文件内部使用 | 去重并保持原始顺序 |
| `SQLServerAccountAdapter._copy_database_permissions` | 仅所在文件内部使用 | 深拷贝数据库权限结构并去重 |
| `SQLServerAccountAdapter._get_server_roles_bulk` | 仅所在文件内部使用 | 批量查询服务器角色 |
| `SQLServerAccountAdapter._get_server_permissions_bulk` | 仅所在文件内部使用 | 批量查询服务器权限 |
| `SQLServerAccountAdapter._get_all_users_database_permissions_batch` | 仅所在文件内部使用 | 批量查询所有用户的数据库权限(优化版) |
| `SQLServerAccountAdapter._normalize_sid` | 仅所在文件内部使用 | 标准化 SID 字节串 |
| `SQLServerAccountAdapter._sid_to_hex_literal` | 仅所在文件内部使用 | 将 SID 字节串转换为十六进制文本表示 |
| `SQLServerAccountAdapter._get_accessible_databases` | 仅所在文件内部使用 | 获取可访问数据库列表 |
| `SQLServerAccountAdapter._map_sids_to_logins` | 仅所在文件内部使用 | 构建 SID 到登录名的映射以及用于筛选的 JSON 负载 |
| `SQLServerAccountAdapter._build_database_permission_queries` | 仅所在文件内部使用 | 拼接查询数据库 principals/roles/permissions 的 SQL |
| `SQLServerAccountAdapter._target_sid_cte` | 仅所在文件内部使用 | 返回 target_sids 公共 CTE |
| `SQLServerAccountAdapter._compose_database_union` | 仅所在文件内部使用 | 将单库模板渲染为 UNION ALL 语句 |
| `SQLServerAccountAdapter._render_database_template` | 仅所在文件内部使用 | 将模板中的占位符替换为具体数据库名 |
| `SQLServerAccountAdapter._get_database_permission_templates` | 仅所在文件内部使用 | 构建数据库权限查询模板集合 |
| `SQLServerAccountAdapter._fetch_principal_data` | 仅所在文件内部使用 | 执行合并后的 SQL 并返回结果 |
| `SQLServerAccountAdapter._build_principal_lookup` | 仅所在文件内部使用 | 构建数据库 + principal_id 到登录名的映射 |
| `SQLServerAccountAdapter._aggregate_database_permissions` | 仅所在文件内部使用 | 根据查询结果组装最终权限结构 |
| `SQLServerAccountAdapter._ensure_dict` | 仅所在文件内部使用 | 负责 ensure dict 相关逻辑 |
| `SQLServerAccountAdapter._ensure_list` | `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py` | 负责 ensure list 相关逻辑 |
| `SQLServerAccountAdapter._apply_role_rows` | 仅所在文件内部使用 | 负责 apply role rows 相关逻辑 |
| `SQLServerAccountAdapter._apply_permission_rows` | 仅所在文件内部使用 | 负责 apply permission rows 相关逻辑 |
| `SQLServerAccountAdapter._get_database_permissions_by_name` | 仅所在文件内部使用 | 基于用户名回退查询数据库权限,用于无法读取 SID 的场景 |
| `SQLServerAccountAdapter._build_db_permission_queries_by_name` | 仅所在文件内部使用 | 构建基于用户名匹配的数据库权限查询 SQL |
| `SQLServerAccountAdapter._fetch_principal_data_by_name` | 仅所在文件内部使用 | 执行基于用户名的权限查询 |
| `SQLServerAccountAdapter._build_principal_lookup_by_name` | 仅所在文件内部使用 | 从 username 直接构建 principal 映射 |
| `SQLServerAccountAdapter._is_permissions_empty` | 仅所在文件内部使用 | 判断聚合结果是否完全为空权限 |
| `SQLServerAccountAdapter._ensure_permission_list` | 仅所在文件内部使用 | 确保权限容器中的指定键为列表并返回引用 |
| `SQLServerAccountAdapter._ensure_permission_map` | 仅所在文件内部使用 | 确保权限容器中的指定键为映射并返回引用 |
| `SQLServerAccountAdapter._ensure_permission_list_in_map` | 仅所在文件内部使用 | 确保映射中键对应列表并返回引用 |
| `SQLServerAccountAdapter._append_permission_entry` | 仅所在文件内部使用 | 将权限写入对应层级 |
| `SQLServerAccountAdapter._append_database_permission` | 仅所在文件内部使用 | 记录数据库级权限 |
| `SQLServerAccountAdapter._append_schema_permission` | 仅所在文件内部使用 | 记录模式级权限 |
| `SQLServerAccountAdapter._append_object_permission` | 仅所在文件内部使用 | 记录表或列级权限 |
| `SQLServerAccountAdapter._quote_identifier` | 仅所在文件内部使用 | 为 SQL Server 标识符加方括号并转义 |

## `app/services/accounts_sync/coordinator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountSyncCoordinator.__init__` | 仅所在文件内部使用 | 绑定实例并准备同步依赖 |
| `AccountSyncCoordinator.__enter__` | 仅所在文件内部使用 | 进入上下文时建立数据库连接 |
| `AccountSyncCoordinator.__exit__` | 仅所在文件内部使用 | 退出上下文时释放连接资源 |
| `AccountSyncCoordinator.connect` | 仅所在文件内部使用 | 建立到数据库实例的连接 |
| `AccountSyncCoordinator.disconnect` | 仅所在文件内部使用 | 断开数据库连接并清理资源 |
| `AccountSyncCoordinator._ensure_connection` | `app/services/database_sync/coordinator.py` | 确保数据库连接有效,如果无效则尝试重新连接 |
| `AccountSyncCoordinator.fetch_remote_accounts` | 仅所在文件内部使用 | 从远程数据库获取账户列表 |
| `AccountSyncCoordinator.synchronize_inventory` | `app/routes/databases/capacity_sync.py`, `app/services/database_sync/coordinator.py`, `app/tasks/capacity_collection_tasks.py` | 执行清单阶段同步,同步账户基本信息 |
| `AccountSyncCoordinator.synchronize_permissions` | 仅所在文件内部使用 | 执行权限阶段同步,同步活跃账户的权限信息 |
| `AccountSyncCoordinator.sync_all` | `app/services/accounts_sync/accounts_sync_service.py`, `app/tasks/accounts_sync_tasks.py` | 执行完整的两阶段同步流程 |

## `app/services/accounts_sync/inventory_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountInventoryManager.__init__` | 仅所在文件内部使用 | 初始化账户清单管理器 |
| `AccountInventoryManager.synchronize` | `app/services/accounts_sync/coordinator.py`, `app/services/database_sync/coordinator.py` | 根据远端账户列表同步 InstanceAccount 表 |

## `app/services/accounts_sync/permission_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PermissionSyncError.__init__` | 仅所在文件内部使用 | 初始化权限同步错误 |
| `AccountPermissionManager.__init__` | 仅所在文件内部使用 | 初始化账户权限管理器 |
| `AccountPermissionManager.synchronize` | `app/services/accounts_sync/coordinator.py`, `app/services/database_sync/coordinator.py` | 同步账户权限数据 |
| `AccountPermissionManager._sync_single_account` | 仅所在文件内部使用 | 负责 sync single account 相关逻辑 |
| `AccountPermissionManager._extract_remote_context` | 仅所在文件内部使用 | 提取远程权限与标志 |
| `AccountPermissionManager._find_permission_record` | 仅所在文件内部使用 | 查找或回填账户权限记录 |
| `AccountPermissionManager._process_existing_permission` | 仅所在文件内部使用 | 负责 process existing permission 相关逻辑 |
| `AccountPermissionManager._process_new_permission` | 仅所在文件内部使用 | 负责 process new permission 相关逻辑 |
| `AccountPermissionManager._mark_synced` | 仅所在文件内部使用 | 更新同步时间戳 |
| `AccountPermissionManager._handle_log_failure` | 仅所在文件内部使用 | 统一处理日志记录异常 |
| `AccountPermissionManager._commit_changes` | 仅所在文件内部使用 | 提交数据库更改 |
| `AccountPermissionManager._finalize_summary` | 仅所在文件内部使用 | 组装同步摘要并输出日志 |
| `AccountPermissionManager._apply_permissions` | 仅所在文件内部使用 | 将权限快照写入账户记录 |
| `AccountPermissionManager._calculate_diff` | 仅所在文件内部使用 | 计算新旧权限之间的差异 |
| `AccountPermissionManager._collect_privilege_changes` | 仅所在文件内部使用 | 收集权限字段的差异 |
| `AccountPermissionManager._collect_other_changes` | 仅所在文件内部使用 | 收集非权限字段差异 |
| `AccountPermissionManager._collect_flag_diff_entries` | 仅所在文件内部使用 | 构建布尔标志差异 |
| `AccountPermissionManager._collect_non_privilege_changes` | 仅所在文件内部使用 | 处理除权限字段之外的差异 |
| `AccountPermissionManager._determine_change_type` | 仅所在文件内部使用 | 根据差异条目判断变更类型 |
| `AccountPermissionManager._log_change` | 仅所在文件内部使用 | 将权限变更写入变更日志表 |
| `AccountPermissionManager._build_initial_diff_payload` | 仅所在文件内部使用 | 构建新账户的权限差异初始结构 |
| `AccountPermissionManager._build_privilege_diff_entries` | 仅所在文件内部使用 | 比较权限字段并返回差异条目 |
| `AccountPermissionManager._build_other_diff_entry` | 仅所在文件内部使用 | 构建非权限字段的差异条目 |
| `AccountPermissionManager._build_other_description` | 仅所在文件内部使用 | 生成非权限字段差异的自然语言描述 |
| `AccountPermissionManager._build_change_summary` | 仅所在文件内部使用 | 根据差异构建日志摘要 |
| `AccountPermissionManager._summarize_privilege_changes` | 仅所在文件内部使用 | 构建权限差异的文本 |
| `AccountPermissionManager._summarize_other_changes` | 仅所在文件内部使用 | 构建非权限变更说明 |
| `AccountPermissionManager._is_mapping` | 仅所在文件内部使用 | 判断值是否为映射类型 |
| `AccountPermissionManager._normalize_mapping` | 仅所在文件内部使用 | 将权限映射标准化为 {str: set} 结构 |
| `AccountPermissionManager._normalize_sequence` | 仅所在文件内部使用 | 将单值或序列转换为集合形式 |
| `AccountPermissionManager._repr_value` | 仅所在文件内部使用 | 将值转换为日志友好的文本 |
| `AccountPermissionManager._count_permissions_by_action` | 仅所在文件内部使用 | 统计差异中指定动作的权限数量 |

## `app/services/aggregation/aggregation_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AggregationService.__init__` | 仅所在文件内部使用 | 初始化聚合服务 |
| `AggregationService._get_instance_or_raise` | 仅所在文件内部使用 | 根据 ID 获取实例,若不存在则抛错 |
| `AggregationService._ensure_partition_for_date` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/instance_aggregation_runner.py` | 保留接口,当前环境无需分区预处理 |
| `AggregationService._commit_with_partition_retry` | 同上 | 提交聚合记录 |
| `AggregationService._default_use_current_period` | 仅所在文件内部使用 | 根据周期类型返回默认是否使用当前周期 |
| `AggregationService._resolve_use_current_period` | 仅所在文件内部使用 | 结合覆盖配置判断是否使用当前周期 |
| `AggregationService._resolve_use_current_period_from_map` | 仅所在文件内部使用 | 从覆盖映射读取周期策略 |
| `AggregationService._period_range` | 仅所在文件内部使用 | 根据周期类型返回起止日期 |
| `AggregationService._to_exception` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/instance_aggregation_runner.py` | 将 BaseException 收敛为 Exception,避免日志类型告警 |
| `AggregationService._aggregate_database_for_instance` | 仅所在文件内部使用 | 对指定实例执行数据库级聚合 |
| `AggregationService._aggregate_instance_for_instance` | 仅所在文件内部使用 | 对指定实例执行实例级聚合 |
| `AggregationService._inactive_instance_summary` | 仅所在文件内部使用 | 构造实例未激活时的聚合摘要 |
| `AggregationService._aggregate_period` | 仅所在文件内部使用 | 统一执行指定周期的聚合 |
| `AggregationService._normalize_period_type` | 仅所在文件内部使用 | 验证并标准化周期类型 |
| `AggregationService._normalize_scope` | 仅所在文件内部使用 | 解析运行范围并返回执行标记 |
| `AggregationService._build_runner_callbacks` | 仅所在文件内部使用 | 将回调映射转换为 RunnerCallbacks |
| `AggregationService._run_period_runner` | 仅所在文件内部使用 | 在启用时执行聚合 Runner |
| `AggregationService._summarize_current_period_status` | 仅所在文件内部使用 | 根据子任务结果计算整体状态 |
| `AggregationService._execute_instance_period` | 仅所在文件内部使用 | 执行单个实例周期聚合并封装异常 |
| `AggregationService._normalize_periods` | 仅所在文件内部使用 | 标准化周期参数列表 |
| `AggregationService.aggregate_database_periods` | `app/tasks/capacity_aggregation_tasks.py` | 计算数据库级聚合结果 |
| `AggregationService.calculate_all_aggregations` | 仅所在文件内部使用 | 计算所有实例的统计聚合数据 |
| `AggregationService.calculate_daily_aggregations` | 仅所在文件内部使用 | 计算每日统计聚合(处理今日数据) |
| `AggregationService.aggregate_current_period` | `app/routes/capacity/aggregations.py` | 计算当前周期(含今日)统计聚合 |
| `AggregationService.calculate_weekly_aggregations` | 仅所在文件内部使用 | 计算每周统计聚合 |
| `AggregationService.calculate_monthly_aggregations` | 仅所在文件内部使用 | 计算每月统计聚合 |
| `AggregationService.calculate_quarterly_aggregations` | 仅所在文件内部使用 | 计算每季度统计聚合 |
| `AggregationService.calculate_daily_database_aggregations_for_instance` | `app/routes/databases/capacity_sync.py`, `app/tasks/capacity_collection_tasks.py` | 为指定实例计算当日数据库聚合 |
| `AggregationService.calculate_weekly_database_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算周数据库聚合 |
| `AggregationService.calculate_monthly_database_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算月数据库聚合 |
| `AggregationService.calculate_quarterly_database_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算季度数据库聚合 |
| `AggregationService.calculate_daily_instance_aggregations` | 仅所在文件内部使用 | 计算每日实例统计聚合 |
| `AggregationService.calculate_weekly_instance_aggregations` | 仅所在文件内部使用 | 计算每周实例统计聚合 |
| `AggregationService.calculate_monthly_instance_aggregations` | 仅所在文件内部使用 | 计算每月实例统计聚合 |
| `AggregationService.calculate_quarterly_instance_aggregations` | 仅所在文件内部使用 | 计算每季度实例统计聚合 |
| `AggregationService.calculate_instance_aggregations` | `app/tasks/capacity_aggregation_tasks.py` | 计算指定实例的多周期聚合 |
| `AggregationService.calculate_daily_aggregations_for_instance` | `app/routes/databases/capacity_sync.py`, `app/tasks/capacity_collection_tasks.py` | 为指定实例计算日统计聚合 |
| `AggregationService.calculate_weekly_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算周统计聚合 |
| `AggregationService.calculate_monthly_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算月统计聚合 |
| `AggregationService.calculate_quarterly_aggregations_for_instance` | 仅所在文件内部使用 | 为指定实例计算季度统计聚合 |
| `AggregationService.calculate_period_aggregations` | `app/tasks/capacity_aggregation_tasks.py` | 计算指定时间范围的聚合数据 |
| `AggregationService.get_aggregations` | 仅所在文件内部使用 | 获取数据库级聚合数据 |
| `AggregationService.get_instance_aggregations` | 仅所在文件内部使用 | 获取实例整体聚合数据 |

## `app/services/aggregation/calculator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PeriodCalculator.__init__` | 仅所在文件内部使用 | 初始化周期计算器 |
| `PeriodCalculator.today` | 仅所在文件内部使用 | 获取当前日期 |
| `PeriodCalculator.get_last_period` | `app/services/aggregation/aggregation_service.py` | 获取上一周期的开始和结束日期 |
| `PeriodCalculator.get_current_period` | `app/routes/capacity/aggregations.py`, `app/services/aggregation/aggregation_service.py` | 获取当前周期的自然起止日期 |
| `PeriodCalculator.get_previous_period` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/instance_aggregation_runner.py` | 根据当前周期起止日期推算上一周期范围 |
| `PeriodCalculator._normalize` | 仅所在文件内部使用 | 规范化周期类型字符串 |

## `app/services/aggregation/callbacks.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |

## `app/services/aggregation/database_aggregation_runner.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseAggregationRunner.__init__` | 仅所在文件内部使用 | 初始化数据库聚合执行器 |
| `DatabaseAggregationRunner._invoke_callback` | `app/services/aggregation/instance_aggregation_runner.py` | 安全执行回调 |
| `DatabaseAggregationRunner.aggregate_period` | `app/services/aggregation/aggregation_service.py` | 聚合所有激活实例在指定周期内的数据库统计 |
| `DatabaseAggregationRunner.aggregate_database_period` | 同上 | 为指定实例计算指定周期的数据库级聚合 |
| `DatabaseAggregationRunner.aggregate_daily_for_instance` | 仅所在文件内部使用 | 为指定实例计算当天数据库级聚合 |
| `DatabaseAggregationRunner._query_database_stats` | 仅所在文件内部使用 | 查询实例在指定时间范围内的容量数据 |
| `DatabaseAggregationRunner._group_by_database` | 仅所在文件内部使用 | 按数据库名称分组统计数据 |
| `DatabaseAggregationRunner._persist_database_aggregation` | 仅所在文件内部使用 | 保存单个数据库的聚合结果 |
| `DatabaseAggregationRunner._apply_change_statistics` | `app/services/aggregation/instance_aggregation_runner.py` | 计算相邻周期的增量统计 |
| `DatabaseAggregationRunner._to_float` | `app/services/aggregation/instance_aggregation_runner.py`, `app/services/aggregation/query_service.py` | 将数值或 Decimal 转换为 float,过滤 ColumnElement |
| `DatabaseAggregationRunner._to_int_value` | 仅所在文件内部使用 | 将可能的列值转换为整数 |
| `DatabaseAggregationRunner._to_exception` | `app/services/aggregation/aggregation_service.py`, `app/services/aggregation/instance_aggregation_runner.py` | 规范化日志异常类型 |

## `app/services/aggregation/instance_aggregation_runner.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `InstanceAggregationRunner.__init__` | 仅所在文件内部使用 | 初始化实例聚合执行器 |
| `InstanceAggregationRunner._invoke_callback` | `app/services/aggregation/database_aggregation_runner.py` | 安全地执行回调 |
| `InstanceAggregationRunner.aggregate_period` | `app/services/aggregation/aggregation_service.py` | 聚合所有激活实例在指定周期内的实例统计 |
| `InstanceAggregationRunner.aggregate_instance_period` | 同上 | 聚合单个实例的指定周期,并返回汇总信息 |
| `InstanceAggregationRunner._query_instance_stats` | 仅所在文件内部使用 | 查询实例在指定时间段的统计记录 |
| `InstanceAggregationRunner._persist_instance_aggregation` | 仅所在文件内部使用 | 保存实例聚合结果 |
| `InstanceAggregationRunner._apply_change_statistics` | `app/services/aggregation/database_aggregation_runner.py` | 计算实例聚合的增量统计 |
| `InstanceAggregationRunner._to_float` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/query_service.py` | 将列值安全转换为 float |
| `InstanceAggregationRunner._to_exception` | `app/services/aggregation/aggregation_service.py`, `app/services/aggregation/database_aggregation_runner.py` | 将 BaseException 归一为 Exception 便于日志记录 |

## `app/services/aggregation/query_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AggregationQueryService.get_database_aggregations` | `app/services/aggregation/aggregation_service.py` | 获取数据库级聚合数据 |
| `AggregationQueryService.get_instance_aggregations` | 同上 | 获取实例级聚合数据 |
| `AggregationQueryService._format_database_aggregation` | 仅所在文件内部使用 | 格式化数据库级聚合记录 |
| `AggregationQueryService._format_instance_aggregation` | 仅所在文件内部使用 | 格式化实例级聚合记录 |
| `AggregationQueryService._safe_iso_date` | 仅所在文件内部使用 | 将日期列安全转换为 ISO 字符串 |
| `AggregationQueryService._safe_iso_datetime` | 仅所在文件内部使用 | 将 datetime 列安全转换为 ISO 字符串 |
| `AggregationQueryService._to_int` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py` | Column/Decimal 安全转换为 int |
| `AggregationQueryService._to_float` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/instance_aggregation_runner.py` | Column/Decimal 安全转换为 float,缺省返回 0 |
| `AggregationQueryService._to_optional_float` | 仅所在文件内部使用 | 允许空值的 float 转换 |
| `AggregationQueryService._safe_str` | 仅所在文件内部使用 | 将可选字符串字段安全提取 |

## `app/services/aggregation/results.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PeriodSummary.status` | 仅所在文件内部使用 | 计算聚合状态 |
| `PeriodSummary.to_dict` | 仅所在文件内部使用 | 转换为字典格式 |
| `InstanceSummary.status` | 仅所在文件内部使用 | 计算聚合状态 |
| `InstanceSummary.to_dict` | 仅所在文件内部使用 | 转换为字典格式 |

## `app/services/cache_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CacheService.__init__` | 仅所在文件内部使用 | 初始化缓存服务并设置默认 TTL |
| `CacheService._generate_cache_key` | 仅所在文件内部使用 | 生成缓存键 |
| `CacheService.invalidate_user_cache` | `app/routes/cache.py` | 清除用户的所有缓存 |
| `CacheService.invalidate_instance_cache` | 同上 | 清除实例的所有缓存 |
| `CacheService.get_cache_stats` | 同上 | 获取缓存统计信息 |
| `CacheService.get_rule_evaluation_cache` | 仅所在文件内部使用 | 获取规则评估缓存 |
| `CacheService.set_rule_evaluation_cache` | 仅所在文件内部使用 | 设置规则评估缓存 |
| `CacheService.get_classification_rules_cache` | `app/services/account_classification/cache.py` | 获取分类规则缓存 |
| `CacheService.set_classification_rules_cache` | 同上 | 设置分类规则缓存 |
| `CacheService.invalidate_account_cache` | 仅所在文件内部使用 | 清除账户相关缓存 |
| `CacheService.invalidate_classification_cache` | `app/services/account_classification/cache.py` | 清除分类相关缓存 |
| `CacheService.invalidate_all_rule_evaluation_cache` | 仅所在文件内部使用 | 清除所有规则评估缓存 |
| `CacheService.get_classification_rules_by_db_type_cache` | `app/routes/cache.py` | 获取按数据库类型分类的规则缓存 |
| `CacheService.set_classification_rules_by_db_type_cache` | `app/services/account_classification/cache.py` | 设置按数据库类型分类的规则缓存 |
| `CacheService.invalidate_db_type_cache` | `app/routes/cache.py`, `app/services/account_classification/cache.py` | 清除特定数据库类型的缓存 |
| `CacheService.invalidate_all_db_type_cache` | `app/services/account_classification/cache.py` | 清除所有数据库类型的规则缓存 |
| `CacheService.health_check` | `app/routes/health.py` | 缓存健康检查 |
| `init_cache_service` | `app/__init__.py` | 初始化缓存服务 |

## `app/services/connection_adapters/adapters/base.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_default_schema` | `app/services/connection_adapters/adapters/mysql_adapter.py`, `app/services/connection_adapters/adapters/postgresql_adapter.py`, `app/services/connection_adapters/adapters/sqlserver_adapter.py` | 根据数据库类型返回默认 schema/database 名称 |
| `DatabaseConnection.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseConnection.connect` | 仅所在文件内部使用 | 建立数据库连接 |
| `DatabaseConnection.disconnect` | 仅所在文件内部使用 | 断开数据库连接 |
| `DatabaseConnection.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py` | 测试数据库连接结果 |
| `DatabaseConnection.execute_query` | 仅所在文件内部使用 | 执行查询并返回结果 |
| `DatabaseConnection.get_version` | `app/services/connection_adapters/adapters/mysql_adapter.py`, `app/services/connection_adapters/adapters/oracle_adapter.py`, `app/services/connection_adapters/adapters/postgresql_adapter.py`, `app/services/connection_adapters/adapters/sqlserver_adapter.py`, `app/services/connection_adapters/connection_test_service.py` | 获取数据库版本号 |

## `app/services/connection_adapters/adapters/mysql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `MySQLConnection.connect` | 仅所在文件内部使用 | 建立 MySQL 连接并缓存连接对象 |
| `MySQLConnection.disconnect` | 仅所在文件内部使用 | 关闭当前连接并复位状态标识 |
| `MySQLConnection.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py` | 快速测试数据库连通性并返回版本信息 |
| `MySQLConnection.execute_query` | 仅所在文件内部使用 | 执行 SQL 查询并返回全部结果 |
| `MySQLConnection.get_version` | `app/services/connection_adapters/adapters/oracle_adapter.py`, `app/services/connection_adapters/adapters/postgresql_adapter.py`, `app/services/connection_adapters/adapters/sqlserver_adapter.py`, `app/services/connection_adapters/connection_test_service.py` | 查询数据库版本 |

## `app/services/connection_adapters/adapters/oracle_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleConnection.connect` | 仅所在文件内部使用 | 建立 Oracle 连接并在必要时初始化客户端 |
| `OracleConnection.disconnect` | 仅所在文件内部使用 | 断开 Oracle 连接并清理句柄 |
| `OracleConnection.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py` | 测试 Oracle 连接并返回版本信息 |
| `OracleConnection.execute_query` | 仅所在文件内部使用 | 执行 SQL 查询并返回全部行 |
| `OracleConnection.get_version` | `app/services/connection_adapters/adapters/mysql_adapter.py`, `app/services/connection_adapters/adapters/postgresql_adapter.py`, `app/services/connection_adapters/adapters/sqlserver_adapter.py`, `app/services/connection_adapters/connection_test_service.py` | 获取 Oracle 版本字符串 |

## `app/services/connection_adapters/adapters/postgresql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLConnection.connect` | 仅所在文件内部使用 | 建立 PostgreSQL 连接 |
| `PostgreSQLConnection.disconnect` | 仅所在文件内部使用 | 关闭 PostgreSQL 连接并复位状态 |
| `PostgreSQLConnection.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py` | 测试连接并返回版本信息 |
| `PostgreSQLConnection.execute_query` | 仅所在文件内部使用 | 执行 SQL 查询并返回所有结果 |
| `PostgreSQLConnection.get_version` | `app/services/connection_adapters/adapters/mysql_adapter.py`, `app/services/connection_adapters/adapters/oracle_adapter.py`, `app/services/connection_adapters/adapters/sqlserver_adapter.py`, `app/services/connection_adapters/connection_test_service.py` | 查询数据库版本字符串 |

## `app/services/connection_adapters/adapters/sqlserver_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerConnection.__init__` | 仅所在文件内部使用 | 初始化 SQL Server 连接适配器 |
| `SQLServerConnection.connect` | 仅所在文件内部使用 | 建立 SQL Server 连接(当前仅支持 pymssql) |
| `SQLServerConnection._try_pymssql_connection` | 仅所在文件内部使用 | 使用 pymssql 尝试连接 SQL Server |
| `SQLServerConnection.disconnect` | 仅所在文件内部使用 | 断开 SQL Server 连接并清理状态 |
| `SQLServerConnection.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py` | 测试连接并返回版本信息 |
| `SQLServerConnection.execute_query` | 仅所在文件内部使用 | 执行 SQL 查询并返回 `fetchall` 结果 |
| `SQLServerConnection.get_version` | `app/services/connection_adapters/adapters/mysql_adapter.py`, `app/services/connection_adapters/adapters/oracle_adapter.py`, `app/services/connection_adapters/adapters/postgresql_adapter.py`, `app/services/connection_adapters/connection_test_service.py` | 查询 SQL Server 版本字符串 |

## `app/services/connection_adapters/connection_factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ConnectionFactory.create_connection` | `app/services/accounts_sync/coordinator.py`, `app/services/connection_adapters/connection_test_service.py`, `app/services/database_sync/coordinator.py` | 创建数据库连接对象 |
| `ConnectionFactory.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_test_service.py` | 测试数据库连接 |
| `ConnectionFactory.get_supported_types` | 仅所在文件内部使用 | 获取支持的数据库类型列表 |
| `ConnectionFactory.is_type_supported` | `app/routes/connections.py` | 检查数据库类型是否支持 |

## `app/services/connection_adapters/connection_test_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ConnectionTestService.__init__` | 仅所在文件内部使用 | 初始化连接测试服务 |
| `ConnectionTestService.test_connection` | `app/routes/connections.py`, `app/services/connection_adapters/connection_factory.py` | 测试数据库连接 |
| `ConnectionTestService._update_last_connected` | 仅所在文件内部使用 | 更新最后连接时间 |

## `app/services/database_sync/adapters/base_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `BaseCapacityAdapter.__init__` | 仅所在文件内部使用 | 初始化容量适配器,注入系统日志记录器 |
| `BaseCapacityAdapter.fetch_inventory` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py`, `app/services/database_sync/coordinator.py` | 列出实例当前的数据库/表空间 |
| `BaseCapacityAdapter.fetch_capacity` | 同上 | 采集指定数据库的容量数据 |
| `BaseCapacityAdapter._normalize_targets` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py` | 规范化目标数据库列表 |
| `BaseCapacityAdapter._safe_to_float` | `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py` | 安全地将值转换为浮点数 |

## `app/services/database_sync/adapters/factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_capacity_adapter` | `app/services/database_sync/coordinator.py` | 根据数据库类型获取容量同步适配器实例 |

## `app/services/database_sync/adapters/mysql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `MySQLCapacityAdapter.fetch_inventory` | `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py`, `app/services/database_sync/coordinator.py` | 列出 MySQL 实例当前的数据库清单 |
| `MySQLCapacityAdapter.fetch_capacity` | 同上 | 采集指定数据库的容量数据 |
| `MySQLCapacityAdapter._assert_permission` | 仅所在文件内部使用 | 验证 MySQL 权限 |
| `MySQLCapacityAdapter._collect_tablespace_sizes` | 仅所在文件内部使用 | 采集 MySQL 表空间大小 |
| `MySQLCapacityAdapter._process_tablespace_rows` | 仅所在文件内部使用 | 解析表空间查询结果并聚合到字典 |
| `MySQLCapacityAdapter._ensure_databases_presence` | 仅所在文件内部使用 | 确保所有数据库至少有零值占位 |
| `MySQLCapacityAdapter._build_stats_from_tablespaces` | 仅所在文件内部使用 | 将表空间统计转换为标准容量数据 |
| `MySQLCapacityAdapter._normalize_database_name` | 仅所在文件内部使用 | 将 MySQL tablespace 名称中的 @XXXX 转回正常字符 |
| `MySQLCapacityAdapter._to_int` | 仅所在文件内部使用 | 安全转换表空间数值 |
| `MySQLCapacityAdapter._build_tablespace_queries` | 仅所在文件内部使用 | 构建表空间查询语句列表 |

## `app/services/database_sync/adapters/oracle_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleCapacityAdapter.fetch_inventory` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py`, `app/services/database_sync/coordinator.py` | 列出 Oracle 实例当前的表空间清单 |
| `OracleCapacityAdapter.fetch_capacity` | 同上 | 采集 Oracle 表空间容量数据 |
| `OracleCapacityAdapter._to_int` | 仅所在文件内部使用 | 安全转换容量字段 |

## `app/services/database_sync/adapters/postgresql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLCapacityAdapter.fetch_inventory` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py`, `app/services/database_sync/coordinator.py` | 列出 PostgreSQL 实例当前的数据库清单 |
| `PostgreSQLCapacityAdapter.fetch_capacity` | 同上 | 采集 PostgreSQL 数据库容量数据 |

## `app/services/database_sync/adapters/sqlserver_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerCapacityAdapter.fetch_inventory` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/coordinator.py` | 列出 SQL Server 实例当前的数据库清单 |
| `SQLServerCapacityAdapter.fetch_capacity` | 同上 | 采集 SQL Server 数据库容量数据 |

## `app/services/database_sync/coordinator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CapacitySyncCoordinator.__init__` | 仅所在文件内部使用 | 初始化容量同步协调器 |
| `CapacitySyncCoordinator.__enter__` | 仅所在文件内部使用 | 进入上下文管理器并建立连接 |
| `CapacitySyncCoordinator.__exit__` | 仅所在文件内部使用 | 退出上下文管理器并断开连接 |
| `CapacitySyncCoordinator.inventory_manager` | 仅所在文件内部使用 | 返回库存同步管理器实例 |
| `CapacitySyncCoordinator.persistence` | 仅所在文件内部使用 | 返回容量持久化服务 |
| `CapacitySyncCoordinator.connect` | 仅所在文件内部使用 | 建立数据库连接 |
| `CapacitySyncCoordinator.disconnect` | 仅所在文件内部使用 | 断开数据库连接 |
| `CapacitySyncCoordinator.synchronize_inventory` | `app/routes/databases/capacity_sync.py`, `app/services/accounts_sync/coordinator.py`, `app/tasks/capacity_collection_tasks.py` | 执行库存同步:远端拉取 → instance_databases 落库 |
| `CapacitySyncCoordinator.synchronize_database_inventory` | 仅所在文件内部使用 | 兼容旧接口名,委托到 synchronize_inventory |
| `CapacitySyncCoordinator.fetch_inventory` | `app/services/database_sync/adapters/mysql_adapter.py`, `app/services/database_sync/adapters/oracle_adapter.py`, `app/services/database_sync/adapters/postgresql_adapter.py`, `app/services/database_sync/adapters/sqlserver_adapter.py` | 获取远程数据库清单 |
| `CapacitySyncCoordinator.sync_instance_databases` | 仅所在文件内部使用 | 同步数据库清单到本地 |
| `CapacitySyncCoordinator.collect_capacity` | `app/routes/databases/capacity_sync.py`, `app/tasks/capacity_collection_tasks.py` | 采集容量数据 |
| `CapacitySyncCoordinator.save_database_stats` | 同上 | 保存数据库容量统计数据 |
| `CapacitySyncCoordinator.save_instance_stats` | `app/services/database_sync/persistence.py` | 保存实例容量统计数据 |
| `CapacitySyncCoordinator.update_instance_total_size` | `app/routes/databases/capacity_sync.py`, `app/tasks/capacity_collection_tasks.py` | 更新实例总容量 |
| `CapacitySyncCoordinator.collect_and_save` | `app/services/database_sync/database_sync_service.py` | 执行完整的库存同步 + 容量采集 + 数据持久化流程 |
| `CapacitySyncCoordinator._ensure_connection` | `app/services/accounts_sync/coordinator.py` | 确保数据库连接已建立 |

## `app/services/database_sync/database_filters.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseSyncFilterManager.__init__` | 仅所在文件内部使用 | 初始化过滤配置管理器,支持自定义配置路径 |
| `DatabaseSyncFilterManager.config_path` | 仅所在文件内部使用 | 返回当前生效的配置文件路径 |
| `DatabaseSyncFilterManager.reload` | 仅所在文件内部使用 | 从磁盘重新加载过滤配置 |
| `DatabaseSyncFilterManager._compile_pattern` | 仅所在文件内部使用 | 将 LIKE 风格的模式转换为正则表达式 |
| `DatabaseSyncFilterManager.should_exclude_database` | `app/services/database_sync/inventory_manager.py` | 判断给定实例下的数据库是否需要被过滤 |
| `DatabaseSyncFilterManager.filter_database_names` | `app/services/database_sync/coordinator.py` | 过滤数据库名称,返回保留与排除列表 |
| `DatabaseSyncFilterManager.filter_capacity_payload` | 同上 | 过滤容量采集结果,返回保留记录与被排除的库名 |

## `app/services/database_sync/database_sync_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `collect_all_instances_database_sizes` | 仅所在文件内部使用 | 采集所有活跃实例的数据库容量数据 |

## `app/services/database_sync/inventory_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `InventoryManager.__init__` | 仅所在文件内部使用 | 初始化库存管理器,注入过滤器与日志记录器 |
| `InventoryManager.synchronize` | `app/services/accounts_sync/coordinator.py`, `app/services/database_sync/coordinator.py` | 根据远端数据库列表同步 instance_databases |
| `InventoryManager._commit_inventory_changes` | 仅所在文件内部使用 | 提交库存同步事务并处理异常 |
| `InventoryManager._log_and_return_summary` | 仅所在文件内部使用 | 汇总同步结果并输出日志 |

## `app/services/database_sync/persistence.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CapacityPersistence.__init__` | 仅所在文件内部使用 | 初始化容量持久化组件,注入系统日志记录器 |
| `CapacityPersistence.save_database_stats` | `app/routes/databases/capacity_sync.py`, `app/services/database_sync/coordinator.py`, `app/tasks/capacity_collection_tasks.py` | 保存数据库容量数据 |
| `CapacityPersistence.save_instance_stats` | `app/services/database_sync/coordinator.py` | 保存实例总体容量数据 |
| `CapacityPersistence.update_instance_total_size` | `app/routes/databases/capacity_sync.py`, `app/services/database_sync/coordinator.py`, `app/tasks/capacity_collection_tasks.py` | 根据当天采集数据刷新实例汇总 |

## `app/services/database_type_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseTypeService.get_all_types` | 仅所在文件内部使用 | 获取所有数据库类型配置 |
| `DatabaseTypeService.get_active_types` | `app/routes/capacity/databases.py`, `app/routes/capacity/instances.py`, `app/routes/instances/detail.py`, `app/routes/instances/manage.py`, `app/services/form_service/classification_rule_service.py`, `app/services/form_service/instance_service.py`, ...（共7处） | 获取启用的数据库类型 |
| `DatabaseTypeService.get_type_by_name` | `app/services/connection_adapters/adapters/base.py` | 根据名称获取数据库类型 |
| `DatabaseTypeService.get_database_types_for_form` | `app/routes/common.py` | 获取用于表单的数据库类型列表 |

## `app/services/form_service/classification_rule_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ClassificationRuleFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `ClassificationRuleFormService.validate` | 同上 | 校验分类规则数据 |
| `ClassificationRuleFormService.assign` | 同上 | 将数据赋值给规则实例 |
| `ClassificationRuleFormService.after_save` | 同上 | 保存后记录日志并清除缓存 |
| `ClassificationRuleFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `ClassificationRuleFormService._validate_required_fields` | `app/utils/data_validator.py` | 校验必填字段是否全部存在 |
| `ClassificationRuleFormService._validate_option` | 仅所在文件内部使用 | 校验值是否存在于预设选项中 |
| `ClassificationRuleFormService._validate_expression_payload` | 仅所在文件内部使用 | 校验表达式格式并返回规范化结果 |
| `ClassificationRuleFormService._normalize_expression` | 仅所在文件内部使用 | 规范化规则表达式为 JSON 字符串 |
| `ClassificationRuleFormService._is_valid_option` | `app/services/form_service/classification_service.py` | 检查值是否在选项列表中 |
| `ClassificationRuleFormService._get_db_type_options` | 仅所在文件内部使用 | 负责 get db type options 相关逻辑 |
| `ClassificationRuleFormService._rule_name_exists` | 仅所在文件内部使用 | 负责 rule name exists 相关逻辑 |
| `ClassificationRuleFormService._expression_exists` | 仅所在文件内部使用 | 负责 expression exists 相关逻辑 |
| `ClassificationRuleFormService._get_classification_by_id` | 仅所在文件内部使用 | 负责 get classification by id 相关逻辑 |

## `app/services/form_service/classification_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ClassificationFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `ClassificationFormService.validate` | 同上 | 校验账户分类数据 |
| `ClassificationFormService.assign` | 同上 | 将数据赋值给分类实例 |
| `ClassificationFormService.after_save` | 同上 | 保存后记录日志 |
| `ClassificationFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `ClassificationFormService._parse_priority` | 仅所在文件内部使用 | 解析优先级值 |
| `ClassificationFormService._is_valid_option` | `app/services/form_service/classification_rule_service.py` | 检查值是否在选项列表中 |
| `ClassificationFormService._name_exists` | 仅所在文件内部使用 | 负责 name exists 相关逻辑 |

## `app/services/form_service/credential_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CredentialFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `CredentialFormService.validate` | 同上 | 校验凭据数据 |
| `CredentialFormService.assign` | 同上 | 将数据赋值给凭据实例 |
| `CredentialFormService.after_save` | 同上 | 保存后记录日志 |
| `CredentialFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `CredentialFormService._validate_payload_fields` | 仅所在文件内部使用 | 对凭据表单的核心字段执行逐项校验 |
| `CredentialFormService._normalize_payload` | `app/services/form_service/tag_service.py`, `app/services/form_service/user_service.py` | 规范化表单数据 |
| `CredentialFormService._create_instance` | `app/services/form_service/resource_service.py` | 为凭据创建空白实例 |
| `CredentialFormService._placeholder_secret` | 仅所在文件内部使用 | 生成占位密码,优先使用环境变量以避免硬编码 |
| `CredentialFormService.upsert` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/credentials.py`, `app/routes/tags/manage.py`, `app/routes/users.py`, `app/services/form_service/scheduler_job_service.py`, ...（共8处） | 执行凭据创建或更新操作 |
| `CredentialFormService._normalize_db_error` | 仅所在文件内部使用 | 将数据库异常转换为用户可读的错误信息 |

## `app/services/form_service/instance_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `InstanceFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `InstanceFormService.validate` | 同上 | 校验实例数据 |
| `InstanceFormService.assign` | 同上 | 将数据赋值给实例 |
| `InstanceFormService.after_save` | 同上 | 保存后同步标签并记录日志 |
| `InstanceFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `InstanceFormService._resolve_credential_id` | 仅所在文件内部使用 | 解析凭据 ID |
| `InstanceFormService._normalize_tag_names` | 仅所在文件内部使用 | 规范化标签名称列表 |
| `InstanceFormService._create_instance` | `app/services/form_service/resource_service.py` | 提供实例模型的占位对象,便于沿用基类保存流程 |
| `InstanceFormService._sync_tags` | 仅所在文件内部使用 | 同步实例的标签 |

## `app/services/form_service/password_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ChangePasswordFormService.sanitize` | `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `ChangePasswordFormService.validate` | 同上 | 校验密码修改数据 |
| `ChangePasswordFormService._validate_password_inputs` | 仅所在文件内部使用 | 执行密码校验逻辑并返回错误描述 |
| `ChangePasswordFormService.assign` | `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 将新密码赋值给用户实例 |
| `ChangePasswordFormService.after_save` | 同上 | 保存后记录日志 |
| `ChangePasswordFormService.upsert` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/credentials.py`, `app/routes/tags/manage.py`, `app/routes/users.py`, `app/services/form_service/credential_service.py`, ...（共9处） | 执行密码修改操作 |

## `app/services/form_service/resource_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ServiceResult.ok` | `app/services/form_service/classification_rule_service.py`, `app/services/form_service/classification_service.py`, `app/services/form_service/credential_service.py`, `app/services/form_service/instance_service.py`, `app/services/form_service/password_service.py`, `app/services/form_service/scheduler_job_service.py`, ...（共8处） | 创建成功结果 |
| `ServiceResult.fail` | 同上 | 创建失败结果 |
| `BaseResourceService.load` | 仅所在文件内部使用 | 根据主键加载资源 |
| `BaseResourceService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理原始请求数据,默认转换为普通字典 |
| `BaseResourceService.validate` | 同上 | 子类应该实现具体校验逻辑 |
| `BaseResourceService.assign` | 同上 | 将数据写入模型实例,必须由子类实现 |
| `BaseResourceService.after_save` | 同上 | 保存成功后的钩子(可选) |
| `BaseResourceService.build_context` | `app/views/mixins/resource_forms.py` | 提供模板渲染所需的额外上下文 |
| `BaseResourceService.upsert` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/credentials.py`, `app/routes/tags/manage.py`, `app/routes/users.py`, `app/services/form_service/credential_service.py`, ...（共9处） | 创建或更新资源 |
| `BaseResourceService._create_instance` | 仅所在文件内部使用 | 创建新的模型实例 |

## `app/services/form_service/scheduler_job_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SchedulerJobResource.__post_init__` | 仅所在文件内部使用 | 初始化资源 id,要求 Job 提供 id 属性 |
| `SchedulerJobFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py` | 清理表单数据 |
| `SchedulerJobFormService.load` | 仅所在文件内部使用 | 加载定时任务 |
| `SchedulerJobFormService.validate` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py` | 校验触发器配置是否合法 |
| `SchedulerJobFormService.assign` | 同上 | 将新的触发器应用到调度器 |
| `SchedulerJobFormService.after_save` | 同上 | 触发器更新后的善后处理,负责记录下一次执行时间 |
| `SchedulerJobFormService.upsert` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/credentials.py`, `app/routes/tags/manage.py`, `app/routes/users.py`, `app/services/form_service/credential_service.py`, ...（共8处） | 更新内置任务的触发器配置 |
| `SchedulerJobFormService._build_trigger` | 仅所在文件内部使用 | 根据触发器类型分发到具体构建函数 |
| `SchedulerJobFormService._build_cron_trigger` | 仅所在文件内部使用 | 基于 cron 表达式或分段字段构建触发器 |
| `SchedulerJobFormService._collect_cron_fields` | 仅所在文件内部使用 | 收集 cron 字段,支持整行表达式与分段字段混合覆盖 |
| `SchedulerJobFormService._extract_cron_base_fields` | 仅所在文件内部使用 | 从表单字段提取 cron 各字段 |
| `SchedulerJobFormService._split_cron_expression` | 仅所在文件内部使用 | 将 cron 表达式拆分为列表 |
| `SchedulerJobFormService._apply_expression_overrides` | 仅所在文件内部使用 | 用表达式分段覆盖缺失字段 |
| `SchedulerJobFormService._build_cron_kwargs` | 仅所在文件内部使用 | 过滤掉空值生成 CronTrigger 所需参数 |
| `SchedulerJobFormService._pick` | 仅所在文件内部使用 | 按顺序选择第一个有值的字段 |
| `SchedulerJobFormService._merge_parts` | 仅所在文件内部使用 | 用表达式分段填充缺失字段 |
| `SchedulerJobFormService._build_interval_trigger` | 仅所在文件内部使用 | 基于 interval 字段构建触发器 |
| `SchedulerJobFormService._build_date_trigger` | 仅所在文件内部使用 | 基于单次运行时间构建触发器 |

## `app/services/form_service/tag_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `TagFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `TagFormService.validate` | 同上 | 校验标签数据 |
| `TagFormService.assign` | 同上 | 将数据赋值给标签实例 |
| `TagFormService.after_save` | 同上 | 保存后记录日志 |
| `TagFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `TagFormService._normalize_payload` | `app/services/form_service/credential_service.py`, `app/services/form_service/user_service.py` | 规范化表单数据 |
| `TagFormService._create_instance` | `app/services/form_service/resource_service.py` | 提供标签模型的占位实例 |

## `app/services/form_service/user_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `UserFormService.sanitize` | `app/services/form_service/password_service.py`, `app/services/form_service/resource_service.py`, `app/services/form_service/scheduler_job_service.py` | 清理表单数据 |
| `UserFormService.validate` | 同上 | 校验用户数据 |
| `UserFormService.assign` | 同上 | 将数据赋值给用户实例 |
| `UserFormService.after_save` | 同上 | 保存后记录日志 |
| `UserFormService.build_context` | `app/views/mixins/resource_forms.py` | 构建模板渲染上下文 |
| `UserFormService._normalize_payload` | `app/services/form_service/credential_service.py`, `app/services/form_service/tag_service.py` | 规范化表单数据 |
| `UserFormService._is_target_state_admin` | 仅所在文件内部使用 | 判断提交后的用户是否仍为活跃管理员 |
| `UserFormService._user_query` | 仅所在文件内部使用 | 暴露 user query,便于单测注入 |
| `UserFormService._validate_password_strength` | 仅所在文件内部使用 | 验证密码强度 |
| `UserFormService._validate_username` | 仅所在文件内部使用 | 校验用户名格式 |
| `UserFormService._validate_role` | 仅所在文件内部使用 | 校验角色合法性 |
| `UserFormService._validate_password_requirement` | 仅所在文件内部使用 | 校验密码是否满足必填与强度要求 |
| `UserFormService._validate_unique_username` | 仅所在文件内部使用 | 检查用户名唯一性 |
| `UserFormService._ensure_last_admin` | 仅所在文件内部使用 | 确保至少保留一名活跃管理员 |

## `app/services/instances/batch_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_init_deletion_stats` | 仅所在文件内部使用 | 初始化删除统计字典 |
| `InstanceBatchCreationService.create_instances` | `app/routes/instances/batch.py` | 批量创建实例 |
| `InstanceBatchCreationService._ensure_payload_exists` | 仅所在文件内部使用 | 确保入参非空 |
| `InstanceBatchCreationService._find_duplicate_names` | 仅所在文件内部使用 | 定位 payload 内部的重复名称 |
| `InstanceBatchCreationService._find_existing_names` | 仅所在文件内部使用 | 查找数据库中已存在的实例名 |
| `InstanceBatchCreationService._create_valid_instances` | 仅所在文件内部使用 | 创建通过校验的实例并收集错误 |
| `InstanceBatchCreationService._build_instance_from_payload` | 仅所在文件内部使用 | 从数据字典构建实例对象 |
| `InstanceBatchDeletionService.delete_instances` | `app/routes/instances/batch.py`, `app/routes/instances/manage.py` | 批量删除实例及其关联数据 |
| `InstanceBatchDeletionService._delete_single_instance` | 仅所在文件内部使用 | 删除单个实例的所有关联数据 |

## `app/services/ledgers/database_ledger_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseLedgerService.__init__` | 仅所在文件内部使用 | 初始化服务 |
| `DatabaseLedgerService.get_ledger` | `app/routes/databases/ledgers.py` | 获取数据库台账分页数据 |
| `DatabaseLedgerService.iterate_all` | `app/routes/files.py` | 遍历所有台账记录(用于导出) |
| `DatabaseLedgerService.get_capacity_trend` | `app/routes/databases/ledgers.py` | 获取指定数据库最近 N 天的容量走势 |
| `DatabaseLedgerService._base_query` | 仅所在文件内部使用 | 构造基础查询 |
| `DatabaseLedgerService._apply_filters` | 仅所在文件内部使用 | 在基础查询上叠加筛选条件 |
| `DatabaseLedgerService._with_latest_stats` | 仅所在文件内部使用 | 为查询附加最新容量信息 |
| `DatabaseLedgerService._serialize_row` | 仅所在文件内部使用 | 将数据库记录转换为序列化结构 |
| `DatabaseLedgerService._fetch_instance_tags` | 仅所在文件内部使用 | 根据实例 ID 批量获取标签列表 |
| `DatabaseLedgerService._resolve_sync_status` | 仅所在文件内部使用 | 根据采集时间生成同步状态 |
| `DatabaseLedgerService._format_size` | `app/services/statistics/partition_statistics_service.py` | 将大小(MB)格式化为易读文本 |
| `DatabaseLedgerService._to_bytes` | 仅所在文件内部使用 | 将 MB 转换为字节 |

## `app/services/partition_management_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PartitionAction.to_dict` | 仅所在文件内部使用 | 将分区操作转换为序列化字典 |
| `PartitionManagementService.__init__` | 仅所在文件内部使用 | 初始化分区管理服务,配置不同分区表的元数据 |
| `PartitionManagementService.create_partition` | `app/routes/partition.py`, `app/tasks/partition_management_tasks.py` | 创建指定日期所在月份的分区 |
| `PartitionManagementService.create_future_partitions` | `app/tasks/partition_management_tasks.py` | 批量创建未来几个月的分区 |
| `PartitionManagementService.cleanup_old_partitions` | `app/routes/partition.py`, `app/tasks/partition_management_tasks.py` | 清理超过保留期的旧分区 |
| `PartitionManagementService._month_window` | 仅所在文件内部使用 | 计算目标日期所在月份的开始和结束日期 |
| `PartitionManagementService._get_table_partitions` | `app/services/statistics/partition_statistics_service.py` | 查询单张表的所有分区信息 |
| `PartitionManagementService._partition_exists` | 仅所在文件内部使用 | 检查指定分区表是否存在 |
| `PartitionManagementService._get_partitions_to_cleanup` | 仅所在文件内部使用 | 获取需要清理的分区名称列表 |
| `PartitionManagementService._extract_date_from_partition_name` | 仅所在文件内部使用 | 从分区名称中解析出日期字符串 |
| `PartitionManagementService._ensure_partition_identifier` | 仅所在文件内部使用 | 校验并返回安全的分区名称 |
| `PartitionManagementService._get_partition_record_count` | 仅所在文件内部使用 | 查询单个分区的记录数 |
| `PartitionManagementService._get_partition_status` | 仅所在文件内部使用 | 根据日期推断分区状态 |
| `PartitionManagementService._create_partition_indexes` | 仅所在文件内部使用 | 为分区表创建必要的索引 |
| `PartitionManagementService._format_size` | `app/services/ledgers/database_ledger_service.py`, `app/services/statistics/partition_statistics_service.py` | 将字节数格式化为可读的大小字符串 |
| `PartitionManagementService._rollback_on_error` | 仅所在文件内部使用 | 提供一个上下文管理器用于异常时自动回滚事务 |

## `app/services/statistics/account_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_is_account_locked` | 仅所在文件内部使用 | 根据数据库类型判断账户是否锁定 |
| `fetch_summary` | `app/routes/accounts/statistics.py`, `app/services/statistics/database_statistics_service.py`, `app/services/statistics/instance_statistics_service.py` | 获取账户汇总统计信息 |
| `fetch_db_type_stats` | `app/routes/accounts/statistics.py` | 按数据库类型返回账户统计信息 |
| `fetch_classification_stats` | 同上 | 按账户分类返回统计信息 |
| `fetch_classification_overview` | `app/routes/dashboard.py` | 获取分类账户概览 |
| `fetch_rule_match_stats` | `app/routes/accounts/classifications.py` | 统计每条规则所关联的账户数量 |
| `build_aggregated_statistics` | `app/routes/accounts/statistics.py`, `app/services/statistics/instance_statistics_service.py` | 组装账户统计页面的完整数据 |
| `empty_statistics` | 同上 | 构造空的统计结果 |
| `_query_classification_rows` | 仅所在文件内部使用 | 查询账户分类统计行 |
| `_query_auto_classified_count` | 仅所在文件内部使用 | 查询自动分类的账户数量 |

## `app/services/statistics/database_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_build_aggregation_filters` | 仅所在文件内部使用 | 负责 build aggregation filters 相关逻辑 |
| `_apply_base_filters` | 仅所在文件内部使用 | 负责 apply base filters 相关逻辑 |
| `fetch_summary` | `app/routes/accounts/statistics.py`, `app/services/statistics/account_statistics_service.py`, `app/services/statistics/instance_statistics_service.py` | 汇总数据库数量统计 |
| `empty_summary` | 仅所在文件内部使用 | 构造空的数据库统计结果 |
| `fetch_aggregations` | `app/routes/capacity/databases.py` | 获取数据库容量聚合数据 |
| `fetch_aggregation_summary` | 同上 | 计算数据库容量聚合汇总统计 |

## `app/services/statistics/instance_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `fetch_summary` | `app/routes/accounts/statistics.py`, `app/services/statistics/account_statistics_service.py`, `app/services/statistics/database_statistics_service.py` | 获取实例数量汇总统计 |
| `fetch_capacity_summary` | `app/routes/dashboard.py` | 汇总实例容量信息 |
| `build_aggregated_statistics` | `app/routes/accounts/statistics.py`, `app/services/statistics/account_statistics_service.py` | 构建实例统计页面的详细数据 |
| `empty_statistics` | 同上 | 构造空的实例统计结果 |

## `app/services/statistics/log_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `fetch_log_trend_data` | `app/routes/dashboard.py` | 获取最近 N 天的错误/告警日志趋势 |
| `fetch_log_level_distribution` | 同上 | 统计错误/告警日志级别分布 |

## `app/services/statistics/partition_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PartitionStatisticsService.get_partition_info` | `app/routes/partition.py`, `app/tasks/partition_management_tasks.py` | 获取所有分区的详细信息 |
| `PartitionStatisticsService.get_partition_statistics` | 同上 | 获取分区统计信息 |

## `app/services/sync_session_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SyncSessionService.__init__` | 仅所在文件内部使用 | 初始化同步会话服务,准备系统与同步日志记录器 |
| `SyncSessionService._clean_sync_details` | 仅所在文件内部使用 | 清理同步详情中的 datetime 对象,确保 JSON 可序列化 |
| `SyncSessionService.create_session` | `app/routes/capacity/aggregations.py`, `app/services/accounts_sync/accounts_sync_service.py`, `app/tasks/accounts_sync_tasks.py`, `app/tasks/capacity_aggregation_tasks.py`, `app/tasks/capacity_collection_tasks.py` | 创建同步会话 |
| `SyncSessionService.add_instance_records` | 同上 | 为会话添加实例记录 |
| `SyncSessionService.start_instance_sync` | 同上 | 开始实例同步 |
| `SyncSessionService.complete_instance_sync` | 同上 | 完成实例同步 |
| `SyncSessionService.fail_instance_sync` | 同上 | 标记实例同步失败 |
| `SyncSessionService._update_session_statistics` | 仅所在文件内部使用 | 更新会话统计信息 |
| `SyncSessionService.get_session_records` | `app/routes/history/sessions.py` | 获取会话的所有实例记录 |
| `SyncSessionService.get_session_by_id` | `app/routes/capacity/aggregations.py`, `app/routes/history/sessions.py` | 根据 ID 获取会话 |
| `SyncSessionService.get_sessions_by_type` | 仅所在文件内部使用 | 根据类型获取会话列表 |
| `SyncSessionService.get_sessions_by_category` | `app/routes/scheduler.py` | 根据分类获取会话列表 |
| `SyncSessionService.get_recent_sessions` | `app/routes/history/sessions.py` | 获取最近的会话列表 |
| `SyncSessionService.cancel_session` | 同上 | 取消会话 |

## `app/utils/cache_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CacheManager.__init__` | 仅所在文件内部使用 | 初始化缓存管理器,配置缓存实例与默认超时时间 |
| `CacheManager._generate_key` | 仅所在文件内部使用 | 生成缓存键 |
| `CacheManager.build_key` | 仅所在文件内部使用 | 对外暴露的缓存键生成方法 |
| `CacheManager.get` | 仅所在文件内部使用 | 获取缓存值 |
| `CacheManager.set` | 仅所在文件内部使用 | 设置缓存值 |
| `CacheManager.delete` | 仅所在文件内部使用 | 删除缓存值 |
| `CacheManager.clear` | 仅所在文件内部使用 | 清空所有缓存 |
| `CacheManager.get_or_set` | 仅所在文件内部使用 | 获取缓存值,如果不存在则调用函数生成并写入 |
| `invalidate_pattern` | 仅所在文件内部使用 | 根据模式批量删除缓存项 |
| `CacheManagerRegistry.init` | 仅所在文件内部使用 | 初始化缓存管理器并写入注册表 |
| `CacheManagerRegistry.get` | 仅所在文件内部使用 | 获取已注册的缓存管理器 |
| `init_cache_manager` | `app/__init__.py` | 初始化缓存管理器并返回实例 |
| `cached` | 仅所在文件内部使用 | 缓存装饰器,自动复用函数返回值 |
| `dashboard_cache` | `app/routes/dashboard.py` | 仪表板缓存装饰器,绑定统一前缀 |

## `app/utils/data_validator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DataValidator.validate_instance_data` | `app/routes/instances/detail.py`, `app/routes/instances/manage.py`, `app/services/form_service/instance_service.py` | 验证实例数据 |
| `DataValidator._validate_required_fields` | `app/services/form_service/classification_rule_service.py` | 检查必填字段是否存在 |
| `DataValidator._validate_optional_value` | 仅所在文件内部使用 | 当值存在时执行对应校验函数 |
| `DataValidator._validate_name` | 仅所在文件内部使用 | 验证实例名称并返回错误信息 |
| `DataValidator._validate_db_type` | 仅所在文件内部使用 | 验证数据库类型是否在受支持范围 |
| `DataValidator._validate_host` | 仅所在文件内部使用 | 验证主机地址格式 |
| `DataValidator._validate_port` | 仅所在文件内部使用 | 验证端口号是否处于允许范围 |
| `DataValidator._validate_database_name` | 仅所在文件内部使用 | 验证数据库名称长度与字符集合 |
| `DataValidator._validate_description` | 仅所在文件内部使用 | 验证描述字段长度 |
| `DataValidator._validate_credential_id` | 仅所在文件内部使用 | 验证凭据 ID 是否为正整数 |
| `DataValidator._is_valid_host` | 仅所在文件内部使用 | 检查主机地址是否是合法 IP 或域名 |
| `DataValidator.validate_batch_data` | `app/services/instances/batch_service.py` | 验证批量数据 |
| `DataValidator.sanitize_string` | 仅所在文件内部使用 | 清理字符串,移除潜在的危险内容 |
| `DataValidator.sanitize_input` | `app/routes/instances/detail.py`, `app/routes/instances/manage.py` | 清理输入数据 |
| `DataValidator.sanitize_form_data` | `app/routes/credentials.py`, `app/routes/tags/manage.py`, `app/services/form_service/credential_service.py`, `app/services/form_service/instance_service.py`, `app/services/form_service/password_service.py`, `app/services/form_service/tag_service.py`, ...（共7处） | 清理表单提交的数据结构 |
| `DataValidator._sanitize_form_value` | 仅所在文件内部使用 | 负责 sanitize form value 相关逻辑 |
| `DataValidator.validate_required_fields` | `app/services/form_service/credential_service.py`, `app/services/form_service/tag_service.py` | 验证必填字段是否存在 |
| `DataValidator.validate_db_type` | `app/services/form_service/credential_service.py` | 验证数据库类型是否受支持 |
| `DataValidator.set_custom_db_types` | 仅所在文件内部使用 | 在测试场景中自定义受支持的数据库类型集合 |
| `DataValidator._resolve_allowed_db_types` | 仅所在文件内部使用 | 获取允许的数据库类型集合,优先使用数据库配置 |
| `DataValidator.validate_credential_type` | `app/services/form_service/credential_service.py` | 验证凭据类型 |
| `DataValidator.validate_username` | 同上 | 验证用户名格式 |
| `DataValidator.validate_password` | `app/services/form_service/credential_service.py`, `app/services/form_service/password_service.py` | 验证密码强度 |

## `app/utils/database_batch_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseBatchManager.__init__` | 仅所在文件内部使用 | 初始化批量管理器 |
| `DatabaseBatchManager.add_operation` | 仅所在文件内部使用 | 添加数据库操作到批次队列 |
| `DatabaseBatchManager.commit_batch` | 仅所在文件内部使用 | 提交当前批次的所有操作 |
| `DatabaseBatchManager.flush_remaining` | 仅所在文件内部使用 | 提交剩余的所有操作 |
| `DatabaseBatchManager.rollback` | 仅所在文件内部使用 | 回滚所有未提交的操作 |
| `DatabaseBatchManager.get_statistics` | 仅所在文件内部使用 | 获取批量操作统计信息 |
| `DatabaseBatchManager.__enter__` | 仅所在文件内部使用 | 上下文管理器入口 |
| `DatabaseBatchManager.__exit__` | 仅所在文件内部使用 | 上下文管理器出口 |

## `app/utils/decorators.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `admin_required` | 仅所在文件内部使用 | 确保被装饰函数仅允许管理员访问的装饰器 |
| `login_required` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/scheduler.py`, `app/routes/users.py` | 要求调用者已登录的装饰器 |
| `permission_required` | 仅所在文件内部使用 | 校验指定权限(view/create/update/delete)的装饰器工厂 |
| `_extract_csrf_token` | 仅所在文件内部使用 | 从请求头、JSON 或表单中提取 CSRF 令牌 |
| `require_csrf` | `app/routes/accounts/classifications.py`, `app/routes/auth.py`, `app/routes/scheduler.py`, `app/routes/users.py` | 统一的 CSRF 校验装饰器 |
| `has_permission` | `app/constants/user_roles.py` | 检查给定用户是否具备指定权限 |
| `view_required` | `app/routes/databases/capacity_sync.py`, `app/routes/databases/ledgers.py`, `app/routes/files.py` | 负责 view required 相关逻辑 |
| `view_required` | 同上 | 负责 view required 相关逻辑 |
| `view_required` | 同上 | 校验查看权限的装饰器,可直接使用或指定自定义权限 |
| `create_required` | `app/routes/accounts/classifications.py`, `app/routes/users.py` | 负责 create required 相关逻辑 |
| `create_required` | 同上 | 负责 create required 相关逻辑 |
| `create_required` | 同上 | 校验创建权限的装饰器 |
| `update_required` | 同上 | 负责 update required 相关逻辑 |
| `update_required` | 同上 | 负责 update required 相关逻辑 |
| `update_required` | 同上 | 校验更新权限的装饰器 |
| `delete_required` | 仅所在文件内部使用 | 负责 delete required 相关逻辑 |
| `delete_required` | 仅所在文件内部使用 | 负责 delete required 相关逻辑 |
| `delete_required` | 仅所在文件内部使用 | 校验删除权限的装饰器 |
| `scheduler_view_required` | 仅所在文件内部使用 | 定时任务查看权限装饰器 |
| `scheduler_manage_required` | `app/routes/scheduler.py` | 定时任务管理权限装饰器 |

## `app/utils/logging/context_vars.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |

## `app/utils/logging/error_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ErrorContext.ensure_request` | `app/utils/structlog_config.py` | 确保请求上下文信息已填充 |
| `derive_error_metadata` | 同上 | 从异常对象推导错误元数据 |
| `build_public_context` | 同上 | 构建可对外暴露的错误上下文信息 |
| `get_error_suggestions` | 同上 | 根据错误类别获取建议的解决方案 |

## `app/utils/logging/handlers.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DebugFilter.__init__` | 仅所在文件内部使用 | 初始化 DEBUG 过滤器 |
| `DebugFilter.set_enabled` | `app/utils/structlog_config.py` | 设置是否启用 DEBUG 日志 |
| `DebugFilter.__call__` | 仅所在文件内部使用 | 处理日志事件,根据配置决定是否丢弃 DEBUG 日志 |
| `DatabaseLogHandler.__init__` | 仅所在文件内部使用 | 初始化数据库日志处理器 |
| `DatabaseLogHandler.set_worker` | `app/utils/structlog_config.py` | 设置日志队列工作线程 |
| `DatabaseLogHandler.__call__` | 仅所在文件内部使用 | 处理日志事件,将其入队等待写入数据库 |
| `_build_log_entry` | 仅所在文件内部使用 | 把 structlog 事件转换为 UnifiedLog 可用的字段字典 |
| `_extract_module_from_logger` | 仅所在文件内部使用 | 从日志记录器名称中提取模块名 |
| `_build_context` | `app/views/mixins/resource_forms.py` | 构建日志上下文信息 |

## `app/utils/logging/queue_worker.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_get_logging_dependencies` | 仅所在文件内部使用 | 惰性加载数据库句柄与日志模型以避免循环导入 |
| `LogQueueWorker.__init__` | 仅所在文件内部使用 | 初始化日志队列工作线程 |
| `LogQueueWorker.enqueue` | `app/utils/logging/handlers.py` | 将日志条目加入队列 |
| `LogQueueWorker.close` | 仅所在文件内部使用 | 显式关闭工作线程并刷新剩余日志 |
| `LogQueueWorker._run` | 仅所在文件内部使用 | 工作线程主循环,从队列中取出日志并批量写入数据库 |
| `LogQueueWorker._should_flush` | 仅所在文件内部使用 | 判断是否应该刷新缓冲区 |
| `LogQueueWorker._flush_buffer` | 仅所在文件内部使用 | 将缓冲区中的日志批量写入数据库 |
| `LogQueueWorker.__del__` | 仅所在文件内部使用 | 对象回收时仅标记关闭,避免在 GC 期间执行日志 IO |

## `app/utils/password_crypto_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PasswordManager.__init__` | 仅所在文件内部使用 | 初始化密码加密工具,准备密钥与对称加密器 |
| `PasswordManager._get_or_create_key` | 仅所在文件内部使用 | 获取或创建加密密钥 |
| `PasswordManager.encrypt_password` | `app/models/credential.py` | 加密密码 |
| `PasswordManager.decrypt_password` | 同上 | 解密密码 |
| `PasswordManager.is_encrypted` | 同上 | 检查密码是否已加密 |
| `get_password_manager` | 同上 | 获取密码管理器实例(延迟初始化) |

## `app/utils/query_filter_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `build_tag_options` | `app/services/common/filter_options_service.py` | 将标签列表转换为下拉/多选 options 结构 |
| `build_category_options` | `app/services/common/filter_options_service.py` | 将分类值列表转换为下拉 options 结构 |
| `build_classification_options` | `app/services/common/filter_options_service.py` | 将账户分类列表转换为下拉 options 结构 |
| `build_instance_select_options` | `app/services/common/filter_options_service.py` | 将实例列表转换为 instance_filter 组件 options 结构 |
| `build_database_select_options` | `app/services/common/filter_options_service.py` | 将数据库列表转换为 database_filter 组件 options 结构 |
| `build_key_value_options` | 暂未发现引用 | 将值列表转换为 value/label 同名的 options 结构 |

## `app/utils/rate_limiter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `RateLimiter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `RateLimiter._get_key` | 仅所在文件内部使用 | 生成缓存键 |
| `RateLimiter._get_memory_key` | 仅所在文件内部使用 | 生成内存键 |
| `RateLimiter.is_allowed` | 仅所在文件内部使用 | 判断给定标识符在当前窗口内是否允许访问 |
| `RateLimiter._check_cache` | 仅所在文件内部使用 | 基于缓存记录检查速率限制 |
| `RateLimiter._check_memory` | 仅所在文件内部使用 | 在无缓存情况下,使用内存列表进行限流 |
| `RateLimiterRegistry.configure` | `app/utils/structlog_config.py` | 初始化或替换当前速率限制器实例 |
| `RateLimiterRegistry.get` | 仅所在文件内部使用 | 返回当前注册的速率限制器 |
| `login_rate_limit` | `app/routes/auth.py` | 负责 login rate limit 相关逻辑 |
| `login_rate_limit` | 同上 | 负责 login rate limit 相关逻辑 |
| `login_rate_limit` | 同上 | 登录接口速率限制装饰器 |
| `password_reset_rate_limit` | 同上 | 负责 password reset rate limit 相关逻辑 |
| `password_reset_rate_limit` | 同上 | 负责 password reset rate limit 相关逻辑 |
| `password_reset_rate_limit` | 同上 | 密码重置速率限制装饰器 |
| `init_rate_limiter` | `app/__init__.py` | 初始化速率限制器 |

## `app/utils/response_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `unified_success_response` | `app/tasks/partition_management_tasks.py` | 生成统一的成功响应载荷 |
| `unified_error_response` | `app/__init__.py`, `app/tasks/partition_management_tasks.py` | 生成统一的错误响应载荷 |
| `jsonify_unified_success` | `app/routes/accounts/classifications.py`, `app/routes/accounts/ledgers.py`, `app/routes/accounts/statistics.py`, `app/routes/accounts/sync.py`, `app/routes/auth.py`, `app/routes/cache.py`, ...（共29处） | 返回 Flask Response 对象的成功响应便捷函数 |
| `jsonify_unified_error` | `app/routes/databases/ledgers.py` | 返回 Flask Response 对象的错误响应便捷函数 |
| `jsonify_unified_error_message` | `app/routes/accounts/classifications.py`, `app/routes/accounts/sync.py`, `app/routes/instances/batch.py`, `app/routes/tags/manage.py`, `app/utils/rate_limiter.py`, `app/views/scheduler_forms.py` | 基于简单消息快速生成错误响应 |

## `app/utils/route_safety.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `log_with_context` | `app/routes/accounts/ledgers.py`, `app/routes/accounts/sync.py`, `app/routes/cache.py`, `app/routes/connections.py`, `app/routes/credentials.py`, `app/routes/databases/capacity_sync.py`, ...（共10处） | 记录带有统一上下文字段的结构化日志 |
| `safe_route_call` | `app/routes/accounts/classifications.py`, `app/routes/accounts/ledgers.py`, `app/routes/accounts/statistics.py`, `app/routes/accounts/sync.py`, `app/routes/cache.py`, `app/routes/capacity/aggregations.py`, ...（共25处） | 安全执行视图逻辑,集中处理日志与异常转换 |

## `app/utils/safe_query_builder.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SafeQueryBuilder.__init__` | 仅所在文件内部使用 | 初始化查询构建器 |
| `SafeQueryBuilder.add_condition` | `app/services/accounts_sync/adapters/mysql_adapter.py` | 添加查询条件 |
| `SafeQueryBuilder._generate_placeholder` | 仅所在文件内部使用 | 生成数据库特定的占位符 |
| `SafeQueryBuilder.add_in_condition` | 仅所在文件内部使用 | 添加 IN 条件 |
| `SafeQueryBuilder.add_not_in_condition` | 仅所在文件内部使用 | 添加 NOT IN 条件 |
| `SafeQueryBuilder.add_like_condition` | 仅所在文件内部使用 | 添加 LIKE 条件 |
| `SafeQueryBuilder.add_not_like_condition` | 仅所在文件内部使用 | 添加 NOT LIKE 条件 |
| `SafeQueryBuilder.build_where_clause` | `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py` | 构建 WHERE 子句 |
| `SafeQueryBuilder.add_database_specific_condition` | 同上 | 添加数据库特定的过滤条件 |
| `SafeQueryBuilder.reset` | 仅所在文件内部使用 | 重置构建器 |
| `build_safe_filter_conditions` | `app/services/accounts_sync/accounts_sync_filters.py` | 构建安全的过滤条件 - 统一入口函数 |

## `app/utils/sensitive_data.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `scrub_sensitive_fields` | `app/routes/users.py` | 脱敏敏感字段,返回新的字典副本 |

## `app/utils/sqlserver_connection_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerConnectionDiagnostics.__init__` | 仅所在文件内部使用 | 初始化 SQL Server 连接诊断工具 |
| `SQLServerConnectionDiagnostics.diagnose_connection_error` | `app/services/connection_adapters/adapters/sqlserver_adapter.py` | 诊断 SQL Server 连接错误 |
| `SQLServerConnectionDiagnostics._check_network_connectivity` | 仅所在文件内部使用 | 检查网络连通性 |
| `SQLServerConnectionDiagnostics._check_port_accessibility` | 仅所在文件内部使用 | 检查端口可访问性 |
| `SQLServerConnectionDiagnostics.get_connection_string_suggestions` | 仅所在文件内部使用 | 获取连接字符串建议 |
| `SQLServerConnectionDiagnostics.analyze_error_patterns` | 仅所在文件内部使用 | 分析错误模式 |

## `app/utils/structlog_config.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `StructlogConfig.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `StructlogConfig.configure` | `app/utils/rate_limiter.py` | 初始化 structlog 处理器(幂等) |
| `StructlogConfig._attach_app` | 仅所在文件内部使用 | 绑定位于 Flask 应用上的队列配置 |
| `StructlogConfig._add_request_context` | 仅所在文件内部使用 | 向事件字典写入请求上下文 |
| `StructlogConfig._add_user_context` | 仅所在文件内部使用 | 附加当前用户上下文 |
| `StructlogConfig._add_global_context` | 仅所在文件内部使用 | 附加环境、版本等全局上下文 |
| `StructlogConfig._get_console_renderer` | 仅所在文件内部使用 | 根据终端能力返回渲染器 |
| `StructlogConfig.shutdown` | `app/scheduler.py` | 关闭日志系统 |
| `get_logger` | `app/services/cache_service.py`, `app/utils/database_batch_manager.py`, `app/utils/logging/handlers.py`, `app/utils/route_safety.py`, `app/utils/time_utils.py` | 获取结构化日志记录器 |
| `configure_structlog` | `app/__init__.py` | 配置 structlog 并注册 Flask 钩子 |
| `should_log_debug` | `app/utils/decorators.py` | 检查是否应该记录调试日志 |
| `log_info` | `app/routes/accounts/classifications.py`, `app/routes/accounts/sync.py`, `app/routes/cache.py`, `app/routes/capacity/aggregations.py`, `app/routes/common.py`, `app/routes/connections.py`, ...（共37处） | 记录信息级别日志 |
| `log_warning` | `app/routes/accounts/sync.py`, `app/routes/connections.py`, `app/routes/databases/capacity_sync.py`, `app/routes/partition.py`, `app/routes/scheduler.py`, `app/services/aggregation/database_aggregation_runner.py`, ...（共9处） | 记录警告级别日志 |
| `log_error` | `app/services/account_classification/auto_classify_service.py`, `app/services/account_classification/cache.py`, `app/services/account_classification/classifiers/mysql_classifier.py`, `app/services/account_classification/classifiers/oracle_classifier.py`, `app/services/account_classification/classifiers/postgresql_classifier.py`, `app/services/account_classification/classifiers/sqlserver_classifier.py`, ...（共23处） | 记录错误级别日志 |
| `log_critical` | 仅所在文件内部使用 | 记录严重错误级别日志 |
| `log_debug` | `app/services/aggregation/database_aggregation_runner.py`, `app/services/aggregation/instance_aggregation_runner.py` | 记录调试级别日志 |
| `get_system_logger` | `app/__init__.py`, `app/models/credential.py`, `app/scheduler.py`, `app/services/accounts_sync/accounts_sync_filters.py`, `app/services/database_sync/adapters/base_adapter.py`, `app/services/database_sync/coordinator.py`, ...（共16处） | 返回系统级 logger |
| `get_api_logger` | 仅所在文件内部使用 | 返回 API 级 logger |
| `get_auth_logger` | `app/routes/auth.py` | 返回认证模块 logger |
| `get_db_logger` | `app/services/connection_adapters/adapters/base.py` | 返回数据库操作 logger |
| `get_sync_logger` | `app/services/accounts_sync/accounts_sync_service.py`, `app/services/accounts_sync/adapters/mysql_adapter.py`, `app/services/accounts_sync/adapters/oracle_adapter.py`, `app/services/accounts_sync/adapters/postgresql_adapter.py`, `app/services/accounts_sync/adapters/sqlserver_adapter.py`, `app/services/accounts_sync/coordinator.py`, ...（共14处） | 返回同步任务 logger |
| `get_task_logger` | `app/tasks/log_cleanup_tasks.py` | 返回后台任务 logger |
| `enhanced_error_handler` | `app/utils/response_utils.py` | 增强的错误处理器 |
| `_log_enhanced_error` | 仅所在文件内部使用 | 根据严重度输出增强错误 |
| `error_handler` | 仅所在文件内部使用 | Flask 视图装饰器,统一捕获异常并输出结构化日志 |

## `app/utils/time_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `TimeUtils.now` | 仅所在文件内部使用 | 获取当前 UTC 时间 |
| `TimeUtils.now_china` | `app/__init__.py`, `app/routes/capacity/instances.py`, `app/routes/dashboard.py`, `app/routes/health.py`, `app/routes/partition.py`, `app/services/aggregation/calculator.py`, ...（共15处） | 获取当前中国时间 |
| `TimeUtils.to_china` | `app/models/unified_log.py`, `app/routes/capacity/aggregations.py`, `app/routes/capacity/databases.py`, `app/routes/history/logs.py`, `app/routes/instances/detail.py`, `app/routes/partition.py` | 将时间转换为中国时区 |
| `TimeUtils.to_utc` | `app/routes/dashboard.py`, `app/services/form_service/scheduler_job_service.py`, `app/services/statistics/log_statistics_service.py`, `app/utils/logging/handlers.py` | 将时间转换为 UTC 时区 |
| `TimeUtils.format_china_time` | 仅所在文件内部使用 | 格式化中国时间显示 |
| `TimeUtils.format_utc_time` | 仅所在文件内部使用 | 格式化 UTC 时间显示 |
| `TimeUtils.get_relative_time` | `app/__init__.py` | 获取相对时间描述 |
| `TimeUtils.is_today` | 同上 | 判断给定时间是否属于今天(以中国时区为准) |
| `TimeUtils.get_time_range` | 仅所在文件内部使用 | 获取指定小时跨度的起止时间 |
| `TimeUtils.to_json_serializable` | 仅所在文件内部使用 | 转换时间对象为 JSON 可序列化的 ISO 字符串 |

## `app/utils/version_parser.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseVersionParser.parse_version` | `app/services/connection_adapters/connection_test_service.py` | 解析数据库版本信息 |
| `DatabaseVersionParser._extract_main_version` | 仅所在文件内部使用 | 提取主版本号 |
| `DatabaseVersionParser.format_version_display` | `app/services/connection_adapters/connection_test_service.py` | 格式化版本显示 |
