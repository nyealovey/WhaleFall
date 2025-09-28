# 数据库关系架构解决方案

## 问题分析

### 当前架构问题
1. **缺少实例-数据库关系表**：没有一张表来维护"实例包含哪些数据库"的关系
2. **删除状态不明确**：`database_size_stats` 表中的 `is_deleted` 字段只是标记数据是否被删除，而不是数据库是否被删除
3. **显示逻辑混乱**：前端"显示已删除数据库"功能无法正确实现，因为无法区分哪些数据库是真正被删除的

### 现有数据结构
- `database_size_stats` - 存储每个数据库的历史大小数据
- `instance_size_stats` - 存储实例级别的汇总统计  
- `instances` - 存储实例基本信息

## 解决方案

### 1. 创建实例-数据库关系表

创建 `instance_databases` 表来维护实例和数据库的关系，并记录数据库的状态变化。

```sql
-- 创建实例-数据库关系表
CREATE TABLE IF NOT EXISTS instance_databases (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_date DATE NOT NULL DEFAULT CURRENT_DATE,
    last_seen_date DATE NOT NULL DEFAULT CURRENT_DATE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 唯一约束：一个实例中的数据库名称唯一
    UNIQUE(instance_id, database_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_instance_databases_instance_id ON instance_databases (instance_id);
CREATE INDEX IF NOT EXISTS ix_instance_databases_database_name ON instance_databases (database_name);
CREATE INDEX IF NOT EXISTS ix_instance_databases_active ON instance_databases (is_active);
CREATE INDEX IF NOT EXISTS ix_instance_databases_last_seen ON instance_databases (last_seen_date);
```

### 2. 创建对应的数据模型

```python
# app/models/instance_database.py
class InstanceDatabase(db.Model):
    """实例-数据库关系模型"""
    
    __tablename__ = "instance_databases"
    
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    database_name = db.Column(db.String(255), nullable=False, comment="数据库名称")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="数据库是否活跃（未删除）")
    first_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="首次发现日期")
    last_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="最后发现日期")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, nullable=False)
    
    # 关系
    instance = db.relationship("Instance", back_populates="instance_databases")
    
    __table_args__ = (
        db.UniqueConstraint("instance_id", "database_name", name="uq_instance_database_instance_name"),
        db.Index("ix_instance_databases_database_name", "database_name"),
        db.Index("ix_instance_databases_active", "is_active"),
        db.Index("ix_instance_databases_last_seen", "last_seen_date"),
    )
```

### 3. 更新数据采集服务

修改 `DatabaseSizeCollectorService` 的 `save_collected_data` 方法，在保存数据库大小数据时同步更新 `instance_databases` 表：

```python
def save_collected_data(self, data: List[Dict[str, Any]]) -> int:
    """保存采集到的数据库大小数据，同时更新实例-数据库关系"""
    try:
        saved_count = 0
        collected_date = date.today()
        
        for item in data:
            # 保存数据库大小数据
            stat = DatabaseSizeStat(
                instance_id=self.instance.id,
                database_name=item['database_name'],
                size_mb=item['size_mb'],
                data_size_mb=item.get('data_size_mb', 0),
                log_size_mb=item.get('log_size_mb'),
                collected_date=collected_date,
                collected_at=item.get('collected_at', datetime.utcnow()),
                is_deleted=False
            )
            db.session.add(stat)
            
            # 更新实例-数据库关系
            InstanceDatabase.update_database_status(
                self.instance.id, 
                item['database_name'], 
                collected_date
            )
            
            saved_count += 1
        
        db.session.commit()
        return saved_count
        
    except Exception as e:
        db.session.rollback()
        self.logger.error(f"保存数据库大小数据失败: {str(e)}")
        raise
```

### 4. 修改API接口

更新 `get_instance_database_sizes` API，支持按数据库状态过滤：

