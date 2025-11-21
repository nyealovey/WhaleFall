# 日志中心 Grid.js 重构方案

> 基于 `docs/refactor/gridjs-migration-standard.md` 标准，将日志中心从卡片式布局迁移到 Grid.js + GridWrapper 统一实现。

## 概述

将日志中心从自定义 DOM 渲染的卡片式布局重构为 Grid.js 表格布局，遵循项目 Grid.js 迁移标准，保持原有的级别颜色样式和交互功能。

## 目标

- 使用 Grid.js + GridWrapper 替代当前的卡片式日志列表
- 遵循 `gridjs-migration-standard.md` 中的接口约定和前端标准流程
- 保留原有的日志级别颜色区分（ERROR 红色、WARNING 黄色、INFO 蓝色、DEBUG 灰色）
- 保持点击查看详情的交互功能
- 统一分页、排序、筛选逻辑
- 优化性能和用户体验

## 当前实现分析

### 现有结构

**路由**: `app/routes/logs.py`
- `/logs/` - 日志中心首页
- `/logs/api/search` - 日志搜索 API
- `/logs/api/stats` - 统计信息 API

**模板**: `app/templates/history/logs/logs.html`
- 使用卡片式布局
- 包含统计面板、筛选器、日志列表容器

**前端**: `app/static/js/modules/views/history/logs/logs.js`
- 使用自定义 DOM 渲染
- 通过 `createLogEntryElement()` 创建日志条目

**样式**: `app/static/css/pages/history/logs.css`
- 定义了日志级别颜色
- 卡片式布局样式

### 日志级别颜色映射

```css
.log-level-DEBUG   { color: var(--gray-600); }
.log-level-INFO    { color: var(--info-color); }
.log-level-WARNING { color: var(--warning-color); }
.log-level-ERROR   { color: var(--danger-color); }
.log-level-CRITICAL{ color: var(--danger-color); font-weight: bold; }
```

对应的 Bootstrap 颜色类：
- DEBUG → `secondary`
- INFO → `info`
- WARNING → `warning`
- ERROR → `danger`
- CRITICAL → `dark`

## 重构方案

### 1. 后端调整

#### 修改 `app/routes/logs.py`

添加符合标准的 Grid.js API 端点 `/logs/api/list`：

```python
@logs_bp.route("/api/list")
@login_required
def list_logs_api() -> tuple[Response, int]:
    """Grid.js 日志列表 API - 符合 gridjs-migration-standard.md 规范"""
    # 标准分页参数
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    sort_field = request.args.get("sort", "timestamp")
    sort_order = request.args.get("order", "desc")
    
    # 业务筛选参数
    level = request.args.get("level", "").strip()
    module = request.args.get("module", "").strip()
    search = request.args.get("search", "").strip()
    hours = request.args.get("hours", type=int)
    
    # 构建查询
    query = UnifiedLog.query
    
    # 时间范围（默认24小时）
    if hours:
        start_time = time_utils.now() - timedelta(hours=hours)
        query = query.filter(UnifiedLog.timestamp >= start_time)
    else:
        # 默认24小时
        default_start = time_utils.now() - timedelta(hours=24)
        query = query.filter(UnifiedLog.timestamp >= default_start)
    
    # 级别过滤
    if level:
        try:
            log_level = LogLevel(level.upper())
            query = query.filter(UnifiedLog.level == log_level)
        except ValueError:
            pass
    
    # 模块过滤
    if module:
        query = query.filter(UnifiedLog.module.like(f"%{module}%"))
    
    # 关键词搜索
    if search:
        search_filter = or_(
            UnifiedLog.message.like(f"%{search}%"),
            cast(UnifiedLog.context, Text).like(f"%{search}%"),
        )
        query = query.filter(search_filter)
    
    # 排序
    sortable_fields = {
        "id": UnifiedLog.id,
        "timestamp": UnifiedLog.timestamp,
        "level": UnifiedLog.level,
        "module": UnifiedLog.module,
        "message": UnifiedLog.message,
    }
    order_column = sortable_fields.get(sort_field, UnifiedLog.timestamp)
    if sort_order == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    # 构建响应 - 符合标准格式
    items = []
    for log in pagination.items:
        items.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "timestamp_display": time_utils.formatTime(log.timestamp, 'datetime') if log.timestamp else "-",
            "level": log.level.value if hasattr(log.level, 'value') else str(log.level),
            "module": log.module or "-",
            "message": log.message or "",
            "context": log.context,
        })
    
    # 标准响应格式：包含 items, total, page, pages
    return jsonify_unified_success(
        data={
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        }
    )
```

