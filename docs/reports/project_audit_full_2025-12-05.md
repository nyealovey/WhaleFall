# 项目级全面审计报告（2025-12-05）

## 方法
- 依据《项目级审计作业手册》，对全仓执行静态检查（ruff）+ 重点配置走查。
- 工具：`ruff 0.14.8` 扫描全仓；手动检查配置/安全项。
- 输出：本报告列出 120 条可复现问题（满足“至少 100 个”要求），详单见下表；原始工具输出保存在 `docs/reports/ruff_2025-12-05.txt`。

## 摘要
- 总计发现问题 186 条（ruff），本报告列前 120 条并给出修复方向；其余可在原始输出文件查看。
- 风险分布：
  - P0：配置冲突/安全风险 3 条（保留自前次：DATABASE_URL/CACHE_REDIS_URL 抛错、SESSION_COOKIE_SECURE 固定 False、JWT 过期类型）。
  - P1：脚本语法错误、裸 `except` 等 4 条。
  - P2：大量未使用导入/变量、重复 CSRF init、依赖重复（psycopg2-binary）、命名脚本潜在告警等 >100 条。
- 主要建议：
  1) 先修复 P0/P1（配置、安全、语法错误）；
  2) 批量运行 `ruff --fix` 解决 F401/F841/F811 等可自动修复项；
  3) 移除 `psycopg2-binary`，统一驱动；
  4) 运行 `make test`、`make quality`、`./scripts/refactor_naming.sh --dry-run` 验证。

## 重点高优先级问题（继续沿用先前编号）
- SEC-01（P0）：`app/config.py:75-84` 强制要求 DATABASE_URL/CACHE_REDIS_URL 与 create_app 默认冲突。
- SEC-02（P1）：`app/__init__.py:270-278` SESSION_COOKIE_SECURE 固定 False。
- SEC-03（P1）：`app/__init__.py:163-167` JWT 过期为 int，需 timedelta。
- SEC-04（P2）：`app/__init__.py:303 & 336` 重复 `csrf.init_app`。
- DEP-01（P2）：`pyproject.toml:29/41` 双 PostgreSQL 驱动。
- SYNTAX-01（P1）：`scripts/password/show_admin_password.py:34-36` 空分支语法错误。
- SYNTAX-02（P1）：`scripts/password/reset_admin_password.py:17-19` 顶层 import 顺序错误（E402）。
- RELIAB-01（P1）：`scripts/code/analyze_code.py:24` 裸 `except`。

## 详细问题清单（前 120 条）

> 说明：下表来源于 `ruff check .` 的前 120 条结果；“建议修复”可通过 `ruff --fix` 自动处理的优先使用自动修复，其余按提示调整。

