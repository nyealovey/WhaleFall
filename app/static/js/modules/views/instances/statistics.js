/**
 * 挂载实例统计页面。
 *
 * 初始化实例统计页面的所有组件，包括实例管理服务、Store、
 * 图表渲染、自动刷新和状态提示等功能。
 *
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountInstanceStatisticsPage();
 */
function mountInstanceStatisticsPage() {
    const global = window;
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载实例统计页面脚本');
        return;
    }

    const LodashUtils = global.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

    const ColorTokens = global.ColorTokens;
    if (!ColorTokens) {
        console.error('ColorTokens 未初始化，无法加载实例统计页面脚本');
        return;
    }

    const { ready, selectOne, select, from } = helpers;

    const InstanceManagementService = global.InstanceManagementService;
    let instanceService = null;
    try {
        if (InstanceManagementService) {
            instanceService = new InstanceManagementService(global.httpU);
        } else {
            throw new Error('InstanceManagementService 未加载');
        }
    } catch (error) {
        console.error('初始化 InstanceManagementService 失败:', error);
    }

    let instanceStore = null;
    const instanceStoreSubscriptions = [];

    /**
     * 校验 InstanceManagementService 是否初始化。
     *
     * @returns {boolean} 是否可用。
     */
    function ensureInstanceService() {
        if (!instanceService) {
            if (global.toast?.error) {
                global.toast.error('实例管理服务未初始化');
            } else {
                console.error('实例管理服务未初始化');
            }
            return false;
        }
        return true;
    }

    let versionChart = null;
    let refreshInterval = null;

    ready(() => {
        initializeInstanceStore();
        createVersionChart();
        startAutoRefresh();

        from(global).on('beforeunload', () => {
            stopAutoRefresh();
            teardownInstanceStore();
        });
        from(document).on('visibilitychange', handleVisibilityChange);
    });

    /**
     * 初始化 InstanceStore 并加载统计。
     *
     * @returns {void} 成功时构建 store，失败时仅记录日志。
     */
    function initializeInstanceStore() {
        if (!global.createInstanceStore) {
            console.warn('createInstanceStore 未加载，跳过实例 Store 初始化');
            return;
        }
        if (!ensureInstanceService()) {
            return;
        }
        try {
            instanceStore = global.createInstanceStore({
                service: instanceService,
                emitter: global.mitt ? global.mitt() : null,
            });
        } catch (error) {
            console.error('初始化 InstanceStore 失败:', error);
            instanceStore = null;
            return;
        }
        instanceStore
            .init({})
            .then(() => {
                bindInstanceStoreEvents();
                instanceStore.actions.loadStats({ silent: true }).catch(() => {});
            })
            .catch((error) => {
                console.warn('InstanceStore 初始化失败', error);
            });
    }

    /**
     * 订阅 store 事件。
     *
     * @returns {void} 注册统计更新的事件回调。
     */
    function bindInstanceStoreEvents() {
        if (!instanceStore) {
            return;
        }
        subscribeToInstanceStore('instances:statsUpdated', handleStatsUpdated);
    }

    /**
     * 订阅单个 store 事件。
     *
     * @param {string} eventName 事件名称。
     * @param {Function} handler 回调函数。
     * @returns {void} 保存订阅句柄，便于卸载。
     */
    function subscribeToInstanceStore(eventName, handler) {
        instanceStore.subscribe(eventName, handler);
        instanceStoreSubscriptions.push({ eventName, handler });
    }

    /**
     * store 通报统计更新后的处理。
     *
     * @param {Object} payload store 推送的数据。
     * @returns {void} 更新统计并提示用户。
     */
    function handleStatsUpdated(payload) {
        const stats =
            payload?.stats ||
            payload?.state?.stats ||
            payload ||
            {};
        updateStatistics(stats);
        showDataUpdatedNotification();
    }

    /**
     * 销毁 store 并移除订阅。
     *
     * @returns {void} 清理订阅并释放实例。
     */
    function teardownInstanceStore() {
        if (!instanceStore) {
            return;
        }
        instanceStoreSubscriptions.forEach(({ eventName, handler }) => {
            instanceStore.unsubscribe(eventName, handler);
        });
        instanceStoreSubscriptions.length = 0;
        instanceStore.destroy?.();
        instanceStore = null;
    }

    /**
     * 页面可见性变化时管理自动刷新。
     *
     * @returns {void} 根据页面 visibility 状态切换刷新。
     */
    function handleVisibilityChange() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    }

    /**
     * 基于版本统计渲染环状图。
     *
     * @returns {void} 若存在数据则绘制图表，否则展示空状态。
     */
    function createVersionChart() {
        const ctxWrapper = selectOne('#versionChart');
        if (!ctxWrapper.length) {
            return;
        }
        const ctx = ctxWrapper.first();
        const versionStats = getVersionStats();

        if (!versionStats || versionStats.length === 0) {
            showEmptyChart(ctx);
            return;
        }

        const groupedStats = groupStatsByDbType(versionStats);
        const chartData = createChartData(groupedStats);

        versionChart = new global.Chart(ctx, {
            type: 'doughnut',
            data: chartData,
            options: getChartOptions(),
        });
    }

    /**
     * 从 data 属性或全局变量读取统计数据。
     *
     * @returns {Array<Object>|null}
     */
    function getVersionStats() {
        const versionStatsElement = selectOne('[data-version-stats]');
        if (versionStatsElement.length) {
            try {
                return JSON.parse(versionStatsElement.first().dataset.versionStats);
            } catch (error) {
                console.error('解析版本统计数据失败:', error);
            }
        }
        if (typeof global.versionStats !== 'undefined') {
            return global.versionStats;
        }
        return null;
    }

    /**
     * 按数据库类型分组版本数据。
     *
     * @param {Array<Object>} versionStats 原始数据。
     * @returns {Object} 分组后的映射。
     */
    function groupStatsByDbType(versionStats) {
        if (!Array.isArray(versionStats)) {
            return {};
        }
        return LodashUtils.groupBy(versionStats, (stat) => stat?.db_type || 'unknown');
    }

    /**
     * 将分组数据转换为 Chart.js 数据结构。
     *
     * @param {Object} groupedStats 分组数据。
     * @returns {Object} Chart.js data 字段。
     */
    function createChartData(groupedStats) {
        const dbTypeBaseColors = {
            mysql: ColorTokens.getStatusColor('success'),
            postgresql: ColorTokens.getChartColor(1),
            sqlserver: ColorTokens.getStatusColor('warning'),
            oracle: ColorTokens.getChartColor(3),
            default: ColorTokens.resolveCssVar('--gray-600') || 'gray',
        };

        const flattened = LodashUtils.flatMap(Object.entries(groupedStats || {}), ([dbType, stats]) =>
            (stats || []).map((stat) => {
                const normalizedType = (stat?.db_type || dbType || 'unknown').toLowerCase();
                const baseColor = dbTypeBaseColors[normalizedType] || dbTypeBaseColors.default;
                return {
                    dbType: normalizedType,
                    version: stat?.version || 'unknown',
                    count: Number(stat?.count) || 0,
                    baseColor,
                };
            }),
        );

        const ordered = LodashUtils.orderBy(
            flattened,
            [
                (item) => item.dbType,
                (item) => item.version,
            ],
            ['asc', 'asc'],
        );

        const labels = ordered.map((item) => `${item.dbType.toUpperCase()} ${item.version}`);
        const data = ordered.map((item) => item.count);
        const backgroundColors = ordered.map((item) => ColorTokens.withAlpha(item.baseColor, 0.85));
        const borderColors = ordered.map((item) => item.baseColor);

        return {
            labels,
            datasets: [
                {
                    data,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                },
            ],
        };
    }

    /**
     * 返回 Chart.js 选项。
     *
     * @returns {Object} 配置项。
     */
    function getChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                    },
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const valueLabel = global.NumberFormat.formatInteger(context.parsed, { fallback: '0' });
                            let percentLabel = '0%';
                            if (total > 0) {
                                const ratio = context.parsed / total;
                                percentLabel = global.NumberFormat.formatPercent(ratio, {
                                    precision: 1,
                                    trimZero: true,
                                    inputType: 'ratio',
                                });
                            }
                            return `${context.label}: ${valueLabel} 个实例 (${percentLabel})`;
                        },
                    },
                },
            },
        };
    }

    /**
     * 在画布上渲染“暂无数据”。
     *
     * @param {HTMLCanvasElement} ctx 画布。
     * @returns {void} 直接在画布上绘制提示文本。
     */
    function showEmptyChart(ctx) {
        const canvas = ctx.getContext('2d');
        canvas.font = '16px Arial';
        canvas.fillStyle = ColorTokens.resolveCssVar('--gray-600') || 'black';
        canvas.textAlign = 'center';
        canvas.fillText('暂无版本数据', ctx.width / 2, ctx.height / 2);
    }

    /**
     * 启动定时刷新。
     *
     * @returns {void} 设置定时器，避免重复注册。
     */
    function startAutoRefresh() {
        if (refreshInterval) {
            return;
        }
        refreshInterval = global.setInterval(() => {
            refreshStatistics();
        }, 60000);
    }

    /**
     * 停止定时刷新。
     *
     * @returns {void} 清理定时器并释放引用。
     */
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }

    /**
     * 主动刷新统计数据。
     *
     * @returns {void} 触发网络请求并更新统计。
     */
    function refreshStatistics() {
        if (!ensureInstanceService()) {
            return;
        }
        const loader = instanceStore
            ? instanceStore.actions.loadStats({ silent: true })
            : instanceService.fetchStatistics();
        loader
            .then((data) => {
                if (!instanceStore) {
                    updateStatistics(data);
                    showDataUpdatedNotification();
                }
            })
            .catch((error) => {
                console.error('刷新统计数据失败:', error);
                showErrorNotification('刷新统计数据失败');
            });
    }

    /**
     * 更新统计卡片。
     *
     * @param {Object} stats 最新统计数据。
     * @returns {void} 刷新 DOM 以及版本图表。
     */
    function updateStatistics(stats) {
        setStatValue('total_instances', stats.total_instances);
        setStatValue('active_instances', stats.active_instances);
        setStatValue('inactive_instances', stats.inactive_instances);
        setStatValue('db_types_count', stats.db_types_count);

        if (stats.version_stats && versionChart) {
            updateVersionChart(stats.version_stats);
        }
    }

    /**
     * 将数值写入 data-stat-value 对应节点。
     *
     * @param {string} key 数据键。
     * @param {number|string} value 数值。
     * @returns {void}
     */
    function setStatValue(key, value) {
        const targetElements = select(`[data-stat-value="${key}"]`);
        if (!targetElements.length) {
            return;
        }
        const resolved = value === null || value === undefined ? '-' : value;
        const formatted = global.NumberFormat?.formatInteger?.(resolved, { fallback: resolved }) ?? resolved;
        targetElements.text(formatted);
    }

    /**
     * 使用新的版本数据更新图表。
     *
     * @param {Array<Object>} versionStats 数据。
     * @returns {void} 更新图表 datasets 并重绘。
     */
    function updateVersionChart(versionStats) {
        if (!versionChart || !versionStats || versionStats.length === 0) {
            return;
        }
        const groupedStats = groupStatsByDbType(versionStats);
        versionChart.data = createChartData(groupedStats);
        versionChart.update();
    }

    /**
     * 移除已存在的通知元素。
     *
     * @returns {void} 清空 `.data-updated` DOM。
     */
    function removeExistingNotification() {
        select('.data-updated').remove();
    }

    /**
     * 显示数据已更新提示。
     *
     * @returns {void} 在页面上短暂显示提示框。
     */
    function showDataUpdatedNotification() {
        removeExistingNotification();

        const notification = document.createElement('div');
        notification.className = 'data-updated';
        notification.innerHTML = '<i class="fas fa-sync me-2"></i>数据已更新';

        document.body.appendChild(notification);

        global.setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    /**
     * 显示错误提示。
     *
     * @param {string} message 错误文案。
     * @returns {void} 显示并在超时后移除提示。
     */
    function showErrorNotification(message) {
        removeExistingNotification();

        const notification = document.createElement('div');
        notification.className = 'data-updated';
        notification.style.backgroundColor = ColorTokens.getStatusColor('danger');
        notification.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;

        document.body.appendChild(notification);

        global.setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * 手动刷新按钮处理。
     *
     * @param {HTMLElement|EventTarget} [trigger] 触发刷新事件的按钮。
     * @returns {void} 刷新统计并恢复按钮状态。
     */
    function manualRefresh(trigger) {
        const buttonWrapper = trigger ? from(trigger) : selectOne('[data-action="refresh-stats"]');
        if (!buttonWrapper.length) {
            refreshStatistics();
            return;
        }
        const button = buttonWrapper.first();
        const originalContent = buttonWrapper.html();
        buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>刷新中...');
        buttonWrapper.attr('disabled', 'disabled');

        refreshStatistics();

        global.setTimeout(() => {
            buttonWrapper.html(originalContent);
            buttonWrapper.attr('disabled', null);
        }, 2000);
    }

    global.manualRefresh = manualRefresh;
}

window.InstanceStatisticsPage = {
    mount: mountInstanceStatisticsPage,
};