**注意事项**：
- 保留原有的 `/api/search` 端点以保持向后兼容
- 新端点 `/api/list` 专门用于 Grid.js
- 响应格式严格遵循标准：`{ data: { items, total, page, pages }, success, message }`

### 2. 前端重构

#### 重构 `app/static/js/modules/views/history/logs/logs.js`

遵循标准流程，移除 LogsStore，直接使用 GridWrapper：

```javascript
/**
 * 日志中心页面 - Grid.js 重构版本
 * 遵循 gridjs-migration-standard.md 标准
 */
(function (global) {
    'use strict';

    function mount() {
        const helpers = global.DOMHelpers;
        if (!helpers) {
            console.error('DOMHelpers 未初始化');
            return;
        }

        const gridjs = global.gridjs;
        const GridWrapper = global.GridWrapper;
        if (!gridjs || !GridWrapper) {
            console.error('Grid.js 或 GridWrapper 未加载');
            return;
        }

        const LodashUtils = global.LodashUtils;
        if (!LodashUtils) {
            console.error('LodashUtils 未初始化');
            return;
        }

        const { ready, selectOne, from } = helpers;
        const gridHtml = gridjs.html;

        const LOG_FILTER_FORM_ID = 'logs-filter-form';
        let logsGrid = null;
        let logFilterCard = null;
        let logDetailModalController = null;

        ready(() => {
            initializePage();
        });

        function initializePage() {
            setDefaultTimeRange();
            initializeGrid();
            initializeLogFilterCard();
            initializeLogDetailModal();
            exposeGlobalActions();
        }

        /**
         * 初始化 Grid.js - 标准流程
         */
        function initializeGrid() {
            const container = document.getElementById('logs-grid');
            if (!container) {
                console.warn('找不到 #logs-grid 容器');
                return;
            }

            logsGrid = new GridWrapper(container, {
                search: false,
                sort: false,
                columns: [
                    {
                        name: 'ID',
                        id: 'id',
                        width: '80px',
                        formatter: (cell) => {
                            if (!gridHtml) return cell;
                            return gridHtml(`<span class="text-muted small">#${cell}</span>`);
                        },
                    },
                    {
                        name: '消息',
                        id: 'message',
                        formatter: (cell, row) => {
                            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
                            const message = escapeHtmlValue(cell || '-');
                            return gridHtml ? gridHtml(message) : message;
                        },
                    },
                    {
                        name: '级别',
                        id: 'level',
                        width: '100px',
                        formatter: (cell) => {
                            const level = String(cell || 'INFO').toUpperCase();
                            const colors = {
                                DEBUG: 'secondary',
                                INFO: 'info',
                                WARNING: 'warning',
                                ERROR: 'danger',
                                CRITICAL: 'dark',
                            };
                            const color = colors[level] || 'secondary';
                            if (!gridHtml) return level;
                            return gridHtml(`<span class="badge bg-${color}">${level}</span>`);
                        },
                    },
                    {
                        name: '模块',
                        id: 'module',
                        width: '140px',
                        formatter: (cell) => {
                            const module = cell || '-';
                            if (!gridHtml) return module;
                            if (module === '-') {
                                return gridHtml('<span class="text-muted">-</span>');
                            }
                            return gridHtml(
                                `<span class="badge bg-light text-dark">${escapeHtmlValue(module)}</span>`
                            );
                        },
                    },
                    {
                        name: '时间',
                        id: 'timestamp_display',
                        width: '180px',
                        formatter: (cell) => {
                            if (!gridHtml) return cell || '-';
                            return gridHtml(
                                `<small class="text-muted">${escapeHtmlValue(cell || '-')}</small>`
                            );
                        },
                    },
                    {
                        name: '操作',
                        id: 'actions',
                        width: '100px',
                        sort: false,
                        formatter: (cell, row) => {
                            const meta = row?.cells?.[row.cells.length - 1]?.data || {};
                            const logId = meta.id;
                            if (!gridHtml) return '详情';
                            return gridHtml(`
                                <button type="button" 
                                        class="btn btn-sm btn-outline-primary" 
                                        onclick="LogsActions.viewDetail(${logId})"
                                        title="查看详情">
                                    <i class="fas fa-eye"></i> 详情
                                </button>
                            `);
                        },
                    },
                ],
                server: {
                    url: '/logs/api/list?sort=timestamp&order=desc',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    then: (response) => {
                        const payload = response?.data || response || {};
                        const items = payload.items || [];
                        return items.map((item) => [
                            item.id,
                            item.message || '',
                            item.level || 'INFO',
                            item.module || '-',
                            item.timestamp_display || '-',
                            null, // 操作列占位
                            item, // 元数据，用于 formatter
                        ]);
                    },
                    total: (response) => {
                        const payload = response?.data || response || {};
                        return payload.total || 0;
                    },
                },
                style: {
                    table: {
                        'white-space': 'normal',
                    },
                },
            });

            // 标准流程：初始化筛选
            const initialFilters = normalizeFilters(resolveFormValues());
            logsGrid.init();
            if (initialFilters && Object.keys(initialFilters).length > 0) {
                logsGrid.setFilters(initialFilters);
            }
        }

        /**
         * 暴露全局操作方法 - 供按钮调用
         */
        function exposeGlobalActions() {
            global.LogsActions = {
                viewDetail: viewLogDetail,
            };
        }

        /**
         * 初始化筛选卡片 - 使用标准 FilterCard
         */
        function initializeLogFilterCard() {
            const factory = global.UI?.createFilterCard;
            if (!factory) {
                console.error('UI.createFilterCard 未加载');
                return;
            }

            logFilterCard = factory({
                formSelector: `#${LOG_FILTER_FORM_ID}`,
                autoSubmitOnChange: true,
                onSubmit: ({ values }) => applyLogFilters(values),
                onClear: () => applyLogFilters({}),
                onChange: ({ values }) => applyLogFilters(values),
            });
        }

        /**
         * 应用筛选 - 标准流程
         */
        function applyLogFilters(values) {
            if (!logsGrid) return;

            const rawValues = values && Object.keys(values || {}).length
                ? values
                : collectFormValues();

            const filters = normalizeFilters(rawValues);

            // 验证搜索关键词
            const searchTerm = filters.search || '';
            if (typeof searchTerm === 'string' && searchTerm.trim().length > 0 && searchTerm.trim().length < 2) {
                global.toast?.warning?.('搜索关键词至少需要2个字符');
                return;
            }

            // 标准流程：调用 updateFilters
            logsGrid.updateFilters(filters);

            // 同时更新统计信息
            updateStats(filters);
        }

        /**
         * 规范化筛选参数
         */
        function normalizeFilters(rawValues) {
            const timeRangeValue = rawValues?.time_range || rawValues?.timeRange || '';
            const hoursValue = rawValues?.hours || (timeRangeValue ? getHoursFromTimeRange(timeRangeValue) : 24);

            const filters = {
                level: rawValues?.level,
                module: rawValues?.module,
                search: rawValues?.search || rawValues?.q,
                hours: hoursValue,
            };

            // 移除空值
            Object.keys(filters).forEach((key) => {
                if (!filters[key] || filters[key] === '' || filters[key] === 'all') {
                    delete filters[key];
                }
            });

            return filters;
        }

        /**
         * 收集表单值
         */
        function collectFormValues() {
            if (logFilterCard?.serialize) {
                return logFilterCard.serialize();
            }

            const form = selectOne(`#${LOG_FILTER_FORM_ID}`).first();
            if (!form) return {};

            const serializer = global.UI?.serializeForm;
            if (serializer) {
                return serializer(form);
            }

            const formData = new FormData(form);
            const result = {};
            formData.forEach((value, key) => {
                result[key] = value;
            });
            return result;
        }

        function resolveFormValues() {
            return collectFormValues();
        }

        /**
         * 设置默认时间范围
         */
        function setDefaultTimeRange() {
            const timeRangeSelect = selectOne('#time_range');
            if (!timeRangeSelect.length) return;

            const defaultValue = '1d';
            const selectElement = timeRangeSelect.first();
            if (selectElement.tomselect) {
                const currentValue = selectElement.tomselect.getValue();
                if (!currentValue) {
                    selectElement.tomselect.setValue(defaultValue, true);
                }
            } else if (!selectElement.value) {
                selectElement.value = defaultValue;
            }
        }

        /**
         * 时间范围转小时数
         */
        function getHoursFromTimeRange(timeRange) {
            const map = { '1h': 1, '1d': 24, '1w': 168, '1m': 720 };
            return map[timeRange] || 24;
        }

        /**
         * 更新统计信息
         */
        function updateStats(filters) {
            const LogsService = global.LogsService;
            if (!LogsService) return;

            const logsService = new LogsService(global.httpU);
            logsService.getStats(filters)
                .then((response) => {
                    if (response?.success && response?.data) {
                        updateStatsDisplay(response.data);
                    }
                })
                .catch((error) => {
                    console.error('更新统计信息失败:', error);
                });
        }

        /**
         * 更新统计面板
         */
        function updateStatsDisplay(stats) {
            const elements = {
                totalLogs: stats.total_logs || 0,
                errorLogs: stats.error_logs || 0,
                warningLogs: stats.warning_logs || 0,
                modulesCount: stats.modules_count || 0,
            };

            Object.entries(elements).forEach(([id, value]) => {
                const element = selectOne(`#${id}`);
                if (element.length) {
                    element.text(value);
                }
            });
        }

        /**
         * 查看日志详情
         */
        function viewLogDetail(logId) {
            if (!logDetailModalController) return;

            const LogsService = global.LogsService;
            if (!LogsService) return;

            const logsService = new LogsService(global.httpU);
            logsService.getLogDetail(logId)
                .then((response) => {
                    if (response?.success && response?.data?.log) {
                        logDetailModalController.open(response.data.log);
                    }
                })
                .catch((error) => {
                    console.error('获取日志详情失败:', error);
                    global.toast?.error?.('获取日志详情失败');
                });
        }

        /**
         * 初始化日志详情模态
         */
        function initializeLogDetailModal() {
            if (!global.LogsLogDetailModal?.createController) {
                console.error('LogsLogDetailModal 未加载');
                return;
            }

            logDetailModalController = global.LogsLogDetailModal.createController({
                ui: global.UI,
                toast: global.toast,
                timeUtils: global.timeUtils,
                modalSelector: '#logDetailModal',
                contentSelector: '#logDetailContent',
                copyButtonSelector: '#copyLogDetailButton',
            });
        }

        /**
         * HTML 转义
         */
        function escapeHtmlValue(value) {
            if (value === undefined || value === null) return '';
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }
    }

    global.LogsPage = {
        mount,
    };
})(window);
```

**关键变更**：
1. 移除 LogsStore，直接使用 GridWrapper
2. 遵循标准流程：`new GridWrapper() → init() → setFilters()`
3. 筛选通过 `logsGrid.updateFilters()` 应用
4. 统计信息独立更新，不依赖 Grid.js

### 3. 模板调整

#### 修改 `app/templates/history/logs/logs.html`

按照标准引入 Grid.js 资源：

```html
{% extends "base.html" %}
{% from 'components/filters/macros.html' import filter_card, search_input, log_level_filter, module_filter, time_range_filter %}
{% from 'components/ui/macros.html' import stats_card %}

