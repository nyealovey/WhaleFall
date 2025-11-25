/**
 * 挂载实例列表页面。
 *
 * 初始化实例列表页面的所有组件，包括服务、Store、Grid、筛选器、
 * 工具栏操作和事件订阅。负责页面的完整生命周期管理。
 *
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountInstancesListPage();
 */
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
        updateBatchActionState();
    });

    /**
     * 初始化服务实例。
     *
     * 创建 InstanceService 和 InstanceManagementService 实例，
     * 用于后续的数据查询和管理操作。
     *
     * @return {void}
     */
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

    /**
     * 初始化实例 Store。
     *
     * 创建 InstanceStore 实例并初始化状态，包括选中的实例 ID 集合。
     *
     * @return {void}
     */
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

    /**
     * 初始化实例相关模态。
     */
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

    /**
     * 初始化实例列表 gridjs。
     */
    function initializeGrid() {
        const container = document.getElementById('instances-grid');
        if (!container) {
            console.warn('未找到 instances-grid 容器');
            return;
        }

        instancesGrid = new GridWrapper(container, {
            search: false,
            sort: false,
            columns: buildColumns(),
            server: {
                url: buildBaseUrl(),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                then: handleServerResponse,
                total: (response) => {
                    const payload = response?.data || response || {};
                    const total = payload.total || 0;
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

    /**
     * 构建表格列配置。
     *
     * 根据用户权限和页面配置，动态构建 Grid.js 表格的列定义，
     * 包括选择框、实例信息、数据库类型、标签、状态等列。
     *
     * @return {Array<Object>} Grid.js 列配置数组
     */
    function buildColumns() {
        const columns = [];

        if (canManage) {
            columns.push({
                id: 'select',
                name: '',
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
                    const name = escapeHtml(cell || '-');
                    return gridHtml(`
                        <div class="d-flex align-items-start">
                            <i class="fas fa-database text-primary me-2 mt-1"></i>
                            <div class="fw-semibold">${name}</div>
                        </div>
                    `);
                },
            },
            {
                id: 'db_type',
                name: '类型',
                width: '100px',
                formatter: (cell) => renderDbTypeBadge(cell),
            },
            {
                id: 'host',
                name: '主机/IP',
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const host = cell || meta.host || '';
                    if (!gridHtml) {
                        return host || '-';
                    }
                    return gridHtml(`<span class="text-monospace">${escapeHtml(host || '-')}</span>`);
                },
            },
            {
                id: 'status',
                name: '状态',
                width: '80px',
                formatter: (cell, row) => renderStatusBadge(Boolean(resolveRowMeta(row).is_active)),
            },
            {
                id: 'active_counts',
                name: '活跃',
                width: '80px',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const dbCount = meta.active_db_count || 0;
                    const accountCount = meta.active_account_count || 0;
                    if (!gridHtml) {
                        return `${dbCount}/${accountCount}`;
                    }
                    return gridHtml(`
                        <div class="d-flex flex-column gap-1">
                            <span class="badge bg-primary stat-badge">
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
                id: 'main_version',
                name: '版本',
                width: '90px',
                formatter: (cell) => {
                    if (!gridHtml) {
                        return cell || '未检测';
                    }
                    if (!cell) {
                        return gridHtml('<small class="text-muted">-</small>');
                    }
                    return gridHtml(`<span class="badge bg-primary">${escapeHtml(cell)}</span>`);
                },
            },
            {
                id: 'tags',
                name: '标签',
                sort: false,
                formatter: (cell, row) => renderTags(resolveRowMeta(row).tags || []),
            },
            {
                id: 'last_sync_time',
                name: '最后同步',
                width: '140px',
                formatter: (cell) => renderLastSync(cell),
            },
            {
                id: 'actions',
                name: '操作',
                sort: false,
                width: '100px',
                formatter: (cell, row) => renderActions(resolveRowMeta(row)),
            },
            { id: '__meta__', hidden: true },
        );

        return columns;
    }

    /**
     * 处理服务器响应数据。
     *
     * 解析服务器返回的实例列表数据，更新 Store 中的可用实例 ID，
     * 并返回格式化后的数据供 Grid.js 渲染。
     *
     * @param {Object} response - 服务器响应对象
     * @param {Object} response.data - 响应数据
     * @param {Array<Object>} response.data.items - 实例列表
     * @param {number} response.data.total - 总数
     * @return {Object} 包含 data 和 total 的对象
     */
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
                item.host || '',
                item.is_active,
                null,
                item.main_version || '',
                item.tags || [],
                item.last_sync_time || '',
                null,
                item,
            );
            return row;
        });
    }

    /**
     * 渲染数据库类型徽章。
     */
    function renderDbTypeBadge(dbType) {
        const typeStr = typeof dbType === 'string' ? dbType : (dbType || '').toString();
        const meta = dbTypeMap[typeStr] || {};
        if (!gridHtml) {
            return meta.display_name || typeStr || '-';
        }
        const color = meta.color || 'secondary';
        const icon = meta.icon || 'fa-database';
        const label = meta.display_name || (typeStr ? typeStr.toUpperCase() : '-');
        return gridHtml(`<span class="badge bg-${color}"><i class="fas ${icon} me-1"></i>${escapeHtml(label)}</span>`);
    }

    /**
     * 渲染标签列表。
     */
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

    /**
     * 渲染活跃状态。
     */
    function renderStatusBadge(isActive) {
        if (!gridHtml) {
            return isActive ? '正常' : '禁用';
        }
        const color = isActive ? 'success' : 'danger';
        const text = isActive ? '正常' : '禁用';
        return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
    }

    /**
     * 渲染最后同步时间。
     */
    function renderLastSync(timestamp) {
        if (!gridHtml) {
            return timestamp || '暂无同步记录';
        }
        if (!timestamp) {
            return gridHtml('<small class="text-muted">暂无同步记录</small>');
        }
        return gridHtml(`<small class="text-muted">${escapeHtml(formatTimestamp(timestamp))}</small>`);
    }

    /**
     * 渲染操作按钮列。
     */
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
        }
        return gridHtml(`<div class="btn-group btn-group-sm" role="group">${buttons.join('')}</div>`);
    }

    /**
     * grid 渲染完成后的回调。
     */
    function handleGridUpdated() {
        syncSelectionCheckboxes();
    }

    /**
     * 从 gridjs 行中取出 meta 数据。
     */
    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    /**
     * 初始化筛选表单。
     */
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

    /**
     * 应用过滤条件。
     */
    function handleFilterChange(values) {
        if (!instancesGrid) {
            return;
        }
        const filters = normalizeFilters(resolveFilters(values));
        instancesGrid.updateFilters(filters);
        instanceStore?.actions?.applyFilters?.(filters);
        syncUrl(filters);
    }

    /**
     * 获取筛选值，支持覆盖。
     *
     * @param {Object} [overrideValues] 外部传入的新值。
     * @returns {Object} 规范化后的筛选条件。
     */
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

    /**
     * 收集筛选表单字段。
     *
     * @returns {Object} 表单值映射。
     */
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

    /**
     * 清理空值，返回有效 filters。
     *
     * @param {Object} raw 原始过滤值。
     * @returns {Object} 去除空值后的过滤值。
     */
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

    /**
     * 去除文本空格。
     *
     * @param {string} value 输入值。
     * @returns {string} 处理后的文本。
     */
    function sanitizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        return trimmed || '';
    }

    /**
     * 规范化数组型参数。
     *
     * @param {string|Array<string>} value 元素集合或逗号分隔字符串。
     * @returns {Array<string>} 清洗后的数组。
     */
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

    /**
     * 构造后端 API URL。
     *
     * @returns {string} API 地址。
     */
    function buildBaseUrl() {
        const base = '/instances/api/instances';
        return `${base}?sort=id&order=desc`;
    }

    /**
     * 将 filters 编码为查询字符串。
     *
     * @param {Object} filters 过滤条件。
     * @returns {URLSearchParams}
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
     * 使用 history API 更新地址栏。
     *
     * @param {Object} filters 过滤条件。
     */
    function syncUrl(filters) {
        if (!global.history?.replaceState) {
            return;
        }
        const params = buildSearchParams(filters);
        const query = params.toString();
        const path = query ? `/instances?${query}` : '/instances';
        global.history.replaceState(null, '', path);
    }

    /**
     * 初始化标签筛选器组件。
     */
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

    /**
     * 解析隐藏字段中的标签。
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
     * 绑定工具栏批量操作按钮。
     */
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

    /**
     * 触发批量删除。
     */
    function handleBatchDelete(event) {
        event.preventDefault();
        if (!instanceStore?.actions?.batchDeleteSelected) {
            return;
        }
        if (!selectedInstanceIds.size) {
            global.toast?.warning?.('请先选择要删除的实例');
            return;
        }
        syncStoreSelection();
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

    /**
     * 触发批量测试。
     */
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

    /**
     * 导出当前筛选下的实例。
     */
    function exportInstances() {
        const filters = normalizeFilters(resolveFilters());
        const params = buildSearchParams(filters);
        const query = params.toString();
        const url = query ? `${exportEndpoint}?${query}` : exportEndpoint;
        global.location.href = url;
    }

    /**
     * 订阅 store 的 selection 事件。
     */
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

    /**
     * 更新页面上的选中统计。
     */
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

    /**
     * 同步 grid 复选框的状态。
     */
    function syncSelectionCheckboxes() {
        if (!canManage) {
            return;
        }
        const checkboxes = pageRoot.querySelectorAll('.grid-instance-checkbox');
        checkboxes.forEach((checkbox) => {
            checkbox.removeEventListener('change', handleRowSelectionChange);
            const id = Number(checkbox.value);
            checkbox.checked = selectedInstanceIds.has(id);
            checkbox.addEventListener('change', handleRowSelectionChange);
        });
        updateSelectAllCheckbox(checkboxes);
        updateBatchActionState();
    }

    /**
     * 根据当前选中情况更新全选按钮。
     */
    function updateSelectAllCheckbox(checkboxes) {
        const selectAll = document.getElementById('grid-select-all');
        if (!selectAll) {
            return;
        }
        const availableIds = collectAvailableInstanceIds(checkboxes);
        const total = availableIds.length;
        selectAll.removeEventListener('change', handleSelectAllChange);
        if (!total) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        } else if (selectedInstanceIds.size === total) {
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

    /**
     * 收集当前页面可选的实例 ID。
     */
    function collectAvailableInstanceIds(checkboxes) {
        const state = instanceStore?.getState?.();
        const fromState = Array.isArray(state?.availableInstanceIds) ? state.availableInstanceIds : [];
        if (fromState.length) {
            return fromState
                .map((value) => Number(value))
                .filter((id) => Number.isFinite(id));
        }
        const elements = checkboxes || pageRoot.querySelectorAll('.grid-instance-checkbox');
        return Array.from(elements)
            .map((checkbox) => Number(checkbox.value))
            .filter((id) => Number.isFinite(id));
    }

    /**
     * 根据选中数量启用或禁用批量按钮。
     */
    function updateBatchActionState() {
        const batchDeleteBtn = selectOne('[data-action="batch-delete"]').first();
        const batchTestBtn = selectOne('[data-action="batch-test"]').first();
        const disabled = !selectedInstanceIds.size;
        if (batchDeleteBtn) {
            if (disabled) {
                batchDeleteBtn.setAttribute('disabled', 'disabled');
            } else {
                batchDeleteBtn.removeAttribute('disabled');
            }
        }
        if (batchTestBtn) {
            if (disabled) {
                batchTestBtn.setAttribute('disabled', 'disabled');
            } else {
                batchTestBtn.removeAttribute('disabled');
            }
        }
    }

    /**
     * 将当前选中的实例同步到 store。
     */
    function syncStoreSelection() {
        if (!instanceStore?.actions?.setSelection) {
            return;
        }
        const ids = Array.from(selectedInstanceIds);
        try {
            instanceStore.actions.setSelection(ids, { reason: 'manualSync' });
        } catch (error) {
            console.warn('同步实例选择状态失败:', error);
        }
    }

    /**
     * 行复选框变动事件处理。
     */
    function handleRowSelectionChange(event) {
        const checkbox = event.currentTarget;
        const id = Number(checkbox.value);
        if (!Number.isFinite(id)) {
            return;
        }
        if (checkbox.checked) {
            selectedInstanceIds.add(id);
        } else {
            selectedInstanceIds.delete(id);
        }
        syncStoreSelection();
        updateSelectionSummary();
        updateBatchActionState();
        updateSelectAllCheckbox();
    }

    /**
     * 全选复选框变动事件处理。
     */
    function handleSelectAllChange(event) {
        const checked = event.currentTarget.checked;
        const availableIds = collectAvailableInstanceIds();
        if (checked) {
            availableIds.forEach((id) => selectedInstanceIds.add(id));
        } else {
            availableIds.forEach((id) => selectedInstanceIds.delete(id));
        }
        syncStoreSelection();
        updateSelectionSummary();
        updateBatchActionState();
        syncSelectionCheckboxes();
    }

    /**
     * 测试实例连接并展示结果。
     */
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

    /**
     * 切换按钮 loading 状态。
     */
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

    /**
     * 安全解析 JSON，失败时返回 fallback。
     */
    function safeParseJSON(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            console.warn('解析 JSON 失败:', error);
            return fallback;
        }
    }

    /**
     * 格式化时间戳。
     */
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

    /**
     * 暴露对外的全局方法。
     */
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
        };
    }

    /**
     * 简单 HTML 转义。
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
}

window.InstancesListPage = {
    mount: mountInstancesListPage,
};
