# 后端分层标准问题报告（layer/10篇聚焦审计，2026-01-11）
> 状态: Draft  
> 创建: 2026-01-11  
> 更新: 2026-01-11  
> 范围: `docs/Obsidian/standards/backend/layer/*.md`(10 篇) + 代码对照(`app/**`)  
> 本次重点: Constants / Types / Models / Utils / Repositories（含魔法数字扫描、pyright 基线清零）

## 0. 结论摘要（TL;DR）

- `pyright` diagnostics 已清零；`scripts/ci/baselines/pyright.txt` 已更新为空基线（0 行）。
- 标准文本层面的主要问题：
  - `layer/README.md` 的依赖图对 `Errors/Constants/Types` 的箭头方向与“保持纯净、被全局复用”的设定不一致，容易误导依赖方向。见 `docs/Obsidian/standards/backend/layer/README.md:45`。
  - `constants-layer-standards.md` 的 “MUST NOT: app.*” 过于绝对，按字面会否决 `app/constants/**` 内部模块互相 import 的现实做法。见 `docs/Obsidian/standards/backend/layer/constants-layer-standards.md:70`。
  - `types-layer-standards.md` 明确 “只定义类型，不写业务逻辑”，但 `app/types/**` 当前包含 payload 解析/转换函数，口径不一致。见 `docs/Obsidian/standards/backend/layer/types-layer-standards.md:37`。
- 代码层面的主要漂移点：
  - Utils 层出现 DB 事务/写入（`app/utils/database_batch_manager.py`），与 utils-layer-standards 的“无 DB 依赖”冲突。
  - Types 层出现解析/转换逻辑（`app/types/request_payload.py`, `app/types/converters.py`），与 types-layer-standards 的“无逻辑”冲突。
  - Constants 层大量提供 helper methods（`TimeConstants.minutes()` 等），与 constants-layer-standards 的“只放不可变常量/枚举/静态映射”描述不一致（需要“标准补齐”或“代码迁移”二选一）。

## 1. 标准文本层面的边界问题（docs 层）

### 1.1 `layer/README.md` 依赖图方向不一致（会误导）

现状：依赖图用 `A --> B` 表达 “A 依赖 B”（例如 `Routes --> Services`），但同一语义下：

- `Errors --> Routes & API & ...`（`docs/Obsidian/standards/backend/layer/README.md:45`）
- `Constants --> Routes & API & ...`（`docs/Obsidian/standards/backend/layer/README.md:46`）
- `Types --> Routes & API & ...`（`docs/Obsidian/standards/backend/layer/README.md:47`）

这会在阅读者心智里推导出 “Errors/Constants/Types 依赖上层” 的结论，与各层标准中“保持纯净、被各层复用”的设定相冲突。

建议（择一并全量统一）：

- 方案 A：保持现有箭头语义（上层依赖下层），把 Errors/Constants/Types 的箭头反转为 `Routes/API/Tasks/Services/Repositories/Models/FormsViews/Utils --> Errors/Constants/Types`。
- 方案 B：改写图的语义为“可被依赖/可被 import”，则需要将整张图箭头反向（含 Routes/Services 等），避免局部特殊化。

### 1.2 `constants-layer-standards.md` 的依赖规则表述过宽（与代码实践冲突）

现状：`docs/Obsidian/standards/backend/layer/constants-layer-standards.md:70` 规定：

- `MUST NOT: app.* 任何应用模块(保持纯净)`

按字面将把 `app.constants` 内部模块互相 import 也一并否决（例如 `app/constants/filter_options.py` 内 import `app.constants.database_types`），与现实做法冲突，容易在评审中产生“标准与实现二选一”的争议。

建议：把禁止范围收窄到“业务层/有副作用的依赖”，例如：

- MUST NOT: `app.(api|routes|tasks|services|repositories|models|forms|views|utils|settings|infra|schemas).*`
- MAY: `app.constants.*` 内部互相 import（或推荐只从 `app.constants` 聚合导出导入）

### 1.3 `types-layer-standards.md` 的“无逻辑”口径与 `app/types/**` 现状不一致

现状：`docs/Obsidian/standards/backend/layer/types-layer-standards.md:37` 规定：

- MUST: 只定义类型, 不写业务逻辑.

但当前 `app/types/**` 中存在纯函数的“解析/转换逻辑”（见 2.2）。

建议（必须二选一，避免长期口径不一致）：

- 方案 A：迁移解析/转换代码到 `app/utils/**`（Types 只保留 types/structures/aliases/protocols）。
- 方案 B：补齐标准，允许“纯函数/无副作用/只依赖标准库 + app.types.structures”的轻量 converters/parsers，但仍保持：
  - MUST NOT: `db.session` / `app.models.*` / `app.services.*` / `app.repositories.*`

## 2. 代码对照发现（按本次重点层）

### 2.1 Utils 层：出现 DB 事务与写入（边界漂移）

- 文件：`app/utils/database_batch_manager.py:13`（`from app import db`）与 `app/utils/database_batch_manager.py:151`（`db.session.begin/begin_nested/add/merge/delete/flush/rollback`）。
- 与标准冲突：utils-layer-standards 明确禁止工具层依赖 `db.session`。

风险：

- 工具层变成“隐形仓储/隐形事务边界”，一旦被 routes/services 直接复用，很容易让 DB 写入路径绕过 Repository/Service 的边界约束。

建议（方向建议，不在本报告内直接实施）：

- 若这是“批量写入能力”：迁移到 `app/repositories/common/**` 或 `app/infra/db/**`（归入“允许 DB”的层）。
- 若这是“任务/同步 runner 的内部优化”：把它作为 repository 内部 helper，由 service 统一控制 commit/rollback。

