# 标签管理功能技术文档

## 功能概述

标签管理功能是鲸落系统中用于对数据库实例进行分类和标记的核心功能模块。该功能支持标签的创建、编辑、删除、批量分配等操作，并提供灵活的标签分类体系和搜索筛选功能。

## 技术架构

### 前端架构

#### 主要页面
- **标签管理首页** (`/tags/`)：标签列表展示、搜索筛选
- **标签创建页面** (`/tags/create`)：新建标签表单
- **标签编辑页面** (`/tags/edit/<id>`)：编辑标签信息
- **批量分配页面** (`/tags/batch_assign`)：批量为实例分配标签

#### 核心组件
- **TagSelector组件**：标签选择器，支持搜索、筛选、多选
- **UnifiedSearch组件**：统一搜索组件，支持标签筛选
- **BatchAssignManager**：批量分配管理器

#### JavaScript文件
```
app/static/js/
├── pages/tags/
│   ├── index.js                    # 标签管理主页逻辑
│   └── batch_assign.js             # 批量分配页面逻辑
├── components/
│   ├── tag_selector.js             # 标签选择器组件
│   └── unified_search.js           # 统一搜索组件
└── pages/instances/
    ├── list.js                     # 实例列表页标签功能
    └── edit.js                     # 实例编辑页标签功能
```

#### CSS样式文件
```
app/static/css/
├── pages/tags/
│   └── index.css                   # 标签管理页面样式
└── components/
    ├── tag_selector.css            # 标签选择器样式
    └── unified_search.css          # 统一搜索样式
```

### 后端架构

#### 路由定义
```python
# app/routes/tags.py
@tags_bp.route("/")                           # 标签管理首页
@tags_bp.route("/create")                     # 创建标签
@tags_bp.route("/edit/<int:tag_id>")          # 编辑标签
@tags_bp.route("/delete/<int:tag_id>")        # 删除标签
@tags_bp.route("/batch_assign")               # 批量分配页面
@tags_bp.route("/api/tags")                   # 获取标签列表API
@tags_bp.route("/api/all_tags")               # 获取所有标签API
@tags_bp.route("/api/categories")             # 获取标签分类API
@tags_bp.route("/api/instances")              # 获取实例列表API
@tags_bp.route("/api/batch_assign_tags")      # 批量分配标签API
```

#### 数据模型
```python
# app/models/tag.py
class Tag(db.Model):
    """标签模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)      # 标签代码
    display_name = db.Column(db.String(100), nullable=False)          # 显示名称
    category = db.Column(db.String(50), nullable=False)               # 标签分类
    color = db.Column(db.String(20), default="primary")               # 标签颜色
    description = db.Column(db.Text, nullable=True)                   # 描述
    sort_order = db.Column(db.Integer, default=0)                     # 排序顺序
    is_active = db.Column(db.Boolean, default=True)                   # 是否激活
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关系
    instances = db.relationship("Instance", secondary="instance_tags", back_populates="tags")

# 实例标签关联表
instance_tags = db.Table(
    'instance_tags',
    db.Column('instance_id', db.Integer, db.ForeignKey('instances.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('created_at', db.DateTime(timezone=True), default=now),
)
```

#### 业务逻辑层
标签管理功能主要通过路由层直接处理业务逻辑，没有独立的服务层。主要业务逻辑包括：
- 标签的CRUD操作
- 标签与实例的关联管理
- 标签分类和颜色管理
- 批量分配逻辑

## 核心功能实现

### 1. 标签管理

#### 标签列表展示
```python
# app/routes/tags.py - index()
def index() -> str:
    """标签管理首页"""
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status = request.args.get("status", "all", type=str)
    
    # 构建查询条件
    query = Tag.query
    if search:
        query = query.filter(db.or_(
            Tag.name.contains(search),
            Tag.display_name.contains(search),
            Tag.description.contains(search),
        ))
    if category:
        query = query.filter(Tag.category == category)
    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)
    
    # 排序和分页
    query = query.order_by(Tag.category, Tag.sort_order, Tag.name)
    tags = query.paginate(page=page, per_page=per_page, error_out=False)
```

