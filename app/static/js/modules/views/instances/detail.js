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

const LodashUtils = window.LodashUtils;
if (!LodashUtils) {
    throw new Error('LodashUtils 未初始化');
}

const DOMHelpers = window.DOMHelpers;
if (!DOMHelpers) {
    throw new Error('DOMHelpers 未初始化');
}

const { ready, selectOne, select, from } = DOMHelpers;

const InstanceManagementService = window.InstanceManagementService;
let instanceService = null;
try {
    if (InstanceManagementService) {
        instanceService = new InstanceManagementService(window.httpU);
    } else {
        throw new Error('InstanceManagementService 未加载');
    }
} catch (error) {
    console.error('初始化 InstanceManagementService 失败:', error);
}

let instanceStore = null;
let historyModal = null;

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
    initializeInstanceStore();
    initializeHistoryModal();
    const checkbox = selectOne('#showDeletedAccounts');
    if (checkbox.length) {
        const element = checkbox.first();
        element.checked = false;
        toggleDeletedAccounts();
    }
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
    const fallbackBtn = selectOne('button[onclick="testConnection()"]').first();
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

            const statusBadge = selectOne('#connectionStatus');
            const resultDiv = selectOne('#testResult');

            statusBadge.text('正常');
            statusBadge.attr('class', 'badge bg-success');

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

            const statusBadge = selectOne('#connectionStatus');
            const resultDiv = selectOne('#testResult');

            statusBadge.text('失败');
            statusBadge.attr('class', 'badge bg-danger');

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
    const fallbackBtn = selectOne('button[onclick="syncAccounts()"]').first();
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

    const request = instanceStore
        ? instanceStore.actions.syncInstanceAccounts(getInstanceId())
        : instanceService.syncInstanceAccounts(getInstanceId());
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
    const fallbackBtn = selectOne('button[onclick*="syncCapacity"]').first();
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

    const actionLabels = {
        GRANT: { text: '授权', badge: 'bg-success' },
        REVOKE: { text: '撤销', badge: 'bg-danger' },
        ALTER: { text: '更新', badge: 'bg-primary' },
    };

    let html = '<div class="mt-2"><h6 class="text-muted small mb-1">权限变更</h6><ul class="list-unstyled mb-0">';
    diffEntries.forEach(entry => {
        const action = entry?.action || 'UPDATE';
        const actionInfo = actionLabels[action] || { text: action, badge: 'bg-secondary' };
        const target = entry?.object || entry?.label || '';
        const perms =
            Array.isArray(entry?.permissions) && entry.permissions.length > 0
                ? entry.permissions.map(escapeHtml).join('、')
                : escapeHtml(entry?.permissions || '无');

        html += `
            <li class="mb-1">
                <span class="badge ${actionInfo.badge} me-2">${actionInfo.text}</span>
                <span class="text-muted small">${escapeHtml(target)}</span>
                <div class="text-muted small ps-4">${perms}</div>
            </li>
        `;
    });
    html += '</ul></div>';
    return html;
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

    let html = '<div class="mt-2"><h6 class="text-muted small mb-1">其他变更</h6><ul class="list-unstyled mb-0">';
    diffEntries.forEach(entry => {
        const desc = entry?.description || `${entry?.label || ''} 已更新`;
        html += `<li class="text-muted small">${escapeHtml(desc)}</li>`;
    });
    html += '</ul></div>';
    return html;
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
    instanceService.fetchAccountChangeHistory(getInstanceId(), accountId)
        .then(data => {
            const payload = (data && typeof data === 'object' && data.data && typeof data.data === 'object')
                ? data.data
                : data;
            const history = Array.isArray(payload?.history) ? payload.history : null;

            if (data && data.success) {
                // 显示变更历史模态框
                const historyContentWrapper = selectOne('#historyContent');
                if (!historyContentWrapper.length) {
                    console.error('未找到历史记录模态框元素');
                    return;
                }
                if (history && history.length > 0) {
                    let html = '<div class="timeline">';
                    history.forEach(change => {
                        const messageHtml = escapeHtml(change.message || '无描述');
                        const privilegeHtml = renderPrivilegeDiffEntries(change.privilege_diff);
                        const otherHtml = renderOtherDiffEntries(change.other_diff);

                        html += `
                        <div class="timeline-item">
                            <div class="timeline-marker bg-primary"></div>
                            <div class="timeline-content">
                                <h6 class="mb-1">${escapeHtml(change.change_type || '变更')}</h6>
                                <p class="text-muted mb-1">${messageHtml}</p>
                                ${privilegeHtml}
                                ${otherHtml}
                                <small class="text-muted d-block mt-2">${escapeHtml(change.change_time || '未知时间')}</small>
                            </div>
                        </div>
                    `;
                    });
                    html += '</div>';
                    // 安全地设置HTML内容，避免XSS攻击
                    historyContentWrapper.html(html);
                } else {
                historyContentWrapper.html('<p class="text-muted">暂无变更记录</p>');
                }

                ensureHistoryModal().open();
            } else {
                console.error('获取变更历史失败:', data?.error || data?.message);
                toast.error(data?.error || data?.message || '获取变更历史失败');
            }
        })
        .catch(error => {
            console.error('获取变更历史失败:', error.message || error);
        });
}

