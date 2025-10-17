# 时间与时区 & 日志枚举统一整改方案（无兼容，强制版）

本方案基于《日志与错误处理统一方案（无过渡兼容，强制版）》的配套改造，采用"无过渡兼容"策略，强制统一：
- 模型时间字段的时区一致性与存储策略统一
- 日志级别枚举 `LogLevel` 的统一来源，彻底消除重复定义
- 时间处理函数统一，删除所有兼容函数，强制使用标准方式
- 时间格式常量统一，删除重复定义，强制使用统一常量

## 1. 目标与策略
- 强制统一时间字段时区语义：所有模型时间列使用 `db.DateTime(timezone=True)`，按 UTC 存储，展示层按需转换
- 彻底消除 `LogLevel` 重复定义：仅保留 `app/constants/system_constants.py` 中的枚举，移除其他位置的重复定义
- 统一时间序列化格式：API 响应统一使用 `datetime.isoformat()`，前端显示统一转换为中国时区

## 2. 现状分析
### 时间字段现状
- **已统一的模型**：大部分模型已使用 `db.DateTime(timezone=True)`，包括：
  - `app/models/unified_log.py`：完全符合规范
  - `app/models/instance.py`：所有时间字段已带时区
  - `app/models/credential.py`：所有时间字段已带时区
  - `app/models/user.py`：所有时间字段已带时区
  - 其他大部分模型均已符合规范
- **待修复的模型**：
  - `app/models/global_param.py`：`created_at` 和 `updated_at` 字段缺少 `timezone=True`

### 日志级别枚举现状
- **重复定义位置**：
  - `app/constants/system_constants.py`：标准定义（保留）
  - `app/models/unified_log.py`：重复定义（需移除）
- **引用位置**：
  - `app/utils/structlog_config.py`：从 `unified_log` 导入（需修改）
  - `app/routes/dashboard.py`：从 `unified_log` 导入（需修改）
  - `app/routes/logs.py`：从 `unified_log` 导入（需修改）

## 3. 问题与风险
- **时间字段不一致**：`global_param.py` 中的时间列缺少时区信息，可能导致序列化、显示或范围查询偏移
- **枚举重复定义**：`LogLevel` 在多处定义可能造成枚举比较失败或值不一致，影响筛选与统计
- **导入依赖混乱**：多个模块从 `unified_log` 导入 `LogLevel`，违反了单一来源原则
- **时间显示不一致**：部分地方可能存在时区转换不统一的问题

## 4. 统一策略与原则（无兼容，强制版）
### 时间字段统一
- **模型层**：所有时间列强制使用 `db.DateTime(timezone=True)`，默认值与更新值统一使用 `time_utils.now`（UTC）
- **存储层**：一律按 UTC 入库，不在数据库中做隐式本地化
- **展示层**：统一使用 `time_utils.format_china_time()` 显示中国时区，API 序列化统一使用 `datetime.isoformat()`

### 日志级别枚举统一
- **唯一来源**：`from app.constants.system_constants import LogLevel`
- **模型绑定**：`SQLEnum(LogLevel, name="log_level")`，移除本地重复枚举定义
- **引用统一**：所有模块（路由、工具、日志处理器）统一从 `app.constants` 导入枚举

### 时间处理函数统一
- **唯一入口**：强制使用 `time_utils.method()` 方式，删除所有兼容函数
- **标准调用**：`time_utils.now()`, `time_utils.now_china()`, `time_utils.to_china()`, `time_utils.format_china_time()`
- **禁止使用**：删除并禁止使用 `utc_to_china()`, `get_china_time()`, `now()` 等兼容函数

### 时间格式常量统一
- **唯一来源**：`from app.constants.system_constants import TimeFormats`
- **标准引用**：`TimeFormats.DATETIME_FORMAT`, `TimeFormats.ISO_FORMAT` 等
- **删除重复**：删除 `time_utils.py` 中的 `TIME_FORMATS` 字典

## 5. 强制修复清单
### 必须修改的文件
1. **`app/models/global_param.py`**
   - 将 `created_at` 和 `updated_at` 改为 `db.DateTime(timezone=True)`
   - 保持现有的默认值和 `onupdate` 设置

2. **`app/models/unified_log.py`**
   - 移除本地 `LogLevel` 枚举定义
   - 改为 `from app.constants.system_constants import LogLevel`
   - 保持 `SQLEnum(LogLevel, name="log_level")` 的使用