#### 标签创建
```python
# app/routes/tags.py - create()
def create() -> str | Response:
    """创建标签"""
    if request.method == "POST":
        # 验证必填字段
        required_fields = ["name", "display_name", "category"]
        validation_error = validate_required_fields(request.form, required_fields)
        
        # 获取表单数据
        name = request.form.get("name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        category = request.form.get("category", "").strip()
        color = request.form.get("color", "primary").strip()
        description = request.form.get("description", "").strip()
        sort_order = request.form.get("sort_order", 0, type=int)
        is_active = request.form.get("is_active") == "on"
        
        # 检查名称唯一性
        existing_tag = Tag.query.filter_by(name=name).first()
        if existing_tag:
            flash(f"标签代码 '{name}' 已存在", "error")
            return render_template("tags/create.html")
        
        # 创建标签
        tag = Tag(
            name=name,
            display_name=display_name,
            category=category,
            color=color,
            description=description,
            sort_order=sort_order,
            is_active=is_active,
        )
        db.session.add(tag)
        db.session.commit()
```

#### 标签编辑
```python
# app/routes/tags.py - edit()
def edit(tag_id: int) -> str | Response:
    """编辑标签"""
    tag = Tag.query.get_or_404(tag_id)
    
    if request.method == "POST":
        # 验证必填字段
        required_fields = ["name", "display_name", "category"]
        validation_error = validate_required_fields(request.form, required_fields)
        
        # 获取表单数据并更新
        name = request.form.get("name", "").strip()
        # 检查名称唯一性（排除当前记录）
        existing_tag = Tag.query.filter(
            Tag.name == name,
            Tag.id != tag_id
        ).first()
        
        # 更新标签属性
        tag.name = name
        tag.display_name = display_name
        tag.category = category
        # ... 其他属性更新
        
        db.session.commit()
```

#### 标签删除
```python
# app/routes/tags.py - delete()
def delete(tag_id: int) -> Response:
    """删除标签"""
    tag = Tag.query.get_or_404(tag_id)
    
    # 检查是否有实例使用该标签
    instance_count = tag.instances.count()
    if instance_count > 0:
        flash(f"无法删除标签 '{tag.display_name}'，有 {instance_count} 个实例正在使用", "error")
        return redirect(url_for("tags.index"))
    
    # 硬删除标签
    db.session.delete(tag)
    db.session.commit()
```

### 2. 标签分类管理

#### 标签分类定义
```python
# app/models/tag.py - get_category_choices()
@staticmethod
def get_category_choices() -> list:
    """获取标签分类选项"""
    return [
        ("location", "地区标签"),
        ("company_type", "公司类型"),
        ("environment", "环境标签"),
        ("department", "部门标签"),
        ("project", "项目标签"),
        ("virtualization", "虚拟化类型"),
        ("deployment", "部署方式"),
        ("architecture", "架构类型"),
        ("other", "其他标签"),
    ]
```

#### 标签颜色管理
```python
# app/models/tag.py - get_color_choices()
@staticmethod
def get_color_choices() -> list:
    """获取颜色选项"""
    return [
        ("primary", "蓝色"),
        ("success", "绿色"),
        ("info", "青色"),
        ("warning", "黄色"),
        ("danger", "红色"),
        ("secondary", "灰色"),
        ("dark", "深色"),
        ("light", "浅色"),
    ]
```

### 3. 标签选择器组件

