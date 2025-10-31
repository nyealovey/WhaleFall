#!/usr/bin/env bash

# Rebuild database & instance capacity aggregations for a given month.
# Usage: ./scripts/repair_month_aggregations.sh YYYY-MM
#
# Prerequisites:
#   - Run from repository根目录，并已激活虚拟环境 / 安装依赖
#   - 需要访问数据库的账号、环境配置与正常运行时一致

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 YYYY-MM" >&2
    exit 1
fi

if [[ ! $1 =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]; then
    echo "Error: month must be in YYYY-MM format" >&2
    exit 1
fi

YEAR=${1%-*}
MONTH=${1#*-}

export AGG_REPAIR_YEAR="$YEAR"
export AGG_REPAIR_MONTH="$MONTH"

python3 <<'PY'
import os
from datetime import date, timedelta
from calendar import monthrange

from app import create_app, db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.services.aggregation.database_size_aggregation_service import DatabaseSizeAggregationService

year = int(os.environ["AGG_REPAIR_YEAR"])
month = int(os.environ["AGG_REPAIR_MONTH"])

app = create_app()
app.app_context().push()

service = DatabaseSizeAggregationService()

start_date = date(year, month, 1)
end_date = date(year, month, monthrange(year, month)[1])

print(f"[repair] Rebuilding aggregations for {start_date:%Y-%m} ({start_date} ~ {end_date})")

# 1) 删除目标时间段已有聚合数据，避免重复
# 日聚合：period_start 在当月内
for model in (DatabaseSizeAggregation, InstanceSizeAggregation):
    deleted = model.query.filter(
        model.period_type == 'daily',
        model.period_start.between(start_date, end_date)
    ).delete(synchronize_session=False)
    if deleted:
        print(f"[repair] removed {deleted} daily records from {model.__tablename__}")

# 周聚合：覆盖该月的周起始日
weekly_starts = []
week_start = start_date - timedelta(days=start_date.weekday())
while week_start <= end_date:
    weekly_starts.append(week_start)
    week_start += timedelta(days=7)

for model in (DatabaseSizeAggregation, InstanceSizeAggregation):
    deleted = model.query.filter(
        model.period_type == 'weekly',
        model.period_start.in_(weekly_starts)
    ).delete(synchronize_session=False)
    if deleted:
        print(f"[repair] removed {deleted} weekly records from {model.__tablename__}")

# 月聚合：当前月份
for model in (DatabaseSizeAggregation, InstanceSizeAggregation):
    deleted = model.query.filter(
        model.period_type == 'monthly',
        model.period_start == start_date
    ).delete(synchronize_session=False)
    if deleted:
        print(f"[repair] removed {deleted} monthly records from {model.__tablename__}")

# 季度聚合：包含该月的季度（跨年时自动处理）
quarter_start_month = ((month - 1) // 3) * 3 + 1
quarter_start_year = year
if quarter_start_month <= 0:
    quarter_start_month += 12
    quarter_start_year -= 1
quarter_start = date(quarter_start_year, quarter_start_month, 1)
quarter_end_month = quarter_start_month + 2
quarter_end_year = quarter_start_year
if quarter_end_month > 12:
    quarter_end_month -= 12
    quarter_end_year += 1
quarter_end = date(
    quarter_end_year,
    quarter_end_month,
    monthrange(quarter_end_year, quarter_end_month)[1]
)

for model in (DatabaseSizeAggregation, InstanceSizeAggregation):
    deleted = model.query.filter(
        model.period_type == 'quarterly',
        model.period_start == quarter_start
    ).delete(synchronize_session=False)
    if deleted:
        print(f"[repair] removed {deleted} quarterly records from {model.__tablename__}")

db.session.commit()

# 2) 重建日聚合
day = start_date
while day <= end_date:
    service._calculate_aggregations('daily', day, day)
    service._calculate_instance_aggregations('daily', day, day)
    day += timedelta(days=1)
print(f"[repair] rebuilt daily aggregations for {start_date:%Y-%m}")

# 3) 重建周聚合
for week_start in weekly_starts:
    week_end = week_start + timedelta(days=6)
    service._calculate_aggregations('weekly', week_start, week_end)
    service._calculate_instance_aggregations('weekly', week_start, week_end)
print(f"[repair] rebuilt weekly aggregations covering {start_date:%Y-%m}")

# 4) 重建月聚合
service._calculate_aggregations('monthly', start_date, end_date)
service._calculate_instance_aggregations('monthly', start_date, end_date)
print(f"[repair] rebuilt monthly aggregations for {start_date:%Y-%m}")

# 5) 重建季度聚合
service._calculate_aggregations('quarterly', quarter_start, quarter_end)
service._calculate_instance_aggregations('quarterly', quarter_start, quarter_end)
print(f"[repair] rebuilt quarterly aggregations for Q{((start_date.month - 1) // 3) + 1} {start_date.year}")

print("[repair] aggregation rebuild complete.")
PY