3. **`app/utils/structlog_config.py`**
   - 移除从 `app.models.unified_log` 导入 `LogLevel`
   - 改为 `from app.constants.system_constants import LogLevel`
   - 确保 DEBUG 级别仅控制台输出，INFO+ 才入库（现状已符合）

4. **`app/routes/dashboard.py`**
   - 移除从 `app.models.unified_log` 导入 `LogLevel`
   - 改为 `from app.constants.system_constants import LogLevel`

5. **`app/routes/logs.py`**
   - 移除从 `app.models.unified_log` 导入 `LogLevel`
   - 改为 `from app.constants.system_constants import LogLevel`

6. **`app/constants/system_constants.py`**
   - 在 `TimeFormats` 类中添加缺少的 `DATETIME_MS_FORMAT = "%Y-%m-%d %H:%M:%S.%f"`
   - 确保所有时间格式常量完整定义

7. **`app/utils/time_utils.py`**
   - 添加 `from app.constants.system_constants import TimeFormats`
   - **删除** `TIME_FORMATS` 字典，强制使用 `TimeFormats` 类
   - **删除所有兼容函数**：`utc_to_china()`, `get_china_time()`, `now()`, `format_china_time()`, `china_to_utc()`, `get_china_date()`, `get_china_today()`, `get_china_tomorrow()`
   - 修改 `TimeUtils` 类方法使用统一常量

8. **修改所有使用兼容函数的文件**
   - `app/routes/logs.py`：替换 `utc_to_china()` 为 `time_utils.to_china()`
   - `app/routes/main.py`：替换 `get_china_time()` 为 `time_utils.now_china()`
   - `app/models/unified_log.py`：替换 `now()` 为 `time_utils.now()`
   - `app/routes/connections.py`：替换 `now()` 为 `time_utils.now()`
   - `app/__init__.py`：替换 `format_china_time()` 为 `time_utils.format_china_time()`

## 6. 分步实施计划与修复逻辑

### 修复逻辑总览
1. **优先级原则**：先修复数据库层面的时区问题，再处理应用层的枚举和时间处理
2. **兼容性原则**：保持向后兼容，避免破坏现有功能
3. **渐进式原则**：分阶段执行，每个阶段都有明确的验证标准
4. **统一性原则**：所有时间处理统一使用 `time_utils`，所有枚举统一从 `constants` 导入

### 第一阶段：基础设施修复（优先级：高）
**目标**：修复数据库时区问题、枚举重复定义、常量统一、函数调用统一

1. **修复 `global_param.py` 时间字段**
   - 将 `created_at` 和 `updated_at` 改为 `db.DateTime(timezone=True)`
   - 保持原有的 `nullable`、`default`、`onupdate`、`comment` 属性
   - 创建对应的 Alembic 迁移脚本

2. **LogLevel 枚举统一**
   - 在 `app/models/unified_log.py` 中移除本地 `LogLevel` 枚举定义
   - 添加 `from app.constants.system_constants import LogLevel`
   - 确保 `SQLEnum(LogLevel, name="log_level")` 正常工作

3. **统一所有 LogLevel 引用位置**
   - 修改 `app/utils/structlog_config.py` 的导入
   - 修改 `app/routes/dashboard.py` 的导入
   - 修改 `app/routes/logs.py` 的导入
   - 确保所有位置都从 `app.constants.system_constants` 导入

4. **时间格式常量统一**
   - 完善 `app/constants/system_constants.py` 中的 `TimeFormats` 类
   - 添加缺少的 `DATETIME_MS_FORMAT` 常量
   - 修改 `app/utils/time_utils.py` 引用统一常量
   - **删除** `TIME_FORMATS` 字典，强制使用 `TimeFormats` 类

5. **删除所有兼容函数并修改调用代码**
   - 删除 `app/utils/time_utils.py` 中所有兼容函数
   - 修改 `app/routes/logs.py`: `utc_to_china()` → `time_utils.to_china()`
   - 修改 `app/routes/main.py`: `get_china_time()` → `time_utils.now_china()`
   - 修改 `app/models/unified_log.py`: `now()` → `time_utils.now()`
   - 修改 `app/__init__.py`: `format_china_time()` → `time_utils.format_china_time()`

**验证标准**：
- 数据库迁移成功执行
- 日志系统正常工作
- 所有 LogLevel 引用统一
- 时间格式常量统一，所有代码使用 `TimeFormats` 类
- 所有兼容函数删除，代码使用标准 `time_utils.method()` 方式

