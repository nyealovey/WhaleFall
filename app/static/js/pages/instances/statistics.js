/**
 * 实例统计页面JavaScript
 * 处理统计数据的显示、图表渲染和自动刷新功能
 */

// 全局变量
let versionChart = null;
let refreshInterval = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    createVersionChart();
    startAutoRefresh();
});

// 创建版本分布图表
function createVersionChart() {
    const ctx = document.getElementById('versionChart');
    if (!ctx) return;
    
    // 获取版本统计数据
    const versionStats = getVersionStats();
    
    if (!versionStats || versionStats.length === 0) {
        showEmptyChart(ctx);
        return;
    }
    
    // 按数据库类型分组
    const groupedStats = groupStatsByDbType(versionStats);
    
    // 创建图表数据
    const chartData = createChartData(groupedStats);
    
    // 创建图表
    versionChart = new Chart(ctx, {
        type: 'doughnut',
        data: chartData,
        options: getChartOptions()
    });
}

// 获取版本统计数据
function getVersionStats() {
    // 从页面中获取版本统计数据
    const versionStatsElement = document.querySelector('[data-version-stats]');
    if (versionStatsElement) {
        try {
            return JSON.parse(versionStatsElement.dataset.versionStats);
        } catch (error) {
            console.error('解析版本统计数据失败:', error);
            return null;
        }
    }
    
    // 如果没有data属性，尝试从全局变量获取
    if (typeof window.versionStats !== 'undefined') {
        return window.versionStats;
    }
    
    return null;
}

// 按数据库类型分组统计数据
function groupStatsByDbType(versionStats) {
    const groupedStats = {};
    versionStats.forEach(stat => {
        if (!groupedStats[stat.db_type]) {
            groupedStats[stat.db_type] = [];
        }
        groupedStats[stat.db_type].push(stat);
    });
    return groupedStats;
}

// 创建图表数据
function createChartData(groupedStats) {
    const labels = [];
    const data = [];
    const colors = [];
    const dbTypeColors = {
        'mysql': 'rgba(40, 167, 69, 0.8)',
        'postgresql': 'rgba(0, 123, 255, 0.8)',
        'sqlserver': 'rgba(255, 193, 7, 0.8)',
        'oracle': 'rgba(23, 162, 184, 0.8)'
    };
    
    Object.keys(groupedStats).forEach(dbType => {
        groupedStats[dbType].forEach(stat => {
            labels.push(`${stat.db_type.toUpperCase()} ${stat.version}`);
            data.push(stat.count);
            colors.push(dbTypeColors[stat.db_type] || 'rgba(108, 117, 125, 0.8)');
        });
    });
    
    return {
        labels: labels,
        datasets: [{
            data: data,
            backgroundColor: colors,
            borderColor: colors.map(color => color.replace('0.8', '1')),
            borderWidth: 2
        }]
    };
}

// 获取图表配置选项
function getChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const valueLabel = window.NumberFormat
                            ? window.NumberFormat.formatInteger(context.parsed, { fallback: '0' })
                            : `${context.parsed}`;
                        let percentLabel = '0%';
                        if (total > 0) {
                            const ratio = context.parsed / total;
                            percentLabel = window.NumberFormat
                                ? window.NumberFormat.formatPercent(ratio, {
                                    precision: 1,
                                    trimZero: true,
                                    inputType: 'ratio'
                                  })
                                : `${Math.round(ratio * 1000) / 10}%`;
                        }
                        return `${context.label}: ${valueLabel} 个实例 (${percentLabel})`;
                    }
                }
            }
        }
    };
}

// 显示空图表提示
function showEmptyChart(ctx) {
    const canvas = ctx.getContext('2d');
    canvas.font = '16px Arial';
    canvas.fillStyle = '#666';
    canvas.textAlign = 'center';
    canvas.fillText('暂无版本数据', ctx.width / 2, ctx.height / 2);
}

// 开始自动刷新
function startAutoRefresh() {
    // 每60秒刷新一次统计数据
    refreshInterval = setInterval(() => {
        refreshStatistics();
    }, 60000);
}

// 停止自动刷新
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// 刷新统计数据
function refreshStatistics() {
    http.get('/instances/api/statistics')
        .then(data => {
            // 更新统计数据显示
            updateStatistics(data);
            showDataUpdatedNotification();
        })
        .catch(error => {
            console.error('刷新统计数据失败:', error);
            showErrorNotification('刷新统计数据失败');
        });
}

// 更新统计数据显示
function updateStatistics(stats) {
    // 更新统计卡片
    const totalInstancesElement = document.querySelector('.card.bg-primary .card-title');
    const activeInstancesElement = document.querySelector('.card.bg-success .card-title');
    const inactiveInstancesElement = document.querySelector('.card.bg-warning .card-title');
    const dbTypesCountElement = document.querySelector('.card.bg-info .card-title');
    
    if (totalInstancesElement) totalInstancesElement.textContent = stats.total_instances;
    if (activeInstancesElement) activeInstancesElement.textContent = stats.active_instances;
    if (inactiveInstancesElement) inactiveInstancesElement.textContent = stats.inactive_instances;
    if (dbTypesCountElement) dbTypesCountElement.textContent = stats.db_types_count;
    
    // 更新版本统计图表
    if (stats.version_stats && versionChart) {
        updateVersionChart(stats.version_stats);
    }
}

// 更新版本统计图表
function updateVersionChart(versionStats) {
    if (!versionChart || !versionStats || versionStats.length === 0) return;
    
    const groupedStats = groupStatsByDbType(versionStats);
    const chartData = createChartData(groupedStats);
    
    versionChart.data = chartData;
    versionChart.update();
}

// 显示数据更新通知
function showDataUpdatedNotification() {
    // 移除已存在的通知
    const existingNotification = document.querySelector('.data-updated');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建新通知
    const notification = document.createElement('div');
    notification.className = 'data-updated';
    notification.innerHTML = '<i class="fas fa-sync me-2"></i>数据已更新';
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// 显示错误通知
function showErrorNotification(message) {
    // 移除已存在的通知
    const existingNotification = document.querySelector('.data-updated');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建错误通知
    const notification = document.createElement('div');
    notification.className = 'data-updated';
    notification.style.backgroundColor = '#dc3545';
    notification.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;
    
    document.body.appendChild(notification);
    
    // 5秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// 手动刷新数据
function manualRefresh() {
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        const originalContent = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
        refreshBtn.disabled = true;
        
        refreshStatistics();
        
        // 2秒后恢复按钮状态
        setTimeout(() => {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }, 2000);
    }
}

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// 页面隐藏时暂停自动刷新，显示时恢复
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
    }
});