### 2.2 Types 层：出现 payload 解析/类型转换逻辑（边界漂移）

现状文件：

- `app/types/request_payload.py:23` 定义 `parse_payload(...)`（解析 MultiDict/Mapping、输入清理、补默认）。
- `app/types/converters.py:26` 定义 `as_str/as_int/as_bool/...`（纯函数转换）。

与标准冲突：

- types-layer-standards 明确“只定义类型，不写业务逻辑”（见 1.3）。

风险：

- `app/types/**` 变成“工具层”，未来容易把更多“轻逻辑”塞进 types，导致 types 的依赖面变大、边界变糊、循环依赖风险上升。

建议（方向建议）：

- 迁移到 `app/utils/request_payload.py` + `app/utils/payload_converters.py`；
- 或按 1.3 方案 B 补齐标准，明确其允许范围与禁止范围。

### 2.3 Constants 层：helper methods 与标准描述不一致（标准/实现漂移）

示例：

- `app/constants/time_constants.py:39` 起存在 `TimeConstants.minutes/hours/days/to_minutes/to_hours/to_days` 等方法（运行时计算）。

现状矛盾点：

- constants-layer-standards 重点描述“不可变常量/枚举/静态映射”，但 constants 包内普遍存在 `is_valid/get_display_name/normalize/...` 等 helper methods。

建议：

- 若团队认可“constants 允许纯 helper methods”：在标准中明确允许哪些 helper（例如 `choices()`/纯 getter），并明确禁止哪些（例如 IO、环境读取、DB、复杂业务判断）。
- 若团队坚持“constants 只放值”：将 helper methods 下沉到 `app/utils/**` 或对应 domain service，constants 只保留 `Final`/`Enum`/静态 mapping。

### 2.4 Repositories/Models 层：本轮扫描未发现硬违规

硬规则扫描结果（聚焦本次重点）：

- Repositories：未发现 `db.session.commit`，未发现反向依赖 `app.services/app.routes/app.api`。
- Models：未发现反向依赖 `app.services/app.repositories`。

> 注：本轮不做 “Model 内 query helper 是否过多” 的深挖；若要做，需要以“绕过 Repository 的潜在路径”作为专项口径单独扫描。

## 3. 魔法数字扫描（常量候选）

### 3.1 `ruff`（`PLR2004`）命中清单（比较阈值类，26 处）

扫描命令：

```bash
./.venv/bin/ruff check --select PLR2004 --output-format concise app
```

命中（按文件聚合后摘录核心项，完整列表可复跑命令获取）：

- `app/api/v1/namespaces/databases.py`: 2000（limit 上限）
- `app/schemas/auth.py`: 6 / 128（密码长度上下限）
- `app/schemas/credentials.py`: 3 / 50 / 6 / 128（字段长度/密码长度）
- `app/schemas/instances.py`: 100 / 255 / 65535 / 64 / 500（字段长度/阈值）
- `app/services/account_classification/dsl_v4.py`: 4
- `app/services/accounts_permissions/facts_builder.py`: 4
- `app/services/accounts_permissions/snapshot_view.py`: 4
- `app/services/database_sync/table_size_adapters/*`: 2 / 5
- `app/settings.py`: 4 / 23

建议：将“跨文件复用且具备业务语义的阈值”收敛到常量层（例如 `app/constants/validation_limits.py`），并为 ruff PLR2004 引入 baseline 机制（类似 pyright-guard），避免一次性清仓带来的评审/合并压力。

### 3.2 tokenize 统计（非比较场景的数字分布，摘要）

说明：该统计能帮助识别“重复出现且缺少语义命名”的数值，但需要人工过滤 HTTP 状态码、SQLAlchemy Column 精度等“天然数字”。

建议关注的候选点（举例）：

- 分页/列表默认与上限：`20/50/100/200/2000`
- 字段长度：`64/100/128/255/500/65535`
- 重试/等待：`2/3.0/5.0/10`

## 4. Types：pyright 基线清零（已完成）

验证口径：

```bash
./scripts/ci/pyright-guard.sh
```

现状：

- `pyright` 当前 diagnostics: 0
- `scripts/ci/baselines/pyright.txt`: 0 行（空基线）

本次为清零所做的改动点（与业务行为无关，主要为类型与 API 调用修复）：

- 修复聚合计数查询行字段命名冲突：`app/repositories/aggregation_repository.py`
- 修复 SQLAlchemy `fetchall()` 返回类型与注解不一致：`app/repositories/partition_management_repository.py`
- 补齐聚合 service 的缺失方法并修复 read service 调用方式：`app/services/aggregation/aggregation_service.py`, `app/services/aggregation/capacity_aggregation_task_runner.py`
- 修复 SQLAlchemy model 字段类型推断导致的 dict key 类型不匹配：`app/services/aggregation/database_aggregation_runner.py`
- 修复 manual task 里对实例读 service 的错误调用：`app/tasks/capacity_aggregation_manual_tasks.py`
- 修复 manual task 里对 `total_size_mb` 的类型收敛：`app/tasks/capacity_collection_manual_tasks.py`

## 5. 后续建议（落地方向）

按“先统一口径，再做迁移”的顺序：

1) 先修正 `layer/README.md` 依赖图方向（避免继续误导）。
2) 决策并落地：Types 是否允许 converters/parsers（A：迁移到 utils；B：补齐标准）。
3) 决策并落地：Constants 是否允许 helper methods（A：补齐标准；B：迁移到 utils/service）。
4) 处理 `app/utils/database_batch_manager.py` 的 DB 访问漂移（迁移到 repo/common 或 infra/db）。
5) 将 “有业务语义的魔法数字阈值” 收敛到常量，并为 ruff PLR2004 引入 baseline/门禁策略。