#### TagSelector类
```javascript
// app/static/js/components/tag_selector.js
class TagSelector {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            allowMultiple: true,
            showSearch: true,
            showCategories: true,
            showStats: true,
            maxSelections: null,
            onSelectionChange: null,
            onTagAdd: null,
            onTagRemove: null,
            ...options
        };
        
        this.selectedTags = new Set();
        this.allTags = [];
        this.filteredTags = [];
        this.currentCategory = 'all';
        this.searchQuery = '';
        
        this.init();
    }
    
    // 初始化标签选择器
    init() {
        this.loadTags();
        this.bindEvents();
        this.render();
    }
    
    // 加载标签数据
    async loadTags() {
        try {
            const response = await fetch('/tags/api/tags');
            const data = await response.json();
            if (data.success) {
                this.allTags = data.tags || [];
                this.filteredTags = [...this.allTags];
                this.renderTags();
                this.updateStats();
            }
        } catch (error) {
            console.error('Error loading tags:', error);
        }
    }
    
    // 处理搜索
    handleSearch(query) {
        this.searchQuery = query.toLowerCase();
        this.filterTags();
    }
    
    // 筛选标签
    filterTags() {
        this.filteredTags = this.allTags.filter(tag => {
            const matchesSearch = !this.searchQuery || 
                tag.name.toLowerCase().includes(this.searchQuery) ||
                tag.display_name.toLowerCase().includes(this.searchQuery);
            
            const matchesCategory = this.currentCategory === 'all' || 
                tag.category === this.currentCategory;
            
            return matchesSearch && matchesCategory;
        });
        
        this.renderTags();
    }
}
```

### 4. 批量分配功能

#### 批量分配管理器
```javascript
// app/static/js/pages/tags/batch_assign.js
class BatchAssignManager {
    constructor() {
        this.selectedInstances = new Set();
        this.selectedTags = new Set();
        this.allInstances = [];
        this.allTags = [];
        this.currentFilters = {
            dbType: '',
            search: '',
            status: 'all'
        };
        
        this.init();
    }
    
    // 初始化
    init() {
        this.loadInstances();
        this.loadTags();
        this.bindEvents();
    }
    
    // 执行批量分配
    async performBatchAssign() {
        if (this.selectedInstances.size === 0) {
            this.showAlert('warning', '请选择要分配标签的实例');
            return;
        }
        
        if (this.selectedTags.size === 0) {
            this.showAlert('warning', '请选择要分配的标签');
            return;
        }
        
        const instanceIds = Array.from(this.selectedInstances);
        const tagIds = Array.from(this.selectedTags);
        
        try {
            const response = await fetch('/tags/api/batch_assign_tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    instance_ids: instanceIds,
                    tag_ids: tagIds
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showAlert('success', `成功为 ${instanceIds.length} 个实例分配了 ${tagIds.length} 个标签`);
                this.clearSelections();
            } else {
                this.showAlert('danger', '批量分配失败: ' + data.error);
            }
        } catch (error) {
            this.showAlert('danger', '批量分配时出错: ' + error.message);
        }
    }
}
```

#### 批量分配API
```python
# app/routes/tags.py - batch_assign_tags()
@tags_bp.route("/api/batch_assign_tags", methods=["POST"])
@login_required
@create_required
def batch_assign_tags() -> Response:
    """批量分配标签给实例"""
    try:
        data = request.get_json()
        instance_ids = data.get("instance_ids", [])
        tag_ids = data.get("tag_ids", [])
        
        if not instance_ids or not tag_ids:
            return jsonify({"success": False, "error": "实例ID和标签ID不能为空"}), 400
        
        # 获取实例和标签
        instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        
        # 批量分配标签
        success_count = 0
        for instance in instances:
            for tag in tags:
                if tag not in instance.tags:
                    instance.tags.append(tag)
                    success_count += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"成功分配了 {success_count} 个标签关联",
            "assigned_count": success_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
```

### 5. API接口设计

