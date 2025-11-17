function mountAdminPartitionsPage(global) {
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
    let partitionStore = null;
    const partitionStoreSubscriptions = [];
    let createPartitionModal = null;
    let cleanupPartitionsModal = null;

    ready(() => {
        initializeModals();
        const initialized = initializePartitionStore();
        if (!initialized) {
            loadPartitionData();
        }
        bindEvents();
    });

    function initializePartitionStore() {
        if (!global.createPartitionStore) {
            console.warn('createPartitionStore 未加载，回退到直接调用服务');
            return false;
        }
        const reusedStore = Boolean(global.PartitionStoreInstance);
        if (reusedStore) {
            partitionStore = global.PartitionStoreInstance;
        } else {
            try {
                partitionStore = global.createPartitionStore({
                    service: partitionService,
                    emitter: global.mitt ? global.mitt() : null,
                });
                global.PartitionStoreInstance = partitionStore;
            } catch (error) {
                console.error('初始化 PartitionStore 失败:', error);
                partitionStore = null;
                return false;
            }
        }
        global.dispatchEvent?.(
            new CustomEvent('partitionStore:ready', {
                detail: { store: partitionStore },
            }),
        );
        bindPartitionStoreEvents();
        const loadPromise = reusedStore
            ? partitionStore.actions.loadInfo({ silent: true })
            : partitionStore.init();
        loadPromise.catch((error) => {
            console.warn('PartitionStore 加载失败，回退到直接加载', error);
            loadPartitionData();
        });
        global.addEventListener('beforeunload', teardownPartitionStore, { once: true });
        return true;
    }

    function bindPartitionStoreEvents() {
        if (!partitionStore) {
            return;
        }
        subscribeToPartitionStore('partitions:infoUpdated', handleInfoUpdated);
        subscribeToPartitionStore('partitions:loading', handlePartitionLoading);
        subscribeToPartitionStore('partitions:error', handlePartitionError);
        subscribeToPartitionStore('partitions:create:success', handleCreateSuccess);
        subscribeToPartitionStore('partitions:cleanup:success', handleCleanupSuccess);
    }

    function subscribeToPartitionStore(eventName, handler) {
        partitionStore.subscribe(eventName, handler);
        partitionStoreSubscriptions.push({ eventName, handler });
    }

    function teardownPartitionStore() {
        if (!partitionStore) {
            return;
        }
        partitionStoreSubscriptions.forEach(({ eventName, handler }) => {
            partitionStore.unsubscribe(eventName, handler);
        });
        partitionStoreSubscriptions.length = 0;
        partitionStore.destroy?.();
        partitionStore = null;
    }

    function bindEvents() {
        selectOne('#createPartitionBtn').on('click', openCreatePartitionModal);
        selectOne('#cleanupPartitionsBtn').on('click', openCleanupPartitionsModal);
    }

    function initializeModals() {
        const factory = global.UI?.createModal;
        if (!factory) {
            throw new Error('UI.createModal 未加载，分区管理模态无法初始化');
        }
        createPartitionModal = factory({
            modalSelector: '#createPartitionModal',
            onOpen: prepareCreatePartitionForm,
            onConfirm: () => createPartition(),
        });
        cleanupPartitionsModal = factory({
            modalSelector: '#cleanupPartitionsModal',
            onConfirm: () => cleanupPartitions(),
        });
    }

    function ensureModalInstance(key) {
        const map = {
            create: createPartitionModal,
            cleanup: cleanupPartitionsModal,
        };
        const instance = map[key];
        if (!instance) {
            throw new Error(`分区管理模态未初始化: ${key}`);
        }
        return instance;
    }

    async function loadPartitionData() {
        if (partitionStore) {
            return partitionStore.actions.loadInfo();
        }
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

    function openCreatePartitionModal(event) {
        event?.preventDefault?.();
        prepareCreatePartitionForm();
        ensureModalInstance('create').open();
    }

    function prepareCreatePartitionForm() {
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

    function openCleanupPartitionsModal(event) {
        event?.preventDefault?.();
        ensureModalInstance('cleanup').open();
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

        const executor = partitionStore
            ? partitionStore.actions.createPartition({ date })
            : partitionService.createPartition({ date });
        try {
            const data = await executor;
            if (partitionStore || data.success) {
                global.alert('分区创建成功');
                ensureModalInstance('create').close();
                if (!partitionStore) {
                    loadPartitionData();
                }
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

        const executor = partitionStore
            ? partitionStore.actions.cleanupPartitions({ retention_months: parseInt(retentionMonths, 10) })
            : partitionService.cleanupPartitions({
                  retention_months: parseInt(retentionMonths, 10),
              });
        try {
            const data = await executor;
            if (partitionStore || data.success) {
                global.alert('分区清理成功');
                ensureModalInstance('cleanup').close();
                if (!partitionStore) {
                    loadPartitionData();
                }
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

    function handleInfoUpdated(payload) {
        const stats = payload?.stats || payload?.state?.stats || {};
        const partitions = payload?.partitions || payload?.state?.partitions || [];
        updatePartitionStats(stats);
        renderPartitionTable(partitions);
    }

    function handlePartitionLoading(payload) {
        const target = payload?.target;
        const loading = payload?.loading || {};
        if (target === 'info') {
            if (loading.info) {
                showLoadingState();
            }
        }
    }

    function handlePartitionError(payload) {
        const target = payload?.meta?.target;
        if (target === 'info') {
            showError(payload?.error?.message || '加载分区数据失败');
        } else if (target === 'create') {
            global.alert(payload?.error?.message || '创建分区失败');
        } else if (target === 'cleanup') {
            global.alert(payload?.error?.message || '清理分区失败');
        } else if (target === 'metrics') {
            console.error('分区核心指标加载失败:', payload?.error);
        }
    }

    function handleCreateSuccess() {
        ensureModalInstance('create').close();
        global.toast?.success?.('分区创建成功') || global.alert('分区创建成功');
    }

    function handleCleanupSuccess() {
        ensureModalInstance('cleanup').close();
        global.toast?.success?.('分区清理成功') || global.alert('分区清理成功');
    }
}

window.AdminPartitionsPage = {
    mount: function () {
        mountAdminPartitionsPage(window);
    },
};
