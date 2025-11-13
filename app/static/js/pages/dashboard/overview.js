/**
 * 系统仪表板页面JavaScript
 * 处理图表初始化、系统状态更新等功能
 */

// 全局变量
let logTrendChart = null;

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 初始化页面
function initializePage() {
    initCharts();
}

// 初始化图表
function initCharts() {
    // 初始化日志趋势图
    initLogTrendChart();
}

// 获取CSS变量值
function getCssVariable(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

// 将RGB或Hex颜色转换为带有alpha通道的RGBA字符串
function colorWithAlpha(color, alpha) {
    if (color.startsWith('#')) {
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    if (color.startsWith('rgb')) { // rgb(r, g, b)
        return `rgba(${color.substring(color.indexOf('(') + 1, color.indexOf(')'))}, ${alpha})`;
    }
    return color; // Fallback
}

// 初始化日志趋势图
function initLogTrendChart() {
    const ctx = document.getElementById('logTrendChart');
    if (!ctx) return;
    
    const context = ctx.getContext('2d');
    
    // 获取颜色
    const dangerColor = getCssVariable('--danger-color');
    const warningColor = getCssVariable('--warning-color');

    // 获取日志趋势数据
    http.get('/dashboard/api/charts?type=logs')
        .then(data => {
            const payload = data?.data ?? data ?? {};
            const logTrend = payload.log_trend ?? [];
            
            logTrendChart = new Chart(context, {
                type: 'line',
                data: {
                    labels: logTrend.map(item => item.date),
                    datasets: [{
                        label: '错误日志',
                        data: logTrend.map(item => item.error_count),
                        borderColor: dangerColor,
                        backgroundColor: colorWithAlpha(dangerColor, 0.2),
                        tension: 0.1,
                        fill: true
                    }, {
                        label: '告警日志',
                        data: logTrend.map(item => item.warning_count),
                        borderColor: warningColor,
                        backgroundColor: colorWithAlpha(warningColor, 0.2),
                        tension: 0.1,
                        fill: true
                    }]
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
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: '日期'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: '日志数量'
                            },
                            beginAtZero: true
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });
        })
        .catch(error => {
            console.error('加载日志趋势数据失败:', error);
            showError('加载日志趋势数据失败');
        });
}

// 刷新仪表板
function refreshDashboard() {
    const button = event.target;
    const originalText = button.innerHTML;
    
    // 显示加载状态
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
    button.disabled = true;
    
    // 刷新页面数据
    setTimeout(() => {
        location.reload();
    }, 1000);
}

// 更新系统状态
function updateSystemStatus(status) {
    // 更新CPU使用率
    updateResourceUsage('cpu', status.system.cpu);
    
    // 更新内存使用率
    updateResourceUsage('memory', status.system.memory.percent);
    
    // 更新磁盘使用率
    updateResourceUsage('disk', status.system.disk.percent);
    
    // 更新系统运行时间
    updateUptime(status.uptime);
    
    // 显示数据更新通知
    showDataUpdatedNotification('数据已更新');
}

// 更新资源使用率
function updateResourceUsage(type, percent) {
    const elements = {
        cpu: {
            badge: document.querySelector('.card-body .mb-3:first-child .badge'),
            bar: document.querySelector('.card-body .mb-3:first-child .progress-bar')
        },
        memory: {
            badge: document.querySelector('.card-body .mb-3:nth-child(2) .badge'),
            bar: document.querySelector('.card-body .mb-3:nth-child(2) .progress-bar')
        },
        disk: {
            badge: document.querySelector('.card-body .mb-3:nth-child(3) .badge'),
            bar: document.querySelector('.card-body .mb-3:nth-child(3) .progress-bar')
        }
    };
    
    const element = elements[type];
    if (!element.badge || !element.bar) return;
    
    // 更新徽章
    const badgeText = window.NumberFormat.formatPercent(percent, { precision: 1, trimZero: true });
    element.badge.textContent = badgeText;
    const badgeClass = getResourceBadgeClass(percent);
    element.badge.className = `badge ${badgeClass}`;
    
    // 更新进度条
    element.bar.style.width = `${percent}%`;
    const barClass = getResourceBarClass(percent);
    element.bar.className = `progress-bar ${barClass}`;
}

// 获取资源徽章样式类
function getResourceBadgeClass(percent) {
    if (percent > 80) return 'bg-danger';
    if (percent > 60) return 'bg-warning';
    return 'bg-success';
}

// 获取资源进度条样式类
function getResourceBarClass(percent) {
    if (percent > 80) return 'bg-danger';
    if (percent > 60) return 'bg-warning';
    return 'bg-success';
}

// 更新系统运行时间
function updateUptime(uptime) {
    const uptimeElement = document.querySelector('.card-body .mt-3 small');
    if (uptimeElement) {
        uptimeElement.innerHTML = `<i class="fas fa-clock me-1"></i>系统运行时间: ${uptime || '未知'}`;
    }
}

// 显示数据更新通知
function showDataUpdatedNotification(message) {
    // 移除已存在的通知
    const existingNotification = document.querySelector('.data-updated');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建新通知
    const notification = document.createElement('div');
    notification.className = 'data-updated';
    notification.innerHTML = `<i class="fas fa-sync me-2"></i>${message}`;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// 显示错误信息
function showError(message) {
    toast.error(message);
}

// 显示成功信息
function showSuccess(message) {
    toast.success(message);
}

// 显示警告信息
function showWarning(message) {
    toast.warning(message);
}

// 导出函数供全局使用
window.refreshDashboard = refreshDashboard;