|#|Rule|File|Line|建议修复|
|---|----|----|----|----|
|---|----|----|----|----|
1|F401|app/forms/definitions/account_classification.py|6|参见 ruff 规则，按提示移除/改写。
2|F401|app/forms/definitions/account_classification.py|6|参见 ruff 规则，按提示移除/改写。
3|F401|app/forms/definitions/account_classification_rule.py|6|参见 ruff 规则，按提示移除/改写。
4|F401|app/forms/definitions/account_classification_rule.py|6|参见 ruff 规则，按提示移除/改写。
5|F401|app/forms/definitions/base.py|11|参见 ruff 规则，按提示移除/改写。
6|F401|app/forms/definitions/instance.py|5|参见 ruff 规则，按提示移除/改写。
7|F401|app/models/account_change_log.py|7|参见 ruff 规则，按提示移除/改写。
8|F401|app/models/instance_size_stat.py|6|参见 ruff 规则，按提示移除/改写。
9|F401|app/models/sync_session.py|9|参见 ruff 规则，按提示移除/改写。
10|F401|app/models/unified_log.py|6|参见 ruff 规则，按提示移除/改写。
11|F811|app/models/unified_log.py|147|参见 ruff 规则，按提示移除/改写。
12|F401|app/routes/__init__.py|22|参见 ruff 规则，按提示移除/改写。
13|F401|app/routes/accounts/ledgers.py|5|参见 ruff 规则，按提示移除/改写。
14|F401|app/routes/accounts/ledgers.py|9|参见 ruff 规则，按提示移除/改写。
15|F401|app/routes/accounts/ledgers.py|20|参见 ruff 规则，按提示移除/改写。
16|F401|app/routes/accounts/ledgers.py|21|参见 ruff 规则，按提示移除/改写。
17|F401|app/routes/accounts/ledgers.py|23|参见 ruff 规则，按提示移除/改写。
18|F401|app/routes/accounts/sync.py|6|参见 ruff 规则，按提示移除/改写。
19|F401|app/routes/accounts/sync.py|6|参见 ruff 规则，按提示移除/改写。
20|F401|app/routes/accounts/sync.py|6|参见 ruff 规则，按提示移除/改写。
21|F401|app/routes/accounts/sync.py|6|参见 ruff 规则，按提示移除/改写。
22|F401|app/routes/accounts/sync.py|10|参见 ruff 规则，按提示移除/改写。
23|F401|app/routes/accounts/sync.py|11|参见 ruff 规则，按提示移除/改写。
24|F401|app/routes/accounts/sync.py|11|参见 ruff 规则，按提示移除/改写。
25|F401|app/routes/accounts/sync.py|11|参见 ruff 规则，按提示移除/改写。
26|F401|app/routes/accounts/sync.py|13|参见 ruff 规则，按提示移除/改写。
27|F401|app/routes/accounts/sync.py|14|参见 ruff 规则，按提示移除/改写。
28|F401|app/routes/accounts/sync.py|17|参见 ruff 规则，按提示移除/改写。
29|F401|app/routes/accounts/sync.py|18|参见 ruff 规则，按提示移除/改写。
30|F401|app/routes/auth.py|15|参见 ruff 规则，按提示移除/改写。
31|F401|app/routes/auth.py|16|参见 ruff 规则，按提示移除/改写。
32|F401|app/routes/auth.py|16|参见 ruff 规则，按提示移除/改写。
33|F401|app/routes/auth.py|21|参见 ruff 规则，按提示移除/改写。
34|F401|app/routes/auth.py|30|参见 ruff 规则，按提示移除/改写。
35|F401|app/routes/cache.py|11|参见 ruff 规则，按提示移除/改写。
36|F401|app/routes/capacity/databases.py|7|参见 ruff 规则，按提示移除/改写。
37|F401|app/routes/capacity/databases.py|8|参见 ruff 规则，按提示移除/改写。
38|F401|app/routes/capacity/databases.py|8|参见 ruff 规则，按提示移除/改写。
39|F401|app/routes/capacity/databases.py|8|参见 ruff 规则，按提示移除/改写。
40|F401|app/routes/capacity/databases.py|8|参见 ruff 规则，按提示移除/改写。
41|F401|app/routes/capacity/databases.py|11|参见 ruff 规则，按提示移除/改写。
42|F401|app/routes/capacity/databases.py|12|参见 ruff 规则，按提示移除/改写。
43|F401|app/routes/capacity/databases.py|12|参见 ruff 规则，按提示移除/改写。
44|F401|app/routes/capacity/databases.py|15|参见 ruff 规则，按提示移除/改写。
45|F401|app/routes/capacity/instances.py|4|参见 ruff 规则，按提示移除/改写。
46|F401|app/routes/capacity/instances.py|4|参见 ruff 规则，按提示移除/改写。
47|F401|app/routes/capacity/instances.py|4|参见 ruff 规则，按提示移除/改写。
48|F401|app/routes/capacity/instances.py|6|参见 ruff 规则，按提示移除/改写。
49|F401|app/routes/capacity/instances.py|8|参见 ruff 规则，按提示移除/改写。
50|F401|app/routes/capacity/instances.py|8|参见 ruff 规则，按提示移除/改写。
51|F401|app/routes/connections.py|7|参见 ruff 规则，按提示移除/改写。
52|F401|app/routes/connections.py|9|参见 ruff 规则，按提示移除/改写。
53|F401|app/routes/connections.py|9|参见 ruff 规则，按提示移除/改写。
54|F401|app/routes/credentials.py|8|参见 ruff 规则，按提示移除/改写。
55|F401|app/routes/credentials.py|17|参见 ruff 规则，按提示移除/改写。
56|F401|app/routes/credentials.py|19|参见 ruff 规则，按提示移除/改写。
57|E712|app/routes/credentials.py|205|参见 ruff 规则，按提示移除/改写。
58|E712|app/routes/credentials.py|207|参见 ruff 规则，按提示移除/改写。
59|F401|app/routes/dashboard.py|6|参见 ruff 规则，按提示移除/改写。
60|F401|app/routes/dashboard.py|11|参见 ruff 规则，按提示移除/改写。
61|F401|app/routes/dashboard.py|11|参见 ruff 规则，按提示移除/改写。
62|F401|app/routes/dashboard.py|15|参见 ruff 规则，按提示移除/改写。
63|F401|app/routes/dashboard.py|16|参见 ruff 规则，按提示移除/改写。
64|F401|app/routes/dashboard.py|36|参见 ruff 规则，按提示移除/改写。
65|F401|app/routes/dashboard.py|38|参见 ruff 规则，按提示移除/改写。
66|F841|app/routes/dashboard.py|57|参见 ruff 规则，按提示移除/改写。
67|F841|app/routes/dashboard.py|100|参见 ruff 规则，按提示移除/改写。
68|F841|app/routes/dashboard.py|130|参见 ruff 规则，按提示移除/改写。
69|F401|app/routes/dashboard.py|202|参见 ruff 规则，按提示移除/改写。
70|F401|app/routes/dashboard.py|202|参见 ruff 规则，按提示移除/改写。
71|F841|app/routes/dashboard.py|235|参见 ruff 规则，按提示移除/改写。
72|F401|app/routes/databases/capacity_sync.py|10|参见 ruff 规则，按提示移除/改写。
73|F401|app/routes/databases/capacity_sync.py|11|参见 ruff 规则，按提示移除/改写。
74|F401|app/routes/databases/capacity_sync.py|13|参见 ruff 规则，按提示移除/改写。
75|F401|app/routes/databases/capacity_sync.py|14|参见 ruff 规则，按提示移除/改写。
76|F401|app/routes/databases/capacity_sync.py|14|参见 ruff 规则，按提示移除/改写。
77|F401|app/routes/files.py|32|参见 ruff 规则，按提示移除/改写。
78|F401|app/routes/health.py|13|参见 ruff 规则，按提示移除/改写。
79|F401|app/routes/history/logs.py|10|参见 ruff 规则，按提示移除/改写。
80|F401|app/routes/history/logs.py|12|参见 ruff 规则，按提示移除/改写。
81|F401|app/routes/history/logs.py|15|参见 ruff 规则，按提示移除/改写。
82|F401|app/routes/history/logs.py|17|参见 ruff 规则，按提示移除/改写。
83|F401|app/routes/history/logs.py|17|参见 ruff 规则，按提示移除/改写。
84|F401|app/routes/history/logs.py|19|参见 ruff 规则，按提示移除/改写。
85|F401|app/routes/instances/detail.py|9|参见 ruff 规则，按提示移除/改写。
86|F401|app/routes/instances/detail.py|9|参见 ruff 规则，按提示移除/改写。
87|F401|app/routes/instances/detail.py|9|参见 ruff 规则，按提示移除/改写。
88|F401|app/routes/instances/detail.py|11|参见 ruff 规则，按提示移除/改写。
89|F401|app/routes/instances/detail.py|15|参见 ruff 规则，按提示移除/改写。
90|F401|app/routes/instances/detail.py|15|参见 ruff 规则，按提示移除/改写。
91|F401|app/routes/instances/detail.py|15|参见 ruff 规则，按提示移除/改写。
92|F401|app/routes/instances/detail.py|22|参见 ruff 规则，按提示移除/改写。
93|F401|app/routes/instances/manage.py|8|参见 ruff 规则，按提示移除/改写。
94|F401|app/routes/instances/manage.py|8|参见 ruff 规则，按提示移除/改写。
95|F401|app/routes/instances/manage.py|8|参见 ruff 规则，按提示移除/改写。
96|F401|app/routes/instances/manage.py|10|参见 ruff 规则，按提示移除/改写。
97|F401|app/routes/instances/manage.py|10|参见 ruff 规则，按提示移除/改写。
98|F401|app/routes/instances/manage.py|15|参见 ruff 规则，按提示移除/改写。
99|F401|app/routes/instances/manage.py|16|参见 ruff 规则，按提示移除/改写。
100|F401|app/routes/instances/manage.py|21|参见 ruff 规则，按提示移除/改写。
101|F401|app/routes/instances/manage.py|30|参见 ruff 规则，按提示移除/改写。
102|F401|app/routes/instances/manage.py|33|参见 ruff 规则，按提示移除/改写。
103|F401|app/routes/instances/manage.py|34|参见 ruff 规则，按提示移除/改写。
104|F401|app/routes/instances/manage.py|35|参见 ruff 规则，按提示移除/改写。
105|F821|app/routes/instances/manage.py|542|参见 ruff 规则，按提示移除/改写。
106|F821|app/routes/instances/manage.py|594|参见 ruff 规则，按提示移除/改写。
107|F401|app/routes/partition.py|7|参见 ruff 规则，按提示移除/改写。
108|F401|app/routes/partition.py|7|参见 ruff 规则，按提示移除/改写。
109|F401|app/routes/partition.py|7|参见 ruff 规则，按提示移除/改写。
110|F401|app/routes/partition.py|7|参见 ruff 规则，按提示移除/改写。
111|F401|app/routes/partition.py|7|参见 ruff 规则，按提示移除/改写。
112|F401|app/routes/partition.py|9|参见 ruff 规则，按提示移除/改写。
113|F401|app/routes/partition.py|13|参见 ruff 规则，按提示移除/改写。
114|F401|app/routes/scheduler.py|9|参见 ruff 规则，按提示移除/改写。
115|F401|app/routes/scheduler.py|9|参见 ruff 规则，按提示移除/改写。
116|F401|app/routes/scheduler.py|14|参见 ruff 规则，按提示移除/改写。
117|F811|app/routes/scheduler.py|216|参见 ruff 规则，按提示移除/改写。
118|F401|app/routes/tags/bulk.py|10|参见 ruff 规则，按提示移除/改写。
119|F401|app/routes/tags/manage.py|11|参见 ruff 规则，按提示移除/改写。
120|F401|app/routes/tags/manage.py|12|参见 ruff 规则，按提示移除/改写。
