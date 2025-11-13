/**
 * 分区管理页面JavaScript
 * 提供分区创建、清理、状态监控等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    loadPartitionData();
    bindEvents();
});

/**
 * 绑定事件处理器
 */
function bindEvents() {
    // 创建分区按钮
    document.getElementById('createPartitionBtn').addEventListener('click', function () {
        showCreatePartitionModal();
    });

    // 清理分区按钮
    document.getElementById('cleanupPartitionsBtn').addEventListener('click', function () {
        showCleanupPartitionsModal();
    });

    // 确认创建分区
    document.getElementById('confirmCreatePartition').addEventListener('click', function () {
        createPartition();
    });

    // 确认清理分区
    document.getElementById('confirmCleanupPartitions').addEventListener('click', function () {
        cleanupPartitions();
    });
}

/**
 * 加载分区数据
 */
async function loadPartitionData() {
    try {
        showLoadingState();

        const data = await http.get('/partition/api/info');

        if (data.success) {
            const payload = data?.data?.data ?? data?.data ?? data ?? {};
            updatePartitionStats(payload);
            renderPartitionTable(Array.isArray(payload.partitions) ? payload.partitions : []);
        } else {
            console.error('加载分区数据失败:', data);
            showError('加载分区数据失败: ' + (data.error || '未知错误'));
        }

    } catch (error) {
        console.error('加载分区数据异常:', error);
        showError('加载分区数据异常: ' + error.message);
    } finally {
        hideLoadingState();
    }
}

/**
 * 更新分区统计信息
 */
function updatePartitionStats(data) {
    const stats = data && typeof data === 'object' ? data : {};
    document.getElementById('totalPartitions').textContent = stats.total_partitions ?? 0;
    document.getElementById('totalSize').textContent = stats.total_size ?? '0 B';
    document.getElementById('totalRecords').textContent = stats.total_records ?? 0;
    document.getElementById('partitionStatus').textContent = '正常';
}

/**
 * 渲染分区表格
 */
function renderPartitionTable(partitions) {
    const tbody = document.getElementById('partitionsTableBody');
    tbody.innerHTML = '';

    if (!partitions || partitions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="fas fa-inbox me-2"></i>
                    暂无分区数据
                </td>
            </tr>
        `;
        return;
    }

    partitions.forEach(partition => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <span class="badge bg-secondary">${partition.table_type || '未知'}</span>
            </td>
            <td>${partition.name || '-'}</td>
            <td>${partition.size || '0 B'}</td>
            <td>${partition.record_count || 0}</td>
            <td>
                <span class="badge bg-${getStatusColor(partition.status)}">
                    ${partition.status || '未知'}
                </span>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * 显示创建分区模态框
 */
function showCreatePartitionModal() {
    const modal = new bootstrap.Modal(document.getElementById('createPartitionModal'));
    modal.show();

    // 填充年份选项
    const yearSelect = document.getElementById('partitionYear');
    const monthSelect = document.getElementById('partitionMonth');
    // 使用统一的时间获取
    const now = timeUtils.getChinaTime();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    yearSelect.innerHTML = '<option value="">请选择年份</option>';

    for (let year = currentYear; year <= currentYear + 2; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year + '年';
        yearSelect.appendChild(option);
    }

    const updateMonthOptions = () => {
        const selectedYear = parseInt(yearSelect.value, 10);
        Array.from(monthSelect.options).forEach(option => {
            if (!option.value) {
                return;
            }
            const month = parseInt(option.value, 10);
            option.disabled = !Number.isNaN(selectedYear) && selectedYear === currentYear && month < currentMonth;
        });
    };

    yearSelect.removeEventListener('change', updateMonthOptions);
    yearSelect.addEventListener('change', updateMonthOptions);
    updateMonthOptions();
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
    const year = document.getElementById('partitionYear').value;
    const month = document.getElementById('partitionMonth').value;

    if (!year || !month) {
        alert('请选择年份和月份');
        return;
    }

    const date = `${year}-${month.padStart(2, '0')}-01`;

    try {
        const data = await http.post('/partition/api/create', { date: date });

        if (data.success) {
            alert('分区创建成功');
            bootstrap.Modal.getInstance(document.getElementById('createPartitionModal')).hide();
            loadPartitionData();
        } else {
            alert('分区创建失败: ' + (data.error || '未知错误'));
        }

    } catch (error) {
        console.error('创建分区异常:', error);
        alert('创建分区异常: ' + error.message);
    }
}

/**
 * 清理分区
 */
async function cleanupPartitions() {
    const retentionMonths = document.getElementById('retentionMonths').value;

    if (!retentionMonths || retentionMonths < 1) {
        alert('请输入有效的保留月数');
        return;
    }

    if (!confirm(`确定要清理${retentionMonths}个月之前的分区吗？此操作不可恢复！`)) {
        return;
    }

    try {
        const data = await http.post('/partition/api/cleanup', { retention_months: parseInt(retentionMonths) });

        if (data.success) {
            alert('分区清理成功');
            bootstrap.Modal.getInstance(document.getElementById('cleanupPartitionsModal')).hide();
            loadPartitionData();
        } else {
            alert('分区清理失败: ' + (data.error || '未知错误'));
        }

    } catch (error) {
        console.error('清理分区异常:', error);
        alert('清理分区异常: ' + error.message);
    }
}


/**
 * 显示加载状态
 */
function showLoadingState() {
    const tbody = document.getElementById('partitionsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
            </td>
        </tr>
    `;
}

/**
 * 隐藏加载状态
 */
function hideLoadingState() {
    // 加载状态会在renderPartitionTable中被替换
}

/**
 * 显示错误信息
 */
function showError(message) {
    const tbody = document.getElementById('partitionsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="5" class="text-center text-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </td>
        </tr>
    `;
}

/**
 * 根据分区状态获取对应的颜色类
 */
function getStatusColor(status) {
    switch (status) {
        case 'current':
            return 'success';  // 绿色 - 当前分区
        case 'past':
            return 'secondary';  // 灰色 - 过去分区
        case 'future':
            return 'info';  // 蓝色 - 未来分区
        default:
            return 'warning';  // 橙色 - 未知状态
    }
}

/**
 * 格式化文件大小
 */
function formatSize(mb) {
    return window.NumberFormat.formatBytesFromMB(mb, {
        precision: 2,
        fallback: '0 B',
    });
}

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数