{% block title %}日志中心{% endblock %}

{% block extra_css %}
<!-- 标准 Grid.js 样式 -->
<link rel="stylesheet" href="{{ url_for('static', filename='vendor/gridjs/mermaid.min.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/pages/history/logs.css') }}">
{% endblock %}

{% block content %}
<!-- 页面头部 -->
<div class="page-header">
    <div class="container">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h2><i class="fas fa-chart-line me-2"></i>日志中心</h2>
                <p class="mb-0">查看系统日志和操作记录</p>
            </div>
        </div>
    </div>
</div>

<div class="container-fluid">
    <!-- 统计信息 -->
    <div class="row mb-4">
        {{ stats_card('总日志数', 'totalLogs', 'fas fa-file-alt', 'bg-primary text-white', default_value='0') }}
        {{ stats_card('错误日志', 'errorLogs', 'fas fa-exclamation-triangle', 'bg-danger text-white', default_value='0') }}
        {{ stats_card('警告日志', 'warningLogs', 'fas fa-exclamation-circle', 'bg-warning text-white text-dark', default_value='0') }}
        {{ stats_card('模块数量', 'modulesCount', 'fas fa-cubes', 'bg-info text-white', default_value='0') }}
    </div>

    <!-- 搜索和筛选 -->
    <div class="logs-page">
        {% call filter_card(form_id='logs-filter-form', action='#', auto_register=False) %}
            {{ search_input(placeholder='输入搜索关键词') }}
            {{ log_level_filter(log_level_options) }}
            {{ module_filter(module_options) }}
            {{ time_range_filter(time_range_options, '1d') }}
        {% endcall %}
    </div>

    <!-- 日志列表 - Grid.js 容器 -->
    <div class="card logs-container">
        <div class="card-body">
            <div id="logs-grid"></div>
        </div>
    </div>
