# 查询参数标准分析

## 概述
分析项目中各个表/路由的查询参数实现情况，识别不一致的地方，为统一标准提供依据。

## 1. 分页参数

### 当前实现情况

#### 使用 `page` + `per_page` 的路由
- **account.py** (账户列表)
  - `page = request.args.get("page", 1, type=int)`
  - `per_page = request.args.get("per_page", 20, type=int)`
  - 默认值: page=1, per_page=20

- **logs.py** (日志查询)
  - `page = int(request.args.get("page", 1))`
  - `per_page = int(request.args.get("per_page", 50))`
  - 默认值: page=1, per_page=50

- **account_sync.py** (同步记录)
  - `page = request.args.get("page", 1, type=int)`
  - `per_page = request.args.get("per_page", 20, type=int)`
  - 默认值: page=1, per_page=20

- **users.py** (用户管理)
  - `page = request.args.get("page", 1, type=int)`
  - `per_page = request.args.get("per_page", 10, type=int)`
  - 默认值: page=1, per_page=10

- **sync_sessions.py** (同步会话)
  - `page = int(request.args.get("page", 1))`
  - `per_page = int(request.args.get("per_page", 20))`
  - 默认值: page=1, per_page=20

#### 使用 `limit` 的路由
- **logs.py** (错误日志、导出日志、实时日志)
  - `limit = int(request.args.get("limit", 50))`
  - `limit = int(request.args.get("limit", 1000))`
  - `limit = int(request.args.get("limit", 20))`
  - 不同接口默认值不同: 20/50/1000

- **account.py** (变更日志、同步记录)
  - `.limit(50)` - 硬编码
  - `.limit(10)` - 硬编码

### 问题识别
1. **参数名称不统一**: 混用 `page+per_page` 和 `limit`
2. **默认值不统一**: per_page 有 10/20/50 等不同值
3. **类型转换方式不统一**: 
   - `request.args.get("page", 1, type=int)` ✓ 推荐
   - `int(request.args.get("page", 1))` - 可能抛异常
4. **硬编码limit**: 部分查询直接写死 `.limit(50)`


## 2. 搜索/过滤参数

### 当前实现情况

#### account.py (账户列表)
```python
search = request.args.get("search", "").strip()
instance_id = request.args.get("instance_id", type=int)
is_locked = request.args.get("is_locked")
is_superuser = request.args.get("is_superuser")
plugin = request.args.get("plugin", "").strip()
tags = [tag for tag in request.args.getlist("tags") if tag.strip()]
classification = request.args.get("classification", "").strip()
```

#### logs.py (日志查询)
```python
level = request.args.get("level")
module = request.args.get("module")
search_term = request.args.get("q", "").strip()  # 注意: 使用 "q" 而非 "search"
start_time = request.args.get("start_time")
end_time = request.args.get("end_time")
hours = request.args.get("hours")
sort_by = request.args.get("sort_by", "timestamp")
sort_order = request.args.get("sort_order", "desc")
```

#### account_sync.py (同步记录)
```python
sync_type = request.args.get("sync_type", "all")
status = request.args.get("status", "all")
date_range = request.args.get("date_range", "all")
```

#### users.py (用户管理)
```python
search = request.args.get("search", "", type=str)
role_filter = request.args.get("role", "", type=str)
status_filter = request.args.get("status", "", type=str)
```

#### sync_sessions.py (同步会话)
```python
sync_type = request.args.get("sync_type", "")
sync_category = request.args.get("sync_category", "")
status = request.args.get("status", "")
```

### 问题识别
1. **搜索参数名不统一**: 
   - `search` (account.py, users.py)
   - `q` (logs.py)
   - 建议统一使用 `search` 或 `q`

2. **默认值处理不统一**:
   - 有的用空字符串 `""`
   - 有的用 `"all"`
   - 有的不设默认值 (None)

