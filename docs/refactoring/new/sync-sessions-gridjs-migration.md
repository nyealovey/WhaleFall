# 会话中心 Grid.js 迁移方案

> 将会话中心列表从自定义卡片渲染升级为基于 Grid.js + GridWrapper 的统一实现，**核心要求：完整保留现有进度条样式与动画效果**。

## 1. 迁移目标
- 统一分页、排序、筛选逻辑，支持服务端数据源
- 前后端交互使用 `/sync_sessions/api/sessions` REST 接口，响应格式包含 `sessions`, `pagination`, `total`
- 表格列渲染支持自定义 HTML（使用 `gridjs.html`）
- **完整保留现有进度条样式**：渐变色、动画条纹、成功率颜色映射
- 保留会话详情模态、取消会话、自动刷新等核心功能
- 移除自定义分页 HTML，由 GridWrapper 接管分页控制

## 2. 通用资产引用
- **脚本与样式**
  - `app/static/vendor/gridjs/gridjs.umd.js`
  - `app/static/vendor/gridjs/mermaid.min.css`
  - `app/static/js/common/grid-wrapper.js`（禁止擅自修改）
- **保留现有样式**
  - `app/static/css/pages/history/sync-sessions.css`（进度条样式必须保留）
- **模板引用**：在 `templates/history/sessions/sync-sessions.html` 中添加
  ```html
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/gridjs/mermaid.min.css') }}">
  <script src="{{ url_for('static', filename='vendor/gridjs/gridjs.umd.js') }}"></script>
  <script src="{{ url_for('static', filename='js/common/grid-wrapper.js') }}"></script>
  ```

## 3. 后端接口改造

### 3.1 接口规范化
当前接口 `/sync_sessions/api/sessions` 已基本符合要求，需微调响应格式：

```python
@sync_sessions_bp.route("/api/sessions")
@login_required
@view_required
def list_sessions() -> Response:  # 函数名改为 list_sessions（移除 api_ 前缀）
    """获取同步会话列表 API"""
    try:
        sync_type = request.args.get("sync_type", "")
        sync_category = request.args.get("sync_category", "")
        status = request.args.get("status", "")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))  # 改为 limit 参数
        sort = request.args.get("sort", "started_at")  # 新增排序参数
        order = request.args.get("order", "desc")  # 新增排序方向
        
        # 获取并过滤会话
        all_sessions = sync_session_service.get_recent_sessions(1000)
        
        filtered_sessions = all_sessions
        if sync_type and sync_type.strip():
            filtered_sessions = [s for s in filtered_sessions if s.sync_type == sync_type]
        if sync_category and sync_category.strip():
            filtered_sessions = [s for s in filtered_sessions if s.sync_category == sync_category]
        if status and status.strip():
            filtered_sessions = [s for s in filtered_sessions if s.status == status]
        
        # 排序
        reverse = (order == 'desc')
        if sort == 'started_at':
            filtered_sessions.sort(key=lambda s: s.started_at or '', reverse=reverse)
        elif sort == 'completed_at':
            filtered_sessions.sort(key=lambda s: s.completed_at or '', reverse=reverse)
        elif sort == 'status':
            filtered_sessions.sort(key=lambda s: s.status or '', reverse=reverse)
        
        # 分页
        total = len(filtered_sessions)
        start = (page - 1) * limit
        end = start + limit
        sessions_page = filtered_sessions[start:end]
        
        sessions_data = [session.to_dict() for session in sessions_page]
        
        total_pages = (total + limit - 1) // limit
        
        # 调整响应格式以符合 GridWrapper 标准
        return jsonify_unified_success(
            data={
                "items": sessions_data,  # 改为 items
                "total": total,
                "page": page,
                "pages": total_pages
            },
            message="获取同步会话列表成功",
        )
    except Exception as e:
        log_error(f"获取同步会话列表失败: {str(e)}", module="sync_sessions")
        raise SystemError("获取会话列表失败") from e
```

### 3.2 路由命名规范
- **禁止使用** `api_list_sessions` 作为函数名
- **正确命名**：`list_sessions`（动词短语，无 `api_` 前后缀）
- 路由路径：`/sync_sessions/api/sessions`（路径中可包含 `api`，但函数名不得带）

## 4. 前端脚本改造

