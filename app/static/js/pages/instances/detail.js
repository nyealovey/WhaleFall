/**
 * 实例详情页面JavaScript
 * 处理连接测试、账户同步、权限查看等功能
 */

// 页面加载完成，不自动测试连接
document.addEventListener('DOMContentLoaded', function () {
    // 页面加载完成，等待用户手动测试连接
    // 默认隐藏已删除账户（复选框未勾选状态）
    const checkbox = document.getElementById('showDeletedAccounts');
    if (checkbox) {
        checkbox.checked = false;
        toggleDeletedAccounts();
    }
});

// 测试连接 - 使用新的连接管理API
function testConnection() {
    const testBtn = event ? event.target : document.querySelector('button[onclick="testConnection()"]');
    const originalText = testBtn.innerHTML;

    // 记录操作开始日志
    console.info('开始测试连接', {
        operation: 'test_connection',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
    testBtn.disabled = true;

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

            const statusBadge = document.getElementById('connectionStatus');
            const resultDiv = document.getElementById('testResult');

            statusBadge.textContent = '正常';
            statusBadge.className = 'badge bg-success';

            // 使用连接管理组件的显示方法
            connectionManager.showTestResult(data, 'testResultContent');
            resultDiv.style.display = 'block';
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

            const statusBadge = document.getElementById('connectionStatus');
            const resultDiv = document.getElementById('testResult');

            statusBadge.textContent = '失败';
            statusBadge.className = 'badge bg-danger';

            // 使用连接管理组件的显示方法
            connectionManager.showTestResult(error, 'testResultContent');
            resultDiv.style.display = 'block';
        }
    }).finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// 同步账户
function syncAccounts() {
    const syncBtn = event ? event.target : document.querySelector('button[onclick="syncAccounts()"]');
    const originalText = syncBtn.innerHTML;

    // 记录操作开始日志
    console.info('开始同步账户', {
        operation: 'sync_accounts',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    syncBtn.disabled = true;

    http.post(`/account_sync/api/instances/${getInstanceId()}/sync`)
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
            syncBtn.innerHTML = originalText;
            syncBtn.disabled = false;
        });
}

// 同步容量
function syncCapacity(instanceId, instanceName) {
    const syncBtn = event ? event.target : document.querySelector('button[onclick*="syncCapacity"]');
    const originalText = syncBtn.innerHTML;

    // 记录操作开始日志
    console.info('开始同步容量', {
        operation: 'sync_capacity',
        instance_id: instanceId,
        instance_name: instanceName
    });

    syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    syncBtn.disabled = true;

    http.post(`/capacity/api/instances/${instanceId}/sync-capacity`)
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
            syncBtn.innerHTML = originalText;
            syncBtn.disabled = false;
        });
}

// 查看实例账户权限
function viewInstanceAccountPermissions(accountId) {
    // 调用全局的 viewAccountPermissions 函数，指定instances页面的API URL
    window.viewAccountPermissions(accountId, {
        apiUrl: `/instances/api/${getInstanceId()}/accounts/${accountId}/permissions`
    });
}

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

// 查看账户变更历史
function viewAccountChangeHistory(accountId) {
    http.get(`/instances/api/${getInstanceId()}/accounts/${accountId}/change-history`)
        .then(data => {
            const payload = (data && typeof data === 'object' && data.data && typeof data.data === 'object')
                ? data.data
                : data;
            const history = Array.isArray(payload?.history) ? payload.history : null;

            if (data && data.success) {
                // 显示变更历史模态框
                const modal = new bootstrap.Modal(document.getElementById('historyModal'));
                const historyContent = document.getElementById('historyContent');

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
                    historyContent.innerHTML = '';
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = html;
                    while (tempDiv.firstChild) {
                        historyContent.appendChild(tempDiv.firstChild);
                    }
                } else {
                    // 安全地设置HTML内容，避免XSS攻击
                    const p = document.createElement('p');
                    p.className = 'text-muted';
                    p.textContent = '暂无变更记录';
                    historyContent.innerHTML = '';
                    historyContent.appendChild(p);
                }

                modal.show();
            } else {
                console.error('获取变更历史失败:', data?.error || data?.message);
                toast.error(data?.error || data?.message || '获取变更历史失败');
            }
        })
        .catch(error => {
            console.error('获取变更历史失败:', error.message || error);
        });
}