</div>

{% include 'history/logs/modals/log-detail-modal.html' %}
{% endblock %}

{% block extra_js %}
<!-- 标准 Grid.js 脚本 -->
<script src="{{ url_for('static', filename='vendor/gridjs/gridjs.umd.js') }}"></script>
<script src="{{ url_for('static', filename='js/common/grid-wrapper.js') }}"></script>
<!-- 业务脚本 -->
<script src="{{ url_for('static', filename='js/modules/services/logs_service.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/views/history/logs/modals/log-detail-modal.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/views/history/logs/logs.js') }}"></script>
<script src="{{ url_for('static', filename='js/bootstrap/history/logs.js') }}"></script>
{% endblock %}
```

**关键变更**：
1. 移除原有的 `#logsContainer` 和 `#paginationContainer`
2. 使用 `#logs-grid` 作为 Grid.js 容器
3. 保留统计面板和筛选器
4. 按标准顺序引入脚本：Grid.js → GridWrapper → 业务脚本

### 4. 样式调整

#### 修改 `app/static/css/pages/history/logs.css`

添加 Grid.js 相关样式，保留日志级别颜色：

```css
/* ========================================
   Grid.js 表格基础样式
   ======================================== */
#logs-grid .gridjs-wrapper {
    border-radius: var(--border-radius-md);
    overflow: hidden;
}

#logs-grid .gridjs-table {
    width: 100%;
}

/* ========================================
   日志级别行样式 - 保留原有颜色方案
   ======================================== */
#logs-grid tbody tr {
    transition: var(--transition-base);
}

/* ERROR - 红色 */
#logs-grid tbody tr:has(td:nth-child(3) .bg-danger) {
    background-color: rgba(231, 76, 60, 0.05);
    border-left: 4px solid var(--danger-color);
}

/* WARNING - 黄色 */
#logs-grid tbody tr:has(td:nth-child(3) .bg-warning) {
    background-color: rgba(243, 156, 18, 0.05);
    border-left: 4px solid var(--warning-color);
}

/* INFO - 蓝色 */
#logs-grid tbody tr:has(td:nth-child(3) .bg-info) {
    background-color: rgba(52, 152, 219, 0.05);
    border-left: 4px solid var(--info-color);
}

/* DEBUG - 灰色 */
#logs-grid tbody tr:has(td:nth-child(3) .bg-secondary) {
    background-color: var(--gray-100);
    border-left: 4px solid var(--gray-500);
}

/* CRITICAL - 深红色 */
#logs-grid tbody tr:has(td:nth-child(3) .bg-dark) {
    background-color: rgba(231, 76, 60, 0.1);
    border-left: 4px solid var(--danger-color);
    font-weight: 600;
}

/* ========================================
   行交互样式
   ======================================== */
#logs-grid tbody tr:hover {
    background-color: var(--gray-200) !important;
    box-shadow: var(--shadow-sm);
}

/* ========================================
   列样式
   ======================================== */
/* ID 列 */
#logs-grid td[data-column-id="id"] {
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
}

/* 消息列 */
#logs-grid td[data-column-id="message"] {
    white-space: normal;
    word-wrap: break-word;
    word-break: break-word;
    max-width: 600px;
    line-height: 1.5;
}

/* 级别列 */
#logs-grid td[data-column-id="level"] {
    text-align: center;
}

#logs-grid .badge {
    font-size: 0.75rem;
    padding: 4px 10px;
    font-weight: 600;
    min-width: 70px;
    display: inline-block;
}

/* 模块列 */
#logs-grid td[data-column-id="module"] {
    text-align: center;
}

#logs-grid .badge.bg-light {
    border: 1px solid var(--gray-300);
}

/* 时间列 */
#logs-grid td[data-column-id="timestamp_display"] {
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
    white-space: nowrap;
}

/* 操作列 */
#logs-grid td[data-column-id="actions"] {
    text-align: center;
    white-space: nowrap;
}

#logs-grid td[data-column-id="actions"] .btn {
    font-size: 0.875rem;
    padding: 0.25rem 0.75rem;
}

#logs-grid td[data-column-id="actions"] .btn i {
    font-size: 0.75rem;
    margin-right: 0.25rem;
}

/* ========================================
   搜索高亮（暂时保留，后续可能移除）
   ======================================== */
#logs-grid .search-highlight,
#logs-grid mark.search-highlight {
    background-color: #ffeb3b;
    color: #000;
    padding: 2px 4px;
    border-radius: 2px;
    font-weight: 500;
}

/* ========================================
   统计卡片样式（保留原有）
   ======================================== */
.stats-card {
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-md);
    transition: var(--transition-base);
}

.stats-card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

.stats-card.bg-primary {
    background: var(--gradient-primary) !important;
}

.stats-card.bg-danger {
    background: var(--gradient-danger) !important;
}

.stats-card.bg-warning {
    background: var(--gradient-warning) !important;
    color: #fff;
}

.stats-card.bg-info {
    background: var(--gradient-info) !important;
}

/* ========================================
   日志详情模态框样式（保留原有）
   ======================================== */
.log-detail-modal .modal-content {
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-xl);
}

.log-detail-modal .modal-header {
    background: var(--gradient-primary);
    color: white;
    border-radius: var(--border-radius-lg) var(--border-radius-lg) 0 0;
}

.log-detail-item {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--gray-200);
}

.log-detail-label {
    font-weight: 600;
    color: var(--gray-700);
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.log-code-block,
.log-json-block,
.log-traceback-block {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: var(--border-radius-md);
    padding: 1rem;
    font-family: 'Courier New', Consolas, Monaco, monospace;
    font-size: 0.85rem;
    line-height: 1.4;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 400px;
    overflow-y: auto;
    margin: 0.5rem 0;
}

/* ========================================
   移除原有卡片式布局样式
   ======================================== */
/* 以下样式可以删除或注释掉：
.log-entry
.log-entry-content
.log-cell
.logs-wrapper
等卡片式布局相关样式
*/
```