### 4.1 Grid.js 初始化
在 `app/static/js/modules/views/history/sessions/sync-sessions.js` 中：

```javascript
let sessionsGrid = null;

function initializeSessionsGrid() {
    const container = document.getElementById('sessions-grid');
    if (!container) {
        console.error('会话网格容器未找到');
        return;
    }
    
    sessionsGrid = new global.GridWrapper(container, {
        columns: [
            {
                id: 'session_info',
                name: '会话',
                width: '200px',
                formatter: (cell, row) => {
                    const sessionId = row.cells[1].data;
                    const syncType = row.cells[2].data;
                    const syncCategory = row.cells[3].data;
                    return gridjs.html(`
                        <div class="session-info">
                            <div class="session-id">${sessionId.substring(0, 8)}...</div>
                            <div class="text-muted small">${getSyncTypeText(syncType)} • ${getSyncCategoryText(syncCategory)}</div>
                        </div>
                    `);
                }
            },
            { id: 'session_id', name: 'Session ID', hidden: true },
            { id: 'sync_type', name: 'Sync Type', hidden: true },
            { id: 'sync_category', name: 'Sync Category', hidden: true },
            {
                id: 'status',
                name: '状态',
                width: '100px',
                formatter: (cell) => {
                    const statusColor = getStatusColor(cell);
                    const statusText = getStatusText(cell);
                    return gridjs.html(`
                        <span class="badge bg-${statusColor}">${statusText}</span>
                    `);
                }
            },
            {
                id: 'progress',
                name: '进度',
                width: '180px',
                sort: false,
                formatter: (cell, row) => {
                    const totalInstances = row.cells[6].data || 0;
                    const successfulInstances = row.cells[7].data || 0;
                    const failedInstances = row.cells[8].data || 0;
                    const successRate = totalInstances > 0 
                        ? Math.round((successfulInstances / totalInstances) * 100) 
                        : 0;
                    const progressInfo = getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances);
                    
                    return gridjs.html(`
                        <div class="session-progress">
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar ${progressInfo.barClass}" 
                                     role="progressbar" 
                                     style="width: ${successRate}%" 
                                     title="${progressInfo.tooltip}"></div>
                            </div>
                            <div class="text-muted small mt-1">
                                <span class="${progressInfo.textClass}">
                                    <i class="${progressInfo.icon}"></i> ${successRate}% (${successfulInstances}/${totalInstances})
                                </span>
                            </div>
                        </div>
                    `);
                }
            },
            { id: 'total_instances', name: 'Total', hidden: true },
            { id: 'successful_instances', name: 'Success', hidden: true },
            { id: 'failed_instances', name: 'Failed', hidden: true },
            {
                id: 'started_at',
                name: '开始时间',
                width: '140px',
                formatter: (cell) => {
                    const formatted = timeUtils.formatTime(cell, 'datetime');
                    return gridjs.html(`<div class="text-muted small">${formatted}</div>`);
                }
            },
            {
                id: 'completed_at',
                name: '完成时间',
                width: '140px',
                formatter: (cell) => {
                    if (!cell) {
                        return gridjs.html('<div class="text-muted small">-</div>');
                    }
                    const formatted = timeUtils.formatTime(cell, 'datetime');
                    return gridjs.html(`<div class="text-muted small">${formatted}</div>`);
                }
            },
            {
                id: 'duration',
                name: '耗时',
                width: '100px',
                sort: false,
                formatter: (cell, row) => {
                    const startedAt = row.cells[9].data;
                    const completedAt = row.cells[10].data;
                    const badge = getDurationBadge(startedAt, completedAt);
                    return gridjs.html(`<div class="session-duration">${badge}</div>`);
                }
            },
            {
                id: 'actions',
                name: '操作',
                width: '150px',
                sort: false,
                formatter: (cell, row) => {
                    const sessionId = row.cells[1].data;
                    const status = row.cells[4].data;
                    
                    let buttons = `
                        <button class="btn btn-sm btn-outline-primary" 
                                data-action="view" 
                                data-id="${sessionId}">
                            <i class="fas fa-eye"></i> 详情
                        </button>`;
                    
                    if (status === 'running') {
                        buttons += `
                        <button class="btn btn-sm btn-outline-danger" 
                                data-action="cancel" 
                                data-id="${sessionId}">
                            <i class="fas fa-stop"></i> 取消
                        </button>`;
                    }
                    
                    return gridjs.html(`
                        <div class="session-actions d-flex gap-2">
                            ${buttons}
                        </div>
                    `);
                }
            }
        ],
        server: {
            url: '/sync_sessions/api/sessions?sort=started_at&order=desc',
            then: (response) => {
                const payload = response.data || response;
                const items = payload.items || [];
                return items.map(item => [
                    null, // session_info (computed)
                    item.session_id,
                    item.sync_type,
                    item.sync_category,
                    item.status,
                    null, // progress (computed)
                    item.total_instances,
                    item.successful_instances,
                    item.failed_instances,
                    item.started_at,
                    item.completed_at,
                    null, // duration (computed)
                    null  // actions
                ]);
            },
            total: (response) => {
                const payload = response.data || response;
                return payload.total || 0;
            }
        },
        pagination: {
            enabled: true,
            limit: 20,
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
        },
        className: {
            table: 'table table-hover sessions-grid-table'
        }
    });
    
    const initialFilters = normalizeFilters(resolveSyncFilters());
    sessionsGrid.init();
    
    if (Object.keys(initialFilters).length) {
        sessionsGrid.setFilters(initialFilters);
    }
    
    bindGridEvents();
    setupAutoRefresh();
}

function bindGridEvents() {
    // 使用事件委托绑定按钮
    const gridContainer = document.getElementById('sessions-grid');
    if (gridContainer) {
        gridContainer.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('[data-action="view"]');
            if (viewBtn) {
                const sessionId = viewBtn.getAttribute('data-id');
                viewSessionDetail(sessionId);
                return;
            }
            
            const cancelBtn = e.target.closest('[data-action="cancel"]');
            if (cancelBtn) {
                const sessionId = cancelBtn.getAttribute('data-id');
                cancelSession(sessionId);
                return;
            }
        });
    }
}

function setupAutoRefresh() {
    // 每30秒自动刷新
    setInterval(() => {
        if (sessionsGrid) {
            sessionsGrid.refresh({ silent: true });
        }
    }, 30000);
}

function normalizeFilters(rawFilters) {
    const normalized = {};
    Object.entries(rawFilters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
            normalized[key] = value;
        }
    });
    return normalized;
}
```

