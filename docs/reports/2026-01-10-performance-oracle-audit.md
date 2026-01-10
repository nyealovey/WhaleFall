# Performance Audit (performance-oracle)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-10
> 更新: 2026-01-10
> 范围: `app/services/**`, `app/repositories/**`, `app/api/v1/**`, `app/tasks/**`, `app/static/js/**`
> 方法: 静态审计(查询形态, I/O, 算法复杂度, 缓存与导出路径), 不包含线上 profiling 与真实 QPS/数据量基准

## 1. Performance summary

优势(有利于性能与扩展):

- API 列表接口具备统一的 `page/limit` 语义与上限(`limit <= 200`), 降低了 "一次拉全量" 的风险(`app/utils/pagination_utils.py`).
- 容量采集写入采用 PostgreSQL upsert(`on_conflict_do_update`), 避免逐行 insert/update(`app/services/database_sync/persistence.py`).
- 聚合计算优先在数据库侧做 group_by(avg/max/min/count), 避免拉取明细后在 Python 分组(`app/services/aggregation/database_aggregation_runner.py`).

主要风险(随数据增长会放大):

- 多处存在 N+1 与 "按实例逐个查询" 的读路径, 在实例数与数据量上升时会显著拖慢任务与页面加载.
- 数据库台账的 "latest stats" 子查询未做时间/分区约束, 可能随着 `database_size_stats` 增长成为 P0 级热点.
- 导出路径存在 "全量读入内存 + 全量生成字符串" 的组合, 大数据集下容易触发内存与响应时间问题.

## 2. Critical issues

### P0-1: Tags bulk actions 存在 N+1 + O(n*m) 级写操作

位置: `app/services/tags/tags_bulk_actions_service.py`

现状:

- `Instance.tags` 使用 `lazy="dynamic"`(返回 Query), 导致每个 instance 访问 `instance.tags.all()` 都会触发一次查询(`app/models/instance.py`).
- `assign/remove/remove_all/list_instance_tags` 均在循环内调用 `tags_relation.all()`, 形成 N+1 查询, 并在写路径上做逐条 append/remove.

规模化影响(10x/100x):

- 10x instances: 查询数近似线性上升, 写路径 append/remove 触发的 flush/relationship bookkeeping 也会放大.
- 100x instances: 在批量操作中很容易出现秒级甚至分钟级延迟, 并放大 DB 锁竞争.

推荐方案(用 association table 做批量读写):

核心思路:

- 读: 一次性取出 `instance_tags` 的 (instance_id, tag_id) 形成 existing map.
- 写:
  - assign: 计算缺失 pair 后批量 insert.
  - remove: 单条 delete 条件 `instance_id in (...) and tag_id in (...)`.
  - remove_all: 单条 delete 条件 `instance_id in (...)`.

示例(伪代码, 需按事务边界与错误封套落地):

```python
from collections import defaultdict

from app import db
from app.models.tag import instance_tags

rows = (
    db.session.query(instance_tags.c.instance_id, instance_tags.c.tag_id)
    .filter(instance_tags.c.instance_id.in_(instance_ids))
    .all()
)
existing = defaultdict(set)
for instance_id, tag_id in rows:
    existing[int(instance_id)].add(int(tag_id))

to_insert = []
for instance_id in instance_ids:
    for tag_id in tag_ids:
        if tag_id not in existing[instance_id]:
            to_insert.append({"instance_id": instance_id, "tag_id": tag_id})

if to_insert:
    db.session.execute(instance_tags.insert(), to_insert)

db.session.execute(
    instance_tags.delete().where(
        instance_tags.c.instance_id.in_(instance_ids)
        & instance_tags.c.tag_id.in_(tag_ids)
    )
)
```

### P0-2: Database ledger "latest stats" 子查询可能无法随数据增长保持低延迟

位置: `app/repositories/ledgers/database_ledger_repository.py:_with_latest_stats`

现状:

- 通过 `DatabaseSizeStat` 全表 group_by(instance_id, database_name) + max(collected_at) 得到 latest, 再 outer join 回去.
- 该子查询没有时间范围条件, 在分区表场景下可能导致跨分区扫描, 成本随历史数据线性增长.

规模化影响(以每日 1 行/库 估算):

- 例如 200 instances * 200 databases * 365 days ~= 14.6M rows/year.
- ledger 页面属于高频读, 若每次请求都扫描历史 stats, 延迟会随时间增长, 并逐步成为系统主热点.

推荐方案(按侵入性从低到高):

1. 低侵入: 用 `max(collected_date)` 替代 `max(collected_at)` 并 join `collected_date`
   - 原因: `database_size_stats` 已有 `instance_id + collected_date` 索引与 `uq(instance_id, database_name, collected_date)`.
   - 目标: 让查询更容易被索引/分区裁剪利用.

2. 中侵入: 引入 "latest snapshot" 表或字段
   - 在采集写入时, 同步维护每个 (instance_id, database_name) 的 latest size 与 collected_at.
   - ledger 列表直接 join snapshot, 避免对 stats 做全表聚合.

