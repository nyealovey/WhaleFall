> 注意：本文件已被《统一改造执行计划》整合与编排。执行请以 `docs/refactoring/unified_refactoring_plan.md` 为准；本文件保留作专题说明与背景参考。

# 时间与时区 & 日志枚举统一整改方案（配套版）

本文档为《日志与错误处理统一方案（无过渡兼容，强制版）》的配套改造，聚焦于：
- 模型时间字段的时区一致性与存储策略；
- 日志级别枚举 `LogLevel` 的统一来源与引用；
- 时间序列化与展示一致化（后端统一、前端易解析）。

目标：确保日志与错误处理链路中的时间与级别信息端到端一致、无歧义、无偏移。

---

## 背景与目标
- 统一时间字段的时区语义：按 UTC 存储，展示层按需转换（中国时区）。
- 统一日志级别枚举来源：仅使用 `app/constants/system_constants.py` 中的 `LogLevel`。
- 消除重复定义与不一致引用，减少维护成本与错误风险。

## 现状综述（简要）
- 时间列：多数模型使用 `db.DateTime` 或 `db.DateTime(timezone=True)`，默认值与更新值来自 `app.utils.time_utils.now`。
  - `app/models/unified_log.py` 明确使用 `DateTime(timezone=True)`，并在 `create_log_entry` 中补齐时区信息（默认 UTC）。
  - `app/models/global_param.py` 的 `created_at` 与 `updated_at` 近期发现不含 `timezone=True`（已列为统一整改对象）。
- 时间工具：`app/utils/time_utils.py` 提供 `now()`（UTC、带时区），`to_utc()`、`to_china()`、`format_*`，兼容 `"Z"` 字符串。
- 日志级别：`LogLevel` 重复定义于 `constants/system_constants.py`、`models/unified_log.py`、`utils/logging_config.py`。

## 问题与风险
- 时间列混用 `timezone=True` 与非时区列，会导致序列化、显示或范围查询偏移。
- `LogLevel` 多处定义可能造成枚举比较失败或值不一致，影响筛选与统计。
- 展示与序列化不统一（`isoformat()` 与前端解析差异）可能导致 UI 时间显示错位。

## 统一策略与原则
### 时间字段
- 模型层：所有时间列统一为 `db.DateTime(timezone=True)`；默认值与更新值统一使用 `app.utils.time_utils.now`（UTC）。
- 存储层：一律按 UTC 入库；不在数据库中做隐式本地化。
- 展示层：统一使用 `to_china()/format_china_time()` 显示中国时区；API 序列化统一使用 `datetime.isoformat()`。

### 日志级别枚举
- 唯一来源：`from app.constants import LogLevel`。
- 模型绑定：`SQLEnum(LogLevel, name="log_level")`；移除本地重复枚举。
- 所有引用（路由、工具、日志处理器）统一从 `app.constants` 导入枚举。

即刻修复清单（精准到文件）
- `app/models/global_param.py`：将 `created_at/updated_at` 改为 `db.DateTime(timezone=True)`（默认值与 `onupdate` 使用 `now`）。
- `app/models/unified_log.py`：移除本地 `LogLevel` 枚举；改为 `from app.constants import LogLevel` 并保持 `SQLEnum(LogLevel, name="log_level")`。
- `app/utils/logging_config.py`：移除本地 `LogLevel/LogType` 枚举定义；统一 `from app.constants import LogLevel, LogType`，保留配置数据类与管理器。
- `app/utils/structlog_config.py`：改为 `from app.constants import LogLevel`，不再从 `app.models.unified_log` 导入枚举；确保 DEBUG 级别仅控制台输出，INFO+ 才入库（现状已具备）。

### 错误处理协同
- 与强制版错误处理方案协同：统一的时间与枚举语义用于 `structlog` 落库与错误响应时间戳生成；响应结构中的时间统一为 `now().isoformat()`（UTC）。

## 分步实施计划（不立即执行，供评审）
1. 模型时间列审计与统一
   - 目标列：`created_at`、`updated_at`、`deleted_at`、`collected_at`、`calculated_at`、`last_sync_time`、`last_change_time` 等。
   - 动作：统一改为 `db.Column(db.DateTime(timezone=True), default=now, onupdate=now)`；保持原有 `nullable/index/comment`。

2. `LogLevel` 引用统一
   - 修改文件：`app/models/unified_log.py`、`app/utils/structlog_config.py`、`app/utils/logging_config.py`、`app/routes/dashboard.py`、`app/routes/logs.py` 等。
   - 规则：一律 `from app.constants import LogLevel`；删除 `app/utils/logging_config.py` 中的重复枚举定义（保留其配置数据类若仍需要）。
   - 注意：先统一模型层（`unified_log.py`）的枚举来源，再统一 `structlog_config.py` 的导入，避免 SQLAlchemy 枚举类型不一致导致比较或入库异常。