3. **布尔值处理不统一**:
   - `is_locked = request.args.get("is_locked")` - 返回字符串
   - 需要后续判断 `is_locked == "true"`
   - 缺少统一的布尔值转换函数

4. **列表参数处理**:
   - `tags = request.args.getlist("tags")` - 正确
   - 但缺少统一的列表参数验证


## 3. 排序参数

### 当前实现情况

#### logs.py (日志查询)
```python
sort_by = request.args.get("sort_by", "timestamp")
sort_order = request.args.get("sort_order", "desc")
```

#### 其他路由
- 大部分路由没有排序参数，直接硬编码排序逻辑
- 例如: `.order_by(SyncSession.created_at.desc())`

### 问题识别
1. **缺少统一的排序参数**: 只有 logs.py 实现了排序参数
2. **排序字段验证缺失**: 没有验证 sort_by 是否为有效字段
3. **排序方向验证缺失**: 没有验证 sort_order 是否为 asc/desc

## 4. 时间范围参数

### 当前实现情况

#### logs.py (日志查询)
```python
start_time = request.args.get("start_time")
end_time = request.args.get("end_time")
hours = request.args.get("hours")  # 相对时间
```

#### account_sync.py (同步记录)
```python
date_range = request.args.get("date_range", "all")
# 支持: "all", "today", "week", "month"
```

### 问题识别
1. **时间参数名称不统一**:
   - `start_time` + `end_time` (绝对时间)
   - `hours` (相对时间)
   - `date_range` (预设范围)

2. **时间格式验证不统一**:
   - logs.py 使用 `datetime.fromisoformat()`
   - 缺少统一的时间格式验证

3. **时间范围优先级不明确**:
   - hours 和 start_time/end_time 同时存在时的处理逻辑不一致

## 5. 数据库类型参数

### 当前实现情况

#### account.py
```python
@account_bp.route("/")
@account_bp.route("/<db_type>")
def list_accounts(db_type: str | None = None):
    # db_type 从路由路径获取
    if db_type and db_type != "all":
        query = query.filter(CurrentAccountSyncData.db_type == db_type)
```

#### account.py (导出功能)
```python
db_type = request.args.get("db_type", type=str)
```

### 问题识别
1. **参数来源不统一**: 
   - 有的从路由路径获取 `/<db_type>`
   - 有的从查询参数获取 `?db_type=mysql`

2. **缺少类型验证**: 没有验证 db_type 是否为有效的数据库类型


## 6. 完整对比表

| 路由 | 分页方式 | 默认per_page | 搜索参数 | 排序参数 | 时间参数 | 其他过滤 |
|------|---------|-------------|---------|---------|---------|---------|
| account.py | page+per_page | 20 | search | ❌ | ❌ | instance_id, is_locked, is_superuser, plugin, tags, classification |
| logs.py | page+per_page | 50 | q | sort_by, sort_order | start_time, end_time, hours | level, module |
| account_sync.py | page+per_page | 20 | ❌ | ❌ | date_range | sync_type, status |
| users.py | page+per_page | 10 | search | ❌ | ❌ | role, status |
| sync_sessions.py | page+per_page | 20 | ❌ | ❌ | ❌ | sync_type, sync_category, status |
| logs.py (错误日志) | limit | 50 | ❌ | ❌ | hours | level |
| logs.py (导出) | limit | 1000 | ❌ | ❌ | start_time, end_time | level, module |
| logs.py (实时) | limit | 20 | ❌ | ❌ | ❌ | level |

## 7. 统一标准建议

### 7.1 分页参数标准
```python
# 推荐标准
page = request.args.get("page", 1, type=int)
per_page = request.args.get("per_page", 20, type=int)

# 统一默认值
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100  # 防止过大查询

# 验证逻辑
if page < 1:
    page = 1
if per_page < 1 or per_page > MAX_PER_PAGE:
    per_page = DEFAULT_PER_PAGE
```

