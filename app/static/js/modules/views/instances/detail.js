(function (window) {
    'use strict';

    const LodashUtils = window.LodashUtils;
    const DOMHelpers = window.DOMHelpers;
    const InstanceManagementService = window.InstanceManagementService;
    const InstanceService = window.InstanceService;
    const gridjs = window.gridjs;
    const GridWrapper = window.GridWrapper;
    const gridHtml = gridjs ? gridjs.html : null;
    const connectionManager = window.connectionManager || null;
    const toast = window.toast || {
        success: console.info,
        error: console.error,
        info: console.info,
    };
    const timeUtils = window.timeUtils;
    if (!timeUtils) {
        throw new Error('timeUtils 未初始化');
    }
    const helpersFallback = {
        ready: (fn) => fn?.(),
        selectOne: () => ({ length: 0, first: () => null, text: () => '', html: () => {}, attr: () => {}, on: () => {}, off: () => {} }),
        select: () => ({ length: 0, each: () => {} }),
        from: () => ({ html: () => {}, attr: () => {}, first: () => null })
    };

    const { ready, selectOne, select, from } = DOMHelpers || helpersFallback;

    let instanceService = null;
    let instanceCrudService = null;
    let instanceModals = null;
    let instanceStore = null;
	    let historyModal = null;
	    let accountsGrid = null;
	    let accountSearchTimer = null;
	    let databaseSizesGrid = null;
	    let databaseSearchTimer = null;

/**
 * 挂载实例详情页面。
 *
 * 初始化实例详情页面的所有组件，包括实例管理服务、Store、
 * 历史记录模态框等。提供连接测试、账户同步、权限查看等功能。
 *
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountInstanceDetailPage();
 */
function mountInstanceDetailPage() {

if (!LodashUtils) {
    throw new Error('LodashUtils 未初始化');
}

if (!DOMHelpers) {
    throw new Error('DOMHelpers 未初始化');
}

try {
    if (InstanceManagementService) {
        instanceService = new InstanceManagementService(window.httpU);
    } else {
        throw new Error('InstanceManagementService 未加载');
    }
} catch (error) {
    console.error('初始化 InstanceManagementService 失败:', error);
}

/**
 * 确保实例服务已初始化。
 *
 * @return {boolean} 如果服务已初始化返回 true，否则返回 false
 */
function ensureInstanceService() {
    if (!instanceService) {
        if (window.toast?.error) {
            window.toast.error('实例管理服务未初始化');
        } else {
            console.error('实例管理服务未初始化');
        }
        return false;
    }
    return true;
}

	// 页面加载完成，不自动测试连接
		ready(() => {
		    bindTemplateActions();
		    initializeInstanceStore();
		    initializeHistoryModal();
		    initializeInstanceModals();
		    initializeAccountsGrid();
		    bindAccountSearchInput();
		    initializeDatabaseSizesGrid();
		    bindDatabaseSearchInput();
		    const checkbox = selectOne('#showDeletedAccounts');
		    if (checkbox.length) {
		        const element = checkbox.first();
		        element.checked = false;
		        toggleDeletedAccounts();
		    }
		    const databaseCheckbox = selectOne('#showDeletedDatabases');
		    if (databaseCheckbox.length) {
		        const element = databaseCheckbox.first();
		        element.checked = false;
		        toggleDeletedDatabases();
		    }
		    window.setTimeout(loadDatabaseSizes, 500);
		});

/**
 * 初始化实例 Store。
 *
 * @return {void}
 */
function initializeInstanceStore() {
    if (!window.createInstanceStore) {
        console.warn('createInstanceStore 未加载，跳过实例 Store 初始化');
        return;
    }
    if (!ensureInstanceService()) {
        return;
    }
    try {
        instanceStore = window.createInstanceStore({
            service: instanceService,
            emitter: window.mitt ? window.mitt() : null,
        });
    } catch (error) {
        console.error('初始化 InstanceStore 失败:', error);
        instanceStore = null;
        return;
    }
    const numericId = Number(getInstanceId());
    const metadata = Number.isFinite(numericId) ? [{ id: numericId, name: getInstanceName() }] : [];
    instanceStore.init({ instances: metadata }).catch((error) => {
        console.warn('InstanceStore 初始化失败', error);
    });
    window.addEventListener('beforeunload', teardownInstanceStore, { once: true });
}

/**
 * 页面卸载时销毁 Store。
 *
 * @return {void}
 */
function teardownInstanceStore() {
    if (!instanceStore) {
        return;
    }
    instanceStore.destroy?.();
    instanceStore = null;
}

/**
 * 测试数据库连接。
 *
 * 使用连接管理 API 测试实例的数据库连接状态。
 *
 * @param {Event} event - 点击事件对象
 * @return {void}
 */
function testConnection(event) {
    const fallbackBtn = selectOne('[data-action="test-connection"]').first();
    const testBtn = event?.currentTarget || event?.target || fallbackBtn;
    if (!testBtn) {
        console.warn('未找到测试连接按钮');
        return;
    }
    const buttonWrapper = from(testBtn);
    const originalText = buttonWrapper.html();

    // 记录操作开始日志
    console.info('开始测试连接', {
        operation: 'test_connection',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>测试中...');
    buttonWrapper.attr('disabled', 'disabled');

    // 使用新的连接管理API
    connectionManager.testInstanceConnection(getInstanceId(), {
        onSuccess: (data) => {
            // 记录成功日志
            console.info('测试连接成功', {
                operation: 'test_connection',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'success',
                message: data.message || '数据库连接正常'
            });

            const resultDiv = selectOne('#testResult');
            const statusBadge = selectOne('#connectionStatus');

            if (statusBadge?.length) {
                statusBadge.text('正常');
                statusBadge.attr('class', 'status-pill status-pill--success');
            }

            // 使用连接管理组件的显示方法
            connectionManager.showTestResult(data, 'testResultContent');
            const resultElement = resultDiv.first();
            if (resultElement) {
                resultElement.style.display = 'block';
            }
        },
        onError: (error) => {
            // 记录失败日志
            console.error('测试连接失败', {
                operation: 'test_connection',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'failed',
                error: error.error
            });

            const resultDiv = selectOne('#testResult');
            const statusBadge = selectOne('#connectionStatus');

            if (statusBadge?.length) {
                statusBadge.text('失败');
                statusBadge.attr('class', 'status-pill status-pill--danger');
            }

            // 使用连接管理组件的显示方法
            connectionManager.showTestResult(error, 'testResultContent');
            const resultElement = resultDiv.first();
            if (resultElement) {
                resultElement.style.display = 'block';
            }
        }
    }).finally(() => {
        buttonWrapper.html(originalText || '测试连接');
        buttonWrapper.attr('disabled', null);
    });
}

/**
 * 同步实例账户。
 *
 * @param {Event} event - 点击事件对象
 * @return {void}
 */
function syncAccounts(event) {
    if (!ensureInstanceService()) {
        return;
    }
    const fallbackBtn = selectOne('[data-action="sync-accounts"]').first();
    const syncBtn = event?.currentTarget || event?.target || fallbackBtn;
    if (!syncBtn) {
        console.warn('未找到同步账户按钮');
        return;
    }
    const buttonWrapper = from(syncBtn);
    const originalText = buttonWrapper.html();

    // 记录操作开始日志
    console.info('开始同步账户', {
        operation: 'sync_accounts',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
    buttonWrapper.attr('disabled', 'disabled');

    const customUrl = getSyncAccountsUrl();
    const syncOptions = customUrl ? { customUrl } : undefined;
    const request = instanceStore
        ? instanceStore.actions.syncInstanceAccounts(getInstanceId(), syncOptions)
        : instanceService.syncInstanceAccounts(getInstanceId(), syncOptions);
    request
        .then(data => {
            const isSuccess = data?.success || Boolean(data?.message);
            const successMessage = data?.message || data?.data?.result?.message || '账户同步成功';
            const errorMessage =
                data?.error ||
                data?.message && !isSuccess ? data.message : '账户同步失败';

            if (isSuccess) {
                console.info('同步账户成功', {
                    operation: 'sync_accounts',
                    instance_id: getInstanceId(),
                    instance_name: getInstanceName(),
                    result: 'success',
                    message: successMessage
                });
                toast.success(successMessage || '账户同步成功');
            } else {
                console.error('同步账户失败', {
                    operation: 'sync_accounts',
                    instance_id: getInstanceId(),
                    instance_name: getInstanceName(),
                    result: 'failed',
                    error: errorMessage
                });
                toast.error(errorMessage || '账户同步失败');
            }
        })
        .catch(error => {
            // 记录异常日志
            console.error('同步账户异常', error, {
                operation: 'sync_accounts',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'exception'
            });
            toast.error('同步账户失败: ' + (error?.message || '未知错误'));
        })
        .finally(() => {
            buttonWrapper.html(originalText || '同步账户');
            buttonWrapper.attr('disabled', null);
        });
}

function openEditInstance(event) {
    event?.preventDefault?.();
    if (!instanceModals) {
        initializeInstanceModals();
    }
    if (!instanceModals?.openEdit) {
        window.toast?.error?.('实例编辑模态未初始化');
        return;
    }
    instanceModals.openEdit(getInstanceId());
}

async function confirmDeleteInstance(event) {
    event?.preventDefault?.();
    if (!ensureInstanceCrudService()) {
        window.toast?.error?.('实例服务未就绪');
        return;
    }
    const instanceId = getInstanceId();
    const instanceName = getInstanceName();

    const confirmDanger = window.UI?.confirmDanger;
    if (typeof confirmDanger !== 'function') {
        window.toast?.error?.('确认组件未初始化');
        return;
    }

    const confirmed = await confirmDanger({
        title: '确认移入回收站',
        message: '该操作将把实例移入回收站（可恢复），请确认影响范围后继续。',
        details: [
            { label: '目标实例', value: instanceName || `ID: ${instanceId}`, tone: 'danger' },
            { label: '可恢复', value: '可在实例管理页勾选“显示已删除”后恢复', tone: 'info' },
        ],
        confirmText: '确认移入',
        confirmButtonClass: 'btn-danger',
    });
    if (!confirmed) {
        return;
    }
    const fallbackBtn = selectOne('[data-action="delete-instance"]').first();
    const button = event?.currentTarget || fallbackBtn;
    let originalHtml = null;
    if (button) {
        originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>处理中...';
        button.disabled = true;
    }
    instanceCrudService
        .deleteInstance(instanceId)
        .then((resp) => {
            if (!resp?.success) {
                throw new Error(resp?.message || '移入回收站失败');
            }
            window.toast?.success?.(resp?.message || '实例已移入回收站');
            window.location.href = '/instances';
        })
        .catch((error) => {
            console.error('移入回收站失败', error);
            window.toast?.error?.(resolveDetailErrorMessage(error, '移入回收站失败'));
            if (button && originalHtml) {
                button.innerHTML = originalHtml;
                button.disabled = false;
            }
        });
}

/**
 * 同步实例容量数据。
 *
 * @param {number|string} instanceId - 实例 ID
 * @param {string} instanceName - 实例名称
 * @param {Event} event - 点击事件对象
 * @return {void}
 */
function syncCapacity(instanceId, instanceName, event) {
    if (!ensureInstanceService()) {
        return;
    }
    const fallbackBtn = selectOne('[data-action="sync-capacity"]').first();
    const syncBtn = event?.currentTarget || event?.target || fallbackBtn;
    if (!syncBtn) {
        console.warn('未找到同步容量按钮');
        return;
    }
    const buttonWrapper = from(syncBtn);
    const originalText = buttonWrapper.html();

    // 记录操作开始日志
    console.info('开始同步容量', {
        operation: 'sync_capacity',
        instance_id: instanceId,
        instance_name: instanceName
    });

    buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
    buttonWrapper.attr('disabled', 'disabled');

    const request = instanceStore
        ? instanceStore.actions.syncInstanceCapacity(instanceId)
        : instanceService.syncInstanceCapacity(instanceId);
    request
        .then(data => {
            if (data.success) {
                // 记录成功日志
                console.info('同步容量成功', {
                    operation: 'sync_capacity',
                    instance_id: instanceId,
                    instance_name: instanceName,
                    result: 'success',
                    message: data.message || '容量同步成功'
                });
                toast.success(data.message || '容量同步成功');

                // 刷新数据库容量显示
                setTimeout(() => {
                    loadDatabaseSizes();
                }, 1000);
            } else if (data.error) {
                // 记录失败日志
                console.error('同步容量失败', {
                    operation: 'sync_capacity',
                    instance_id: instanceId,
                    instance_name: instanceName,
                    result: 'failed',
                    error: data.error
                });
                toast.error(data.error);
            }
        })
        .catch(error => {
            // 记录异常日志
            console.error('同步容量异常', error, {
                operation: 'sync_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'exception'
            });
            toast.error('同步容量失败: ' + (error.message || '未知错误'));
        })
        .finally(() => {
            buttonWrapper.html(originalText || '同步容量');
            buttonWrapper.attr('disabled', null);
        });
}

/**
 * 查看实例账户权限。
 *
 * @param {number|string} accountId - 账户 ID
 * @return {void}
 */
function viewInstanceAccountPermissions(accountId) {
    // 调用全局的 viewAccountPermissions 函数，指定instances页面的API URL
    window.viewAccountPermissions(accountId, {
        apiUrl: `/instances/api/${getInstanceId()}/accounts/${accountId}/permissions`
    });
}

/**
 * 初始化账户列表 Grid.js。
 *
 * @returns {void}
 */
function initializeAccountsGrid() {
    const container = document.getElementById('instance-accounts-grid');
    if (!container) {
        return;
    }
    if (!gridjs || !GridWrapper) {
        console.warn('Grid.js 或 GridWrapper 未加载，跳过账户列表初始化');
        return;
    }
    if (!gridHtml) {
        console.warn('gridjs.html 未加载，账户列表将回退为纯文本渲染');
    }

    accountsGrid = new GridWrapper(container, {
        search: false,
        sort: false,
        columns: buildAccountsGridColumns(),
        server: {
            url: buildAccountsBaseUrl(),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            then: handleAccountsServerResponse,
            total: (response) => {
                const payload = response?.data || response || {};
                const total = payload.total || 0;
                updateAccountCount(total);
                return total;
            },
        },
    });

    accountsGrid.setFilters(
        {
            include_deleted: 'false',
            search: '',
        },
        { silent: true },
    );
    accountsGrid.init();
}

function buildAccountsBaseUrl() {
    return `/instances/api/${getInstanceId()}/accounts?sort=username&order=asc`;
}

function handleAccountsServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || [];
    return items.map((item) => ([
        item.id || null,
        item.username || '-',
        item.is_locked,
        item.is_superuser,
        item.is_deleted,
        item.last_change_time || '',
        null,
        item,
    ]));
}

function resolveAccountRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
}

function buildAccountsGridColumns() {
    const columns = [
        {
            name: 'ID',
            id: 'id',
            width: '80px',
            formatter: (cell) => renderAccountIdCell(cell),
        },
        {
            name: '账户',
            id: 'username',
            formatter: (cell, row) => renderAccountUsernameCell(cell, resolveAccountRowMeta(row)),
        },
        {
            name: '锁定',
            id: 'is_locked',
            width: '70px',
            formatter: (cell) => renderAccountLockedBadge(Boolean(cell)),
        },
        {
            name: '超管',
            id: 'is_superuser',
            width: '70px',
            formatter: (cell) => renderAccountSuperuserBadge(Boolean(cell)),
        },
        {
            name: '删除',
            id: 'is_deleted',
            width: '70px',
            formatter: (cell) => renderAccountDeletedBadge(Boolean(cell)),
        },
        {
            name: '最后变更',
            id: 'last_change_time',
            width: '180px',
            formatter: (cell) => renderAccountLastChangeTime(cell),
        },
        {
            id: 'actions',
            name: '操作',
            sort: false,
            width: '150px',
            formatter: (cell, row) => renderAccountActions(resolveAccountRowMeta(row)),
        },
        { id: '__meta__', hidden: true },
    ];
    return columns;
}

function renderAccountIdCell(value) {
    const text = value === undefined || value === null ? '-' : String(value);
    if (!gridHtml) {
        return text;
    }
    return gridHtml(`<span class="chip-outline chip-outline--muted">${escapeHtml(text)}</span>`);
}

function renderAccountUsernameCell(value, meta) {
    const username = value === undefined || value === null ? '-' : String(value);
    if (!gridHtml) {
        return username;
    }
    const typeSpecific = meta?.type_specific || {};
    const host = typeSpecific?.host ? String(typeSpecific.host) : null;
    const plugin = typeSpecific?.plugin ? String(typeSpecific.plugin).toUpperCase() : null;
    const subtitleParts = [];
    if (host && !username.includes('@')) {
        subtitleParts.push(`@${host}`);
    }
    if (plugin) {
        subtitleParts.push(plugin);
    }
    const subtitle = subtitleParts.length ? `<div class="text-muted small">${escapeHtml(subtitleParts.join(' · '))}</div>` : '';
    return gridHtml(`
        <div class="d-flex flex-column">
            <div class="fw-semibold">${escapeHtml(username)}</div>
            ${subtitle}
        </div>
    `);
}

function renderAccountLockedBadge(isLocked) {
    const label = isLocked ? '已锁定' : '正常';
    const cls = isLocked ? 'status-pill status-pill--danger' : 'status-pill status-pill--success';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(label)}</span>`) : label;
}

function renderAccountSuperuserBadge(isSuperuser) {
    const label = isSuperuser ? '是' : '否';
    const cls = isSuperuser ? 'status-pill status-pill--warning' : 'status-pill status-pill--muted';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(label)}</span>`) : label;
}

function renderAccountDeletedBadge(isDeleted) {
    const label = isDeleted ? '已删除' : '正常';
    const cls = isDeleted ? 'status-pill status-pill--danger' : 'status-pill status-pill--success';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(label)}</span>`) : label;
}

function renderAccountLastChangeTime(value) {
    if (!value) {
        return gridHtml ? gridHtml('<span class="text-muted">-</span>') : '-';
    }
    const formatted = timeUtils ? timeUtils.formatDateTime(value) : String(value);
    return gridHtml ? gridHtml(`<span class="text-muted">${escapeHtml(formatted)}</span>`) : formatted;
}

function renderAccountActions(meta) {
    const accountId = meta?.id;
    if (!accountId) {
        return '';
    }
    const safeId = escapeHtml(String(accountId));
    if (!gridHtml) {
        return '';
    }
    return gridHtml(`
        <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-primary" data-action="view-permissions" data-account-id="${safeId}" title="查看权限">
                <i class="fas fa-shield-alt"></i>
            </button>
            <button class="btn btn-outline-secondary" data-action="view-history" data-account-id="${safeId}" title="变更历史">
                <i class="fas fa-history"></i>
            </button>
        </div>
    `);
}

function updateAccountCount(total) {
    const badge = selectOne('#accountCount');
    if (!badge.length) {
        return;
    }
    const count = Number(total) || 0;
    badge.text(`共 ${count} 个账户`);
}

function updateAccountsGridFilters(patch) {
    if (!accountsGrid) {
        return;
    }
    const current = accountsGrid.currentFilters || {};
    const next = { ...current, ...(patch || {}) };
    accountsGrid.setFilters(next);
}

function bindAccountSearchInput() {
    const input = document.getElementById('accountSearchInput');
    if (!input) {
        return;
    }
    input.addEventListener('input', () => {
        if (accountSearchTimer) {
            window.clearTimeout(accountSearchTimer);
        }
        accountSearchTimer = window.setTimeout(() => {
            const value = input.value ? input.value.trim() : '';
            updateAccountsGridFilters({ search: value });
        }, 250);
    });
}

/**
 * 初始化数据库容量列表 Grid.js。
 *
 * @returns {void}
 */
function initializeDatabaseSizesGrid() {
    const container = document.getElementById('instance-databases-grid');
    if (!container) {
        return;
    }
    if (!gridjs || !GridWrapper) {
        console.warn('Grid.js 或 GridWrapper 未加载，跳过数据库容量列表初始化');
        return;
    }
    if (!gridHtml) {
        console.warn('gridjs.html 未加载，数据库容量列表将回退为纯文本渲染');
    }

    let wrapper = null;
    const paginationUrl = (prev, page, limit) => {
        if (!wrapper) {
            return prev;
        }
        let next = wrapper.applyFiltersToUrl(prev, wrapper.currentFilters);
        next = wrapper.removeQueryKeys(next, ['page', 'page_size', 'pageSize', 'limit', 'offset']);
        next = wrapper.appendParam(next, `limit=${limit}`);
        next = wrapper.appendParam(next, `offset=${page * limit}`);
        return next;
    };

    wrapper = new GridWrapper(container, {
        search: false,
        sort: false,
        pagination: {
            enabled: true,
            limit: 20,
            summary: true,
            server: { url: paginationUrl },
        },
        columns: buildDatabaseSizesGridColumns(),
        server: {
            url: buildDatabaseSizesBaseUrl(),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            then: handleDatabaseSizesServerResponse,
            total: (response) => {
                const payload = response?.data || response || {};
                const total = payload.total || 0;
                updateDatabaseCount(total);
                return total;
            },
        },
    });

    databaseSizesGrid = wrapper;
    databaseSizesGrid.setFilters(
        {
            latest_only: 'true',
            include_inactive: 'false',
            database_name: '',
        },
        { silent: true },
    );
    databaseSizesGrid.init();
}

function buildDatabaseSizesBaseUrl() {
    return `/instances/api/databases/${getInstanceId()}/sizes`;
}

function handleDatabaseSizesServerResponse(response) {
    const payload = response?.data || response || {};
    const databases = Array.isArray(payload.databases) ? payload.databases : [];
    return databases.map((entry) => ([
        entry.database_name || '-',
        entry.size_mb,
        entry.is_active,
        entry.collected_at,
        entry,
    ]));
}

function resolveDatabaseRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
}

function buildDatabaseSizesGridColumns() {
    return [
        {
            name: '数据库',
            id: 'database_name',
            formatter: (cell, row) => renderDatabaseNameCell(cell, resolveDatabaseRowMeta(row)),
        },
        {
            name: '总大小',
            id: 'size_mb',
            width: '140px',
            formatter: (cell, row) => renderDatabaseSizeCell(cell, resolveDatabaseRowMeta(row)),
        },
        {
            name: '状态',
            id: 'is_active',
            width: '220px',
            formatter: (cell, row) => renderDatabaseStatusCell(Boolean(cell !== false), resolveDatabaseRowMeta(row)),
        },
        {
            name: '采集时间',
            id: 'collected_at',
            width: '200px',
            formatter: (cell) => renderDatabaseCollectedAtCell(cell),
        },
        { id: '__meta__', hidden: true },
    ];
}

function renderDatabaseNameCell(value, meta) {
    const name = value === undefined || value === null ? '-' : String(value);
    if (!gridHtml) {
        return name;
    }
    const isActive = meta?.is_active !== false;
    const iconClass = isActive ? 'text-primary' : 'text-muted';
    const textClass = isActive ? 'fw-semibold' : 'fw-semibold text-muted';
    return gridHtml(`
        <div class="d-flex align-items-start">
            <i class="fas fa-database ${iconClass} me-2 mt-1"></i>
            <div class="${textClass}" style="word-wrap: break-word; white-space: normal; line-height: 1.4;">${escapeHtml(name)}</div>
        </div>
    `);
}

function resolveSizeBadgeClass(sizeMb) {
    const numeric = Number(sizeMb) || 0;
    if (numeric >= 1024 * 1000) {
        return 'status-pill status-pill--danger';
    }
    if (numeric >= 1024 * 100) {
        return 'status-pill status-pill--warning';
    }
    if (numeric >= 1024 * 10) {
        return 'status-pill status-pill--info';
    }
    return 'status-pill status-pill--success';
}

function renderDatabaseSizeCell(value) {
    const sizeValue = Number(value) || 0;
    if (!sizeValue) {
        return gridHtml ? gridHtml('<span class="text-muted">无数据</span>') : '无数据';
    }
    const sizeLabel = formatGbLabelFromMb(sizeValue);
    const cls = resolveSizeBadgeClass(sizeValue);
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(sizeLabel)}</span>`) : sizeLabel;
}

function renderDatabaseStatusCell(_value, meta) {
    const isActive = meta?.is_active !== false;
    if (!gridHtml) {
        return isActive ? '在线' : '已删除';
    }
    const statusBadge = isActive
        ? '<span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>在线</span>'
        : '<span class="status-pill status-pill--danger"><i class="fas fa-trash me-1"></i>已删除</span>';

    const lastSeen = meta?.last_seen_date ? timeUtils.formatDate(meta.last_seen_date) : null;
    const deletedAt = meta?.deleted_at ? timeUtils.formatDateTime(meta.deleted_at) : null;
    const statusMeta = !isActive && (lastSeen || deletedAt)
        ? `<div class="text-muted small">${lastSeen ? `最后出现：${escapeHtml(lastSeen)}` : ''}${deletedAt ? `<br/>隐藏时间：${escapeHtml(deletedAt)}` : ''}</div>`
        : '';

    return gridHtml(`
        <div class="d-flex flex-column">
            <div>${statusBadge}</div>
            ${statusMeta}
        </div>
    `);
}

function renderDatabaseCollectedAtCell(value) {
    const formatted = value ? timeUtils.formatDateTime(value) : '未采集';
    return gridHtml ? gridHtml(`<span class="text-muted">${escapeHtml(formatted)}</span>`) : formatted;
}

function updateDatabaseCount(total) {
    const badge = selectOne('#databaseCount');
    if (!badge.length) {
        return;
    }
    const count = Number(total) || 0;
    badge.text(`共 ${count} 个数据库`);
}

function updateDatabaseSizesGridFilters(patch) {
    if (!databaseSizesGrid) {
        return;
    }
    const current = databaseSizesGrid.currentFilters || {};
    const next = { ...current, ...(patch || {}) };
    databaseSizesGrid.setFilters(next);
}

function bindDatabaseSearchInput() {
    const input = document.getElementById('databaseSearchInput');
    if (!input) {
        return;
    }
    input.addEventListener('input', () => {
        if (databaseSearchTimer) {
            window.clearTimeout(databaseSearchTimer);
        }
        databaseSearchTimer = window.setTimeout(() => {
            const value = input.value ? input.value.trim() : '';
            updateDatabaseSizesGridFilters({ database_name: value });
        }, 250);
    });
}

function loadDatabaseSizesSummary() {
    if (!ensureInstanceService()) {
        return;
    }
    const instanceId = getInstanceId();
    instanceService.fetchDatabaseSizes(instanceId, {
        latest_only: true,
        include_inactive: true,
        limit: 1,
        offset: 0,
    })
        .then((data) => {
            const payload = data?.data || data || {};
            updateDatabaseSizesSummary(payload);
        })
        .catch((error) => {
            console.error('加载数据库容量汇总失败:', error);
        });
}

function updateDatabaseSizesSummary(payload) {
    if (!payload || typeof payload !== 'object') {
        return;
    }
    const online = selectOne('#databaseOnlineCount');
    const deleted = selectOne('#databaseDeletedCount');
    const total = selectOne('#databaseTotalCapacity');

    const onlineCount = Number(payload.active_count ?? 0) || 0;
    const deletedCount = Number(payload.filtered_count ?? 0) || 0;
    const totalSize = Number(payload.total_size_mb ?? 0) || 0;

    if (online.length) {
        online.text(String(onlineCount));
    }
    if (deleted.length) {
        deleted.text(String(deletedCount));
    }
    if (total.length) {
        total.text(formatGbLabelFromMb(totalSize));
    }
}

/**
 * 转义 HTML 特殊字符。
 *
 * @param {*} value - 要转义的值
 * @return {string} 转义后的字符串
 */
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function resolvePrivilegeActionVariant(action) {
    switch (action) {
        case 'GRANT':
            return { text: '授权', variant: 'status-pill--success' };
        case 'REVOKE':
            return { text: '撤销', variant: 'status-pill--danger' };
        case 'ALTER':
            return { text: '更新', variant: 'status-pill--info' };
        default:
            return { text: '变更', variant: 'status-pill--muted' };
    }
}

function resolveChangeTypeVariant(rawType) {
    switch (rawType) {
        case 'add':
            return { label: '新增变更', variant: 'status-pill--success' };
        case 'remove':
        case 'delete':
            return { label: '移除变更', variant: 'status-pill--danger' };
        case 'update':
        case 'alter':
            return { label: '更新变更', variant: 'status-pill--info' };
        default:
            return { label: '变更', variant: 'status-pill--muted' };
    }
}

function formatHistoryMeta(account, fallback) {
    if (!account || typeof account !== 'object') {
        return fallback;
    }
    const parts = [];
    if (account.username) {
        parts.push(account.username);
    }
    if (account.db_type) {
        parts.push(String(account.db_type).toUpperCase());
    }
    if (account.id) {
        parts.push(`#${account.id}`);
    }
    return parts.length ? parts.join(' · ') : fallback;
}

function renderPermissionValueChips(values, emptyLabel) {
    if (!values || (Array.isArray(values) && values.length === 0)) {
        return `<span class="ledger-chip ledger-chip--muted">${emptyLabel}</span>`;
    }
    const list = Array.isArray(values) ? values : [values];
    return list
        .filter((value) => value !== undefined && value !== null && value !== '')
        .map((value) => `<span class="ledger-chip">${escapeHtml(value)}</span>`)
        .join('') || `<span class="ledger-chip ledger-chip--muted">${emptyLabel}</span>`;
}

function renderChangeHistoryCard(change) {
    const rawType = (change?.change_type || '').toLowerCase();
    const typeInfo = resolveChangeTypeVariant(rawType);
    const privilegeHtml = renderPrivilegeDiffEntries(change?.privilege_diff);
    const otherHtml = renderOtherDiffEntries(change?.other_diff);
    const sections = privilegeHtml || otherHtml
        ? `${privilegeHtml}${otherHtml}`
        : `<section class="change-history-section">
                <span class="status-pill status-pill--muted">无具体字段变更</span>
           </section>`;
    return `
        <article class="change-history-card">
            <div class="change-history-card__header">
                <span class="chip-outline chip-outline--brand">
                    <i class="fas fa-user-edit me-2"></i>${escapeHtml(change?.change_type || '变更')}
                </span>
                <span class="status-pill ${typeInfo.variant}">${typeInfo.label}</span>
                <span class="status-pill status-pill--muted">
                    <i class="fas fa-clock me-1"></i>${escapeHtml(change?.change_time || '未知时间')}
                </span>
            </div>
            <p class="change-history-card__message">${escapeHtml(change?.message || '无摘要')}</p>
            ${sections}
        </article>
    `;
}

/**
 * 渲染权限差异条目。
 *
 * @param {Array} diffEntries - 差异条目数组
 * @return {string} 渲染的 HTML 字符串
 */
function renderPrivilegeDiffEntries(diffEntries) {
    if (!Array.isArray(diffEntries) || diffEntries.length === 0) {
        return '';
    }

    const items = diffEntries.map((entry) => {
        const action = String(entry?.action || '').toUpperCase();
        const actionInfo = resolvePrivilegeActionVariant(action);
        const target = entry?.object || entry?.label || entry?.field || '权限';
        const permissionsHtml = renderPermissionValueChips(entry?.permissions, '无权限');
        return `
            <li class="change-history-permission">
                <span class="status-pill ${actionInfo.variant}">${actionInfo.text}</span>
                <div class="change-history-permission__body">
                    <span class="chip-outline chip-outline--muted">${escapeHtml(target)}</span>
                    <div class="ledger-chip-stack">
                        ${permissionsHtml}
                    </div>
                </div>
            </li>
        `;
    });

    return `
        <section class="change-history-section">
            <div class="change-history-section__title">
                <span class="chip-outline chip-outline--brand">
                    <i class="fas fa-key me-2"></i>权限变更
                </span>
            </div>
            <ul class="change-history-permission-list">
                ${items.join('')}
            </ul>
        </section>
    `;
}

/**
 * 渲染其他差异条目。
 *
 * @param {Array} diffEntries - 差异条目数组
 * @return {string} 渲染的 HTML 字符串
 */
function renderOtherDiffEntries(diffEntries) {
    if (!Array.isArray(diffEntries) || diffEntries.length === 0) {
        return '';
    }

    const rows = diffEntries.map((entry) => {
        const label = entry?.label || entry?.field || '其他字段';
        const before = entry?.before ? `<span class="ledger-chip ledger-chip--muted">${escapeHtml(entry.before)}</span>` : '<span class="ledger-chip ledger-chip--muted">未设置</span>';
        const after = entry?.after ? `<span class="ledger-chip">${escapeHtml(entry.after)}</span>` : '<span class="ledger-chip">未设置</span>';
        const desc = entry?.description
            ? `<p class="change-history-stack-desc">${escapeHtml(entry.description)}</p>`
            : '';
        return `
            <div class="change-history-stack-row">
                <span class="chip-outline chip-outline--muted">${escapeHtml(label)}</span>
                <div class="change-history-stack-value">
                    <span class="status-pill status-pill--muted">原</span>
                    ${before}
                    <span class="status-pill status-pill--info">现</span>
                    ${after}
                </div>
                ${desc}
            </div>
        `;
    });

    return `
        <section class="change-history-section">
            <div class="change-history-section__title">
                <span class="chip-outline chip-outline--brand">
                    <i class="fas fa-sliders-h me-2"></i>其他属性
                </span>
            </div>
            <div class="change-history-stack">
                ${rows.join('')}
            </div>
        </section>
    `;
}

/**
 * 查看账户变更历史。
 *
 * @param {number|string} accountId - 账户 ID
 * @return {void}
 */
function viewAccountChangeHistory(accountId) {
    if (!ensureInstanceService()) {
        return;
    }
    const historyContentWrapper = selectOne('#historyContent');
    if (historyContentWrapper.length) {
        historyContentWrapper.html(renderHistoryLoading());
    }
    const modalMeta = selectOne('#historyModalMeta');
    if (modalMeta.length) {
        modalMeta.text(`账户 #${accountId} · 加载中`);
    }
    instanceService.fetchAccountChangeHistory(getInstanceId(), accountId)
        .then(data => {
            const payload = (data && typeof data === 'object' && data.data && typeof data.data === 'object')
                ? data.data
                : data;
            const history = Array.isArray(payload?.history) ? payload.history : null;

            if (data && data.success) {
                // 显示变更历史模态框
                if (!historyContentWrapper.length) {
                    console.error('未找到历史记录模态框元素');
                    return;
                }
                if (modalMeta.length) {
                    modalMeta.text(formatHistoryMeta(payload?.account, `账户 #${accountId}`));
                }
                if (history && history.length > 0) {
                    const cards = history.map((change) => renderChangeHistoryCard(change)).join('');
                    historyContentWrapper.html(cards);
                } else {
                    historyContentWrapper.html(`
                        <div class="change-history-modal__empty">
                            <span class="status-pill status-pill--muted">暂无变更记录</span>
                        </div>
                    `);
                }

                ensureHistoryModal().open();
            } else {
                console.error('获取变更历史失败:', data?.error || data?.message);
                toast.error(data?.error || data?.message || '获取变更历史失败');
                if (historyContentWrapper.length) {
                    historyContentWrapper.html(`
                        <div class="change-history-modal__empty">
                            <span class="status-pill status-pill--danger">${escapeHtml(data?.error || data?.message || '获取变更历史失败')}</span>
                        </div>
                    `);
                }
            }
        })
        .catch(error => {
            console.error('获取变更历史失败:', error.message || error);
            const message = error?.message || '获取变更历史失败';
            if (historyContentWrapper.length) {
                historyContentWrapper.html(`
                    <div class="change-history-modal__empty">
                        <span class="status-pill status-pill--danger">${escapeHtml(message)}</span>
                    </div>
                `);
            }
            if (modalMeta.length) {
                modalMeta.text(`账户 #${accountId}`);
            }
        });
}

/**
 * 切换已删除账户的显示/隐藏。
 *
 * @return {void}
 */
function toggleDeletedAccounts() {
    const checkbox = selectOne('#showDeletedAccounts');
    if (!checkbox.length) {
        return;
    }

    const showAll = checkbox.first().checked;
    if (accountsGrid) {
        updateAccountsGridFilters({ include_deleted: showAll ? 'true' : 'false' });
        return;
    }

    const accountRows = select('.account-row');
    const accountCount = selectOne('#accountCount');
    if (!accountRows.length) {
        return;
    }

    let visibleCount = 0;
    accountRows.each((row) => {
        const isDeleted = row.getAttribute('data-is-deleted') === 'true';
        if (showAll || !isDeleted) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    if (accountCount.length) {
        accountCount.text(`共 ${visibleCount} 个账户`);
    }
}

// 显示提示信息

/**
 * 获取实例 ID。
 *
 * @return {string} 实例 ID
 */
function getInstanceId() {
    const datasetId = getInstanceDatasetValue('instanceId');
    if (datasetId) {
        return datasetId;
    }
    const urlParts = window.location.pathname.split('/');
    return urlParts[urlParts.length - 1];
}

/**
 * 获取实例名称。
 *
 * @return {string} 实例名称
 */
function getInstanceName() {
    const datasetName = getInstanceDatasetValue('instanceName');
    if (datasetName) {
        return datasetName;
    }
    const titleElement = selectOne('.basic-info-card__title');
    if (titleElement.length) {
        return (titleElement.text() || '').trim();
    }
    return '未知实例';
}

function getSyncAccountsUrl() {
    return getInstanceDatasetValue('syncAccountsUrl');
}

function getInstanceDatasetValue(field) {
    const root = document.getElementById('instanceDetailContainer');
    if (!root) {
        return null;
    }
    switch (field) {
        case 'instanceId':
            return root.dataset?.instanceId || root.getAttribute('data-instance-id') || null;
        case 'instanceName':
            return root.dataset?.instanceName || root.getAttribute('data-instance-name') || null;
        case 'syncAccountsUrl':
            return root.dataset?.syncAccountsUrl || root.getAttribute('data-sync-accounts-url') || null;
        default:
            return null;
    }
}

/**
 * 将 MB 值格式化为 GB 标签。
 *
 * @param {number} mbValue - MB 值
 * @return {string} 格式化后的字符串
 */
function formatGbLabelFromMb(mbValue) {
    const numeric = Number(mbValue) || 0;
    return window.NumberFormat.formatBytesFromMB(numeric, {
        unit: 'GB',
        precision: 3,
        trimZero: false,
        fallback: '0 GB',
    });
}

/**
 * 加载数据库容量数据。
 *
 * @return {void}
 */
function loadDatabaseSizes() {
    if (!ensureInstanceService()) {
        return;
    }

    if (databaseSizesGrid) {
        loadDatabaseSizesSummary();
        databaseSizesGrid.refresh();
        return;
    }

    const instanceId = getInstanceId();
    const contentDiv = selectOne('#databaseSizesContent');
    if (!contentDiv.length) {
        console.error('找不到数据库容量内容容器');
        return;
    }

    // 显示加载状态
    contentDiv.html(`
        <div class="text-center py-4">
            <i class="fas fa-spinner fa-spin fa-2x text-muted mb-3"></i>
            <p class="text-muted">正在加载数据库容量信息...</p>
        </div>
    `);

    instanceService.fetchDatabaseSizes(instanceId, {
        latest_only: true,
        include_inactive: true
    })
        .then(data => {
            const payload = data && typeof data === 'object'
                ? (data.data && typeof data.data === 'object' ? data.data : data)
                : {};

            if (payload && Array.isArray(payload.databases)) {
                displayDatabaseSizes(payload);
            } else {
                const errorMsg = data?.error || data?.message || '加载失败';
                displayDatabaseSizesError(errorMsg);
            }
        })
        .catch(error => {
            console.error('加载数据库容量信息失败:', error);
            displayDatabaseSizesError('网络错误，请稍后重试');
        });
}

/**
 * 显示数据库容量数据。
 *
 * @param {Object} payload - 容量数据对象
 * @return {void}
 */
function displayDatabaseSizes(payload) {
    const contentDiv = selectOne('#databaseSizesContent');
    if (!contentDiv.length) {
        return;
    }
    const rawDatabases = Array.isArray(payload?.databases) ? payload.databases : [];

    if (!rawDatabases.length) {
        contentDiv.html(`
            <div class="text-center py-4">
                <i class="fas fa-database fa-3x text-muted mb-3"></i>
                <p class="text-muted">暂无数据库容量信息</p>
                <p class="text-muted">点击"同步容量"按钮获取容量信息</p>
            </div>
        `);
        return;
    }

    const databases = LodashUtils.orderBy(
        rawDatabases,
        [
            (item) => Number(item?.size_mb) || 0,
        ],
        ['desc']
    );

    const totalSize = Number(payload?.total_size_mb ?? 0) || 0;
    const totalSizeLabel = formatGbLabelFromMb(totalSize);

    const filteredCount = Number(payload?.filtered_count ?? 0) || 0;
    const activeCount = Number(payload?.active_count ?? (databases.length - filteredCount));

    const deletedCount = filteredCount || databases.filter(db => db.is_active === false).length;
    const onlineCount = activeCount;

    let html = `
        <div class="row g-3 mb-3">
            <div class="col-lg-4 col-12">
                <div class="instance-stat-card">
                    <p class="instance-stat-card__label">在线数据库</p>
                    <span class="instance-stat-card__value" data-value-tone="success">${onlineCount}</span>
                    <span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>在线</span>
                </div>
            </div>
            <div class="col-lg-4 col-12">
                <div class="instance-stat-card">
                    <p class="instance-stat-card__label">已删除数据库</p>
                    <span class="instance-stat-card__value" data-value-tone="danger">${deletedCount}</span>
                    <span class="status-pill status-pill--danger"><i class="fas fa-trash me-1"></i>已删除</span>
                </div>
            </div>
            <div class="col-lg-4 col-12">
                <div class="instance-stat-card">
                    <p class="instance-stat-card__label">总容量</p>
                    <span class="instance-stat-card__value" data-value-tone="info">${totalSizeLabel}</span>
                    <span class="status-pill status-pill--info"><i class="fas fa-hdd me-1"></i>容量</span>
                </div>
            </div>
        </div>
        
        <div class="mb-3">
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="showDeletedDatabases" data-action="toggle-deleted-databases">
                <label class="form-check-label" for="showDeletedDatabases">
                    <i class="fas fa-eye me-1"></i>显示已删除数据库
                </label>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th style="width: 38%;"><i class="fas fa-database me-1"></i>数据库名称</th>
                        <th style="width: 18%;"><i class="fas fa-hdd me-1"></i>总大小</th>
                        <th style="width: 14%;"><i class="fas fa-trash me-1"></i>状态</th>
                        <th style="width: 30%;"><i class="fas fa-clock me-1"></i>采集时间</th>
                    </tr>
                </thead>
                <tbody>
    `;

    databases.forEach(db => {
        const isActive = db.is_active !== false;
        const sizeValue = Number(db.size_mb) || 0;
        const sizeLabel = formatGbLabelFromMb(sizeValue);
        const collectedAt = db.collected_at ? timeUtils.formatDateTime(db.collected_at) : '未采集';

        const iconClass = isActive ? 'text-primary' : 'text-muted';
        const textClass = isActive ? '' : 'text-muted';
        const rowClass = `database-row${isActive ? '' : ' table-light text-muted'}`;
        const rowStyle = isActive ? '' : ' style="opacity: 0.7;"';

        // 根据总大小判断颜色
        let sizeBadgeClass = 'status-pill status-pill--success';
        if (sizeValue >= 1024 * 1000) {
            sizeBadgeClass = 'status-pill status-pill--danger';
        } else if (sizeValue >= 1024 * 100) {
            sizeBadgeClass = 'status-pill status-pill--warning';
        } else if (sizeValue >= 1024 * 10) {
            sizeBadgeClass = 'status-pill status-pill--info';
        }

        const displaySize = sizeValue > 0 ? sizeLabel : '<span class="text-muted">无数据</span>';

        // 状态列显示
        const statusBadge = isActive
            ? '<span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>在线</span>'
            : '<span class="status-pill status-pill--danger"><i class="fas fa-trash me-1"></i>已删除</span>';

        const lastSeen = db.last_seen_date ? timeUtils.formatDate(db.last_seen_date) : null;
        const deletedAt = db.deleted_at ? timeUtils.formatDateTime(db.deleted_at) : null;
        const statusMeta = !isActive && (lastSeen || deletedAt)
            ? `<div class="text-muted small">${lastSeen ? `最后出现：${lastSeen}` : ''}${deletedAt ? `<br/>隐藏时间：${deletedAt}` : ''}</div>`
            : '';

        html += `
            <tr class="${rowClass}" data-is-active="${isActive}"${rowStyle}>
                <td>
                    <div class="d-flex align-items-start">
                        <i class="fas fa-database ${iconClass} me-2 mt-1"></i>
                        <div>
                            <strong class="${textClass}" style="word-wrap: break-word; white-space: normal; line-height: 1.4;">${db.database_name}</strong>
                        </div>
                    </div>
                </td>
                <td>
                    ${sizeValue > 0 ? `<span class="${sizeBadgeClass}">${sizeLabel}</span>` : displaySize}
                </td>
                <td>
                    ${statusBadge}
                    ${statusMeta}
                </td>
                <td>
                    <small class="text-muted">${collectedAt}</small>
                </td>
            </tr>
        `;
    });

   html += `
                </tbody>
            </table>
        </div>
    `;

    contentDiv.html(html);

    const checkbox = selectOne('#showDeletedDatabases');
    if (checkbox.length) {
        checkbox.first().checked = false;
    }
    toggleDeletedDatabases();
}

/**
 * 显示数据库容量加载错误。
 *
 * @param {Error|Object} error - 错误对象
 * @return {void}
 */
function displayDatabaseSizesError(error) {
    const contentDiv = selectOne('#databaseSizesContent');
    if (!contentDiv.length) {
        return;
    }
    contentDiv.html(`
        <div class="text-center py-4">
            <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
            <p class="text-muted">加载数据库容量信息失败</p>
            <p class="text-danger">${error}</p>
            <button class="btn btn-outline-primary" data-action="retry-load-database-sizes">
                <i class="fas fa-redo me-1"></i>重试
            </button>
        </div>
    `);
}

/**
 * 刷新数据库容量数据。
 *
 * @return {void}
 */
// 移除未使用导出，避免 no-unused-vars。

/**
 * 切换已删除数据库的显示/隐藏。
 *
 * @return {void}
 */
function toggleDeletedDatabases() {
    const checkbox = selectOne('#showDeletedDatabases');
    if (!checkbox.length) {
        return;
    }
    const showDeleted = checkbox.first().checked;

    if (databaseSizesGrid) {
        updateDatabaseSizesGridFilters({ include_inactive: showDeleted ? 'true' : 'false' });
        return;
    }

    const rows = select('#databaseSizesContent tbody tr[data-is-active]');
    if (!rows.length) {
        return;
    }
    rows.each((row) => {
        const isActive = row.getAttribute('data-is-active') !== 'false';
        if (!isActive) {
            row.style.display = showDeleted ? '' : 'none';
        }
    });
}

/**
 * 绑定模板动作事件，替代内联 onclick/onchange。
 *
 * @return {void}
 */
function bindTemplateActions() {
    const root = document.getElementById('instanceDetailContainer') || document;

    root.addEventListener('click', (event) => {
        const actionEl = event.target.closest('[data-action]');
        if (!actionEl) {
            return;
        }
        const action = actionEl.getAttribute('data-action');
        const actionEvent = { ...event, currentTarget: actionEl, target: actionEl };
        switch (action) {
            case 'test-connection':
                event.preventDefault();
                testConnection(actionEvent);
                break;
            case 'sync-accounts':
                event.preventDefault();
                syncAccounts(actionEvent);
                break;
            case 'sync-capacity':
                event.preventDefault();
                syncCapacity(getInstanceId(), getInstanceName(), actionEvent);
                break;
            case 'edit-instance':
                event.preventDefault();
                openEditInstance(actionEvent);
                break;
            case 'delete-instance':
                event.preventDefault();
                confirmDeleteInstance(actionEvent);
                break;
            case 'view-permissions': {
                const accountId = actionEl.getAttribute('data-account-id');
                if (accountId) {
                    viewInstanceAccountPermissions(accountId);
                }
                break;
            }
            case 'view-history': {
                const accountId = actionEl.getAttribute('data-account-id');
                if (accountId) {
                    viewAccountChangeHistory(accountId);
                }
                break;
            }
            case 'retry-load-database-sizes':
                event.preventDefault();
                loadDatabaseSizes();
                break;
            default:
                break;
        }
    });

    root.addEventListener('change', (event) => {
        const actionEl = event.target.closest('[data-action]');
        if (!actionEl) {
            return;
        }
        const action = actionEl.getAttribute('data-action');
        switch (action) {
            case 'toggle-deleted-accounts':
                toggleDeletedAccounts();
                break;
            case 'toggle-deleted-databases':
                toggleDeletedDatabases();
                break;
            default:
                break;
        }
    });
}

}

window.InstanceDetailPage = {
    mount: mountInstanceDetailPage,
};

/**
 * 渲染变更历史的加载占位。
 *
 * @returns {string} 包含加载态的 HTML 字符串。
 */
function renderHistoryLoading() {
    return `
        <div class="change-history-modal__loading text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2 text-muted">正在加载变更记录...</p>
        </div>
    `;
}

/**
 * 初始化历史记录模态框。
 *
 * @return {void}
 */
function initializeHistoryModal() {
    const factory = window.UI?.createModal;
    if (!factory) {
        throw new Error('UI.createModal 未加载，实例详情模态无法初始化');
    }
    historyModal = factory({
        modalSelector: '#historyModal',
        onClose: resetHistoryContent,
    });
}

function initializeInstanceModals() {
    if (!document.getElementById('instanceModal')) {
        return;
    }
    if (!window.InstanceModals?.createController) {
        console.warn('InstanceModals 未加载，实例编辑不可用');
        return;
    }
    try {
        instanceModals = window.InstanceModals.createController({
            http: window.httpU,
            FormValidator: window.FormValidator,
            ValidationRules: window.ValidationRules,
            toast: window.toast,
            DOMHelpers: window.DOMHelpers,
        });
        instanceModals.init?.();
    } catch (error) {
        console.error('初始化实例模态失败:', error);
        instanceModals = null;
    }
}

function ensureInstanceCrudService() {
    if (instanceCrudService) {
        return true;
    }
    if (!InstanceService) {
        console.warn('InstanceService 未注册，无法执行实例删除');
        return false;
    }
    try {
        instanceCrudService = new InstanceService(window.httpU);
        return true;
    } catch (error) {
        console.error('初始化 InstanceService 失败:', error);
        return false;
    }
}

function resolveDetailErrorMessage(error, fallback) {
    if (!error) {
        return fallback;
    }
    if (typeof error === 'string') {
        return error;
    }
    return error.message || fallback;
}

/**
 * 确保历史记录模态框已初始化。
 *
 * @throws {Error} 当模态框未初始化时抛出
 * @return {void}
 */
function ensureHistoryModal() {
    if (!historyModal) {
        throw new Error('变更历史模态未初始化');
    }
    return historyModal;
}

/**
 * 重置历史记录内容。
 *
 * @return {void}
 */
function resetHistoryContent() {
    const wrapper = selectOne('#historyContent');
    if (wrapper.length) {
        const loadingHtml = typeof renderHistoryLoading === 'function'
            ? renderHistoryLoading()
            : '<div class="change-history-modal__loading text-center py-4">加载中...</div>';
        wrapper.html(loadingHtml);
    }
    const modalMeta = selectOne('#historyModalMeta');
    if (modalMeta.length) {
        modalMeta.text('加载中...');
    }
}

})(window);