/**
 * 切换已删除账户的显示/隐藏。
 *
 * @return {void}
 */
function toggleDeletedAccounts() {
    const checkbox = selectOne('#showDeletedAccounts');
    const accountRows = select('.account-row');
    const accountCount = selectOne('#accountCount');
    if (!checkbox.length || !accountRows.length) {
        return;
    }

    let visibleCount = 0;
    const showAll = checkbox.first().checked;

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
    // 从页面URL或数据属性中获取实例ID
    const urlParts = window.location.pathname.split('/');
    return urlParts[urlParts.length - 1];
}

/**
 * 获取实例名称。
 *
 * @return {string} 实例名称
 */
function getInstanceName() {
    const titleElement = selectOne('h2');
    if (titleElement.length) {
        return (titleElement.text() || '').trim();
    }
    return '未知实例';
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

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

/**
 * 加载数据库容量数据。
 *
 * @return {void}
 */
function loadDatabaseSizes() {
    if (!ensureInstanceService()) {
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
        <div class="row mb-3">
            <div class="col-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-primary">${onlineCount}</h5>
                        <p class="card-text text-muted">在线数据库</p>
                    </div>
                </div>
            </div>
            <div class="col-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-danger">${deletedCount}</h5>
                        <p class="card-text text-muted">已删除数据库</p>
                    </div>
                </div>
            </div>
            <div class="col-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">${totalSizeLabel}</h5>
                        <p class="card-text text-muted">总容量</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mb-3">
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="showDeletedDatabases" onchange="toggleDeletedDatabases()">
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
        let sizeBadgeClass = 'badge bg-success'; // 默认绿色
        if (sizeValue >= 1024 * 1000) {
            sizeBadgeClass = 'badge bg-danger'; // >= 1 TB
        } else if (sizeValue >= 1024 * 100) {
            sizeBadgeClass = 'badge bg-warning';
        } else if (sizeValue >= 1024 * 10) {
            sizeBadgeClass = 'badge bg-primary';
        }

        const displaySize = sizeValue > 0 ? sizeLabel : '<span class="text-muted">无数据</span>';

        // 状态列显示
        const statusBadge = isActive
            ? '<span class="badge bg-success"><i class="fas fa-check me-1"></i>在线</span>'
            : '<span class="badge bg-danger"><i class="fas fa-trash me-1"></i>已删除</span>';

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
            <button class="btn btn-outline-primary" onclick="loadDatabaseSizes()">
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
function refreshDatabaseSizes() {
    loadDatabaseSizes();
}

/**
 * 切换已删除数据库的显示/隐藏。
 *
 * @return {void}
 */
function toggleDeletedDatabases() {
    const checkbox = selectOne('#showDeletedDatabases');
    const rows = select('#databaseSizesContent tbody tr[data-is-active]');
    if (!checkbox.length || !rows.length) {
        return;
    }
    const showDeleted = checkbox.first().checked;
    rows.each((row) => {
        const isActive = row.getAttribute('data-is-active') !== 'false';
        if (!isActive) {
            row.style.display = showDeleted ? '' : 'none';
        }
    });
}

// 页面加载完成后自动加载数据库容量信息
ready(() => {
    window.setTimeout(loadDatabaseSizes, 500);
    Object.assign(window, {
        testConnection,
        syncAccounts,
        syncCapacity,
        viewInstanceAccountPermissions,
        viewAccountChangeHistory,
        loadDatabaseSizes,
        toggleDeletedAccounts,
        toggleDeletedDatabases,
    });
});
}

window.InstanceDetailPage = {
    mount: mountInstanceDetailPage,
};
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
        wrapper.html('');
    }
}
