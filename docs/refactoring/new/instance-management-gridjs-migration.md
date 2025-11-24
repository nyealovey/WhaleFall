# 实例管理页面 Grid.js 迁移方案

> 将实例管理列表从传统 Bootstrap Table 升级为基于 Grid.js + GridWrapper 的统一实现，参考凭据管理页面的最佳实践。

## 1. 迁移目标
- 统一分页、排序、筛选逻辑，支持服务端数据源
- 前后端交互使用 `/instances/api/instances` REST 接口，响应格式包含 `items`, `total`, `page`, `pages`
- 表格列渲染支持自定义 HTML（使用 `gridjs.html`）
- 保留现有批量操作、标签筛选、连接测试等核心功能
- 移除传统分页 HTML，由 GridWrapper 接管分页控制

## 2. 通用资产引用
- **脚本与样式**
  - `app/static/vendor/gridjs/gridjs.umd.js`
  - `app/static/vendor/gridjs/mermaid.min.css`
  - `app/static/js/common/grid-wrapper.js`（禁止擅自修改）
- **模板引用**：在 `templates/instances/list.html` 中添加
  ```html
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/gridjs/mermaid.min.css') }}">
  <script src="{{ url_for('static', filename='vendor/gridjs/gridjs.umd.js') }}"></script>
  <script src="{{ url_for('static', filename='js/common/grid-wrapper.js') }}"></script>
  ```

## 3. 后端接口改造

### 3.1 新增 API 端点
在 `app/routes/instance.py` 中新增：
```python
@instance_bp.route('/api/instances', methods=['GET'])
@login_required
def api_list_instances():
    """实例列表 API - 支持分页、排序、筛选"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')
    
    # 筛选参数
    search = request.args.get('search', '').strip()
    db_type = request.args.get('db_type', '').strip()
    status = request.args.get('status', '').strip()
    tags = request.args.getlist('tags')
    
    # 构建查询
    query = Instance.query
    
    if search:
        query = query.filter(
            db.or_(
                Instance.name.ilike(f'%{search}%'),
                Instance.host.ilike(f'%{search}%')
            )
        )
    
    if db_type:
        query = query.filter(Instance.db_type == db_type)
    
    if status:
        is_active = status == 'active'
        query = query.filter(Instance.is_active == is_active)
    
    if tags:
        query = query.join(Instance.tags).filter(Tag.name.in_(tags))
    
    # 排序
    order_column = getattr(Instance, sort, Instance.id)
    if order == 'asc':
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    # 序列化数据
    items = []
    for instance in pagination.items:
        items.append({
            'id': instance.id,
            'name': instance.name,
            'db_type': instance.db_type,
            'host': instance.host,
            'main_version': instance.main_version,
            'is_active': instance.is_active,
            'tags': [{'name': tag.name, 'display_name': tag.display_name, 'color': tag.color} 
                     for tag in instance.tags.all()],
            'active_db_count': get_active_database_count(instance.id),
            'active_account_count': get_active_account_count(instance.id),
            'last_sync_time': get_last_sync_time(instance.id),
        })
    
    return jsonify({
        'success': True,
        'data': {
            'items': items,
            'total': pagination.total,
            'page': pagination.page,
            'pages': pagination.pages
        }
    })
```

### 3.2 路由命名规范
- **禁止使用** `api_list_instances` 作为函数名
- **正确命名**：`list_instances`（动词短语，无 `api_` 前后缀）
- 路由路径：`/instances/api/instances`（路径中可包含 `api`，但函数名不得带）

## 4. 前端脚本改造

### 4.1 Grid.js 初始化
在 `app/static/js/modules/views/instances/list.js` 中：

