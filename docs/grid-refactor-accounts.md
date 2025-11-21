# 账户管理页面 Grid.js 重构方案

> 基于 `docs/refactor/gridjs-migration-standard.md` 标准，将账户管理从传统表格布局迁移到 Grid.js + GridWrapper 统一实现。

## 概述

账户管理页面是系统中最复杂的列表页面之一，包含：
- 数据库类型导航按钮（全部/MySQL/PostgreSQL/Oracle/SQL Server）
- 标签筛选器（多选）
- 分类筛选器
- 搜索功能
- 导出 CSV 功能
- 权限查看功能

本方案在保持所有功能可用的前提下，尽量保证界面一致性。

## 目标

- 使用 Grid.js + GridWrapper 替代传统 HTML 表格
- 遵循 `gridjs-migration-standard.md` 中的接口约定和前端标准流程
- 保留所有现有功能：数据库类型切换、标签筛选、分类筛选、导出CSV
- 保持界面风格一致，特别是数据库类型导航按钮和工具栏
- 优化性能，支持服务端分页和筛选

## 当前实现分析

### 现有结构

**路由**: `app/routes/account.py`
- `GET /account/` 或 `/account/<db_type>` - 账户列表页面
- `GET /account/api/<account_id>/permissions` - 获取账户权限详情

**模板**: `app/templates/accounts/list.html`
- 使用传统 HTML `<table>` 渲染
- 包含数据库类型按钮组
- 包含筛选卡片（搜索、分类、标签）
- 包含导出CSV按钮
- 自定义分页控件

**前端**: `app/static/js/modules/views/accounts/list.js`
- 使用 InstanceStore 管理同步操作
- 使用 TagSelectorHelper 处理标签筛选
- 使用 FilterCard 处理筛选表单
- 通过页面刷新实现筛选

**样式**: `app/static/css/pages/accounts/list.css`
- 表格样式
- 数据库类型按钮样式
- 标签和分类徽章样式

### 页面特点

1. **数据库类型导航**：顶部按钮组，切换不同数据库类型
2. **复杂筛选**：搜索、分类、标签（多选）
3. **工具栏**：包含"导出CSV"按钮和账户总数显示
4. **动态列**：根据是否选择数据库类型，"数据库类型"列动态显示/隐藏
5. **标签显示**：每个账户显示其实例的标签（多个）
6. **分类显示**：每个账户显示其分类（多个，带颜色）
7. **权限查看**：点击按钮查看账户权限详情

## 重构方案

### 1. 后端调整

#### 新增 Grid.js API 端点

在 `app/routes/account.py` 中添加 `/api/list` 端点：

