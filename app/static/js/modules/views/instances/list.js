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
    const escapeHtml = global.UI?.escapeHtml;
    const CHIP_COLUMN_WIDTH = '220px';
    const TYPE_COLUMN_WIDTH = '110px';
    const STATUS_COLUMN_WIDTH = '70px';
    const ACTIVE_COLUMN_WIDTH = '110px';
    const ACTION_COLUMN_WIDTH = '120px';

    const INSTANCE_FILTER_FORM_ID = 'instance-filter-form';
    const INCLUDE_DELETED_TOGGLE_ID = 'include-deleted-toggle';
    const AUTO_APPLY_FILTER_CHANGE = true;

    const pageRoot = document.getElementById('instances-page-root');
    if (!pageRoot) {
        console.warn('未找到实例列表根元素');
        return;
    }

    const exportEndpoint = pageRoot.dataset.exportUrl || '/files/export_instances';
    const canManage = pageRoot.dataset.canManage === 'true';
    const detailBase = pageRoot.dataset.detailBase || '/instances';
    const rawDbTypeMap = safeParseJSON(pageRoot.dataset.dbTypeMap || '{}', {});
    const dbTypeMetaMap = new Map(Object.entries(rawDbTypeMap));

    let gridPage = null;
    let instancesGrid = null;
    let instanceStore = null;
    let instanceService = null;
    let managementService = null;
    let instanceModalController = null;
    let batchCreateController = null;
    let selectedInstanceIds = new Set();
    let checkboxDelegationInitialized = false;

    ready(() => {
        initializeServices();
        initializeInstanceStore();
        initializeModals();
        initializeGridPage();
        initializeTagFilter();
        bindToolbarActions();
        subscribeToStoreEvents();
        exposeGlobalActions();
        updateBatchActionState();
    });

    /**
     * 读取“显示已删除”开关状态。
     *
     * @returns {string} 勾选返回 "true"，否则返回空字符串。
     */
    function resolveIncludeDeleted() {
        const toggle = document.getElementById(INCLUDE_DELETED_TOGGLE_ID);
        if (!(toggle instanceof HTMLInputElement)) {
            return '';
        }
        if (toggle.type !== 'checkbox') {
            return '';
        }
        return toggle.checked ? 'true' : '';
    }

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
     *
     * @returns {void} 无返回值，通过副作用挂载模态控制器。
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
                global.InstanceBatchCreateController = batchCreateController;
            } catch (error) {
                console.error('批量创建模态初始化失败:', error);
                batchCreateController = null;
            }
        }
    }

    /**
     * 初始化实例列表 grid page skeleton。
     *
     * @returns {void} 无返回值，通过副作用创建 Views.GridPage controller。
     */
    function initializeGridPage() {
        const GridPage = global.Views?.GridPage;
        const GridPlugins = global.Views?.GridPlugins;
        if (!GridPage?.mount || !GridPlugins) {
            console.error('Views.GridPage 未加载');
            return;
        }

        if (!global.UI?.escapeHtml || !global.UI?.renderChipStack || !global.GridRowMeta?.get) {
            console.error('UI helpers 或 GridRowMeta 未加载');
            return;
        }

        gridPage = GridPage.mount({
            root: pageRoot,
            grid: '#instances-grid',
            filterForm: `#${INSTANCE_FILTER_FORM_ID}`,
            gridOptions: {
                search: false,
                sort: false,
                columns: buildColumns(),
                server: {
                    url: buildBaseUrl(),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    then: handleServerResponse,
                    total: (response) => {
                        const payload = response?.data || response || {};
                        return payload.total || 0;
                    },
                },
            },
            filters: {
                allowedKeys: [
                    'search',
                    'db_type',
                    'status',
                    'tags',
                    'include_deleted',
                    'page',
                    'limit',
                    'sort',
                    'order',
                ],
                resolve: (values) => resolveFiltersFromValues(values),
                normalize: (raw) => normalizeFilters(raw),
            },
            plugins: [
                GridPlugins.filterCard({
                    autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
                    onClear: () => {
                        const scope = 'instance-tag-selector';
                        const filterContainer = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
                        const hiddenInput = filterContainer?.querySelector(`#${scope}-selected`);
                        if (hiddenInput) {
                            hiddenInput.value = '';
                        }
                        const chipsContainer = filterContainer?.querySelector(`#${scope}-chips`);
                        if (chipsContainer) {
                            chipsContainer.innerHTML = '';
                        }
                        const previewElement = filterContainer?.querySelector(`#${scope}-preview`);
                        if (previewElement) {
                            previewElement.style.display = 'none';
                        }
                        window.location.href = window.location.pathname;
                    },
                }),
                GridPlugins.urlSync(),
                GridPlugins.exportButton({
                    selector: '[data-action="export"]',
                    endpoint: exportEndpoint,
                }),
                GridPlugins.actionDelegation({
                    containerSelector: '#instances-grid',
                    actions: {
                        'test-connection': ({ event, el }) => {
                            event.preventDefault();
                            const instanceId = Number(el.getAttribute('data-instance-id'));
                            handleTestConnection(instanceId, el);
                        },
                        'restore-instance': ({ event, el }) => {
                            event.preventDefault();
                            const instanceId = Number(el.getAttribute('data-instance-id'));
                            handleRestoreInstance(instanceId, el);
                        },
                    },
                }),
                {
                    name: 'instanceStoreFilters',
                    onFiltersChanged: (_ctx, { filters }) => {
                        instanceStore?.actions?.applyFilters?.(filters);
                    },
                },
            ],
        });

        instancesGrid = gridPage?.gridWrapper || null;
        if (!instancesGrid) {
            return;
        }

        if (instancesGrid.grid?.on) {
            instancesGrid.grid.on('ready', handleGridUpdated);
            instancesGrid.grid.on('updated', handleGridUpdated);
        }

        setupCheckboxDelegation();
    }

    /**
     * 使用事件委托统一处理复选框变更。
     *
     * @returns {void} 仅在可管理模式下绑定一次委托监听。
     */
    function setupCheckboxDelegation() {
        if (!canManage || checkboxDelegationInitialized || !pageRoot) {
            return;
        }
        pageRoot.addEventListener('change', (event) => {
            const target = event.target;
            if (!(target instanceof HTMLInputElement)) {
                return;
            }
            if (target.classList.contains('grid-instance-checkbox')) {
                handleRowSelectionChange(event);
                return;
            }
            if (target.id === 'grid-select-all') {
                handleSelectAllChange(event);
            }
        });
        checkboxDelegationInitialized = true;
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
                name: gridHtml
                    ? gridHtml('<input type="checkbox" class="form-check-input" id="grid-select-all" aria-label="全选">')
                    : '全选',
                width: '48px',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const id = meta?.id ?? '';
                    if (meta?.deleted_at) {
                        return gridHtml('<span class="text-muted">-</span>');
                    }
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
                formatter: (cell) => {
                    if (!gridHtml) {
                        return cell || '-';
                    }
                    const name = escapeHtml(cell || '-');
                    return gridHtml(`
                        <div class="d-flex align-items-start">
                            <i class="fas fa-database account-instance-icon me-2 mt-1" aria-hidden="true"></i>
                            <div class="fw-semibold">${name}</div>
                        </div>
                    `);
                },
            },
            {
                id: 'db_type',
                name: '类型',
                width: TYPE_COLUMN_WIDTH,
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
                width: STATUS_COLUMN_WIDTH,
                formatter: (cell, row) => renderStatusBadge(resolveRowMeta(row)),
            },
            {
                id: 'active_counts',
                name: '活跃',
                width: ACTIVE_COLUMN_WIDTH,
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const dbCount = meta.active_db_count || 0;
                    const accountCount = meta.active_account_count || 0;
                    if (!gridHtml) {
                        return `${dbCount}/${accountCount}`;
                    }
                    return gridHtml(`
                        <div class="active-count-stack">
                            <span class="status-pill status-pill--muted">
                                <i class="fas fa-database" aria-hidden="true"></i>${dbCount} 库
                            </span>
                            <span class="status-pill status-pill--muted">
                                <i class="fas fa-user" aria-hidden="true"></i>${accountCount} 账
                            </span>
                        </div>
                    `);
                },
            },
            {
                id: 'version_sync',
                name: '版本 / 同步',
                width: '140px',
                formatter: (cell, row) => renderVersionSync(resolveRowMeta(row)),
            },
            {
                id: 'tags',
                name: '标签',
                sort: false,
                width: CHIP_COLUMN_WIDTH,
                formatter: (cell, row) => renderTags(resolveRowMeta(row).tags || []),
            },
            {
                id: 'actions',
                name: '操作',
                sort: false,
                width: ACTION_COLUMN_WIDTH,
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
            const metaList = items
                .filter((item) => !item?.deleted_at)
                .map((item) => ({
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
                null,
                item,
            );
            return row;
        });
    }

    /**
     * 渲染数据库类型徽章。
     *
     * @param {string|Object} dbType 数据库类型字符串或包含元数据的对象。
     * @returns {string|import('gridjs').Html} HTML 片段或纯文本。
     */
    function renderDbTypeBadge(dbType) {
        const typeStr = typeof dbType === 'string' ? dbType : (dbType || '').toString();
        const meta = dbTypeMetaMap.get(typeStr) || {};
        if (!gridHtml) {
            return meta.display_name || typeStr || '-';
        }
        const icon = meta.icon || 'fa-database';
        const label = meta.display_name || (typeStr ? typeStr.toUpperCase() : '-');
        return gridHtml(`<span class="chip-outline chip-outline--brand"><i class="fas ${icon}" aria-hidden="true"></i>${escapeHtml(label)}</span>`);
    }

    /**
     * 渲染标签列表。
     *
     * @param {Array<Object>} tags 标签数组。
     * @returns {string|import('gridjs').Html} 渲染后的标签集合。
     */
    function renderTags(tags) {
        if (!gridHtml) {
            return (tags || []).map((tag) => tag.display_name || tag.name).join(', ') || '无标签';
        }
        if (!tags.length) {
            return gridHtml('<span class="text-muted">无标签</span>');
        }
        const names = tags
            .map((tag) => tag?.display_name || tag?.name)
            .filter((name) => typeof name === 'string' && name.trim().length > 0);
        return global.UI.renderChipStack(names, {
            gridHtml,
            baseClass: 'ledger-chip',
            counterClass: 'ledger-chip ledger-chip--counter',
            emptyText: '无标签',
            maxItems: Number.POSITIVE_INFINITY,
        });
    }

    /**
     * 渲染活跃状态。
     *
     * @param {boolean} isActive 是否处于启用状态。
     * @returns {string|import('gridjs').Html} 状态徽章。
     */
    function renderStatusBadge(meta) {
        if (meta?.deleted_at) {
            return renderStatusPill('已删除', 'muted', 'fa-trash');
        }
        const isActive = Boolean(meta?.is_active);
        const resolveText = global.UI?.Terms?.resolveActiveStatusText;
        const text = typeof resolveText === 'function' ? resolveText(isActive) : (isActive ? '启用' : '停用');
        const variant = isActive ? 'success' : 'muted';
        const icon = isActive ? 'fa-check-circle' : 'fa-ban';
        return renderStatusPill(text, variant, icon);
    }

    /**
     * 渲染最后同步时间。
     *
     * @param {string|Date} timestamp 原始时间戳。
     * @returns {string|import('gridjs').Html} 处理后的时间标签。
     */
    function renderVersionSync(meta) {
        const version = meta?.main_version ? escapeHtml(meta.main_version) : '未检测';
        const syncLabel = meta?.last_sync_time
            ? escapeHtml(formatShortTimestamp(meta.last_sync_time))
            : '暂无同步记录';
        if (!gridHtml) {
            return `${version} / ${syncLabel}`;
        }
        return gridHtml(`
            <div class="version-sync-meta">
                <div class="fw-bold">${version}</div>
                <small class="text-muted">${syncLabel}</small>
            </div>
        `);
    }

    /**
     * 渲染操作按钮列。
     *
     * @param {Object} meta 行数据元信息。
     * @returns {string|import('gridjs').Html} 包含操作按钮的 HTML。
     */
    function renderActions(meta) {
        if (!gridHtml) {
            return '';
        }
        if (meta?.deleted_at) {
            if (!canManage) {
                return gridHtml('<span class="text-muted">-</span>');
            }
            const name = escapeHtml(meta?.name || '');
            const hostLabel = meta?.host ? escapeHtml(`${meta.host}:${meta.port || ''}`) : '';
            return gridHtml(`
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button"
                            class="btn btn-outline-primary btn-sm"
                            data-action="restore-instance"
                            data-instance-id="${meta.id}"
                            data-instance-name="${name}"
                            data-instance-host="${hostLabel}">
                        <i class="fas fa-undo me-1" aria-hidden="true"></i>恢复
                    </button>
                </div>
            `);
        }
        const buttons = [
            `<a href="${detailBase}/${meta.id}" class="btn btn-outline-secondary btn-sm btn-icon" title="查看详情"><i class="fas fa-eye"></i></a>`,
            `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="test-connection" data-instance-id="${meta.id}" title="测试连接"><i class="fas fa-plug"></i></button>`,
        ];
        return gridHtml(`<div class="btn-group btn-group-sm" role="group">${buttons.join('')}</div>`);
    }

    /**
     * grid 渲染完成后的回调。
     *
     * @returns {void} 仅同步勾选状态，不返回值。
     */
    function handleGridUpdated() {
        syncSelectionCheckboxes();
    }

    /**
     * 从 gridjs 行中取出 meta 数据。
     *
     * @param {import('gridjs').Row} row Grid.js 行对象。
     * @returns {Object} 附加在行末尾的元数据。
     */
    function resolveRowMeta(row) {
        return global.GridRowMeta.get(row);
    }

    /**
     * 从表单序列化结果中解析 filters。
     *
     * @param {Object} values 表单序列化值。
     * @returns {Object} 原始 filters。
     */
    function resolveFiltersFromValues(values) {
        const source = values && typeof values === 'object' ? values : {};
        const includeDeleted = resolveIncludeDeleted();
        return {
            search: sanitizeText(source?.search || source?.q),
            db_type: sanitizeText(source?.db_type),
            status: sanitizeText(source?.status),
            tags: normalizeArrayValue(source?.tags),
            include_deleted: includeDeleted,
        };
    }

    /**
     * 清理空值，返回有效 filters。
     *
     * @param {Object} raw 原始过滤值。
     * @returns {Object} 去除空值后的过滤值。
     */
    function normalizeFilters(raw) {
        const filters = raw || {};
        const normalized = {};
        const isMeaningful = (value) =>
            !(
                value === undefined ||
                value === null ||
                value === '' ||
                value === 'all' ||
                (Array.isArray(value) && !value.length)
            );
        if (isMeaningful(filters.search)) {
            normalized.search = filters.search;
        }
        if (isMeaningful(filters.db_type)) {
            normalized.db_type = filters.db_type;
        }
        if (isMeaningful(filters.status)) {
            normalized.status = filters.status;
        }
        if (isMeaningful(filters.tags)) {
            normalized.tags = filters.tags;
        }
        if (isMeaningful(filters.include_deleted)) {
            normalized.include_deleted = filters.include_deleted;
        }
        if (isMeaningful(filters.page)) {
            normalized.page = filters.page;
        }
        if (isMeaningful(filters.limit)) {
            normalized.limit = filters.limit;
        }
        if (isMeaningful(filters.sort)) {
            normalized.sort = filters.sort;
        }
        if (isMeaningful(filters.order)) {
            normalized.order = filters.order;
        }
        return normalized;
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
        const base = '/api/v1/instances';
        return `${base}?sort=id&order=desc`;
    }

    /**
     * 初始化标签筛选器组件。
     *
     * @returns {void} 建立标签选择器交互，无返回值。
     */
    function initializeTagFilter() {
        if (!global.TagSelectorHelper) {
            console.warn('TagSelectorHelper 未加载，跳过标签筛选初始化');
            return;
        }
        const scope = 'instance-tag-selector';
        const filterContainer = document.querySelector(`[data-tag-selector-scope="${scope}"]`);
        const hiddenInput = filterContainer?.querySelector(`#${scope}-selected`);
        const initialValues = parseInitialTagValues(hiddenInput?.value || null);
        global.TagSelectorHelper.setupForForm({
            modalSelector: '#tagSelectorModal',
            rootSelector: '[data-tag-selector]',
            scope,
            container: filterContainer,
            hiddenValueKey: 'name',
            initialValues,
            onConfirm: () => {
                if (gridPage?.filterCard?.emit) {
                    gridPage.filterCard.emit('change', { source: 'tag-selector' });
                    return;
                }
                gridPage?.applyFiltersFromForm?.({ source: 'tag-selector' });
            },
        });
    }

    /**
     * 解析隐藏字段中的标签。
     *
     * @param {string|null} raw 逗号分隔的标签字符串。
     * @returns {Array<string>} 处理后的标签名称数组。
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
     *
     * @returns {void} 通过事件绑定实现批量操作触发。
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

        const includeDeletedToggle = document.getElementById(INCLUDE_DELETED_TOGGLE_ID);
        if (includeDeletedToggle instanceof HTMLInputElement) {
            includeDeletedToggle.addEventListener('change', () => {
                gridPage?.applyFiltersFromForm?.({ source: 'include-deleted-toggle' });
            });
        }
    }

    /**
     * 触发批量移入回收站。
     *
     * @param {Event} event 点击事件对象。
     * @returns {void} 通过 store 调度批量删除任务。
     */
    async function handleBatchDelete(event) {
        event.preventDefault();
        if (!instanceStore?.actions?.batchDeleteSelected) {
            return;
        }
        if (!selectedInstanceIds.size) {
            global.toast?.warning?.('请先选择要移入回收站的实例');
            return;
        }

        const confirmDanger = global.UI?.confirmDanger;
        if (typeof confirmDanger !== 'function') {
            global.toast?.error?.('确认组件未初始化');
            return;
        }

        const totalSelected = selectedInstanceIds.size;
        const confirmed = await confirmDanger({
            title: '确认移入回收站',
            message: '该操作将把实例移入回收站（可恢复），请确认影响范围后继续。',
            details: [
                { label: '影响范围', value: `已选择 ${totalSelected} 个实例`, tone: 'danger' },
                { label: '可恢复', value: '可在实例管理页勾选“显示已删除”后恢复', tone: 'info' },
            ],
            confirmText: '确认移入',
            confirmButtonClass: 'btn-danger',
        });
        if (!confirmed) {
            return;
        }

        const button = event.currentTarget instanceof Element ? event.currentTarget : null;
        const originalHtml = button ? button.innerHTML : null;
        if (button) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>处理中...';
            button.disabled = true;
        }

        syncStoreSelection();
        instanceStore.actions
            .batchDeleteSelected()
            .then((response) => {
                if (response?.success === false) {
                    global.toast?.error?.(response?.message || '批量移入回收站失败');
                    return;
                }
                global.toast?.success?.(response?.message || '批量移入回收站成功');
                setTimeout(() => instancesGrid?.refresh?.(), 500);
            })
            .catch((error) => {
                console.error('批量移入回收站失败:', error);
                global.toast?.error?.(error?.message || '批量移入回收站失败');
            })
                .finally(() => {
                    if (button) {
                        button.innerHTML = originalHtml || '<i class="fas fa-trash me-1"></i>移入回收站';
                        button.disabled = false;
                    }
                });
    }

    /**
     * 触发批量测试。
     *
     * @param {Event} event 点击事件对象。
     * @returns {void} 提交批量测试请求。
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
     * 订阅 store 的 selection 事件。
     *
     * @returns {void} 注册事件监听，用于同步 UI 状态。
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
     *
     * @returns {void} 更新 UI 提示，无返回值。
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
     *
     * @returns {void} 根据 store 同步勾选状态。
     */
    function syncSelectionCheckboxes() {
        if (!canManage) {
            return;
        }
        const checkboxes = pageRoot.querySelectorAll('.grid-instance-checkbox');
        checkboxes.forEach((checkbox) => {
            const id = Number(checkbox.value);
            checkbox.checked = selectedInstanceIds.has(id);
        });
        updateSelectAllCheckbox(checkboxes);
        updateBatchActionState();
    }

    /**
     * 根据当前选中情况更新全选按钮。
     *
     * @param {NodeListOf<HTMLInputElement>|Array<HTMLInputElement>} [checkboxes] 可选的复选框集合。
     * @returns {void} 更新全选框状态。
     */
    function updateSelectAllCheckbox(checkboxes) {
        const selectAll = document.getElementById('grid-select-all');
        if (!selectAll) {
            return;
        }
        const availableIds = collectAvailableInstanceIds(checkboxes);
        const total = availableIds.length;
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
    }

    /**
     * 收集当前页面可选的实例 ID。
     *
     * @param {NodeListOf<HTMLInputElement>|Array<HTMLInputElement>} [checkboxes] 复选框集合。
     * @returns {Array<number>} 去重后的实例 ID 列表。
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
     *
     * @returns {void} 更新按钮的 disabled 状态。
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
     *
     * @returns {void} 调度 store 的 selection 动作。
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
     *
     * @param {Event} event change 事件对象。
     * @returns {void} 同步勾选状态。
     */
    function handleRowSelectionChange(event) {
        const checkbox = event?.target;
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }
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
     *
     * @param {Event} event change 事件对象。
     * @returns {void} 根据全选状态批量更新 selection。
     */
    function handleSelectAllChange(event) {
        const checkbox = event?.target;
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }
        const checked = checkbox.checked;
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
     *
     * @param {number} instanceId 实例主键 ID。
     * @param {HTMLElement|EventTarget} [trigger] 触发按钮。
     * @returns {void} 通过连接管理器发起测试。
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
     * 恢复已删除实例。
     *
     * @param {number} instanceId 实例 ID。
     * @param {HTMLElement|EventTarget} [trigger] 触发按钮。
     * @returns {void} 触发恢复请求并刷新表格。
     */
    async function handleRestoreInstance(instanceId, trigger) {
        if (!managementService?.restoreInstance) {
            global.toast?.error?.('实例管理服务未初始化');
            return;
        }

        const confirmDanger = global.UI?.confirmDanger;
        if (typeof confirmDanger !== 'function') {
            global.toast?.error?.('确认组件未初始化');
            return;
        }

        const button = trigger instanceof Element ? trigger : null;
        const instanceName = button?.getAttribute('data-instance-name') || '';
        const instanceHost = button?.getAttribute('data-instance-host') || '';
        const confirmed = await confirmDanger({
            title: '确认恢复实例',
            message: '恢复后实例将重新出现在列表中；如需同步数据请手动执行同步。',
            details: [
                { label: '目标实例', value: instanceName || `ID: ${instanceId}`, tone: 'info' },
                { label: '连接信息', value: instanceHost || '未知', tone: 'muted' },
            ],
            confirmText: '确认恢复',
            confirmButtonClass: 'btn-primary',
        });
        if (!confirmed) {
            return;
        }

        const original = button ? button.innerHTML : null;
        toggleButtonLoading(button, true, '<i class="fas fa-spinner fa-spin"></i>');
        managementService
            .restoreInstance(instanceId)
            .then((result) => {
                if (result?.success === false) {
                    global.toast?.error?.(result?.message || '恢复失败');
                    return;
                }
                global.toast?.success?.(result?.message || '实例恢复成功');
                instancesGrid?.refresh?.();
            })
            .catch((error) => {
                console.error('恢复实例失败:', error);
                global.toast?.error?.(error?.message || '恢复失败');
            })
            .finally(() => {
                toggleButtonLoading(button, false, original);
            });
    }

    /**
     * 切换按钮 loading 状态。
     *
     * @param {HTMLElement|null} button 需要变更状态的按钮。
     * @param {boolean} loading 是否进入加载状态。
     * @param {string} [placeholder] 自定义占位 HTML。
     * @returns {void} 更新按钮内容与禁用状态。
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
     *
     * @param {string} value JSON 字符串。
     * @param {any} fallback 解析失败时返回的默认值。
     * @returns {any} JSON 对应的对象或提供的 fallback。
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
     *
     * @param {string|number|Date} value 原始时间值。
     * @returns {string} 格式化后的时间文本。
     */
    /**
     * 格式化为简短时间（MM/DD HH:mm）。
     *
     * @param {string|number|Date} value 原始时间
     * @returns {string} 简短时间文本
     */
    function formatShortTimestamp(value) {
        if (!value || !global.dayjs) {
            return '';
        }
        const dayjsValue = global.dayjs(value);
        return dayjsValue.isValid() ? dayjsValue.format('MM/DD HH:mm') : '';
    }

    /**
     * 暴露对外的全局方法。
     *
     * @returns {void} 在 window 上注册 InstanceListActions。
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
}

window.InstancesListPage = {
    mount: mountInstancesListPage,
};