### 4.2 筛选集成
```javascript
function initializeSyncFilterCard() {
    const factory = window.UI?.createFilterCard;
    if (!factory) {
        console.error('UI.createFilterCard 未加载');
        return;
    }
    
    syncFilterCard = factory({
        formSelector: '#sync-sessions-filter-form',
        autoSubmitOnChange: true,
        onSubmit: ({ values }) => applySyncFilters(values),
        onClear: () => applySyncFilters({}),
        onChange: ({ values }) => applySyncFilters(values)
    });
}

function applySyncFilters(values) {
    if (!sessionsGrid) {
        console.warn('会话网格未初始化');
        return;
    }
    
    const filters = resolveSyncFilters(null, values);
    sessionsGrid.updateFilters(filters);
}
```

### 4.3 保留进度条样式函数
**关键：完整保留现有进度条逻辑，确保样式一致**

```javascript
/**
 * 根据成功率计算进度条样式与提示
 * 此函数必须保持不变，确保进度条样式与原实现一致
 */
function getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances) {
    if (totalInstances === 0) {
        return { 
            barClass: 'bg-secondary', 
            textClass: 'text-muted', 
            icon: 'fas fa-question-circle', 
            tooltip: '无实例数据' 
        };
    }
    if (successRate === 100) {
        return { 
            barClass: 'bg-success', 
            textClass: 'text-success', 
            icon: 'fas fa-check-circle', 
            tooltip: '全部成功' 
        };
    } else if (successRate === 0) {
        return { 
            barClass: 'bg-danger', 
            textClass: 'text-danger', 
            icon: 'fas fa-times-circle', 
            tooltip: '全部失败' 
        };
    } else if (successRate >= 70) {
        return { 
            barClass: 'bg-warning', 
            textClass: 'text-warning', 
            icon: 'fas fa-exclamation-triangle', 
            tooltip: `部分成功 (${successfulInstances}成功, ${failedInstances}失败)` 
        };
    } else {
        return { 
            barClass: 'bg-danger', 
            textClass: 'text-danger', 
            icon: 'fas fa-exclamation-triangle', 
            tooltip: `大部分失败 (${successfulInstances}成功, ${failedInstances}失败)` 
        };
    }
}
```

