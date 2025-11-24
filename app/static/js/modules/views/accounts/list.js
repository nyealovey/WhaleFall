function mountAccountsListPage() {
    'use strict';

    const global = window;
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
    const exportEndpoint = pageRoot?.dataset.exportUrl || '/api/account-export';

    let accountsGrid = null;
    let accountFilterCard = null;
    let instanceStore = null;
    let instanceService = null;

    ready(() => {
        setDefaultTimeRange();
        initializeInstanceService();
        initializeInstanceStore();
        initializeTagFilter();
        initializeFilterCard();
        initializeGrid();
        bindDatabaseTypeButtons();
        exposeGlobalActions();
    });

    function initializeInstanceService() {
        if (!global.InstanceManagementService) {
            console.warn('InstanceManagementService 未加载，跳过同步能力');
            return;
        }
        try {
            instanceService = new global.InstanceManagementService(global.httpU);
        } catch (error) {
            console.error('初始化 InstanceManagementService 失败:', error);
            instanceService = null;
        }
    }

    function initializeInstanceStore() {
        if (!global.createInstanceStore || !instanceService) {
            return;
        }
        try {
            instanceStore = global.createInstanceStore({
                service: instanceService,
                emitter: global.mitt ? global.mitt() : null,
            });
            instanceStore.init({}).catch((error) => {
                console.warn('InstanceStore 初始化失败', error);
            });
        } catch (error) {
            console.error('初始化 InstanceStore 失败:', error);
            instanceStore = null;
        }
    }

    function initializeGrid() {
        const container = document.getElementById('accounts-grid');
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
    }

    function buildColumns(includeDbTypeColumn) {
        const columns = [
            {
                name: '账户名称',
                id: 'username',
                formatter: (cell) => {
                    if (!gridHtml) {
                        return cell || '-';
                    }
                    return gridHtml(`
                        <div class="d-flex align-items-center">
                            <i class="fas fa-user text-primary me-2"></i>
                            <strong>${escapeHtml(cell || '-')}</strong>
                        </div>
                    `);
                },
            },
            {
                name: '状态',
                id: 'is_locked',
                width: '80px',
                formatter: (cell) => renderStatusBadge(Boolean(cell)),
            },
            {
                name: '分类',
                id: 'classifications',
                sort: false,
                formatter: (cell) => renderClassifications(Array.isArray(cell) ? cell : []),
            },
            {
                name: '实例信息',
                id: 'instance_name',
                formatter: (cell) => {
                    if (!gridHtml) {
                        return cell || '-';
                    }
                    return gridHtml(`
                        <div class="d-flex align-items-center">
                            <i class="fas fa-database text-info me-2"></i>
                            <small class="text-muted">${escapeHtml(cell || '-')}</small>
                        </div>
                    `);
                },
            },
            {
                name: 'IP地址',
                id: 'instance_host',
                formatter: (cell) => (gridHtml ? gridHtml(`<small class="text-muted">${escapeHtml(cell || '-')}</small>`) : cell || '-'),
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
                formatter: (cell) => renderTags(Array.isArray(cell) ? cell : []),
            },
            {
                name: '操作',
                id: 'actions',
                sort: false,
                width: '110px',
                formatter: (cell, row) => renderActions(resolveRowMeta(row)),
            },
            { id: '__meta__', hidden: true }
        );

        return columns;
    }

    function handleServerResponse(includeDbTypeColumn) {
        return (response) => {
            const payload = response?.data || response || {};
            const items = payload.items || [];
            return items.map((item) => {
                const row = [
                    item.username || '-',
                    item.instance_name || '-',
                    item.instance_host || '-',
                    item.tags || [],
                ];
                if (includeDbTypeColumn) {
                    row.push(item.db_type || '-');
                }
                row.push(item.classifications || [], item.is_locked, null, item);
                return row;
            });
        };
    }

    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    function renderTags(tags) {
        if (!gridHtml) {
            return tags.map((tag) => tag.display_name || tag.name).join(', ') || '无标签';
        }
        if (!tags.length) {
            return gridHtml('<span class="text-muted">无标签</span>');
        }
        const content = tags
            .map((tag) => {
                const color = escapeHtml(tag.color || 'secondary');
                const label = escapeHtml(tag.display_name || tag.name || '标签');
                return `<span class="badge bg-${color} me-1 mb-1"><i class="fas fa-tag me-1"></i>${label}</span>`;
            })
            .join('');
        return gridHtml(content);
    }

    function renderClassifications(list) {
        if (!gridHtml) {
            return list.map((item) => item.name).join(', ') || '未分类';
        }
        if (!list.length) {
            return gridHtml('<span class="text-muted">未分类</span>');
        }
        const content = list
            .map((item) => {
                const color = escapeHtml(item.color || '#6c757d');
                const name = escapeHtml(item.name || '分类');
                return `<span class="badge me-1 mb-1" style="background-color: ${color}; color: #fff;">${name}</span>`;
            })
            .join('');
        return gridHtml(content);
    }

    function renderDbTypeBadge(dbType) {
        const map = {
            mysql: { color: 'success', label: 'MySQL', icon: 'fa-database' },
            postgresql: { color: 'primary', label: 'PostgreSQL', icon: 'fa-database' },
            sqlserver: { color: 'warning', label: 'SQL Server', icon: 'fa-server' },
            oracle: { color: 'info', label: 'Oracle', icon: 'fa-database' },
        };
        const normalized = (dbType || '').toLowerCase();
        const meta = map[normalized] || { color: 'secondary', label: (dbType || '').toUpperCase(), icon: 'fa-database' };
        if (!gridHtml) {
            return meta.label || '-';
        }
        return gridHtml(`<span class="badge bg-${meta.color}"><i class="fas ${meta.icon} me-1"></i>${escapeHtml(meta.label || '-')}</span>`);
    }

    function renderStatusBadge(isLocked) {
        if (!gridHtml) {
            return isLocked ? '已锁定' : '正常';
        }
        const color = isLocked ? 'danger' : 'success';
        const text = isLocked ? '已锁定' : '正常';
        return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
    }

    function renderActions(meta) {
        if (!meta?.id) {
            return '';
        }
        if (!gridHtml) {
            return '详情';
        }
        return gridHtml(`
            <button type="button" class="btn btn-outline-primary btn-sm" onclick="AccountsActions.viewPermissions(${meta.id})" title="查看权限">
                <i class="fas fa-eye"></i>
            </button>
        `);
    }

    function initializeFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载');
            return;
        }
        accountFilterCard = factory({
            formSelector: `#${ACCOUNT_FILTER_FORM_ID}`,
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
                const countElement = document.getElementById('selected-tags-count');
                if (countElement) {
                    countElement.textContent = '0';
                }
                const previewElement = document.getElementById('selected-tags-preview');
                if (previewElement) {
                    previewElement.textContent = '未选择标签';
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

    function handleFilterChange(values) {
        if (!accountsGrid) {
            return;
        }
        const filters = normalizeFilters(resolveFilters(values));
        filters.db_type = currentDbType;
        accountsGrid.updateFilters(filters);
        syncUrl(filters);
    }

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

    function collectFormValues() {
        if (accountFilterCard?.serialize) {
            return accountFilterCard.serialize();
        }
        const form = selectOne(`#${ACCOUNT_FILTER_FORM_ID}`).first();
        if (!form) {
            return {};
        }
        const serializer = global.UI?.serializeForm;
        if (serializer) {
            return serializer(form);
        }
        const formData = new FormData(form);
        const result = {};
        formData.forEach((value, key) => {
            if (result[key] === undefined) {
                result[key] = value;
            } else if (Array.isArray(result[key])) {
                result[key].push(value);
            } else {
                result[key] = [result[key], value];
            }
        });
        return result;
    }

    function normalizeFilters(raw) {
        const filters = { ...(raw || {}) };
        Object.keys(filters).forEach((key) => {
            const value = filters[key];
            if (value === undefined || value === null || value === '' || value === 'all' || (Array.isArray(value) && value.length === 0)) {
                delete filters[key];
            }
        });
        return filters;
    }

    function sanitizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        return trimmed || '';
    }

    function sanitizeFlag(value) {
        if (value === 'true' || value === 'false') {
            return value;
        }
        return '';
    }

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

    function bindDatabaseTypeButtons() {
        const buttons = document.querySelectorAll('[data-db-type-btn]');
        buttons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const dbType = button.getAttribute('data-db-type') || 'all';
                switchDatabaseType(dbType);
            });
        });
    }

    function switchDatabaseType(dbType) {
        currentDbType = dbType;
        const filters = normalizeFilters(resolveFilters());
        filters.db_type = dbType;
        const basePath = dbType && dbType !== 'all' ? `/account/${dbType}` : '/account';
        const params = buildSearchParams(filters);
        const query = params.toString();
        global.location.href = query ? `${basePath}?${query}` : basePath;
    }

    function buildBaseUrl() {
        const base = currentDbType && currentDbType !== 'all' ? `/account/api/list?db_type=${encodeURIComponent(currentDbType)}` : '/account/api/list';
        return base.includes('?') ? `${base}&sort=username&order=asc` : `${base}?sort=username&order=asc`;
    }

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

    function syncUrl(filters) {
        if (!global.history?.replaceState) {
            return;
        }
        const params = buildSearchParams(filters);
        const query = params.toString();
        const basePath = currentDbType && currentDbType !== 'all' ? `/account/${currentDbType}` : '/account';
        const nextUrl = query ? `${basePath}?${query}` : basePath;
        global.history.replaceState(null, '', nextUrl);
    }

    function initializeTagFilter() {
        if (!global.TagSelectorHelper) {
            console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
            return;
        }
        const hiddenInput = selectOne('#selected-tag-names');
        const initialValues = parseInitialTagValues(hiddenInput.length ? hiddenInput.attr('value') : null);
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

    function parseInitialTagValues(raw) {
        if (!raw) {
            return [];
        }
        return raw
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean);
    }

    function setDefaultTimeRange() {
        const timeRangeSelect = document.getElementById('time_range');
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

    function updateTotalCount(total) {
        const element = document.getElementById('accounts-total');
        if (element) {
            element.textContent = `共 ${total} 个账户`;
        }
    }

    function exposeGlobalActions() {
        global.AccountsActions = {
            viewPermissions: (accountId) => global.viewAccountPermissions?.(accountId),
            exportCSV: exportAccountsCSV,
        };
        global.syncAllAccounts = syncAllAccounts;
    }

    function exportAccountsCSV() {
        const filters = normalizeFilters(resolveFilters());
        filters.db_type = currentDbType;
        const params = buildSearchParams(filters);
        const base = exportEndpoint || '/api/account-export';
        const query = params.toString();
        const url = query ? `${base}?${query}` : base;
        global.location.href = url;
    }

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
}

window.AccountsListPage = {
    mount: mountAccountsListPage,
};
