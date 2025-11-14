(function (global) {
    /**
     * 分区管理页面 JavaScript
     * 提供分区创建、清理、状态监控等功能
     */
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载分区管理脚本');
        return;
    }

    const { ready, selectOne, from } = helpers;

    const PartitionService = global.PartitionService;
    if (!PartitionService) {
        console.error('PartitionService 未初始化，无法加载分区管理脚本');
        return;
    }
    const partitionService = new PartitionService(global.httpU);

    ready(() => {
        loadPartitionData();
        bindEvents();
    });

    function bindEvents() {
        selectOne('#createPartitionBtn').on('click', showCreatePartitionModal);
        selectOne('#cleanupPartitionsBtn').on('click', showCleanupPartitionsModal);
        selectOne('#confirmCreatePartition').on('click', createPartition);
        selectOne('#confirmCleanupPartitions').on('click', cleanupPartitions);
    }

    async function loadPartitionData() {
        try {
            showLoadingState();

            const data = await partitionService.fetchInfo();

            if (data.success) {
                const payload = data?.data?.data ?? data?.data ?? data ?? {};
                updatePartitionStats(payload);
                renderPartitionTable(Array.isArray(payload.partitions) ? payload.partitions : []);
            } else {
                console.error('加载分区数据失败:', data);
                showError(`加载分区数据失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('加载分区数据异常:', error);
            showError(`加载分区数据异常: ${error.message}`);
        } finally {
            hideLoadingState();
        }
    }

    function updatePartitionStats(data) {
        const stats = data && typeof data === 'object' ? data : {};
        selectOne('#totalPartitions').text(stats.total_partitions ?? 0);
        selectOne('#totalSize').text(stats.total_size ?? '0 B');
        selectOne('#totalRecords').text(stats.total_records ?? 0);
        selectOne('#partitionStatus').text('正常');
    }

    function renderPartitionTable(partitions) {
        const tbodyWrapper = selectOne('#partitionsTableBody');
        if (!tbodyWrapper.length) {
            return;
        }
        const tbody = tbodyWrapper.first();
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

        partitions.forEach((partition) => {
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

    function showCreatePartitionModal() {
        const modalElement = selectOne('#createPartitionModal').first();
        if (!modalElement || !global.bootstrap?.Modal) {
            return;
        }
        const modal = global.bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();

        const yearSelect = selectOne('#partitionYear').first();
        const monthSelect = selectOne('#partitionMonth').first();
        if (!yearSelect || !monthSelect) {
            return;
        }

        const now = global.timeUtils.getChinaTime();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;

        yearSelect.innerHTML = '<option value="">请选择年份</option>';
        for (let year = currentYear; year <= currentYear + 2; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `${year}年`;
            yearSelect.appendChild(option);
        }

        const updateMonthOptions = () => {
            const selectedYear = parseInt(yearSelect.value, 10);
            Array.from(monthSelect.options).forEach((option) => {
                if (!option.value) {
                    return;
                }
                const month = parseInt(option.value, 10);
                option.disabled = !Number.isNaN(selectedYear) && selectedYear === currentYear && month < currentMonth;
            });
        };

        from(yearSelect).off('change', updateMonthOptions);
        from(yearSelect).on('change', updateMonthOptions);
        updateMonthOptions();
    }

    function showCleanupPartitionsModal() {
        const modalElement = selectOne('#cleanupPartitionsModal').first();
        if (!modalElement || !global.bootstrap?.Modal) {
            return;
        }
        const modal = global.bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }

    async function createPartition() {
        const monthElement = selectOne('#partitionMonth').first();
        const yearElement = selectOne('#partitionYear').first();
        const selectedYear = yearElement ? yearElement.value : '';
        const selectedMonth = monthElement ? monthElement.value : '';

        if (!selectedYear || !selectedMonth) {
            global.alert('请选择年份和月份');
            return;
        }

        const date = `${selectedYear}-${selectedMonth.padStart(2, '0')}-01`;

        try {
        const data = await partitionService.createPartition({ date });
            if (data.success) {
                global.alert('分区创建成功');
                const modal = global.bootstrap.Modal.getInstance(selectOne('#createPartitionModal').first());
                modal?.hide();
                loadPartitionData();
            } else {
                global.alert(`分区创建失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('创建分区异常:', error);
            global.alert(`创建分区异常: ${error.message}`);
        }
    }

    async function cleanupPartitions() {
        const retentionInput = selectOne('#retentionMonths').first();
        const retentionMonths = retentionInput ? Number(retentionInput.value) : 0;

        if (!retentionMonths || retentionMonths < 1) {
            global.alert('请输入有效的保留月数');
            return;
        }

        if (!global.confirm(`确定要清理${retentionMonths}个月之前的分区吗？此操作不可恢复！`)) {
            return;
        }

        try {
            const data = await partitionService.cleanupPartitions({
                retention_months: parseInt(retentionMonths, 10),
            });
            if (data.success) {
                global.alert('分区清理成功');
                const modal = global.bootstrap.Modal.getInstance(selectOne('#cleanupPartitionsModal').first());
                modal?.hide();
                loadPartitionData();
            } else {
                global.alert(`分区清理失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('清理分区异常:', error);
            global.alert(`清理分区异常: ${error.message}`);
        }
    }

    function showLoadingState() {
        const tbody = selectOne('#partitionsTableBody');
        if (!tbody.length) {
            return;
        }
        tbody.html(`
            <tr>
                <td colspan="7" class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                </td>
            </tr>
        `);
    }

    function hideLoadingState() {
        // 渲染函数会覆盖加载状态
    }

    function showError(message) {
        const tbody = selectOne('#partitionsTableBody');
        if (!tbody.length) {
            return;
        }
        tbody.html(`
            <tr>
                <td colspan="5" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </td>
            </tr>
        `);
    }

    function getStatusColor(status) {
        switch (status) {
            case 'current':
                return 'success';
            case 'past':
                return 'secondary';
            case 'future':
                return 'info';
            default:
                return 'warning';
        }
    }

    global.formatPartitionSize = function formatSize(mb) {
        return global.NumberFormat.formatBytesFromMB(mb, {
            precision: 2,
            fallback: '0 B',
        });
    };

    global.createPartition = createPartition;
    global.cleanupPartitions = cleanupPartitions;
})(window);