### 7.2 搜索参数标准
```python
# 推荐使用 "search" 作为通用搜索参数
search = request.args.get("search", "").strip()

# 或者使用 "q" (更简短，RESTful风格)
q = request.args.get("q", "").strip()

# 建议: 统一使用 "search"，更语义化
```

### 7.3 排序参数标准
```python
# 推荐标准
sort_by = request.args.get("sort_by", "created_at")
sort_order = request.args.get("sort_order", "desc")

# 验证逻辑
VALID_SORT_FIELDS = ["id", "created_at", "updated_at", "name"]
VALID_SORT_ORDERS = ["asc", "desc"]

if sort_by not in VALID_SORT_FIELDS:
    sort_by = "created_at"
if sort_order not in VALID_SORT_ORDERS:
    sort_order = "desc"
```

### 7.4 时间范围参数标准
```python
# 推荐标准 - 支持多种方式
# 方式1: 绝对时间
start_time = request.args.get("start_time")  # ISO 8601格式
end_time = request.args.get("end_time")

# 方式2: 相对时间
hours = request.args.get("hours", type=int)  # 最近N小时
days = request.args.get("days", type=int)    # 最近N天

# 方式3: 预设范围
date_range = request.args.get("date_range")  # today, week, month, quarter, year

# 优先级: start_time/end_time > hours/days > date_range > 默认24小时
```

### 7.5 布尔值参数标准
```python
# 推荐使用统一的布尔值转换函数
def parse_bool_param(value: str | None, default: bool = False) -> bool:
    """统一的布尔值参数解析"""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")

# 使用示例
is_active = parse_bool_param(request.args.get("is_active"))
is_locked = parse_bool_param(request.args.get("is_locked"))
```


## 8. 需要统一的具体问题

### 8.1 高优先级问题

#### 问题1: 分页默认值不统一
**现状**:
- users.py: per_page=10
- account.py: per_page=20
- logs.py: per_page=50

**建议**: 统一为 per_page=20

**影响范围**:
- app/routes/users.py (1处)
- app/routes/logs.py (1处)

#### 问题2: 搜索参数名不统一
**现状**:
- account.py, users.py: 使用 "search"
- logs.py: 使用 "q"

**建议**: 统一使用 "search"

**影响范围**:
- app/routes/logs.py (多处)
- 前端JS文件可能需要同步修改

#### 问题3: 类型转换方式不统一
**现状**:
- 方式1: `request.args.get("page", 1, type=int)` ✓
- 方式2: `int(request.args.get("page", 1))` ✗

**建议**: 统一使用方式1，更安全

**影响范围**:
- app/routes/logs.py (多处)
- app/routes/sync_sessions.py (多处)

#### 问题4: 布尔值处理不统一
**现状**:
- 直接获取字符串，后续判断 `== "true"`
- 没有统一的转换函数

**建议**: 创建统一的 `parse_bool_param()` 函数

**影响范围**:
- app/routes/account.py (is_locked, is_superuser)
- app/routes/users.py (status_filter)
- 其他需要布尔值参数的地方

### 8.2 中优先级问题

#### 问题5: 缺少排序参数
**现状**: 只有 logs.py 实现了排序参数

**建议**: 为主要列表接口添加排序参数

**影响范围**:
- app/routes/account.py
- app/routes/users.py
- app/routes/sync_sessions.py

#### 问题6: 时间参数不统一
**现状**:
- logs.py: start_time, end_time, hours
- account_sync.py: date_range

**建议**: 统一支持多种时间参数方式

**影响范围**:
- app/routes/account_sync.py
- 其他需要时间过滤的接口

#### 问题7: 硬编码的limit
**现状**:
- account.py: `.limit(50)`, `.limit(10)`
- 无法通过参数控制

**建议**: 改为可配置的参数

**影响范围**:
- app/routes/account.py (变更日志、同步记录查询)

### 8.3 低优先级问题

#### 问题8: 缺少参数验证
**现状**: 大部分参数没有验证