**注意事项**：
1. 使用 CSS `:has()` 选择器根据级别徽章设置行样式
2. 保留原有的日志级别颜色方案
3. 移除或注释掉原有的卡片式布局样式
4. 保留统计卡片和详情模态框样式

### 5. 服务层调整（可选）

如果需要在 `app/static/js/modules/services/logs_service.js` 中添加新方法：

```javascript
class LogsService {
    constructor(http) {
        this.http = http;
    }

    /**
     * 获取日志列表 - Grid.js 专用
     */
    getLogsList(params = {}) {
        const queryParams = new URLSearchParams(params);
        return this.http.get(`/logs/api/list?${queryParams.toString()}`);
    }

    /**
     * 获取统计信息
     */
    getStats(params = {}) {
        const queryParams = new URLSearchParams(params);
        return this.http.get(`/logs/api/stats?${queryParams.toString()}`);
    }

    /**
     * 获取日志详情
     */
    getLogDetail(logId) {
        return this.http.get(`/logs/api/detail/${logId}`);
    }
}
```

## 实施步骤

### 1. 准备工作
```bash
# 创建功能分支
git checkout -b feature/logs-grid-refactor

# 备份原有文件
cp app/static/js/modules/views/history/logs/logs.js app/static/js/modules/views/history/logs/logs.js.bak
cp app/templates/history/logs/logs.html app/templates/history/logs/logs.html.bak
```

