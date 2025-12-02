/**
 * 日志管理页面模块。
 *
 * 提供日志列表展示、筛选、统计和详情查看功能。
 *
 * @module LogsPage
 */
(function (global) {
    'use strict';

    const LOG_FILTER_FORM_ID = 'logs-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    let helpers = null;
    let logsService = null;
    let logsGrid = null;
    let logFilterCard = null;
    let logDetailModalController = null;
    const logCache = new Map();

    /**
     * 挂载日志页面。
     *
     * 初始化所有必需的组件，包括网格、筛选器和模态框。
     *
     * @param {void} 无参数。IIFE 内直接调用。
     * @returns {void}
     */
    function mount() {
        helpers = global.DOMHelpers;
        if (!helpers) {
            console.error('DOMHelpers 未初始化，无法加载日志页面脚本');
            return;
        }
        if (!global.gridjs || !global.GridWrapper) {
            console.error('Grid.js 或 GridWrapper 未加载');
            return;
        }
        if (!global.LogsService) {
            console.error('LogsService 未初始化');
            return;
        }
        logsService = new global.LogsService(global.httpU);

        const { ready } = helpers;
        ready(() => {
            setDefaultTimeRange();
            initializeLogDetailModal();
            initializeGrid();
            initializeFilterCard();
            refreshStats(resolveFilters());
        });
    }

    /**
     * 初始化日志列表网格。
     *
     * @param {void} 无参数。直接操作 #logs-grid。
     * @returns {void}
     */
    function initializeGrid() {
        const container = document.getElementById('logs-grid');
        if (!container) {
            console.warn('未找到日志列表容器');
            return;
        }
        logsGrid = new global.GridWrapper(container, {
            columns: buildColumns(),
            server: {
                url: '/history/logs/api/list?sort=timestamp&order=desc',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                then: handleServerResponse,
                total: (response) => {
                    const payload = response?.data || response || {};
                    return payload.total || 0;
                },
            },
        });
        const initialFilters = sanitizeFilters(resolveFilters());
        logsGrid.setFilters(initialFilters, { silent: true });
        logsGrid.init();
    }

    /**
     * 处理服务器响应数据。
     *
     * @param {Object} response - 服务器响应对象
     * @return {Array} 格式化后的行数据数组
     */
    function handleServerResponse(response) {
        const payload = response?.data || response || {};
        const items = Array.isArray(payload.items) ? payload.items : [];
        logCache.clear();
        return items.map((item) => {
            const normalized = normalizeLogItem(item);
            logCache.set(normalized.id, normalized);
            return [
                normalized.timestamp_display || '-',
                normalized.level || '-',
                normalized.module || '-',
                normalized.message || '',
                normalized.tags || [],
                '',
                normalized,
            ];
        });
    }

    /**
     * 构建网格列配置。
     *
     * @param {void} 无参数。使用全局 gridjs 渲染器。
     * @return {Array} 列配置数组
     */
    function buildColumns() {
        const gridHtml = global.gridjs?.html;
        return [
            {
                name: '时间',
                id: 'timestamp',
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const text = meta.timestamp_display || cell || '-';
                    return gridHtml
                        ? gridHtml(`<span class="text-nowrap">${escapeHtml(text)}</span>`)
                        : text;
                },
            },
            {
                name: '级别',
                id: 'level',
                formatter: (cell, row) => renderLogLevel(resolveRowMeta(row), gridHtml),
            },
            {
                name: '模块',
                id: 'module',
                formatter: (cell) => renderModuleChip(cell, gridHtml),
            },
            {
                name: '消息',
                id: 'message',
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    const text = meta.message || cell || '';
                    if (!gridHtml) {
                        return text;
                    }
                    const escaped = escapeHtml(text);
                    return gridHtml(
                        `<div class="log-message-cell text-truncate" style="max-width: 480px;" title="${escaped}">${escaped}</div>`
                    );
                },
            },
            {
                name: '标签',
                id: 'tags',
                formatter: (cell, row) => renderContextChips(resolveRowMeta(row).tags || cell || [], gridHtml),
            },
            {
                name: '操作',
                id: 'actions',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    if (!meta.id) {
                        return '';
                    }
                    return gridHtml ? renderActionButton(meta.id) : '详情';
                },
            },
            { id: '__meta__', hidden: true },
        ];
    }

    /**
     * 渲染日志级别徽章。
     *
     * @param {Object} log - 日志对象
     * @param {Function} gridHtml - Grid.js HTML 渲染函数
     * @return {string|Object} 渲染的 HTML 或纯文本
     */
    function renderLogLevel(log, gridHtml) {
        const level = (log.level || 'INFO').toUpperCase();
        const variantMap = {
            DEBUG: 'muted',
            INFO: 'info',
            WARNING: 'warning',
            ERROR: 'danger',
            CRITICAL: 'danger',
        };
        const iconMap = {
            DEBUG: 'fa-bug',
            INFO: 'fa-info-circle',
            WARNING: 'fa-exclamation-triangle',
            ERROR: 'fa-times-circle',
            CRITICAL: 'fa-fire-alt',
        };
        const variant = variantMap[level] || 'muted';
        const icon = iconMap[level] || 'fa-info-circle';
        return renderStatusPill(level, variant, icon, gridHtml);
    }

    /**
     * 从行数据中解析元数据。
     *
     * @param {Object} row - 行对象
     * @return {Object} 元数据对象
     */
    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    /**
     * 规范化日志项数据。
     *
     * @param {Object} item - 原始日志项
     * @return {Object} 规范化后的日志对象
     */
    function normalizeLogItem(item) {
        return {
            id: item.id,
            timestamp: item.timestamp,
            timestamp_display: item.timestamp_display || item.timestamp || '-',
            level: item.level || '-',
            module: item.module || '-',
            message: item.message || '',
            context: item.context,
            traceback: item.traceback,
            tags: resolveLogTags(item),
        };
    }

    /**
     * 初始化筛选卡片。
     *
     * @param {void} 无参数。调用全局 UI.createFilterCard。
     * @returns {void}
     */
    function initializeFilterCard() {
        const factory = global.UI?.createFilterCard;
        if (!factory) {
            console.error('UI.createFilterCard 未加载，日志筛选无法初始化');
            return;
        }
        logFilterCard = factory({
            formSelector: `#${LOG_FILTER_FORM_ID}`,
            autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
            onSubmit: ({ values }) => handleFilterChange(values),
            onClear: () => handleFilterChange({}),
            onChange: ({ values }) => {
                if (AUTO_APPLY_FILTER_CHANGE) {
                    handleFilterChange(values);
                }
            },
        });
    }

    /**
     * 处理筛选条件变化。
     *
     * @param {Object} values - 筛选值对象
     * @return {void}
     */
    function handleFilterChange(values) {
        const filters = sanitizeFilters(resolveFilters(values));
        logsGrid?.updateFilters(filters);
        refreshStats(filters);
    }

    /**
     * 解析筛选条件。
     *
     * @param {Object} [rawValues] - 原始筛选值
     * @return {Object} 解析后的筛选对象
     */
    function resolveFilters(rawValues) {
        const { selectOne } = helpers;
        const sourceValues =
            rawValues && Object.keys(rawValues || {}).length
                ? rawValues
                : collectFormValues(selectOne(`#${LOG_FILTER_FORM_ID}`).first());
        const timeRangeValue = sourceValues?.time_range || '';
        const hoursValue = sourceValues?.hours || getHoursFromTimeRange(timeRangeValue);
        const filters = {
            search: sanitizeText(sourceValues?.search || sourceValues?.q),
            level: sanitizeText(sourceValues?.level),
            module: sanitizeText(sourceValues?.module),
            hours: Number.isFinite(Number(hoursValue)) ? Number(hoursValue) : 24,
        };
        if (!filters.hours || filters.hours <= 0) {
            filters.hours = 24;
        }
        return filters;
    }

    /**
     * 清理筛选条件，移除空值。
     *
     * @param {Object} filters - 筛选对象
     * @return {Object} 清理后的筛选对象
     */
    function sanitizeFilters(filters) {
        const result = {};
        Object.entries(filters || {}).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '') {
                return;
            }
            result[key] = value;
        });
        return result;
    }

    /**
     * 清理文本值。
     *
     * @param {string} value - 文本值
     * @return {string} 清理后的文本
     */
    function sanitizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        return trimmed === '' ? '' : trimmed;
    }

    /**
     * 收集表单值。
     *
     * @param {HTMLElement} form - 表单元素
     * @return {Object} 表单值对象
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
            if (result[key] === undefined) {
                result[key] = value;
            } else if (Array.isArray(result[key])) {
                result[key].push(value);
            } else {
                result[key] = [result[key], value];
            }
        });
        return result;
    }

    /**
     * 设置默认时间范围。
     *
     * @param {void} 无参数。直接操作 #time_range。
     * @returns {void}
     */
    function setDefaultTimeRange() {
        const { selectOne } = helpers || {};
        if (!selectOne) {
            return;
        }
        const selectWrapper = selectOne('#time_range');
        if (!selectWrapper.length) {
            return;
        }
        const selectElement = selectWrapper.first();
        if (selectElement.tomselect) {
            if (!selectElement.tomselect.getValue()) {
                selectElement.tomselect.setValue('1d', true);
            }
        } else if (!selectElement.value) {
            selectElement.value = '1d';
        }
    }

    /**
     * 从时间范围字符串获取小时数。
     *
     * @param {string} timeRange - 时间范围字符串（如 '1h', '1d', '1w', '1m'）
     * @return {number} 小时数
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
     * 刷新统计数据。
     *
     * @param {Object} filters - 筛选条件对象
     * @return {void}
     */
    function refreshStats(filters) {
        if (!logsService) {
            return;
        }
        const params = Object.assign({}, filters || {});
        if (params.search) {
            params.q = params.search;
        }
        delete params.search;
        logsService
            .fetchStats(params)
            .then((response) => {
                const payload = response?.data || response || {};
                updateStatsDisplay(payload);
            })
            .catch((error) => {
                console.error('获取日志统计失败:', error);
                showStatsError('获取日志统计失败');
            });
    }

    /**
     * 更新统计数据显示。
     *
     * @param {Object} stats - 统计数据对象
     * @return {void}
     */
    function updateStatsDisplay(stats) {
        const mapping = {
            totalLogs: stats.total_logs ?? stats.total ?? 0,
            errorLogs: stats.error_logs ?? stats.error_count ?? 0,
            warningLogs: stats.warning_logs ?? stats.warning_count ?? 0,
            modulesCount: stats.modules_count ?? stats.module_count ?? 0,
        };
        Object.entries(mapping).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (!element) {
                return;
            }
            const format = element.dataset?.statFormat || 'plain';
            let display = value ?? 0;
            if (format === 'count') {
                display = `${display} 条`;
            }
            element.textContent = display;
        });
    }

    /**
     * 显示统计错误消息。
     *
     * @param {string} message - 错误消息
     * @return {void}
     */
    function showStatsError(message) {
        if (global.toast?.error) {
            global.toast.error(message);
        } else {
            console.error(message);
        }
    }

    /**
     * 初始化日志详情模态框。
     *
     * @param {void} 无参数。依赖全局 LogsLogDetailModal。
     * @returns {void}
     */
    function initializeLogDetailModal() {
        if (!global.LogsLogDetailModal?.createController) {
            console.error('LogsLogDetailModal 未加载，无法初始化日志详情模态');
            return;
        }
        try {
            logDetailModalController = global.LogsLogDetailModal.createController({
                ui: global.UI,
                toast: global.toast,
                timeUtils: global.timeUtils,
                modalSelector: '#logDetailModal',
                contentSelector: '#logDetailContent',
                copyButtonSelector: '#copyLogDetailButton',
            });
        } catch (error) {
            console.error('初始化日志详情模态失败:', error);
        }
    }

    /**
     * 转义 HTML 特殊字符。
     *
     * @param {*} value - 要转义的值
     * @return {string} 转义后的字符串
     */
    function escapeHtml(value) {
        if (value === undefined || value === null) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * 根据 ID 打开日志详情。
     *
     * @param {number|string} logId - 日志 ID
     * @return {void}
     */
    function openLogDetailById(logId) {
        const numericId = Number(logId);
        if (!numericId) {
            return;
        }
        const cached = logCache.get(numericId);
        if (cached) {
            logDetailModalController?.open(cached);
            return;
        }
        if (!logsService) {
            return;
        }
        logsService
            .fetchLogDetail(numericId)
            .then((response) => {
                const payload = response?.data || response || {};
                const log = payload.log || payload.data || payload || {};
                logDetailModalController?.open(log);
            })
            .catch((error) => {
                console.error('获取日志详情失败:', error);
                showStatsError('获取日志详情失败');
            });
    }

    /**
     * 日志页面公共接口。
     *
     * @namespace LogsPage
     * @property {Function} mount - 挂载页面
     * @property {Function} openDetail - 打开日志详情
     */
    function renderModuleChip(text, gridHtml) {
        const value = text || '-';
        if (!gridHtml) {
            return value;
        }
        return gridHtml(`<span class="chip-outline chip-outline--muted">${escapeHtml(value)}</span>`);
    }

    function renderContextChips(rawTags, gridHtml) {
        const tags = Array.isArray(rawTags) ? rawTags : [];
        if (!gridHtml) {
            return tags.join(', ') || '无标签';
        }
        return renderChipStack(tags, { emptyText: '无标签' });
    }

    function renderChipStack(items, options = {}) {
        const { emptyText = '', baseClass = 'ledger-chip', counterClass = 'ledger-chip ledger-chip--counter', maxItems = 3 } = options;
        const list = (items || [])
            .map((item) => (typeof item === 'string' ? item.trim() : ''))
            .filter((item) => item.length > 0)
            .map((item) => escapeHtml(item));
        if (!list.length) {
            if (global.gridjs?.html && emptyText) {
                return global.gridjs.html(`<span class="text-muted">${escapeHtml(emptyText)}</span>`);
            }
            return emptyText;
        }
        if (!global.gridjs?.html) {
            return list.join(', ');
        }
        const limit = Number.isFinite(maxItems) ? maxItems : list.length;
        const chips = list.slice(0, limit).map((value) => `<span class="${baseClass}">${value}</span>`);
        if (list.length > limit) {
            chips.push(`<span class="${counterClass}">+${list.length - limit}</span>`);
        }
        return global.gridjs.html(`<div class="ledger-chip-stack">${chips.join('')}</div>`);
    }

    function resolveLogTags(item) {
        if (Array.isArray(item?.tags)) {
            return item.tags.map((tag) => (typeof tag === 'string' ? tag : tag?.display_name || tag?.name)).filter(Boolean);
        }
        const context = item?.context;
        if (context && typeof context === 'object') {
            return Object.entries(context)
                .map(([key, value]) => `${key}:${String(value).slice(0, 30)}`)
                .slice(0, 4);
        }
        return [];
    }

    function renderStatusPill(text, variant = 'muted', icon, gridHtml) {
        if (!gridHtml) {
            return text;
        }
        const classes = ['status-pill'];
        if (variant) {
            classes.push(`status-pill--${variant}`);
        }
        const iconHtml = icon ? `<i class="fas ${icon}" aria-hidden="true"></i>` : '';
        return gridHtml(`<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '')}</span>`);
    }

    function renderActionButton(logId) {
        if (!global.gridjs?.html) {
            return '查看';
        }
        return global.gridjs.html(`
            <button class="btn btn-outline-secondary btn-icon" data-log-id="${logId}" onclick="window.LogsPage.openDetail(${logId})" title="查看详情">
                <i class="fas fa-eye"></i>
            </button>
        `);
    }

    global.LogsPage = {
        mount,
        openDetail: openLogDetailById,
    };
})(window);
