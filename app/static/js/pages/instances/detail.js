/**
 * 实例详情页面JavaScript
 * 处理连接测试、账户同步、权限查看等功能
 */

// 页面加载完成，不自动测试连接
document.addEventListener('DOMContentLoaded', function() {
    // 页面加载完成，等待用户手动测试连接
    // 默认隐藏已删除账户（复选框未勾选状态）
    const checkbox = document.getElementById('showDeletedAccounts');
    if (checkbox && !checkbox.checked) {
        toggleDeletedAccounts();
    }
});

// 测试连接
function testConnection() {
    const testBtn = event ? event.target : document.querySelector('button[onclick="testConnection()"]');
    const originalText = testBtn.innerHTML;

    // 记录操作开始日志
    logUserAction('开始测试连接', {
        operation: 'test_connection',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>测试中...';
    testBtn.disabled = true;

    // 获取CSRF token
    const csrfToken = getCSRFToken();

    fetch(`/instances/api/instances/${getInstanceId()}/test`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                throw new Error('认证失败，请重新登录');
            } else if (response.status === 404) {
                throw new Error('API接口不存在');
            } else {
                throw new Error(`HTTP错误: ${response.status}`);
            }
        }
        return response.json();
    })
    .then(data => {
        const statusBadge = document.getElementById('connectionStatus');
        const resultDiv = document.getElementById('testResult');
        const contentDiv = document.getElementById('testResultContent');

        if (data.success) {
            // 记录成功日志
            logUserAction('测试连接成功', {
                operation: 'test_connection',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'success',
                message: data.message || '数据库连接正常'
            });

            statusBadge.textContent = '正常';
            statusBadge.className = 'badge bg-success';

            // 安全地创建HTML内容，避免XSS攻击
            const successDiv = document.createElement('div');
            successDiv.className = 'alert alert-success';
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-check-circle me-2';
            
            const strong = document.createElement('strong');
            strong.textContent = '连接成功！';
            
            const br = document.createElement('br');
            
            const message = document.createElement('span');
            message.textContent = data.message || '数据库连接正常';
            
            successDiv.appendChild(icon);
            successDiv.appendChild(strong);
            successDiv.appendChild(br);
            successDiv.appendChild(message);
            
            contentDiv.innerHTML = '';
            contentDiv.appendChild(successDiv);
        } else if (data.error) {
            // 记录失败日志
            logError('测试连接失败', {
                operation: 'test_connection',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'failed',
                error: data.error
            });

            statusBadge.textContent = '失败';
            statusBadge.className = 'badge bg-danger';

            // 构建详细的错误信息
            let errorHtml = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>连接失败！</strong><br>
                    <strong>错误类型：</strong>${data.error}<br>
            `;

            // 添加详细信息
            if (data.details) {
                errorHtml += `<strong>详细信息：</strong>${data.details}<br>`;
            }

            // 添加解决方案
            if (data.solution) {
                errorHtml += `<strong>解决方案：</strong>${data.solution}<br>`;
            }

            // 添加错误类型
            if (data.error_type) {
                errorHtml += `<small class="text-muted">错误类型: ${data.error_type}</small>`;
            }

            errorHtml += `</div>`;

            contentDiv.innerHTML = errorHtml;
        }

        resultDiv.style.display = 'block';
    })
    .catch(error => {
        const statusBadge = document.getElementById('connectionStatus');
        statusBadge.textContent = '错误';
        statusBadge.className = 'badge bg-danger';

        // 安全地创建错误HTML内容，避免XSS攻击
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-triangle me-2';
        
        const strong1 = document.createElement('strong');
        strong1.textContent = '测试失败！';
        
        const br1 = document.createElement('br');
        
        const strong2 = document.createElement('strong');
        strong2.textContent = '错误信息：';
        
        const message = document.createElement('span');
        message.textContent = error.message || '未知错误';
        
        const br2 = document.createElement('br');
        
        const small = document.createElement('small');
        small.className = 'text-muted';
        small.textContent = '请检查网络连接或重新登录';
        
        errorDiv.appendChild(icon);
        errorDiv.appendChild(strong1);
        errorDiv.appendChild(br1);
        errorDiv.appendChild(strong2);
        errorDiv.appendChild(message);
        errorDiv.appendChild(br2);
        errorDiv.appendChild(small);
        
        const contentDiv = document.getElementById('testResultContent');
        contentDiv.innerHTML = '';
        contentDiv.appendChild(errorDiv);
        document.getElementById('testResult').style.display = 'block';
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '测试连接异常', {
            operation: 'test_connection',
            instance_id: getInstanceId(),
            instance_name: getInstanceName(),
            result: 'exception'
        });
    })
    .finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// 同步账户
function syncAccounts() {
    const syncBtn = event ? event.target : document.querySelector('button[onclick="syncAccounts()"]');
    const originalText = syncBtn.innerHTML;

    // 记录操作开始日志
    logUserAction('开始同步账户', {
        operation: 'sync_accounts',
        instance_id: getInstanceId(),
        instance_name: getInstanceName()
    });

    syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    syncBtn.disabled = true;

    // 获取CSRF token
    const csrfToken = getCSRFToken();

    fetch(`/instances/${getInstanceId()}/sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            // 记录成功日志
            logUserAction('同步账户成功', {
                operation: 'sync_accounts',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'success',
                message: data.message
            });
            showAlert('success', data.message);
        } else if (data.error) {
            // 记录失败日志
            logError('同步账户失败', {
                operation: 'sync_accounts',
                instance_id: getInstanceId(),
                instance_name: getInstanceName(),
                result: 'failed',
                error: data.error
            });
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '同步账户异常', {
            operation: 'sync_accounts',
            instance_id: getInstanceId(),
            instance_name: getInstanceName(),
            result: 'exception'
        });
        showAlert('danger', '同步失败');
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
    logUserAction('开始同步容量', {
        operation: 'sync_capacity',
        instance_id: instanceId,
        instance_name: instanceName
    });

    syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>同步中...';
    syncBtn.disabled = true;

    // 获取CSRF token
    const csrfToken = getCSRFToken();

    fetch(`/instances/${instanceId}/sync-capacity`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                throw new Error('认证失败，请重新登录');
            } else if (response.status === 404) {
                throw new Error('API接口不存在');
            } else {
                throw new Error(`HTTP错误: ${response.status}`);
            }
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 记录成功日志
            logUserAction('同步容量成功', {
                operation: 'sync_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'success',
                message: data.message || '容量同步成功'
            });
            showAlert('success', data.message || '容量同步成功');
            
            // 刷新数据库容量显示
            setTimeout(() => {
                loadDatabaseSizes();
            }, 1000);
        } else if (data.error) {
            // 记录失败日志
            logError('同步容量失败', {
                operation: 'sync_capacity',
                instance_id: instanceId,
                instance_name: instanceName,
                result: 'failed',
                error: data.error
            });
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        // 记录异常日志
        logErrorWithContext(error, '同步容量异常', {
            operation: 'sync_capacity',
            instance_id: instanceId,
            instance_name: instanceName,
            result: 'exception'
        });
        showAlert('danger', '同步容量失败: ' + (error.message || '未知错误'));
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
        apiUrl: `/instances/${getInstanceId()}/accounts/${accountId}/permissions`
    });
}