### 2. 后端开发
- [ ] 在 `app/routes/logs.py` 中添加 `/api/list` 端点
- [ ] 确保响应格式符合标准：`{ data: { items, total, page, pages } }`
- [ ] 测试 API 端点：`curl http://localhost:5000/logs/api/list?page=1&limit=50`

### 3. 前端重构
- [ ] 重构 `app/static/js/modules/views/history/logs/logs.js`
  - 移除 LogsStore 相关代码
  - 使用 GridWrapper 初始化表格
  - 实现标准筛选流程
  - 保留行点击查看详情功能
- [ ] 更新 `app/static/js/modules/services/logs_service.js`（可选）

### 4. 模板更新
- [ ] 修改 `app/templates/history/logs/logs.html`
  - 引入 Grid.js 标准资源
  - 替换容器为 `#logs-grid`
  - 移除原有的 `#logsContainer` 和 `#paginationContainer`

### 5. 样式调整
- [ ] 更新 `app/static/css/pages/history/logs.css`
  - 添加 Grid.js 表格样式
  - 实现日志级别行颜色
  - 移除或注释原有卡片式布局样式

### 6. 测试清单
- [ ] **基础功能**
  - [ ] 日志列表正常显示
  - [ ] 分页功能正常
  - [ ] 排序功能正常（如果启用）