3. 序列化/展示一致化
   - 模型 `to_dict()`：时间字段统一 `isoformat()`；分页/统计接口保持 UTC。
   - 前端：在视图层统一使用中国时区显示；避免后端返回不同格式。

4. 测试与回归
   - 单测：时间转换、无 `tzinfo` 修复、枚举一致性、日志落库与错误响应时间字段校验。
   - 集成：`/dashboard`、`/logs`、`/instances`、`/credentials` 常见路径抽样验证。

## 数据迁移设计（Alembic 草案）
### PostgreSQL
- 统一为 `TIMESTAMP WITH TIME ZONE`：
```python
op.alter_column('global_params', 'created_at', type_=sa.DateTime(timezone=True), existing_nullable=True)
op.alter_column('global_params', 'updated_at', type_=sa.DateTime(timezone=True), existing_nullable=True)
```

### MySQL
- `TIMESTAMP`/`DATETIME` 不感知时区；应用层保证入库为 UTC；序列化保留偏移或 `Z`。

### SQLite
- 不区分带时区语义；应用层确保 `tzinfo` 与 `isoformat()` 一致性。

### 历史数据修复策略
- 若 `dt.tzinfo is None`，默认视为 UTC（如业务明确来源为中国时区，则先设为中国时区再转 UTC）。
- 批量修复脚本建议：分页扫描表记录，修正 `tzinfo` 并按需 `astimezone(UTC)`。
 - 模型枚举统一：如将 `unified_log.level` 的枚举类从本地迁移到 `app.constants.LogLevel`，确保枚举值集合一致（`DEBUG/INFO/WARNING/ERROR/CRITICAL`），通常无需变更数据库存储，但需全量回归测试枚举序列化与过滤逻辑。

## 代码变更示例（供评审）
### 枚举引用统一
```python
from app.constants import LogLevel
level = LogLevel.INFO
```

### 模型时间列统一
```python
from app.utils.time_utils import now
created_at = db.Column(db.DateTime(timezone=True), default=now)
updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
```

## 搜索与门禁（持续验证）
### 残留搜索模板
- 统计未带时区的时间列：
  - `rg -n "db\.DateTime\(" app/models | rg -v "timezone=True"`
- 旧枚举引用：
  - `rg -n "from\s+app\.models\.unified_log\s+import\s+LogLevel" app/`
  - `rg -n "class\s+LogLevel\(Enum\)" app/utils app/models`
  - `rg -n "from\s+app\.utils\.logging_config\s+import\s+LogLevel" app/`

### 质量门禁（CI / pre-commit）
- 禁止提交包含旧枚举定义与不带时区的新增列；对现有存量列，必须附带整改计划或迁移脚本。

## 测试清单与验收标准
- 测试维度：
  - 时间：字符串与 `datetime` 输入在 `to_utc()/to_china()` 下行为稳定；序列化保留偏移或 `Z`。
  - 日志：统一 `LogLevel` 来源；`DEBUG` 不落库，仅控制台输出（现有处理器已丢弃 DEBUG）；INFO+ 入库结构完整且枚举序列化一致。
  - 错误响应：统一包含 `timestamp`（UTC）；前端显示正确（中国时区）。
- 验收指标：
  - `rg` 搜索不再出现旧枚举与新增非时区列；
  - 抽样端点错误场景与日志查看均通过；
  - 前端解析统一结构无时间错位。

## 风险与回滚
- 风险：历史数据未标注时区导致显示偏移；部分数据库方言差异带来语义误读。
- 回滚：提供 Alembic `downgrade` 恢复原类型；分批回滚并配合数据修复脚本。

## 排期建议
- 时间列统一与迁移脚本：0.5–1 天
- `LogLevel` 引用统一：0.5 天
- 展示/序列化一致化与测试：1 天
- 总计：约 2–3 天（与错误处理统一联动执行可合并验证）

## 关联文档
- 《日志与错误处理统一方案（无过渡兼容，强制版）》：`docs/refactoring/error_handling_unification.md`
 - 《时区处理规范》：`docs/development/timezone_handling.md`

## 涉及代码位置
- `app/utils/time_utils.py`（统一时间语义与转换）
- `app/utils/structlog_config.py`（时间戳生成与日志落库）
- `app/models/*.py`（时间列统一为 `timezone=True`）
- `app/routes/logs.py`, `app/routes/dashboard.py`（展示层时间统一）