/**
 * 日志仪表板页面JavaScript
 * 处理日志搜索、筛选、分页、详情查看等功能
 */

// 全局变量
let currentPage = 1;
let currentFilters = {};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function () {
    initializePage();
    setupFilterForm();
});

// 初始化页面
function initializePage() {
    loadModules();
    // 设置默认时间范围为今天
    setDefaultTimeRange();
    loadStats();
    searchLogs();
}

function setupFilterForm() {
    if (!window.FilterUtils) {
        return;
    }
    const entry = FilterUtils.registerFilterForm('#logs-filter-form', {
        onSubmit: () => {
            currentPage = 1;
            applyFilters();
        },
        onClear: () => {
            currentFilters = {};
            clearFilters();
        },
        autoSubmitOnChange: false,
    });

    const form = entry?.element || document.getElementById('logs-filter-form');
    if (!form) {
        return;
    }

    const searchInput = form.querySelector('#search');
    if (searchInput) {
        searchInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                applyFilters();
            }
        });
    }

    form.querySelectorAll('select').forEach((select) => {
        select.addEventListener('change', () => {
            applyFilters();
        });
    });
}

// 设置默认时间范围
function setDefaultTimeRange() {
    const timeRangeSelect = document.getElementById('time_range');
    if (!timeRangeSelect) {
        return;
    }

    const defaultValue = '1d';
    if (timeRangeSelect.tomselect) {
        const currentValue = timeRangeSelect.tomselect.getValue();
        if (!currentValue) {
            timeRangeSelect.tomselect.setValue(defaultValue, true);
        }
    } else if (!timeRangeSelect.value) {
        timeRangeSelect.value = defaultValue;
    }
}

// 加载模块列表
function loadModules() {
    http.get('/logs/api/modules')
        .then(data => {
            if (data.success) {
                updateModuleFilter(data.data.modules);
            }
        })
        .catch(error => {
            console.error('Error loading modules:', error);
        });
}

// 更新模块筛选器
function updateModuleFilter(modules) {
    const moduleSelect = document.getElementById('module');
    if (!moduleSelect) {
        return;
    }

    const options = modules || [];
    const previousValue = moduleSelect.value;

    if (moduleSelect.tomselect) {
        const ts = moduleSelect.tomselect;
        const currentValue = ts.getValue();
        ts.clearOptions();
        ts.addOption({ value: '', text: '全部模块' });
        options.forEach((module) => {
            ts.addOption({ value: module, text: module });
        });
        ts.refreshOptions(false);
        if (currentValue && options.includes(currentValue)) {
            ts.setValue(currentValue, true);
        } else {
            ts.setValue('', true);
        }
    } else {
        moduleSelect.innerHTML = '<option value="">全部模块</option>';
        options.forEach((module) => {
            const option = document.createElement('option');
            option.value = module;
            option.textContent = module;
            moduleSelect.appendChild(option);
        });
        if (previousValue && options.includes(previousValue)) {
            moduleSelect.value = previousValue;
        }
    }
}