## 5. 样式文件调整

### 5.1 保留现有进度条样式
**关键：`app/static/css/pages/history/sync-sessions.css` 中的进度条样式必须完整保留**

```css
/* 进度条 - 利用全局样式 */
.progress {
    height: 12px;
    border-radius: var(--border-radius-sm);
    background-color: var(--gray-200);
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}

.progress-bar {
    height: 12px;
    border-radius: var(--border-radius-sm);
    transition: width 0.6s ease;
    position: relative;
    overflow: hidden;
}

.progress-bar.bg-success {
    background: var(--gradient-success);
}

.progress-bar.bg-danger {
    background: var(--gradient-danger);
}

.progress-bar.bg-warning {
    background: var(--gradient-warning);
}

.progress-bar.bg-secondary {
    background: var(--gradient-secondary);
}

/* 进度条动画效果 - 必须保留 */
.progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background-image: linear-gradient(
        -45deg,
        rgba(255, 255, 255, 0.2) 25%,
        transparent 25%,
        transparent 50%,
        rgba(255, 255, 255, 0.2) 50%,
        rgba(255, 255, 255, 0.2) 75%,
        transparent 75%,
        transparent
    );
    background-size: 20px 20px;
    animation: progress-bar-stripes 1s linear infinite;
}

@keyframes progress-bar-stripes {
    0% { background-position: 0 0; }
    100% { background-position: 20px 0; }
}
```

### 5.2 新增 Grid.js 适配样式
在同一文件中添加：

```css
/* Grid.js 表格适配 */
.sessions-grid-table {
    width: 100%;
}

.sessions-grid-table .session-info .session-id {
    font-weight: 600;
    color: var(--gray-700);
}

.sessions-grid-table .session-progress {
    min-width: 150px;
}

.sessions-grid-table .session-duration {
    font-weight: 600;
}

.sessions-grid-table .session-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
}

/* 保持状态边框颜色 */
.sessions-grid-table tr.running {
    border-left: 4px solid var(--success-color);
}

.sessions-grid-table tr.completed {
    border-left: 4px solid var(--info-color);
}

.sessions-grid-table tr.failed {
    border-left: 4px solid var(--danger-color);
}

.sessions-grid-table tr.cancelled {
    border-left: 4px solid var(--gray-400);
}
```

## 6. 模板结构调整

### 6.1 移除自定义渲染容器
删除 `templates/history/sessions/sync-sessions.html` 中的：
- `<div id="sessions-loading">` 加载状态
- `<div id="sessions-container">` 会话列表容器
- `<div id="pagination-container">` 分页容器

### 6.2 添加 Grid.js 容器
```html
<div class="card">
    <div class="card-header">
        <h5 class="mb-0"><i class="fas fa-list"></i> 同步会话列表</h5>
    </div>
    <div class="card-body">
        <!-- Grid.js 容器 -->
        <div id="sessions-grid"></div>
    </div>
</div>
```

### 6.3 保留筛选区
保留现有 `filter_card` 宏调用，无需修改：
```html
{% call filter_card(form_id='sync-sessions-filter-form', action=url_for('sync_sessions.index'), auto_register=False) %}
    {{ sync_type_filter(sync_type_options, '', col_class='col-3') }}
    {{ sync_category_filter(sync_category_options, '', col_class='col-3') }}
    {{ status_sync_filter(status_options, '', col_class='col-3') }}
{% endcall %}
```

## 7. 回归测试清单
- [ ] 同步类型筛选生效，请求包含 `sync_type` 参数
- [ ] 同步分类筛选生效，请求包含 `sync_category` 参数
- [ ] 状态筛选生效，请求包含 `status` 参数
- [ ] 分页切换正常，请求包含 `page` 和 `limit` 参数
- [ ] 列排序点击生效，请求包含 `sort` 和 `order` 参数
- [ ] **进度条样式完整保留**：渐变色、动画条纹、颜色映射
- [ ] 进度条根据成功率显示正确颜色（100%绿色、0%红色、70%+黄色、<70%红色）
- [ ] 进度条动画条纹正常播放
- [ ] 会话详情按钮打开模态正常
- [ ] 取消会话按钮功能正常（仅 running 状态显示）
- [ ] 取消会话后调用 `sessionsGrid.refresh()` 刷新
- [ ] 自动刷新功能正常（每30秒）
- [ ] 耗时徽标显示正确
- [ ] 会话ID、同步类型、同步分类显示正确

