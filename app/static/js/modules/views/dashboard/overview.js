/**
 * 挂载系统仪表板页面。
 *
 * 初始化系统仪表板的所有组件，包括日志趋势图表、系统状态监控等功能。
 * 提供系统运行状态的可视化展示。
 *
 * @param {Object} global - 全局 window 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountDashboardOverview(window);
 */
function mountDashboardOverview(global) {
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载仪表盘脚本');
        return;
    }

    const LodashUtils = global.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

    const ColorTokens = global.ColorTokens;
    if (!ColorTokens) {
        console.error('ColorTokens 未初始化，无法加载仪表盘脚本');
        return;
    }

    const { ready, selectOne, from } = helpers;
    const DashboardService = global.DashboardService;
    if (!DashboardService) {
        console.error('DashboardService 未初始化，无法加载仪表盘数据');
        return;
    }
    const dashboardService = new DashboardService(global.httpU);

    ready(() => {
        bindActions();
        initCharts();
    });

    /**
     * 页面入口：初始化仪表盘图表。
     *
     * @param {void} 无参数。入口处直接调用。
     * @returns {void}
     */
    function initCharts() {
        initLogTrendChart();
    }

    /**
     * 绑定模板动作按钮，替代内联 onclick。
     *
     * @return {void}
     */
    function bindActions() {
        const refreshBtn = selectOne('[data-action="refresh-dashboard"]');
        if (refreshBtn.length) {
            refreshBtn.on('click', (event) => {
                event?.preventDefault?.();
                refreshDashboard(event.currentTarget || event);
            });
        }
    }

    /**
     * 带透明度的颜色转换。
     *
     * 将十六进制或 RGB 颜色转换为带透明度的 RGBA 格式。
     *
     * @param {string} color - 颜色值，支持十六进制（#RRGGBB）或 RGB 格式
     * @param {number} alpha - 透明度，范围 0-1
     * @return {string} RGBA 格式的颜色字符串
     */
    function colorWithAlpha(color, alpha) {
        return ColorTokens.withAlpha(color, alpha);
    }

    /**
     * 初始化日志趋势图表。
     *
     * 从服务端获取日志趋势数据并渲染为折线图，展示错误日志和告警日志的趋势。
     *
     * @param {void} 无参数。直接读取 #logTrendChart。
     * @returns {void}
     */
    function initLogTrendChart() {
        const canvasWrapper = selectOne('#logTrendChart');
        if (!canvasWrapper.length) {
            return;
        }
        const canvas = canvasWrapper.first();
        const context = canvas.getContext('2d');

        const dangerColor = ColorTokens.getStatusColor('danger');
        const warningColor = ColorTokens.getStatusColor('warning');

        dashboardService
            .fetchCharts({ type: 'logs' })
            .then((data) => {
                const payload = data?.data ?? data ?? {};
                const logTrend = LodashUtils.get(payload, 'log_trend', []);
                const labels = LodashUtils.map(logTrend, (item, index) =>
                    LodashUtils.safeGet(item, 'date', `未知 ${index + 1}`),
                );
                const errorSeries = LodashUtils.map(logTrend, (item) => Number(item?.error_count) || 0);
                const warningSeries = LodashUtils.map(logTrend, (item) => Number(item?.warning_count) || 0);

                new global.Chart(context, {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            {
                                label: '错误日志',
                                data: errorSeries,
                                borderColor: dangerColor,
                                backgroundColor: colorWithAlpha(dangerColor, 0.2),
                                tension: 0.1,
                                fill: true,
                            },
                            {
                                label: '告警日志',
                                data: warningSeries,
                                borderColor: warningColor,
                                backgroundColor: colorWithAlpha(warningColor, 0.2),
                                tension: 0.1,
                                fill: true,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                            },
                        },
                        scales: {
                            x: {
                                display: true,
                                title: {
                                    display: true,
                                    text: '日期',
                                },
                            },
                            y: {
                                display: true,
                                title: {
                                    display: true,
                                    text: '日志数量',
                                },
                                beginAtZero: true,
                            },
                        },
                        interaction: {
                            mode: 'nearest',
                            axis: 'x',
                            intersect: false,
                        },
                    },
                });
            })
            .catch((error) => {
                console.error('加载日志趋势数据失败:', error);
                showError('加载日志趋势数据失败');
            });
    }

    /**
     * 从事件或引用中解析按钮元素。
     *
     * @param {Element|Event|Object} reference - 按钮引用或事件对象
     * @return {Element|null} 按钮元素，未找到则返回 null
     */
    function resolveButton(reference) {
        if (!reference && global.event && global.event.target) {
            return global.event.target;
        }
        if (!reference) {
            return null;
        }
        if (reference instanceof Element) {
            return reference;
        }
        if (reference.currentTarget) {
            return reference.currentTarget;
        }
        if (reference.target) {
            return reference.target;
        }
        return null;
    }

    /**
     * 刷新仪表盘。
     *
     * 显示加载状态并重新加载页面。
     *
     * @param {Element|Event} trigger - 触发刷新的按钮或事件
     * @return {void}
     */
    function refreshDashboard(trigger) {
        const button = resolveButton(trigger);
        const buttonWrapper = button ? from(button) : null;
        const originalText = buttonWrapper ? buttonWrapper.html() : null;

        if (buttonWrapper) {
            buttonWrapper.html('<i class="fas fa-spinner fa-spin me-2"></i>刷新中...');
            buttonWrapper.attr('disabled', 'disabled');
        }

        global.setTimeout(() => {
            global.location.reload();
        }, 1000);

        if (buttonWrapper) {
            global.setTimeout(() => {
                buttonWrapper.html(originalText || '刷新');
                buttonWrapper.attr('disabled', null);
            }, 1000);
        }
    }

    /**
     * 显示错误消息。
     *
     * @param {string} message - 错误消息
     * @return {void}
     */
    function showError(message) {
        global.toast.error(message);
    }

}

window.DashboardOverviewPage = {
    mount: function () {
        mountDashboardOverview(window);
    },
};