// 查看账户变更历史
function viewAccountChangeHistory(accountId) {
    // 查看变更历史
    const csrfToken = getCSRFToken();

    fetch(`/instances/api/instances/${getInstanceId()}/accounts/${accountId}/change-history`, {
        method: 'GET',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示变更历史模态框
            const modal = new bootstrap.Modal(document.getElementById('historyModal'));
            const historyContent = document.getElementById('historyContent');

            if (data.history && data.history.length > 0) {
                let html = '<div class="timeline">';
                data.history.forEach(change => {
                    html += `
                        <div class="timeline-item">
                            <div class="timeline-marker bg-primary"></div>
                            <div class="timeline-content">
                                <h6 class="mb-1">${change.change_type || '变更'}</h6>
                                <p class="text-muted mb-1">${change.message || '无描述'}</p>
                                <small class="text-muted">${change.change_time || '未知时间'}</small>
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
            console.error('获取变更历史失败:', data.error);
        }
    })
    .catch(error => {
        console.error('获取变更历史失败:', error);
        console.error('获取变更历史失败:', error.message);
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
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    
    // 安全地创建HTML内容，避免XSS攻击
    const icon = document.createElement('i');
    icon.className = `fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2`;
    
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    
    alertDiv.appendChild(icon);
    alertDiv.appendChild(messageSpan);
    alertDiv.appendChild(closeButton);

    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

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

function getCSRFToken() {
    return document.querySelector('input[name="csrf_token"]')?.value || '';
}

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
    
    fetch(`/instances/${instanceId}/database-sizes`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayDatabaseSizes(data.data, data.total_size_mb);
        } else {
            displayDatabaseSizesError(data.error || '加载失败');
        }
    })
    .catch(error => {
        console.error('加载数据库容量信息失败:', error);
        displayDatabaseSizesError('网络错误，请稍后重试');
    });
}

function displayDatabaseSizes(databases, totalSize) {
    const contentDiv = document.getElementById('databaseSizesContent');
    
    if (!databases || databases.length === 0) {
        contentDiv.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-database fa-3x text-muted mb-3"></i>
                <p class="text-muted">暂无数据库容量信息</p>
                <p class="text-muted">点击"同步容量"按钮获取容量信息</p>
            </div>
        `;
        return;
    }
    
    // 计算总容量显示
    const totalSizeGB = (totalSize / 1024).toFixed(3);
    
    // 统计已删除和在线数据库数量
    const deletedCount = databases.filter(db => db.is_deleted).length;
    const onlineCount = databases.length - deletedCount;
    
    let html = `
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-primary">${onlineCount}</h5>
                        <p class="card-text text-muted">在线数据库</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-danger">${deletedCount}</h5>
                        <p class="card-text text-muted">已删除数据库</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">${totalSizeGB} GB</h5>
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
                        <th style="width: 30%;"><i class="fas fa-database me-1"></i>数据库名称</th>
                        <th style="width: 12%;"><i class="fas fa-hdd me-1"></i>总大小</th>
                        <th style="width: 12%;"><i class="fas fa-file me-1"></i>数据大小</th>
                        <th style="width: 12%;"><i class="fas fa-file-alt me-1"></i>日志大小</th>
                        <th style="width: 10%;"><i class="fas fa-trash me-1"></i>状态</th>
                        <th style="width: 24%;"><i class="fas fa-clock me-1"></i>采集时间</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    databases.forEach(db => {
        const sizeGB = (db.size_mb / 1024).toFixed(3);
        const dataSizeGB = (db.data_size_mb / 1024).toFixed(3);
        const logSizeGB = db.log_size_mb ? (db.log_size_mb / 1024).toFixed(3) : '-';
        const collectedAt = new Date(db.collected_at).toLocaleString('zh-CN');
        
        const isDeleted = db.is_deleted || false;
        const rowClass = isDeleted ? 'table-secondary' : '';
        const iconClass = isDeleted ? 'text-muted' : 'text-primary';
        const textClass = isDeleted ? 'text-muted' : '';
        
        // 根据总大小判断颜色
        let sizeBadgeClass = 'badge bg-success'; // 默认绿色
        const sizeGBValue = parseFloat(sizeGB);
        
        if (sizeGBValue >= 1000) {
            sizeBadgeClass = 'badge bg-danger'; // 红色 - 大于1000GB
        } else if (sizeGBValue >= 100) {
            sizeBadgeClass = 'badge bg-warning'; // 黄色 - 大于100GB
        } else if (sizeGBValue >= 10) {
            sizeBadgeClass = 'badge bg-primary'; // 蓝色 - 大于10GB
        } else {
            sizeBadgeClass = 'badge bg-success'; // 绿色 - 小于10GB
        }
        
        // 状态列显示
        const statusBadge = isDeleted ? 
            '<span class="badge bg-danger">已删除</span>' : 
            '<span class="badge bg-success">在线</span>';
        
        html += `
            <tr class="${rowClass}" data-deleted="${isDeleted}">
                <td>
                    <div class="d-flex align-items-start">
                        <i class="fas fa-database ${iconClass} me-2 mt-1"></i>
                        <div>
                            <strong class="${textClass}" style="word-wrap: break-word; white-space: normal; line-height: 1.4;">${db.database_name}</strong>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="${sizeBadgeClass}">${sizeGB} GB</span>
                </td>
                <td>
                    <span class="text-muted">${dataSizeGB} GB</span>
                </td>
                <td>
                    ${db.log_size_mb ? 
                        `<span class="text-muted">${logSizeGB} GB</span>` : 
                        '<span class="text-muted">-</span>'
                    }
                </td>
                <td>
                    ${statusBadge}
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
    const rows = document.querySelectorAll('#databaseSizesContent tbody tr[data-deleted]');
    
    rows.forEach(row => {
        const isDeleted = row.getAttribute('data-deleted') === 'true';
        if (isDeleted) {
            row.style.display = checkbox.checked ? '' : 'none';
        }
    });
}

// 页面加载完成后自动加载数据库容量信息
document.addEventListener('DOMContentLoaded', function() {
    // 延迟加载，确保页面完全渲染
    setTimeout(loadDatabaseSizes, 500);
});
