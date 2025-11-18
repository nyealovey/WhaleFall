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

    const { ready, selectOne } = helpers;

    const PartitionService = global.PartitionService;
    if (!PartitionService) {
        console.error('PartitionService 未初始化，无法加载分区管理脚本');
        return;
    }
    const partitionService = new PartitionService(global.httpU);
    let partitionStore = null;
    const partitionStoreSubscriptions = [];
    let modalsController = null;

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
        if (!modalsController) {
            console.error('PartitionsModals 未加载，模态事件不生效');
            return;
        }
        selectOne('#createPartitionBtn').on('click', (event) => modalsController.openCreate(event));
        selectOne('#cleanupPartitionsBtn').on('click', (event) => modalsController.openCleanup(event));
    }

    function initializeModals() {
        if (!global.PartitionsModals?.createController) {
            throw new Error('PartitionsModals 未加载，分区管理模态无法初始化');
        }
        modalsController = global.PartitionsModals.createController({
            document,
            UI: global.UI,
            toast: global.toast,
            service: partitionService,
            getStore: () => partitionStore,
            timeUtils: global.timeUtils,
            onReload: refreshPartitionData,
        });
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

    function refreshPartitionData() {
        if (partitionStore) {
            return partitionStore.actions.loadInfo({ silent: true });
        }
        return loadPartitionData();
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
        global.toast?.success?.('分区创建成功') || global.alert('分区创建成功');
        refreshPartitionData();
    }

    function handleCleanupSuccess() {
        global.toast?.success?.('分区清理成功') || global.alert('分区清理成功');
        refreshPartitionData();
    }
}

window.AdminPartitionsPage = {
    mount: function () {
        mountAdminPartitionsPage(window);
    },
};
