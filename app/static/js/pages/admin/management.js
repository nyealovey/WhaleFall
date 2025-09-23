/**
 * 系统管理页面JavaScript
 * 处理系统概览、状态监控、数据刷新等功能
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 初始化页面
function initializePage() {
    loadSystemOverview();
    checkSystemStatus();
    console.log('系统管理页面已加载');
}

// 加载系统概览数据
function loadSystemOverview() {
    fetch('/dashboard/api/overview')
        .then(response => response.json())
        .then(data => {
            updateSystemOverview(data);
        })
        .catch(error => {
            console.error('加载系统概览失败:', error);
            showError('加载系统概览失败');
        });
}

// 更新系统概览显示
function updateSystemOverview(data) {
    const elements = {
        'total-users': data.users?.total || 0,
        'total-instances': data.instances?.total || 0,
        'total-tasks': data.tasks?.total || 0,
        'total-logs': data.logs?.total || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            element.classList.add('fade-in');
        }
    });
}

// 检查系统状态
function checkSystemStatus() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            updateSystemStatus(data);
        })
        .catch(error => {
            console.error('检查系统状态失败:', error);
            updateSystemStatusError();
        });
}

// 更新系统状态显示
function updateSystemStatus(data) {
    // 更新数据库状态
    updateStatusIndicator('db-indicator', data.database === 'connected' ? 'healthy' : 'error');
    updateStatusText('db-status', data.database === 'connected' ? '正常' : '异常');
    
    // 更新Redis状态
    updateStatusIndicator('redis-indicator', data.redis === 'connected' ? 'healthy' : 'error');
    updateStatusText('redis-status', data.redis === 'connected' ? '正常' : '异常');
    
    // 更新应用状态
    updateStatusIndicator('app-indicator', 'healthy');
    updateStatusText('app-status', '运行中');
    
    // 更新运行时间
    const uptimeElement = document.getElementById('uptime');
    if (uptimeElement) {
        uptimeElement.textContent = data.uptime || '未知';
    }
    
    // 更新最后更新时间
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = formatTime(new Date().toISOString(), 'datetime');
    }
}

// 更新系统状态错误显示
function updateSystemStatusError() {
    updateStatusIndicator('db-indicator', 'error');
    updateStatusIndicator('redis-indicator', 'error');
    updateStatusIndicator('app-indicator', 'error');
    
    updateStatusText('db-status', '连接失败');
    updateStatusText('redis-status', '连接失败');
    updateStatusText('app-status', '状态未知');
}

// 更新状态指示器
function updateStatusIndicator(elementId, status) {
    const element = document.getElementById(elementId);
    if (element) {
        element.className = `status-indicator status-${status}`;
    }
}

// 更新状态文本
function updateStatusText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

// 刷新数据
function refreshData() {
    const button = event.target;
    const originalText = button.innerHTML;
    
    // 显示加载状态
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
    button.disabled = true;
    
    // 重新加载数据
    loadSystemOverview();
    checkSystemStatus();
    
    // 显示刷新提示
    showDataUpdatedNotification();
    
    // 恢复按钮状态
    setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 2000);
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

// 格式化时间
function formatTime(timeString, format = 'datetime') {
    if (!timeString) return '-';
    
    try {
        const date = new Date(timeString);
        if (isNaN(date.getTime())) return '-';
        
        // 使用自定义格式化确保使用 - 分隔符
        if (format === 'datetime') {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const seconds = String(date.getSeconds()).padStart(2, '0');
            return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        } else if (format === 'date') {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        } else if (format === 'time') {
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const seconds = String(date.getSeconds()).padStart(2, '0');
            return `${hours}:${minutes}:${seconds}`;
        }
        
        return date.toLocaleString('zh-CN', {
            timeZone: 'Asia/Shanghai',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        console.error('时间格式化错误:', e);
        return '-';
    }
}

// 自动刷新数据（每5分钟）
function startAutoRefresh() {
    setInterval(() => {
        loadSystemOverview();
        checkSystemStatus();
    }, 300000); // 5分钟
}

// 停止自动刷新
function stopAutoRefresh() {
    // 清除所有定时器
    for (let i = 1; i < 99999; i++) {
        window.clearInterval(i);
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

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// 导出函数供全局使用
window.refreshData = refreshData;
window.loadSystemOverview = loadSystemOverview;
window.checkSystemStatus = checkSystemStatus;
