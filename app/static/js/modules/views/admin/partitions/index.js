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

    /**
     * 初始化分区 store，如缺失则退回直连服务。
     */
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

    /**
     * 订阅分区 store 事件。
     */
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
            const data = await partitionService.fetchInfo();
            if (data.success) {
                const payload = data?.data?.data ?? data?.data ?? data ?? {};
                updatePartitionStats(payload);
            } else {
                console.error('加载分区数据失败:', data);
                notifyStatsError(`加载分区数据失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('加载分区数据异常:', error);
            notifyStatsError(`加载分区数据异常: ${error.message}`);
        }
    }

    function refreshPartitionData(options = {}) {
        const loadPromise = partitionStore
            ? partitionStore.actions.loadInfo({ silent: options.silent ?? true })
            : loadPartitionData();
        return Promise.resolve(loadPromise).finally(() => {
            requestPartitionGridRefresh();
        });
    }

    function updatePartitionStats(data) {
        const stats = data && typeof data === 'object' ? data : {};
        selectOne('#totalPartitions').text(stats.total_partitions ?? 0);
        selectOne('#totalSize').text(stats.total_size ?? '0 B');
        selectOne('#totalRecords').text(stats.total_records ?? 0);
        selectOne('#partitionStatus').text(resolvePartitionStatusLabel(stats.status));
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
        updatePartitionStats(stats);
    }

    function handlePartitionLoading(payload) {
        const target = payload?.target;
        if (target === 'info') {
            selectOne('#partitionStatus').text('加载中...');
        }
    }

    function handlePartitionError(payload) {
        const target = payload?.meta?.target;
        if (target === 'info') {
            notifyStatsError(payload?.error?.message || '加载分区统计失败');
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

    function notifyStatsError(message) {
        if (global.toast?.error) {
            global.toast.error(message);
        } else {
            console.error(message);
        }
    }

    function requestPartitionGridRefresh() {
        global.dispatchEvent?.(new CustomEvent('partitionList:refresh'));
    }

    function resolvePartitionStatusLabel(status) {
        const normalized = (status || '').toLowerCase();
        if (normalized === 'healthy') {
            return '正常';
        }
        if (normalized === 'warning') {
            return '告警';
        }
        if (normalized) {
            return normalized;
        }
        return '正常';
    }
}

window.AdminPartitionsPage = {
    mount: function () {
        mountAdminPartitionsPage(window);
    },
};