// 加载统计信息
function loadStats() {
    // 构建查询参数，包含当前的筛选条件
    const params = new URLSearchParams();

    // 获取当前筛选条件
    const levelEl = document.getElementById('level');
    const moduleEl = document.getElementById('module');
    const searchEl = document.getElementById('search');
    const timeRangeEl = document.getElementById('time_range');

    if (levelEl && levelEl.value) params.append('level', levelEl.value);
    if (moduleEl && moduleEl.value) params.append('module', moduleEl.value);
    if (searchEl && searchEl.value) params.append('q', searchEl.value);
    if (timeRangeEl && timeRangeEl.value) {
        // 将时间范围转换为小时数
        const hours = getHoursFromTimeRange(timeRangeEl.value);
        if (hours) params.append('hours', hours);
    }

    http.get(`/logs/api/stats?${params.toString()}`)
        .then(data => {
            if (data.success) {
                updateStatsDisplay(data.data);
            }
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

// 将时间范围转换为小时数
function getHoursFromTimeRange(timeRange) {
    switch (timeRange) {
        case '1h':
            return 1; // 1小时
        case '1d':
            return 24; // 1天
        case '1w':
            return 168; // 1周 (7天)
        case '1m':
            return 720; // 1月 (30天)
        default:
            return 24; // 默认1天
    }
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

    // 如果currentFilters为空，从DOM元素获取（兼容旧代码）
    if (Object.keys(currentFilters).length === 0) {
        const levelFilter = document.getElementById('level');
        const moduleFilter = document.getElementById('module');
        const searchInput = document.getElementById('search');
        const timeRange = document.getElementById('time_range');

        currentFilters = {
            level: levelFilter ? levelFilter.value : '',
            module: moduleFilter ? moduleFilter.value : '',
            q: searchInput ? searchInput.value : '',
            hours: timeRange ? getHoursFromTimeRange(timeRange.value) : 24
        };
    }

    // 构建查询参数
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('per_page', '20');

    // 添加筛选条件
    if (currentFilters.level) params.append('level', currentFilters.level);
    if (currentFilters.module) params.append('module', currentFilters.module);
    if (currentFilters.q) params.append('q', currentFilters.q);
    if (currentFilters.hours) params.append('hours', currentFilters.hours);


    // 显示加载状态
    showLoadingState();

    // 发送请求
    http.get(`/logs/api/search?${params}`)
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

    let html = '<div class="logs-wrapper">';
    logs.forEach(log => {
        html += createLogEntryHTML(log);
    });
    html += '</div>';

    container.innerHTML = html;
}

// 创建日志条目HTML
function createLogEntryHTML(log) {
    const levelClass = `log-level-${log.level}`;
    const levelBadge = getLevelBadgeHTML(log.level);
    const moduleBadge = log.module ? `<span class="module-badge">${log.module}</span>` : '<span class="module-badge empty">-</span>';
    const timestamp = timeUtils.formatTime(log.timestamp, 'datetime');
    const message = highlightSearchTerm(log.message, currentFilters.q);

    return `
        <div class="log-entry ${levelClass}" onclick="viewLogDetail(${log.id})">
            <div class="log-entry-content">
                <span class="log-id">ID: ${log.id}</span>
                <div class="log-main-info">
                    <div class="log-message">${message}</div>
                    <div class="log-header">
                        ${levelBadge}
                        ${moduleBadge}
                        <span class="log-timestamp">${timestamp}</span>
                    </div>
                </div>
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
    http.get(`/logs/api/detail/${logId}`)
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
    const timestamp = timeUtils.formatTime(log.timestamp, 'datetime');
    const createdAt = timeUtils.formatTime(log.created_at, 'datetime');

    content.innerHTML = `
        <div class="log-detail-item">
            <div class="log-detail-label">基本信息</div>
            <div class="log-detail-value">
                <div class="row">
                    <div class="col-6">
                        <strong>时间:</strong> ${timestamp}<br>
                        <strong>级别:</strong> ${levelBadge}<br>
                        <strong>模块:</strong> ${moduleBadge || '<span class="text-muted">未知</span>'}
                    </div>
                    <div class="col-6">
                        <strong>ID:</strong> <code>${log.id}</code><br>
                        <strong>创建时间:</strong> ${createdAt}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="log-detail-item">
            <div class="log-detail-label">消息内容</div>
            <div class="log-detail-value">
                <div class="alert alert-info mb-0">${log.message}</div>
            </div>
        </div>
        
        ${log.context ? `
            <div class="log-detail-item">
                <div class="log-detail-label">上下文信息</div>
                <div class="log-detail-value">
                    <div class="log-json-block">${formatJSON(log.context)}</div>
                </div>
            </div>
        ` : ''}
        
        ${log.traceback ? `
            <div class="log-detail-item">
                <div class="log-detail-label">堆栈跟踪</div>
                <div class="log-detail-value">
                    <div class="log-traceback-block">${escapeHtml(log.traceback)}</div>
                </div>
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
            return escapeHtml(obj);
        }
    }
    return escapeHtml(JSON.stringify(obj, null, 2));
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 复制日志详情
function copyLogDetail() {
    const content = document.getElementById('logDetailContent');
    if (!content) return;

    // 获取纯文本内容
    const textContent = content.innerText;

    // 复制到剪贴板
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textContent).then(() => {
            showSuccess('日志详情已复制到剪贴板');
        }).catch(err => {
            console.error('复制失败:', err);
            showError('复制失败，请手动选择文本复制');
        });
    } else {
        // 降级方案：选择文本
        const range = document.createRange();
        range.selectNode(content);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);

        try {
            document.execCommand('copy');
            showSuccess('日志详情已复制到剪贴板');
        } catch (err) {
            showError('复制失败，请手动选择文本复制');
        }

        window.getSelection().removeAllRanges();
    }
}

// 格式化时间 - 直接使用全局函数
// 注意：本文件不再定义formatTime函数，直接使用window.formatTime

// 重置筛选器
function resetFilters() {
    const levelFilter = document.getElementById('level');
    const moduleFilter = document.getElementById('module');
    const searchInput = document.getElementById('search');
    const timeRange = document.getElementById('time_range');

    if (levelFilter) {
        if (levelFilter.tomselect) {
            levelFilter.tomselect.clear(true);
        } else {
            levelFilter.value = '';
        }
    }
    if (moduleFilter) {
        if (moduleFilter.tomselect) {
            moduleFilter.tomselect.clear(true);
        } else {
            moduleFilter.value = '';
        }
    }
    if (searchInput) {
        searchInput.value = '';
    }
    if (timeRange) {
        if (timeRange.tomselect) {
            timeRange.tomselect.setValue('1d', true);
        } else {
            timeRange.value = '1d';
        }
    }

    searchLogs(1);
}

// 显示错误信息
function showError(message) {
    toast.error(message);
}

// 显示成功信息
function showSuccess(message) {
    toast.success(message);
}

// 应用筛选条件
function applyFilters() {
    // 从统一搜索组件获取筛选条件
    const levelEl = document.getElementById('level');
    const moduleEl = document.getElementById('module');
    const searchEl = document.getElementById('search');
    const timeRangeEl = document.getElementById('time_range');

    // 获取筛选值，空字符串表示不过滤
    const level = levelEl?.value || '';
    const module = moduleEl?.value || '';
    const search = searchEl?.value || '';
    const timeRange = timeRangeEl?.value || '1d';

    // 将时间范围转换为小时数
    const hours = getHoursFromTimeRange(timeRange);

    currentFilters = {
        level: level,
        module: module,
        q: search,
        hours: hours || 24
    };

    currentPage = 1;
    // 更新统计卡片和日志列表
    loadStats();
    searchLogs(1);
}

// 将函数暴露到全局作用域
window.applyFilters = applyFilters;

// 清除筛选条件
window.clearFilters = function () {
    currentFilters = {};
    // 重置时间范围为最近1天
    const timeRangeEl = document.getElementById('time_range');
    if (timeRangeEl) {
        if (timeRangeEl.tomselect) {
            timeRangeEl.tomselect.setValue('1d', true);
        } else {
            timeRangeEl.value = '1d';
        }
    }
    // 更新统计卡片和日志列表
    loadStats();
    searchLogs(1);
}

// 导出函数供全局使用
window.searchLogs = searchLogs;
window.viewLogDetail = viewLogDetail;
window.resetFilters = resetFilters;
window.copyLogDetail = copyLogDetail;
