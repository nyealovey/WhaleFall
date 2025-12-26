# PostgreSQL Schema 基线与初始化口径

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-19  
> 更新：2025-12-26  
> 范围：`sql/init_postgresql*.sql`、`migrations/**`、新环境建库与基线对齐  
> 关联：`../../standards/backend/database-migrations.md`

## 字段/参数表

本仓库提供两条“空库初始化”路径（二选一），以及一条“既有库基线对齐”路径：

| 场景 | 入口/脚本 | 命令 | 结果 |
| --- | --- | --- | --- |
| 空库初始化（SQL 初始化） | `sql/init_postgresql.sql` + 分区脚本 | `psql "$DATABASE_URL" -f ...` + `flask db stamp 20251219161048` | 直接建出与基线一致的结构，并把 Alembic 版本戳到基线 |
| 空库初始化（迁移驱动） | `migrations/**` | `flask db upgrade` | 通过迁移链建库（包含基线 + 后续迁移） |
| 既有库对齐基线 | Alembic 版本戳 | `flask db stamp 20251219161048` | 仅写入 `alembic_version`，不执行 DDL（适用于“结构已同构”的库） |

> 基线 revision：`20251219161048`（见 `migrations/versions/20251219161048_baseline_production_schema.py`）。

## 默认值/约束

- 必须遵循 `../../standards/backend/database-migrations.md` 的“初始化二选一”规则：**禁止**对同一个空库同时执行 SQL 初始化与 `flask db upgrade`。
- 基线之后的迁移以 `migrations/versions/` 为准；当前仓库已存在多个基线后的迁移文件（例如 `20251224120000_*`、`20251224134000_*` 等）。
- 分区脚本按月份拆分：目前仓库内包含 `sql/init_postgresql_partitions_2025_07.sql`、`sql/init_postgresql_partitions_2025_08.sql`；如需新增月份分区，应以新脚本追加（不要改历史脚本）。

## 示例

### 方案 A：SQL 初始化空库（推荐用于“纯初始化”）

```bash
psql "$DATABASE_URL" -f sql/init_postgresql.sql
psql "$DATABASE_URL" -f sql/init_postgresql_partitions_2025_07.sql
psql "$DATABASE_URL" -f sql/init_postgresql_partitions_2025_08.sql

# 建库完成后把版本戳到基线，避免后续 upgrade 重复建表
flask db stamp 20251219161048
```

### 方案 B：迁移驱动空库（推荐用于“统一由迁移驱动”）

```bash
flask db upgrade
```

### 既有库对齐（结构已存在）

```bash
flask db stamp 20251219161048
```

## 版本/兼容性说明

- `sql/init_postgresql.sql` 的注释中可能引用“生产结构导出”来源（例如 `public.sql`）；该导出文件不作为可执行真源，仓库内以 `init_postgresql*.sql` 与 Alembic 迁移链为准。
- 如果你需要把一个旧环境切到当前迁移链，优先用 `stamp` 做“版本对齐”；只有在确认库结构缺失时才使用 `upgrade` 执行 DDL。

## 常见错误

- 空库先跑 `sql/init_postgresql.sql`，再跑 `flask db upgrade`：会出现“对象已存在/重复建表”等错误；正确做法是二选一，或在 SQL 初始化后执行 `flask db stamp 20251219161048`。
- 既有库结构未同构却执行 `stamp`：会导致“版本号对齐但结构缺失”，后续运行可能报错；应先对比 schema 差异并补迁移或回滚改动。
- 分区脚本遗漏：容量统计相关表缺少分区会导致聚合/采集失败；应按月份补齐对应 `init_postgresql_partitions_YYYY_MM.sql`。
