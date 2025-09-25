// app/static/js/pages/database_sizes/partitions.js

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initializePartitionsPage();
    
    // 绑定事件
    bindEvents();
    
    // 加载数据
    loadPartitionData();
});

/**
 * 初始化分区管理页面
 */
function initializePartitionsPage() {
    console.log('初始化分区管理页面...');
    
    // 设置默认日期为下个月
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    nextMonth.setDate(1);
    document.getElementById('partitionDate').value = nextMonth.toISOString().split('T')[0];
}

/**
 * 绑定事件处理器
 */
function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadPartitionData();
    });
    
    // 创建分区按钮
    document.getElementById('createPartitionBtn').addEventListener('click', function() {
        showCreatePartitionModal();
    });
    
    // 清理分区按钮
    document.getElementById('cleanupPartitionsBtn').addEventListener('click', function() {
        showCleanupPartitionsModal();
    });
    
    // 确认创建分区
    document.getElementById('confirmCreatePartition').addEventListener('click', function() {
        createPartition();
    });
    
    // 确认清理分区
    document.getElementById('confirmCleanupPartitions').addEventListener('click', function() {
        cleanupPartitions();
    });
}

/**
 * 加载分区数据
 */
async function loadPartitionData() {
    try {
        showLoadingState();
        
        // 并行加载分区信息和状态
        const [partitionInfoResponse, partitionStatusResponse] = await Promise.all([
            fetch('/database-sizes/partitions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            }),
            fetch('/database-sizes/partitions/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            })
        ]);
        
        if (!partitionInfoResponse.ok || !partitionStatusResponse.ok) {
            throw new Error('加载分区数据失败');
        }
        
        const partitionInfo = await partitionInfoResponse.json();
        const partitionStatus = await partitionStatusResponse.json();
        
        if (partitionInfo.success && partitionStatus.success) {
            updatePartitionOverview(partitionStatus.data);
            updatePartitionsTable(partitionInfo.data.partitions);
        } else {
            throw new Error(partitionInfo.error || partitionStatus.error || '加载分区数据失败');
        }
        
    } catch (error) {
        console.error('加载分区数据失败:', error);
        showError('加载分区数据失败: ' + error.message);
    }
}

/**
 * 更新分区概览
 */
function updatePartitionOverview(data) {
    document.getElementById('totalPartitions').textContent = data.total_partitions || 0;
    document.getElementById('totalSize').textContent = data.total_size || '0 B';
    document.getElementById('totalRecords').textContent = formatNumber(data.total_records || 0);
    
    // 更新状态
    const statusElement = document.getElementById('partitionStatus');
    if (data.status === 'healthy') {
        statusElement.innerHTML = '<span class="badge bg-success">健康</span>';
    } else if (data.status === 'warning') {
        statusElement.innerHTML = '<span class="badge bg-warning">警告</span>';
    } else {
        statusElement.innerHTML = '<span class="badge bg-danger">异常</span>';
    }
    
    // 添加动画效果
    statusElement.classList.add('fade-in');
    setTimeout(() => statusElement.classList.remove('fade-in'), 300);
}

/**
 * 更新分区表格
 */
function updatePartitionsTable(partitions) {
    const tbody = document.getElementById('partitionsTableBody');
    
    if (!partitions || partitions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-inbox me-2"></i>暂无分区数据
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = partitions.map(partition => {
        const status = getPartitionStatus(partition);
        const statusBadge = getStatusBadge(status);
        
        return `
            <tr>
                <td>
                    <code>${partition.name}</code>
                </td>
                <td>
                    ${partition.date ? formatDate(partition.date) : '-'}
                </td>
                <td>
                    <span class="text-info">
                        <i class="fas fa-hdd me-1"></i>${partition.size}
                    </span>
                </td>
                <td>
                    <span class="text-success">
                        <i class="fas fa-database me-1"></i>${formatNumber(partition.record_count)}
                    </span>
                </td>
                <td>
                    ${statusBadge}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info btn-sm" onclick="viewPartitionDetails('${partition.name}')" title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="deletePartition('${partition.name}')" title="删除分区">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * 获取分区状态
 */
function getPartitionStatus(partition) {
    if (!partition.date) return 'unknown';
    
    const partitionDate = new Date(partition.date);
    const now = new Date();
    const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    
    if (partitionDate < currentMonth) {
        return 'old';
    } else if (partitionDate >= currentMonth && partitionDate < nextMonth) {
        return 'current';
    } else {
        return 'future';
    }
}

/**
 * 获取状态徽章
 */
function getStatusBadge(status) {
    switch (status) {
        case 'current':
            return '<span class="badge bg-success">当前</span>';
        case 'future':
            return '<span class="badge bg-info">未来</span>';
        case 'old':
            return '<span class="badge bg-warning">旧分区</span>';
        default:
            return '<span class="badge bg-secondary">未知</span>';
    }
}

/**
 * 显示创建分区模态框
 */
function showCreatePartitionModal() {
    const modal = new bootstrap.Modal(document.getElementById('createPartitionModal'));
    modal.show();
}

/**
 * 显示清理分区模态框
 */
function showCleanupPartitionsModal() {
    const modal = new bootstrap.Modal(document.getElementById('cleanupPartitionsModal'));
    modal.show();
}

/**
 * 创建分区
 */
async function createPartition() {
    const partitionDate = document.getElementById('partitionDate').value;
    
    if (!partitionDate) {
        showError('请选择分区日期');
        return;
    }
    
    try {
        const response = await fetch('/database-sizes/partitions/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                date: partitionDate
            })
        });
        
        if (!response.ok) {
            throw new Error('创建分区失败');
        }
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('分区创建成功: ' + data.data.message);
            bootstrap.Modal.getInstance(document.getElementById('createPartitionModal')).hide();
            loadPartitionData();
        } else {
            throw new Error(data.error || '创建分区失败');
        }
        
    } catch (error) {
        console.error('创建分区失败:', error);
        showError('创建分区失败: ' + error.message);
    }
}

/**
 * 清理分区
 */
async function cleanupPartitions() {
    const retentionMonths = parseInt(document.getElementById('retentionMonths').value);
    
    if (!retentionMonths || retentionMonths < 1) {
        showError('请输入有效的保留月数');
        return;
    }
    
    try {
        const response = await fetch('/database-sizes/partitions/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                retention_months: retentionMonths
            })
        });
        
        if (!response.ok) {
            throw new Error('清理分区失败');
        }
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('分区清理成功: ' + data.data.message);
            bootstrap.Modal.getInstance(document.getElementById('cleanupPartitionsModal')).hide();
            loadPartitionData();
        } else {
            throw new Error(data.error || '清理分区失败');
        }
        
    } catch (error) {
        console.error('清理分区失败:', error);
        showError('清理分区失败: ' + error.message);
    }
}

/**
 * 查看分区详情
 */
function viewPartitionDetails(partitionName) {
    // TODO: 实现分区详情查看功能
    showInfo('分区详情功能开发中: ' + partitionName);
}

/**
 * 删除分区
 */
async function deletePartition(partitionName) {
    if (!confirm(`确定要删除分区 "${partitionName}" 吗？此操作不可恢复！`)) {
        return;
    }
    
    try {
        // TODO: 实现分区删除API
        showError('分区删除功能开发中');
    } catch (error) {
        console.error('删除分区失败:', error);
        showError('删除分区失败: ' + error.message);
    }
}

/**
 * 显示加载状态
 */
function showLoadingState() {
    const tbody = document.getElementById('partitionsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
            </td>
        </tr>
    `;
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

/**
 * 格式化数字
 */
function formatNumber(num) {
    return new Intl.NumberFormat('zh-CN').format(num);
}

/**
 * 获取CSRF Token
 */
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

/**
 * 显示成功消息
 */
function showSuccess(message) {
    if (typeof toastr !== 'undefined') {
        toastr.success(message);
    } else {
        alert('成功: ' + message);
    }
}

/**
 * 显示错误消息
 */
function showError(message) {
    if (typeof toastr !== 'undefined') {
        toastr.error(message);
    } else {
        alert('错误: ' + message);
    }
}

/**
 * 显示信息消息
 */
function showInfo(message) {
    if (typeof toastr !== 'undefined') {
        toastr.info(message);
    } else {
        alert('信息: ' + message);
    }
}