#### 标签列表API
```python
# app/routes/tags.py - api_tags()
@tags_bp.route("/api/tags")
@login_required
@view_required
def api_tags() -> Response:
    """获取标签列表API"""
    try:
        category = request.args.get("category", "", type=str)
        if category:
            tags = Tag.get_tags_by_category(category)
        else:
            tags = Tag.get_active_tags()
        
        tags_data = [tag.to_dict() for tag in tags]
        
        return jsonify({
            "success": True,
            "tags": tags_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

#### 所有标签API
```python
# app/routes/tags.py - api_all_tags()
@tags_bp.route("/api/all_tags")
@login_required
@view_required
def api_all_tags() -> Response:
    """获取所有标签列表API (包括非活跃标签)"""
    try:
        tags = Tag.query.all()
        tags_data = [tag.to_dict() for tag in tags]
        
        # 获取分类名称映射
        category_choices = Tag.get_category_choices()
        category_names = dict(category_choices)
        
        return jsonify({
            "success": True, 
            "tags": tags_data,
            "category_names": category_names
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

#### 标签分类API
```python
# app/routes/tags.py - api_categories()
@tags_bp.route("/api/categories")
@login_required
@view_required
def api_categories() -> Response:
    """获取标签分类列表API"""
    try:
        categories = Tag.get_category_choices()
        return jsonify({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

## 前端交互流程

### 1. 标签管理页面交互
```javascript
// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTagsPage();
});

// 初始化标签管理页面
function initializeTagsPage() {
    initializeEventHandlers();
    initializeSearchForm();
    initializeTagActions();
}

// 搜索和筛选
function handleSearchSubmit(e, form) {
    e.preventDefault();
    const formData = new FormData(form);
    const params = new URLSearchParams(formData);
    window.location.href = `${form.action}?${params.toString()}`;
}

