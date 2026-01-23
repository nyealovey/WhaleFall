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

    let helpers = null;
    let logsService = null;
    let gridPage = null;
    let logDetailModalController = null;
    let GridPage = null;
    let GridPlugins = null;
    let escapeHtml = null;
    let rowMeta = null;
    const logCache = new Map();
    const LOG_LEVEL_SELECT_ID = 'level';
    const LOG_LEVEL_SELECT_TONE_CLASSES = [
        'log-level-select--danger',
        'log-level-select--warning',
        'log-level-select--info',
        'log-level-select--muted',
        'log-level-select--default',
    ];

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
        GridPage = global.Views?.GridPage || null;
        GridPlugins = global.Views?.GridPlugins || null;
        if (!GridPage?.mount || !GridPlugins) {
            console.error('Views.GridPage 或 Views.GridPlugins 未加载');
            return;
        }
        escapeHtml = global.UI?.escapeHtml || null;
        rowMeta = global.GridRowMeta || null;
        if (typeof escapeHtml !== 'function' || typeof rowMeta?.get !== 'function') {
            console.error('UI helpers 或 GridRowMeta 未加载');
            return;
        }
        if (!global.LogsService) {
            console.error('LogsService 未初始化');
            return;
        }
        logsService = new global.LogsService();

        const pageRoot = document.getElementById('logs-page-root');
        if (!pageRoot) {
            console.warn('未找到日志中心页面根元素');
            return;
        }

        const { ready } = helpers;
        ready(() => {
            setDefaultTimeRange();
            syncLogLevelSelectTone();
            initializeLogDetailModal();
            initializeGridPage(pageRoot);
            refreshStats(gridPage?.getFilters?.() || resolveFilters());
        });
    }

    /**
     * 初始化日志列表 grid page skeleton。
     *
     * @param {void} 无参数。直接操作 #logs-grid。
     * @returns {void}
     */
    function initializeGridPage(pageRoot) {
        const container = pageRoot.querySelector('#logs-grid');
        if (!container) {
            console.warn('未找到日志列表容器');
            return;
        }

        const statsPlugin = {
            name: 'logsStats',
            onFiltersChanged: (_ctx, { filters }) => {
                syncLogLevelSelectTone();
                refreshStats(filters);
            },
        };

        gridPage = GridPage.mount({
            root: pageRoot,
            grid: '#logs-grid',
            filterForm: `#${LOG_FILTER_FORM_ID}`,
            gridOptions: {
                sort: false,
                columns: buildColumns(),
                server: {
                    url: logsService.getGridUrl(),
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    then: handleServerResponse,
                    total: (response) => {
                        const payload = response?.data || response || {};
                        return payload.total || 0;
                    },
                },
            },
            filters: {
                allowedKeys: ['search', 'level', 'module', 'hours'],
                resolve: (values) => resolveFilters(values),
                normalize: (filters) => normalizeGridFilters(filters),
            },
            plugins: [
                statsPlugin,
                GridPlugins.filterCard({
                    autoSubmitOnChange: true,
                }),
                GridPlugins.actionDelegation({
                    actions: {
                        'open-log-detail': ({ event, el }) => {
                            event.preventDefault();
                            openLogDetailById(el.getAttribute('data-log-id'));
                        },
                    },
                }),
            ],
        });
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
                width: '160px',
                formatter: (cell, row) => {
                    const meta = getRowMeta(row);
                    const text = meta.timestamp_display || cell || '-';
                    return gridHtml
                        ? gridHtml(`<span class="text-nowrap">${escapeHtml(text)}</span>`)
                        : text;
                },
            },
            {
                name: '级别',
                id: 'level',
                width: '120px',
                formatter: (cell, row) => renderLogLevel(getRowMeta(row), gridHtml),
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
                    const meta = getRowMeta(row);
                    const text = meta.message || cell || '';
                    if (!gridHtml) {
                        return text;
                    }
                    const escaped = escapeHtml(text);
                    return gridHtml(
                        `<div class="log-message-cell" title="${escaped}">${escaped}</div>`
                    );
                },
            },
            {
                name: '操作',
                id: 'actions',
                width: '80px',
                sort: false,
                formatter: (cell, row) => {
                    const meta = getRowMeta(row);
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
        const level = (log.level || 'INFO').toString().toUpperCase();
        let variant = 'muted';
        let icon = 'fa-info-circle';
        switch (level) {
            case 'DEBUG':
                variant = 'muted';
                icon = 'fa-bug';
                break;
            case 'INFO':
                variant = 'info';
                icon = 'fa-info-circle';
                break;
            case 'WARNING':
                variant = 'warning';
                icon = 'fa-exclamation-triangle';
                break;
            case 'ERROR':
                variant = 'danger';
                icon = 'fa-times-circle';
                break;
            case 'CRITICAL':
                variant = 'danger';
                icon = 'fa-fire-alt';
                break;
            default:
                break;
        }
        return renderStatusPill(level, variant, icon, gridHtml);
    }

    /**
     * 从行数据中解析元数据。
     *
     * @param {Object} row - 行对象
     * @return {Object} 元数据对象
     */
    function getRowMeta(row) {
        if (rowMeta?.get) {
            return rowMeta.get(row);
        }
        return {};
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
        };
    }

    /**
     * 解析筛选条件。
     *
     * @param {Object} [rawValues] - 原始筛选值
     * @return {Object} 解析后的筛选对象
     */
    function resolveFilters(rawValues) {
        const sourceValues =
            rawValues && Object.keys(rawValues || {}).length ? rawValues : collectFormValues();
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

    function normalizeGridFilters(filters) {
        const source = filters && typeof filters === 'object' ? filters : {};
        const normalized = {};

        const search = sanitizeText(source.search || source.q);
        if (search) {
            normalized.search = search;
        }

        const level = sanitizeText(source.level);
        if (level && level !== 'all') {
            normalized.level = level;
        }

        const moduleValue = sanitizeText(source.module);
        if (moduleValue && moduleValue !== 'all') {
            normalized.module = moduleValue;
        }

        const hoursRaw = Number(source.hours);
        normalized.hours = Number.isFinite(hoursRaw) && hoursRaw > 0 ? Math.floor(hoursRaw) : 24;

        return normalized;
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

    function collectFormValues() {
        const form = document.getElementById(LOG_FILTER_FORM_ID);
        if (!form) {
            return {};
        }
        const serializer = global.UI?.serializeForm;
        if (serializer) {
            return serializer(form);
        }

        const formData = new FormData(form);
        const result = Object.create(null);
        const search = formData.get('search');
        if (search !== null && search !== undefined) {
            result.search = search;
        }
        const level = formData.get('level');
        if (level !== null && level !== undefined) {
            result.level = level;
        }
        const moduleValue = formData.get('module');
        if (moduleValue !== null && moduleValue !== undefined) {
            result.module = moduleValue;
        }
        const timeRange = formData.get('time_range');
        if (timeRange !== null && timeRange !== undefined) {
            result.time_range = timeRange;
        }
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
        if (!selectElement.value) {
            selectElement.value = '1d';
        }
    }

    /**
     * 同步日志级别下拉框的着色样式。
     *
     * 规则：ERROR/CRITICAL=红色，WARNING=橙色，INFO=蓝色，DEBUG=灰色，其余为默认色。
     *
     * @returns {void}
     */
    function syncLogLevelSelectTone() {
        const selectEl = document.getElementById(LOG_LEVEL_SELECT_ID);
        if (!selectEl) {
            return;
        }
        const value = (selectEl.value || '').toString().toUpperCase();
        let tone = 'default';
        switch (value) {
            case 'ERROR':
            case 'CRITICAL':
                tone = 'danger';
                break;
            case 'WARNING':
                tone = 'warning';
                break;
            case 'INFO':
                tone = 'info';
                break;
            case 'DEBUG':
                tone = 'muted';
                break;
            default:
                tone = 'default';
                break;
        }
        LOG_LEVEL_SELECT_TONE_CLASSES.forEach((className) => {
            selectEl.classList.remove(className);
        });
        selectEl.classList.add(`log-level-select--${tone}`);
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
        const windowHours = Number(params.hours);
        refreshStats.lastWindowHours = Number.isFinite(windowHours) && windowHours > 0 ? windowHours : 24;
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
        const totalLogs = Number(stats.total_logs ?? stats.total ?? 0) || 0;
        const errorLogs = Number(stats.error_logs ?? stats.error_count ?? 0) || 0;
        const warningLogs = Number(stats.warning_logs ?? stats.warning_count ?? 0) || 0;
        const infoLogs = Number(stats.info_count ?? 0) || 0;

        const setText = (id, value) => {
            const element = document.getElementById(id);
            if (!element) {
                return;
            }
            element.textContent = value;
        };

        setText('totalLogs', totalLogs);
        setText('errorLogs', errorLogs);
        setText('warningLogs', warningLogs);
        setText('infoLogs', infoLogs);

        // 二级维度：错误/告警、占比、Top 模块（避免冗余文字，通过 icon + 数字/短文本表达）。
        const windowHours = refreshStats.lastWindowHours || 24;
        setText('logsMetaWindowHours', `${windowHours}h`);

        const formatPercent = global.NumberFormat.formatPercent;
        setText(
            'logsMetaErrorRate',
            formatPercent(stats.error_rate, { precision: 1, trimZero: true, inputType: 'percent', fallback: '0%' }),
        );
        const warningRatio = totalLogs > 0 ? warningLogs / totalLogs : 0;
        setText(
            'logsMetaWarningRate',
            formatPercent(warningRatio, { precision: 1, trimZero: true, inputType: 'ratio', fallback: '0%' }),
        );

        setText('logsMetaCriticalCount', Number(stats.critical_count ?? 0) || 0);
        setText('logsMetaDebugCount', Number(stats.debug_count ?? 0) || 0);

        const errorPerHour = windowHours > 0 ? errorLogs / windowHours : 0;
        const warningPerHour = windowHours > 0 ? warningLogs / windowHours : 0;
        setText(
            'logsMetaErrorPerHour',
            global.NumberFormat.formatDecimal(errorPerHour, { precision: 1, trimZero: true, fallback: '0' }),
        );
        setText(
            'logsMetaWarningPerHour',
            global.NumberFormat.formatDecimal(warningPerHour, { precision: 1, trimZero: true, fallback: '0' }),
        );

        const topModules = Array.isArray(stats.top_modules) ? stats.top_modules : [];
        const top1 = topModules[0] || null;
        const topModuleName = top1?.module ? String(top1.module) : '-';
        const topModuleCount = Number(top1?.count ?? 0) || 0;
        setText('logsMetaTopModule', topModuleName);
        setText('logsMetaTopModuleCount', topModuleCount);
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
            <button class="btn btn-outline-secondary btn-icon" data-action="open-log-detail" data-log-id="${logId}" title="查看详情">
                <i class="fas fa-eye"></i>
            </button>
        `);
    }

    global.LogsPage = {
        mount,
        openDetail: openLogDetailById,
    };
})(window);
