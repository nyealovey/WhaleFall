/**
 * 日志仪表板页面 JavaScript：负责日志检索、筛选、分页与详情查看。
 */
(function (global) {
    'use strict';

    function mount() {
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

        const LogsService = global.LogsService;
        if (!LogsService) {
            console.error('LogsService 未初始化，无法加载日志页面');
            return;
        }
        const logsService = new LogsService(global.httpU);

        const LOG_FILTER_FORM_ID = 'logs-filter-form';
        const AUTO_APPLY_FILTER_CHANGE = true;

        let logsStore = null;
        const storeSubscriptions = [];
        let storeUnloadHandler = null;
        let logFilterCard = null;
        let logDetailModal = null;

        ready(() => {
            initializePage();
        });

    /**
     * 页面入口：store/filter/modal 初始化。
     */
    function initializePage() {
        setDefaultTimeRange();
        initializeLogsStore();
        initializeLogFilterCard();
        initializeLogDetailModal();
        registerUnloadHandlers();
    }

    /**
     * 创建日志 store 并绑定事件。
     */
    function initializeLogsStore() {
        if (!global.createLogsStore) {
            console.error('createLogsStore 未加载');
            return;
        }
        const initialFilters = buildFilterParams();
        try {
            logsStore = global.createLogsStore({
                service: logsService,
                emitter: global.mitt ? global.mitt() : null,
                initialFilters,
            });
        } catch (error) {
            console.error('初始化 LogsStore 失败:', error);
            return;
        }
        bindStoreEvents();
        logsStore.init();
        // 卸载由 registerUnloadHandlers 统一处理
    }

    /**
     * 订阅 store 事件，更新模块、统计、列表等。
     */
    function bindStoreEvents() {
        subscribeToStoreEvent('logs:modulesUpdated', (payload) => {
            updateModuleFilter(payload?.modules || []);
        });
        subscribeToStoreEvent('logs:statsUpdated', (payload) => {
            updateStatsDisplay(payload?.stats || {});
        });
        subscribeToStoreEvent('logs:loading', () => {
            showLoadingState();
        });
        subscribeToStoreEvent('logs:updated', (payload) => {
            const filters = payload?.filters || {};
            const searchTerm = filters.q || filters.search || '';
            displayLogs(payload?.logs || [], searchTerm);
            displayPagination(payload?.pagination || {});
        });
        subscribeToStoreEvent('logs:error', (payload) => {
            const error = payload?.error;
            if (error) {
                console.error('LogsStore error:', error);
            }
            showError(error?.message || '日志操作失败');
        });
        subscribeToStoreEvent('logs:detailLoaded', (payload) => {
            displayLogDetail(payload?.log || {});
        });
    }

    /**
     * 记录订阅，便于销毁。
     */
    function subscribeToStoreEvent(eventName, handler) {
        storeSubscriptions.push({ eventName, handler });
        logsStore.subscribe(eventName, handler);
    }

    /**
     * 卸载日志 store。
     */
    function teardownLogsStore() {
        if (logsStore) {
            storeSubscriptions.forEach(({ eventName, handler }) => {
                logsStore.unsubscribe(eventName, handler);
            });
            storeSubscriptions.length = 0;
            logsStore.destroy?.();
            logsStore = null;
        }
    }

    /**
     * beforeunload 清理。
     */
    function registerUnloadHandlers() {
        if (storeUnloadHandler) {
            from(global).off('beforeunload', storeUnloadHandler);
        }
        storeUnloadHandler = () => {
            destroyLogFilterCard();
            destroyLogDetailModal();
            teardownLogsStore();
            from(global).off('beforeunload', storeUnloadHandler);
            storeUnloadHandler = null;
        };
        from(global).on('beforeunload', storeUnloadHandler);
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

    /**
     * 设置时间范围筛选的默认值（优先保持 TomSelect 状态）。
     */
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

    /**
     * 将模块列表填充到下拉框，保留用户选择。
     */
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

    /**
     * 将快捷时间范围转换为小时数，用于图表或统计。
     */
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

    /**
     * 刷新顶部统计面板数字并应用过渡效果。
     */
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

    /**
     * 在日志容器显示加载提示。
     */
    function showLoadingState() {
        const container = selectOne('#logsContainer');
        if (container.length) {
            container.html('<div class="loading"><i class="fas fa-spinner fa-spin me-2"></i>搜索中...</div>');
        }
    }

    /**
     * 统一错误提示：优先 toast，回退 console。
     */
    function showError(message) {
        if (global.toast && typeof global.toast.error === 'function') {
            global.toast.error(message);
        } else {
            console.error(message);
        }
    }

    /**
     * 调用 store 执行搜索，支持分页参数。
     */
    function searchLogs(page = 1) {
        if (!logsStore) {
            return;
        }
        logsStore.actions.searchLogs({ page });
    }

    /**
     * 将日志列表渲染到 DOM，并高亮搜索关键词。
     */
    function displayLogs(logs, searchTerm = '') {
        const container = selectOne('#logsContainer');
        if (!container.length) {
            return;
        }

        if (!logs || logs.length === 0) {
            container.html('<div class="no-logs"><i class="fas fa-search"></i><br>没有找到匹配的日志</div>');
            return;
        }

        container.html('<div class="logs-wrapper"></div>');
        const wrapper = container.find('.logs-wrapper');
        logs.forEach((log) => {
            wrapper.append(createLogEntryElement(log, searchTerm));
        });
    }

    /**
     * 构建单条日志 DOM 片段并绑定详情点击。
     */
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

    /**
     * 获取日志级别 badge HTML。
     */
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

    /**
     * 在日志 message 中高亮搜索关键词。
     */
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

    /**
     * 渲染分页控件并绑定跳转事件。
     */
    function displayPagination(pagination) {
        const container = selectOne('#paginationContainer');
        if (!container.length) {
            return;
        }
        if (!pagination || (pagination.pages <= 1 && !pagination.has_prev && !pagination.has_next)) {
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

    /**
     * 构造分页按钮结构，含前后页和省略号。
     */
    function buildPaginationPages(pagination) {
        const safe = pagination || {};
        const current = safe.page || 1;
        const total = safe.pages && safe.pages > 0 ? safe.pages : 1;
        const hasPrev = typeof safe.hasPrev === 'boolean' ? safe.hasPrev : Boolean(safe.has_prev);
        const hasNext = typeof safe.hasNext === 'boolean' ? safe.hasNext : Boolean(safe.has_next);
        const prevPage = safe.prevPage ?? safe.prev_num ?? safe.previous_page ?? (hasPrev ? Math.max(1, current - 1) : current);
        const nextPage = safe.nextPage ?? safe.next_num ?? safe.next_page ?? (hasNext ? Math.min(total, current + 1) : current);
        const pages = [];

        pages.push({
            type: 'prev',
            label: '上一页',
            page: prevPage,
            disabled: !hasPrev,
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
            page: nextPage,
            disabled: !hasNext,
        });

        return pages;
    }

    /**
     * 初始化筛选卡片，绑定提交/重置/变更回调。
     */
    function initializeLogFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载，日志筛选无法初始化');
            return;
        }
        logFilterCard = factory({
            formSelector: `#${LOG_FILTER_FORM_ID}`,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => applyLogFilters(null, values),
            onClear: () => applyLogFilters(null, {}),
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    applyLogFilters(null, values);
                }
            },
        });
    }

    /**
     * 销毁筛选卡片实例，释放事件监听。
     */
    function destroyLogFilterCard() {
        if (logFilterCard?.destroy) {
            logFilterCard.destroy();
        }
        logFilterCard = null;
    }

    /**
     * 应用筛选参数并驱动 store 查询。
     */
    function applyLogFilters(form, values) {
        const targetForm = form || logFilterCard?.form || selectOne(`#${LOG_FILTER_FORM_ID}`).first();
        if (!targetForm || !logsStore) {
            return;
        }
        const rawValues =
            values && Object.keys(values || {}).length
                ? values
                : collectFormValues(targetForm);
        const filters = buildFilterParams(rawValues);
        logsStore.actions.applyFilters(filters);
    }

    /**
     * 重置筛选表单并恢复默认过滤。
     */
    function resetLogFilters(form) {
        const targetForm = form || logFilterCard?.form || selectOne(`#${LOG_FILTER_FORM_ID}`).first();
        if (targetForm) {
            targetForm.reset();
        }
        if (!logsStore) {
            return;
        }
        logsStore.actions.resetFilters();
    }

    /**
     * 将 form 序列化为对象，兼容 FilterCard/原生 FormData。
     */
    function collectFormValues(form) {
        if (logFilterCard?.serialize) {
            return logFilterCard.serialize();
        }
        if (!form) {
            return {};
        }
        const serializer = global.UI?.serializeForm;
        if (serializer) {
            return serializer(form);
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

    /**
     * 请求日志详情数据。
     */
    function viewLogDetail(logId) {
        if (!logsStore) {
            return;
        }
        logsStore.actions.loadLogDetail(logId);
    }

    /**
     * 渲染日志详情模态内容。
     */
    function displayLogDetail(log) {
        const contentWrapper = selectOne('#logDetailContent');
        if (!contentWrapper.length) {
            return;
        }
        const safeLog = log && typeof log === 'object' ? log : {};
        const detailPayload = safeLog.context || safeLog.metadata || {};
        const detailTitle = safeLog.context ? '上下文' : safeLog.metadata ? '元数据' : '详情';
        const contextHtml = buildContextContent(detailPayload);
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
            ${
                safeLog.traceback
                    ? `<div class="mb-3">
                        <strong>堆栈：</strong>
                        <pre class="bg-dark text-light p-3 rounded overflow-auto">${escapeHtml(safeLog.traceback)}</pre>
                    </div>`
                    : ''
            }
            <div class="mb-3">
                <strong>${detailTitle}：</strong>
                ${contextHtml}
            </div>
        `;
        contentWrapper.html(detailHtml);

        logDetailModal?.open?.({ logId: safeLog.id });
    }

    /**
     * 将 context/metadata 渲染为分组的 pre 块。
     */
    function buildContextContent(payload) {
        if (payload === null || payload === undefined) {
            return '<div class="text-muted">暂无上下文数据</div>';
        }
        if (typeof payload === 'string') {
            return `<pre class="bg-light p-3 rounded">${escapeHtml(payload)}</pre>`;
        }
        if (typeof payload === 'object') {
            const entries = Object.entries(payload);
            if (entries.length === 0) {
                return '<div class="text-muted">暂无上下文数据</div>';
            }
            const rows = entries
                .map(([key, value]) => {
                    const normalizedValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
                    return `
                        <div class="mb-2">
                            <div class="text-muted small">${escapeHtml(key)}</div>
                            <pre class="bg-light p-3 rounded mb-0">${escapeHtml(String(normalizedValue ?? ''))}</pre>
                        </div>`;
                })
                .join('');
            return `<div class="log-context-section">${rows}</div>`;
        }
        return `<pre class="bg-light p-3 rounded">${escapeHtml(String(payload))}</pre>`;
    }

    /**
     * 基础 HTML 转义。
     */
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

    function copyLogDetail() {
        const content = document.getElementById('logDetailContent');
        if (!content) {
            return;
        }
        const text = content.innerText || content.textContent || '';
        if (!text) {
            if (global.toast && typeof global.toast.info === 'function') {
                global.toast.info('暂无可复制的日志详情');
            }
            return;
        }
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard
                .writeText(text)
                .then(() => {
                    if (global.toast && typeof global.toast.success === 'function') {
                        global.toast.success('日志详情已复制');
                    }
                })
                .catch(() => fallbackCopyText(text));
        } else {
            fallbackCopyText(text);
        }
    }

    /**
     * 复制日志详情的回退方案。
     */
    function fallbackCopyText(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            if (global.toast && typeof global.toast.success === 'function') {
                global.toast.success('日志详情已复制');
            }
        } catch (error) {
            console.error('复制日志详情失败:', error);
        } finally {
            document.body.removeChild(textarea);
        }
    }

    /**
     * 初始化日志详情模态与复制按钮事件。
     */
    function initializeLogDetailModal() {
        const factory = global.UI?.createModal;
        if (!factory) {
            console.error('UI.createModal 未加载，无法初始化日志详情模态框');
            return;
        }
        logDetailModal = factory({
            modalSelector: '#logDetailModal',
        });
        const copyButton = selectOne('#copyLogDetailButton');
        if (copyButton.length) {
            copyButton.on('click', (event) => {
                event?.preventDefault?.();
                copyLogDetail();
            });
        }
    }

    /**
     * 销毁日志详情模态，释放资源。
     */
    function destroyLogDetailModal() {
        if (logDetailModal?.destroy) {
            logDetailModal.destroy();
        }
        logDetailModal = null;
    }

    global.copyLogDetail = copyLogDetail;
    }

    global.LogsPage = {
        mount,
    };
})(window);
