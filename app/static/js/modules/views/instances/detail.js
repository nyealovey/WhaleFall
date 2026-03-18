(function (window) {
    'use strict';

    const LodashUtils = window.LodashUtils;
    const DOMHelpers = window.DOMHelpers;
    if (!DOMHelpers) {
        throw new Error('DOMHelpers 未初始化');
    }
    const InstanceManagementService = window.InstanceManagementService;
    const InstanceService = window.InstanceService;
    const gridjs = window.gridjs;
    const gridHtml = gridjs ? gridjs.html : null;
    const connectionManager = window.connectionManager;
    const toast = window.toast;
    if (!toast?.success || !toast?.error) {
        throw new Error('toast 未初始化');
    }
    const timeUtils = window.timeUtils;
    if (!timeUtils) {
        throw new Error('timeUtils 未初始化');
    }
    const { ready, selectOne, select, from } = DOMHelpers;

    let instanceService = null;
    let instanceCrudStore = null;
    let instanceModals = null;
    let instanceStore = null;
    let historyModal = null;
    let accountsGridController = null;
    let accountsGrid = null;
    let databaseSizesGrid = null;
    let tableSizesModal = null;
    const auditInfoState = {
        loaded: false,
        loading: false,
        payload: null,
        filters: {
            includeDisabled: false,
            scope: 'all',
            search: '',
        },
    };

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

const escapeHtml = window.UI?.escapeHtml;
const resolveErrorMessage = window.UI?.resolveErrorMessage;
const getRowMeta = window.GridRowMeta?.get;

if (typeof escapeHtml !== 'function') {
    console.error('UI.escapeHtml 未初始化');
    return;
}
if (typeof resolveErrorMessage !== 'function') {
    console.error('UI.resolveErrorMessage 未初始化');
    return;
}
if (typeof getRowMeta !== 'function') {
    console.error('GridRowMeta.get 未初始化');
    return;
}

    try {
        if (InstanceManagementService) {
            instanceService = new InstanceManagementService();
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
        configurePermissionViewer();
        bindTemplateActions();
        initializeInstanceStore();
        initializeHistoryModal();
        initializeDatabaseTableSizesModal();
        initializeInstanceModals();
        initializeAuditTab();
        resetGridFilterForms();
        initializeAccountsGrid();
        initializeDatabaseSizesGrid();
        window.setTimeout(loadDatabaseSizes, 500);
    });

function initializeAuditTab() {
    const auditTab = document.getElementById('audit-tab');
    if (!auditTab) {
        return;
    }
    auditTab.addEventListener('shown.bs.tab', () => {
        if (!auditInfoState.loaded && !auditInfoState.loading) {
            loadAuditInfo();
        }
    });
}

function configurePermissionViewer() {
    const viewer = window.PermissionViewer;
    const PermissionService = window.PermissionService;
    if (!viewer?.configure || typeof PermissionService !== 'function') {
        console.error('PermissionViewer/PermissionService 未加载，权限查看功能不可用');
        return;
    }
    if (typeof window.showPermissionsModal !== 'function') {
        console.error('showPermissionsModal 未加载，权限查看功能不可用');
        return;
    }
    let service = null;
    try {
        service = new PermissionService();
    } catch (error) {
        console.error('初始化 PermissionService 失败:', error);
        return;
    }
    try {
        viewer.configure({
            fetchPermissions: ({ accountId, apiUrl }) => {
                return apiUrl ? service.fetchByUrl(apiUrl) : service.fetchAccountPermissions(accountId);
            },
            showPermissionsModal: window.showPermissionsModal,
            toast: window.toast,
        });
    } catch (error) {
        console.error('配置 PermissionViewer 失败:', error);
    }
}

function resetGridFilterForms() {
    ['instance-accounts-filter-form', 'instance-databases-filter-form'].forEach((formId) => {
        const form = document.getElementById(formId);
        if (form instanceof HTMLFormElement) {
            form.reset();
        }
    });
}

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
    if (!instanceStore?.actions?.syncInstanceAccounts) {
        toast.error('InstanceStore 未初始化');
        return;
    }
    if (!isInstanceSyncAvailable()) {
        toast.warning?.('实例已停用，无法同步账户');
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
    instanceStore.actions.syncInstanceAccounts(getInstanceId(), syncOptions)
        .then(data => {
            const resolver = window.UI?.resolveAsyncActionOutcome;
            const outcome = typeof resolver === 'function'
                ? resolver(data, {
                    action: 'instances:syncAccounts',
                    startedMessage: '账户同步任务已启动',
                    failedMessage: '账户同步失败',
                    unknownMessage: '账户同步未完成，请稍后在会话中心确认',
                    resultUrl: '/history/sessions',
                    resultText: '前往会话中心查看同步进度',
                })
                : null;

            const fallbackStatus = data?.success === true ? 'started' : data?.success === false || data?.error === true ? 'failed' : 'unknown';
            const fallbackOutcome = {
                status: fallbackStatus,
                tone: fallbackStatus === 'started' ? 'success' : fallbackStatus === 'failed' ? 'error' : 'warning',
                message: fallbackStatus === 'started'
                    ? (data?.message || '账户同步任务已启动')
                    : fallbackStatus === 'failed'
                        ? (data?.message || '账户同步失败')
                        : (data?.message || '账户同步未完成，请稍后在会话中心确认'),
            };
            const resolved = outcome || fallbackOutcome;

            const warnOrInfo = toast?.warning || toast?.info || console.info;
            const notifier = resolved.tone === 'success'
                ? toast?.success
                : resolved.tone === 'error'
                    ? toast?.error
                    : warnOrInfo;

            if (resolved.status === 'started') {
                console.info('同步账户成功', {
                    operation: 'sync_accounts',
                    instance_id: getInstanceId(),
                    instance_name: getInstanceName(),
                    result: 'success',
                    message: resolved.message
                });
                notifier?.call(toast, resolved.message || '账户同步任务已启动');
            } else if (resolved.status === 'failed') {
                console.error('同步账户失败(业务失败)', {
                    operation: 'sync_accounts',
                    instance_id: getInstanceId(),
                    instance_name: getInstanceName(),
                    result: 'failed',
                    response: data
                });
                notifier?.call(toast, resolved.message || '账户同步失败');
            } else {
                console.warn('同步账户返回结构未知', {
                    operation: 'sync_accounts',
                    instance_id: getInstanceId(),
                    instance_name: getInstanceName(),
                    result: 'unknown',
                    response: data
                });
                notifier?.call(toast, resolved.message || '账户同步未完成，请稍后在会话中心确认');
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
    if (!ensureInstanceCrudStore()) {
        window.toast?.error?.('实例状态未就绪');
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
    instanceCrudStore.actions
        .deleteInstance(instanceId)
        .then((resp) => {
            window.toast?.success?.(resp?.message || '实例已移入回收站');
            window.location.href = '/instances';
        })
        .catch((error) => {
            console.error('移入回收站失败', error);
            window.toast?.error?.(resolveErrorMessage(error, '移入回收站失败'));
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
    if (!instanceStore?.actions?.syncInstanceCapacity) {
        toast.error('InstanceStore 未初始化');
        return;
    }
    if (!isInstanceSyncAvailable()) {
        toast.warning?.('实例已停用，无法同步容量');
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

    instanceStore.actions.syncInstanceCapacity(instanceId)
        .then(data => {
            const resolver = window.UI?.resolveAsyncActionOutcome;
            const outcome = typeof resolver === 'function'
                ? resolver(data, {
                    action: 'instances:syncCapacity',
                    startedMessage: '容量同步任务已启动',
                    failedMessage: '容量同步失败',
                    unknownMessage: '容量同步未完成，请稍后在会话中心确认',
                    resultUrl: '/history/sessions',
                    resultText: '前往会话中心查看同步进度',
                })
                : null;

            const fallbackStatus = data?.success === true ? 'started' : data?.success === false || data?.error === true ? 'failed' : 'unknown';
            const fallbackOutcome = {
                status: fallbackStatus,
                tone: fallbackStatus === 'started' ? 'success' : fallbackStatus === 'failed' ? 'error' : 'warning',
                message: fallbackStatus === 'started'
                    ? (data?.message || '容量同步任务已启动')
                    : fallbackStatus === 'failed'
                        ? (data?.message || '容量同步失败')
                        : (data?.message || '容量同步未完成，请稍后在会话中心确认'),
            };
            const resolved = outcome || fallbackOutcome;

            const warnOrInfo = toast?.warning || toast?.info || console.info;
            const notifier = resolved.tone === 'success'
                ? toast?.success
                : resolved.tone === 'error'
                    ? toast?.error
                    : warnOrInfo;

            notifier?.call(toast, resolved.message);

            if (resolved.status === 'started') {
                console.info('同步容量成功', {
                    operation: 'sync_capacity',
                    instance_id: instanceId,
                    instance_name: instanceName,
                    result: 'success',
                    message: resolved.message
                });

                // 刷新数据库容量显示(异步任务场景下可能有延迟)
                setTimeout(() => {
                    loadDatabaseSizes();
                }, 1000);
            } else if (resolved.status === 'failed') {
                console.error('同步容量失败(业务失败)', {
                    operation: 'sync_capacity',
                    instance_id: instanceId,
                    instance_name: instanceName,
                    result: 'failed',
                    response: data
                });
            } else {
                console.warn('同步容量返回结构未知', {
                    operation: 'sync_capacity',
                    instance_id: instanceId,
                    instance_name: instanceName,
                    result: 'unknown',
                    response: data,
                });
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

function syncAuditInfo(event) {
    if (!instanceStore?.actions?.syncInstanceAuditInfo) {
        toast.error('InstanceStore 未初始化');
        return;
    }
    const dbType = String(getInstanceDbType() || '').toLowerCase();
    if (dbType !== 'sqlserver') {
        toast.warning?.('当前仅支持 SQL Server 审计信息采集');
        return;
    }
    if (!isInstanceSyncAvailable()) {
        toast.warning?.('实例已停用，无法同步审计信息');
        return;
    }

    const fallbackBtn = selectOne('[data-action="sync-audit-info"]').first();
    const syncBtn = event?.currentTarget || event?.target || fallbackBtn;
    if (!syncBtn) {
        return;
    }
    const buttonWrapper = from(syncBtn);
    const originalText = buttonWrapper.html();

    buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>同步中...');
    buttonWrapper.attr('disabled', 'disabled');

    instanceStore.actions.syncInstanceAuditInfo(getInstanceId())
        .then((response) => {
            const payload = response?.data || response || {};
            const summary = payload.summary || {};
            const auditCount = Number(summary.audit_count) || 0;
            toast.success(`审计信息同步成功，已刷新 ${auditCount} 个审计目标`);
            showAuditTab();
            loadAuditInfo(true);
        })
        .catch((error) => {
            toast.error('同步审计信息失败: ' + (error?.message || '未知错误'));
        })
        .finally(() => {
            buttonWrapper.html(originalText || '同步审计');
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
    const viewer = window.PermissionViewer?.viewAccountPermissions;
    if (typeof viewer !== 'function') {
        console.error('PermissionViewer 未注册');
        return;
    }
    viewer(accountId, { scope: 'instance-permission' });
}

/**
 * 初始化账户列表 Grid.js。
 *
 * @returns {void}
 */
function initializeAccountsGrid() {
    const pageRoot = document.getElementById('instanceDetailContainer');
    if (!pageRoot) {
        return;
    }
    const container = pageRoot.querySelector('#instance-accounts-grid');
    if (!container) {
        return;
    }

    const GridPage = window.Views?.GridPage;
    const GridPlugins = window.Views?.GridPlugins;
    if (!GridPage?.mount || !GridPlugins?.filterCard || !GridPlugins?.actionDelegation) {
        console.warn('Views.GridPage 或 GridPlugins 未加载，跳过账户列表初始化');
        return;
    }

    if (!gridHtml) {
        console.warn('gridjs.html 未加载，账户列表将回退为纯文本渲染');
    }

    // 避免重复 mount 导致出现多个 grid。
    if (accountsGridController?.destroy) {
        try {
            accountsGridController.destroy();
        } catch (error) {
            console.warn('销毁旧账户列表 grid 失败:', error);
        }
    }
    accountsGridController = null;
    accountsGrid = null;
    container.innerHTML = '';

    const controller = GridPage.mount({
        root: pageRoot,
        grid: '#instance-accounts-grid',
        filterForm: '#instance-accounts-filter-form',
        gridOptions: {
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
        },
        filters: {
            allowedKeys: ['include_deleted', 'search'],
            normalize: normalizeAccountsFilters,
        },
        plugins: [
            GridPlugins.filterCard({
                autoSubmitOnChange: true,
                autoSubmitDebounce: 250,
            }),
            GridPlugins.actionDelegation({
                actions: {
                    'view-permissions': ({ event, el }) => {
                        event.preventDefault();
                        const accountId = el.getAttribute('data-account-id');
                        if (accountId) {
                            viewInstanceAccountPermissions(accountId);
                        }
                    },
                    'view-history': ({ event, el }) => {
                        event.preventDefault();
                        const accountId = el.getAttribute('data-account-id');
                        if (accountId) {
                            viewAccountChangeHistory(accountId);
                        }
                    },
                },
            }),
        ],
    });

    accountsGridController = controller || null;
    accountsGrid = controller?.gridWrapper || null;
}

function buildAccountsBaseUrl() {
    return `/api/v1/accounts/ledgers?instance_id=${getInstanceId()}&sort=username&order=asc&include_roles=true`;
}

function handleAccountsServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || [];
    return items.map((item) => ([
        item.id || null,
        item.username || '-',
        item.type_specific?.plugin || '',
        item.type_specific?.account_kind || '',
        item.is_locked,
        item.is_superuser,
        item.is_deleted,
        item.last_change_time || '',
        null,
        item,
    ]));
}

function normalizeAccountsFilters(filters) {
    const source = filters && typeof filters === 'object' ? filters : {};
    const normalized = {};

    const rawInclude = source.include_deleted;
    const includeValues = Array.isArray(rawInclude) ? rawInclude : [rawInclude];
    const includeDeleted = includeValues.some((value) => {
        if (value === undefined || value === null) {
            return false;
        }
        const text = String(value).toLowerCase();
        return text === 'true' || text === 'on';
    });
    normalized.include_deleted = includeDeleted ? 'true' : 'false';

    const rawSearch = Array.isArray(source.search) ? source.search[0] : source.search;
    const search = typeof rawSearch === 'string' ? rawSearch.trim() : '';
    if (search) {
        normalized.search = search;
    }

    return normalized;
}

function buildAccountsGridColumns() {
    const dbType = String(getInstanceDbType() || '').toLowerCase();
    const showMySQLFields = dbType === 'mysql';

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
            formatter: (cell, row) => renderAccountUsernameCell(cell, getRowMeta(row)),
        },
        {
            name: '插件',
            id: 'plugin',
            width: '220px',
            hidden: !showMySQLFields,
            formatter: (cell, row) => renderAccountPluginCell(cell, getRowMeta(row)),
        },
        {
            name: '类型',
            id: 'account_kind',
            width: '90px',
            hidden: !showMySQLFields,
            formatter: (cell, row) => renderAccountKindCell(cell, getRowMeta(row)),
        },
        {
            name: '锁定',
            id: 'is_locked',
            width: '70px',
            formatter: (cell, row) => renderAccountLockedCell(cell, getRowMeta(row)),
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
            formatter: (cell, row) => renderAccountActions(getRowMeta(row)),
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
    const subtitleParts = [];
    if (host && !username.includes('@')) {
        subtitleParts.push(`@${host}`);
    }
    const subtitle = subtitleParts.length ? `<div class="text-muted small">${escapeHtml(subtitleParts.join(' · '))}</div>` : '';
    return gridHtml(`
        <div class="d-flex flex-column">
            <div class="fw-semibold">${escapeHtml(username)}</div>
            ${subtitle}
        </div>
    `);
}

function renderAccountPluginCell(value, meta) {
    const typeSpecific = meta?.type_specific || {};
    const rawPlugin = value || typeSpecific?.plugin;
    const plugin = rawPlugin ? String(rawPlugin).toUpperCase() : '';
    if (!plugin) {
        return gridHtml ? gridHtml('<span class="text-muted">-</span>') : '-';
    }
    return gridHtml ? gridHtml(`<span class="chip-outline chip-outline--muted">${escapeHtml(plugin)}</span>`) : plugin;
}

function renderAccountKindCell(value, meta) {
    const typeSpecific = meta?.type_specific || {};
    const rawKind = value || typeSpecific?.account_kind;
    const kind = typeof rawKind === 'string' ? rawKind.toLowerCase() : '';
    if (kind !== 'user' && kind !== 'role') {
        return gridHtml ? gridHtml('<span class="text-muted">-</span>') : '-';
    }
    const cls = kind === 'role' ? 'status-pill status-pill--info' : 'status-pill status-pill--muted';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(kind)}</span>`) : kind;
}

function renderAccountLockedCell(isLocked, meta) {
    const typeSpecific = meta?.type_specific || {};
    const accountKind = typeSpecific?.account_kind ? String(typeSpecific.account_kind).toLowerCase() : null;
    if (accountKind === 'role') {
        return gridHtml ? gridHtml('<span class="text-muted">-</span>') : '-';
    }
    return renderAccountLockedBadge(Boolean(isLocked));
}

function renderAccountLockedBadge(isLocked) {
    const resolveText = window.UI?.Terms?.resolveLockStatusText;
    const label = typeof resolveText === 'function' ? resolveText(isLocked) : (isLocked ? '已锁定' : '正常');
    const cls = isLocked ? 'status-pill status-pill--danger' : 'status-pill status-pill--success';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(label)}</span>`) : label;
}

function renderAccountSuperuserBadge(isSuperuser) {
    const label = isSuperuser ? '是' : '否';
    const cls = isSuperuser ? 'status-pill status-pill--warning' : 'status-pill status-pill--muted';
    return gridHtml ? gridHtml(`<span class="${cls}">${escapeHtml(label)}</span>`) : label;
}

function renderAccountDeletedBadge(isDeleted) {
    const resolveText = window.UI?.Terms?.resolveDeletionStatusText;
    const label = typeof resolveText === 'function' ? resolveText(isDeleted) : (isDeleted ? '已删除' : '正常');
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
    const node = selectOne('#accountTotalCount');
    if (!node.length) {
        return;
    }
    const count = Number(total) || 0;
    node.text(String(count));
}

/**
 * 初始化数据库容量列表 Grid.js。
 *
 * @returns {void}
 */
function initializeDatabaseSizesGrid() {
    const pageRoot = document.getElementById('instanceDetailContainer');
    if (!pageRoot) {
        return;
    }
    const container = pageRoot.querySelector('#instance-databases-grid');
    if (!container) {
        return;
    }

    const GridPage = window.Views?.GridPage;
    const GridPlugins = window.Views?.GridPlugins;
    if (!GridPage?.mount || !GridPlugins?.filterCard) {
        console.warn('Views.GridPage 或 GridPlugins 未加载，跳过数据库容量列表初始化');
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
        next = wrapper.appendParam(next, `page=${page + 1}`);
        return next;
    };

    const controller = GridPage.mount({
        root: pageRoot,
        grid: '#instance-databases-grid',
        filterForm: '#instance-databases-filter-form',
        gridOptions: {
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
        },
        filters: {
            allowedKeys: ['latest_only', 'include_inactive', 'database_name'],
            normalize: normalizeDatabaseSizesFilters,
        },
        plugins: [
            {
                name: 'databaseSizesPaginationBinding',
                init: (ctx) => {
                    wrapper = ctx.gridWrapper;
                },
            },
            GridPlugins.filterCard({
                autoSubmitOnChange: true,
                autoSubmitDebounce: 250,
            }),
        ],
    });

    databaseSizesGrid = controller?.gridWrapper || null;
    wrapper = databaseSizesGrid;
}

function buildDatabaseSizesBaseUrl() {
    return `/api/v1/databases/sizes?instance_id=${getInstanceId()}`;
}

function handleDatabaseSizesServerResponse(response) {
    const payload = response?.data || response || {};
    const databases = Array.isArray(payload.databases) ? payload.databases : [];
    return databases.map((entry) => ([
        entry.database_name || '-',
        entry.size_mb,
        entry.is_active,
        entry.collected_at,
        null,
        entry,
    ]));
}

function normalizeDatabaseSizesFilters(filters) {
    const source = filters && typeof filters === 'object' ? filters : {};
    const normalized = {
        latest_only: 'true',
    };

    const rawInclude = source.include_inactive;
    const includeValues = Array.isArray(rawInclude) ? rawInclude : [rawInclude];
    const includeInactive = includeValues.some((value) => {
        if (value === undefined || value === null) {
            return false;
        }
        const text = String(value).toLowerCase();
        return text === 'true' || text === 'on';
    });
    normalized.include_inactive = includeInactive ? 'true' : 'false';

    const rawSearch = Array.isArray(source.database_name) ? source.database_name[0] : source.database_name;
    const search = typeof rawSearch === 'string' ? rawSearch.trim() : '';
    if (search) {
        normalized.database_name = search;
    }

    return normalized;
}

function buildDatabaseSizesGridColumns() {
    return [
        {
            name: '数据库',
            id: 'database_name',
            formatter: (cell, row) => renderDatabaseNameCell(cell, getRowMeta(row)),
        },
        {
            name: '总大小',
            id: 'size_mb',
            width: '140px',
            formatter: (cell, row) => renderDatabaseSizeCell(cell, getRowMeta(row)),
        },
        {
            name: '状态',
            id: 'is_active',
            width: '220px',
            formatter: (cell, row) => renderDatabaseStatusCell(Boolean(cell !== false), getRowMeta(row)),
        },
        {
            name: '采集时间',
            id: 'collected_at',
            width: '200px',
            formatter: (cell) => renderDatabaseCollectedAtCell(cell),
        },
        {
            name: '操作',
            id: 'actions',
            width: '140px',
            formatter: (_cell, row) => renderDatabaseActionsCell(getRowMeta(row)),
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

function renderDatabaseActionsCell(meta) {
    if (!gridHtml) {
        return '-';
    }
    const databaseName = meta?.database_name ? String(meta.database_name) : '';
    const databaseId = meta?.id !== undefined && meta?.id !== null ? String(meta.id) : '';
    if (!databaseName) {
        return gridHtml('<span class="text-muted">-</span>');
    }
    const isActive = meta?.is_active !== false;
    const buttonClass = isActive ? 'btn-outline-primary' : 'btn-outline-secondary';
    return gridHtml(`
        <button type="button" class="btn btn-sm ${buttonClass}" data-action="open-table-sizes" data-database-id="${escapeHtml(databaseId)}" data-database-name="${escapeHtml(databaseName)}">
            <i class="fas fa-table me-1"></i>表容量
        </button>
    `);
}

function updateDatabaseCount(total) {
    const node = selectOne('#databaseTotalCount');
    if (!node.length) {
        return;
    }
    const count = Number(total) || 0;
    node.text(String(count));
}

function openDatabaseTableSizesModal(actionEvent) {
    const actionEl = actionEvent?.currentTarget;
    const databaseId = actionEl?.getAttribute?.('data-database-id') || actionEl?.dataset?.databaseId;
    const databaseName = actionEl?.getAttribute?.('data-database-name') || actionEl?.dataset?.databaseName;
    if (!databaseId) {
        toast.error('缺少数据库ID');
        return;
    }

    const modal = ensureTableSizesModal();
    if (!modal?.open) {
        toast.error('表容量模态未初始化');
        return;
    }

    modal.open(databaseId, databaseName);
}

function loadDatabaseSizesSummary() {
    if (!instanceStore?.actions?.fetchDatabaseSizes) {
        return;
    }
    const instanceId = getInstanceId();
    instanceStore.actions.fetchDatabaseSizes(instanceId, {
        latest_only: true,
        include_inactive: true,
        limit: 1,
        page: 1,
    })
        .then((resp) => {
            const payload = resp?.data || resp || {};
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
    const normalized = (rawType || '').toString().trim().toLowerCase();
    switch (normalized) {
        case 'add':
            return { label: '新增', variant: 'status-pill--success' };
        case 'modify_privilege':
            return { label: '权限变更', variant: 'status-pill--info' };
        case 'modify_other':
            return { label: '属性变更', variant: 'status-pill--info' };
        case 'delete':
        case 'remove':
            return { label: '删除', variant: 'status-pill--danger' };
        default:
            return { label: rawType || '变更', variant: 'status-pill--muted' };
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
    if (!instanceStore?.actions?.fetchAccountChangeHistory) {
        toast.error('InstanceStore 未初始化');
        return;
    }
    const historyContentWrapper = selectOne('#historyContent');
    if (historyContentWrapper.length) {
        const loading = window.ChangeHistoryRenderer?.renderHistoryLoading;
        historyContentWrapper.html(typeof loading === 'function' ? loading() : renderHistoryLoading());
    }
    const modalMeta = selectOne('#historyModalMeta');
    if (modalMeta.length) {
        modalMeta.text(`账户 #${accountId} · 加载中`);
    }
    instanceStore.actions.fetchAccountChangeHistory(accountId)
        .then((resp) => {
            const payload = resp?.data || resp || {};
            const history = Array.isArray(payload?.history) ? payload.history : [];

            if (!historyContentWrapper.length) {
                console.error('未找到历史记录模态框元素');
                return;
            }
            if (modalMeta.length) {
                modalMeta.text(formatHistoryMeta(payload?.account, `账户 #${accountId}`));
            }

            const openAllLink = document.getElementById('historyModalOpenAll');
            if (openAllLink && payload?.account && typeof payload.account === 'object') {
                const baseHref = openAllLink.getAttribute('href') || '/history/account-change-logs/';
                const params = new URLSearchParams();
                const instanceId = getInstanceId();
                if (instanceId) {
                    params.set('instance_id', String(instanceId));
                }
                if (payload.account.username) {
                    params.set('search', payload.account.username);
                }
                if (payload.account.db_type) {
                    params.set('db_type', payload.account.db_type);
                }
                const query = params.toString();
                openAllLink.setAttribute('href', query ? `${baseHref}?${query}` : baseHref);
            }

            if (history.length > 0) {
                const renderer = window.ChangeHistoryRenderer?.renderChangeHistoryCard;
                const cards = history
                    .map((change, index) =>
                        typeof renderer === 'function'
                            ? renderer(change, { collapsible: true, open: index === 0 })
                            : renderChangeHistoryCard(change),
                    )
                    .join('');
                historyContentWrapper.html(cards);
            } else {
                historyContentWrapper.html(`
                    <div class="change-history-modal__empty">
                        <span class="status-pill status-pill--muted">暂无变更记录</span>
                    </div>
                `);
            }

            ensureHistoryModal().open();
        })
        .catch((error) => {
            console.error('获取变更历史失败:', error?.message || error);
            const message = error?.message || '获取变更历史失败';
            toast.error(message);
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
        return;
    }

    const accountRows = select('.account-row');
    const accountTotal = selectOne('#accountTotalCount');
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

    if (accountTotal.length) {
        accountTotal.text(String(visibleCount));
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

function getInstanceDbType() {
    const datasetType = getInstanceDatasetValue('dbType');
    if (datasetType) {
        return datasetType;
    }
    const badge = selectOne('.chip-outline--brand');
    if (badge.length) {
        return (badge.text() || '').trim();
    }
    return '';
}

function getSyncAccountsUrl() {
    return getInstanceDatasetValue('syncAccountsUrl');
}

function isInstanceSyncAvailable() {
    const datasetValue = getInstanceDatasetValue('instanceActive');
    return datasetValue !== 'false';
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
        case 'dbType':
            return root.dataset?.dbType || root.getAttribute('data-db-type') || null;
        case 'instanceActive':
            return root.dataset?.instanceActive || root.getAttribute('data-instance-active') || null;
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

function showAuditTab() {
    const auditTab = document.getElementById('audit-tab');
    const bootstrapTab = window.bootstrap?.Tab;
    if (!auditTab || !bootstrapTab?.getOrCreateInstance) {
        return;
    }
    bootstrapTab.getOrCreateInstance(auditTab).show();
}

function loadAuditInfo(forceRefresh = false) {
    if (!instanceStore?.actions?.fetchInstanceAuditInfo) {
        toast.error('InstanceStore 未初始化');
        return;
    }
    if (auditInfoState.loading) {
        return;
    }
    if (auditInfoState.loaded && !forceRefresh) {
        renderAuditInfo(auditInfoState.payload);
        return;
    }

    auditInfoState.loading = true;
    renderAuditLoading();

    instanceStore.actions.fetchInstanceAuditInfo(getInstanceId())
        .then((response) => {
            auditInfoState.payload = response?.data || response || null;
            auditInfoState.loaded = true;
            renderAuditInfo(auditInfoState.payload);
        })
        .catch((error) => {
            renderAuditError(error?.message || '加载审计信息失败');
        })
        .finally(() => {
            auditInfoState.loading = false;
        });
}

function renderAuditLoading() {
    const contentDiv = selectOne('#auditInfoContent');
    if (!contentDiv.length) {
        return;
    }
    contentDiv.html(`
        <div class="text-center py-4">
            <i class="fas fa-spinner fa-spin fa-2x text-muted mb-3"></i>
            <p class="text-muted mb-0">正在加载审计信息...</p>
        </div>
    `);
}

function renderAuditError(message) {
    const contentDiv = selectOne('#auditInfoContent');
    if (!contentDiv.length) {
        return;
    }
    contentDiv.html(`
        <section class="instance-audit-placeholder instance-audit-placeholder--muted">
            <div class="instance-audit-placeholder__icon">
                <i class="fas fa-triangle-exclamation"></i>
            </div>
            <div class="instance-audit-placeholder__content">
                <span class="chip-outline chip-outline--muted">错误</span>
                <h3 class="instance-audit-placeholder__title">审计信息加载失败</h3>
                <p class="instance-audit-placeholder__text">${escapeHtml(message || '请稍后重试')}</p>
            </div>
        </section>
    `);
}

function renderAuditInfo(payload) {
    const contentDiv = selectOne('#auditInfoContent');
    if (!contentDiv.length) {
        return;
    }
    const data = payload && typeof payload === 'object' ? payload : {};
    const dbType = String(data.db_type || getInstanceDbType() || '').toLowerCase();
    if (data.supported === false) {
        contentDiv.html(renderUnsupportedAuditPlaceholder(dbType));
        return;
    }
    if (!data.available || !data.snapshot) {
        contentDiv.html(renderAuditEmptyState(data));
        return;
    }

    const snapshot = data.snapshot || {};
    const facts = data.facts || {};
    const serverAudits = Array.isArray(snapshot.server_audits) ? snapshot.server_audits : [];
    const serverSpecs = Array.isArray(snapshot.audit_specifications) ? snapshot.audit_specifications : [];
    const databaseSpecs = Array.isArray(snapshot.database_audit_specifications)
        ? snapshot.database_audit_specifications
        : [];
    const warnings = [
        ...(Array.isArray(facts.warnings) ? facts.warnings : []),
        ...(Array.isArray(snapshot.errors) ? snapshot.errors : []),
    ];
    const scope = auditInfoState.filters.scope || 'all';
    const search = (auditInfoState.filters.search || '').trim().toLowerCase();
    const includeDisabled = auditInfoState.filters.includeDisabled === true;

    const filteredAudits = serverAudits.filter((item) => matchAuditTarget(item, { search, includeDisabled }));
    const filteredServerSpecs = serverSpecs.filter((item) => matchAuditSpec(item, { search, includeDisabled }));
    const filteredDatabaseSpecs = databaseSpecs.filter((item) => matchAuditSpec(item, { search, includeDisabled }));

    const showAudits = scope === 'all' || scope === 'audit_targets';
    const showSpecs = scope === 'all' || scope === 'server_specs' || scope === 'database_specs';
    const visibleSpecs = scope === 'server_specs'
        ? filteredServerSpecs
        : scope === 'database_specs'
            ? filteredDatabaseSpecs
            : [...filteredServerSpecs, ...filteredDatabaseSpecs];

    contentDiv.html(`
        <section class="instance-overview-band instance-overview-band--audit">
            <div class="instance-overview-band__facts">
                <article class="instance-overview-band__fact" data-tone="brand">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">审计目标数</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true"><i class="fas fa-shield-halved"></i></span>
                    </div>
                    <strong class="instance-overview-band__fact-value">${escapeHtml(String(Number(facts.audit_count) || 0))}</strong>
                    <span class="status-pill status-pill--muted"><i class="fas fa-layer-group me-1"></i>catalog</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="success">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">已启用审计</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true"><i class="fas fa-toggle-on"></i></span>
                    </div>
                    <strong class="instance-overview-band__fact-value">${escapeHtml(String(Number(facts.enabled_audit_count) || 0))}</strong>
                    <span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>启用</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="info">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">规范总数</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true"><i class="fas fa-list-check"></i></span>
                    </div>
                    <strong class="instance-overview-band__fact-value">${escapeHtml(String(Number(facts.specification_count) || 0))}</strong>
                    <span class="status-pill status-pill--info"><i class="fas fa-list me-1"></i>规范</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="danger">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">覆盖数据库数</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true"><i class="fas fa-database"></i></span>
                    </div>
                    <strong class="instance-overview-band__fact-value">${escapeHtml(String(Number(facts.covered_database_count) || 0))}</strong>
                    <span class="status-pill status-pill--danger"><i class="fas fa-database me-1"></i>数据库</span>
                </article>
            </div>
            <div class="instance-overview-band__controls">
                <form class="instance-overview-band__toolbar" action="#">
                    <div class="form-check form-switch mb-0 instance-overview-band__toggle">
                        <input class="form-check-input" type="checkbox" role="switch" id="showDisabledAudits" data-action="toggle-audit-disabled" ${includeDisabled ? 'checked' : ''}>
                        <label class="form-check-label" for="showDisabledAudits">
                            <i class="fas fa-eye me-1"></i>显示未启用项
                        </label>
                    </div>
                    <select class="form-select form-select-sm" data-action="filter-audit-scope" style="max-width: 13rem;">
                        <option value="all" ${scope === 'all' ? 'selected' : ''}>全部范围</option>
                        <option value="audit_targets" ${scope === 'audit_targets' ? 'selected' : ''}>仅审计目标</option>
                        <option value="server_specs" ${scope === 'server_specs' ? 'selected' : ''}>仅服务规范</option>
                        <option value="database_specs" ${scope === 'database_specs' ? 'selected' : ''}>仅数据库规范</option>
                    </select>
                    <div class="input-group input-group-sm instance-overview-band__search">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                        <input type="text" class="form-control" placeholder="搜索名称 / 数据库 / 目标" data-action="filter-audit-search" value="${escapeHtml(auditInfoState.filters.search || '')}" autocomplete="off">
                    </div>
                </form>
                <div class="instance-overview-band__realtime">
                    <span class="chip-outline chip-outline--muted"><i class="fas fa-clock me-1"></i>${escapeHtml(formatAuditSyncTime(data.last_sync_time))}</span>
                </div>
            </div>
        </section>
        ${renderAuditWarnings(warnings)}
        ${showAudits ? renderAuditTargetsSection(filteredAudits, serverAudits.length) : ''}
        ${showSpecs ? renderAuditSpecificationsSection(visibleSpecs, serverSpecs.length + databaseSpecs.length, scope) : ''}
    `);
}

function renderUnsupportedAuditPlaceholder(dbType) {
    const label = (dbType || 'unknown').toUpperCase();
    return `
        <section class="instance-audit-placeholder instance-audit-placeholder--muted">
            <div class="instance-audit-placeholder__icon">
                <i class="fas fa-circle-info"></i>
            </div>
            <div class="instance-audit-placeholder__content">
                <span class="chip-outline chip-outline--muted">${escapeHtml(label)}</span>
                <h3 class="instance-audit-placeholder__title">当前实例暂不支持审计采集</h3>
                <p class="instance-audit-placeholder__text">统一入口已经就位。首期仅支持 SQL Server，后续可以在同一标签下继续扩展其他数据库的审计与安全基线。</p>
            </div>
        </section>
    `;
}

function renderAuditEmptyState(data) {
    const dbType = String(data.db_type || getInstanceDbType() || '').toUpperCase();
    return `
        <section class="instance-audit-placeholder">
            <div class="instance-audit-placeholder__icon">
                <i class="fas fa-shield-halved"></i>
            </div>
            <div class="instance-audit-placeholder__content">
                <span class="chip-outline chip-outline--brand">${escapeHtml(dbType)}</span>
                <h3 class="instance-audit-placeholder__title">尚未采集审计信息</h3>
                <p class="instance-audit-placeholder__text">${escapeHtml(data.message || '点击“同步审计”后，此处会展示审计目标、审计规范和覆盖范围。')}</p>
            </div>
        </section>
    `;
}

function renderAuditWarnings(warnings) {
    if (!Array.isArray(warnings) || !warnings.length) {
        return '';
    }
    const items = warnings.map((warning) => `
        <div class="instance-audit-warning">
            <i class="fas fa-triangle-exclamation"></i>
            <div>${escapeHtml(formatAuditWarningMessage(warning))}</div>
        </div>
    `).join('');
    return `<div class="instance-audit-warning-list">${items}</div>`;
}

function formatAuditWarningMessage(warning) {
    if (warning && typeof warning === 'object') {
        const databaseName = warning.database_name || warning.databaseName;
        const reason = warning.reason || warning.error_code || 'DATABASE_QUERY_FAILED';
        if (databaseName) {
            return `数据库 ${databaseName} 审计配置读取失败（${reason}）`;
        }
        if (warning.error_message || warning.errorMessage) {
            return String(warning.error_message || warning.errorMessage);
        }
    }
    if (typeof warning === 'string' && warning.startsWith('DATABASE_AUDIT_SPECIFICATIONS_PARTIAL:')) {
        const suffix = warning.split(':').slice(1).join(':');
        return `部分数据库审计配置未读取成功：${suffix}`;
    }
    return String(warning);
}

function renderAuditTargetsSection(audits, totalCount) {
    const rows = Array.isArray(audits) ? audits : [];
    const body = rows.length
        ? rows.map((audit) => `
            <tr>
                <td>
                    <div class="instance-audit-name-cell">
                        <strong>${escapeHtml(String(audit.name || '-'))}</strong>
                    </div>
                </td>
                <td>${renderAuditStatusPill(audit.enabled)}</td>
                <td>${escapeHtml(String(audit.target_type || '-'))}</td>
                <td>
                    <div class="instance-audit-name-cell">
                        <strong>${escapeHtml(String(audit.target_summary || audit.file_path || audit.target_type || '-'))}</strong>
                        <span class="instance-audit-subtle">Queue delay: ${escapeHtml(formatAuditQueueDelay(audit.queue_delay))}</span>
                    </div>
                </td>
                <td>${escapeHtml(String(audit.on_failure || '-'))}</td>
                <td>${escapeHtml(formatAuditTimestamp(audit.updated_at || audit.created_at))}</td>
            </tr>
        `).join('')
        : `<tr><td colspan="6"><div class="instance-audit-empty">当前筛选条件下没有审计目标</div></td></tr>`;
    return `
        <section class="instance-audit-section">
            <header class="instance-audit-section__header">
                <h3 class="instance-audit-section__title"><i class="fas fa-shield-halved"></i>审计目标</h3>
                <span class="instance-audit-section__meta">显示 ${escapeHtml(String(rows.length))} / ${escapeHtml(String(totalCount || 0))}</span>
            </header>
            <div class="table-responsive">
                <table class="table table-hover instance-audit-table">
                    <thead>
                        <tr>
                            <th>名称</th>
                            <th>状态</th>
                            <th>目标类型</th>
                            <th>目标摘要</th>
                            <th>失败策略</th>
                            <th>更新时间</th>
                        </tr>
                    </thead>
                    <tbody>${body}</tbody>
                </table>
            </div>
        </section>
    `;
}

function renderAuditSpecificationsSection(specifications, totalCount, scope) {
    const rows = Array.isArray(specifications) ? specifications : [];
    const title = scope === 'server_specs'
        ? '服务审计规范'
        : scope === 'database_specs'
            ? '数据库审计规范'
            : '审计规范';
    const body = rows.length
        ? rows.map((spec) => `
            <tr>
                <td>${renderAuditScopePill(spec.scope)}</td>
                <td>
                    <div class="instance-audit-name-cell">
                        <strong>${escapeHtml(String(spec.name || '-'))}</strong>
                        <span class="instance-audit-subtle">${escapeHtml(String(spec.database_name || '实例级'))}</span>
                    </div>
                </td>
                <td>${escapeHtml(String(spec.audit_name || '-'))}</td>
                <td>${renderAuditStatusPill(spec.enabled)}</td>
                <td>${escapeHtml(String(Number(spec.action_count) || 0))}</td>
                <td>${renderAuditActionList(spec.actions)}</td>
            </tr>
        `).join('')
        : `<tr><td colspan="6"><div class="instance-audit-empty">当前筛选条件下没有审计规范</div></td></tr>`;
    return `
        <section class="instance-audit-section">
            <header class="instance-audit-section__header">
                <h3 class="instance-audit-section__title"><i class="fas fa-list-check"></i>${escapeHtml(title)}</h3>
                <span class="instance-audit-section__meta">显示 ${escapeHtml(String(rows.length))} / ${escapeHtml(String(totalCount || 0))}</span>
            </header>
            <div class="table-responsive">
                <table class="table table-hover instance-audit-table">
                    <thead>
                        <tr>
                            <th>范围</th>
                            <th>名称</th>
                            <th>绑定审计</th>
                            <th>状态</th>
                            <th>动作数</th>
                            <th>动作预览</th>
                        </tr>
                    </thead>
                    <tbody>${body}</tbody>
                </table>
            </div>
        </section>
    `;
}

function matchAuditTarget(item, options) {
    const entry = item && typeof item === 'object' ? item : {};
    const search = options?.search || '';
    if (!options?.includeDisabled && entry.enabled !== true) {
        return false;
    }
    if (!search) {
        return true;
    }
    const haystack = [
        entry.name,
        entry.target_type,
        entry.target_summary,
        entry.file_path,
        entry.on_failure,
    ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
    return haystack.includes(search);
}

function matchAuditSpec(item, options) {
    const entry = item && typeof item === 'object' ? item : {};
    const search = options?.search || '';
    if (!options?.includeDisabled && entry.enabled !== true) {
        return false;
    }
    if (!search) {
        return true;
    }
    const actionPreview = renderAuditActionSearchText(entry.actions);
    const haystack = [
        entry.name,
        entry.audit_name,
        entry.database_name,
        entry.scope,
        actionPreview,
    ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
    return haystack.includes(search);
}

function renderAuditStatusPill(enabled) {
    return enabled
        ? '<span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>启用</span>'
        : '<span class="status-pill status-pill--muted"><i class="fas fa-pause me-1"></i>未启用</span>';
}

function renderAuditScopePill(scope) {
    if (String(scope || '').toLowerCase() === 'database') {
        return '<span class="chip-outline chip-outline--info">DATABASE</span>';
    }
    return '<span class="chip-outline chip-outline--brand">SERVER</span>';
}

function renderAuditActionSearchText(actions) {
    const list = Array.isArray(actions) ? actions : [];
    return list
        .map((action) => resolveAuditActionDisplayText(action))
        .filter(Boolean)
        .join(' ');
}

function renderAuditActionList(actions) {
    const list = Array.isArray(actions) ? actions : [];
    const labels = list
        .map((action) => resolveAuditActionDisplayText(action))
        .filter(Boolean);
    if (!labels.length) {
        return '<span class="text-muted">无动作</span>';
    }
    const items = labels
        .map((value) => `<div class="instance-audit-action-list__item">${escapeHtml(String(value))}</div>`)
        .join('');
    return `<div class="instance-audit-action-list">${items}</div>`;
}

function resolveAuditActionDisplayText(action) {
    if (action && typeof action === 'object') {
        const displayText = action.display_text || action.displayText;
        if (displayText) {
            return String(displayText);
        }
        if (action.name) {
            return String(action.name);
        }
        return '';
    }
    if (action === undefined || action === null) {
        return '';
    }
    return String(action);
}

function formatAuditTimestamp(value) {
    if (!value) {
        return '未记录';
    }
    return timeUtils.formatDateTime(value);
}

function formatAuditQueueDelay(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return '未配置';
    }
    return `${numeric} ms`;
}

function formatAuditSyncTime(value) {
    if (!value) {
        return '未同步';
    }
    return `最近同步 ${timeUtils.formatDateTime(value)}`;
}

/**
 * 加载数据库容量数据。
 *
 * @return {void}
 */
function loadDatabaseSizes() {
    if (!instanceStore?.actions?.fetchDatabaseSizes) {
        toast.error('InstanceStore 未初始化');
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

    instanceStore.actions.fetchDatabaseSizes(instanceId, {
        latest_only: true,
        include_inactive: true
    })
        .then((resp) => {
            const payload = resp?.data || resp || {};

            if (payload && Array.isArray(payload.databases)) {
                displayDatabaseSizes(payload);
            } else {
                const errorMsg = resp?.error || resp?.message || '加载失败';
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
    const currentCount = Number(payload?.total ?? databases.length) || 0;

    const filteredCount = Number(payload?.filtered_count ?? 0) || 0;
    const activeCount = Number(payload?.active_count ?? (databases.length - filteredCount));

    const deletedCount = filteredCount || databases.filter(db => db.is_active === false).length;
    const onlineCount = activeCount;

    let html = `
        <section class="instance-overview-band instance-overview-band--capacity">
            <div class="instance-overview-band__facts">
                <article class="instance-overview-band__fact" data-tone="brand">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">当前数据库</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true">
                            <i class="fas fa-database"></i>
                        </span>
                    </div>
                    <strong class="instance-overview-band__fact-value" id="databaseTotalCount">${currentCount}</strong>
                    <span class="status-pill status-pill--muted"><i class="fas fa-layer-group me-1"></i>当前结果</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="success">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">在线数据库</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true">
                            <i class="fas fa-check-circle"></i>
                        </span>
                    </div>
                    <strong class="instance-overview-band__fact-value" id="databaseOnlineCount">${onlineCount}</strong>
                    <span class="status-pill status-pill--success"><i class="fas fa-check me-1"></i>在线</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="danger">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">已删除数据库</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true">
                            <i class="fas fa-trash"></i>
                        </span>
                    </div>
                    <strong class="instance-overview-band__fact-value" id="databaseDeletedCount">${deletedCount}</strong>
                    <span class="status-pill status-pill--danger"><i class="fas fa-trash me-1"></i>已删除</span>
                </article>
                <article class="instance-overview-band__fact" data-tone="info">
                    <div class="instance-overview-band__fact-header">
                        <span class="instance-overview-band__fact-label">总容量</span>
                        <span class="instance-overview-band__fact-icon" aria-hidden="true">
                            <i class="fas fa-hdd"></i>
                        </span>
                    </div>
                    <strong class="instance-overview-band__fact-value" id="databaseTotalCapacity">${totalSizeLabel}</strong>
                    <span class="status-pill status-pill--info"><i class="fas fa-hdd me-1"></i>容量</span>
                </article>
            </div>

            <div class="instance-overview-band__controls">
                <form class="instance-overview-band__toolbar" action="#">
                    <div class="form-check form-switch mb-0 instance-overview-band__toggle">
                        <input class="form-check-input" type="checkbox" id="showDeletedDatabases" data-action="toggle-deleted-databases">
                        <label class="form-check-label" for="showDeletedDatabases">
                            <i class="fas fa-eye me-1"></i>显示已删除数据库
                        </label>
                    </div>
                </form>
                <div class="instance-overview-band__realtime">
                    <span class="chip-outline chip-outline--muted"><i class="fas fa-info-circle me-1"></i>实时</span>
                </div>
            </div>
        </section>

        <div class="table-responsive mt-3">
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
            case 'sync-audit-info':
                event.preventDefault();
                syncAuditInfo(actionEvent);
                break;
            case 'edit-instance':
                event.preventDefault();
                openEditInstance(actionEvent);
                break;
            case 'delete-instance':
                event.preventDefault();
                confirmDeleteInstance(actionEvent);
                break;
            case 'retry-load-database-sizes':
                event.preventDefault();
                loadDatabaseSizes();
                break;
            case 'open-table-sizes':
                event.preventDefault();
                openDatabaseTableSizesModal(actionEvent);
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
            case 'toggle-audit-disabled':
                auditInfoState.filters.includeDisabled = Boolean(actionEl.checked);
                renderAuditInfo(auditInfoState.payload);
                break;
            case 'filter-audit-scope':
                auditInfoState.filters.scope = actionEl.value || 'all';
                renderAuditInfo(auditInfoState.payload);
                break;
            default:
                break;
        }
    });

    root.addEventListener('input', (event) => {
        const actionEl = event.target.closest('[data-action]');
        if (!actionEl) {
            return;
        }
        const action = actionEl.getAttribute('data-action');
        if (action === 'filter-audit-search') {
            auditInfoState.filters.search = actionEl.value || '';
            renderAuditInfo(auditInfoState.payload);
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
 * 初始化表容量模态框。
 *
 * @return {void}
 */
function initializeDatabaseTableSizesModal() {
    if (!document.getElementById('tableSizesModal')) {
        return;
    }
    const factory = window.InstanceDatabaseTableSizesModal?.createController;
    if (typeof factory !== 'function') {
        console.warn('InstanceDatabaseTableSizesModal 未加载，表容量模态不可用');
        return;
    }
    try {
        tableSizesModal = factory({
            ui: window.UI,
            toast,
            store: instanceStore,
        });
    } catch (error) {
        console.error('初始化表容量模态失败:', error);
        tableSizesModal = null;
    }
}

function ensureTableSizesModal() {
    if (!tableSizesModal) {
        initializeDatabaseTableSizesModal();
    }
    return tableSizesModal;
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
    const createInstanceCrudStore = window.createInstanceCrudStore;
    if (typeof createInstanceCrudStore !== 'function') {
        console.error('createInstanceCrudStore 未加载，实例编辑不可用');
        return;
    }
    if (!InstanceService) {
        console.warn('InstanceService 未注册，实例编辑不可用');
        return;
    }
        try {
        if (!instanceCrudStore) {
            instanceCrudStore = createInstanceCrudStore({
                service: new InstanceService(),
                emitter: window.mitt ? window.mitt() : null,
            });
        }
            instanceModals = window.InstanceModals.createController({
                store: instanceCrudStore,
                FormValidator: window.FormValidator,
                ValidationRules: window.ValidationRules,
                toast: window.toast,
                DOMHelpers: window.DOMHelpers,
                onSaved: () => window.location.reload(),
        });
        instanceModals.init?.();
    } catch (error) {
        console.error('初始化实例模态失败:', error);
        instanceModals = null;
    }
}

function ensureInstanceCrudStore() {
    if (instanceCrudStore) {
        return true;
    }
    const createInstanceCrudStore = window.createInstanceCrudStore;
    if (typeof createInstanceCrudStore !== 'function') {
        console.warn('createInstanceCrudStore 未加载，无法执行实例删除');
        return false;
    }
    if (!InstanceService) {
        console.warn('InstanceService 未注册，无法创建 InstanceCrudStore');
        return false;
    }
    try {
        instanceCrudStore = createInstanceCrudStore({
            service: new InstanceService(),
            emitter: window.mitt ? window.mitt() : null,
        });
        return true;
    } catch (error) {
        console.error('初始化 InstanceCrudStore 失败:', error);
        instanceCrudStore = null;
        return false;
    }
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
