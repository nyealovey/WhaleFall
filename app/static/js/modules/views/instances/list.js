function mountInstancesListPage() {
    'use strict';

    const global = window;
    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载实例列表页面');
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

    const { ready, selectOne, select } = helpers;
    const gridHtml = gridjs.html;

    const INSTANCE_FILTER_FORM_ID = 'instance-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    const pageRoot = document.getElementById('instances-page-root');
    if (!pageRoot) {
        console.warn('未找到实例列表根元素');
        return;
    }

    const exportEndpoint = pageRoot.dataset.exportUrl || '/files/export_instances';
    const canManage = pageRoot.dataset.canManage === 'true';
    const detailBase = pageRoot.dataset.detailBase || '/instances';
    const dbTypeMap = safeParseJSON(pageRoot.dataset.dbTypeMap || '{}', {});

    let instancesGrid = null;
    let instanceFilterCard = null;
    let instanceStore = null;
    let instanceService = null;
    let managementService = null;
    let instanceModalController = null;
    let batchCreateController = null;
    let selectedInstanceIds = new Set();

    ready(() => {
        initializeServices();
        initializeInstanceStore();
        initializeModals();
        initializeTagFilter();
        initializeFilterCard();
        initializeGrid();
        bindToolbarActions();
        subscribeToStoreEvents();
        exposeGlobalActions();
    });

    function initializeServices() {
        if (global.InstanceService) {
            try {
                instanceService = new global.InstanceService(global.httpU);
            } catch (error) {
                console.error('初始化 InstanceService 失败:', error);
                instanceService = null;
            }
        }
        if (global.InstanceManagementService) {
            try {
                managementService = new global.InstanceManagementService(global.httpU);
            } catch (error) {
                console.error('初始化 InstanceManagementService 失败:', error);
                managementService = null;
            }
        }
    }

    function initializeInstanceStore() {
        if (!global.createInstanceStore || !managementService) {
            return;
        }
        try {
            instanceStore = global.createInstanceStore({
                service: managementService,
                emitter: global.mitt ? global.mitt() : null,
            });
            instanceStore
                .init({})
                .then((state) => {
                    selectedInstanceIds = new Set(state?.selection || []);
                })
                .catch((error) => {
                    console.warn('InstanceStore 初始化失败', error);
                });
        } catch (error) {
            console.error('创建 InstanceStore 失败:', error);
            instanceStore = null;
        }
    }

    function initializeModals() {
        if (global.InstanceModals?.createController) {
            try {
                instanceModalController = global.InstanceModals.createController();
                instanceModalController.init?.();
            } catch (error) {
                console.error('实例模态初始化失败:', error);
                instanceModalController = null;
            }
        }
        if (global.BatchCreateInstanceModal?.createController) {
            try {
                batchCreateController = global.BatchCreateInstanceModal.createController({
                    instanceService,
                    getInstanceStore: () => instanceStore,
                });
            } catch (error) {
                console.error('批量创建模态初始化失败:', error);
                batchCreateController = null;
            }
        }
    }

    function initializeGrid() {
        const container = document.getElementById('instances-grid');
        if (!container) {
            console.warn('未找到 instances-grid 容器');
            return;
        }

        instancesGrid = new GridWrapper(container, {
            search: false,
            columns: buildColumns(),
            server: {
                url: buildBaseUrl(),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                then: handleServerResponse,
                total: (response) => {
                    const payload = response?.data || response || {};
                    const total = payload.total || 0;
                    updateInstanceTotal(total);
                    return total;
                },
            },
        });

        const initialFilters = normalizeFilters(resolveFilters());
        instancesGrid.setFilters(initialFilters, { silent: true });
        instancesGrid.init();

        if (instancesGrid.grid?.on) {
            instancesGrid.grid.on('ready', handleGridUpdated);
            instancesGrid.grid.on('updated', handleGridUpdated);
        }
    }

    function buildColumns() {
        const columns = [];

        if (canManage) {
            columns.push({
                id: 'select',
                name: gridHtml('<input type="checkbox" class="form-check-input" id="grid-select-all">'),
                width: '48px',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const id = meta?.id ?? '';
                    return gridHtml(
                        `<input type="checkbox" class="form-check-input grid-instance-checkbox" value="${id}">`,
                    );
                },
            });
        }

        columns.push(
            {
                id: 'name',
                name: '名称',
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    if (!gridHtml) {
                        return cell || '-';
                    }
                    const host = escapeHtml(meta.host || '');
                    const name = escapeHtml(cell || '-');
                    return gridHtml(`
                        <div class="d-flex align-items-start">
                            <i class="fas fa-database text-primary me-2 mt-1"></i>
                            <div>
                                <div class="fw-semibold">${name}</div>
                                <small class="text-muted">${host}</small>
                            </div>
                        </div>
                    `);
                },
            },
            {
                id: 'db_type',
                name: '类型',
                width: '120px',
                formatter: (cell) => renderDbTypeBadge(cell),
            },
            {
                id: 'main_version',
                name: '版本信息',
                width: '120px',
                formatter: (cell) => {
                    if (!gridHtml) {
                        return cell || '未检测';
                    }
                    if (!cell) {
                        return gridHtml('<small class="text-muted">未检测</small>');
                    }
                    return gridHtml(`<span class="badge bg-primary">${escapeHtml(cell)}</span>`);
                },
            },
            {
                id: 'active_counts',
                name: '活跃',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const dbCount = meta.active_db_count || 0;
                    const accountCount = meta.active_account_count || 0;
                    if (!gridHtml) {
                        return `${dbCount}/${accountCount}`;
                    }
                    return gridHtml(`
                        <div class="d-flex align-items-center">
                            <span class="badge bg-primary me-2 stat-badge">
                                <i class="fas fa-database me-1"></i>${dbCount}
                            </span>
                            <span class="badge bg-info text-white stat-badge">
                                <i class="fas fa-user me-1"></i>${accountCount}
                            </span>
                        </div>
                    `);
                },
            },
            {
                id: 'tags',
                name: '标签',
                sort: false,
                formatter: (cell, row) => renderTags(resolveRowMeta(row).tags || []),
            },
            {
                id: 'status',
                name: '状态',
                width: '100px',
                formatter: (cell, row) => renderStatusBadge(Boolean(resolveRowMeta(row).is_active)),
            },
            {
                id: 'last_sync_time',
                name: '最后同步',
                width: '150px',
                formatter: (cell) => renderLastSync(cell),
            },
            {
                id: 'actions',
                name: '操作',
                sort: false,
                width: '180px',
                formatter: (cell, row) => renderActions(resolveRowMeta(row)),
            },
            { id: '__meta__', hidden: true },
        );

        return columns;
    }

    function handleServerResponse(response) {
        const payload = response?.data || response || {};
        const items = payload.items || [];
        if (instanceStore?.actions?.setAvailableInstances) {
            const metaList = items.map((item) => ({
                id: item.id,
                name: item.name,
                dbType: item.db_type,
            }));
            instanceStore.actions.setAvailableInstances(metaList);
        }
        return items.map((item) => {
            const row = [];
            if (canManage) {
                row.push(null);
            }
            row.push(
                item.name || '-',
                item.db_type || '-',
                item.main_version || '',
                null,
                item.tags || [],
                item.is_active,
                item.last_sync_time || '',
                null,
                item,
            );
            return row;
        });
    }

    function renderDbTypeBadge(dbType) {
        const meta = dbTypeMap[dbType] || {};
        if (!gridHtml) {
            return meta.display_name || dbType || '-';
        }
        const color = meta.color || 'secondary';
        const icon = meta.icon || 'fa-database';
        const label = meta.display_name || (dbType ? dbType.toUpperCase() : '-');
        return gridHtml(`<span class="badge bg-${color}"><i class="fas ${icon} me-1"></i>${escapeHtml(label)}</span>`);
    }

    function renderTags(tags) {
        if (!gridHtml) {
            return (tags || []).map((tag) => tag.display_name || tag.name).join(', ') || '无标签';
        }
        if (!tags.length) {
            return gridHtml('<span class="text-muted">无标签</span>');
        }
        return gridHtml(
            tags
                .map((tag) => {
                    const color = escapeHtml(tag.color || 'secondary');
                    const label = escapeHtml(tag.display_name || tag.name || '标签');
                    return `<span class="badge bg-${color} me-1 mb-1"><i class="fas fa-tag me-1"></i>${label}</span>`;
                })
                .join(''),
        );
    }

    function renderStatusBadge(isActive) {
        if (!gridHtml) {
            return isActive ? '正常' : '禁用';
        }
        const color = isActive ? 'success' : 'danger';
        const text = isActive ? '正常' : '禁用';
        return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
    }

    function renderLastSync(timestamp) {
        if (!gridHtml) {
            return timestamp || '暂无同步记录';
        }
        if (!timestamp) {
            return gridHtml('<small class="text-muted">暂无同步记录</small>');
        }
        return gridHtml(`<small class="text-muted">${escapeHtml(formatTimestamp(timestamp))}</small>`);
    }

    function renderActions(meta) {
        if (!gridHtml) {
            return '';
        }
        const buttons = [
            `<a href="${detailBase}/${meta.id}" class="btn btn-outline-primary btn-sm" title="查看详情"><i class="fas fa-eye"></i></a>`,
            `<button type="button" class="btn btn-outline-success btn-sm" onclick="InstanceListActions.testConnection(${meta.id}, this)" title="测试连接"><i class="fas fa-plug"></i></button>`,
        ];
        if (canManage) {
            buttons.push(
                `<button type="button" class="btn btn-outline-warning btn-sm" onclick="InstanceListActions.openEdit(${meta.id})" title="编辑"><i class="fas fa-edit"></i></button>`,
            );
            buttons.push(
                `<button type="button" class="btn btn-outline-info btn-sm" onclick="InstanceListActions.sync(${meta.id}, this)" title="同步账户"><i class="fas fa-sync"></i></button>`,
            );
        }
        return gridHtml(`<div class="btn-group btn-group-sm" role="group">${buttons.join('')}</div>`);
    }

    function handleGridUpdated() {
        syncSelectionCheckboxes();
    }

    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    function initializeFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载');
            return;
        }
        instanceFilterCard = factory({
            formSelector: `#${INSTANCE_FILTER_FORM_ID}`,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => handleFilterChange(values),
            onClear: () => handleFilterChange({}),
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    handleFilterChange(values);
                }
            },
        });
    }

    function handleFilterChange(values) {
        if (!instancesGrid) {
            return;
        }
        const filters = normalizeFilters(resolveFilters(values));
        instancesGrid.updateFilters(filters);
        instanceStore?.actions?.applyFilters?.(filters);
        syncUrl(filters);
    }

    function resolveFilters(overrideValues) {
        const values =
            overrideValues && Object.keys(overrideValues || {}).length
                ? overrideValues
                : collectFormValues();
        return {
            search: sanitizeText(values?.search || values?.q),
            db_type: sanitizeText(values?.db_type),
            status: sanitizeText(values?.status),
            tags: normalizeArrayValue(values?.tags),
        };
    }

    function collectFormValues() {
        if (instanceFilterCard?.serialize) {
            return instanceFilterCard.serialize();
        }
        const form = selectOne(`#${INSTANCE_FILTER_FORM_ID}`).first();
        if (!form) {
            return {};
        }
        if (global.UI?.serializeForm) {
            return global.UI.serializeForm(form);
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
            if (
                value === undefined ||
                value === null ||
                value === '' ||
                value === 'all' ||
                (Array.isArray(value) && !value.length)
            ) {
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

    function normalizeArrayValue(value) {
        if (!value) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.map((item) => item && item.trim()).filter(Boolean);
        }
        if (typeof value === 'string') {
            return value
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean);
        }
        return [];
    }

    function buildBaseUrl() {
        const base = '/instances/api/instances';
        return `${base}?sort=id&order=desc`;
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
        const path = query ? `/instances?${query}` : '/instances';
        global.history.replaceState(null, '', path);
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
                if (instanceFilterCard?.emit) {
                    instanceFilterCard.emit('change', { source: 'tag-selector' });
                } else {
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

    function bindToolbarActions() {
        const createButtons = select('[data-action="create-instance"]');
        createButtons.each((el) => {
            const button = el instanceof Element ? el : el?.first();
            if (!button) {
                return;
            }
            button.addEventListener('click', (event) => {
                event.preventDefault();
                instanceModalController?.openCreate?.();
            });
        });

        const batchDeleteBtn = selectOne('[data-action="batch-delete"]').first();
        if (batchDeleteBtn) {
            batchDeleteBtn.addEventListener('click', handleBatchDelete);
        }

        const batchTestBtn = selectOne('[data-action="batch-test"]').first();
        if (batchTestBtn) {
            batchTestBtn.addEventListener('click', handleBatchTest);
        }

        const exportBtn = selectOne('[data-action="export"]').first();
        if (exportBtn) {
            exportBtn.addEventListener('click', (event) => {
                event.preventDefault();
                exportInstances();
            });
        }
    }

    function handleBatchDelete(event) {
        event.preventDefault();
        if (!instanceStore?.actions?.batchDeleteSelected) {
            return;
        }
        if (!selectedInstanceIds.size) {
            global.toast?.warning?.('请先选择要删除的实例');
            return;
        }
        instanceStore.actions
            .batchDeleteSelected()
            .then((response) => {
                if (response?.success === false) {
                    global.toast?.error?.(response?.message || '批量删除失败');
                    return;
                }
                global.toast?.success?.(response?.message || '批量删除任务已提交');
                setTimeout(() => instancesGrid?.refresh?.(), 500);
            })
            .catch((error) => {
                console.error('批量删除实例失败:', error);
                global.toast?.error?.(error?.message || '批量删除失败');
            });
    }

    function handleBatchTest(event) {
        event.preventDefault();
        if (!selectedInstanceIds.size) {
            global.toast?.warning?.('请先选择要测试的实例');
            return;
        }
        const connectionManager = global.connectionManager;
        if (!connectionManager?.batchTestConnections) {
            global.toast?.error?.('连接管理服务未初始化');
            return;
        }
        const ids = Array.from(selectedInstanceIds);
        connectionManager
            .batchTestConnections(ids)
            .then((result) => {
                if (result?.success === false) {
                    global.toast?.error?.(result?.error || '批量测试失败');
                    return;
                }
                global.toast?.success?.(result?.message || '批量测试任务已提交');
            })
            .catch((error) => {
                console.error('批量测试连接失败:', error);
                global.toast?.error?.(error?.message || '批量测试失败');
            });
    }

    function exportInstances() {
        const filters = normalizeFilters(resolveFilters());
        const params = buildSearchParams(filters);
        const query = params.toString();
        const url = query ? `${exportEndpoint}?${query}` : exportEndpoint;
        global.location.href = url;
    }

    function subscribeToStoreEvents() {
        if (!instanceStore?.subscribe) {
            return;
        }
        instanceStore.subscribe('instances:selectionChanged', ({ selectedIds }) => {
            selectedInstanceIds = new Set(selectedIds || []);
            updateSelectionSummary();
            syncSelectionCheckboxes();
        });
        instanceStore.subscribe('instances:batchDelete:success', () => {
            selectedInstanceIds.clear();
            instancesGrid?.refresh?.();
        });
    }

    function updateInstanceTotal(total) {
        const element = document.getElementById('instances-total');
        if (element) {
            element.textContent = `共 ${total} 个实例`;
        }
    }

    function updateSelectionSummary() {
        const element = document.getElementById('instances-selection-summary');
        if (!element) {
            return;
        }
        if (!selectedInstanceIds.size) {
            element.textContent = '未选择实例';
            return;
        }
        element.textContent = `已选择 ${selectedInstanceIds.size} 个实例`;
    }

    function syncSelectionCheckboxes() {
        if (!canManage) {
            return;
        }
        const checkboxes = pageRoot.querySelectorAll('.grid-instance-checkbox');
        const state = instanceStore?.getState?.();
        const availableIds = new Set(state?.availableInstanceIds || []);
        checkboxes.forEach((checkbox) => {
            checkbox.removeEventListener('change', handleRowSelectionChange);
            const id = Number(checkbox.value);
            checkbox.checked = selectedInstanceIds.has(id);
            checkbox.addEventListener('change', handleRowSelectionChange);
        });
        const selectAll = document.getElementById('grid-select-all');
        if (selectAll) {
            selectAll.removeEventListener('change', handleSelectAllChange);
            if (!availableIds.size) {
                selectAll.checked = false;
                selectAll.indeterminate = false;
            } else if (selectedInstanceIds.size === availableIds.size) {
                selectAll.checked = true;
                selectAll.indeterminate = false;
            } else if (selectedInstanceIds.size > 0) {
                selectAll.checked = false;
                selectAll.indeterminate = true;
            } else {
                selectAll.checked = false;
                selectAll.indeterminate = false;
            }
            selectAll.addEventListener('change', handleSelectAllChange);
        }
        const batchDeleteBtn = selectOne('[data-action="batch-delete"]').first();
        const batchTestBtn = selectOne('[data-action="batch-test"]').first();
        const disabled = !selectedInstanceIds.size;
        if (batchDeleteBtn) {
            batchDeleteBtn.disabled = disabled;
        }
        if (batchTestBtn) {
            batchTestBtn.disabled = disabled;
        }
    }

    function handleRowSelectionChange(event) {
        const checkbox = event.currentTarget;
        const id = Number(checkbox.value);
        if (!Number.isFinite(id)) {
            return;
        }
        if (instanceStore?.actions?.toggleSelection) {
            instanceStore.actions.toggleSelection(id);
        }
    }

    function handleSelectAllChange(event) {
        if (!instanceStore?.actions) {
            return;
        }
        const checked = event.currentTarget.checked;
        if (checked) {
            instanceStore.actions.selectAll?.();
        } else {
            instanceStore.actions.clearSelection?.();
        }
    }

    function handleTestConnection(instanceId, trigger) {
        const connectionManager = global.connectionManager;
        if (!connectionManager?.testInstanceConnection) {
            global.toast?.error?.('连接管理服务未初始化');
            return;
        }
        const button = trigger instanceof Element ? trigger : null;
        const original = button ? button.innerHTML : null;
        toggleButtonLoading(button, true, '<i class="fas fa-spinner fa-spin"></i>');
        connectionManager
            .testInstanceConnection(instanceId)
            .then((result) => {
                if (result?.success) {
                    global.toast?.success?.(result?.message || '连接正常');
                } else {
                    global.toast?.error?.(result?.error || result?.message || '连接失败');
                }
            })
            .catch((error) => {
                console.error('测试连接失败:', error);
                global.toast?.error?.('测试连接失败');
            })
            .finally(() => {
                toggleButtonLoading(button, false, original);
            });
    }

    function handleSyncInstance(instanceId, trigger) {
        if (!instanceStore?.actions?.syncInstanceAccounts) {
            return;
        }
        const button = trigger instanceof Element ? trigger : null;
        const original = button ? button.innerHTML : null;
        toggleButtonLoading(button, true, '<i class="fas fa-spinner fa-spin"></i>');
        instanceStore.actions
            .syncInstanceAccounts(instanceId)
            .then((result) => {
                if (result?.success === false) {
                    global.toast?.error?.(result?.message || '同步失败');
                    return;
                }
                global.toast?.success?.(result?.message || '同步任务已启动');
                setTimeout(() => instancesGrid?.refresh?.(), 1200);
            })
            .catch((error) => {
                console.error('同步实例失败:', error);
                global.toast?.error?.(error?.message || '同步失败');
            })
            .finally(() => {
                toggleButtonLoading(button, false, original);
            });
    }

    function toggleButtonLoading(button, loading, placeholder) {
        if (!button) {
            return;
        }
        if (loading) {
            button.dataset.originalContent = button.innerHTML;
            button.innerHTML = placeholder || '<i class="fas fa-spinner fa-spin"></i>';
            button.disabled = true;
        } else {
            const previous = button.dataset.originalContent || placeholder;
            if (previous) {
                button.innerHTML = previous;
            }
            button.disabled = false;
            delete button.dataset.originalContent;
        }
    }

    function safeParseJSON(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            console.warn('解析 JSON 失败:', error);
            return fallback;
        }
    }

    function formatTimestamp(value) {
        if (!value) {
            return '';
        }
        try {
            if (global.dayjs) {
                const dayjsValue = global.dayjs(value);
                if (dayjsValue.isValid()) {
                    return dayjsValue.format('YYYY-MM-DD HH:mm');
                }
            }
            const date = new Date(value);
            if (!Number.isNaN(date.getTime())) {
                return date.toLocaleString();
            }
        } catch (error) {
            return value;
        }
        return value;
    }

    function exposeGlobalActions() {
        global.InstanceListActions = {
            openDetail: (instanceId) => {
                if (!instanceId) {
                    return;
                }
                global.location.href = `${detailBase}/${instanceId}`;
            },
            openEdit: (instanceId) => instanceModalController?.openEdit?.(instanceId),
            testConnection: (instanceId, trigger) => handleTestConnection(instanceId, trigger),
            sync: (instanceId, trigger) => handleSyncInstance(instanceId, trigger),
        };
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

window.InstancesListPage = {
    mount: mountInstancesListPage,
};
