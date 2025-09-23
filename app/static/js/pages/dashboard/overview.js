/**
 * 系统仪表板页面JavaScript
 * 处理图表初始化、自动刷新、系统状态更新等功能
 */

// 全局变量
let autoRefreshInterval = null;
let logTrendChart = null;

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 初始化页面
function initializePage() {
    initCharts();
    startAutoRefresh();
    console.log('系统仪表板页面已加载');
}

// 初始化图表
function initCharts() {
    // 初始化日志趋势图
    initLogTrendChart();
}

// 初始化日志趋势图
function initLogTrendChart() {
    const ctx = document.getElementById('logTrendChart');
    if (!ctx) return;
    
    const context = ctx.getContext('2d');
    
    // 获取日志趋势数据
    fetch('/dashboard/api/charts?type=logs')
        .then(response => response.json())
        .then(data => {
            const logTrend = data.log_trend || [];
            
            logTrendChart = new Chart(context, {
                type: 'line',
                data: {
                    labels: logTrend.map(item => item.date),
                    datasets: [{
                        label: '错误日志',
                        data: logTrend.map(item => item.error_count),
                        borderColor: 'rgb(220, 53, 69)',
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        tension: 0.1,
                        fill: true
                    }, {
                        label: '告警日志',
                        data: logTrend.map(item => item.warning_count),
                        borderColor: 'rgb(255, 193, 7)',
                        backgroundColor: 'rgba(255, 193, 7, 0.2)',
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

// 切换自动刷新
function toggleAutoRefresh() {
    const button = document.querySelector('button[onclick="toggleAutoRefresh()"]');
    
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        button.innerHTML = '<i class="fas fa-clock me-2"></i>自动刷新';
        button.classList.remove('active');
        showDataUpdatedNotification('自动刷新已停止');
    } else {
        startAutoRefresh();
        button.innerHTML = '<i class="fas fa-pause me-2"></i>停止刷新';
        button.classList.add('active');
        showDataUpdatedNotification('自动刷新已启动');
    }
}

// 启动自动刷新
function startAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        // 刷新系统状态
        fetch('/dashboard/api/status')
            .then(response => response.json())
            .then(data => {
                updateSystemStatus(data);
            })
            .catch(error => {
                console.error('刷新系统状态失败:', error);
                showError('刷新系统状态失败');
            });
    }, 30000); // 30秒刷新一次
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
    element.badge.textContent = `${percent.toFixed(1)}%`;
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
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 显示成功信息
function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// 显示警告信息
function showWarning(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-warning alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 4000);
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// 页面隐藏时暂停自动刷新，显示时恢复
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
    }
});

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// 导出函数供全局使用
window.refreshDashboard = refreshDashboard;
window.toggleAutoRefresh = toggleAutoRefresh;