// 切换已删除账户显示
function toggleDeletedAccounts() {
    const checkbox = document.getElementById('showDeletedAccounts');
    const accountRows = document.querySelectorAll('.account-row');
    const accountCount = document.getElementById('accountCount');

    let visibleCount = 0;

    accountRows.forEach(row => {
        const isDeleted = row.getAttribute('data-is-deleted') === 'true';

        if (checkbox.checked) {
            // 显示所有账户（包括已删除的）
            row.style.display = '';
            visibleCount++;
        } else {
            // 只显示非已删除账户
            if (isDeleted) {
                row.style.display = 'none';
            } else {
                row.style.display = '';
                visibleCount++;
            }
        }
    });

    // 更新账户计数
    if (accountCount) {
        accountCount.textContent = `共 ${visibleCount} 个账户`;
    }
}

// 显示提示信息

// 工具函数
function getInstanceId() {
    // 从页面URL或数据属性中获取实例ID
    const urlParts = window.location.pathname.split('/');
    return urlParts[urlParts.length - 1];
}

function getInstanceName() {
    // 从页面标题或数据属性中获取实例名称
    const titleElement = document.querySelector('h2');
    if (titleElement) {
        return titleElement.textContent.trim();
    }
    return '未知实例';
}

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

// 数据库容量相关函数
function loadDatabaseSizes() {
    const instanceId = getInstanceId();
    const contentDiv = document.getElementById('databaseSizesContent');

    if (!contentDiv) {
        console.error('找不到数据库容量内容容器');
        return;
    }

    // 显示加载状态
    contentDiv.innerHTML = `
        <div class="text-center py-4">
            <i class="fas fa-spinner fa-spin fa-2x text-muted mb-3"></i>
            <p class="text-muted">正在加载数据库容量信息...</p>
        </div>
    `;

    http.get(`/instances/api/databases/${instanceId}/sizes?latest_only=true&include_inactive=true`)
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

function displayDatabaseSizes(payload) {
    const contentDiv = document.getElementById('databaseSizesContent');
    const databases = Array.isArray(payload?.databases) ? payload.databases : [];

    if (!databases.length) {
        contentDiv.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-database fa-3x text-muted mb-3"></i>
                <p class="text-muted">暂无数据库容量信息</p>
                <p class="text-muted">点击"同步容量"按钮获取容量信息</p>
            </div>
        `;
        return;
    }

    const totalSize = Number(payload?.total_size_mb ?? 0) || 0;
    const totalSizeLabel = formatGbLabelFromMb(totalSize);

    const filteredCount = Number(payload?.filtered_count ?? 0) || 0;
    const activeCount = Number(payload?.active_count ?? (databases.length - filteredCount));

    // 按数据库大小从大到小排序
    databases.sort((a, b) => (Number(b.size_mb) || 0) - (Number(a.size_mb) || 0));

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

    contentDiv.innerHTML = html;

    const checkbox = document.getElementById('showDeletedDatabases');
    if (checkbox) {
        checkbox.checked = false;
    }
    toggleDeletedDatabases();
}

function displayDatabaseSizesError(error) {
    const contentDiv = document.getElementById('databaseSizesContent');
    contentDiv.innerHTML = `
        <div class="text-center py-4">
            <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
            <p class="text-muted">加载数据库容量信息失败</p>
            <p class="text-danger">${error}</p>
            <button class="btn btn-outline-primary" onclick="loadDatabaseSizes()">
                <i class="fas fa-redo me-1"></i>重试
            </button>
        </div>
    `;
}

function refreshDatabaseSizes() {
    loadDatabaseSizes();
}

// 切换已删除数据库显示/隐藏
function toggleDeletedDatabases() {
    const checkbox = document.getElementById('showDeletedDatabases');
    const rows = document.querySelectorAll('#databaseSizesContent tbody tr[data-is-active]');

    rows.forEach(row => {
        const isActive = row.getAttribute('data-is-active') !== 'false';
        if (!isActive) {
            row.style.display = checkbox.checked ? '' : 'none';
        }
    });
}

// 页面加载完成后自动加载数据库容量信息
document.addEventListener('DOMContentLoaded', function () {
    // 延迟加载，确保页面完全渲染
    setTimeout(loadDatabaseSizes, 500);
});