### 第二阶段：直接 datetime 使用修复（优先级：中）
**目标**：替换所有直接使用 datetime 的代码，统一使用 time_utils

**修复策略**：
1. **路由层修复**
   - `app/routes/dashboard.py`: 替换 `datetime.now().date()` 
   - `app/routes/scheduler.py`: 替换 `datetime.strptime()`
   - `app/routes/database_stats.py`: 统一日期解析
   - `app/routes/partition.py`: 统一分区日期处理

2. **服务层修复**
   - `app/services/sync_session_service.py`: 统一同步时间处理
   - `app/services/database_size_aggregation_service.py`: 统一聚合时间计算
   - `app/services/account_classification_service.py`: 统一时间解析
   - `app/services/partition_management_service.py`: 统一分区时间计算

**修复原则**：
- 优先使用 `time_utils.now()` 和 `time_utils.now_china()`
- 时间解析统一使用 `time_utils` 提供的方法
- 保持现有业务逻辑不变，只替换时间获取和处理方式

### 第三阶段：时间格式化统一（优先级：中）
**目标**：统一所有时间格式化操作

**修复范围**：
1. **导出功能时间格式化**
   - `app/routes/instances.py`: 实例导出时间格式
   - `app/routes/account.py`: 账户导出时间格式
   - `app/routes/logs.py`: 日志导出时间格式

2. **显示时间格式化**
   - `app/routes/account_sync.py`: 同步记录时间显示
   - `app/routes/dashboard.py`: 仪表板时间标签
   - `app/routes/partition.py`: 分区统计时间显示

**修复方法**：
- 替换 `.strftime()` 调用为 `time_utils.format_china_time()`
- 统一时间格式常量的使用
- 确保所有用户界面显示的时间都是中国时区

### 第四阶段：time_utils 优化（优先级：低）
**目标**：清理 time_utils.py 中的重复代码（暂不执行，保持兼容性）

**发现的问题**：
1. 功能重复：`utc_to_china()` 和 `TimeUtils.to_china()` 功能相同
2. 命名不一致：`china_to_utc()` vs `to_utc()`
3. 向后兼容函数过多：增加维护成本

**长期优化方案**：
1. 推荐使用 `time_utils.method()` 方式而非独立函数
2. 在后续重构中逐步迁移旧函数名到统一命名
3. 减少不必要的向后兼容函数

### 第五阶段：验证与测试（优先级：高）
**功能验证**：
1. 验证日志系统正常工作，LogLevel 枚举正确
2. 验证时间显示正确，时区转换一致
3. 验证枚举比较和过滤功能正常
4. 验证导出功能时间格式正确

**回归测试**：
1. 运行相关单元测试
2. 测试 `/dashboard`、`/logs`、`/instances` 等关键路径
3. 验证数据库迁移正常执行
4. 测试前端时间显示是否正确

## 7. 数据迁移设计
### PostgreSQL 数据库迁移
针对 `global_params` 表的时间字段修复，需要执行以下 SQL 语句：

```sql
-- 修复 global_params 表时间字段时区信息
-- 将 created_at 和 updated_at 字段改为支持时区的类型

-- 修改 created_at 字段为 TIMESTAMP WITH TIME ZONE
ALTER TABLE global_params 
ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;

-- 修改 updated_at 字段为 TIMESTAMP WITH TIME ZONE  
ALTER TABLE global_params 
ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

-- 验证修改结果
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'global_params' 
AND column_name IN ('created_at', 'updated_at');
```

### 回滚 SQL（如需要）
```sql
-- 回滚到普通 TIMESTAMP（不带时区）
ALTER TABLE global_params ALTER COLUMN created_at TYPE TIMESTAMP;
ALTER TABLE global_params ALTER COLUMN updated_at TYPE TIMESTAMP;
```

### 历史数据处理
- 现有数据假设为 UTC 时间（符合系统设计）
- 枚举统一不影响数据库存储，仅影响应用层引用

## 8. 代码变更示例与修复逻辑

### 8.1 时间字段修复
```python
# 修改前 (app/models/global_param.py)
created_at = db.Column(db.DateTime, default=now, comment="创建时间")
updated_at = db.Column(db.DateTime, default=now, onupdate=now, comment="更新时间")

# 修改后
created_at = db.Column(db.DateTime(timezone=True), default=now, comment="创建时间")
updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, comment="更新时间")
```