- [ ] **筛选功能**
  - [ ] 日志级别筛选
  - [ ] 模块筛选
  - [ ] 时间范围筛选
  - [ ] 关键词搜索
  - [ ] 清空筛选
- [ ] **交互功能**
  - [ ] 点击"详情"按钮查看日志详情
  - [ ] 详情模态框正常显示
  - [ ] 详情模态框显示完整日志信息
  - [ ] 统计面板数据更新
  - [ ] 操作按钮样式正常
- [ ] **视觉效果**
  - [ ] ERROR 日志显示红色
  - [ ] WARNING 日志显示黄色
  - [ ] INFO 日志显示蓝色
  - [ ] DEBUG 日志显示灰色
  - [ ] 行悬停效果正常
- [ ] **性能测试**
  - [ ] 大量日志加载速度
  - [ ] 筛选响应速度
  - [ ] 分页切换流畅度

### 7. 回归测试
- [ ] 搜索、筛选、分页、排序均能触发带参数的 Network 请求
- [ ] 查看详情后关闭模态不会触发无效请求
- [ ] 统计面板数据与筛选条件同步
- [ ] 浏览器控制台无错误信息

### 8. 部署准备
- [ ] 清理备份文件
- [ ] 更新相关文档
- [ ] 提交代码并创建 PR
- [ ] 通知团队强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）