// 标签删除确认
function confirmDelete(tagId, tagName) {
    if (confirm(`确定要删除标签 "${tagName}" 吗？`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/tags/delete/${tagId}`;
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}
```

### 2. 标签选择器交互
```javascript
// 标签选择事件
handleTagSelection(tagId, isSelected) {
    if (isSelected) {
        this.selectedTags.add(tagId);
    } else {
        this.selectedTags.delete(tagId);
    }
    
    this.updateSelectedTagsDisplay();
    
    if (this.options.onSelectionChange) {
        this.options.onSelectionChange(Array.from(this.selectedTags));
    }
}

// 更新选中标签显示
updateSelectedTagsDisplay() {
    const selectedTagsContainer = this.container.querySelector('.selected-tags');
    if (!selectedTagsContainer) return;
    
    selectedTagsContainer.innerHTML = '';
    
    this.selectedTags.forEach(tagId => {
        const tag = this.allTags.find(t => t.id === tagId);
        if (tag) {
            const tagElement = this.createSelectedTagElement(tag);
            selectedTagsContainer.appendChild(tagElement);
        }
    });
}
```

### 3. 批量分配交互
```javascript
// 实例选择
handleInstanceSelection(instanceId, isSelected) {
    if (isSelected) {
        this.selectedInstances.add(instanceId);
    } else {
        this.selectedInstances.delete(instanceId);
    }
    
    this.updateSelectionInfo();
}

// 标签选择
handleTagSelection(tagId, isSelected) {
    if (isSelected) {
        this.selectedTags.add(tagId);
    } else {
        this.selectedTags.delete(tagId);
    }
    
    this.updateSelectionInfo();
}

// 更新选择信息
updateSelectionInfo() {
    const instanceCount = this.selectedInstances.size;
    const tagCount = this.selectedTags.size;
    
    document.getElementById('selectedInstancesCount').textContent = instanceCount;
    document.getElementById('selectedTagsCount').textContent = tagCount;
    
    const assignButton = document.getElementById('performAssign');
    assignButton.disabled = instanceCount === 0 || tagCount === 0;
}
```

## 数据库设计

### 标签表结构
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,           -- 标签代码
    display_name VARCHAR(100) NOT NULL,         -- 显示名称
    category VARCHAR(50) NOT NULL,              -- 标签分类
    color VARCHAR(20) DEFAULT 'primary',        -- 标签颜色
    description TEXT,                           -- 描述
    sort_order INTEGER DEFAULT 0,               -- 排序顺序
    is_active BOOLEAN DEFAULT TRUE,             -- 是否激活
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_category ON tags(category);
CREATE INDEX idx_tags_is_active ON tags(is_active);
```

### 实例标签关联表
```sql
CREATE TABLE instance_tags (
    instance_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (instance_id, tag_id),
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_instance_tags_instance_id ON instance_tags(instance_id);
CREATE INDEX idx_instance_tags_tag_id ON instance_tags(tag_id);
```

## 权限控制

### 路由权限装饰器
```python
# 查看权限
@tags_bp.route("/")
@login_required
@view_required
def index():
    pass

# 创建权限
@tags_bp.route("/create")
@login_required
@create_required
def create():
    pass

# 更新权限
@tags_bp.route("/edit/<int:tag_id>")
@login_required
@update_required
def edit(tag_id: int):
    pass

# 删除权限
@tags_bp.route("/delete/<int:tag_id>")
@login_required
@delete_required
def delete(tag_id: int):
    pass
```

### 前端权限控制
```html
<!-- 标签管理首页权限控制 -->
{% if current_user.role == 'admin' %}
<div>
    <a href="{{ url_for('tags.create') }}" class="btn btn-light">
        <i class="fas fa-plus me-2"></i>添加标签
    </a>
    <a href="{{ url_for('tags.batch_assign') }}" class="btn btn-light ms-2">
        <i class="fas fa-tasks me-2"></i>批量分配
    </a>
</div>
{% endif %}
```

## 错误处理

### 后端错误处理
```python
# 标签创建错误处理
try:
    # 检查名称唯一性
    existing_tag = Tag.query.filter_by(name=name).first()
    if existing_tag:
        flash(f"标签代码 '{name}' 已存在", "error")
        return render_template("tags/create.html")
    
    # 创建标签
    tag = Tag(...)
    db.session.add(tag)
    db.session.commit()
    
    log_info("标签创建成功", module="tags", tag_id=tag.id)
    flash("标签创建成功", "success")
    
except Exception as e:
    db.session.rollback()
    log_error("标签创建失败", module="tags", error=str(e))
    flash("标签创建失败，请重试", "error")
```

### 前端错误处理
```javascript
// API调用错误处理
async function loadTags() {
    try {
        this.showLoading();
        
        const response = await fetch('/tags/api/tags');
        if (!response.ok) {
            throw new Error('Failed to load tags');
        }
        
        const data = await response.json();
        if (data.success) {
            this.allTags = data.tags || [];
            this.renderTags();
        } else {
            throw new Error(data.message || 'Failed to load tags');
        }
    } catch (error) {
        console.error('Error loading tags:', error);
        this.showError('加载标签失败: ' + error.message);
    } finally {
        this.hideLoading();
    }
}
```

## 性能优化

### 数据库查询优化
```python
# 使用索引优化查询
query = Tag.query.filter_by(is_active=True)  # 使用is_active索引
query = query.filter(Tag.category == category)  # 使用category索引
query = query.order_by(Tag.category, Tag.sort_order, Tag.name)  # 复合排序
```

### 前端性能优化
```javascript
// 防抖搜索
const debouncedSearch = debounce((query) => {
    this.handleSearch(query);
}, 300);

// 虚拟滚动（大量标签时）
renderTags() {
    const visibleTags = this.getVisibleTags();
    const container = this.container.querySelector('.tags-list');
    container.innerHTML = '';
    
    visibleTags.forEach(tag => {
        const tagElement = this.createTagElement(tag);
        container.appendChild(tagElement);
    });
}
```

## 测试策略

### 单元测试
```python
# 测试标签模型
def test_tag_creation():
    tag = Tag(
        name="test_tag",
        display_name="测试标签",
        category="environment"
    )
    assert tag.name == "test_tag"
    assert tag.display_name == "测试标签"
    assert tag.is_active is True

# 测试标签查询
def test_get_active_tags():
    tags = Tag.get_active_tags()
    assert all(tag.is_active for tag in tags)
```

### 集成测试
```python
# 测试标签创建API
def test_create_tag_api(client, auth_headers):
    response = client.post('/tags/create', data={
        'name': 'test_tag',
        'display_name': '测试标签',
        'category': 'environment'
    }, headers=auth_headers)
    
    assert response.status_code == 302  # 重定向到列表页
    
    # 验证标签已创建
    tag = Tag.query.filter_by(name='test_tag').first()
    assert tag is not None
    assert tag.display_name == '测试标签'
```

### 前端测试
```javascript
// 测试标签选择器
describe('TagSelector', () => {
    let tagSelector;
    
    beforeEach(() => {
        document.body.innerHTML = '<div id="tag-selector"></div>';
        tagSelector = new TagSelector('tag-selector');
    });
    
    test('should initialize correctly', () => {
        expect(tagSelector.selectedTags.size).toBe(0);
        expect(tagSelector.allTags).toEqual([]);
    });
    
    test('should handle tag selection', () => {
        tagSelector.handleTagSelection(1, true);
        expect(tagSelector.selectedTags.has(1)).toBe(true);
    });
});
```

## 部署和维护

### 数据库迁移
```python
# 创建标签表迁移
def upgrade():
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_tags_name', 'tags', ['name'], unique=True)
    op.create_index('idx_tags_category', 'tags', ['category'], unique=False)
```

### 监控和日志
```python
# 标签操作日志
log_info(
    "标签创建成功",
    module="tags",
    tag_id=tag.id,
    name=tag.name,
    display_name=tag.display_name,
    category=tag.category,
    user_id=current_user.id
)

log_error(
    "标签删除失败",
    module="tags",
    tag_id=tag_id,
    error=str(e),
    user_id=current_user.id
)
```

## 扩展功能

### 标签统计
```python
# 标签使用统计
def get_tag_usage_stats():
    """获取标签使用统计"""
    stats = db.session.query(
        Tag.id,
        Tag.name,
        Tag.display_name,
        func.count(instance_tags.c.instance_id).label('usage_count')
    ).outerjoin(instance_tags).group_by(Tag.id).all()
    
    return [
        {
            'tag_id': stat.id,
            'name': stat.name,
            'display_name': stat.display_name,
            'usage_count': stat.usage_count
        }
        for stat in stats
    ]
```

### 标签导入导出
```python
# 标签导出
def export_tags():
    """导出标签配置"""
    tags = Tag.query.all()
    return {
        'tags': [tag.to_dict() for tag in tags],
        'export_time': datetime.now().isoformat()
    }

# 标签导入
def import_tags(data):
    """导入标签配置"""
    for tag_data in data.get('tags', []):
        existing_tag = Tag.query.filter_by(name=tag_data['name']).first()
        if not existing_tag:
            tag = Tag(**tag_data)
            db.session.add(tag)
    
    db.session.commit()
```

## 总结

标签管理功能是鲸落系统中的重要组成部分，提供了完整的标签生命周期管理能力。该功能具有以下特点：

1. **完整的CRUD操作**：支持标签的创建、查看、编辑、删除
2. **灵活的分类体系**：支持多种标签分类和颜色管理
3. **强大的搜索筛选**：支持按名称、分类、状态等多维度筛选
4. **批量操作能力**：支持批量为实例分配标签
5. **组件化设计**：提供可复用的标签选择器组件
6. **完善的权限控制**：基于角色的访问控制
7. **良好的用户体验**：响应式设计，支持移动端访问

通过合理的架构设计和实现，标签管理功能为数据库实例的分类和管理提供了强有力的支持。
