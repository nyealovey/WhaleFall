# 仪表盘统计查询性能优化：账户汇总与容量汇总（基于 2025-12-22）

> 目标：修复仪表盘概览接口在数据量上升后的明显卡顿问题，将“拉回全量行 -> Python 聚合”的实现改为“数据库侧聚合 -> O(1) 返回”。

## 1. 背景与影响面

仪表盘首页与 `/dashboard/api/overview` 会聚合多个统计模块的数据（见 `app/routes/dashboard.py` 的 `get_system_overview()`）。其中两处统计曾使用 `.all()` 拉回大量行并在 Python 侧做遍历/去重：

- **账户汇总**：`app/services/statistics/account_statistics_service.py` 的 `fetch_summary()`。
- **容量汇总**：`app/services/statistics/instance_statistics_service.py` 的 `fetch_capacity_summary()`。

当账户数量、实例数量、容量历史记录增长时，这两处实现会导致：

- 首次加载（或缓存失效后首次命中）明显变慢。
- Web Worker CPU/内存占用上升，触发 GC 抖动，影响同进程的其他请求。
- SQL 语句数量不稳定（可能出现 N+1），进一步放大波动。

## 2. 性能问题定位（为何会慢）

### 2.1 账户汇总：`.all()` + Python 计数 + 潜在 N+1

**位置**：`app/services/statistics/account_statistics_service.py:fetch_summary`

旧实现流程（简化）：

1) 构造 `AccountPermission` 的查询并 `.all()` 拉回所有匹配行（ORM 对象列表）。  
2) Python 遍历每一行，通过 `instance_account.is_active` 与锁定逻辑累加计数。  

核心问题：

- **不需要“行级对象”却拉回了完整 ORM 对象**：包含 JSON 字段与关系字段，反序列化/构造对象成本高。
- **潜在 N+1**：查询中虽然 `join(InstanceAccount, ...)`，但未显式 eager-load 关系；遍历时访问 `account.instance_account` 可能触发按行懒加载，SQL 数量随行数线性增长。
- **可替代性强**：实际只需要 `total/active/locked` 三个计数（再派生 `normal/deleted`），完全适合数据库侧 `COUNT/SUM(CASE...)`。

### 2.2 容量汇总：最近 N 天全量拉回 + Python “每实例取最新”

**位置**：`app/services/statistics/instance_statistics_service.py:fetch_capacity_summary`

旧实现流程（简化）：

1) 拉回最近 N 天的 `InstanceSizeStat` 全量记录（行数约为 `实例数 * N`）。  
2) Python 用 dict 按 `instance_id` 去重，仅保留“最新一条”，最后求和。  

核心问题：

- **I/O 与内存浪费**：为了最终一个 sum，拉回了大量行与对象。
- **复杂度放大**：数据规模增长时，遍历与去重的 CPU 成本线性上升。
- **数据库更擅长做“每组取最新 + 聚合”**：可以用窗口函数或子查询一次性完成。

## 3. 重构方案（改什么，怎么改）

### 3.1 账户汇总：用数据库条件聚合替代 Python 遍历

**目标**：只返回计数，不返回行对象。

实现要点：

- 使用单条聚合查询获取：
  - `total_accounts = COUNT(account_permission.id)`
  - `active_accounts = SUM(CASE WHEN instance_accounts.is_active THEN 1 ELSE 0 END)`
  - `locked_accounts = SUM(CASE WHEN instance_accounts.is_active AND account_permission.is_locked THEN 1 ELSE 0 END)`
- `deleted_accounts = total_accounts - active_accounts`
- `normal_accounts = active_accounts - locked_accounts`

代码落点：

- `app/services/statistics/account_statistics_service.py:fetch_summary`

### 3.2 容量汇总：窗口函数取每实例最新一条后求和

**目标**：只返回 “每实例最新一条”的 `total_size_mb` 总和（再换算成 GB）。

实现要点：

- 在 `InstanceSizeStat` 的时间窗口内（最近 N 天）：
  - `ROW_NUMBER() OVER (PARTITION BY instance_id ORDER BY collected_date DESC, collected_at DESC)` 标记每个实例的最新记录为 `rn=1`
- 外层 `SUM(total_size_mb)` 只对 `rn=1` 的记录求和

代码落点：

- `app/services/statistics/instance_statistics_service.py:fetch_capacity_summary`

> 说明：旧实现仅按 `collected_date` 取最新；新实现在同一天存在多条记录时，会按 `collected_at` 进一步选“更晚”的一条，更符合“最新一条”的语义。

## 4. 预期收益（量化口径）

以“仪表盘概览一次缓存 miss 的请求”为口径：

- **账户汇总**
  - 旧：1 次大查询拉回 N 行对象 +（可能）N 次懒加载查询 + Python O(N) 遍历
  - 新：1 次聚合查询返回 1 行（O(1)）
- **容量汇总**
  - 旧：拉回约 `实例数 * N` 行对象 + Python 去重/求和
  - 新：数据库侧计算后返回 1 个数值（O(1)）

## 5. 验证建议（上线前/回归）

1) 质量门禁（改动文件级别）
```bash
ruff check app/services/statistics/account_statistics_service.py app/services/statistics/instance_statistics_service.py
npx pyright --warnings app/services/statistics
pytest -m unit
```

2) 性能验证（建议本地对比）
- 在数据量较大的开发库上对比 `/dashboard/api/overview` 响应时间与 SQL 语句数量。
- 如需定位 SQL 数量，可临时打开 SQLAlchemy 日志（注意不要提交调试代码）。

## 6. 后续改进（可选）

- 账户统计页的 `fetch_db_type_stats()` 仍存在 `.all()` + Python 计数的同类模式，可按本方案进一步改为按 `db_type` 分组的条件聚合，减少重复扫描。
- 如容量表数据量持续增长，可考虑为 `instance_size_stats` 增加更贴合查询的复合索引（例如 `(instance_id, collected_date, collected_at)`），并结合实际数据库选择索引排序方向。

