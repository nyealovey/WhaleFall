/**
 * 挂载账户列表页面。
 *
 * 初始化账户列表页面的所有组件，包括数据表格、筛选器、标签选择器、
 * 数据库类型切换按钮和导出功能。
 *
 * @param {Window} [context=window] 全局上下文，便于测试注入。
 * @returns {void}
 */
function mountAccountsListPage(context) {
    'use strict';

    const global = context || window;
    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载账户列表页面');
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
    const AUTO_APPLY_FILTER_CHANGE = true;
    const pageRoot = document.getElementById('accounts-page-root');
    let currentDbType = pageRoot?.dataset.currentDbType || 'all';
    const exportEndpoint = pageRoot?.dataset.exportUrl || '/api/v1/files/account-export';

    let accountsGrid = null;
    let accountFilterCard = null;
    let instanceStore = null;
    let instanceService = null;
    let gridActionDelegationBound = false;

    /**
     * 初始化实例管理服务。
     *
     * @param {Object} [options={}] 可选配置。
     * @param {Window} [options.windowRef=global] 自定义上下文。
     * @returns {void}
     */
    function initializeInstanceService(options = {}) {
        const host = options.windowRef || global;
        if (!host.InstanceManagementService) {
            console.warn('InstanceManagementService 未加载，跳过同步能力');
            return;
        }
        try {
            instanceService = new host.InstanceManagementService(host.httpU);
        } catch (error) {
            console.error('初始化 InstanceManagementService 失败:', error);
            instanceService = null;
        }
    }

    /**
     * 初始化实例状态管理器。
     *
     * @param {Object} [options={}] 可选配置。
     * @param {Window} [options.windowRef=global] 自定义上下文。
     * @returns {void}
     */
    function initializeInstanceStore(options = {}) {
        const host = options.windowRef || global;
        if (!host.createInstanceStore || !instanceService) {
            return;
        }
        try {
            instanceStore = host.createInstanceStore({
                service: instanceService,
                emitter: host.mitt ? host.mitt() : null,
            });
            instanceStore.init({}).catch((error) => {
                console.warn('InstanceStore 初始化失败', error);
            });
        } catch (error) {
            console.error('初始化 InstanceStore 失败:', error);
            instanceStore = null;
        }
    }

    /**
     * 初始化账户数据表格。
     *
     * 创建 Grid.js 表格实例，配置列定义、服务端数据源和分页。
     *
     * @param {Object} [options={}] 表格配置。
     * @param {string} [options.containerSelector="#accounts-grid"] 容器选择器。
     * @returns {void}
     */
    function initializeGrid(options = {}) {
        const container = document.querySelector(options.containerSelector || '#accounts-grid');
        if (!container) {
            console.warn('未找到 accounts-grid 容器');
            return;
        }
        const showDbTypeColumn = !currentDbType || currentDbType === 'all';
        const columns = buildColumns(showDbTypeColumn);

        accountsGrid = new GridWrapper(container, {
            search: false,
            sort: false,
            columns,
            server: {
                url: buildBaseUrl(),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                then: handleServerResponse(showDbTypeColumn),
                total: (response) => {
                    const payload = response?.data || response || {};
                    const total = payload.total || 0;
                    updateTotalCount(total);
                    return total;
                },
            },
        });
        const initialFilters = normalizeFilters(resolveFilters());
        initialFilters.db_type = currentDbType;
        accountsGrid.setFilters(initialFilters, { silent: true });
        accountsGrid.init();
        bindGridActionDelegation(container);
    }

    /**
     * 构建表格列定义。
     *
     * @param {boolean} includeDbTypeColumn 是否包含数据库类型列。
     * @returns {Array<Object>} 列定义数组。
     */
    function buildColumns(includeDbTypeColumn) {
        const CHIP_COLUMN_WIDTH = '220px';

        const columns = [
            {
                name: '账户/实例',
                id: 'username',
                formatter: (cell, row) => renderAccountCell(resolveRowMeta(row)),
            },
            {
                name: '可用性',
                id: 'is_locked',
                width: '70px',
                formatter: (cell) => renderStatusBadge(Boolean(cell)),
            },
            {
                name: '是否删除',
                id: 'is_deleted',
                width: '70px',
                formatter: (cell) => renderDeletionBadge(Boolean(cell)),
            },
            {
                name: '是否超极',
                id: 'is_superuser',
                width: '70px',
                formatter: (cell) => renderSuperuserBadge(Boolean(cell)),
            },
            {
                name: '分类',
                id: 'classifications',
                sort: false,
                width: CHIP_COLUMN_WIDTH,
                formatter: (cell) => renderClassifications(Array.isArray(cell) ? cell : []),
            },
        ];

        if (includeDbTypeColumn) {
            columns.push({
                name: '数据库类型',
                id: 'db_type',
                width: '120px',
                formatter: (cell) => renderDbTypeBadge(cell),
            });
        }

        columns.push(
            {
                name: '标签',
                id: 'tags',
                sort: false,
                width: CHIP_COLUMN_WIDTH,
                formatter: (cell) => renderTags(Array.isArray(cell) ? cell : []),
            },
            {
                name: '操作',
                id: 'actions',
                sort: false,
                width: '70px',
                formatter: (cell, row) => renderActions(resolveRowMeta(row)),
            },
            { id: '__meta__', hidden: true }
        );

        return columns;
    }

    /**
     * 处理服务端响应数据。
     *
     * @param {boolean} includeDbTypeColumn 是否包含数据库类型列。
     * @returns {Function} 响应处理函数。
     */
    function handleServerResponse(includeDbTypeColumn) {
        return (response) => {
            const payload = response?.data || response || {};
            const items = payload.items || [];
            return items.map((item) => {
                const row = [
                    item.username || '-',
                    item.is_locked,
                    item.is_deleted,
                    item.is_superuser,
                    item.classifications || [],
                ];
                if (includeDbTypeColumn) {
                    row.push(item.db_type || '-');
                }
                row.push(item.tags || [], null, item);
                return row;
            });
        };
    }

    /**
     * 从 gridjs 行中取出附加的 meta 数据。
     *
     * @param {Object} row gridjs 行对象。
     * @returns {Object} 元信息。
     */
    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    /**
     * 渲染标签列。
     *
     * @param {Array<Object>} tags 标签集合。
     * @returns {string|Object} Grid.js 解析的 HTML。
     */
    function renderTags(tags) {
        if (!gridHtml) {
            return tags.map((tag) => tag.display_name || tag.name).join(', ') || '无标签';
        }
        if (!tags.length) {
            return gridHtml('<span class="text-muted">无标签</span>');
        }
        const names = tags
            .map((tag) => tag?.display_name || tag?.name)
            .filter((name) => typeof name === 'string' && name.trim().length > 0);
        return renderChipStack(names, {
            emptyText: '无标签',
            baseClass: 'ledger-chip',
            counterClass: 'ledger-chip ledger-chip--counter',
            maxItems: Number.POSITIVE_INFINITY,
        });
    }

    /**
     * 渲染账户名称与实例信息。
     *
     * @param {Object} meta 行元数据。
     * @returns {string|Object} Grid.js HTML。
     */
    function renderAccountCell(meta = {}) {
        if (!gridHtml) {
            return meta.username || '-';
        }
        const username = escapeHtml(meta.username || '-');
        const instanceName = escapeHtml(meta.instance_name || '未知实例');
        const host = escapeHtml(meta.instance_host || '-');
        return gridHtml(`
            <div>
                <strong>${username}</strong>
                <div class="small account-instance-meta">
                    <i class="fas fa-database account-instance-icon me-1" aria-hidden="true"></i>${instanceName} · ${host}
                </div>
            </div>
        `);
    }

    /**
     * 渲染分类徽章列表。
     *
     * @param {Array<Object>} list 分类数组。
     * @returns {string|Object} HTML 片段。
     */
    function renderClassifications(list) {
        if (!gridHtml) {
            return list.map((item) => item.name).join(', ') || '未分类';
        }
        const names = list
            .map((item) => item?.name)
            .filter((name) => typeof name === 'string' && name.trim().length > 0);
        return renderChipStack(names, {
            emptyText: '未分类',
            baseClass: 'chip-outline',
            baseModifier: 'chip-outline--muted',
            counterClass: 'chip-outline chip-outline--muted chip-outline--ghost',
        });
    }

    /**
     * 渲染数据库类型徽章。
     *
     * @param {string} dbType 数据库类型。
     * @returns {string|Object} 徽章 HTML。
     */
    const UNSAFE_KEYS = ['__proto__', 'prototype', 'constructor'];
    const ALLOWED_FILTER_KEYS = [
        'username',
        'email',
        'role',
        'status',
        'db_type',
        'instance_name',
        'cluster',
        'search',
        'page',
        'page_size',
        'sort',
        'direction',
    ];
    const isSafeKey = (key) => typeof key === 'string' && !UNSAFE_KEYS.includes(key);
    const isAllowedFilterKey = (key) => isSafeKey(key) && ALLOWED_FILTER_KEYS.includes(key);

    function assignFilterField(target, key, value) {
        switch (key) {
            case 'username':
                target.username = value;
                break;
            case 'email':
                target.email = value;
                break;
            case 'role':
                target.role = value;
                break;
            case 'status':
                target.status = value;
                break;
            case 'db_type':
                target.db_type = value;
                break;
            case 'instance_name':
                target.instance_name = value;
                break;
            case 'cluster':
                target.cluster = value;
                break;
            case 'search':
                target.search = value;
                break;
            case 'page':
                target.page = value;
                break;
            case 'page_size':
                target.page_size = value;
                break;
            case 'sort':
                target.sort = value;
                break;
            case 'direction':
                target.direction = value;
                break;
            default:
                break;
        }
    }

    function getFilterField(target, key) {
        switch (key) {
            case 'username':
                return target.username;
            case 'email':
                return target.email;
            case 'role':
                return target.role;
            case 'status':
                return target.status;
            case 'db_type':
                return target.db_type;
            case 'instance_name':
                return target.instance_name;
            case 'cluster':
                return target.cluster;
            case 'search':
                return target.search;
            case 'page':
                return target.page;
            case 'page_size':
                return target.page_size;
            case 'sort':
                return target.sort;
            case 'direction':
                return target.direction;
            default:
                return undefined;
        }
    }

    function renderDbTypeBadge(dbType) {
        const typeStr = typeof dbType === 'string' ? dbType : String(dbType || '');
        const normalized = typeStr.toLowerCase();
        let meta;
        if (isSafeKey(normalized)) {
            switch (normalized) {
                case 'mysql':
                    meta = { color: 'success', label: 'MySQL', icon: 'fa-database' };
                    break;
                case 'postgresql':
                    meta = { color: 'primary', label: 'PostgreSQL', icon: 'fa-database' };
                    break;
                case 'sqlserver':
                    meta = { color: 'warning', label: 'SQL Server', icon: 'fa-server' };
                    break;
                case 'oracle':
                    meta = { color: 'info', label: 'Oracle', icon: 'fa-database' };
                    break;
                default:
                    meta = null;
                    break;
            }
        }
        if (!meta) {
            meta = { color: 'secondary', label: typeStr.toUpperCase() || '-', icon: 'fa-database' };
        }
        if (!gridHtml) {
            return meta.label || '-';
        }
        const label = escapeHtml(meta.label || '-');
        return gridHtml(`<span class="chip-outline chip-outline--brand" data-db-type="${escapeHtml(normalized)}"><i class="fas ${meta.icon} me-1" aria-hidden="true"></i>${label}</span>`);
    }

    /**
     * 渲染锁定状态标签。
     *
     * @param {boolean} isLocked 是否锁定。
     * @returns {string|Object} 徽章 HTML。
     */
    function renderStatusBadge(isLocked) {
        const text = isLocked ? '锁定' : '正常';
        const variant = isLocked ? 'danger' : 'success';
        const icon = isLocked ? 'fa-lock' : 'fa-check';
        return renderStatusPill(text, variant, icon);
    }

    /**
     * 渲染删除状态徽章。
     *
     * @param {boolean} isDeleted 是否被删除。
     * @returns {string|Object} 徽章 HTML。
     */
    function renderDeletionBadge(isDeleted) {
        const text = isDeleted ? '已删除' : '正常';
        const variant = isDeleted ? 'danger' : 'muted';
        const icon = isDeleted ? 'fa-trash' : 'fa-check';
        return renderStatusPill(text, variant, icon);
    }

    /**
     * 渲染超级管理员徽章。
     *
     * @param {boolean} isSuperuser 是否为超级管理员。
     * @returns {string|Object} 徽章 HTML。
     */
    function renderSuperuserBadge(isSuperuser) {
        const text = isSuperuser ? '是' : '否';
        const variant = isSuperuser ? 'warning' : 'muted';
        const icon = isSuperuser ? 'fa-crown' : null;
        return renderStatusPill(text, variant, icon);
    }

    /**
     * 渲染中性色芯片栈，自动折叠超出项。
     *
     * @param {string[]} names 标签/分类名称集合。
     * @param {Object} [options] 渲染选项。
     * @param {string} [options.emptyText='无数据'] 无数据时的展示文本。
     * @param {string} [options.baseClass='ledger-chip'] 主芯片基础类。
     * @param {string} [options.baseModifier=''] 主芯片附加类。
     * @param {string} [options.counterClass='ledger-chip ledger-chip--counter'] 计数芯片类。
     * @param {number} [options.maxItems=2] 单个芯片展示的最大标签数。
     * @returns {string|Object} Grid.js HTML。
     */
    function renderChipStack(names, options = {}) {
        const {
            emptyText = '无数据',
            baseClass = 'ledger-chip',
            baseModifier = '',
            counterClass = 'ledger-chip ledger-chip--counter',
            maxItems = 2,
        } = options;

        const sanitized = (names || [])
            .filter((name) => typeof name === 'string' && name.trim().length > 0)
            .map((name) => escapeHtml(name.trim()));
        if (!sanitized.length) {
            return gridHtml ? gridHtml(`<span class="text-muted">${emptyText}</span>`) : emptyText;
        }
        if (!gridHtml) {
            return sanitized.join(', ');
        }
        const limit = Number.isFinite(maxItems) ? maxItems : sanitized.length;
        const visibleItems = sanitized.slice(0, limit);
        const visible = visibleItems.join(' · ');
        const baseClasses = [baseClass, baseModifier].filter(Boolean).join(' ').trim();
        const chips = [`<span class="${baseClasses}">${visible}</span>`];
        if (sanitized.length > limit) {
            const rest = sanitized.length - limit;
            chips.push(`<span class="${counterClass}">+${rest}</span>`);
        }
        return gridHtml(`<div class="ledger-chip-stack">${chips.join('')}</div>`);
    }

    /**
     * 统一渲染状态 Pill。
     *
     * @param {string} text 展示文案。
     * @param {string} [variant='muted'] 颜色风格，对应 CSS 修饰。
     * @param {string|null} [icon] FontAwesome 图标类。
     * @returns {string|Object} 渲染结果。
     */
    function renderStatusPill(text, variant = 'muted', icon) {
        if (!gridHtml) {
            return text;
        }
        const classes = ['status-pill'];
        if (variant) {
            classes.push(`status-pill--${variant}`);
        }
        const iconHtml = icon ? `<i class="fas ${icon}" aria-hidden="true"></i>` : '';
        return gridHtml(`<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '')}</span>`);
    }

    /**
     * 渲染操作列按钮。
     *
     * @param {Object} meta 行元信息。
     * @returns {string|Object} 操作列 HTML。
     */
    function renderActions(meta) {
        if (!meta?.id) {
            return '';
        }
        if (!gridHtml) {
            return '详情';
        }
        return gridHtml(`
            <button type="button" class="btn btn-outline-primary btn-sm" data-action="view-permissions" data-account-id="${meta.id}" title="查看权限">
                <i class="fas fa-eye"></i>
            </button>
        `);
    }

    /**
     * 初始化账户筛选卡片，接管 onSubmit/onChange 行为。
     *
     * @returns {void}
     */
    /**
     * 初始化账户筛选卡片，接管 onSubmit/onChange 行为。
     *
     * @param {Object} [options={}] 自定义 UI 参数。
     * @param {Window} [options.windowRef=global] 自定义上下文。
     * @param {string} [options.formSelector] 表单选择器。
     * @returns {void}
     */
    function initializeFilterCard(options = {}) {
        const factory = (options.windowRef || global).UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载');
            return;
        }
        accountFilterCard = factory({
            formSelector: options.formSelector || `#${ACCOUNT_FILTER_FORM_ID}`,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => handleFilterChange(values),
            onClear: () => {
                // 清除标签选择器
                const hiddenInput = document.getElementById('selected-tag-names');
                if (hiddenInput) {
                    hiddenInput.value = '';
                }
                // 清除标签显示
                const chipsContainer = document.getElementById('selected-tags-chips');
                if (chipsContainer) {
                    chipsContainer.innerHTML = '';
                }
                const previewElement = document.getElementById('selected-tags-preview');
                if (previewElement) {
                    previewElement.style.display = 'none';
                }
                // 刷新页面
                window.location.href = window.location.pathname;
            },
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    handleFilterChange(values);
                }
            },
        });
    }

    /**
     * 根据筛选值刷新 URL 并触发重载。
     *
     * @param {Object} values 表单值。
     * @returns {void}
     */
    function handleFilterChange(values) {
        if (!accountsGrid) {
            return;
        }
        const filters = normalizeFilters(resolveFilters(values));
        filters.db_type = currentDbType;
        accountsGrid.updateFilters(filters);
        syncUrl(filters);
    }

    /**
     * 统一解析筛选字段，支持覆盖值。
     *
     * @param {Object} [overrideValues] 覆盖值。
     * @returns {Object} 标准化后的过滤条件。
     */
    function resolveFilters(overrideValues) {
        const values =
            overrideValues && Object.keys(overrideValues || {}).length
                ? overrideValues
                : collectFormValues();
        return {
            search: sanitizeText(values?.search || values?.q),
            classification: sanitizeText(values?.classification),
            tags: normalizeArrayValue(values?.tags),
            instance_id: sanitizeText(values?.instance_id),
            is_locked: sanitizeFlag(values?.is_locked),
            is_superuser: sanitizeFlag(values?.is_superuser),
        };
    }

    /**
     * 收集筛选表单字段。
     *
     * @returns {Object} 表单值。
     */
    /**
     * 收集筛选表单字段。
     *
     * @param {HTMLFormElement} [formElement] 可选表单对象。
     * @returns {Object} 表单值。
     */
    function collectFormValues(formElement) {
        if (accountFilterCard?.serialize) {
            return accountFilterCard.serialize();
        }
        const form = formElement || selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (!form) {
            return {};
        }
        const serializer = global.UI?.serializeForm;
        if (serializer) {
            return serializer(form);
        }
        const formData = new FormData(form);
        const result = Object.create(null);
        formData.forEach((value, key) => {
            if (!isAllowedFilterKey(key)) {
                return;
            }
            const normalized = value instanceof File ? value.name : value;
            const existing = getFilterField(result, key);
            if (existing === undefined) {
                assignFilterField(result, key, normalized);
            } else if (Array.isArray(existing)) {
                existing.push(normalized);
                assignFilterField(result, key, existing);
            } else {
                assignFilterField(result, key, [existing, normalized]);
            }
        });
        return result;
    }

    /**
     * 移除空或默认值，生成最终 filters。
     *
     * @param {Object} raw 原始过滤条件。
     * @returns {Object} 清理后的过滤条件。
     */
    function normalizeFilters(raw) {
        const filters = raw || {};
        const cleaned = Object.create(null);
        const entries = Object.entries(filters).filter(([key]) => isAllowedFilterKey(key));
        entries.forEach(([key, value]) => {
            const emptyArray = Array.isArray(value) && value.length === 0;
            if (value === undefined || value === null || value === '' || value === 'all' || emptyArray) {
                return;
            }
            assignFilterField(cleaned, key, value);
        });
        return cleaned;
    }

    /**
     * 去除文本前后空格，不合法时返回空字符串。
     *
     * @param {string} value 原始值。
     * @returns {string} 清洗后的值。
     */
    function sanitizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        return trimmed || '';
    }

    /**
     * 将布尔字符串标准化为 'true'/'false'。
     *
     * @param {string} value 原始值。
     * @returns {string} 标准化后的布尔字符串。
     */
    function sanitizeFlag(value) {
        if (value === 'true' || value === 'false') {
            return value;
        }
        return '';
    }

    /**
     * 规范化数组输入，兼容逗号分隔字符串。
     *
     * @param {string|Array} value 原始数组值。
     * @returns {Array<string>} 过滤后的数组。
     */
    function normalizeArrayValue(value) {
        if (!value) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.filter((item) => item && item.trim());
        }
        if (typeof value === 'string') {
            return value
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean);
        }
        return [];
    }

    /**
     * 绑定数据库类型切换按钮点击事件。
     *
     * @returns {void}
     */
    /**
     * 绑定数据库类型切换按钮点击事件。
     *
     * @param {string} [selector='[data-db-type-btn]'] 按钮选择器。
     * @returns {void}
     */
    function bindDatabaseTypeButtons(selector = '[data-db-type-btn]') {
        const buttons = document.querySelectorAll(selector);
        buttons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const dbType = button.getAttribute('data-db-type') || 'all';
                switchDatabaseType(dbType);
            });
        });
    }

    /**
     * 切换视图并刷新 URL 中的 db_type。
     *
     * @param {string} dbType 目标数据库类型。
     * @returns {void}
     */
    function switchDatabaseType(dbType) {
        currentDbType = dbType;
        const filters = normalizeFilters(resolveFilters());
        filters.db_type = dbType;
        const basePath = dbType && dbType !== 'all'
            ? `/accounts/ledgers/${dbType}`
            : '/accounts/ledgers';
        const params = buildSearchParams(filters);
        const query = params.toString();
        global.location.href = query ? `${basePath}?${query}` : basePath;
    }

    /**
     * 构造账户列表 API 基础 URL。
     *
     * @returns {string} 带排序参数的基础地址。
     */
    /**
     * 构造账户列表 API 基础 URL。
     *
     * @param {Object} [config={}] 配置项。
     * @param {string} [config.dbType=currentDbType] 数据库类型过滤。
     * @returns {string} 带排序参数的基础地址。
     */
    function buildBaseUrl(config = {}) {
        const dbType = config.dbType ?? currentDbType;
        const base = dbType && dbType !== 'all'
            ? `/api/v1/accounts/ledgers?db_type=${encodeURIComponent(dbType)}`
            : '/api/v1/accounts/ledgers';
        return base.includes('?') ? `${base}&sort=username&order=asc` : `${base}?sort=username&order=asc`;
    }

    /**
     * 将过滤条件转为 URL 查询参数。
     *
     * @param {Object} filters 过滤条件。
     * @returns {URLSearchParams} 查询对象。
     */
    function buildSearchParams(filters) {
        const params = new URLSearchParams();
        Object.entries(filters || {}).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '') {
                return;
            }
            if (Array.isArray(value)) {
                value.forEach((item) => params.append(key, item));
            } else {
                params.append(key, value);
            }
        });
        return params;
    }

    /**
     * 使用 history.replaceState 同步地址栏。
     *
     * @param {Object} filters 过滤条件。
     * @returns {void}
     */
    function syncUrl(filters) {
        if (!global.history?.replaceState) {
            return;
        }
        const params = buildSearchParams(filters);
        const query = params.toString();
        const basePath = currentDbType && currentDbType !== 'all'
            ? `/accounts/ledgers/${currentDbType}`
            : '/accounts/ledgers';
        const nextUrl = query ? `${basePath}?${query}` : basePath;
        global.history.replaceState(null, '', nextUrl);
    }

    /**
     * 初始化标签筛选器交互。
     *
     * @returns {void}
     */
    /**
     * 初始化标签筛选器交互。
     *
     * @param {Object} [options={}] 自定义参数。
     * @param {Window} [options.windowRef=global] TagSelector 来源。
     * @param {string} [options.hiddenInputSelector='#selected-tag-names'] 隐藏字段。
     * @returns {void}
     */
    function initializeTagFilter(options = {}) {
        const host = options.windowRef || global;
        if (!host.TagSelectorHelper) {
            console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
            return;
        }
        const hiddenInput = selectOne(options.hiddenInputSelector || '#selected-tag-names');
        const initialValues = parseInitialTagValues(hiddenInput.length ? hiddenInput.attr('value') : null);
        host.TagSelectorHelper.setupForForm({
            modalSelector: options.modalSelector || '#tagSelectorModal',
            rootSelector: options.rootSelector || '[data-tag-selector]',
            openButtonSelector: options.openButtonSelector || '#open-tag-filter-btn',
            previewSelector: options.previewSelector || '#selected-tags-preview',
            chipsSelector: options.chipsSelector || '#selected-tags-chips',
            hiddenInputSelector: options.hiddenInputSelector || '#selected-tag-names',
            hiddenValueKey: 'name',
            initialValues,
            onConfirm: () => {
                try {
                    if (accountFilterCard?.emit) {
                        accountFilterCard.emit('change', { source: 'account-tag-selector' });
                    } else {
                        handleFilterChange(resolveFilters());
                    }
                } catch (error) {
                    console.error('应用标签筛选失败:', error);
                    handleFilterChange(resolveFilters());
                }
            },
        });
    }

    /**
     * 解析初始标签值（JSON/逗号分隔）。
     *
     * @param {string|null} raw 原始字符串。
     * @returns {Array<string>} 标签数组。
     */
    function parseInitialTagValues(raw) {
        if (!raw) {
            return [];
        }
        return raw
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean);
    }

    /**
     * 若未选择时间范围则回填默认值。
     *
     * @returns {void}
     */
    /**
     * 若未选择时间范围则回填默认值。
     *
     * @param {HTMLSelectElement} [selectElement] 可选下拉。
     * @returns {void}
     */
    function setDefaultTimeRange(selectElement) {
        const timeRangeSelect = selectElement || document.getElementById('time_range');
        if (!timeRangeSelect) {
            return;
        }
        if (timeRangeSelect.tomselect) {
            if (!timeRangeSelect.tomselect.getValue()) {
                timeRangeSelect.tomselect.setValue('1d', true);
            }
            return;
        }
        if (!timeRangeSelect.value) {
            timeRangeSelect.value = '1d';
        }
    }

    /**
     * 更新表格上方的总数提示。
     *
     * @param {number} total 账户总数。
     * @returns {void}
     */
    function updateTotalCount(total) {
        const element = document.getElementById('accounts-total');
        if (element) {
            element.textContent = `共 ${total} 个账户`;
        }
    }

    /**
     * 将新实现暴露到全局命名空间，兼容旧模板。
     *
     * @returns {void}
     */
    /**
     * 将新实现暴露到全局命名空间，兼容旧模板。
     *
     * @param {Window|Object} [target=global] 命名空间对象。
     * @returns {void}
     */
    /**
     * 查看账户权限的统一入口。
     *
     * @param {number|string} accountId 账户 ID。
     * @param {HTMLElement|EventTarget} [trigger] 触发元素。
     * @param {Window|Object} [host=global] 运行上下文。
     * @returns {void}
     */
    function handleViewPermissions(accountId, trigger, host = global) {
        const viewer = host.viewAccountPermissions;
        if (typeof viewer !== 'function') {
            console.error('viewAccountPermissions 未注册');
            return;
        }
        viewer(accountId, {
            apiUrl: `/api/v1/accounts/ledgers/${accountId}/permissions`,
            trigger,
        });
    }

    /**
     * 依据当前过滤条件导出账户列表。
     *
     * @returns {void}
     */
    /**
     * 依据当前过滤条件导出账户列表。
     *
     * @param {Object} [options={}] 导出配置。
     * @param {string} [options.dbType=currentDbType] 指定数据库类型。
     * @param {string} [options.endpoint=exportEndpoint] 导出 API。
     * @returns {void}
     */
    function exportAccountsCSV(options = {}) {
        const filters = normalizeFilters(resolveFilters());
        filters.db_type = options.dbType ?? currentDbType;
        const params = buildSearchParams(filters);
        const base = options.endpoint || exportEndpoint || '/api/v1/files/account-export';
        const query = params.toString();
        const url = query ? `${base}?${query}` : base;
        global.location.href = url;
    }

    /**
     * 调用批量同步接口，并在按钮上展示 loading。
     *
     * @param {Element|EventTarget} trigger 触发按钮或事件 target。
     * @returns {void}
     */
    function syncAllAccounts(trigger) {
        const button = trigger instanceof Element ? trigger : global.event?.target;
        const wrapper = button ? from(button) : null;
        const original = wrapper ? wrapper.html() : null;
        if (wrapper) {
            wrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
            wrapper.attr('disabled', 'disabled');
        }
        const request = instanceStore?.actions?.syncAllAccounts?.() || instanceService?.syncAllAccounts?.();
        Promise.resolve(request)
            .then((result) => {
                if (result?.success) {
                    global.toast?.success?.(result.message || '批量同步任务已启动');
                    setTimeout(() => {
                        accountsGrid?.refresh?.();
                    }, 1500);
                } else if (result?.error) {
                    global.toast?.error?.(result.error);
                }
            })
            .catch((error) => {
                console.error('账户同步失败:', error);
                global.toast?.error?.('同步失败');
            })
            .finally(() => {
                if (wrapper) {
                    wrapper.html(original || '同步所有账户');
                    wrapper.attr('disabled', null);
                }
            });
    }

    /**
     * 简单 HTML 转义，用于渲染徽章文本。
     *
     * @param {*} value 原始文本。
     * @returns {string} 转义后的字符串。
     */
    function escapeHtml(value) {
        if (value === undefined || value === null) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    ready(() => {
        setDefaultTimeRange();
        initializeInstanceService();
        initializeInstanceStore();
        initializeTagFilter();
        initializeFilterCard();
        initializeGrid();
        bindDatabaseTypeButtons();
        bindTemplateActions();
    });

    /**
     * 绑定模板动作按钮，替代内联 onclick。
     *
     * @returns {void}
     */
    function bindTemplateActions() {
        const syncButton = selectOne('[data-action="sync-all-accounts"]');
        if (syncButton.length) {
            syncButton.on('click', async (event) => {
                event?.preventDefault?.();
                const confirmDanger = global.UI?.confirmDanger;
                if (typeof confirmDanger !== 'function') {
                    global.toast?.error?.('确认组件未初始化');
                    return;
                }

                const confirmed = await confirmDanger({
                    title: '确认同步所有账户',
                    message: '该操作将触发全量账户同步任务，请确认影响范围与资源消耗后继续。',
                    details: [
                        { label: '影响范围', value: '对全部实例执行账户同步', tone: 'warning' },
                        { label: '资源消耗', value: '可能占用较多数据库资源，建议低峰期执行', tone: 'warning' },
                    ],
                    confirmText: '开始同步',
                    confirmButtonClass: 'btn-warning',
                    resultUrl: '/history/sessions',
                    resultText: '前往会话中心查看同步进度',
                });
                if (!confirmed) {
                    return;
                }
                syncAllAccounts(event.currentTarget || event);
            });
        }
        const exportButton = selectOne('[data-action="export-accounts-csv"]');
        if (exportButton.length) {
            exportButton.on('click', (event) => {
                event?.preventDefault?.();
                exportAccountsCSV();
            });
        }
    }

    /**
     * 绑定 Grid 内按钮动作，替代字符串 onclick。
     *
     * @param {HTMLElement} container grid 容器。
     * @returns {void}
     */
    function bindGridActionDelegation(container) {
        if (!container || gridActionDelegationBound) {
            return;
        }
        container.addEventListener('click', (event) => {
            const actionBtn = event.target.closest('[data-action]');
            if (!actionBtn || !container.contains(actionBtn)) {
                return;
            }
            const action = actionBtn.getAttribute('data-action');
            if (action === 'view-permissions') {
                event.preventDefault();
                const accountId = actionBtn.getAttribute('data-account-id');
                handleViewPermissions(accountId, actionBtn);
            }
        });
        gridActionDelegationBound = true;
    }
}

window.AccountsListPage = {
    mount: mountAccountsListPage,
};
