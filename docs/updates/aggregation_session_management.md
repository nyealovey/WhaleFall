# 聚合定时任务会话管理集成

## 概述
为"统计聚合"定时任务添加了会话管理支持，使其能够在会话中心显示和管理。

## 修改内容

### 1. 数据库更新
- **文件**: `sql/init_postgresql.sql`
- **修改**: 在同步会话表和同步实例记录表的CHECK约束中添加了`'aggregation'`分类
- **影响**: 新部署的数据库将直接支持aggregation分类

### 2. 后端代码更新

#### 模型更新
- **文件**: `app/models/sync_session.py`
- **修改**: 更新了同步分类的文档注释，添加了aggregation分类

#### 服务更新
- **文件**: `app/services/sync_session_service.py`
- **修改**: 更新了同步分类的文档注释，添加了aggregation分类

#### 任务更新
- **文件**: `app/tasks/database_size_aggregation_tasks.py`
- **修改**: 完全重写了`calculate_database_size_aggregations()`函数
- **新增功能**:
  - 创建同步会话
  - 添加实例记录
  - 按周期类型分别处理（daily, weekly, monthly, quarterly）
  - 详细的日志记录和状态跟踪
  - 错误处理和会话状态管理

### 3. 前端代码更新

#### 统一搜索组件
- **文件**: `app/templates/components/unified_search_form.html`
- **修改**: 在同步分类筛选中添加了`aggregation`选项

#### 会话管理页面
- **文件**: `app/static/js/pages/sync_sessions/management.js`
- **修改**: 更新了`getSyncCategoryText()`函数，添加了中文显示名称映射
- **新增**: `aggregation` → `统计聚合`

## 功能特性

### 会话管理
- 聚合任务现在会在会话中心显示为"统计聚合"分类
- 支持实时进度跟踪
- 详细的实例记录和错误日志

### 任务执行流程
1. **创建会话** - 生成唯一的会话ID
2. **添加实例记录** - 为每个活跃实例创建记录
3. **按周期处理** - 分别计算daily、weekly、monthly、quarterly聚合
4. **更新状态** - 实时更新实例记录和会话状态
5. **完成会话** - 标记会话为completed或failed

### 日志记录
- 使用结构化日志记录所有操作
- 支持按模块过滤（aggregation_sync）
- 详细的错误信息和堆栈跟踪

## 数据库迁移

### 现有数据库更新
对于已经部署的数据库，需要执行以下SQL语句：

```sql
-- 更新同步会话表的约束
ALTER TABLE sync_sessions 
DROP CONSTRAINT IF EXISTS sync_sessions_sync_category_check;

ALTER TABLE sync_sessions 
ADD CONSTRAINT sync_sessions_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 更新同步实例记录表的约束
ALTER TABLE sync_instance_records 
DROP CONSTRAINT IF EXISTS sync_instance_records_sync_category_check;

ALTER TABLE sync_instance_records 
ADD CONSTRAINT sync_instance_records_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 添加注释
COMMENT ON COLUMN sync_sessions.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
COMMENT ON COLUMN sync_instance_records.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
```

### 新数据库部署
新部署的数据库将直接使用更新后的`init_postgresql.sql`文件，自动包含aggregation分类支持。

## 测试验证

### 功能测试
1. 启动应用后，检查定时任务是否正确创建
2. 在会话中心查看是否有"统计聚合"分类的筛选选项
3. 等待聚合任务执行，验证会话是否正确创建和更新

### 数据验证
1. 检查`sync_sessions`表中是否有`sync_category='aggregation'`的记录
2. 验证会话状态是否正确更新
3. 检查实例记录是否包含详细的聚合信息

## 注意事项

1. **向后兼容**: 现有的会话记录不会受到影响
2. **性能影响**: 聚合任务现在会创建更多的数据库记录，但影响很小
3. **日志增加**: 由于添加了详细的日志记录，日志量会有所增加
4. **错误处理**: 增强了错误处理机制，失败的任务会在会话中显示具体错误信息

## 相关文件

- `sql/init_postgresql.sql` - 数据库初始化脚本
- `sql/add_aggregation_sync_category.sql` - 现有数据库更新脚本
- `app/tasks/database_size_aggregation_tasks.py` - 聚合任务实现
- `app/models/sync_session.py` - 同步会话模型
- `app/services/sync_session_service.py` - 同步会话服务
- `app/templates/components/unified_search_form.html` - 统一搜索组件
- `app/static/js/pages/sync_sessions/management.js` - 会话管理页面脚本
