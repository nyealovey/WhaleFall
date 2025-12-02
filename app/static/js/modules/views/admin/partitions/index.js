/**
 * 挂载分区管理页面。
 *
 * 初始化分区管理页面的所有组件，包括分区 Store、模态框、
 * 事件绑定和数据加载。提供分区创建、清理、状态监控等功能。
 *
 * @param {Window} global 全局 window 对象。
 * @returns {void}
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
     * @param {Object} [options={}] 可选配置。
     * @param {Window} [options.windowRef=global] 自定义上下文。
     * @returns {boolean} Store 是否初始化成功。
     */
    function initializePartitionStore(options = {}) {
        const host = options.windowRef || global;
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
     *
     * @param {Object} [store=partitionStore] PartitionStore 实例。
     * @returns {void}
     */
    function bindPartitionStoreEvents(store = partitionStore) {
        if (!store) {
            return;
        }
        subscribeToPartitionStore(store, 'partitions:infoUpdated', handleInfoUpdated);
        subscribeToPartitionStore(store, 'partitions:loading', handlePartitionLoading);
        subscribeToPartitionStore(store, 'partitions:error', handlePartitionError);
        subscribeToPartitionStore(store, 'partitions:create:success', handleCreateSuccess);
        subscribeToPartitionStore(store, 'partitions:cleanup:success', handleCleanupSuccess);
    }

    /**
     * 订阅 store 事件并记录，便于销毁。
     *
     * @param {Object} store PartitionStore 实例。
     * @param {string} eventName 事件名。
     * @param {Function} handler 回调。
     * @returns {void}
     */
    function subscribeToPartitionStore(store, eventName, handler) {
        store.subscribe(eventName, handler);
        partitionStoreSubscriptions.push({ store, eventName, handler });
    }

    /**
     * 取消订阅并销毁 store。
     *
     * @param {Object} [store=partitionStore] 待销毁的 PartitionStore。
     * @returns {void}
     */
    function teardownPartitionStore(store = partitionStore) {
        if (!store) {
            return;
        }
        partitionStoreSubscriptions.forEach(({ eventName, handler }) => {
            store.unsubscribe(eventName, handler);
        });
        partitionStoreSubscriptions.length = 0;
        store.destroy?.();
        if (store === partitionStore) {
            partitionStore = null;
        }
    }

    /**
     * 绑定创建/清理按钮事件。
     *
     * @param {Object} [controller=modalsController] 模态控制器。
     * @returns {void}
     */
    function bindEvents(controller = modalsController) {
        if (!controller) {
            console.error('PartitionsModals 未加载，模态事件不生效');
            return;
        }
        selectOne('#createPartitionBtn').on('click', (event) => controller.openCreate(event));
        selectOne('#cleanupPartitionsBtn').on('click', (event) => controller.openCleanup(event));
    }

    /**
     * 初始化分区操作模态。
     *
     * @param {Object} [options={}] 可选配置。
     * @returns {void}
     */
    function initializeModals(options = {}) {
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
     *
     * @returns {Promise<void>} 完成后 resolve。
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
     *
     * @param {Object} [options={}] 配置。
     * @param {boolean} [options.silent=true] 是否静默加载。
     * @returns {Promise<void>} 刷新 promise。
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
     *
     * @param {Object} data 统计数据。
     * @returns {void}
     */
    function updatePartitionStats(data) {
        const stats = data && typeof data === 'object' ? data : {};

        setStatCard('total_partitions', {
            value: formatNumber(stats.total_partitions ?? 0),
        });
        setStatCard('total_size', {
            value: stats.total_size || '0 B',
        });
        setStatCard('total_records', {
            value: formatNumber(stats.total_records ?? 0),
        });

        const healthMeta = resolvePartitionStatusMeta(stats.status);
        setStatCard('health', {
            value: healthMeta.text,
            metaHtml: renderStatusPill(healthMeta.text, healthMeta.tone, healthMeta.icon),
        });
    }

    global.formatPartitionSize = function formatSize(mb) {
        return global.NumberFormat.formatBytesFromMB(mb, {
            precision: 2,
            fallback: '0 B',
        });
    };

    /**
     * store 通知：信息更新。
     *
     * @param {Object} payload store 事件负载。
     * @returns {void}
     */
    function handleInfoUpdated(payload) {
        const stats = payload?.stats || payload?.state?.stats || {};
        updatePartitionStats(stats);
    }

    /**
     * store 通知：加载状态变更。
     *
     * @param {Object} payload store 事件负载。
     * @returns {void}
     */
    function handlePartitionLoading(payload) {
        const target = payload?.target;
        if (target === 'info') {
            setStatCard('health', {
                value: '加载中',
                metaHtml: renderStatusPill('同步中', 'muted', 'fa-spinner fa-spin'),
            });
        }
    }

    /**
     * store 通知：操作失败。
     *
     * @param {Object} payload store 事件负载。
     * @returns {void}
     */
    function handlePartitionError(payload) {
        const target = payload?.meta?.target;
        if (target === 'info') {
            const message = payload?.error?.message || '加载分区统计失败';
            notifyStatsError(message);
            setStatCard('health', {
                value: '异常',
                metaHtml: renderStatusPill(message, 'danger', 'fa-exclamation-triangle'),
            });
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
     *
     * @param {Object} [payload] 事件负载。
     * @returns {void}
     */
    function handleCreateSuccess(payload) {
        const message = payload?.message || '分区创建成功';
        global.toast?.success?.(message) || global.alert(message);
        refreshPartitionData();
    }

    /**
     * 分区清理成功后的提示与刷新。
     *
     * @param {Object} [payload] 事件负载。
     * @returns {void}
     */
    function handleCleanupSuccess(payload) {
        const message = payload?.message || '分区清理成功';
        global.toast?.success?.(message) || global.alert(message);
        refreshPartitionData();
    }

    /**
     * 显示统计相关错误。
     *
     * @param {string} message 提示文案。
     * @returns {void}
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
     *
     * @param {Window|EventTarget} [target=global] 事件目标。
     * @returns {void}
     */
    function requestPartitionGridRefresh(target = global) {
        target.dispatchEvent?.(new CustomEvent('partitionList:refresh'));
    }

    /**
     * 将状态码转为文案。
     *
     * @param {string} status 状态码。
     * @returns {string} 中文描述。
     */
    function setStatCard(key, payload) {
        const wrapper = selectOne(`[data-stat="${key}"]`);
        if (!wrapper.length) {
            return;
        }
        const valueNode = wrapper.find('[data-stat-value]');
        if (valueNode.length && payload?.value !== undefined) {
            valueNode.text(payload.value);
        }
        const metaNode = wrapper.find('[data-stat-meta]');
        if (metaNode.length) {
            if (payload?.metaHtml !== undefined) {
                metaNode.html(payload.metaHtml);
            } else if (payload?.meta !== undefined) {
                metaNode.text(payload.meta);
            } else {
                metaNode.text('');
            }
        }
    }

    function resolvePartitionStatusMeta(status) {
        const normalized = (status || '').toLowerCase();
        if (normalized === 'healthy') {
            return { text: '正常', tone: 'success', icon: 'fa-check-circle' };
        }
        if (normalized === 'warning') {
            return { text: '告警', tone: 'danger', icon: 'fa-exclamation-triangle' };
        }
        if (normalized === 'maintenance') {
            return { text: '维护中', tone: 'info', icon: 'fa-tools' };
        }
        return { text: '未知', tone: 'muted', icon: 'fa-info-circle' };
    }

    function renderStatusPill(label, tone, icon) {
        const iconHtml = icon ? `<i class="fas ${icon}"></i>` : '';
        return `<span class="status-pill status-pill--${tone}">${iconHtml}${label}</span>`;
    }

    function formatNumber(value) {
        const formatter = new Intl.NumberFormat('zh-CN');
        return formatter.format(Number(value) || 0);
    }
}

window.AdminPartitionsPage = {
    mount: function () {
        mountAdminPartitionsPage(window);
    },
};