### 8.2 LogLevel 枚举统一
```python
# 修改前 (app/models/unified_log.py)
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# 修改后 - 移除重复定义
from app.constants.system_constants import LogLevel

# 修改前 (app/utils/structlog_config.py)
from app.models.unified_log import LogLevel, UnifiedLog

# 修改后 - 统一导入来源
from app.constants.system_constants import LogLevel
from app.models.unified_log import UnifiedLog
```

### 8.3 time_utils.py 重复代码和常量统一

**发现的重复问题**：
1. **功能重复**：多个函数实现相同功能但命名不同
2. **向后兼容函数过多**：增加维护成本
3. **命名不一致**：`utc_to_china` vs `to_china`
4. **常量重复定义**：时间格式常量在两个地方定义

**兼容函数使用情况分析**：
```python
# 被使用的兼容函数（需要保留）
utc_to_china()      # 被 app/routes/logs.py, app/models/unified_log.py 使用
get_china_time()    # 被 app/routes/main.py 使用
now()              # 被 app/models/unified_log.py, app/routes/connections.py 使用
format_china_time() # 被 app/__init__.py 模板过滤器大量使用

# 未被使用的兼容函数（可以删除）
china_to_utc()      # 无使用，可删除
get_china_date()    # 无使用，可删除
get_china_today()   # 无使用，可删除
get_china_tomorrow() # 无使用，可删除
```

**常量重复问题**：
```python
# app/constants/system_constants.py 中已有定义
class TimeFormats:
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    CHINESE_DATETIME_FORMAT = "%Y年%m月%d日 %H:%M:%S"
    CHINESE_DATE_FORMAT = "%Y年%m月%d日"

# app/utils/time_utils.py 中重复定义
TIME_FORMATS = {
    "datetime": "%Y-%m-%d %H:%M:%S",
    "date": "%Y-%m-%d",
    "time": "%H:%M:%S",
    "datetime_ms": "%Y-%m-%d %H:%M:%S.%f",  # system_constants 中缺少
    "iso": "%Y-%m-%dT%H:%M:%S.%fZ",
    "display": "%Y年%m月%d日 %H:%M:%S",
}
```

**修复逻辑（无兼容，强制版）**：
```python
# 1. 统一时间格式常量到 system_constants.py
class TimeFormats:
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    DATETIME_MS_FORMAT = "%Y-%m-%d %H:%M:%S.%f"  # 新增
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    CHINESE_DATETIME_FORMAT = "%Y年%m月%d日 %H:%M:%S"
    CHINESE_DATE_FORMAT = "%Y年%m月%d日"

# 2. time_utils.py 中引用统一常量，删除重复定义
from app.constants.system_constants import TimeFormats
# 删除 TIME_FORMATS 字典

# 3. 修改 TimeUtils 类使用统一常量
def format_china_time(dt, format_str: str = TimeFormats.DATETIME_FORMAT):
    # 使用统一常量

# 4. 删除所有兼容函数（无兼容）
# - 删除 utc_to_china()
# - 删除 get_china_time()
# - 删除 now()
# - 删除 format_china_time()
# - 删除 china_to_utc()
# - 删除 get_china_date()
# - 删除 get_china_today()
# - 删除 get_china_tomorrow()

# 5. 修改所有使用兼容函数的代码
# app/routes/logs.py: utc_to_china() -> time_utils.to_china()
# app/routes/main.py: get_china_time() -> time_utils.now_china()
# app/models/unified_log.py: now() -> time_utils.now()
# app/__init__.py: format_china_time() -> time_utils.format_china_time()
```

### 8.4 兼容函数调用修改
```python
# 修改前 (app/routes/logs.py)
from app.utils.time_utils import utc_to_china
china_time = utc_to_china(log.timestamp)

# 修改后
from app.utils.time_utils import time_utils
china_time = time_utils.to_china(log.timestamp)

# 修改前 (app/routes/main.py)
from app.utils.time_utils import get_china_time
"timestamp": get_china_time().isoformat()

# 修改后
from app.utils.time_utils import time_utils
"timestamp": time_utils.now_china().isoformat()

# 修改前 (app/models/unified_log.py)
from app.utils.time_utils import now, utc_to_china

# 修改后
from app.utils.time_utils import time_utils
```

