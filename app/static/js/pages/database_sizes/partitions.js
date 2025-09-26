// app/static/js/pages/database_sizes/partitions.js

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initializePartitionsPage();
    
    // 绑定事件
    bindEvents();
    
    // 加载数据
    loadPartitionData();
    
    // 加载聚合数据
    loadAggregationData();
});

/**
 * 初始化分区管理页面
 */
function initializePartitionsPage() {
    console.log('初始化分区管理页面...');
    
    // 初始化年份选择器
    initializeYearSelector();
    
    // 设置默认月份为下个月
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    document.getElementById('partitionYear').value = nextMonth.getFullYear();
    document.getElementById('partitionMonth').value = nextMonth.getMonth() + 1;
}

/**
 * 初始化年份选择器
 */
function initializeYearSelector() {
    const yearSelect = document.getElementById('partitionYear');
    const currentYear = new Date().getFullYear();
    
    // 添加过去2年到未来2年的选项
    for (let year = currentYear - 2; year <= currentYear + 2; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year + '年';
        yearSelect.appendChild(option);
    }
}

/**
 * 绑定事件处理器
 */
function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadPartitionData();
        loadAggregationData();
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
    
    // 聚合数据表搜索
    document.getElementById('searchAggregationTable').addEventListener('input', function() {
        filterAggregationTable();
    });
    
    // 聚合数据表周期类型筛选
    document.getElementById('periodTypeFilter').addEventListener('change', function() {
        loadAggregationData();
    });
    
    // 聚合数据表排序
    document.getElementById('sortAggregationTable').addEventListener('change', function() {
        sortAggregationTable();
    });
    
    // 聚合数据表分页
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('page-link')) {
            e.preventDefault();
            const page = parseInt(e.target.getAttribute('data-page'));
            if (page && page !== window.currentAggregationPage) {
                goToAggregationPage(page);
            }
        }
    });
    
    // 上一页/下一页按钮
    document.getElementById('prevPage').addEventListener('click', function(e) {
        e.preventDefault();
        if (window.currentAggregationPage > 1) {
            goToAggregationPage(window.currentAggregationPage - 1);
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', function(e) {
        e.preventDefault();
        if (window.currentAggregationPage < window.totalAggregationPages) {
            goToAggregationPage(window.currentAggregationPage + 1);
        }
    });
}

/**
 * 加载分区数据
 */