## 8. 进度条样式验证重点
**这是本次迁移的核心要求，必须严格验证：**

1. **渐变背景**：
   - 成功（绿色）：`var(--gradient-success)`
   - 失败（红色）：`var(--gradient-danger)`
   - 警告（黄色）：`var(--gradient-warning)`
   - 次要（灰色）：`var(--gradient-secondary)`

2. **动画条纹**：
   - 斜向条纹（-45度）
   - 1秒循环动画
   - 白色半透明覆盖层

3. **颜色映射逻辑**：
   - 100% 成功率 → 绿色进度条 + 绿色文字 + 勾选图标
   - 0% 成功率 → 红色进度条 + 红色文字 + 叉号图标
   - 70%-99% 成功率 → 黄色进度条 + 黄色文字 + 警告图标
   - 1%-69% 成功率 → 红色进度条 + 红色文字 + 警告图标
   - 无数据 → 灰色进度条 + 灰色文字 + 问号图标

4. **视觉验证**：
   - 打开浏览器开发者工具，检查进度条元素的 CSS 类
   - 确认 `::after` 伪元素存在且动画正常
   - 对比迁移前后的截图，确保视觉一致

## 9. 注意事项
- **禁止修改** `app/static/js/common/grid-wrapper.js`
- **禁止修改** 进度条样式相关的 CSS 规则
- **禁止修改** `getProgressInfo` 函数的逻辑
- 所有新增命名必须符合 AGENTS.md 规范：
  - 路由函数：`list_sessions`（禁止 `api_list_sessions`）
  - 服务方法：`fetch_sessions`（禁止 `fetch_sessions_optimized`）
- 部署后强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）
- 确保 CSS 变量（如 `--gradient-success`）在全局样式中已定义

## 10. 参考实现
- 凭据管理页面：
  - 模板：`app/templates/credentials/list.html`
  - 脚本：`app/static/js/modules/views/credentials/list.js`
  - 路由：`app/routes/credentials.py:200+`
- Grid.js 迁移标准：`docs/refactoring/new/gridjs-migration-standard.md`
- 实例管理迁移：`docs/refactoring/new/instance-management-gridjs-migration.md`

## 11. 迁移步骤
1. 后端调整 `/sync_sessions/api/sessions` 接口响应格式（`items`, `total`, `page`, `pages`）
2. 后端函数重命名：`api_list_sessions` → `list_sessions`
3. 前端引入 Grid.js 资产（CSS + JS）
4. 改造 `sync-sessions.js`，初始化 `GridWrapper`
5. **验证进度条样式完整保留**（关键步骤）
6. 调整模板，移除自定义容器，添加 `#sessions-grid` 容器
7. 适配筛选器与 Grid.js 的 `updateFilters` 方法
8. 测试会话详情、取消会话、自动刷新功能
9. 执行回归测试清单，特别是进度条样式验证
10. 部署并通知用户刷新缓存

## 12. 迁移风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 进度条样式丢失 | 高 | 完整复制 CSS 规则，迁移前后对比截图 |
| 动画条纹失效 | 中 | 确保 `::after` 伪元素和 `@keyframes` 保留 |
| 颜色映射错误 | 中 | 保持 `getProgressInfo` 函数不变 |
| 自动刷新失效 | 低 | 使用 `sessionsGrid.refresh({ silent: true })` |
| 模态功能异常 | 低 | 保留现有模态控制器，仅改数据源 |

## 13. 验收标准
- [ ] 所有回归测试通过
- [ ] 进度条样式与迁移前完全一致（截图对比）
- [ ] 进度条动画流畅播放
- [ ] 颜色映射逻辑正确（手动测试各成功率场景）
- [ ] 性能无明显下降（Network 请求时间 < 500ms）
- [ ] 无 JavaScript 错误（Console 无报错）
- [ ] 代码符合 AGENTS.md 命名规范