```javascript
let instancesGrid = null;

function initializeInstancesGrid() {
    const container = selectOne('#instances-grid').first();
    if (!container) {
        console.error('实例网格容器未找到');
        return;
    }
    
    instancesGrid = new global.GridWrapper(container, {
        columns: [
            {
                id: 'select',
                name: gridjs.html('<input type="checkbox" id="grid-select-all">'),
                width: '50px',
                sort: false,
                formatter: (cell, row) => {
                    const instanceId = row.cells[1].data;
                    return gridjs.html(
                        `<input type="checkbox" class="form-check-input instance-checkbox" value="${instanceId}">`
                    );
                }
            },
            { id: 'id', name: 'ID', hidden: true },
            {
                id: 'name',
                name: '名称',
                formatter: (cell) => gridjs.html(`
                    <div class="d-flex align-items-center">
                        <i class="fas fa-database text-primary me-2"></i>
                        <small class="text-muted">${cell}</small>
                    </div>
                `)
            },
            {
                id: 'db_type',
                name: '类型',
                formatter: (cell) => {
                    const config = DATABASE_TYPE_MAP[cell] || {};
                    return gridjs.html(`
                        <span class="badge bg-${config.color || 'secondary'}">
                            <i class="fas ${config.icon || 'fa-database'} me-1"></i>${config.display_name || cell.toUpperCase()}
                        </span>
                    `);
                }
            },
            {
                id: 'host',
                name: '主机',
                formatter: (cell) => gridjs.html(`<small class="text-muted">${cell}</small>`)
            },
            {
                id: 'main_version',
                name: '版本信息',
                formatter: (cell) => {
                    if (cell) {
                        return gridjs.html(`<span class="badge bg-primary">${cell}</span>`);
                    }
                    return gridjs.html('<small class="text-muted">未检测</small>');
                }
            },
            {
                id: 'active_counts',
                name: '活跃',
                sort: false,
                formatter: (cell, row) => {
                    const dbCount = row.cells[6].data || 0;
                    const accountCount = row.cells[7].data || 0;
                    return gridjs.html(`
                        <div class="d-flex align-items-center">
                            <span class="badge bg-primary me-2" style="min-width: 58px;">
                                <i class="fas fa-database me-1"></i>${dbCount}
                            </span>
                            <span class="badge bg-info text-white" style="min-width: 58px;">
                                <i class="fas fa-user me-1"></i>${accountCount}
                            </span>
                        </div>
                    `);
                }
            },
            { id: 'active_db_count', name: 'DB Count', hidden: true },
            { id: 'active_account_count', name: 'Account Count', hidden: true },
            {
                id: 'tags',
                name: '标签',
                sort: false,
                formatter: (cell) => {
                    if (!cell || cell.length === 0) {
                        return gridjs.html('<span class="text-muted">无标签</span>');
                    }
                    const badges = cell.map(tag => 
                        `<span class="badge bg-${tag.color} me-1 mb-1">
                            <i class="fas fa-tag me-1"></i>${tag.display_name}
                        </span>`
                    ).join('');
                    return gridjs.html(badges);
                }
            },
            {
                id: 'is_active',
                name: '状态',
                formatter: (cell) => {
                    if (cell) {
                        return gridjs.html('<span class="badge bg-success">正常</span>');
                    }
                    return gridjs.html('<span class="badge bg-danger">禁用</span>');
                }
            },
            {
                id: 'last_sync_time',
                name: '最后同步',
                formatter: (cell) => {
                    if (cell) {
                        return gridjs.html(`<small class="text-muted">${cell}</small>`);
                    }
                    return gridjs.html('<small class="text-muted">暂无同步记录</small>');
                }
            },
            {
                id: 'actions',
                name: '操作',
                sort: false,
                formatter: (cell, row) => {
                    const instanceId = row.cells[1].data;
                    const isAdmin = window.currentUserRole === 'admin';
                    
                    if (isAdmin) {
                        return gridjs.html(`
                            <div class="btn-group btn-group-sm" role="group">
                                <a href="/instances/${instanceId}/detail" class="btn btn-outline-primary" title="查看详情">
                                    <i class="fas fa-eye"></i>
                                </a>
                                <button type="button" class="btn btn-outline-warning" 
                                        data-action="edit-instance" data-instance-id="${instanceId}" title="编辑">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button type="button" class="btn btn-outline-success" 
                                        onclick="testConnection(${instanceId})" title="测试连接">
                                    <i class="fas fa-plug"></i>
                                </button>
                            </div>
                        `);
                    } else {
                        return gridjs.html(`
                            <div class="btn-group btn-group-sm" role="group">
                                <a href="/instances/${instanceId}/detail" class="btn btn-outline-primary" title="查看详情">
                                    <i class="fas fa-eye"></i>
                                </a>
                                <button type="button" class="btn btn-outline-success" 
                                        onclick="testConnection(${instanceId})" title="测试连接">
                                    <i class="fas fa-plug"></i>
                                </button>
                                <span class="btn btn-outline-secondary disabled" title="只读模式">
                                    <i class="fas fa-lock"></i>
                                </span>
                            </div>
                        `);
                    }
                }
            }
        ],
        server: {
            url: '/instances/api/instances?sort=id&order=desc',
            then: (response) => {
                const payload = response.data || response;
                const items = payload.items || [];
                return items.map(item => [
                    null, // select checkbox
                    item.id,
                    item.name,
                    item.db_type,
                    item.host,
                    item.main_version,
                    null, // active_counts (computed)
                    item.active_db_count,
                    item.active_account_count,
                    item.tags,
                    item.is_active,
                    item.last_sync_time,
                    null // actions
                ]);
            },
            total: (response) => {
                const payload = response.data || response;
                return payload.total || 0;
            }
        },
        pagination: {
            enabled: true,
            limit: 10,
            server: {
                url: (prev, page, limit) => {
                    const url = new URL(prev, window.location.origin);
                    url.searchParams.set('page', page + 1);
                    url.searchParams.set('limit', limit);
                    return url.toString();
                }
            }
        },
        sort: {
            multiColumn: false,
            server: {
                url: (prev, columns) => {
                    if (!columns.length) return prev;
                    const url = new URL(prev, window.location.origin);
                    const col = columns[0];
                    url.searchParams.set('sort', col.id);
                    url.searchParams.set('order', col.direction === 1 ? 'asc' : 'desc');
                    return url.toString();
                }
            }
        }
    });
    
    const initialFilters = normalizeFilters(resolveInstanceFilterValues());
    instancesGrid.init();
    
    if (Object.keys(initialFilters).length) {
        instancesGrid.setFilters(initialFilters);
    }
    
    bindGridEvents();
}

function normalizeFilters(rawFilters) {
    const normalized = {};
    Object.entries(rawFilters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
            if (Array.isArray(value) && value.length > 0) {
                normalized[key] = value;
            } else if (!Array.isArray(value)) {
                normalized[key] = value;
            }
        }
    });
    return normalized;
}

function bindGridEvents() {
    // 绑定全选复选框
    const selectAllCheckbox = selectOne('#grid-select-all').first();
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            const checked = e.target.checked;
            const checkboxes = select('.instance-checkbox').nodes || [];
            checkboxes.forEach(cb => cb.checked = checked);
            syncSelectionFromDom();
        });
    }
    
    // 绑定行复选框（使用事件委托）
    const gridContainer = selectOne('#instances-grid').first();
    if (gridContainer) {
        gridContainer.addEventListener('change', (e) => {
            if (e.target.classList.contains('instance-checkbox')) {
                syncSelectionFromDom();
            }
        });
    }
}
```

