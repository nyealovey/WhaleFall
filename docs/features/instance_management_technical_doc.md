# 实例管理功能技术文档

## 功能概述

实例管理功能是鲸落系统的核心基础功能，负责管理数据库实例的创建、编辑、删除、连接测试、容量同步等操作。支持MySQL、PostgreSQL、SQL Server、Oracle等多种数据库类型。

## 技术架构

### 1. 前端架构

#### 1.1 HTML模板文件
- **主模板**: `app/templates/instances/list.html`
  - 实例列表页面主模板
  - 包含搜索筛选、批量操作、标签管理等功能
  - 继承自 `base.html` 基础模板

- **创建模板**: `app/templates/instances/create.html`
  - 实例创建表单页面
  - 包含数据库类型选择、连接参数配置等

- **编辑模板**: `app/templates/instances/edit.html`
  - 实例编辑表单页面
  - 预填充现有实例数据

- **详情模板**: `app/templates/instances/detail.html`
  - 实例详情展示页面
  - 包含实例信息、账户列表、统计图表等

#### 1.2 JavaScript文件
- **主页面脚本**: `app/static/js/pages/instances/list.js`
  - 实例列表页面交互逻辑
  - 连接测试、容量同步、批量操作等功能
  - 标签选择器集成

- **创建页面脚本**: `app/static/js/pages/instances/create.js`
  - 实例创建表单验证和提交
  - 数据库类型切换逻辑

- **编辑页面脚本**: `app/static/js/pages/instances/edit.js`
  - 实例编辑表单处理
  - 数据预填充和验证

- **详情页面脚本**: `app/static/js/pages/instances/detail.js`
  - 实例详情页面交互
  - 账户列表管理、统计图表展示

- **统计页面脚本**: `app/static/js/pages/instances/statistics.js`
  - 实例统计页面功能
  - 图表渲染和数据分析

#### 1.3 CSS样式文件
- **主样式**: `app/static/css/pages/instances/list.css`
  - 实例列表页面样式
  - 卡片布局、状态指示器、批量操作按钮等

- **通用组件样式**: `app/static/css/components/`
  - `tag_selector.css`: 标签选择器组件样式
  - `unified_search.css`: 统一搜索组件样式

### 2. 后端架构

#### 2.1 数据模型
- **主模型**: `app/models/instance.py`
  - `Instance` 类：数据库实例模型
  - 包含实例基本信息、连接参数、版本信息等
  - 支持软删除、标签关联、凭据关联

#### 2.2 路由控制器
- **主路由**: `app/routes/instances.py`
  - 实例管理相关API接口
  - 包含CRUD操作、连接测试、容量同步等

#### 2.3 服务层
- **连接测试服务**: `app/services/connection_test_service.py`
  - 数据库连接测试逻辑
  - 支持多种数据库类型的连接验证

- **数据库大小采集服务**: `app/services/database_size_collector_service.py`
  - 实例容量数据采集
  - 支持MySQL、SQL Server、PostgreSQL、Oracle

- **同步数据管理器**: `app/services/sync_data_manager.py`
  - 统一同步数据管理
  - 适配器模式支持多种数据库类型

- **连接工厂**: `app/services/connection_factory.py`
  - 数据库连接创建工厂
  - 统一连接接口和生命周期管理

#### 2.4 工具类
- **数据验证器**: `app/utils/data_validator.py`
  - 表单数据验证
  - 实例参数校验

- **安全工具**: `app/utils/security.py`
  - 数据清理和验证
  - 安全防护措施

- **版本解析器**: `app/utils/version_parser.py`
  - 数据库版本信息解析
  - 支持多种数据库版本格式

## 核心功能实现

### 1. 实例CRUD操作

#### 1.1 创建实例
**前端流程**:
```javascript
// 表单提交处理
function submitInstanceForm() {
    const formData = new FormData(document.getElementById('instanceForm'));
    
    fetch('/instances/create', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            window.location.href = '/instances/';
        } else {
            showAlert('danger', data.error);
        }
    });
}
```

**后端处理**:
```python
@instances_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
def create() -> str | Response:
    """创建实例"""
    if request.method == "POST":
        # 数据验证
        validator = DataValidator()
        validation_result = validator.validate_instance_data(request.form)
        
        if not validation_result["valid"]:
            flash(validation_result["error"], "error")
            return render_template("instances/create.html", form_data=request.form)
        
        # 创建实例
        instance = Instance(
            name=request.form["name"],
            db_type=request.form["db_type"],
            host=request.form["host"],
            port=int(request.form["port"]),
            database_name=request.form.get("database_name"),
            credential_id=request.form.get("credential_id") or None,
            description=request.form.get("description"),
        )
        
        db.session.add(instance)
        db.session.commit()
        
        flash("实例创建成功", "success")
        return redirect(url_for("instances.detail", instance_id=instance.id))
    
    return render_template("instances/create.html")
```

