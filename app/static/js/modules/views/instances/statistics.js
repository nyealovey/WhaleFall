function mountInstanceStatisticsPage() {
    const global = window;
    /**
     * 实例统计页面 JavaScript
     * 负责图表渲染、自动刷新与状态提示
     */
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

    function bindInstanceStoreEvents() {
        if (!instanceStore) {
            return;
        }
        subscribeToInstanceStore('instances:statsUpdated', handleStatsUpdated);
    }

    function subscribeToInstanceStore(eventName, handler) {
        instanceStore.subscribe(eventName, handler);
        instanceStoreSubscriptions.push({ eventName, handler });
    }

    function handleStatsUpdated(payload) {
        const stats =
            payload?.stats ||
            payload?.state?.stats ||
            payload ||
            {};
        updateStatistics(stats);
        showDataUpdatedNotification();
    }

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

    function handleVisibilityChange() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    }

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

    function groupStatsByDbType(versionStats) {
        if (!Array.isArray(versionStats)) {
            return {};
        }
        return LodashUtils.groupBy(versionStats, (stat) => stat?.db_type || 'unknown');
    }

    function createChartData(groupedStats) {
        const dbTypeColors = {
            mysql: 'rgba(40, 167, 69, 0.8)',
            postgresql: 'rgba(0, 123, 255, 0.8)',
            sqlserver: 'rgba(255, 193, 7, 0.8)',
            oracle: 'rgba(23, 162, 184, 0.8)',
            default: 'rgba(108, 117, 125, 0.8)',
        };

        const flattened = LodashUtils.flatMap(Object.entries(groupedStats || {}), ([dbType, stats]) =>
            (stats || []).map((stat) => {
                const normalizedType = (stat?.db_type || dbType || 'unknown').toLowerCase();
                return {
                    dbType: normalizedType,
                    version: stat?.version || 'unknown',
                    count: Number(stat?.count) || 0,
                    color: dbTypeColors[normalizedType] || dbTypeColors.default,
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
        const colors = ordered.map((item) => item.color);

        return {
            labels,
            datasets: [
                {
                    data,
                    backgroundColor: colors,
                    borderColor: colors.map(toOpaqueColor),
                    borderWidth: 2,
                },
            ],
        };
    }

    function toOpaqueColor(color) {
        if (typeof color !== 'string') {
            return 'rgba(108, 117, 125, 1)';
        }
        if (color.startsWith('rgba')) {
            return color.replace(/rgba\(([^,]+,\s*[^,]+,\s*[^,]+),\s*[^)]+\)/, 'rgba($1, 1)');
        }
        return color;
    }

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

    function showEmptyChart(ctx) {
        const canvas = ctx.getContext('2d');
        canvas.font = '16px Arial';
        canvas.fillStyle = '#666';
        canvas.textAlign = 'center';
        canvas.fillText('暂无版本数据', ctx.width / 2, ctx.height / 2);
    }

    function startAutoRefresh() {
        if (refreshInterval) {
            return;
        }
        refreshInterval = global.setInterval(() => {
            refreshStatistics();
        }, 60000);
    }

    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }

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

    function updateStatistics(stats) {
        const totalInstancesElement = selectOne('.card.bg-primary .card-title');
        const activeInstancesElement = selectOne('.card.bg-success .card-title');
        const inactiveInstancesElement = selectOne('.card.bg-warning .card-title');
        const dbTypesCountElement = selectOne('.card.bg-info .card-title');

        if (totalInstancesElement.length) totalInstancesElement.text(stats.total_instances);
        if (activeInstancesElement.length) activeInstancesElement.text(stats.active_instances);
        if (inactiveInstancesElement.length) inactiveInstancesElement.text(stats.inactive_instances);
        if (dbTypesCountElement.length) dbTypesCountElement.text(stats.db_types_count);

        if (stats.version_stats && versionChart) {
            updateVersionChart(stats.version_stats);
        }
    }

    function updateVersionChart(versionStats) {
        if (!versionChart || !versionStats || versionStats.length === 0) {
            return;
        }
        const groupedStats = groupStatsByDbType(versionStats);
        versionChart.data = createChartData(groupedStats);
        versionChart.update();
    }

    function removeExistingNotification() {
        select('.data-updated').remove();
    }

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

    function showErrorNotification(message) {
        removeExistingNotification();

        const notification = document.createElement('div');
        notification.className = 'data-updated';
        notification.style.backgroundColor = '#dc3545';
        notification.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;

        document.body.appendChild(notification);

        global.setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    function manualRefresh(trigger) {
        const buttonWrapper = trigger ? from(trigger) : selectOne('.refresh-btn');
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
