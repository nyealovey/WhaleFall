/**
 * 日志仪表板页面JavaScript
 * 处理日志搜索、筛选、分页、详情查看等功能
 */

// 全局变量
let currentPage = 1;
let currentFilters = {};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 初始化页面
function initializePage() {
    loadModules();
    loadStats();
    searchLogs();
    console.log('日志仪表板页面已加载');
}

// 加载模块列表
function loadModules() {
    fetch('/logs/api/modules')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateModuleFilter(data.data.modules);
            }
        })
        .catch(error => {
            console.error('Error loading modules:', error);
            showError('加载模块列表失败');
        });
}

// 更新模块筛选器
function updateModuleFilter(modules) {
    const moduleSelect = document.getElementById('moduleFilter');
    if (moduleSelect) {
        moduleSelect.innerHTML = '<option value="">全部模块</option>';
        modules.forEach(module => {
            const option = document.createElement('option');
            option.value = module;
            option.textContent = module;
            moduleSelect.appendChild(option);
        });
    }
}

// 加载统计信息
function loadStats() {
    fetch('/logs/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateStatsDisplay(data.data);
            }
        })
        .catch(error => {
            console.error('Error loading stats:', error);
            showError('加载统计信息失败');
        });
}

// 更新统计信息显示
function updateStatsDisplay(stats) {
    const elements = {
        'totalLogs': stats.total_logs || 0,
        'errorLogs': stats.error_logs || 0,
        'warningLogs': stats.warning_logs || 0,
        'modulesCount': stats.modules_count || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            element.classList.add('fade-in');
        }
    });
}

// 搜索日志
function searchLogs(page = 1) {
    currentPage = page;
    
    // 收集过滤条件
    currentFilters = {
        page: page,
        per_page: 50,
        level: document.getElementById('levelFilter').value,
        module: document.getElementById('moduleFilter').value,
        q: document.getElementById('searchTerm').value,
        hours: parseInt(document.getElementById('timeRange').value)
    };

    // 构建查询参数
    const params = new URLSearchParams();
    Object.keys(currentFilters).forEach(key => {
        if (currentFilters[key]) {
            params.append(key, currentFilters[key]);
        }
    });

    // 显示加载状态
    showLoadingState();

    // 发送请求
    fetch(`/logs/api/search?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayLogs(data.data.logs);
                displayPagination(data.data.pagination);
            } else {
                showError('搜索失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error searching logs:', error);
            showError('搜索出错: ' + error.message);
        });
}

// 显示加载状态
function showLoadingState() {
    const container = document.getElementById('logsContainer');
    if (container) {
        container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin me-2"></i>搜索中...</div>';
    }
}

// 显示日志列表
function displayLogs(logs) {
    const container = document.getElementById('logsContainer');
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="no-logs"><i class="fas fa-search"></i><br>没有找到匹配的日志</div>';
        return;
    }

    let html = '';
    logs.forEach(log => {
        html += createLogEntryHTML(log);
    });
    
    container.innerHTML = html;
}

// 创建日志条目HTML
function createLogEntryHTML(log) {
    const levelClass = `log-level-${log.level}`;
    const levelBadge = getLevelBadgeHTML(log.level);
    const moduleBadge = log.module ? `<span class="module-badge">${log.module}</span>` : '';
    const timestamp = formatTime(log.timestamp, 'datetime');
    const message = highlightSearchTerm(log.message, currentFilters.q);
    
    return `
        <div class="log-entry ${levelClass}" onclick="viewLogDetail(${log.id})">
            <div class="log-header">
                ${levelBadge}
                ${moduleBadge}
                <span class="timestamp-display">${timestamp}</span>
            </div>
            <div class="log-message">${message}</div>
            <div class="log-right-info">
                <span class="log-id-display">ID: ${log.id}</span>
            </div>
        </div>
    `;
}

// 获取级别徽章HTML
function getLevelBadgeHTML(level) {
    const colors = {
        'DEBUG': 'secondary',
        'INFO': 'info',
        'WARNING': 'warning',
        'ERROR': 'danger',
        'CRITICAL': 'dark'
    };
    const color = colors[level] || 'secondary';
    return `<span class="badge bg-${color} log-level-badge">${level}</span>`;
}

// 高亮搜索词
function highlightSearchTerm(text, searchTerm) {
    if (!searchTerm) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

// 显示分页
function displayPagination(pagination) {
    const container = document.getElementById('paginationContainer');
    if (!container) return;
    
    let html = '<nav><ul class="pagination">';
    
    // 上一页
    if (pagination.has_prev) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="searchLogs(${pagination.prev_num}); return false;">上一页</a></li>`;
    } else {
        html += `<li class="page-item disabled"><span class="page-link">上一页</span></li>`;
    }
    
    // 页码
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.pages, pagination.page + 2);
    
    // 第一页和省略号
    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="searchLogs(1); return false;">1</a></li>`;
        if (startPage > 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    // 中间页码
    for (let i = startPage; i <= endPage; i++) {
        const active = i === pagination.page ? 'active' : '';
        html += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="searchLogs(${i}); return false;">${i}</a></li>`;
    }
    
    // 最后一页和省略号
    if (endPage < pagination.pages) {
        if (endPage < pagination.pages - 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="searchLogs(${pagination.pages}); return false;">${pagination.pages}</a></li>`;
    }
    
    // 下一页
    if (pagination.has_next) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="searchLogs(${pagination.next_num}); return false;">下一页</a></li>`;
    } else {
        html += `<li class="page-item disabled"><span class="page-link">下一页</span></li>`;
    }
    
    html += '</ul></nav>';
    container.innerHTML = html;
}