### 8.5 时间格式常量修改
```python
# 修改前 (app/utils/time_utils.py)
TIME_FORMATS = {
    "datetime": "%Y-%m-%d %H:%M:%S",
    "date": "%Y-%m-%d",
    # ...
}
def format_china_time(dt, format_str: str = TIME_FORMATS["datetime"]):

# 修改后
from app.constants.system_constants import TimeFormats
def format_china_time(dt, format_str: str = TimeFormats.DATETIME_FORMAT):

# 修改前 (其他文件使用 TIME_FORMATS)
from app.utils.time_utils import TIME_FORMATS
format_str = TIME_FORMATS["datetime"]

# 修改后
from app.constants.system_constants import TimeFormats
format_str = TimeFormats.DATETIME_FORMAT
```

### 8.6 直接 datetime 使用修复
```python
# 修改前 (app/routes/dashboard.py)
from datetime import datetime, timedelta
recent_date = datetime.now().date() - timedelta(days=7)

# 修改后
from app.utils.time_utils import time_utils
recent_date = time_utils.now_china().date() - timedelta(days=7)

# 修改前 (app/routes/instances.py)
instance.last_connected.strftime("%Y-%m-%d %H:%M:%S")

# 修改后
from app.constants.system_constants import TimeFormats
time_utils.format_china_time(instance.last_connected, TimeFormats.DATETIME_FORMAT)
```

## 9. 自动化检测脚本
### 残留问题搜索命令
```bash
# 检查未带时区的时间列
rg -n "db\.DateTime," app/models

# 检查重复的 LogLevel 枚举定义
rg -n "class LogLevel\(Enum\)" app/

# 检查从 unified_log 导入 LogLevel 的位置
rg -n "from app\.models\.unified_log import.*LogLevel" app/

# 检查是否还有其他枚举重复定义
rg -n "from app\.utils\.logging_config import.*LogLevel" app/
```

### 验证脚本
```bash
#!/bin/bash
# 验证修复完成情况

echo "检查时间字段修复情况..."
if rg -q "db\.DateTime," app/models/global_param.py; then
    echo "❌ global_param.py 仍有未修复的时间字段"
    exit 1
else
    echo "✅ global_param.py 时间字段已修复"
fi

echo "检查 LogLevel 枚举统一情况..."
if rg -q "class LogLevel\(Enum\)" app/models/unified_log.py; then
    echo "❌ unified_log.py 仍有重复的 LogLevel 定义"
    exit 1
else
    echo "✅ unified_log.py LogLevel 重复定义已移除"
fi

if rg -q "from app\.models\.unified_log import.*LogLevel" app/; then
    echo "❌ 仍有模块从 unified_log 导入 LogLevel"
    exit 1
else
    echo "✅ 所有 LogLevel 导入已统一"
fi

echo "✅ 所有检查通过"
```

## 10. 测试与验收标准
### 功能测试
- **时间处理测试**
  - 验证 `global_param.py` 的时间字段正确保存和显示
  - 验证时区转换功能正常工作
  - 验证 API 响应中的时间格式统一

- **日志系统测试**
  - 验证日志记录功能正常
  - 验证 `LogLevel` 枚举比较和过滤正常
  - 验证日志查询和统计功能

### 验收指标
- 所有检测脚本返回通过状态
- 相关单元测试全部通过
- 手动测试关键功能正常
- 数据库迁移成功执行

## 11. 风险控制与回滚策略
### 主要风险
- **数据库迁移风险**：时间字段类型变更可能影响现有数据
- **枚举引用风险**：LogLevel 导入变更可能导致运行时错误
- **时区显示风险**：时间转换逻辑变更可能影响前端显示

### 缓解措施
- 在测试环境充分验证所有变更
- 分阶段执行，先修复枚举引用，再处理时间字段
- 保留详细的回滚脚本和步骤

### 回滚策略
- **数据库回滚**：使用 Alembic downgrade 恢复字段类型
- **代码回滚**：通过 Git 回滚到变更前的提交
- **验证回滚**：确保回滚后系统功能正常

## 12. 执行时间估算
- **时间字段修复**：0.5 天（包括迁移脚本编写和测试）
- **LogLevel 枚举统一**：0.5 天（包括所有引用位置修改）
- **测试与验证**：1 天（包括功能测试和回归测试）
- **总计**：2 天

