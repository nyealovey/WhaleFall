(function (window) {
    /**
     * 同步会话中心页面脚本：负责列表渲染、筛选、自动刷新与详情/错误日志弹窗。
     * 依赖：bootstrap、toast.js、time-utils.js、DOMHelpers、httpU。
     */
    'use strict';

    const helpers = window.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载同步会话页面脚本');
        return;
    }

    const LodashUtils = window.LodashUtils;
    if (!LodashUtils) {
        throw new Error('LodashUtils 未初始化');
    }

    const { ready, selectOne, select, from } = helpers;

    const SYNC_FILTER_FORM_ID = 'sync-sessions-filter-form';
    const AUTO_APPLY_FILTER_CHANGE = true;

    let currentSessions = [];
    let currentFilters = {};
    let currentPage = 1;
    let pagination = null;
    let syncFilterEventHandler = null;
    let autoRefreshTimer = null;
    let debouncedAutoRefresh = null;

    ready(() => {
        loadSessions();
        setupAutoRefresh();
        registerSyncFilterForm();
        subscribeSyncFilters();
    });

    function notifyAlert(message, type = 'info') {
        window.toast[type] ? window.toast[type](message) : window.toast.show(type, message);
    }

    function sanitizePrimitiveValue(value) {
        if (value instanceof File) {
            return value.name;
        }
        if (typeof value === 'string') {
            const trimmed = value.trim();
            return trimmed === '' ? null : trimmed;
        }
        if (value === undefined || value === null) {
            return null;
        }
        return value;
    }

    function sanitizeFilterValue(value) {
        if (Array.isArray(value)) {
            return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
        }
        return sanitizePrimitiveValue(value);
    }

    function resolveSyncFilters(form, overrideValues) {
        const baseForm = form || selectOne(`#${SYNC_FILTER_FORM_ID}`).first();
        const rawValues =
            overrideValues && Object.keys(overrideValues || {}).length ? overrideValues : collectFormValues(baseForm);
        return Object.entries(rawValues || {}).reduce((result, [key, value]) => {
            if (key === 'csrf_token') {
                return result;
            }
            const normalized = sanitizeFilterValue(value);
            if (normalized === null || normalized === undefined) {
                return result;
            }
            if (Array.isArray(normalized) && normalized.length === 0) {
                return result;
            }
            result[key] = normalized;
            return result;
        }, {});
    }

    function buildSyncQueryParams(filters) {
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

    function setupAutoRefresh() {
        if (debouncedAutoRefresh) {
            debouncedAutoRefresh.cancel?.();
        }
        debouncedAutoRefresh = LodashUtils.debounce(() => {
            loadSessions(currentPage, { silent: true });
        }, 500, { leading: false, trailing: true });

        clearInterval(autoRefreshTimer);
        autoRefreshTimer = window.setInterval(() => {
            debouncedAutoRefresh();
        }, 30000);

        from(window).on('beforeunload', () => {
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = null;
            }
            debouncedAutoRefresh?.cancel?.();
        });
    }

    function showLoadingState() {
        selectOne('#sessions-loading').attr('style', 'display: block;');
        selectOne('#sessions-container').attr('style', 'display: none;');
    }

    function hideLoadingState() {
        selectOne('#sessions-loading').attr('style', 'display: none;');
        selectOne('#sessions-container').attr('style', 'display: block;');
    }

    function loadSessions(page = 1, options = {}) {
        currentPage = page;
        const params = buildSyncQueryParams({
            ...currentFilters,
            page,
            per_page: 20,
        });

        if (!options.silent) {
            showLoadingState();
        }

        window.httpU
            .get(`/sync_sessions/api/sessions?${params.toString()}`)
            .then((data) => {
                if (data.success) {
                    const payload = data?.data ?? {};
                    currentSessions = payload.sessions ?? payload.items ?? payload ?? [];
                    if (!Array.isArray(currentSessions)) {
                        currentSessions = [];
                    }
                    pagination = payload.pagination ?? data.pagination ?? null;
                    renderSessions(currentSessions);
                    renderPagination(pagination);
                } else {
                    console.error('加载会话列表失败:', data.message);
                    notifyAlert(`加载会话列表失败: ${data.message}`, 'error');
                }
            })
            .catch((err) => {
                console.error('加载会话列表出错:', err);
                notifyAlert('加载会话列表出错', 'error');
            })
            .finally(() => {
                if (!options.silent) {
                    hideLoadingState();
                }
            });
    }

    function renderSessions(sessions) {
        const container = selectOne('#sessions-container');
        if (!container.length) {
            return;
        }

        if (!sessions || sessions.length === 0) {
            container.html('<div class="text-center py-4 text-muted">暂无同步会话</div>');
            return;
        }

        const cards = sessions.map((session) => buildSessionCard(session)).join('');
        container.html(cards);

        container.find('[data-action="view-detail"]').on('click', (event) => {
            event.preventDefault();
            const sessionId = event.currentTarget.getAttribute('data-session-id');
            if (sessionId) {
                viewSessionDetail(sessionId);
            }
        });

        container.find('[data-action="view-errors"]').on('click', (event) => {
            event.preventDefault();
            const sessionId = event.currentTarget.getAttribute('data-session-id');
            if (sessionId) {
                viewErrorLogs(sessionId);
            }
        });

        container.find('[data-action="cancel-session"]').on('click', (event) => {
            event.preventDefault();
            const sessionId = event.currentTarget.getAttribute('data-session-id');
            if (sessionId) {
                cancelSession(sessionId);
            }
        });
    }

    function buildSessionCard(session) {
        const statusClass = getStatusClass(session.status);
        const statusText = getStatusText(session.status);
        const startedAt = window.timeUtils.formatTime(session.started_at, 'datetime');
        const completedAt = session.completed_at ? window.timeUtils.formatTime(session.completed_at, 'datetime') : '-';

        const totalInstances = session.total_instances || 0;
        const successfulInstances = session.successful_instances || 0;
        const failedInstances = session.failed_instances || 0;
        const successRate = totalInstances > 0 ? Math.round((successfulInstances / totalInstances) * 100) : 0;
        const progressInfo = getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances);

        return `
            <div class="card session-card ${statusClass} mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h5 class="card-title mb-1">
                                <i class="fas fa-sync-alt me-2"></i>
                                会话 #${session.id}
                            <span class="badge ${progressInfo.badgeClass} ms-2">${statusText}</span>
                            </h5>
                            <p class="text-muted mb-0">
                                <i class="fas fa-database me-1"></i>${session.instance_name || '未知实例'}
                            </p>
                        </div>
                        <div class="session-actions">
                            <button class="btn btn-outline-primary btn-sm me-2" data-action="view-detail" data-session-id="${session.id}">
                                <i class="fas fa-eye me-1"></i>详情
                            </button>
                            <button class="btn btn-outline-danger btn-sm" data-action="cancel-session" data-session-id="${session.id}" ${session.status !== 'running' ? 'disabled' : ''}>
                                <i class="fas fa-stop-circle me-1"></i>取消
                            </button>
                        </div>
                    </div>
                    <div class="progress mb-2">
                        <div class="progress-bar ${progressInfo.barClass}" role="progressbar" style="width: ${successRate}%" aria-valuenow="${successRate}" aria-valuemin="0" aria-valuemax="100">
                            ${successRate}%
                        </div>
                    </div>
                    <div class="d-flex justify-content-between text-muted small">
                        <span>总实例：${totalInstances}</span>
                        <span>成功：${successfulInstances}</span>
                        <span>失败：${failedInstances}</span>
                        <span>开始：${startedAt}</span>
                        <span>完成：${completedAt}</span>
                    </div>
                    <div class="mt-3">
                        <button class="btn btn-link btn-sm ps-0" data-action="view-errors" data-session-id="${session.id}">
                            <i class="fas fa-bug me-1"></i>查看错误日志
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
