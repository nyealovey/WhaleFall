/**
 * 同步记录页面JavaScript
 * 处理同步记录查看、重试、批量操作等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 初始化页面
function initializePage() {
    // 可以添加页面初始化逻辑
    console.log('同步记录页面已加载');
}

// 查看详情
function viewDetails(recordId) {
    const detailsContent = document.getElementById('detailsContent');
    if (detailsContent) {
        detailsContent.innerHTML = `
            <div class="text-center">
                <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                <p>加载详情中...</p>
            </div>
        `;
    }
    
    const detailsModal = document.getElementById('detailsModal');
    if (detailsModal) {
        new bootstrap.Modal(detailsModal).show();
    }
    
    // 模拟加载详情
    setTimeout(() => {
        if (detailsContent) {
            detailsContent.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    详情功能开发中，记录ID: ${recordId}
                </div>
            `;
        }
    }, 1000);
}

// 重试同步
function retrySync(instanceId) {
    if (confirm('确定要重试同步此实例吗？')) {
        const btn = event.target.closest('button');
        const originalHtml = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;
        
        fetch(`/accounts/sync/${instanceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                showAlert('success', data.message);
                setTimeout(() => location.reload(), 2000);
            } else if (data.error) {
                showAlert('danger', data.error);
            }
        })
        .catch(error => {
            showAlert('danger', '重试同步失败');
        })
        .finally(() => {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        });
    }
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 获取提示图标
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'info': 'info-circle',
        'warning': 'exclamation-triangle',
        'danger': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
}

// 查看批量同步详情
function viewBatchDetails(recordIds) {
    try {
        // 检查recordIds是否有效
        if (!recordIds || !Array.isArray(recordIds) || recordIds.length === 0) {
            showAlert('danger', '没有提供记录ID');
            return;
        }
        
        const recordIdsStr = recordIds.join(',');
        const url = `/account-sync/sync-details-batch?record_ids=${encodeURIComponent(recordIdsStr)}`;
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showBatchDetailsModal(data.details);
            } else {
                showAlert('danger', data.error || '获取详情失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', `获取详情失败: ${error.message}`);
        });
    } catch (error) {
        console.error('JavaScript错误:', error);
        showAlert('danger', `操作失败: ${error.message}`);
    }
}

// 查看失败详情
function viewFailedDetails(recordIds) {
    try {
        // 检查recordIds是否有效
        if (!recordIds || !Array.isArray(recordIds) || recordIds.length === 0) {
            showAlert('danger', '没有提供记录ID');
            return;
        }
        
        const recordIdsStr = recordIds.join(',');
        const url = `/account-sync/sync-details-batch?record_ids=${encodeURIComponent(recordIdsStr)}&failed_only=true`;
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showFailedDetailsModal(data.details);
            } else {
                showAlert('danger', data.error || '获取失败详情失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', `获取失败详情失败: ${error.message}`);
        });
    } catch (error) {
        console.error('JavaScript错误:', error);
        showAlert('danger', `操作失败: ${error.message}`);
    }
}

// 显示批量同步详情模态框
function showBatchDetailsModal(details) {
    // 检查是否有数据
    if (!details || details.length === 0) {
        showAlert('warning', '该同步任务没有实例记录，可能是早期失败的任务或数据不完整');
        return;
    }
    
    // 计算统计信息
    const successCount = details.filter(d => d.status === 'completed').length;
    const failedCount = details.filter(d => d.status === 'failed').length;
    const totalAccounts = details.reduce((sum, d) => sum + (d.synced_count || 0), 0);
    const totalInstances = details.length;
    
    const modalHtml = createBatchDetailsModalHtml(successCount, failedCount, totalAccounts, totalInstances, details);
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('batchDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('batchDetailsModal'));
    modal.show();
}

// 创建批量详情模态框HTML
function createBatchDetailsModalHtml(successCount, failedCount, totalAccounts, totalInstances, details) {
    return `
        <div class="modal fade" id="batchDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-list me-2"></i>批量同步详情
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <div class="card bg-success text-white">
                                    <div class="card-body text-center">
                                        <h4>${successCount}</h4>
                                        <small>成功实例</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-danger text-white">
                                    <div class="card-body text-center">
                                        <h4>${failedCount}</h4>
                                        <small>失败实例</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-info text-white">
                                    <div class="card-body text-center">
                                        <h4>${totalAccounts}</h4>
                                        <small>同步账户</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-warning text-white">
                                    <div class="card-body text-center">
                                        <h4>${totalInstances}</h4>
                                        <small>总实例</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>实例名称</th>
                                        <th>状态</th>
                                        <th>同步数量</th>
                                        <th>消息</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${details.map(result => `
                                        <tr>
                                            <td>${result.instance_name}</td>
                                            <td>
                                                <span class="badge bg-${getStatusBadgeClass(result.status)}">
                                                    ${getStatusText(result.status)}
                                                </span>
                                            </td>
                                            <td>${result.synced_count || 0}</td>
                                            <td>${result.message || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 显示失败详情模态框
function showFailedDetailsModal(details) {
    // 过滤出失败的记录
    const failedDetails = details.filter(d => d.status === 'failed');
    const failedCount = failedDetails.length;
    
    const modalHtml = createFailedDetailsModalHtml(failedCount, failedDetails);
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('failedDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('failedDetailsModal'));
    modal.show();
}

// 创建失败详情模态框HTML
function createFailedDetailsModalHtml(failedCount, failedDetails) {
    return `
        <div class="modal fade" id="failedDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>失败实例详情
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <i class="fas fa-info-circle me-2"></i>
                            共 ${failedCount} 个实例同步失败，以下是详细信息：
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>实例名称</th>
                                        <th>状态</th>
                                        <th>失败原因</th>
                                        <th>同步时间</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${failedDetails.map(result => `
                                        <tr>
                                            <td>${result.instance_name}</td>
                                            <td>
                                                <span class="badge bg-danger">失败</span>
                                            </td>
                                            <td>
                                                <small class="text-danger">${result.message || '未知错误'}</small>
                                            </td>
                                            <td>
                                                <small class="text-muted">${result.sync_time ? formatTime(result.sync_time, 'datetime') : '-'}</small>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 工具函数
function getStatusBadgeClass(status) {
    const classes = {
        'completed': 'success',
        'failed': 'danger',
        'cancelled': 'secondary',
        'running': 'primary'
    };
    return classes[status] || 'warning';
}

function getStatusText(status) {
    const texts = {
        'completed': 'completed',
        'failed': 'failed',
        'cancelled': 'cancelled',
        'running': 'running'
    };
    return texts[status] || status;
}

// 初始化统一搜索组件
function initUnifiedSearch() {
    // 等待统一搜索组件加载完成
    if (typeof UnifiedSearch !== 'undefined') {
        const searchForm = document.querySelector('.unified-search-form');
        if (searchForm) {
            const unifiedSearch = new UnifiedSearch(searchForm);
            
            // 重写搜索方法
            unifiedSearch.handleSubmit = function(e) {
                e.preventDefault();
                applyFilters();
            };
            
            // 重写清除方法
            unifiedSearch.clearForm = function() {
                // 清除所有筛选条件
                const inputs = this.form.querySelectorAll('.unified-input');
                inputs.forEach(input => {
                    input.value = '';
                });

                const selects = this.form.querySelectorAll('.unified-select');
                selects.forEach(select => {
                    select.selectedIndex = 0;
                });

                // 刷新页面，清除所有筛选条件
                window.location.href = window.location.pathname;
            };
        }
    } else {
        // 如果统一搜索组件未加载，使用传统方式
        setTimeout(initUnifiedSearch, 100);
    }
}

// 应用筛选条件
function applyFilters() {
    const form = document.querySelector('.unified-search-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const params = new URLSearchParams();
    
    // 获取筛选条件
    const syncType = formData.get('sync_type') || '';
    const status = formData.get('status') || '';
    const timeRange = formData.get('time_range') || '';
    
    // 构建URL参数
    if (syncType) params.append('sync_type', syncType);
    if (status) params.append('status', status);
    if (timeRange) params.append('date_range', timeRange);
    
    // 跳转到筛选后的页面
    const url = new URL(window.location);
    url.search = params.toString();
    window.location.href = url.toString();
}

// 页面加载完成后初始化统一搜索组件
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    initUnifiedSearch();
});

// 导出函数供全局使用
window.viewDetails = viewDetails;
window.retrySync = retrySync;
window.showAlert = showAlert;
window.viewBatchDetails = viewBatchDetails;
window.viewFailedDetails = viewFailedDetails;
window.applyFilters = applyFilters;