**建议**: 添加参数验证逻辑
- 分页参数范围验证
- 排序字段白名单验证
- 时间格式验证
- 枚举值验证

#### 问题9: 缺少统一的参数解析工具
**现状**: 每个路由都重复写参数解析代码

**建议**: 创建统一的参数解析工具类


## 9. 实施建议

### 9.1 分阶段实施

#### 第一阶段: 创建统一工具 (不影响现有功能)
1. 创建 `app/utils/query_params.py`
2. 实现统一的参数解析函数:
   - `parse_pagination_params()` - 分页参数
   - `parse_bool_param()` - 布尔值参数
   - `parse_sort_params()` - 排序参数
   - `parse_time_range_params()` - 时间范围参数
3. 添加单元测试

#### 第二阶段: 逐步迁移 (按优先级)
1. 先迁移简单的路由 (users.py)
2. 再迁移复杂的路由 (account.py, logs.py)
3. 最后迁移其他路由

#### 第三阶段: 清理旧代码
1. 删除重复的参数解析代码
2. 统一默认值配置
3. 更新文档

### 9.2 工具函数示例

```python
# app/utils/query_params.py

from typing import Any
from flask import request

# 默认配置
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

def parse_pagination_params() -> tuple[int, int]:
    """解析分页参数"""
    page = request.args.get("page", DEFAULT_PAGE, type=int)
    per_page = request.args.get("per_page", DEFAULT_PER_PAGE, type=int)
    
    # 验证
    if page < 1:
        page = DEFAULT_PAGE
    if per_page < 1 or per_page > MAX_PER_PAGE:
        per_page = DEFAULT_PER_PAGE
    
    return page, per_page

def parse_bool_param(key: str, default: bool = False) -> bool:
    """解析布尔值参数"""
    value = request.args.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")

def parse_sort_params(
    valid_fields: list[str],
    default_field: str = "created_at",
    default_order: str = "desc"
) -> tuple[str, str]:
    """解析排序参数"""
    sort_by = request.args.get("sort_by", default_field)
    sort_order = request.args.get("sort_order", default_order)
    
    # 验证
    if sort_by not in valid_fields:
        sort_by = default_field
    if sort_order not in ("asc", "desc"):
        sort_order = default_order
    
    return sort_by, sort_order

def parse_search_param() -> str:
    """解析搜索参数"""
    return request.args.get("search", "").strip()
```

### 9.3 迁移示例

#### 迁移前 (users.py)
```python
page = request.args.get("page", 1, type=int)
per_page = request.args.get("per_page", 10, type=int)
search = request.args.get("search", "", type=str)
```

#### 迁移后 (users.py)
```python
from app.utils.query_params import (
    parse_pagination_params,
    parse_search_param
)

page, per_page = parse_pagination_params()
search = parse_search_param()
```

## 10. 总结

### 主要发现
1. **分页参数**: 基本统一使用 page+per_page，但默认值不一致
2. **搜索参数**: 参数名不统一 (search vs q)
3. **类型转换**: 方式不统一，存在安全隐患
4. **布尔值**: 缺少统一的转换函数
5. **排序参数**: 大部分接口缺失
6. **时间参数**: 实现方式差异大

### 统一收益
1. **代码复用**: 减少重复代码
2. **一致性**: 提升API一致性
3. **可维护性**: 集中管理参数逻辑
4. **安全性**: 统一的验证和错误处理
5. **文档化**: 更容易生成API文档

### 风险评估
- **低风险**: 创建新工具函数
- **中风险**: 修改默认值 (需要测试)
- **高风险**: 修改参数名 (需要前后端同步)

### 建议优先级
1. ✅ 创建统一工具函数 (立即执行)
2. ✅ 统一类型转换方式 (高优先级)
3. ✅ 统一布尔值处理 (高优先级)
4. ⚠️ 统一默认值 (中优先级，需测试)
5. ⚠️ 统一搜索参数名 (中优先级，需前端配合)
6. 📋 添加排序参数 (低优先级，功能增强)
