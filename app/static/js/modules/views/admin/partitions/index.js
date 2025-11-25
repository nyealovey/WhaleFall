/**
 * 挂载分区管理页面。
 *
 * 初始化分区管理页面的所有组件，包括分区 Store、模态框、
 * 事件绑定和数据加载。提供分区创建、清理、状态监控等功能。
 *
 * @param {Object} global - 全局 window 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountAdminPartitionsPage(window);
 */
function mountAdminPartitionsPage(global) {
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
     * 初始化分区 Store。
     *
     * 创建或复用 PartitionStore 实例，如果 Store 不可用则退回直连服务模式。
     * Store 初始化成功后会触发 'partitionStore:ready' 事件。
     *
     * @return {boolean} Store 是否初始化成功
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

    /**
     * 订阅 store 事件并记录，便于销毁。
     */
    function subscribeToPartitionStore(eventName, handler) {
        partitionStore.subscribe(eventName, handler);
        partitionStoreSubscriptions.push({ eventName, handler });
    }

    /**
     * 取消订阅并销毁 store。
     */
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

    /**
     * 绑定创建/清理按钮事件。
     */
    function bindEvents() {
        if (!modalsController) {
            console.error('PartitionsModals 未加载，模态事件不生效');
            return;
        }
        selectOne('#createPartitionBtn').on('click', (event) => modalsController.openCreate(event));
        selectOne('#cleanupPartitionsBtn').on('click', (event) => modalsController.openCleanup(event));
    }

    /**
     * 初始化分区操作模态。
     */
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

    /**
     * 直接从服务端加载分区统计。
     */
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

    /**
     * 刷新 store 并在完成后通知 grid 重载。
     */
    function refreshPartitionData(options = {}) {
        const loadPromise = partitionStore
            ? partitionStore.actions.loadInfo({ silent: options.silent ?? true })
            : loadPartitionData();
        return Promise.resolve(loadPromise).finally(() => {
            requestPartitionGridRefresh();
        });
    }

    /**
     * 更新仪表盘统计展示。
     */
    function updatePartitionStats(data) {
        const stats = data && typeof data === 'object' ? data : {};
        selectOne('#totalPartitions').text(stats.total_partitions ?? 0);
        selectOne('#totalSize').text(stats.total_size ?? '0 B');
        selectOne('#totalRecords').text(stats.total_records ?? 0);
        selectOne('#partitionStatus').text(resolvePartitionStatusLabel(stats.status));
    }

    /**
     * 将分区状态映射为颜色。
     */
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

    /**
     * store 通知：信息更新。
     */
    function handleInfoUpdated(payload) {
        const stats = payload?.stats || payload?.state?.stats || {};
        updatePartitionStats(stats);
    }

    /**
     * store 通知：加载状态变更。
     */
    function handlePartitionLoading(payload) {
        const target = payload?.target;
        if (target === 'info') {
            selectOne('#partitionStatus').text('加载中...');
        }
    }

    /**
     * store 通知：操作失败。
     */
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

    /**
     * 分区创建成功后的提示与刷新。
     */
    function handleCreateSuccess() {
        global.toast?.success?.('分区创建成功') || global.alert('分区创建成功');
        refreshPartitionData();
    }

    /**
     * 分区清理成功后的提示与刷新。
     */
    function handleCleanupSuccess() {
        global.toast?.success?.('分区清理成功') || global.alert('分区清理成功');
        refreshPartitionData();
    }

    /**
     * 显示统计相关错误。
     */
    function notifyStatsError(message) {
        if (global.toast?.error) {
            global.toast.error(message);
        } else {
            console.error(message);
        }
    }

    /**
     * 发出自定义事件，通知列表刷新。
     */
    function requestPartitionGridRefresh() {
        global.dispatchEvent?.(new CustomEvent('partitionList:refresh'));
    }

    /**
     * 将状态码转为文案。
     */
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
