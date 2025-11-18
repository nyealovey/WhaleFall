function mountDashboardOverview(global) {
    /**
     * 系统仪表板页面 JavaScript
     * 处理图表初始化、系统状态更新等功能
     */
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
     */
    function initCharts() {
        initLogTrendChart();
    }

    /**
     * 读取 CSS 变量值。
     */
    function getCssVariable(variable) {
        return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
    }

    /**
     * 带透明度的颜色转换。
     */
    function colorWithAlpha(color, alpha) {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        if (color.startsWith('rgb')) {
            return `rgba(${color.substring(color.indexOf('(') + 1, color.indexOf(')'))}, ${alpha})`;
        }
        return color;
    }

    /**
     * 初始化日志趋势图表。
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

    function updateSystemStatus(status) {
        updateResourceUsage('cpu', status.system.cpu);
        updateResourceUsage('memory', status.system.memory.percent);
        updateResourceUsage('disk', status.system.disk.percent);
        updateUptime(status.uptime);
        showDataUpdatedNotification('数据已更新');
    }

    function updateResourceUsage(type, percent) {
        const selectors = {
            cpu: {
                badge: '.card-body .mb-3:first-child .badge',
                bar: '.card-body .mb-3:first-child .progress-bar',
            },
            memory: {
                badge: '.card-body .mb-3:nth-child(2) .badge',
                bar: '.card-body .mb-3:nth-child(2) .progress-bar',
            },
            disk: {
                badge: '.card-body .mb-3:nth-child(3) .badge',
                bar: '.card-body .mb-3:nth-child(3) .progress-bar',
            },
        };

        const current = selectors[type];
        if (!current) {
            return;
        }
        const badge = selectOne(current.badge);
        const bar = selectOne(current.bar);
        if (!badge.length || !bar.length) {
            return;
        }

        const badgeText = global.NumberFormat.formatPercent(percent, { precision: 1, trimZero: true });
        badge.text(badgeText);
        const badgeClass = getResourceBadgeClass(percent);
        badge.attr('class', `badge ${badgeClass}`);

        bar.first().style.width = `${percent}%`;
        const barClass = getResourceBarClass(percent);
        bar.attr('class', `progress-bar ${barClass}`);
    }

    function getResourceBadgeClass(percent) {
        if (percent > 80) return 'bg-danger';
        if (percent > 60) return 'bg-warning';
        return 'bg-success';
    }

    function getResourceBarClass(percent) {
        if (percent > 80) return 'bg-danger';
        if (percent > 60) return 'bg-warning';
        return 'bg-success';
    }

    function updateUptime(uptime) {
        const uptimeElement = selectOne('.card-body .mt-3 small');
        if (!uptimeElement.length) {
            return;
        }
        uptimeElement.html(`<i class="fas fa-clock me-1"></i>系统运行时间: ${uptime || '未知'}`);
    }

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

    function showError(message) {
        global.toast.error(message);
    }

    function showSuccess(message) {
        global.toast.success(message);
    }

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