// 查看日志详情
function viewLogDetail(logId) {
    fetch(`/logs/api/detail/${logId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayLogDetail(data.data.log);
            } else {
                showError('加载日志详情失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error loading log detail:', error);
            showError('加载日志详情失败: ' + error.message);
        });
}

// 显示日志详情
function displayLogDetail(log) {
    const content = document.getElementById('logDetailContent');
    if (!content) return;
    
    const levelBadge = getLevelBadgeHTML(log.level);
    const moduleBadge = log.module ? `<span class="badge bg-secondary">${log.module}</span>` : '';
    const timestamp = formatTime(log.timestamp, 'datetime');
    const createdAt = formatTime(log.created_at, 'datetime');
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <strong>时间:</strong> ${timestamp}<br>
                <strong>级别:</strong> ${levelBadge}<br>
                <strong>模块:</strong> ${moduleBadge}
            </div>
            <div class="col-md-6">
                <strong>ID:</strong> <code>${log.id}</code><br>
                <strong>创建时间:</strong> ${createdAt}
            </div>
        </div>
        <hr>
        <div class="mb-3">
            <strong>消息:</strong><br>
            <div class="alert alert-info">${log.message}</div>
        </div>
        ${log.context ? `
            <div class="mb-3">
                <strong>上下文:</strong><br>
                <div class="json-context">${formatJSON(log.context)}</div>
            </div>
        ` : ''}
        ${log.traceback ? `
            <div class="mb-3">
                <strong>堆栈追踪:</strong><br>
                <div class="traceback-content">${log.traceback}</div>
            </div>
        ` : ''}
    `;
    
    const modal = document.getElementById('logDetailModal');
    if (modal) {
        new bootstrap.Modal(modal).show();
    }
}

// 获取级别颜色
function getLevelColor(level) {
    const colors = {
        'DEBUG': 'secondary',
        'INFO': 'info',
        'WARNING': 'warning',
        'ERROR': 'danger',
        'CRITICAL': 'dark'
    };
    return colors[level] || 'secondary';
}

// 格式化JSON
function formatJSON(obj) {
    if (typeof obj === 'string') {
        try {
            obj = JSON.parse(obj);
        } catch (e) {
            return obj;
        }
    }
    return JSON.stringify(obj, null, 2);
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

// 重置筛选器
function resetFilters() {
    document.getElementById('levelFilter').value = '';
    document.getElementById('moduleFilter').value = '';
    document.getElementById('searchTerm').value = '';
    document.getElementById('timeRange').value = '24';
    
    searchLogs(1);
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

// 导出函数供全局使用
window.searchLogs = searchLogs;
window.viewLogDetail = viewLogDetail;
window.resetFilters = resetFilters;
