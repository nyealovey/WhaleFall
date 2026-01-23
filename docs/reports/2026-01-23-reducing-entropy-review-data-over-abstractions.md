> **Status**: Draft
> **Owner**: Codex（reducing-entropy）
> **Created**: 2026-01-23
> **Updated**: 2026-01-23
> **Mindset**: Data-Over-Abstractions（数据胜过抽象）
> **Success Metric**: 以“合并/删除后仓库总代码量净减少”为唯一成功指标（不是“改动更小”）
> **Scope**: `/Users/apple/Github/WhaleFall`（静态审查；以 `app/**` 为主，辅以 `scripts/**`、构建入口文件）

# reducing-entropy 审查报告：Data-Over-Abstractions (2026-01-23)

## 1. 核心原则（本报告的判定标准）

“更多函数作用于同一份通用数据结构”通常比“更少函数 + 更多自定义结构/DTO/层”更能减少长期代码量。

优先级排序（从“更省代码”到“更耗代码”）：

1) `dict/list/set` + 少量通用函数（可组合、可复用）
2) 业务 schema 只做“校验 + canonicalize”，输出 `dict`（稳定形状）
3) 轻量 repository（只有在真的能减少重复 Query 组装时才保留）
4) 大量 DTO/types/dataclass/manager/registry（通常是熵增来源）

## 2. 仓库体量快照（证据）

> 仅用于定位“熵主要集中在哪里”，不是精确 KPI。

- `app/**/*.py`：469 个文件，约 66,429 行
- `app/services/**/*.py`：约 26,908 行（主要熵源）
- `app/api/v1/**/*.py`：约 9,568 行（API 模型/封套/namespace）
- `app/repositories/**/*.py`：约 5,063 行
- `app/schemas/**/*.py`：约 4,923 行
- `app/utils/**/*.py`：约 4,614 行
- `app/models/**/*.py`：约 3,640 行

结论：真正的“减熵”要么发生在 `services/`、要么发生在 `api/v1/namespaces/`（其次是 `repositories/` / `schemas/` 的重复与薄封装）。

## 3. P0 建议（高确定性净删，优先做）

### 3.1 删除“薄读服务层” + 删除对应 DTO/types（让数据直接以 dict 流动）

现象：大量读路径 service 只做“repo 调用 + 轻量拼装/转 DTO”，形成重复的“Query -> Filters -> DTO -> Response”翻译链。

删除/合并建议（优先从最薄、最稳定的模块开始）：

- 凭据读/列/options：
  - `app/services/credentials/credential_detail_read_service.py:1`
  - `app/services/credentials/credential_options_service.py:1`
  - `app/services/credentials/credentials_list_service.py:1`
- 用户读/列/stats：
  - `app/services/users/user_detail_read_service.py:1`
  - `app/services/users/users_list_service.py:1`
  - `app/services/users/users_stats_service.py:1`
- 实例 list/statistics：
  - `app/services/instances/instance_list_service.py:1`
  - `app/services/instances/instance_statistics_read_service.py:1`

并同步删掉“只为这些 service 存在的 DTO/types”（把返回结构改为 `dict`，或在 API 层直接组装）：

- `app/core/types/credentials.py:1`
- `app/core/types/users.py:1`
- `app/core/types/instances.py:1`
- `app/core/types/instance_statistics.py:1`
- `app/core/types/listing.py:1`

预期净减少：

- 仅上述 service + types 合计约 **924 行**（`wc -l` 口径；不含引用点替换产生的少量增量）

风险：

- 契约测试可能依赖字段默认值/排序；错误抛出位置从 service 移到 API/route。

验证/测试：

- API 契约：`tests/unit/routes/test_api_v1_credentials_contract.py:1`、`tests/unit/routes/test_api_v1_users_contract.py:1`、`tests/unit/routes/test_api_v1_instances_contract.py:1`、`tests/unit/routes/test_api_v1_instances_statistics_contract.py:1`

### 3.2 删除“薄 Repository”（一条查询一个类：不值）

典型薄封装示例：

- `app/repositories/health_repository.py:1`（只执行 `SELECT 1`）
- `app/repositories/database_type_repository.py:1`（几乎是 Model 静态方法转发）

删除/合并建议：

- 直接在调用点用 `db.session` 或 `Model.query`，删除上述 repo 文件与类。

预期净减少：