### 4.2 筛选集成
```javascript
function initializeInstanceFilterCard() {
    const factory = window.UI?.createFilterCard;
    if (!factory) {
        console.error('UI.createFilterCard 未加载');
        return;
    }
    
    instanceFilterCard = factory({
        formSelector: '#instance-filter-form',
        autoSubmitOnChange: true,
        onSubmit: ({ values }) => applyInstanceFilters(values),
        onClear: () => applyInstanceFilters({}),
        onChange: ({ values }) => applyInstanceFilters(values)
    });
}

function applyInstanceFilters(values) {
    if (!instancesGrid) {
        console.warn('实例网格未初始化');
        return;
    }
    
    const filters = resolveInstanceFilterValues(null, values);
    instancesGrid.updateFilters(filters);
}
```

### 4.3 批量操作适配
保留现有批量删除、批量测试连接功能，但从 Grid.js 中获取选中项：

```javascript
function getSelectedInstances() {
    const checkboxes = select('input.instance-checkbox:checked').nodes || [];
    return checkboxes
        .map(cb => parseInt(cb.value, 10))
        .filter(id => Number.isFinite(id));
}

function batchDelete() {
    const selectedIds = getSelectedInstances();
    if (!selectedIds.length) {
        toast.warning('请选择要删除的实例');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个实例吗？`)) {
        return;
    }
    
    instanceService.batchDeleteInstances(selectedIds)
        .then(() => {
            toast.success('批量删除成功');
            instancesGrid.refresh();
        })
        .catch(error => {
            toast.error(error?.message || '批量删除失败');
        });
}
```

## 5. 模板结构调整

### 5.1 移除传统表格和分页
删除 `templates/instances/list.html` 中的：
- `<table class="table table-hover">` 及其内容
- `<nav aria-label="实例分页">` 分页导航

### 5.2 添加 Grid.js 容器
```html
<div class="card">
    <div class="card-body">
        <!-- 批量操作工具栏保留 -->
        <div class="d-flex justify-content-between align-items-center mb-3">
            <!-- 现有批量操作按钮 -->
        </div>
        
        <!-- Grid.js 容器 -->
        <div id="instances-grid"></div>
    </div>