3. 高侵入: 针对统计表做物化视图/增量聚合
   - 适合数据量巨大且查询模式稳定的场景, 但运维与一致性成本更高.

### P0-3: 导出路径存在 "全量加载 + 全量生成" 的内存与延迟风险

位置:

- `app/repositories/ledgers/database_ledger_repository.py:iterate_all` 返回 `list[...]`
- `app/services/files/database_ledger_export_service.py` 使用 `io.StringIO` 在内存生成完整 CSV

影响:

- 数据量上升时, 内存占用与响应时间会线性上升, 并可能触发 WSGI worker 被 OOM 或超时杀死.

推荐方案:

- repository 提供 generator + `yield_per`/分页游标, 避免一次性 `.all()`.
- export 端使用 streaming response(逐行 yield CSV), 或落盘临时文件后由 Nginx/对象存储分发.

## 3. Optimization opportunities

### O1: 减少不必要的 `.all()` 与大对象 materialization

观测:

- 多处使用 `Instance.query.filter_by(is_active=True).all()` 作为任务入口与统计入口, 如:
  - `app/tasks/capacity_collection_tasks.py`
  - `app/services/aggregation/database_aggregation_runner.py`

建议:

- 若只需要 id/name, 使用 `with_entities(Instance.id, Instance.name)` 减少列.
- 若实例数可能增大, 用 chunk 分批处理(按 id 排序 + limit/offset 或 keyset)以控制内存峰值.

### O2: `update_instance_total_size` 可改为 SQL 聚合避免拉全量行

位置: `app/services/database_sync/persistence.py:update_instance_total_size`

现状:

- `.all()` 拉回当天所有数据库 stats 行, Python `sum/len`, 然后又构造列表传入 `save_instance_stats` 让其再次 `sum/len`.

建议:

- 直接用 SQL 计算 sum/count:

```python
from sqlalchemy import func

total_size, database_count = (
    db.session.query(func.sum(DatabaseSizeStat.size_mb), func.count(DatabaseSizeStat.id))
    .filter(DatabaseSizeStat.instance_id == instance.id, DatabaseSizeStat.collected_date == today)
    .one()
)
```

- `save_instance_stats` 增加一个 "summary" 入口, 允许传入已计算好的 `total_size_mb` 与 `database_count`.

### O3: 计数查询(`count()`)对大表分页可能成为热点

位置示例:

- `app/repositories/ledgers/database_ledger_repository.py:list_ledger` (join + distinct + count)
- `app/repositories/history_logs_repository.py` (时间范围 count)

建议(按 UI 诉求取舍):

- 若 UI 强依赖 total: 确保 count 的 where 条件可用索引, 并避免对 join/distinct 直接 count(可改为 count(distinct pk)).
- 若 UI 可接受 "has_next": 用 `limit(per_page + 1)` 代替 count, 返回 `has_next` 与 `items`.

### O4: 缓存相关的性能与一致性问题(引用既有审计)

已有审计指出多个与性能强相关的问题:

- cache 清理接口 no-op 但返回成功, 使得缓存失效与运维动作失真
- decorator cache 无法缓存 None, 造成 cache penetration
- Nginx 静态资源长 TTL + immutable 但缺少指纹化, 容易造成前端版本漂移

建议优先阅读并按 P0/P1 清单处理: `docs/reports/2026-01-04-cache-usage-audit.md`

## 4. Scalability assessment (10x/100x)

### 4.1 Core data growth projections

- `database_size_stats`: 近似按 (instances * databases * days) 增长, 且为 ledger/dashboard 的主要数据源.
- `unified_logs`: 近似按 QPS 增长, 当前已有复合索引, 但仍需 retention/cleanup 机制持续生效.

### 4.2 Concurrency and background jobs

- scheduler executor `max_workers=5`(`app/scheduler.py`) 对外部 DB 采集属于保守配置, 有利于避免压垮被管 DB, 但会拉长全量任务完成时间.
- 任务实现多为 "遍历活跃实例顺序执行", 10x instances 时整体任务时间近似线性增长.

建议:

- 为任务补齐 "总耗时/单实例耗时/失败率" 的指标, 决定是否需要并发或分片.
- 若引入并发, 以 instance 为粒度做 bounded concurrency(例如 3-5 并发), 并对外部 DB 做 per-host 限流.

## 5. Recommended actions (prioritized)

1. P0: 将 tags bulk actions 改为 `instance_tags` 表的批量读写, 消除 N+1 与 O(n*m) 逐条写.
2. P0: 优化 ledger 的 latest stats 计算路径, 避免对 stats 表做无界 group_by.
3. P0: 让导出路径支持流式查询与流式输出, 避免全量 `.all()` 与内存构建 CSV.
4. P1: 对高频分页接口梳理 count() 的成本与索引覆盖, 必要时提供 has_next 模式.
5. P1: 落地 cache 审计中的 P0 项, 并为关键缓存与任务补齐可观测指标(耗时, 命中率, 删除数).