## 注意事项

### 遵循标准规范
1. **禁止修改 GridWrapper**：`app/static/js/common/grid-wrapper.js` 禁止擅自修改，如需扩展功能先讨论评审
2. **命名规范**：所有新增命名需符合 `AGENTS.md` 中的命名规范
3. **接口约定**：严格遵循 `/api/list` 接口返回格式：`{ data: { items, total, page, pages } }`

### 技术要点
4. **保持向后兼容**：保留原有的 `/api/search` 端点，以防其他地方使用
5. **性能考虑**：Grid.js 默认分页大小设为 50，可根据实际情况调整
6. **操作列实现**：新增"操作"列，包含"详情"按钮，通过全局方法 `LogsActions.viewDetail()` 调用
7. **取消行点击**：不再使用行点击事件，改为明确的按钮操作，用户体验更清晰
8. **级别颜色**：通过 CSS `:has()` 选择器实现行级别颜色，确保与原有设计一致
9. **搜索高亮**：暂时保留前端高亮逻辑，后续可能移除（Grid.js 不支持服务端高亮）

### 部署注意
9. **浏览器缓存**：部署后强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）
10. **移动端适配**：Grid.js 支持响应式，但需要测试小屏幕显示效果
11. **统计面板**：统计信息独立更新，不依赖 Grid.js 数据

### 已知限制
12. **LogsStore 移除**：原有的 LogsStore 架构将被完全移除，改用 GridWrapper 直接管理
13. **分页控件**：Grid.js 自带分页，移除原有的自定义分页 HTML
14. **CSS `:has()` 兼容性**：需要现代浏览器支持（Chrome 105+, Firefox 121+, Safari 15.4+）
15. **全局方法暴露**：`LogsActions.viewDetail()` 暴露到全局作用域，供按钮 `onclick` 调用

## 参考资料

### 标准文档
- **Grid.js 迁移标准**：`docs/refactor/gridjs-migration-standard.md`
- **命名规范**：`AGENTS.md`

### 参考实现
- **凭据管理**：`app/templates/credentials/list.html`、`app/static/js/modules/views/credentials/list.js`
- **标签管理**：`app/static/js/modules/views/tags/index.js`
- **用户管理**：`app/static/js/modules/views/auth/list.js`

### 核心组件
- **GridWrapper 封装**：`app/static/js/common/grid-wrapper.js`
- **FilterCard 组件**：`app/static/js/modules/ui/filter-card.js`
- **Grid.js 官方文档**：https://gridjs.io/docs/

## 预期效果

重构完成后，日志中心将具备以下特性：

1. ✅ 统一的表格展示，与其他管理页面风格一致
2. ✅ 保留原有的日志级别颜色区分（ERROR 红色、WARNING 黄色等）
3. ✅ 服务端分页、排序、筛选，性能更优
4. ✅ 新增"操作"列，包含"详情"按钮，操作更明确
5. ✅ 取消行点击，避免误触，用户体验更好
6. ✅ 统计面板实时更新
7. ✅ 代码结构更清晰，易于维护
8. ✅ 符合项目 Grid.js 迁移标准

## 界面对比

### 重构前（卡片式）
- 每条日志显示为独立卡片
- 点击整个卡片查看详情
- 自定义分页控件
- 使用 LogsStore 管理状态

### 重构后（表格式）
- 统一的表格布局，列对齐清晰
- 明确的"详情"按钮，操作更直观
- Grid.js 标准分页
- GridWrapper 直接管理数据
- 保留日志级别行颜色（左侧边框 + 背景色）