```python
@account_bp.route("/api/list")
@login_required
@view_required
def list_accounts_api() -> tuple[Response, int]:
    """Grid.js 账户列表 API - 符合 gridjs-migration-standard.md 规范"""
    # 标准分页参数
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    sort_field = request.args.get("sort", "username")
    sort_order = request.args.get("order", "asc")
    
    # 业务筛选参数
    db_type = request.args.get("db_type", "").strip()
    search = request.args.get("search", "").strip()
    instance_id = request.args.get("instance_id", type=int)
    is_locked = request.args.get("is_locked", "").strip()
    is_superuser = request.args.get("is_superuser", "").strip()
    classification = request.args.get("classification", "").strip()
    tags = request.args.getlist("tags")
    
    from app.models.instance_account import InstanceAccount
    from app import db
    
    # 构建查询
    query = AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
    query = query.filter(InstanceAccount.is_active.is_(True))
    
    # 数据库类型过滤
    if db_type and db_type != "all":
        query = query.filter(AccountPermission.db_type == db_type)
    
    # 实例过滤
    if instance_id:
        query = query.filter(AccountPermission.instance_id == instance_id)
    
    # 搜索过滤
    if search:
        query = query.join(Instance, AccountPermission.instance_id == Instance.id)
        query = query.filter(
            db.or_(
                AccountPermission.username.contains(search),
                Instance.name.contains(search),
                Instance.host.contains(search)
            )
        )
    
    # 锁定状态过滤
    if is_locked:
        query = query.filter(AccountPermission.is_locked == (is_locked == "true"))
    
    # 超级用户过滤
    if is_superuser:
        query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))
    
    # 标签过滤
    if tags:
        try:
            query = query.join(Instance).join(Instance.tags).filter(Tag.name.in_(tags))
        except Exception as e:
            log_error("标签过滤失败", module="account", tags=tags, error=str(e))
    
    # 分类过滤
    if classification and classification != "all":
        try:
            classification_id = int(classification)
            query = (
                query.join(AccountClassificationAssignment)
                .join(AccountClassification)
                .filter(
                    AccountClassification.id == classification_id,
                    AccountClassificationAssignment.is_active.is_(True)
                )
            )
        except (ValueError, TypeError) as e:
            log_error("分类ID转换失败", module="account", classification=classification, error=str(e))
    
    # 排序
    sortable_fields = {
        "username": AccountPermission.username,
        "db_type": AccountPermission.db_type,
        "is_locked": AccountPermission.is_locked,
        "is_superuser": AccountPermission.is_superuser,
    }
    order_column = sortable_fields.get(sort_field, AccountPermission.username)
    if sort_order == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    # 获取账户分类信息
    classifications = {}
    if pagination.items:
        account_ids = [account.id for account in pagination.items]
        assignments = AccountClassificationAssignment.query.filter(
            AccountClassificationAssignment.account_id.in_(account_ids),
            AccountClassificationAssignment.is_active.is_(True),
        ).all()
        
        for assignment in assignments:
            if assignment.account_id not in classifications:
                classifications[assignment.account_id] = []
            classifications[assignment.account_id].append({
                "name": assignment.classification.name,
                "color": assignment.classification.color_value,
            })
    
    # 构建响应
    items = []
    for account in pagination.items:
        instance = account.instance
        item = {
            "id": account.id,
            "username": account.username,
            "instance_name": instance.name if instance else "未知实例",
            "instance_host": instance.host if instance else "未知主机",
            "db_type": account.db_type,
            "is_locked": account.is_locked,
            "is_superuser": account.is_superuser,
            "tags": [
                {
                    "name": tag.name,
                    "display_name": tag.display_name,
                    "color": tag.color,
                }
                for tag in (instance.tags if instance else [])
            ],
            "classifications": classifications.get(account.id, []),
        }
        items.append(item)
    
    # 标准响应格式
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
- 保留原有的 `list_accounts()` 端点以保持向后兼容
- 新端点 `/api/list` 专门用于 Grid.js
- 响应格式严格遵循标准：`{ data: { items, total, page, pages } }`
- 预加载标签和分类信息，避免 N+1 查询问题


### 2. 前端重构

#### 重构 `app/static/js/modules/views/accounts/list.js`

遵循标准流程，使用 GridWrapper：

```javascript
/**
 * 账户管理页面 - Grid.js 重构版本
 * 遵循 gridjs-migration-standard.md 标准
 */
