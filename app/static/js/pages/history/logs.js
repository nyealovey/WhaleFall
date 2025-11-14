/**
 * 日志仪表板页面 JavaScript：负责日志检索、筛选、分页与详情查看。
 */
(function (global) {
    'use strict';

    const helpers = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载日志页面脚本');
        return;
    }

    const LodashUtils = global.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

    const { ready, selectOne, select, from } = helpers;

    const LOG_FILTER_FORM_ID = 'logs-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    let currentPage = 1;
    let currentFilters = {};
    let logFilterEventHandler = null;

    ready(() => {
        initializePage();
    });

    function initializePage() {
        loadModules();
        setDefaultTimeRange();
        loadStats();
        searchLogs();
        registerLogFilterForm();
        subscribeLogFilters();
    }

    function normalizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        return value.trim().toLowerCase();
    }

    function hasMeaningfulValue(value) {
        if (value === undefined || value === null) {
            return false;
        }
        if (typeof value === 'string') {
            return value.trim() !== '';
        }
        if (Array.isArray(value)) {
            return value.length > 0;
        }
        return true;
    }

    function prepareModuleOptions(modules) {
        const collection = Array.isArray(modules) ? modules : [];
        const compacted = LodashUtils.compact(collection);
        const uniqueModules = LodashUtils.uniq(compacted);
        return LodashUtils.orderBy(uniqueModules, [normalizeText], ['asc']);
    }

    function buildFilterParams(rawValues) {
        const sourceValues =
            rawValues && Object.keys(rawValues || {}).length
                ? rawValues
                : collectFormValues(selectOne(`#${LOG_FILTER_FORM_ID}`).first());
        const timeRangeValue = sourceValues?.time_range || sourceValues?.timeRange || '';
        const hoursValue = sourceValues?.hours || (timeRangeValue ? getHoursFromTimeRange(timeRangeValue) : undefined);

        const candidate = {
            level: sourceValues?.level,
            module: sourceValues?.module,
            q: sourceValues?.search || sourceValues?.q,
            hours: hoursValue,
        };

        const result = {};
        Object.entries(candidate).forEach(([key, value]) => {
            if (hasMeaningfulValue(value)) {
                result[key] = typeof value === 'string' ? value.trim() : value;
            }
        });

        if (!hasMeaningfulValue(result.hours)) {
            result.hours = 24;
        }
        return result;
    }

    function ensureCurrentFilters() {
        if (!Object.keys(currentFilters).length) {
            currentFilters = buildFilterParams();
        }
        return currentFilters;
    }

    function setDefaultTimeRange() {
        const timeRangeSelect = selectOne('#time_range');
        if (!timeRangeSelect.length) {
            return;
        }

        const defaultValue = '1d';
        const selectElement = timeRangeSelect.first();
        if (selectElement.tomselect) {
            const currentValue = selectElement.tomselect.getValue();
            if (!currentValue) {
                selectElement.tomselect.setValue(defaultValue, true);
            }
        } else if (!selectElement.value) {
            selectElement.value = defaultValue;
        }
    }

    function loadModules() {
        global.httpU
            .get('/logs/api/modules')
            .then((data) => {
                if (data.success) {
                    updateModuleFilter(data.data.modules);
                }
            })
            .catch((error) => {
                console.error('加载模块列表失败:', error);
            });
    }

    function updateModuleFilter(modules) {
        const moduleSelectWrapper = selectOne('#module');
        if (!moduleSelectWrapper.length) {
            return;
        }
        const moduleSelect = moduleSelectWrapper.first();
        const options = prepareModuleOptions(modules);
        const previousValue = moduleSelect.value;

        if (moduleSelect.tomselect) {
            const ts = moduleSelect.tomselect;
            const currentValue = ts.getValue();
            ts.clearOptions();
            ts.addOption({ value: '', text: '全部模块' });
            options.forEach((moduleName) => {
                ts.addOption({ value: moduleName, text: moduleName });
            });
            ts.refreshOptions(false);
            if (currentValue && options.includes(currentValue)) {
                ts.setValue(currentValue, true);
            } else {
                ts.setValue('', true);
            }
        } else {
            moduleSelect.innerHTML = '<option value="">全部模块</option>';
            options.forEach((moduleName) => {
                const option = document.createElement('option');
                option.value = moduleName;
                option.textContent = moduleName;
                moduleSelect.appendChild(option);
            });
            if (previousValue && options.includes(previousValue)) {
                moduleSelect.value = previousValue;
            }
        }
    }

    function loadStats() {
        const filters = ensureCurrentFilters();
        const params = buildLogQueryParams({ ...filters });

        global.httpU
            .get(`/logs/api/stats?${params.toString()}`)
            .then((data) => {
                if (data.success) {
                    updateStatsDisplay(data.data);
                }
            })
            .catch((error) => {
                console.error('加载统计信息失败:', error);
            });
    }

    function getHoursFromTimeRange(timeRange) {
        switch (timeRange) {
            case '1h':
                return 1;
            case '1d':
                return 24;
            case '1w':
                return 168;
            case '1m':
                return 720;
            default:
                return 24;
        }
    }

    function updateStatsDisplay(stats) {
        const elements = {
            totalLogs: stats.total_logs || 0,
            errorLogs: stats.error_logs || 0,
            warningLogs: stats.warning_logs || 0,
            modulesCount: stats.modules_count || 0,
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = selectOne(`#${id}`);
            if (element.length) {
                element.text(value);
                element.addClass('fade-in');
            }
        });
    }

    function showLoadingState() {
        const container = selectOne('#logsContainer');
        if (container.length) {
            container.html('<div class="loading"><i class="fas fa-spinner fa-spin me-2"></i>搜索中...</div>');
        }
    }

    function showError(message) {
        global.toast.error(message);
    }

    function searchLogs(page = 1) {
        currentPage = page;
        const filters = ensureCurrentFilters();

        const params = buildLogQueryParams({
            ...filters,
            page,
            per_page: 20,
        });

        showLoadingState();

        global.httpU
            .get(`/logs/api/search?${params}`)
            .then((data) => {
                if (data.success) {
                    displayLogs(data.data.logs);
                    displayPagination(data.data.pagination);
                } else {
                    showError(`搜索失败: ${data.message}`);
                }
            })
            .catch((error) => {
                console.error('搜索日志失败:', error);
                showError(`搜索出错: ${error.message}`);
            });
    }

    function displayLogs(logs) {
        const container = selectOne('#logsContainer');
        if (!container.length) {
            return;
        }

        if (!logs || logs.length === 0) {
            container.html('<div class="no-logs"><i class="fas fa-search"></i><br>没有找到匹配的日志</div>');
            return;
        }

        const filters = ensureCurrentFilters();
        container.html('<div class="logs-wrapper"></div>');
        const wrapper = container.find('.logs-wrapper');
        logs.forEach((log) => {
            wrapper.append(createLogEntryElement(log, filters.q));
        });
    }

    function createLogEntryElement(log, searchTerm) {
        const levelClass = `log-level-${log.level}`;
        const levelBadge = getLevelBadgeHTML(log.level);
        const moduleBadge = log.module
            ? `<span class="module-badge">${log.module}</span>`
            : '<span class="module-badge empty">-</span>';
        const timestamp = global.timeUtils.formatTime(log.timestamp, 'datetime');
        const message = highlightSearchTerm(log.message, searchTerm);

        const entry = document.createElement('div');
        entry.className = `log-entry ${levelClass}`;
        entry.setAttribute('data-log-id', log.id);
        entry.innerHTML = `
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
        `;
        from(entry).on('click', () => viewLogDetail(log.id));
        return entry;
    }

    function getLevelBadgeHTML(level) {
        const colors = {
            DEBUG: 'secondary',
            INFO: 'info',
            WARNING: 'warning',
            ERROR: 'danger',
            CRITICAL: 'dark',
        };
        const color = colors[level] || 'secondary';
        return `<span class="badge bg-${color} log-level-badge">${level}</span>`;
    }

    function highlightSearchTerm(text, searchTerm) {
        if (!searchTerm) {
            return text;
        }
        const normalizedText = text == null ? '' : String(text);
        const trimmed = searchTerm.trim();
        if (!trimmed) {
            return normalizedText;
        }
        const escaped =
            typeof LodashUtils.escapeRegExp === 'function'
                ? LodashUtils.escapeRegExp(trimmed)
                : trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (!escaped) {
            return normalizedText;
        }
        const regex = new RegExp(`(${escaped})`, 'gi');
        return normalizedText.replace(regex, '<span class="search-highlight">$1</span>');
    }

    function displayPagination(pagination) {
        const container = selectOne('#paginationContainer');
        if (!container.length) {
            return;
        }
        if (!pagination) {
            container.html('');
            return;
        }

        const pages = buildPaginationPages(pagination);
        const html = pages
            .map((page) => {
                if (page.type === 'ellipsis') {
                    return '<li class="page-item disabled"><span class="page-link">...</span></li>';
                }
                if (page.type === 'prev' || page.type === 'next') {
                    return `<li class="page-item${page.disabled ? ' disabled' : ''}">
                        <a class="page-link" href="#" data-page="${page.page}">${page.label}</a>
                    </li>`;
                }
                return `<li class="page-item${page.active ? ' active' : ''}">
                    <a class="page-link" href="#" data-page="${page.page}">${page.page}</a>
                </li>`;
            })
            .join('');

        container.html(`<nav><ul class="pagination">${html}</ul></nav>`);

        container.find('a.page-link').on('click', (event) => {
            event.preventDefault();
            const value = event.currentTarget.getAttribute('data-page');
            const targetPage = Number(value);
            if (Number.isInteger(targetPage)) {
                searchLogs(targetPage);
            }
        });
    }

    function buildPaginationPages(pagination) {
        const pages = [];
        const current = pagination.page;
        const total = pagination.pages;

        pages.push({
            type: 'prev',
            label: '上一页',
            page: pagination.prev_num || current,
            disabled: !pagination.has_prev,
        });

        const startPage = Math.max(1, current - 2);
        const endPage = Math.min(total, current + 2);

        if (startPage > 1) {
            pages.push({ type: 'page', page: 1, active: current === 1 });
            if (startPage > 2) {
                pages.push({ type: 'ellipsis' });
            }
        }

        for (let i = startPage; i <= endPage; i += 1) {
            pages.push({ type: 'page', page: i, active: i === current });
        }

        if (endPage < total) {
            if (endPage < total - 1) {
                pages.push({ type: 'ellipsis' });
            }
            pages.push({ type: 'page', page: total, active: current === total });
        }

        pages.push({
            type: 'next',
            label: '下一页',
            page: pagination.next_num || current,
            disabled: !pagination.has_next,
        });

        return pages;
    }

    function buildLogQueryParams(filters) {
        const params = new URLSearchParams();
        Object.entries(filters || {}).forEach(([key, value]) => {
            if (Array.isArray(value)) {
                value.forEach((item) => params.append(key, item));
            } else if (value !== undefined && value !== null) {
                params.append(key, value);
            }
        });
        return params;
    }

    function registerLogFilterForm() {
        if (!global.FilterUtils) {
            console.warn('FilterUtils 未加载，跳过日志筛选初始化');
            return;
        }
        const selector = `#${LOG_FILTER_FORM_ID}`;
        const form = selectOne(selector);
        if (!form.length) {
            return;
        }
        global.FilterUtils.registerFilterForm(selector, {
            onSubmit: ({ form, event }) => {
                event?.preventDefault?.();
                applyLogFilters(form);
            },
            onClear: ({ form, event }) => {
                event?.preventDefault?.();
                resetLogFilters(form);
            },
            autoSubmitOnChange: true,
        });
    }

    function subscribeLogFilters() {
        if (!global.EventBus) {
            return;
        }
        const formElement = selectOne(`#${LOG_FILTER_FORM_ID}`).first();
        if (!formElement) {
            return;
        }
        const handler = (detail) => {
            if (!detail) {
                return;
            }
            const incoming = (detail.formId || '').replace(/^#/, '');
            if (incoming !== LOG_FILTER_FORM_ID) {
                return;
            }
            switch (detail.action) {
                case 'clear':
                    resetLogFilters(formElement);
                    break;
                case 'change':
                    if (AUTO_APPLY_FILTER_CHANGE) {
                        applyLogFilters(formElement, detail.values);
                    }
                    break;
                case 'submit':
                    applyLogFilters(formElement, detail.values);
                    break;
                default:
                    break;
            }
        };

        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.on(`filters:${action}`, handler);
        });
        logFilterEventHandler = handler;

        from(global).on('beforeunload', cleanupLogFilters);
    }

    function cleanupLogFilters() {
        if (!global.EventBus || !logFilterEventHandler) {
            return;
        }
        ['change', 'submit', 'clear'].forEach((action) => {
            global.EventBus.off(`filters:${action}`, logFilterEventHandler);
        });
        logFilterEventHandler = null;
    }

    function applyLogFilters(form, values) {
        const targetForm = form || selectOne(`#${LOG_FILTER_FORM_ID}`).first();
        if (!targetForm) {
            return;
        }
        currentFilters = buildFilterParams(values);
        searchLogs(1);
    }

    function resetLogFilters(form) {
        const targetForm = form || selectOne(`#${LOG_FILTER_FORM_ID}`).first();
        if (targetForm) {
            targetForm.reset();
        }
        currentFilters = {};
        searchLogs(1);
    }

    function collectFormValues(form) {
        if (!form) {
            return {};
        }
        if (global.FilterUtils && typeof global.FilterUtils.serializeForm === 'function') {
            return global.FilterUtils.serializeForm(form);
        }
        const formData = new FormData(form);
        const result = {};
        formData.forEach((value, key) => {
            const normalized = value instanceof File ? value.name : value;
            if (result[key] === undefined) {
                result[key] = normalized;
            } else if (Array.isArray(result[key])) {
                result[key].push(normalized);
            } else {
                result[key] = [result[key], normalized];
            }
        });
        return result;
    }

    function viewLogDetail(logId) {
        global.httpU
            .get(`/logs/api/detail/${logId}`)
            .then((data) => {
                if (data.success) {
                    displayLogDetail(data.data.log || data.log || data.data);
                } else {
                    showError(`加载日志详情失败: ${data.message}`);
                }
            })
            .catch((error) => {
                console.error('加载日志详情失败:', error);
                showError(`加载日志详情失败: ${error.message}`);
            });
    }

    function displayLogDetail(log) {
        const contentWrapper = selectOne('#logDetailContent');
        if (!contentWrapper.length) {
            return;
        }
        const safeLog = log || {};
        const detailHtml = `
            <div class="mb-3">
                <strong>日志 ID：</strong>${safeLog.id || '-'}
            </div>
            <div class="mb-3">
                <strong>级别：</strong>${safeLog.level || '-'}
            </div>
            <div class="mb-3">
                <strong>模块：</strong>${safeLog.module || '-'}
            </div>
            <div class="mb-3">
                <strong>时间：</strong>${safeLog.timestamp ? global.timeUtils.formatTime(safeLog.timestamp, 'datetime') : '-'}
            </div>
            <div class="mb-3">
                <strong>消息：</strong>
                <pre class="bg-light p-3 rounded">${escapeHtml(safeLog.message || '')}</pre>
            </div>
            <div class="mb-3">
                <strong>详情：</strong>
                <pre class="bg-light p-3 rounded">${escapeHtml(JSON.stringify(safeLog.context || safeLog.metadata || {}, null, 2))}</pre>
            </div>
        `;
        contentWrapper.html(detailHtml);

        const modalElement = selectOne('#logDetailModal').first();
        if (modalElement && global.bootstrap?.Modal) {
            global.bootstrap.Modal.getOrCreateInstance(modalElement).show();
        }
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
})(window);