</div>
```

### 5.3 保留筛选区
保留现有 `filter_card` 宏调用，无需修改：
```html
{% call filter_card(form_id='instance-filter-form', action=url_for('instance.index')) %}
    {{ search_input(value=search, col_class='col-2') }}
    {{ db_type_filter(database_type_options, db_type) }}
    {{ status_active_filter(status_options, status) }}
    {{ tag_selector_filter(tag_options, selected_tags) }}
{% endcall %}
```

## 6. 回归测试清单
- [ ] 搜索框输入触发筛选，Network 请求包含 `search` 参数
- [ ] 数据库类型下拉筛选生效，请求包含 `db_type` 参数
- [ ] 状态筛选（正常/禁用）生效，请求包含 `status` 参数
- [ ] 标签筛选器选择标签后触发筛选，请求包含 `tags` 参数
- [ ] 分页切换正常，请求包含 `page` 和 `limit` 参数
- [ ] 列排序点击生效，请求包含 `sort` 和 `order` 参数
- [ ] 全选复选框能选中/取消所有行
- [ ] 批量删除功能正常，删除后调用 `instancesGrid.refresh()` 刷新
- [ ] 批量测试连接功能正常
- [ ] 单个实例编辑、测试连接、查看详情按钮正常
- [ ] 关闭模态不会触发无效请求
- [ ] 只读模式下批量操作按钮禁用

## 7. 注意事项
- **禁止修改** `app/static/js/common/grid-wrapper.js`
- 所有新增命名必须符合 AGENTS.md 规范：
  - 路由函数：`list_instances`（禁止 `api_list_instances`）
  - 服务方法：`fetch_instances`（禁止 `fetch_instances_optimized`）
  - 前端文件：保持 `list.js`（kebab-case）
- 部署后强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）
- 确保 `DATABASE_TYPE_MAP` 在前端全局可用（可通过 `base.html` 注入）

## 8. 参考实现
- 凭据管理页面：
  - 模板：`app/templates/credentials/list.html`
  - 脚本：`app/static/js/modules/views/credentials/list.js`
  - 路由：`app/routes/credentials.py:200+`
- Grid.js 迁移标准：`docs/refactoring/new/gridjs-migration-standard.md`

## 9. 迁移步骤
1. 后端新增 `/instances/api/instances` 接口
2. 前端引入 Grid.js 资产（CSS + JS）
3. 改造 `list.js`，初始化 `GridWrapper`
4. 调整模板，移除传统表格，添加 `#instances-grid` 容器
5. 适配筛选器与 Grid.js 的 `updateFilters` 方法
6. 测试批量操作、分页、排序、筛选功能
7. 执行回归测试清单
8. 部署并通知用户刷新缓存