#### 1.2 实例列表查询
**前端搜索筛选**:
```javascript
// 搜索和筛选功能
function applyFilters() {
    const search = document.getElementById('search').value;
    const dbType = document.getElementById('db_type').value;
    const status = document.getElementById('status').value;
    const tags = document.getElementById('selected-tag-names').value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (dbType) params.append('db_type', dbType);
    if (status) params.append('status', status);
    if (tags) params.append('tags', tags);
    
    window.location.href = `/instances/?${params.toString()}`;
}
```

**后端查询逻辑**:
```python
@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    db_type = request.args.get("db_type", "", type=str)
    status = request.args.get("status", "", type=str)
    tags_str = request.args.get("tags", "")
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    # 构建查询
    query = Instance.query

    if search:
        query = query.filter(
            db.or_(
                Instance.name.contains(search),
                Instance.host.contains(search),
                Instance.description.contains(search),
            )
        )

    if db_type:
        query = query.filter(Instance.db_type == db_type)
    
    if status:
        if status == 'active':
            query = query.filter(Instance.is_active == True)
        elif status == 'inactive':
            query = query.filter(Instance.is_active == False)

    # 标签筛选
    if tags:
        query = query.join(Instance.tags).filter(Tag.name.in_(tags))

    # 分页查询
    instances = query.order_by(Instance.id).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template("instances/list.html", instances=instances)
```

### 2. 连接测试功能





### 3. 容量同步功能

#### 3.1 前端容量同步
```javascript
function syncCapacity(instanceId, instanceName) {
    const btn = event.target.closest('button');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    fetch(`/instances/api/instances/${instanceId}/sync-capacity`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            // 刷新页面以更新容量显示
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        showAlert('danger', '同步容量失败');
    })
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}
```

#### 3.2 后端容量同步
```python
@instances_bp.route("/api/instances/<int:instance_id>/sync-capacity", methods=["POST"])
@login_required
@view_required
def sync_instance_capacity(instance_id: int) -> Response:
    """同步实例容量"""
    instance = Instance.query.get_or_404(instance_id)
    
    try:
        # 使用数据库大小采集服务
        with DatabaseSizeCollectorService(instance) as collector:
            # 采集数据库大小数据
            data = collector.collect_database_sizes()
            
            # 保存数据
            saved_count = collector.save_collected_data(data)
            
            return jsonify({
                "success": True,
                "message": f"容量同步成功，采集了 {saved_count} 条记录",
                "data": {
                    "saved_count": saved_count,
                    "instance_id": instance_id,
                    "instance_name": instance.name
                }
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"容量同步失败: {str(e)}"
        }), 500
```

### 4. 批量操作功能

#### 4.1 批量删除
```javascript
function batchDelete() {
    const selectedCheckboxes = document.querySelectorAll('.instance-checkbox:checked');
    const instanceIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

    if (instanceIds.length === 0) {
        showAlert('warning', '请选择要删除的实例');
        return;
    }

    if (!confirm(`确定要删除选中的 ${instanceIds.length} 个实例吗？此操作不可撤销！`)) {
        return;
    }

    const btn = document.getElementById('batchDeleteBtn');
    const originalText = btn.textContent;

    btn.textContent = '删除中...';
    btn.disabled = true;

    fetch('/instances/batch-delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ instance_ids: instanceIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        showAlert('danger', '批量删除失败');
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = true;
    });
}
```

#### 4.2 批量创建
```javascript
function submitBatchCreate() {
    const uploadMethod = document.querySelector('input[name="uploadMethod"]:checked');
    
    if (uploadMethod && uploadMethod.value === 'file') {
        submitFileUpload();
    } else {
        submitJsonInput();
    }
}

function submitFileUpload() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        showAlert('warning', '请选择CSV文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/instances/batch-create', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            if (data.errors && data.errors.length > 0) {
                showAlert('warning', `部分实例创建失败：\n${data.errors.join('\n')}`);
            }
            // 关闭模态框并刷新页面
            const modal = bootstrap.Modal.getInstance(document.getElementById('batchCreateModal'));
            if (modal) modal.hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        showAlert('danger', '批量创建失败');
    });
}
```

### 5. 标签管理功能

#### 5.1 标签选择器集成
```javascript
// 初始化标签选择器
function initializeInstanceListTagSelector() {
    const listPageSelector = document.getElementById('list-page-tag-selector');
    
    if (listPageSelector) {
        const modalElement = listPageSelector.querySelector('#tagSelectorModal');
        const containerElement = modalElement.querySelector('#tag-selector-container');
        
        if (containerElement) {
            // 初始化标签选择器组件
            listPageTagSelector = new TagSelector('tag-selector-container', {
                allowMultiple: true,
                allowCreate: true,
                allowSearch: true,
                allowCategoryFilter: true
            });
            
            // 设置事件监听
            setupTagSelectorEvents();
        }
    }
}

// 标签选择确认
function confirmTagSelection() {
    if (listPageTagSelector) {
        listPageTagSelector.confirmSelection();
        const selectedTags = listPageTagSelector.getSelectedTags();
        updateSelectedTagsPreview(selectedTags);
        closeTagSelector();
    }
}
```

## 数据库设计