## 13. 关联文档
- 《日志与错误处理统一方案（无过渡兼容，强制版）》：`docs/refactoring/error_handling_unification.md`
- 《时区处理规范》：`docs/development/timezone_handling.md`（如存在）

## 14. 涉及文件清单与修复优先级

### 第一阶段：必须修改的文件（高优先级）
**数据库模型修复**：
- `app/models/global_param.py`：修复时间字段时区问题

**LogLevel 枚举统一**：
- `app/models/unified_log.py`：移除重复 LogLevel 枚举定义
- `app/utils/structlog_config.py`：修改 LogLevel 导入来源
- `app/routes/dashboard.py`：修改 LogLevel 导入来源
- `app/routes/logs.py`：修改 LogLevel 导入来源

**时间格式常量统一**：
- `app/constants/system_constants.py`：完善 TimeFormats 类，添加缺少的常量
- `app/utils/time_utils.py`：引用统一的时间格式常量，删除重复的 TIME_FORMATS 字典

**兼容函数删除和调用修改**：
- `app/utils/time_utils.py`：删除所有兼容函数
- `app/routes/logs.py`：修改函数调用
- `app/routes/main.py`：修改函数调用
- `app/models/unified_log.py`：修改函数调用
- `app/routes/connections.py`：修改函数调用
- `app/__init__.py`：修改模板过滤器函数调用

### 第二阶段：直接 datetime 使用修复（中优先级）
**路由层文件**：
- `app/routes/dashboard.py`：替换 `datetime.now().date()` 使用
- `app/routes/scheduler.py`：替换 `datetime.strptime()` 使用
- `app/routes/database_stats.py`：统一日期解析方法
- `app/routes/partition.py`：统一分区日期处理

**服务层文件**：
- `app/services/sync_session_service.py`：统一同步时间处理
- `app/services/database_size_aggregation_service.py`：统一聚合时间计算
- `app/services/account_classification_service.py`：统一时间解析方法
- `app/services/partition_management_service.py`：统一分区时间计算
- `app/services/cache_manager.py`：统一缓存时间处理

### 第三阶段：时间格式化统一（中优先级）
**导出功能相关**：
- `app/routes/instances.py`：统一实例导出时间格式化
- `app/routes/account.py`：统一账户导出时间格式化
- `app/routes/logs.py`：统一日志导出时间格式化

**显示功能相关**：
- `app/routes/account_sync.py`：统一同步记录时间显示
- `app/routes/partition.py`：统一分区统计时间显示

### 第四阶段：前端和任务优化（低优先级）
**前端文件**：
- `app/static/js/common/time-utils.js`：优化前端时间处理
- `app/static/js/common/console-utils.js`：统一性能监控时间
- `app/static/js/pages/history/sync_sessions.js`：优化时间差计算
- `app/static/js/pages/accounts/account_classification.js`：统一时间显示

**任务模块**：
- `app/tasks/database_size_aggregation_tasks.py`：统一聚合任务时间
- `app/tasks/database_size_collection_tasks.py`：统一收集任务时间
- `app/tasks/partition_management_tasks.py`：统一分区任务时间

### 需要创建的文件
- `migrations/versions/xxx_fix_global_params_timezone.py`：数据库迁移脚本

### 参考文件（会修改但保持兼容性）
- `app/constants/system_constants.py`：标准枚举和常量定义来源，需要完善 TimeFormats
- `app/utils/time_utils.py`：时间处理工具，需要统一常量引用但保持向后兼容

### 强制修改的文件（无兼容策略）
- 所有使用兼容函数的文件都必须修改为标准调用方式
- 不保留任何向后兼容性，强制使用统一的时间处理方式

### 必须删除的内容
- `time_utils.py` 中所有兼容函数：`utc_to_china()`, `get_china_time()`, `now()`, `format_china_time()`, `china_to_utc()`, `get_china_date()`, `get_china_today()`, `get_china_tomorrow()`
- `time_utils.py` 中的 `TIME_FORMATS` 字典

### 文件修改风险评估
**高风险**：
- `app/models/unified_log.py`：移除枚举定义可能影响日志系统
- `app/models/global_param.py`：数据库字段修改需要迁移脚本

**中风险**：
- 所有路由文件：时间处理修改可能影响用户界面显示
- 服务层文件：时间计算修改可能影响业务逻辑

**低风险**：
- 导入语句修改：只要枚举值一致，风险较低
- 时间格式化修改：主要影响显示格式，不影响核心功能