- 先做最薄的 2 个 repo，至少 **50 行级别**；若扩大到同类 repo，可达 **数百行**。

风险：

- 测试若依赖 repository 作为注入点，需要改为注入函数或注入 session。

验证：

- 健康/类型配置相关 API 契约：`tests/unit/routes/test_api_v1_health_ping_contract.py:1`

### 3.3 删除“只被单一模块使用的 internal contract types 层”

证据：`build_internal_contract_ok/error` 仅被 `permission_snapshot_v4` 使用（全库搜索无其他引用）。

删除/合并建议：

- 删除 `app/core/types/internal_contracts.py:1`（88 行）
- 将其返回结构与构造函数内联到 `app/schemas/internal_contracts/permission_snapshot_v4.py:1`
- 从 `app/core/types/__init__.py:1` 移除相关导出，减少入口聚合污染

预期净减少：**~88 行 + 减少 import/export 噪音**

风险：

- 返回结构字段必须保持一致（否则影响调用链与测试）。

验证/测试：

- `tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py:1`

### 3.4 合并 external_contracts 里重复的 coercion 工具函数（数据清洗应是通用操作）

证据：以下文件重复实现 `_as_dict/_as_str_list/_as_dict_of_str_list`：

- `app/schemas/external_contracts/mysql_account.py:19`
- `app/schemas/external_contracts/postgresql_account.py:19`
- `app/schemas/external_contracts/sqlserver_account.py:19`
- `app/schemas/external_contracts/oracle_account.py:19`

删除/合并建议：

- 把这些 coercion 函数集中到一个共享文件（例如 `app/schemas/_coercions.py` 或并入 `app/schemas/base.py`），其余文件只保留 schema 定义。

预期净减少：

- 取决于合并方式；通常是“删 4 份重复 + 新增 1 份共享”，净减少 **几十行到百行**（并显著降低行为漂移）。

风险：

- 某些 DB 的“兼容规则”可能存在细微差异，合并前需先对齐差异。

验证/测试：

- 以 accounts-sync 的契约测试覆盖为主：`tests/unit/routes/test_api_v1_accounts_sync_contract.py:1`

## 4. P1 建议（需要确认/有一定回归风险，但潜在收益大）

### 4.1 “缓存体系”存在两套概念（CacheService vs CacheManager），可收敛为一套

证据：

- `app/services/cache_service.py:1`（对外提供 CacheService）
- `app/utils/cache_utils.py:1`（CacheManager + CacheManagerRegistry + decorators）
- `app/services/cache/cache_actions_service.py:1`（再包一层动作编排）

删除/合并建议（以净删为目标的最小收敛）：

- 选定“唯一 cache 抽象”：要么只保留 `CacheService`，要么只保留 `CacheManager`（二选一）
- 删除另一个体系与其 registry/薄编排层：
  - `app/utils/cache_utils.py:1`（若决定保留 CacheService）
  - 或删除 `app/services/cache_service.py:1` + `app/services/cache/cache_actions_service.py:1`（若决定保留 CacheManager）

风险：

- cache 初始化、全局单例、异常口径一致性；需要配合 API 行为与日志字段回归。

验证/测试：

- `tests/unit/routes/test_api_v1_cache_contract.py:1`

### 4.2 合并“分页/filters DTO”到 schema（避免多级翻译链）

建议方向：

- schema 层输出 `dict`（稳定形状），repository 直接消费 `dict`，API 直接消费 `dict` 返回（减少中间类型）。

风险与验证：

- 以现有 contract tests 为准，确保返回结构不变。

## 5. 建议执行顺序（按“确定性/收益”排序）

1) 删除 `app/static/js/modules/stores/logs_store.js:1`（全库无引用；见另一报告，但属于纯净删，应该先做）
2) 删除薄 read services（credentials/users/instances）+ 删除对应 types DTO
3) 删除薄 repo（health/database_type 等）
4) 清理 internal_contract types 层
5) 合并 external_contract coercions

## 6. 附录：建议的“减熵验收方式”

建议每做一组删减就做一次“净减少”验收：

- 代码量：`git diff --stat`（以净删为主）
- 契约：`uv run pytest -m unit`（至少覆盖 routes/schemas 契约测试集）
- 手工：打开 1~2 个核心页面（实例列表、账户台账、凭据管理）确认无明显断链

