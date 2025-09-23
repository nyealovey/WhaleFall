(function() {
let currentPage = 1;
let currentFilters = {};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadModules();
    loadStats();
    searchLogs();
});

// 加载模块列表
function loadModules() {
    fetch('/logs/api/modules')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const moduleSelect = document.getElementById('moduleFilter');
                moduleSelect.innerHTML = '<option value="">全部模块</option>';
                data.data.modules.forEach(module => {
                    const option = document.createElement('option');
                    option.value = module;
                    option.textContent = module;
                    moduleSelect.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error loading modules:', error));
}

// 加载统计信息
function loadStats() {
    fetch('/logs/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('totalLogs').textContent = data.data.total_logs || 0;
                document.getElementById('errorLogs').textContent = data.data.error_logs || 0;
                document.getElementById('warningLogs').textContent = data.data.warning_logs || 0;
                document.getElementById('modulesCount').textContent = data.data.modules_count || 0;
            }
        })
        .catch(error => console.error('Error loading stats:', error));
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
    document.getElementById('logsContainer').innerHTML = 
        '<div class="loading"><i class="fas fa-spinner fa-spin me-2"></i>搜索中...</div>';

    // 发送请求
    fetch(`/logs/api/search?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayLogs(data.data.logs);
                displayPagination(data.data.pagination);
            } else {
                document.getElementById('logsContainer').innerHTML = 
                    '<div class="no-logs">搜索失败: ' + data.message + '</div>';
            }
        })
        .catch(error => {
            console.error('Error searching logs:', error);
            document.getElementById('logsContainer').innerHTML = 
                '<div class="no-logs">搜索出错: ' + error.message + '</div>';
        });
}

// 显示日志列表
function displayLogs(logs) {
    const container = document.getElementById('logsContainer');
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="no-logs"><i class="fas fa-search"></i><br>没有找到匹配的日志</div>';
        return;
    }

    let html = `
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>日志ID</th>
                        <th>时间</th>
                        <th>级别</th>
                        <th>模块</th>
                        <th>消息</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    logs.forEach(log => {
        // 更准确地检查上下文：排除空对象和只有null值的对象
        const hasContext = log.context && 
                          typeof log.context === 'object' && 
                          Object.keys(log.context).length > 0 &&
                          Object.values(log.context).some(value => value !== null && value !== undefined && value !== '');
        
        const hasTraceback = log.traceback && log.traceback.trim().length > 0;
        
        html += `
            <tr>
                <td><code>${log.id}</code></td>
                <td>${formatTime(log.timestamp, 'datetime')}</td>
                <td>
                    <span class="badge bg-${getLevelColor(log.level)}">
                        ${log.level}
                    </span>
                </td>
                <td><code>${log.module}</code></td>
                <td class="text-truncate" style="max-width: 400px;" title="${log.message}">
                    ${log.message}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="viewLogDetail(${log.id})" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${hasContext ? `
                        <button class="btn btn-sm btn-outline-info me-1" onclick="viewLogContext(${log.id})" title="查看上下文">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    ` : ''}
                    ${hasTraceback ? `
                        <button class="btn btn-sm btn-outline-warning me-1" onclick="viewLogDebug(${log.id})" title="查看调试信息">
                            <i class="fas fa-bug"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    container.innerHTML = html;
}

// 显示分页
function displayPagination(pagination) {
    const container = document.getElementById('pagination');
    
    
    if (!pagination || pagination.pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<nav aria-label="日志分页"><ul class="pagination justify-content-center">';
    
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
                const log = data.data.log;
                const content = document.getElementById('logDetailContent');
                
                content.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <strong>时间:</strong> ${formatTime(log.timestamp, 'datetime')}<br>
                            <strong>级别:</strong> <span class="badge bg-${getLevelColor(log.level)}">${log.level}</span><br>
                            <strong>模块:</strong> <span class="badge bg-secondary">${log.module}</span>
                        </div>
                        <div class="col-md-6">
                            <strong>ID:</strong> <code>${log.id}</code><br>
                            <strong>创建时间:</strong> ${formatTime(log.created_at, 'datetime')}
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
                            <div class="log-context" style="margin-top: 8px;">${formatJSON(log.context)}</div>
                        </div>
                    ` : ''}
                    ${log.traceback ? `
                        <div class="mb-3">
                            <strong>堆栈追踪:</strong><br>
                            <div class="log-traceback" style="margin-top: 8px;">${log.traceback}</div>
                        </div>
                    ` : ''}
                `;
                
                new bootstrap.Modal(document.getElementById('logDetailModal')).show();
            }
        })
        .catch(error => {
            console.error('Error loading log detail:', error);
            console.error('加载日志详情失败:', error.message);
        });
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

// 格式化JSON显示
function formatJSON(obj) {
    if (!obj) return '';
    try {
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return String(obj);
    }
}

// 使用统一的时间格式化函数
// formatTimestamp 函数已由 time-utils.js 提供

// 导出日志
function exportLogs(format) {
    const params = new URLSearchParams(currentFilters);
    params.append('format', format);
    
    window.open(`/logs/api/export?${params}`, '_blank');
}

// 查看日志上下文
function viewLogContext(logId) {
    fetch(`/logs/api/detail/${logId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const log = data.data.log;
                const content = document.getElementById('logDetailContent');
                
                content.innerHTML = `
                    <div class="mb-3">
                        <h6><i class="fas fa-info-circle me-2"></i>日志上下文信息</h6>
                        <hr>
                    </div>
                    <div class="mb-3">
                        <strong>日志ID:</strong> <code>${log.id}</code><br>
                        <strong>模块:</strong> <span class="badge bg-secondary">${log.module}</span><br>
                        <strong>级别:</strong> <span class="badge bg-${getLevelColor(log.level)}">${log.level}</span>
                    </div>
                    <div class="mb-3">
                        <strong>上下文数据:</strong><br>
                        <div class="log-context" style="margin-top: 8px;">${log.context ? formatJSON(log.context) : '暂无上下文信息'}</div>
                    </div>
                `;
                
                document.getElementById('logDetailModal').querySelector('.modal-title').textContent = '日志上下文';
                new bootstrap.Modal(document.getElementById('logDetailModal')).show();
            }
        })
        .catch(error => {
            console.error('Error loading log context:', error);
            console.error('加载日志上下文失败:', error.message);
        });
}

// 查看调试信息
function viewLogDebug(logId) {
    fetch(`/logs/api/detail/${logId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const log = data.data.log;
                const content = document.getElementById('logDetailContent');
                
                content.innerHTML = `
                    <div class="mb-3">
                        <h6><i class="fas fa-bug me-2"></i>调试信息</h6>
                        <hr>
                    </div>
                    <div class="mb-3">
                        <strong>日志ID:</strong> <code>${log.id}</code><br>
                        <strong>模块:</strong> <span class="badge bg-secondary">${log.module}</span><br>
                        <strong>级别:</strong> <span class="badge bg-${getLevelColor(log.level)}">${log.level}</span><br>
                        <strong>时间:</strong> ${formatTime(log.timestamp, 'datetime')}
                    </div>
                    <div class="mb-3">
                        <strong>错误消息:</strong><br>
                        <div class="alert alert-danger border-0">${log.message}</div>
                    </div>
                    <div class="mb-3">
                        <strong>堆栈追踪:</strong><br>
                        <div class="log-traceback" style="margin-top: 8px;">${log.traceback || '暂无堆栈追踪信息'}</div>
                    </div>
                    ${log.context ? `
                        <div class="mb-3">
                            <strong>调试上下文:</strong><br>
                            <div class="log-context" style="margin-top: 8px;">${formatJSON(log.context)}</div>
                        </div>
                    ` : ''}
                `;
                
                document.getElementById('logDetailModal').querySelector('.modal-title').textContent = '调试信息';
                new bootstrap.Modal(document.getElementById('logDetailModal')).show();
            }
        })
        .catch(error => {
            console.error('Error loading log debug info:', error);
            console.error('加载调试信息失败:', error.message);
        });
}


// 回车搜索
document.getElementById('searchTerm').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchLogs();
    }
});
})();