function mountAccountsListPage() {
    const global = window;
    'use strict';

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

    const ACCOUNT_FILTER_FORM_ID = 'account-filter-form';
    let accountsGrid = null;
    let accountFilterCard = null;
    let instanceStore = null;
    let currentDbType = 'all';

    ready(() => {
        initializePage();
    });

    function initializePage() {
        // 从 URL 或页面数据获取当前数据库类型
        currentDbType = getCurrentDbType();
        
        initializeInstanceStore();
        initializeGrid();
        initializeAccountFilterCard();
        initializeTagFilter();
        bindDatabaseTypeButtons();
        exposeGlobalActions();
    }

    /**
     * 获取当前数据库类型
     */
    function getCurrentDbType() {
        const pathParts = global.location.pathname.split('/');
        const dbType = pathParts[pathParts.length - 1];
        return dbType && dbType !== 'account' ? dbType : 'all';
    }

    /**
     * 初始化 Grid.js - 标准流程
     */
    function initializeGrid() {
        const container = document.getElementById('accounts-grid');
        if (!container) {
            console.warn('找不到 #accounts-grid 容器');
            return;
        }

        // 根据当前数据库类型决定是否显示"数据库类型"列
        const showDbTypeColumn = !currentDbType || currentDbType === 'all';

        const columns = [
            {
                name: '账户名称',
                id: 'username',
                formatter: (cell) => {
                    if (!gridHtml) return cell;
                    return gridHtml(`
                        <div class="d-flex align-items-center">
                            <i class="fas fa-user text-primary me-2"></i>
                            <strong>${escapeHtmlValue(cell)}</strong>
                        </div>
                    `);
                },
            },
            {
                name: '实例信息',
                id: 'instance_name',
                formatter: (cell) => {
                    if (!gridHtml) return cell;
                    return gridHtml(`
                        <div class="d-flex align-items-center">
                            <i class="fas fa-database text-info me-2"></i>
                            <small class="text-muted">${escapeHtmlValue(cell)}</small>
                        </div>
                    `);
                },
            },
            {
                name: 'IP地址',
                id: 'instance_host',
                formatter: (cell) => {
                    if (!gridHtml) return cell;
                    return gridHtml(`<small class="text-muted">${escapeHtmlValue(cell)}</small>`);
                },
            },
            {
                name: '标签',
                id: 'tags',
                sort: false,
                formatter: (cell) => {
                    const tags = Array.isArray(cell) ? cell : [];
                    if (!gridHtml) {
                        return tags.map(t => t.display_name).join(', ') || '无标签';
                    }
                    if (tags.length === 0) {
                        return gridHtml('<span class="text-muted">无标签</span>');
                    }
                    const tagsHtml = tags.map(tag => 
                        `<span class="badge bg-${escapeHtmlValue(tag.color)} me-1 mb-1">
                            <i class="fas fa-tag me-1"></i>${escapeHtmlValue(tag.display_name)}
                        </span>`
                    ).join('');
                    return gridHtml(tagsHtml);
                },
            },
        ];

        // 条件添加"数据库类型"列
        if (showDbTypeColumn) {
            columns.push({
                name: '数据库类型',
                id: 'db_type',
                width: '120px',
                formatter: (cell) => {
                    const dbType = String(cell || '').toLowerCase();
                    const dbTypeMap = {
                        mysql: { label: 'MySQL', color: 'success', icon: 'fa-database' },
                        postgresql: { label: 'PostgreSQL', color: 'primary', icon: 'fa-database' },
                        sqlserver: { label: 'SQL Server', color: 'warning', icon: 'fa-server' },
                        oracle: { label: 'Oracle', color: 'info', icon: 'fa-database' },
                    };
                    const config = dbTypeMap[dbType] || { label: dbType.toUpperCase(), color: 'secondary', icon: 'fa-database' };
                    if (!gridHtml) return config.label;
                    return gridHtml(`
                        <span class="badge bg-${config.color}">
                            <i class="fas ${config.icon} me-1"></i>${config.label}
                        </span>
                    `);
                },
            });
        }

        // 继续添加其他列
        columns.push(
            {
                name: '分类',
                id: 'classifications',
                sort: false,
                formatter: (cell) => {
                    const classifications = Array.isArray(cell) ? cell : [];
                    if (!gridHtml) {
                        return classifications.map(c => c.name).join(', ') || '未分类';
                    }
                    if (classifications.length === 0) {
                        return gridHtml('<span class="text-muted">未分类</span>');
                    }
                    const classHtml = classifications.map(cls =>
                        `<span class="badge me-1 mb-1" style="background-color: ${escapeHtmlValue(cls.color || '#6c757d')}; color: white;">
                            ${escapeHtmlValue(cls.name)}
                        </span>`
                    ).join('');
                    return gridHtml(classHtml);
                },
            },
            {
                name: '状态',
                id: 'is_locked',
                width: '100px',
                formatter: (cell) => {
                    const isLocked = Boolean(cell);
                    if (!gridHtml) return isLocked ? '已锁定' : '正常';
                    const color = isLocked ? 'danger' : 'success';
                    const text = isLocked ? '已锁定' : '正常';
                    return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
                },
            },
            {
                name: '操作',
                id: 'actions',
                width: '100px',
                sort: false,
                formatter: (cell, row) => {
                    const meta = row?.cells?.[row.cells.length - 1]?.data || {};
                    const accountId = meta.id;
                    if (!gridHtml) return '查看';
                    return gridHtml(`
                        <button type="button" 
                                class="btn btn-sm btn-outline-primary" 
                                onclick="AccountsActions.viewPermissions(${accountId})"
                                title="查看权限">
                            <i class="fas fa-eye"></i>
                        </button>
                    `);
                },
            }
        );

        accountsGrid = new GridWrapper(container, {
            search: false,
            sort: false,
            columns: columns,
            server: {
                url: `/account/api/list?sort=username&order=asc&db_type=${currentDbType}`,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                then: (response) => {
                    const payload = response?.data || response || {};
                    const items = payload.items || [];
                    return items.map((item) => {
                        const row = [
                            item.username || '-',
                            item.instance_name || '-',
                            item.instance_host || '-',
                            item.tags || [],
                        ];
                        
                        // 条件添加数据库类型
                        if (showDbTypeColumn) {
                            row.push(item.db_type || '-');
                        }
                        
                        row.push(
                            item.classifications || [],
                            item.is_locked,
                            null, // 操作列占位
                            item  // 元数据
                        );
                        
                        return row;
                    });
                },
                total: (response) => {
                    const payload = response?.data || response || {};
                    return payload.total || 0;
                },
            },
        });

        // 标准流程：初始化筛选
        const initialFilters = normalizeFilters(resolveFormValues());
        accountsGrid.init();
        if (initialFilters && Object.keys(initialFilters).length > 0) {
            accountsGrid.setFilters(initialFilters);
        }
    }

    /**
     * 绑定数据库类型按钮点击事件
     */
    function bindDatabaseTypeButtons() {
        const buttons = document.querySelectorAll('[data-db-type-btn]');
        buttons.forEach(button => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const dbType = button.getAttribute('data-db-type') || 'all';
                switchDatabaseType(dbType);
            });
        });
    }

    /**
     * 切换数据库类型
     */
    function switchDatabaseType(dbType) {
        currentDbType = dbType;
        const filters = normalizeFilters(resolveFormValues());
        filters.db_type = dbType;
        
        // 更新 URL
        const basePath = '/account';
        const newPath = dbType === 'all' ? basePath : `${basePath}/${dbType}`;
        const params = buildSearchParams(filters);
        const query = params.toString();
        global.location.href = query ? `${newPath}?${query}` : newPath;
    }

    /**
     * 初始化筛选卡片
     */
    function initializeAccountFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载');
            return;
        }

        accountFilterCard = factory({
            formSelector: `#${ACCOUNT_FILTER_FORM_ID}`,
            autoSubmitOnChange: true,
            onSubmit: ({ values }) => applyAccountFilters(values),
            onClear: () => applyAccountFilters({}),
            onChange: ({ values }) => applyAccountFilters(values),
        });
    }

    /**
     * 应用筛选
     */
    function applyAccountFilters(values) {
        if (!accountsGrid) return;

        const rawValues = values && Object.keys(values || {}).length
            ? values
            : collectFormValues();

        const filters = normalizeFilters(rawValues);
        filters.db_type = currentDbType;

        // 标准流程：调用 updateFilters
        accountsGrid.updateFilters(filters);
    }

    /**
     * 规范化筛选参数
     */
    function normalizeFilters(rawValues) {
        const filters = {
            search: rawValues?.search,
            classification: rawValues?.classification,
            tags: rawValues?.tags,
            instance_id: rawValues?.instance_id,
            is_locked: rawValues?.is_locked,
            is_superuser: rawValues?.is_superuser,
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
        if (accountFilterCard?.serialize) {
            return accountFilterCard.serialize();
        }

        const form = selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
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
     * 构建查询参数
     */
    function buildSearchParams(filters) {
        const params = new URLSearchParams();
        Object.entries(filters || {}).forEach(([key, value]) => {
            if (value === undefined || value === null) return;
            if (Array.isArray(value)) {
                value.forEach((item) => params.append(key, item));
            } else {
                params.append(key, value);
            }
        });
        return params;
    }

    /**
     * 初始化标签筛选器
     */
    function initializeTagFilter() {
        if (!global.TagSelectorHelper) {
            console.warn('TagSelectorHelper 未加载');
            return;
        }

        const hiddenInput = selectOne('#selected-tag-names');
        const initialValues = parseInitialTagValues(
            hiddenInput.length ? hiddenInput.attr('value') : null
        );

        global.TagSelectorHelper.setupForForm({
            modalSelector: '#tagSelectorModal',
            rootSelector: '[data-tag-selector]',
            openButtonSelector: '#open-tag-filter-btn',
            previewSelector: '#selected-tags-preview',
            countSelector: '#selected-tags-count',
            chipsSelector: '#selected-tags-chips',
            hiddenInputSelector: '#selected-tag-names',
            hiddenValueKey: 'name',
            initialValues,
            onConfirm: () => {
                if (accountFilterCard?.emit) {
                    accountFilterCard.emit('change', {
                        source: 'account-tag-selector',
                    });
                }
            },
        });
    }

    /**
     * 解析标签初始值
     */
    function parseInitialTagValues(rawValue) {
        if (!rawValue) return [];
        return rawValue.split(',').map((v) => v.trim()).filter(Boolean);
    }

    /**
     * 初始化实例 Store（用于同步操作）
     */
    function initializeInstanceStore() {
        if (!global.createInstanceStore) {
            console.warn('createInstanceStore 未加载');
            return;
        }

        const InstanceManagementService = global.InstanceManagementService;
        if (!InstanceManagementService) {
            console.warn('InstanceManagementService 未加载');
            return;
        }

        try {
            const instanceService = new InstanceManagementService(global.httpU);
            instanceStore = global.createInstanceStore({
                service: instanceService,
                emitter: global.mitt ? global.mitt() : null,
            });
            instanceStore.init({}).catch((error) => {
                console.warn('InstanceStore 初始化失败', error);
            });
        } catch (error) {
            console.error('初始化 InstanceStore 失败:', error);
        }
    }

    /**
     * 同步所有账户
     */
    function syncAllAccounts(trigger) {
        const button = trigger instanceof Element ? trigger : global.event?.target;
        const buttonWrapper = button ? from(button) : null;
        const originalText = buttonWrapper ? buttonWrapper.html() : null;

        if (buttonWrapper) {
            buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
            buttonWrapper.attr('disabled', 'disabled');
        }

        const InstanceManagementService = global.InstanceManagementService;
        if (!InstanceManagementService) {
            global.toast?.error?.('实例管理服务未初始化');
            return;
        }

        const instanceService = new InstanceManagementService(global.httpU);
        const request = instanceStore
            ? instanceStore.actions.syncAllAccounts()
            : instanceService.syncAllAccounts();

        return request
            .then((data) => {
                if (data.success) {
                    global.toast?.success?.(data.message || '批量同步任务已启动');
                    if (data.data?.manual_job_id) {
                        global.toast?.info?.(`任务线程: ${data.data.manual_job_id}`);
                    }
                    // 刷新表格
                    setTimeout(() => {
                        accountsGrid?.refresh?.();
                    }, 2000);
                } else if (data.error) {
                    global.toast?.error?.(data.error);
                }
            })
            .catch((error) => {
                console.error('账户同步失败:', error);
                global.toast?.error?.('同步失败');
            })
            .finally(() => {
                if (buttonWrapper) {
                    buttonWrapper.html(originalText || '同步');
                    buttonWrapper.attr('disabled', null);
                }
            });
    }

    /**
     * 查看账户权限
     */
    function viewAccountPermissions(accountId) {
        // 调用权限查看模态框
        if (global.viewAccountPermissions) {
            global.viewAccountPermissions(accountId);
        } else {
            console.warn('权限查看功能未加载');
        }
    }

    /**
     * 导出 CSV
     */
    function exportAccountsCSV() {
        const filters = normalizeFilters(resolveFormValues());
        filters.db_type = currentDbType;
        
        const params = buildSearchParams(filters);
        const url = `/files/export_accounts?${params.toString()}`;
        global.location.href = url;
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

    /**
     * 暴露全局操作方法
     */
    function exposeGlobalActions() {
        global.AccountsActions = {
            viewPermissions: viewAccountPermissions,
            exportCSV: exportAccountsCSV,
        };
        global.syncAllAccounts = syncAllAccounts;
    }
}

window.AccountsListPage = {
    mount: mountAccountsListPage,
};
```

**关键变更**：
1. 移除页面刷新，改用 `accountsGrid.updateFilters()`
2. 数据库类型切换仍然通过 URL 实现（保持原有逻辑）
3. 动态列：根据 `currentDbType` 决定是否显示"数据库类型"列
4. 保留 InstanceStore 用于同步操作
5. 保留 TagSelectorHelper 用于标签筛选
6. 导出CSV功能保持不变


### 3. 模板调整

#### 修改 `app/templates/accounts/list.html`

按照标准引入 Grid.js 资源，保留数据库类型按钮和工具栏：

```html
{% extends "base.html" %}
{% from 'components/filters/macros.html' import filter_card, search_input, classification_filter, tag_selector_filter %}

{% block title %}账户管理 - 鲸落{% endblock %}

{% block extra_css %}
<!-- 标准 Grid.js 样式 -->
<link rel="stylesheet" href="{{ url_for('static', filename='vendor/gridjs/mermaid.min.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/pages/accounts/list.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/tag-selector.css') }}">
{% endblock %}

{% block content %}
<!-- 页面头部 -->
<div class="page-header">
    <div class="container">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h2><i class="fas fa-users me-2"></i>账户管理</h2>
                <p class="mb-0">管理数据库账户信息和权限</p>
            </div>
            <div class="btn-group">
                <a href="{{ url_for('account_stat.statistics') }}" class="btn btn-outline-light">
                    <i class="fas fa-chart-bar me-2"></i>账户统计
                </a>
                <button type="button" class="btn btn-light" onclick="syncAllAccounts()">
                    <i class="fas fa-sync me-2"></i>同步所有账户
                </button>
            </div>
        </div>
    </div>
</div>

<div class="container-fluid">
    <!-- 搜索和筛选 -->
    <div class="accounts-page">
        {% call filter_card(form_id='account-filter-form', action='#', auto_register=False) %}
            {{ search_input(value=search, placeholder='搜索账户 / 实例') }}
            {{ classification_filter(classification_options, classification) }}
            {{ tag_selector_filter(tag_options, selected_tags, field_id='account-tag-selector') }}
        {% endcall %}
    </div>

    <!-- 数据库类型切换按钮 -->
    <div class="row mb-3">
        <div class="col-12">
            <div class="btn-group" role="group">
                <button type="button" 
                        class="btn {% if not current_db_type or current_db_type == 'all' %}btn-primary{% else %}btn-outline-primary border-2 fw-bold{% endif %}"
                        data-db-type-btn
                        data-db-type="all">
                    <i class="fas fa-database me-1"></i>全部
                </button>
                {% for db_type in database_type_options %}
                <button type="button"
                        class="btn {% if current_db_type == db_type.value %}btn-primary{% else %}btn-outline-primary border-2 fw-bold{% endif %}"
                        data-db-type-btn
                        data-db-type="{{ db_type.value }}">
                    <i class="fas {{ db_type.icon }} me-1"></i>{{ db_type.label }}
                </button>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- 账户列表 - Grid.js 容器 -->
    <div class="card">
        <div class="card-body">
            <!-- 工具栏 -->
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div class="d-flex align-items-center">
                    <span class="text-muted">账户管理</span>
                    <button type="button" 
                            class="btn btn-outline-primary btn-sm ms-3"
                            onclick="AccountsActions.exportCSV()">
                        <i class="fas fa-download me-1"></i>导出CSV
                    </button>
                </div>
                <div class="text-muted" id="accounts-total">
                    加载中...
                </div>
            </div>

            <!-- Grid.js 容器 -->
            <div id="accounts-grid"></div>
        </div>
    </div>
</div>

{% include 'components/permission_modal.html' %}
{% endblock %}

{% block extra_js %}
<div id="list-page-tag-selector">
    {% include 'components/tag_selector.html' %}
</div>
<!-- 标准 Grid.js 脚本 -->
<script src="{{ url_for('static', filename='vendor/gridjs/gridjs.umd.js') }}"></script>
<script src="{{ url_for('static', filename='js/common/grid-wrapper.js') }}"></script>
<!-- 业务脚本 -->
<script src="{{ url_for('static', filename='js/modules/services/instance_management_service.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/stores/instance_store.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/views/components/permissions/permission-viewer.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/views/components/permissions/permission-modal.js') }}"></script>
<script src="{{ url_for('static', filename='js/modules/views/accounts/list.js') }}"></script>
<script src="{{ url_for('static', filename='js/bootstrap/accounts/list.js') }}"></script>
{% endblock %}
```

**关键变更**：
1. 移除原有的 `<table>` 和自定义分页
2. 使用 `#accounts-grid` 作为 Grid.js 容器
3. 保留数据库类型按钮组，添加 `data-db-type-btn` 属性
4. 保留工具栏（导出CSV按钮）
5. 保留筛选卡片和标签选择器
6. 按标准顺序引入脚本


### 4. 样式调整

#### 修改 `app/static/css/pages/accounts/list.css`

添加 Grid.js 相关样式，保留原有组件样式：

```css
/* ========================================
   Grid.js 表格基础样式
   ======================================== */
#accounts-grid .gridjs-wrapper {
    border-radius: var(--border-radius-md);
    overflow: hidden;
}

#accounts-grid .gridjs-table {
    width: 100%;
}

/* ========================================
   列样式
   ======================================== */
/* 账户名称列 */
#accounts-grid td[data-column-id="username"] {
    font-weight: 500;
}

/* 实例信息列 */
#accounts-grid td[data-column-id="instance_name"],
#accounts-grid td[data-column-id="instance_host"] {
    font-size: 0.9rem;
}

/* 标签列 */
#accounts-grid td[data-column-id="tags"] {
    white-space: normal;
    line-height: 1.8;
}

#accounts-grid td[data-column-id="tags"] .badge {
    font-size: 0.75rem;
    padding: 4px 8px;
}

/* 数据库类型列 */
#accounts-grid td[data-column-id="db_type"] {
    text-align: center;
}

#accounts-grid td[data-column-id="db_type"] .badge {
    font-size: 0.75rem;
    padding: 4px 10px;
    min-width: 90px;
}

/* 分类列 */
#accounts-grid td[data-column-id="classifications"] {
    white-space: normal;
    line-height: 1.8;
}

#accounts-grid td[data-column-id="classifications"] .badge {
    font-size: 0.75rem;
    padding: 4px 8px;
}

/* 状态列 */
#accounts-grid td[data-column-id="is_locked"] {
    text-align: center;
}

#accounts-grid td[data-column-id="is_locked"] .badge {
    font-size: 0.75rem;
    padding: 4px 10px;
    min-width: 60px;
}

/* 操作列 */
#accounts-grid td[data-column-id="actions"] {
    text-align: center;
    white-space: nowrap;
}

#accounts-grid td[data-column-id="actions"] .btn {
    font-size: 0.875rem;
    padding: 0.25rem 0.75rem;
}

/* ========================================
   行交互样式
   ======================================== */
#accounts-grid tbody tr:hover {
    background-color: var(--gray-100);
    box-shadow: var(--shadow-sm);
}

/* ========================================
   数据库类型按钮组样式（保留原有）
   ======================================== */
.btn-group [data-db-type-btn] {
    transition: all 0.2s ease;
}

.btn-group [data-db-type-btn]:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.btn-group [data-db-type-btn].btn-primary {
    font-weight: 600;
}

/* ========================================
   工具栏样式
   ======================================== */
.card-body > .d-flex.justify-content-between {
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--gray-200);
    margin-bottom: var(--spacing-md);
}

#accounts-total {
    font-size: 0.9rem;
    font-weight: 500;
}

/* ========================================
   标签和分类徽章样式（保留原有）
   ======================================== */
.badge {
    font-weight: 500;
    letter-spacing: 0.3px;
}

.badge i {
    font-size: 0.85em;
}

/* ========================================
   响应式调整
   ======================================== */
@media (max-width: 768px) {
    /* 数据库类型按钮组在小屏幕上垂直排列 */
    .btn-group {
        flex-direction: column;
        width: 100%;
    }
    
    .btn-group [data-db-type-btn] {
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    /* 工具栏在小屏幕上垂直排列 */
    .card-body > .d-flex.justify-content-between {
        flex-direction: column;
        align-items: flex-start !important;
    }
    
    .card-body > .d-flex.justify-content-between > div {
        margin-bottom: 0.5rem;
    }
}

/* ========================================
   移除原有表格样式
   ======================================== */
/* 以下样式可以删除或注释掉：
.table-responsive
.table.table-hover
等传统表格相关样式
*/
```

**注意事项**：
1. 保留数据库类型按钮组样式
2. 保留工具栏样式
3. 保留标签和分类徽章样式
4. 添加响应式支持
5. 移除或注释原有的传统表格样式


## 实施步骤

### 1. 准备工作
```bash
# 创建功能分支
git checkout -b feature/accounts-grid-refactor

# 备份原有文件
cp app/routes/account.py app/routes/account.py.bak
cp app/static/js/modules/views/accounts/list.js app/static/js/modules/views/accounts/list.js.bak
cp app/templates/accounts/list.html app/templates/accounts/list.html.bak
```

### 2. 后端开发
- [ ] 在 `app/routes/account.py` 中添加 `/api/list` 端点
- [ ] 确保响应格式符合标准：`{ data: { items, total, page, pages } }`
- [ ] 预加载标签和分类信息，避免 N+1 查询
- [ ] 测试 API 端点：`curl http://localhost:5000/account/api/list?page=1&limit=20`

### 3. 前端重构
- [ ] 重构 `app/static/js/modules/views/accounts/list.js`
  - 使用 GridWrapper 初始化表格
  - 实现动态列（根据数据库类型）
  - 保留数据库类型切换逻辑
  - 保留标签筛选器集成
  - 保留同步功能
  - 实现导出CSV功能

### 4. 模板更新
- [ ] 修改 `app/templates/accounts/list.html`
  - 引入 Grid.js 标准资源
  - 替换容器为 `#accounts-grid`
  - 保留数据库类型按钮组
  - 保留工具栏（导出CSV）
  - 保留筛选卡片
  - 移除原有的 `<table>` 和分页

### 5. 样式调整
- [ ] 更新 `app/static/css/pages/accounts/list.css`
  - 添加 Grid.js 表格样式
  - 保留数据库类型按钮样式
  - 保留工具栏样式
  - 保留标签和分类徽章样式
  - 添加响应式支持
  - 移除或注释原有表格样式

### 6. 测试清单
- [ ] **基础功能**
  - [ ] 账户列表正常显示
  - [ ] 分页功能正常
  - [ ] 排序功能正常（如果启用）
- [ ] **数据库类型切换**
  - [ ] 点击"全部"按钮显示所有账户
  - [ ] 点击"MySQL"按钮只显示MySQL账户
  - [ ] 点击"PostgreSQL"按钮只显示PostgreSQL账户
  - [ ] 点击"Oracle"按钮只显示Oracle账户
  - [ ] 点击"SQL Server"按钮只显示SQL Server账户
  - [ ] 切换后"数据库类型"列动态显示/隐藏
- [ ] **筛选功能**
  - [ ] 搜索功能（账户名/实例名/IP）
  - [ ] 分类筛选
  - [ ] 标签筛选（多选）
  - [ ] 清空筛选
  - [ ] 筛选与数据库类型切换联动
- [ ] **工具栏功能**
  - [ ] 导出CSV按钮正常工作
  - [ ] 导出CSV包含当前筛选条件
  - [ ] 账户总数显示正确
  - [ ] 同步所有账户按钮正常工作
- [ ] **交互功能**
  - [ ] 点击"查看权限"按钮显示权限详情
  - [ ] 权限模态框正常显示
  - [ ] 标签显示正确（多个标签）
  - [ ] 分类显示正确（多个分类，带颜色）
  - [ ] 状态徽章显示正确（正常/已锁定）
- [ ] **视觉效果**
  - [ ] 数据库类型按钮高亮正确
  - [ ] 标签颜色显示正确
  - [ ] 分类颜色显示正确
  - [ ] 行悬停效果正常
  - [ ] 响应式布局正常（移动端）

### 7. 回归测试
- [ ] 搜索、筛选、分页均能触发带参数的 Network 请求
- [ ] 数据库类型切换通过 URL 实现，支持浏览器前进/后退
- [ ] 标签筛选器确认后触发表格刷新
- [ ] 同步操作后表格自动刷新
- [ ] 导出CSV包含当前所有筛选条件
- [ ] 浏览器控制台无错误信息

### 8. 部署准备
- [ ] 清理备份文件
- [ ] 更新相关文档
- [ ] 提交代码并创建 PR
- [ ] 通知团队强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）

## 注意事项

### 遵循标准规范
1. **禁止修改 GridWrapper**：`app/static/js/common/grid-wrapper.js` 禁止擅自修改
2. **命名规范**：所有新增命名需符合 `AGENTS.md` 中的命名规范
3. **接口约定**：严格遵循 `/api/list` 接口返回格式

### 技术要点
4. **保持向后兼容**：保留原有的 `list_accounts()` 端点
5. **动态列实现**：根据 `currentDbType` 动态添加/移除"数据库类型"列
6. **数据库类型切换**：通过 URL 实现，保持原有逻辑，支持浏览器历史记录
7. **标签筛选集成**：保留 TagSelectorHelper，确认后触发 FilterCard 的 change 事件
8. **导出CSV**：保持原有逻辑，通过 URL 参数传递筛选条件
9. **同步功能**：保留 InstanceStore，同步后自动刷新表格

### 性能优化
10. **预加载关联数据**：在后端 API 中预加载标签和分类，避免 N+1 查询
11. **分页大小**：默认 20 条/页，可根据实际情况调整
12. **筛选防抖**：搜索输入框使用 400ms 防抖

### 界面一致性
13. **数据库类型按钮**：保持原有样式和交互，高亮当前选中类型
14. **工具栏位置**：保持在表格上方，包含导出CSV和账户总数
15. **标签和分类显示**：保持原有的徽章样式和颜色
16. **响应式布局**：确保在移动端正常显示

### 已知限制
17. **数据库类型切换**：仍然通过 URL 实现，会触发页面刷新（保持原有逻辑）
18. **动态列**：Grid.js 不支持运行时动态添加/移除列，需要重新初始化
19. **标签筛选**：依赖 TagSelectorHelper，需要确保该组件正常加载

## 参考资料

### 标准文档
- **Grid.js 迁移标准**：`docs/refactor/gridjs-migration-standard.md`
- **命名规范**：`AGENTS.md`

### 参考实现
- **凭据管理**：`app/templates/credentials/list.html`、`app/static/js/modules/views/credentials/list.js`
- **标签管理**：`app/static/js/modules/views/tags/index.js`
- **用户管理**：`app/static/js/modules/views/auth/list.js`
- **日志中心**：`docs/grid-refactor-logs.md`

### 核心组件
- **GridWrapper 封装**：`app/static/js/common/grid-wrapper.js`
- **FilterCard 组件**：`app/static/js/modules/ui/filter-card.js`
- **TagSelectorHelper**：`app/static/js/modules/views/components/tag-selector-helper.js`
- **Grid.js 官方文档**：https://gridjs.io/docs/

## 预期效果

重构完成后，账户管理页面将具备以下特性：

1. ✅ 统一的表格展示，与其他管理页面风格一致
2. ✅ 保留所有现有功能：数据库类型切换、标签筛选、分类筛选、导出CSV
3. ✅ 服务端分页、排序、筛选，性能更优
4. ✅ 动态列：根据数据库类型自动显示/隐藏"数据库类型"列
5. ✅ 保持界面一致性：数据库类型按钮、工具栏、标签和分类显示
6. ✅ 明确的"查看权限"按钮，操作更直观
7. ✅ 代码结构更清晰，易于维护
8. ✅ 符合项目 Grid.js 迁移标准

## 界面对比

### 重构前（传统表格）
- 使用 HTML `<table>` 渲染
- 自定义分页控件
- 通过页面刷新实现筛选
- 数据库类型切换通过 URL

### 重构后（Grid.js）
- 统一的 Grid.js 表格布局
- Grid.js 标准分页
- 通过 GridWrapper 实现筛选（无需刷新）
- 数据库类型切换仍通过 URL（保持原有逻辑）
- 保留所有原有功能和界面元素
- 动态列支持

## 特殊说明

### 为什么数据库类型切换仍使用 URL？

1. **保持原有逻辑**：数据库类型是页面的核心筛选维度，通过 URL 实现有以下优势：
   - 支持浏览器前进/后退
   - 支持书签和分享
   - 与现有路由结构一致（`/account/mysql`、`/account/postgresql` 等）

2. **动态列实现**：Grid.js 不支持运行时动态添加/移除列，切换数据库类型需要重新初始化表格，通过 URL 刷新页面是最简单可靠的方式

3. **用户体验**：数据库类型切换是低频操作，页面刷新的影响可以接受

### 导出CSV如何实现？

导出CSV保持原有逻辑：
1. 收集当前所有筛选条件（包括数据库类型、搜索、分类、标签等）
2. 构建带参数的导出URL：`/files/export_accounts?db_type=mysql&search=xxx&...`
3. 通过 `window.location.href` 触发下载

这种方式简单可靠，无需修改后端导出逻辑。