async function loadPartitionData() {
    try {
        console.log('开始加载分区数据...');
        showLoadingState();
        
        // 获取CSRF token
        const csrfToken = getCSRFToken();
        console.log('CSRF Token:', csrfToken ? '已获取' : '未获取');
        
        // 并行加载分区信息和状态
        const [partitionInfoResponse, partitionStatusResponse] = await Promise.all([
            fetch('/partition-management/partitions?api=true', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            }),
            fetch('/partition-management/partitions/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
        ]);
        
        console.log('分区信息响应状态:', partitionInfoResponse.status);
        console.log('分区状态响应状态:', partitionStatusResponse.status);
        
        if (!partitionInfoResponse.ok) {
            const errorText = await partitionInfoResponse.text();
            console.error('分区信息请求失败:', errorText);
            throw new Error(`分区信息请求失败: ${partitionInfoResponse.status} ${errorText}`);
        }
        
        if (!partitionStatusResponse.ok) {
            const errorText = await partitionStatusResponse.text();
            console.error('分区状态请求失败:', errorText);
            throw new Error(`分区状态请求失败: ${partitionStatusResponse.status} ${errorText}`);
        }
        
        const partitionInfo = await partitionInfoResponse.json();
        const partitionStatus = await partitionStatusResponse.json();
        
        console.log('分区信息响应:', partitionInfo);
        console.log('分区状态响应:', partitionStatus);
        
        if (partitionInfo.success && partitionStatus.success) {
            updatePartitionOverview(partitionStatus.data);
            updatePartitionsTable(partitionInfo.data.partitions);
            console.log('分区数据加载成功');
        } else {
            const errorMsg = partitionInfo.error || partitionStatus.error || '加载分区数据失败';
            console.error('分区数据加载失败:', errorMsg);
            throw new Error(errorMsg);
        }
        
    } catch (error) {
        console.error('加载分区数据失败:', error);
        showError('加载分区数据失败: ' + error.message);
        
        // 显示错误状态
        const tbody = document.getElementById('partitionsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>加载失败: ${error.message}
                    </td>
                </tr>
            `;
        }
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
    const partitionYear = document.getElementById('partitionYear').value;
    const partitionMonth = document.getElementById('partitionMonth').value;
    
    if (!partitionYear || !partitionMonth) {
        showError('请选择年份和月份');
        return;
    }
    
    // 构造日期（使用该月的第一天）
    const partitionDate = `${partitionYear}-${partitionMonth.padStart(2, '0')}-01`;
    
    try {
        const response = await fetch('/partition-management/partitions/create', {
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
        const response = await fetch('/partition-management/partitions/cleanup', {
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
 * 直接使用本地实现，避免循环调用
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * 显示成功消息
 */
function showSuccess(message) {
    try {
        if (typeof toastr !== 'undefined') {
            toastr.success(message);
        } else {
            console.log('成功: ' + message);
            alert('成功: ' + message);
        }
    } catch (error) {
        console.error('显示成功消息失败:', error);
        alert('成功: ' + message);
    }
}

/**
 * 显示错误消息
 */
function showError(message) {
    try {
        if (typeof toastr !== 'undefined') {
            toastr.error(message);
        } else {
            console.error('错误: ' + message);
            alert('错误: ' + message);
        }
    } catch (error) {
        console.error('显示错误消息失败:', error);
        alert('错误: ' + message);
    }
}

/**
 * 显示信息消息
 */
function showInfo(message) {
    try {
        if (typeof toastr !== 'undefined') {
            toastr.info(message);
        } else {
            console.log('信息: ' + message);
            alert('信息: ' + message);
        }
    } catch (error) {
        console.error('显示信息消息失败:', error);
        alert('信息: ' + message);
    }
}

// ==================== 聚合数据表功能 ====================

// 聚合数据表全局变量
window.currentAggregationPage = 1;
window.aggregationPageSize = 20;
window.totalAggregationRecords = 0;
window.totalAggregationPages = 0;
window.aggregationData = [];
window.filteredAggregationData = [];

/**
 * 加载聚合数据
 */
async function loadAggregationData() {
    try {
        console.log('开始加载最新聚合数据...');
        showAggregationLoadingState();
        
        // 获取选中的周期类型
        const periodTypeFilter = document.getElementById('periodTypeFilter');
        const selectedPeriodType = periodTypeFilter ? periodTypeFilter.value : 'daily';
        
        console.log('选中的周期类型:', selectedPeriodType);
        
        const response = await fetch('/database-sizes/aggregations/latest?api=true');
        const data = await response.json();
        
        if (response.ok) {
            console.log('最新聚合数据响应:', data);
            
            // 根据选中的周期类型筛选数据
            let filteredData = [];
            if (data.data && data.data[selectedPeriodType]) {
                filteredData = data.data[selectedPeriodType];
            }
            
            window.aggregationData = filteredData;
            window.filteredAggregationData = [...window.aggregationData];
            window.totalAggregationRecords = filteredData.length;
            window.totalAggregationPages = 1; // 最新数据不需要分页
            
            console.log(`开始渲染${selectedPeriodType}聚合数据表格...`);
            renderLatestAggregationTable(filteredData, data.summary);
            console.log('聚合数据加载完成');
        } else {
            console.error('API响应失败:', response.status, data);
            showError('加载聚合数据失败: ' + data.error);
        }
    } catch (error) {
        console.error('加载聚合数据时出错:', error);
        console.error('错误类型:', typeof error);
        console.error('错误消息:', error.message);
        console.error('错误堆栈:', error.stack);
        showError('加载聚合数据时出错: ' + (error.message || '未知错误'));
    }
}

/**
 * 显示聚合数据表加载状态
 */
function showAggregationLoadingState() {
    const tbody = document.getElementById('aggregationTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="9" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
            </td>
        </tr>
    `;
}

/**
 * 渲染最新聚合数据表
 */
function renderLatestAggregationTable(data, summary) {
    const tbody = document.getElementById('aggregationTableBody');
    tbody.innerHTML = '';
    
    // 获取当前选中的周期类型
    const periodTypeFilter = document.getElementById('periodTypeFilter');
    const selectedPeriodType = periodTypeFilter ? periodTypeFilter.value : 'daily';
    const periodTypeNames = {
        'daily': '日',
        'weekly': '周', 
        'monthly': '月',
        'quarterly': '季'
    };
    const currentPeriodTypeName = periodTypeNames[selectedPeriodType] || '日';
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="empty-state">
                        <i class="fas fa-chart-bar"></i>
                        <h5>暂无${currentPeriodTypeName}聚合数据</h5>
                        <p>没有找到最新的${currentPeriodTypeName}聚合数据，请尝试其他周期类型或点击"聚合今日数据"按钮生成数据</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // 添加汇总信息行
    if (summary) {
        const summaryRow = `
            <tr class="table-info">
                <td colspan="9" class="text-center">
                    <strong>最新聚合数据汇总</strong> | 
                    日: ${summary.daily} | 
                    周: ${summary.weekly} | 
                    月: ${summary.monthly} | 
                    季度: ${summary.quarterly}
                </td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', summaryRow);
    }
    
    // 按周期类型分组显示
    const periodTypes = ['daily', 'weekly', 'monthly', 'quarterly'];
    const periodLabels = {
        'daily': '日',
        'weekly': '周', 
        'monthly': '月',
        'quarterly': '季度'
    };
    
    periodTypes.forEach(periodType => {
        const periodData = data.filter(item => item.period_type === periodType);
        if (periodData.length > 0) {
            // 添加周期类型标题行
            const titleRow = `
                <tr class="table-secondary">
                    <td colspan="9" class="text-center">
                        <strong>${periodLabels[periodType]}聚合数据 (${periodData.length}条)</strong>
                    </td>
                </tr>
            `;
            tbody.insertAdjacentHTML('beforeend', titleRow);
            
            // 显示该周期的数据
            periodData.forEach(item => {
                const row = createAggregationTableRow(item);
                tbody.insertAdjacentHTML('beforeend', row);
            });
        }
    });
}

/**
 * 渲染聚合数据表（保留原函数用于兼容性）
 */
function renderAggregationTable(data) {
    const tbody = document.getElementById('aggregationTableBody');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <div class="empty-state">
                        <i class="fas fa-chart-bar"></i>
                        <h5>暂无数据</h5>
                        <p>没有找到符合条件的聚合数据</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    data.forEach(item => {
        const row = createAggregationTableRow(item);
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

/**
 * 创建聚合数据表行
 */
function createAggregationTableRow(item) {
    const calculatedAt = new Date(item.calculated_at).toLocaleString('zh-CN');
    const periodRange = `${item.period_start} 至 ${item.period_end}`;
    
    return `
        <tr>
            <td>
                <span class="badge bg-primary">${getPeriodTypeLabel(item.period_type)}</span>
            </td>
            <td>
                <span class="instance-name">${item.instance.name}</span>
            </td>
            <td>
                <span class="database-name" title="${item.database_name}">${wrapDatabaseName(item.database_name)}</span>
            </td>
            <td>
                <span class="period-range">${periodRange}</span>
            </td>
            <td>
                <span class="size-display">${formatSizeFromMB(item.avg_size_mb)}</span>
            </td>
            <td>
                <span class="size-display">${formatSizeFromMB(item.max_size_mb)}</span>
            </td>
            <td>
                <span class="size-display">${formatSizeFromMB(item.min_size_mb)}</span>
            </td>
            <td>
                <span class="badge bg-info">${item.data_count}</span>
            </td>
            <td>
                <small class="text-muted">${calculatedAt}</small>
            </td>
        </tr>
    `;
}

/**
 * 获取周期类型标签
 */
function getPeriodTypeLabel(periodType) {
    const labels = {
        'daily': '日',
        'weekly': '周',
        'monthly': '月',
        'quarterly': '季度'
    };
    return labels[periodType] || periodType;
}

/**
 * 包装数据库名称（处理长名称）
 */
function wrapDatabaseName(name) {
    if (name.length <= 15) {
        return name;
    }
    return name.substring(0, 12) + '...';
}

/**
 * 格式化大小（从MB）
 */
function formatSizeFromMB(mb) {
    if (mb === null || mb === undefined) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = mb * 1024 * 1024; // 转换为字节
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * 过滤聚合数据表
 */
function filterAggregationTable() {
    const searchTerm = document.getElementById('searchAggregationTable').value.toLowerCase();
    
    if (searchTerm === '') {
        window.filteredAggregationData = [...window.aggregationData];
    } else {
        window.filteredAggregationData = window.aggregationData.filter(item => 
            item.instance.name.toLowerCase().includes(searchTerm) ||
            item.database_name.toLowerCase().includes(searchTerm) ||
            item.period_type.toLowerCase().includes(searchTerm)
        );
    }
    
    window.currentAggregationPage = 1;
    updateAggregationPagination();
    renderLatestAggregationTable(window.filteredAggregationData, null);
}

/**
 * 排序聚合数据表
 */
function sortAggregationTable() {
    const sortBy = document.getElementById('sortAggregationTable').value;
    
    window.filteredAggregationData.sort((a, b) => {
        switch (sortBy) {
            case 'instance_name':
                return a.instance.name.localeCompare(b.instance.name);
            case 'database_name':
                return a.database_name.localeCompare(b.database_name);
            case 'avg_size_mb':
                return b.avg_size_mb - a.avg_size_mb;
            case 'max_size_mb':
                return b.max_size_mb - a.max_size_mb;
            default:
                return 0;
        }
    });
    
    window.currentAggregationPage = 1;
    updateAggregationPagination();
    renderLatestAggregationTable(window.filteredAggregationData, null);
}

/**
 * 获取当前页数据
 */
function getCurrentPageData() {
    const start = (window.currentAggregationPage - 1) * window.aggregationPageSize;
    const end = start + window.aggregationPageSize;
    return window.filteredAggregationData.slice(start, end);
}

/**
 * 跳转到指定页
 */
function goToAggregationPage(page) {
    if (page < 1 || page > window.totalAggregationPages || page === window.currentAggregationPage) {
        return;
    }
    window.currentAggregationPage = page;
    renderAggregationTable(getCurrentPageData());
    updateAggregationPagination();
}

/**
 * 更新聚合数据表分页
 */
function updateAggregationPagination() {
    // 最新聚合数据不需要分页，显示所有数据
    const total = window.filteredAggregationData.length;
    
    document.getElementById('paginationStart').textContent = total > 0 ? 1 : 0;
    document.getElementById('paginationEnd').textContent = total;
    document.getElementById('paginationTotal').textContent = total;
    
    // 禁用分页按钮
    document.getElementById('prevPage').classList.add('disabled');
    document.getElementById('nextPage').classList.add('disabled');
    
    // 隐藏分页按钮
    const paginationNav = document.getElementById('paginationNav');
    const pageButtons = paginationNav.querySelectorAll('.page-item:not(#prevPage):not(#nextPage)');
    pageButtons.forEach(btn => btn.remove());
}

/**
 * 生成聚合数据表分页按钮
 */
function generateAggregationPaginationButtons() {
    const paginationNav = document.getElementById('paginationNav');
    const pageButtons = paginationNav.querySelectorAll('.page-item:not(#prevPage):not(#nextPage)');
    pageButtons.forEach(btn => btn.remove());
    
    const maxVisiblePages = 5;
    let startPage = Math.max(1, window.currentAggregationPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(window.totalAggregationPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    const prevPageElement = document.getElementById('prevPage');
    for (let i = startPage; i <= endPage; i++) {
        const pageItem = document.createElement('li');
        pageItem.className = `page-item ${i === window.currentAggregationPage ? 'active' : ''}`;
        pageItem.id = `page${i}`;
        pageItem.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
        prevPageElement.insertAdjacentElement('afterend', pageItem);
    }
}
