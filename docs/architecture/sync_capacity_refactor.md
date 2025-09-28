# 同步容量功能重构方案

## 当前问题

现在的"同步容量"功能混合了两个不同的职责：
1. 发现实例中的数据库列表
2. 采集每个数据库的大小信息

这导致功能职责不清晰，难以维护。

## 重构方案

### 1. 功能拆分

#### 1.1 同步数据库 (Sync Databases)
- **目的**：发现和更新实例中的数据库列表
- **职责**：
  - 连接到数据库实例
  - 获取所有数据库名称列表
  - 更新 `instance_databases` 表
  - 标记新发现的数据库
  - 检测已删除的数据库

#### 1.2 同步数据库大小 (Sync Database Sizes)
- **目的**：采集每个数据库的大小信息
- **职责**：
  - 连接到数据库实例
  - 查询每个数据库的大小
  - 保存到 `database_size_stats` 表
  - 更新 `instance_size_stats` 表

### 2. API 设计

#### 2.1 同步数据库 API
```python
@storage_sync_bp.route("/instances/<int:instance_id>/sync-databases", methods=['POST'])
@login_required
@view_required
def sync_instance_databases(instance_id: int):
    """
    同步指定实例的数据库列表
    
    Returns:
        JSON: 同步结果，包含发现的数据库列表
    """
    # 1. 验证实例和凭据
    # 2. 连接到数据库实例
    # 3. 获取数据库列表
    # 4. 更新 instance_databases 表
    # 5. 检测已删除的数据库
    # 6. 返回结果
```

#### 2.2 同步数据库大小 API
```python
@storage_sync_bp.route("/instances/<int:instance_id>/sync-database-sizes", methods=['POST'])
@login_required
@view_required
def sync_database_sizes(instance_id: int):
    """
    同步指定实例的数据库大小信息
    
    Returns:
        JSON: 同步结果，包含大小统计信息
    """
    # 1. 验证实例和凭据
    # 2. 连接到数据库实例
    # 3. 查询每个数据库的大小
    # 4. 保存到 database_size_stats 表
    # 5. 更新 instance_size_stats 表
    # 6. 返回结果
```

#### 2.3 组合同步 API（可选）
```python
@storage_sync_bp.route("/instances/<int:instance_id>/sync-all", methods=['POST'])
@login_required
@view_required
def sync_instance_all(instance_id: int):
    """
    同步指定实例的所有信息（数据库列表 + 大小信息）
    
    Returns:
        JSON: 完整同步结果
    """
    # 1. 先同步数据库列表
    # 2. 再同步数据库大小
    # 3. 返回综合结果
```

### 3. 服务层设计

#### 3.1 数据库发现服务
```python
class DatabaseDiscoveryService:
    """数据库发现服务"""
    
    def __init__(self, instance: Instance):
        self.instance = instance
        self.logger = get_logger(__name__)
    
    def discover_databases(self) -> List[str]:
        """发现实例中的所有数据库"""
        # 根据数据库类型调用不同的发现方法
        if self.instance.db_type == 'mysql':
            return self._discover_mysql_databases()
        elif self.instance.db_type == 'postgresql':
            return self._discover_postgresql_databases()
        # ... 其他数据库类型
    
    def update_database_list(self, discovered_databases: List[str]) -> Dict[str, int]:
        """更新数据库列表到 instance_databases 表"""
        # 1. 获取当前数据库列表
        # 2. 比较发现的新数据库
        # 3. 标记已删除的数据库
        # 4. 添加新发现的数据库
        # 5. 返回统计信息
```

#### 3.2 数据库大小采集服务（现有）
```python
class DatabaseSizeCollectorService:
    """数据库大小采集服务（保持现有功能）"""
    
    def collect_database_sizes(self) -> List[Dict[str, Any]]:
        """采集数据库大小信息"""
        # 现有实现保持不变
    
    def save_collected_data(self, data: List[Dict[str, Any]]) -> int:
        """保存采集到的数据"""
        # 现有实现保持不变
```

### 4. 前端界面设计

#### 4.1 实例详情页面
```html
<!-- 快速操作区域 -->
<div class="quick-actions">
    <button id="syncDatabasesBtn" class="btn btn-primary">
        <i class="fas fa-database"></i> 同步数据库
    </button>
    <button id="syncSizesBtn" class="btn btn-success">
        <i class="fas fa-chart-pie"></i> 同步大小
    </button>
    <button id="syncAllBtn" class="btn btn-info">
        <i class="fas fa-sync"></i> 全部同步
    </button>
</div>
```

#### 4.2 JavaScript 处理
```javascript
// 同步数据库
function syncDatabases() {
    fetch(`/storage-sync/instances/${instanceId}/sync-databases`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`发现 ${data.databases_found} 个数据库，新增 ${data.databases_added} 个，删除 ${data.databases_deleted} 个`);
            loadDatabaseSizes(); // 刷新数据库列表
        } else {
            showError(data.error);
        }
    });
}

// 同步数据库大小
function syncDatabaseSizes() {
    fetch(`/storage-sync/instances/${instanceId}/sync-database-sizes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`成功同步 ${data.saved_count} 个数据库的大小信息`);
            loadDatabaseSizes(); // 刷新数据库列表
        } else {
            showError(data.error);
        }
    });
}
```

### 5. 定时任务设计

#### 5.1 数据库发现任务
```python
def sync_databases_task():
    """定时同步所有实例的数据库列表"""
    instances = Instance.query.filter_by(is_active=True).all()
    
    for instance in instances:
        try:
            discovery_service = DatabaseDiscoveryService(instance)
            databases = discovery_service.discover_databases()
            result = discovery_service.update_database_list(databases)
            
            logger.info(f"实例 {instance.name} 数据库同步完成: {result}")
        except Exception as e:
            logger.error(f"实例 {instance.name} 数据库同步失败: {str(e)}")
```

#### 5.2 数据库大小采集任务（现有）
```python
def collect_database_sizes_task():
    """定时采集所有实例的数据库大小"""
    # 现有实现保持不变
```

### 6. 实施步骤

1. **创建 instance_databases 表**
2. **创建 DatabaseDiscoveryService 服务**
3. **拆分现有同步容量 API**
4. **更新前端界面和 JavaScript**
5. **创建新的定时任务**
6. **更新文档和测试**

### 7. 优势

1. **职责清晰**：每个功能都有明确的职责
2. **灵活性强**：可以独立执行数据库发现或大小采集
3. **易于维护**：功能分离后更容易调试和维护
4. **性能优化**：可以只同步需要的部分
5. **用户体验**：用户可以根据需要选择同步内容

这样的重构将使系统更加模块化和易于维护。
