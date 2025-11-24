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

    function initializeGrid() {
        const container = document.getElementById('logs-grid');
        if (!container) {
            console.warn('未找到日志列表容器');
            return;
        }
        logsGrid = new global.GridWrapper(container, {
            columns: buildColumns(),
            server: {
                url: '/logs/api/list?sort=timestamp&order=desc',
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
                formatter: (cell, row) => renderLevelBadge(resolveRowMeta(row), gridHtml),
            },
            {
                name: '模块',
                id: 'module',
                formatter: (cell) => {
                    const value = cell || '-';
                    return gridHtml ? gridHtml(`<span class="badge bg-light text-dark">${escapeHtml(value)}</span>`) : value;
                },
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
                name: '操作',
                id: 'actions',
                sort: false,
                formatter: (cell, row) => {
                    const meta = resolveRowMeta(row);
                    if (!meta.id) {
                        return '';
                    }
                    return gridHtml
                        ? gridHtml(
                              `<button type="button" class="btn btn-link btn-sm p-0" data-log-id="${meta.id}" onclick="window.LogsPage.openDetail(${meta.id})">详情</button>`
                          )
                        : '详情';
                },
            },
            { id: '__meta__', hidden: true },
        ];
    }

    function renderLevelBadge(log, gridHtml) {
        const colors = {
            DEBUG: 'secondary',
            INFO: 'info',
            WARNING: 'warning',
            ERROR: 'danger',
            CRITICAL: 'dark',
        };
        const level = log.level || 'INFO';
        const color = colors[level] || 'secondary';
        if (!gridHtml) {
            return level;
        }
        return gridHtml(`<span class="badge bg-${color}">${escapeHtml(level)}</span>`);
    }

    function resolveRowMeta(row) {
        return row?.cells?.[row.cells.length - 1]?.data || {};
    }

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

    function handleFilterChange(values) {
        const filters = sanitizeFilters(resolveFilters(values));
        logsGrid?.updateFilters(filters);
        refreshStats(filters);
    }

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

    function sanitizeText(value) {
        if (typeof value !== 'string') {
            return '';
        }
        const trimmed = value.trim();
        return trimmed === '' ? '' : trimmed;
    }

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

    function updateStatsDisplay(stats) {
        const { selectOne } = helpers || {};
        if (!selectOne) {
            return;
        }
        const mapping = {
            totalLogs: stats.total_logs ?? stats.total ?? 0,
            errorLogs: stats.error_logs ?? stats.error_count ?? 0,
            warningLogs: stats.warning_logs ?? stats.warning_count ?? 0,
            modulesCount: stats.modules_count ?? stats.module_count ?? 0,
        };
        Object.entries(mapping).forEach(([id, value]) => {
            const element = selectOne(`#${id}`);
            if (element.length) {
                element.text(value ?? 0);
            }
        });
    }

    function showStatsError(message) {
        if (global.toast?.error) {
            global.toast.error(message);
        } else {
            console.error(message);
        }
    }

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

    global.LogsPage = {
        mount,
        openDetail: openLogDetailById,
    };
})(window);
