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

    const { ready, selectOne, select, from } = helpers;
    const DashboardService = global.DashboardService;
    if (!DashboardService) {
        console.error('DashboardService 未初始化，无法加载仪表盘数据');
        return;
    }
    const dashboardService = new DashboardService(global.httpU);

    let logTrendChart = null;

    ready(() => {
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
     * 读取 CSS 变量值。
     *
     * @param {string} variable - CSS 变量名称，例如 '--danger-color'
     * @return {string} CSS 变量的值
     */
    function getCssVariable(variable) {
        return ColorTokens.resolveCssVar(variable);
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

        const dangerColor = getCssVariable('--danger-color');
        const warningColor = getCssVariable('--warning-color');

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

                logTrendChart = new global.Chart(context, {
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
     * 更新系统状态显示。
     *
     * @param {Object} status - 系统状态数据
     * @param {Object} status.system - 系统资源信息
     * @param {number} status.system.cpu - CPU 使用率
     * @param {Object} status.system.memory - 内存信息
     * @param {number} status.system.memory.percent - 内存使用率
     * @param {Object} status.system.disk - 磁盘信息
     * @param {number} status.system.disk.percent - 磁盘使用率
     * @param {string} status.uptime - 系统运行时间
     * @return {void}
     */
    function updateSystemStatus(status) {
        updateResourceUsage('cpu', status.system.cpu);
        updateResourceUsage('memory', status.system.memory.percent);
        updateResourceUsage('disk', status.system.disk.percent);
        updateUptime(status.uptime);
        showDataUpdatedNotification('数据已更新');
    }

    /**
     * 更新资源使用率显示。
     *
     * @param {string} type - 资源类型：'cpu'、'memory'、'disk'
     * @param {number} percent - 使用率百分比
     * @return {void}
     */
    function updateResourceUsage(type, percent) {
        const normalizedPercent = Number(percent) || 0;
        const container = document.querySelector(`.resource-usage[data-resource="${type}"]`);
        if (!container) {
            return;
        }
        const badge = container.querySelector('[data-resource-badge]');
        const bar = container.querySelector('[data-resource-bar]');
        const variant = resolveUsageVariant(normalizedPercent);
        const formatted = global.NumberFormat.formatPercent(normalizedPercent, { precision: 1, trimZero: true });
        if (badge) {
            badge.textContent = formatted;
            badge.className = buildStatusPillClass(variant);
        }
        if (bar) {
            bar.style.width = `${normalizedPercent}%`;
            bar.className = `progress-bar ${variant ? `progress-bar--${variant}` : ''}`.trim();
        }
    }

    function resolveUsageVariant(percent) {
        if (percent > 80) {
            return 'danger';
        }
        if (percent > 60) {
            return 'warning';
        }
        return 'success';
    }

    function buildStatusPillClass(variant) {
        const classes = ['status-pill'];
        if (variant) {
            classes.push(`status-pill--${variant}`);
        }
        return classes.join(' ');
    }

    /**
     * 更新系统运行时间显示。
     *
     * @param {string} uptime - 运行时间字符串
     * @return {void}
     */
    function updateUptime(uptime) {
        const uptimeElement = selectOne('.card-body .mt-3 small');
        if (!uptimeElement.length) {
            return;
        }
        uptimeElement.html(`<i class="fas fa-clock me-1"></i>系统运行时间: ${uptime || '未知'}`);
    }

    /**
     * 显示数据更新通知。
     *
     * @param {string} message - 通知消息
     * @return {void}
     */
    function showDataUpdatedNotification(message) {
        select('.data-updated').remove();

        const notification = document.createElement('div');
        notification.className = 'data-updated';
        notification.innerHTML = `<i class="fas fa-sync me-2"></i>${message}`;
        document.body.appendChild(notification);

        global.setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
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

    /**
     * 显示成功消息。
     *
     * @param {string} message - 成功消息
     * @return {void}
     */
    function showSuccess(message) {
        global.toast.success(message);
    }

    /**
     * 显示警告消息。
     *
     * @param {string} message - 警告消息
     * @return {void}
     */
    function showWarning(message) {
        global.toast.warning(message);
    }

    global.refreshDashboard = refreshDashboard;
    global.updateSystemStatus = updateSystemStatus;
    global.showDashboardError = showError;
    global.showDashboardSuccess = showSuccess;
    global.showDashboardWarning = showWarning;
}

window.DashboardOverviewPage = {
    mount: function () {
        mountDashboardOverview(window);
    },
};