### 1. 实例表结构
```sql
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    db_type VARCHAR(50) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(255),
    database_version VARCHAR(1000),
    main_version VARCHAR(20),
    detailed_version VARCHAR(50),
    environment VARCHAR(20) DEFAULT 'production',
    sync_count INTEGER DEFAULT 0,
    credential_id INTEGER REFERENCES credentials(id),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    is_active BOOLEAN DEFAULT TRUE,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

### 2. 实例标签关联表
```sql
CREATE TABLE instance_tags (
    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (instance_id, tag_id)
);
```

## API接口文档

### 1. 实例管理接口

#### 1.1 获取实例列表
- **URL**: `GET /instances/`
- **参数**:
  - `page`: 页码 (默认: 1)
  - `per_page`: 每页数量 (默认: 10)
  - `search`: 搜索关键词
  - `db_type`: 数据库类型筛选
  - `status`: 状态筛选 (active/inactive)
  - `tags`: 标签筛选 (逗号分隔)

#### 1.2 创建实例
- **URL**: `POST /instances/create`
- **参数**:
  - `name`: 实例名称 (必填)
  - `db_type`: 数据库类型 (必填)
  - `host`: 主机地址 (必填)
  - `port`: 端口号 (必填)
  - `database_name`: 数据库名称
  - `credential_id`: 凭据ID
  - `description`: 描述



#### 1.4 同步容量
- **URL**: `POST /instances/api/instances/{id}/sync-capacity`
- **返回**:
  ```json
  {
    "success": true,
    "message": "容量同步成功，采集了 5 条记录",
    "data": {
      "saved_count": 5,
      "instance_id": 1,
      "instance_name": "MySQL-01"
    }
  }
  ```

## 错误处理

### 1. 前端错误处理
```javascript
// 统一错误处理函数
function handleError(error, context) {
    console.error(`${context} 错误:`, error);
    
    // 显示用户友好的错误信息
    showAlert('danger', `${context}失败，请稍后重试`);
    
    // 记录错误日志
    logErrorWithContext(error, context, {
        operation: context,
        result: 'exception'
    });
}

// 网络请求错误处理
function handleFetchError(response, context) {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
}
```

### 2. 后端错误处理
```python
# 统一异常处理装饰器
def handle_instance_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except InstanceNotFoundError as e:
            return jsonify({"success": False, "error": "实例不存在"}), 404
        except ConnectionError as e:
            return jsonify({"success": False, "error": "数据库连接失败"}), 500
        except ValidationError as e:
            return jsonify({"success": False, "error": f"数据验证失败: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"实例操作异常: {str(e)}")
            return jsonify({"success": False, "error": "服务器内部错误"}), 500
    return decorated_function
```

## 性能优化

### 1. 数据库查询优化
- 使用索引优化查询性能
- 分页查询避免大量数据加载
- 预加载关联数据减少N+1查询

### 2. 前端性能优化
- 懒加载实例容量数据
- 防抖搜索避免频繁请求
- 缓存标签选择器数据

### 3. 连接池管理
- 使用连接池管理数据库连接
- 自动释放空闲连接
- 连接超时和重试机制

## 安全考虑

### 1. 输入验证
- 所有用户输入进行严格验证
- 防止SQL注入攻击
- 文件上传类型和大小限制

### 2. 权限控制
- 基于角色的访问控制
- 操作权限验证
- 敏感操作审计日志

### 3. 数据安全
- 密码等敏感信息加密存储
- 连接参数安全传输
- 定期清理过期数据

## 测试策略

### 1. 单元测试
- 模型方法测试
- 服务类功能测试
- 工具函数测试

### 2. 集成测试
- API接口测试
- 数据库操作测试
- 前后端交互测试

### 3. 性能测试
- 大量数据查询测试
- 并发操作测试
- 连接池压力测试

## 部署配置

### 1. 环境变量
```bash
# 数据库连接配置
DATABASE_URL=postgresql://user:password@localhost:5432/taifish

# 连接池配置
DB_POOL_SIZE=10
DB_POOL_OVERFLOW=20
DB_POOL_TIMEOUT=30

# 安全配置
SECRET_KEY=your-secret-key
CSRF_SECRET_KEY=your-csrf-secret-key
```

### 2. 依赖包
```txt
Flask==3.0.3
SQLAlchemy==1.4.54
psycopg2-binary==2.9.9
pymysql==1.1.0
pymssql==2.2.8
oracledb==1.4.2
```

## 监控和日志

### 1. 操作日志
- 实例创建、编辑、删除操作
- 连接测试结果记录
- 容量同步操作记录

### 2. 性能监控
- 数据库查询性能
- 连接池使用情况
- 页面加载时间

### 3. 错误监控
- 异常错误记录
- 连接失败统计
- 用户操作错误追踪

## 维护指南

### 1. 日常维护
- 定期清理软删除的实例
- 监控连接池状态
- 检查实例连接状态

### 2. 故障排查
- 查看错误日志定位问题
- 检查数据库连接配置
- 验证网络连通性

### 3. 性能调优
- 分析慢查询日志
- 优化数据库索引
- 调整连接池参数

---

**文档版本**: 1.0  
**最后更新**: 2025-01-28  
**维护人员**: 开发团队