```python
@storage_sync_bp.route("/instances/<int:instance_id>/database-sizes", methods=['GET'])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int):
    """获取指定实例的数据库大小历史数据"""
    try:
        # 获取查询参数
        show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
        latest_only = request.args.get('latest_only', 'false').lower() == 'true'
        
        # 获取实例信息
        instance = Instance.query.get_or_404(instance_id)
        
        # 构建查询
        query = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.instance_id == instance_id
        )
        
        # 如果只需要最新数据，则只返回每个数据库的最新记录
        if latest_only:
            from sqlalchemy import func
            latest_dates_subquery = db.session.query(
                DatabaseSizeStat.database_name,
                func.max(DatabaseSizeStat.collected_date).label('latest_date')
            ).filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.is_deleted == False
            ).group_by(DatabaseSizeStat.database_name).subquery()
            
            query = query.join(
                latest_dates_subquery,
                (DatabaseSizeStat.database_name == latest_dates_subquery.c.database_name) &
                (DatabaseSizeStat.collected_date == latest_dates_subquery.c.latest_date)
            )
        
        # 根据是否显示已删除数据库来过滤
        if not show_deleted:
            # 只显示活跃的数据库
            active_databases = db.session.query(InstanceDatabase.database_name).filter(
                InstanceDatabase.instance_id == instance_id,
                InstanceDatabase.is_active == True
            ).subquery()
            
            query = query.filter(
                DatabaseSizeStat.database_name.in_(
                    db.session.query(active_databases.c.database_name)
                )
            )
        
        # 排序和分页
        query = query.order_by(desc(DatabaseSizeStat.collected_date))
        stats = query.all()
        
        # 格式化数据
        data = []
        for stat in stats:
            # 获取数据库状态
            instance_db = InstanceDatabase.query.filter_by(
                instance_id=instance_id,
                database_name=stat.database_name
            ).first()
            
            data.append({
                'id': stat.id,
                'database_name': stat.database_name,
                'size_mb': stat.size_mb,
                'data_size_mb': stat.data_size_mb,
                'log_size_mb': stat.log_size_mb,
                'collected_date': stat.collected_date.isoformat(),
                'collected_at': stat.collected_at.isoformat(),
                'is_active': instance_db.is_active if instance_db else True,
                'deleted_at': instance_db.deleted_at.isoformat() if instance_db and instance_db.deleted_at else None
            })
        
        # 从 instance_size_stats 表获取总容量信息
        latest_instance_stat = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False
        ).order_by(InstanceSizeStat.collected_date.desc()).first()
        
        total_size_mb = latest_instance_stat.total_size_mb if latest_instance_stat else 0
        database_count = latest_instance_stat.database_count if latest_instance_stat else 0
        
        return jsonify({
            'data': data,
            'total_size_mb': total_size_mb,
            'database_count': database_count,
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库大小数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
```

### 5. 创建数据库状态检测任务

创建定时任务来检测已删除的数据库：

```python
# app/tasks/database_status_tasks.py
def detect_deleted_databases_task():
    """检测并标记已删除的数据库"""
    try:
        from app.models.instance_database import InstanceDatabase
        
        instances = Instance.query.filter_by(is_active=True).all()
        total_deleted = 0
        
        for instance in instances:
            deleted_count = InstanceDatabase.detect_deleted_databases(instance.id)
            total_deleted += deleted_count
            
            if deleted_count > 0:
                logger.info(f"实例 {instance.name} 检测到 {deleted_count} 个已删除的数据库")
        
        logger.info(f"数据库状态检测完成，共标记 {total_deleted} 个已删除的数据库")
        
    except Exception as e:
        logger.error(f"检测已删除数据库失败: {str(e)}")
```

### 6. 更新前端显示逻辑

修改前端JavaScript，支持显示已删除数据库的切换：

```javascript
// 在实例详情页面添加切换功能
function toggleDeletedDatabases(showDeleted) {
    const url = `/storage-sync/instances/${instanceId}/database-sizes?latest_only=true&show_deleted=${showDeleted}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.data && Array.isArray(data.data)) {
                const totalSize = data.total_size_mb || 0;
                displayDatabaseSizes(data.data, totalSize);
            } else {
                displayDatabaseSizesError(data.error || '加载失败');
            }
        })
        .catch(error => {
            console.error('加载数据库容量信息失败:', error);
            displayDatabaseSizesError('网络错误，请稍后重试');
        });
}
```

## 实施步骤

1. **创建数据库表**：执行 `create_instance_databases_table.sql`
2. **创建模型文件**：创建 `app/models/instance_database.py`
3. **更新现有模型**：在 `app/models/instance.py` 中添加关系
4. **修改数据采集服务**：更新 `DatabaseSizeCollectorService`
5. **更新API接口**：修改 `get_instance_database_sizes` API
6. **创建检测任务**：添加数据库状态检测定时任务
7. **更新前端逻辑**：修改JavaScript支持显示已删除数据库

## 优势

1. **清晰的数据关系**：明确维护实例和数据库的关系
2. **准确的状态管理**：能够正确区分活跃和已删除的数据库
3. **完整的历史记录**：保留数据库的首次发现和最后发现时间
4. **灵活的查询**：支持按状态过滤数据库列表
5. **自动化检测**：定时任务自动检测已删除的数据库

这个解决方案将彻底解决当前架构中数据库关系不明确的问题，使"显示已删除数据库"功能能够正确工作。
