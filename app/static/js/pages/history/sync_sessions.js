// 会话中心页脚本（从模板抽离）
// 依赖：bootstrap, toast.js, time-utils.js

(function () {
  const LodashUtils = window.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

  const SYNC_FILTER_FORM_ID = "sync-sessions-filter-form";
  const AUTO_APPLY_FILTER_CHANGE = true;

  function notifyAlert(message, type = 'info') {
    toast.show(type, message);
  }
  // 防抖/节流等工具可后续抽到 shared/utils

  let currentSessions = [];
  let currentFilters = {};
  let currentPage = 1;
  let totalPages = 1;
  let pagination = null;
  let syncFilterEventHandler = null;
  let autoRefreshTimer = null;
  let debouncedAutoRefresh = null;

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
    const baseForm = form || document.getElementById(SYNC_FILTER_FORM_ID);
    const rawValues = overrideValues && Object.keys(overrideValues || {}).length
      ? overrideValues
      : collectFormValues(baseForm);
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
      } else {
        params.append(key, value);
      }
    });
    return params;
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadSessions();
    setupAutoRefresh();
    registerSyncFilterForm();
    subscribeSyncFilters();
  });

  function setupAutoRefresh() {
    if (debouncedAutoRefresh) {
      debouncedAutoRefresh.cancel?.();
    }
    debouncedAutoRefresh = LodashUtils.debounce(() => {
      loadSessions(currentPage, { silent: true });
    }, 500, { leading: false, trailing: true });

    clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(() => {
      debouncedAutoRefresh();
    }, 30000);

    window.addEventListener('beforeunload', () => {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
      }
      if (debouncedAutoRefresh) {
        debouncedAutoRefresh.cancel?.();
      }
    }, { once: true });
  }

  window.loadSessions = function (page = 1, options = {}) {
    currentPage = page;
    const params = buildSyncQueryParams({
      ...currentFilters,
      page,
      per_page: 20,
    });

    const silent = Boolean(options.silent);
    if (!silent) {
      showLoadingState();
    }

    http.get(`/sync_sessions/api/sessions?${params.toString()}`)
      .then(data => {
        if (data.success) {
          const payload = data?.data ?? {};
          currentSessions = payload.sessions ?? payload.items ?? payload ?? [];
          if (!Array.isArray(currentSessions)) {
            currentSessions = [];
          }
          pagination = payload.pagination ?? data.pagination ?? null;
          if (pagination) {
            totalPages = pagination.pages ?? pagination.total_pages ?? 1;
          } else {
            totalPages = 1;
          }
          renderSessions(currentSessions);
          renderPagination(pagination);
          if (!silent) {
            hideLoadingState();
          }
        } else {
          console.error('加载会话列表失败:', data.message);
          notifyAlert('加载会话列表失败: ' + data.message, 'error');
          if (!silent) {
            hideLoadingState();
          }
        }
      })
      .catch(err => {
        console.error('加载会话列表出错:', err);
        notifyAlert('加载会话列表出错', 'error');
        if (!silent) {
          hideLoadingState();
        }
      });
  }

  // 显示加载状态
  function showLoadingState() {
    const loading = document.getElementById('sessions-loading');
    const container = document.getElementById('sessions-container');
    if (loading) loading.style.display = 'block';
    if (container) container.style.display = 'none';
  }

  // 隐藏加载状态
  function hideLoadingState() {
    const loading = document.getElementById('sessions-loading');
    const container = document.getElementById('sessions-container');
    if (loading) loading.style.display = 'none';
    if (container) container.style.display = 'block';
  }

  window.renderSessions = function (sessions) {
    const container = document.getElementById('sessions-container');
    if (!container) return;

    if (!sessions || sessions.length === 0) {
      container.innerHTML = '<div class="text-center py-4 text-muted">暂无同步会话</div>';
      return;
    }

    const html = sessions.map(session => {
      const statusClass = getStatusClass(session.status);
      const statusText = getStatusText(session.status);
      const startedAt = timeUtils.formatTime(session.started_at, 'datetime');
      const completedAt = session.completed_at ? timeUtils.formatTime(session.completed_at, 'datetime') : '-';

      const totalInstances = session.total_instances || 0;
      const successfulInstances = session.successful_instances || 0;
      const failedInstances = session.failed_instances || 0;
      const successRate = totalInstances > 0 ? Math.round((successfulInstances / totalInstances) * 100) : 0;
      const progressInfo = getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances);

      return `
        <div class="card session-card ${statusClass} mb-3">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-2">
                <h6 class="mb-1">${session.session_id.substring(0, 8)}...</h6>
                <small class="text-muted">${getSyncTypeText(session.sync_type)} - ${getSyncCategoryText(session.sync_category)}</small>
              </div>
              <div class="col-2">
                <span class="badge status-badge bg-${getStatusColor(session.status)}">${statusText}</span>
              </div>
              <div class="col-3">
                <div class="progress" style="height: 12px;">
                  <div class="progress-bar ${progressInfo.barClass}" role="progressbar" style="width: ${successRate}%" title="${progressInfo.tooltip}"></div>
                </div>
                <small class="text-muted">
                  <span class="${progressInfo.textClass}">
                    <i class="${progressInfo.icon}"></i> ${successRate}% (${successfulInstances}/${totalInstances})
                  </span>
                </small>
              </div>
              <div class="col-2">
                <small class="text-muted">
                  <i class="fas fa-clock"></i> ${startedAt}<br>
                  <i class="fas fa-check-circle"></i> ${completedAt}
                </small>
              </div>
              <div class="col-1">
                ${getDurationBadge(session.started_at, session.completed_at)}
              </div>
              <div class="text-end col-2">
                <button class="btn btn-sm btn-outline-primary" data-action="view" data-id="${session.session_id}">
                  <i class="fas fa-eye"></i> 详情
                </button>
                ${failedInstances > 0 ? `
                <button class="btn btn-sm btn-outline-warning" data-action="error" data-id="${session.session_id}" title="查看错误">
                  <i class="fas fa-exclamation-triangle"></i> 错误
                </button>` : ''}
                ${session.status === 'running' ? `
                <button class="btn btn-sm btn-outline-danger" data-action="cancel" data-id="${session.session_id}">
                  <i class="fas fa-stop"></i> 取消
                </button>` : ''}
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    container.innerHTML = html;

    container.querySelectorAll('[data-action="view"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      viewSessionDetail(id);
    }));
    container.querySelectorAll('[data-action="error"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      viewErrorLogs(id);
    }));
    container.querySelectorAll('[data-action="cancel"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      cancelSession(id);
    }));
  }

  // 渲染分页控件
  function renderPagination(paginationData) {
    const container = document.getElementById('pagination-container');
    if (!container || !paginationData) {
      if (container) container.style.display = 'none';
      return;
    }

    const page = paginationData.page ?? paginationData.current_page ?? 1;
    const pages = paginationData.pages ?? paginationData.total_pages ?? 1;
    const has_prev = paginationData.has_prev ?? paginationData.has_previous ?? page > 1;
    const has_next = paginationData.has_next ?? paginationData.has_more ?? page < pages;
    const prev_num = paginationData.prev_num ?? paginationData.previous_page ?? (has_prev ? page - 1 : 1);
    const next_num = paginationData.next_num ?? paginationData.next_page ?? (has_next ? page + 1 : pages);

    if (pages <= 1) {
      container.style.display = 'none';
      return;
    }

    let html = '<nav aria-label="会话分页"><ul class="pagination">';

    // 上一页
    if (has_prev) {
      html += `<li class="page-item">
        <a class="page-link" href="#" onclick="loadSessions(${prev_num}); return false;">
          <i class="fas fa-chevron-left"></i>
        </a>
      </li>`;
    } else {
      html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }

    // 页码
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(pages, page + 2);

    if (startPage > 1) {
      html += `<li class="page-item"><a class="page-link" href="#" onclick="loadSessions(1); return false;">1</a></li>`;
      if (startPage > 2) {
        html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      if (i === page) {
        html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
      } else {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadSessions(${i}); return false;">${i}</a></li>`;
      }
    }

    if (endPage < pages) {
      if (endPage < pages - 1) {
        html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
      }
      html += `<li class="page-item"><a class="page-link" href="#" onclick="loadSessions(${pages}); return false;">${pages}</a></li>`;
    }

    // 下一页
    if (has_next) {
      html += `<li class="page-item">
        <a class="page-link" href="#" onclick="loadSessions(${next_num}); return false;">
          <i class="fas fa-chevron-right"></i>
        </a>
      </li>`;
    } else {
      html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }

    html += '</ul></nav>';

    container.innerHTML = html;
    container.style.display = 'block';
  }

  window.viewSessionDetail = function (sessionId) {
    http.get(`/sync_sessions/api/sessions/${sessionId}`)
      .then(data => {
        if (data.success) {
          const session = data?.data?.session ?? data.session ?? data ?? {};
          showSessionDetail(session);
        } else {
          notifyAlert('加载会话详情失败: ' + data.message, 'error');
        }
      })
      .catch(err => { console.error('加载会话详情出错:', err); notifyAlert('加载会话详情出错', 'error'); });
  }

  window.viewErrorLogs = function (sessionId) {
    http.get(`/sync_sessions/api/sessions/${sessionId}/error-logs`)
      .then(data => {
        if (data.success) {
          const payload = data?.data ?? data ?? {};
          showErrorLogs(payload);
        } else {
          notifyAlert('加载错误信息失败: ' + data.message, 'error');
        }
      })
      .catch(err => { console.error('加载错误信息出错:', err); notifyAlert('加载错误信息出错', 'error'); });
  }

  window.showErrorLogs = function (data) {
    const content = document.getElementById('error-logs-content');
    if (!content) return;
    const errorRecords = data.error_records || [];

    if (errorRecords.length === 0) {
      content.innerHTML = '<div class="text-center py-4 text-muted">没有发现错误记录</div>';
    } else {
      const recordsHtml = errorRecords.map(record => `
        <div class="card mb-3 border-danger">
          <div class="card-header bg-danger text-white">
            <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>${record.instance_name} (ID: ${record.instance_id})</h6>
          </div>
          <div class="card-body">
            ${record.error_message ? `
            <div class="alert alert-danger mb-0">
              <h6 class="alert-heading"><i class="fas fa-bug me-2"></i>错误信息</h6>
              <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${record.error_message}</pre>
            </div>` : '<div class="text-muted">没有具体错误信息</div>'}
          </div>
        </div>`).join('');
      content.innerHTML = recordsHtml;
    }

    const modal = new bootstrap.Modal(document.getElementById('errorLogsModal'));
    modal.show();
  }

  window.showSessionDetail = function (session) {
    const content = document.getElementById('session-detail-content');
    if (!content) return;
    const safeSession = session && typeof session === 'object' ? session : {};
    const records = Array.isArray(safeSession.instance_records) ? safeSession.instance_records : [];

    const recordsHtml = records.map(record => {
      const statusClass = getStatusClass(record.status);
      const statusText = getStatusText(record.status);
      // 使用统一的时间解析计算持续时间
      let duration = '-';
      if (record.started_at && record.completed_at) {
          const startTime = timeUtils.parseTime(record.started_at);
          const endTime = timeUtils.parseTime(record.completed_at);
          if (startTime && endTime) {
              duration = Math.round((endTime - startTime) / 1000) + '秒';
          }
      }
      const startedAt = timeUtils.formatTime(record.started_at, 'datetime');
      const completedAt = record.completed_at ? timeUtils.formatTime(record.completed_at, 'datetime') : '-';

      return `
        <div class="card mb-2">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-3">
                <h6 class="mb-1"><strong>ID: ${record.instance_id}</strong> &nbsp;&nbsp; ${record.instance_name}</h6>
              </div>
              <div class="col-2">
                <span class="badge status-badge bg-${getStatusColor(record.status)}">${statusText}</span>
              </div>
              <div class="col-7">
                <small class="text-muted">
                  开始: ${startedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 完成: ${completedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 耗时: ${duration}
                  ${record.error_message ? ` &nbsp;&nbsp; | &nbsp;&nbsp; 错误: ${record.error_message}` : ''}
                </small>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    content.innerHTML = `
      <div class="row mb-3">
        <div class="col-6"><strong>会话ID:</strong> ${safeSession.session_id || '未知'}</div>
        <div class="col-6"><strong>状态:</strong> <span class="badge bg-${getStatusColor(safeSession.status)}">${getStatusText(safeSession.status)}</span></div>
      </div>
      <div class="row mb-3">
        <div class="col-6"><strong>操作方式:</strong> ${getSyncTypeText(safeSession.sync_type)}</div>
        <div class="col-6"><strong>同步分类:</strong> ${getSyncCategoryText(safeSession.sync_category)}</div>
      </div>
      <div class="row mb-3">
        <div class="col-6"><strong>开始时间:</strong> ${timeUtils.formatTime(safeSession.started_at, 'datetime')}</div>
        <div class="col-6"><strong>完成时间:</strong> ${safeSession.completed_at ? timeUtils.formatTime(safeSession.completed_at, 'datetime') : '未完成'}</div>
      </div>
      <div class="row mb-3">
        <div class="col-4"><strong>总实例数:</strong> ${safeSession.total_instances ?? 0}</div>
        <div class="col-4"><strong>成功:</strong> ${safeSession.successful_instances ?? 0}</div>
        <div class="col-4"><strong>失败:</strong> ${safeSession.failed_instances ?? 0}</div>
      </div>
      <hr>
      <h6>实例记录</h6>
      <div class="max-height-400 overflow-auto">${recordsHtml || '<div class="text-muted">暂无实例记录</div>'}</div>`;

    const modal = new bootstrap.Modal(document.getElementById('sessionDetailModal'));
    modal.show();
  }

  window.cancelSession = function (sessionId) {
    if (confirm('确定要取消这个同步会话吗？')) {
      http.post(`/sync_sessions/api/sessions/${sessionId}/cancel`)
        .then(data => {
          if (data.success) { notifyAlert('会话已取消', 'success'); loadSessions(); }
          else { notifyAlert('取消会话失败: ' + data.message, 'error'); }
        })
        .catch(err => { console.error('取消会话出错:', err); notifyAlert('取消会话出错', 'error'); });
    }
  }

  // 应用筛选条件
  function applyFilters() {
    applySyncFilters();
  }

  // 将函数暴露到全局作用域
  window.applyFilters = applyFilters;



  window.clearFilters = function () {
    resetSyncFilters();
  }

  window.getProgressInfo = function (successRate, totalInstances, successfulInstances, failedInstances) {
    if (totalInstances === 0) {
      return { barClass: 'bg-secondary', textClass: 'text-muted', icon: 'fas fa-question-circle', tooltip: '无实例数据' };
    }
    if (successRate === 100) {
      return { barClass: 'bg-success', textClass: 'text-success', icon: 'fas fa-check-circle', tooltip: '全部成功' };
    } else if (successRate === 0) {
      return { barClass: 'bg-danger', textClass: 'text-danger', icon: 'fas fa-times-circle', tooltip: '全部失败' };
    } else if (successRate >= 70) {
      return { barClass: 'bg-warning', textClass: 'text-warning', icon: 'fas fa-exclamation-triangle', tooltip: `部分成功 (${successfulInstances}成功, ${failedInstances}失败)` };
    } else {
      return { barClass: 'bg-danger', textClass: 'text-danger', icon: 'fas fa-exclamation-triangle', tooltip: `大部分失败 (${successfulInstances}成功, ${failedInstances}失败)` };
    }
  }

  function registerSyncFilterForm() {
    if (!window.FilterUtils) {
      console.warn('FilterUtils 未加载，跳过同步会筛选初始化');
      return;
    }
    const selector = `#${SYNC_FILTER_FORM_ID}`;
    const form = document.querySelector(selector);
    if (!form) {
      return;
    }
    window.FilterUtils.registerFilterForm(selector, {
      onSubmit: ({ form, event }) => {
        event?.preventDefault?.();
        applySyncFilters(form);
      },
      onClear: ({ form, event }) => {
        event?.preventDefault?.();
        resetSyncFilters(form);
      },
      autoSubmitOnChange: true,
    });
  }

  function subscribeSyncFilters() {
    if (!window.EventBus) {
      return;
    }
    const form = document.getElementById(SYNC_FILTER_FORM_ID);
    if (!form) {
      return;
    }
    const handler = (detail) => {
      if (!detail) {
        return;
      }
      const incoming = (detail.formId || '').replace(/^#/, '');
      if (incoming !== SYNC_FILTER_FORM_ID) {
        return;
      }
      switch (detail.action) {
        case 'clear':
          resetSyncFilters(form);
          break;
        case 'change':
          if (AUTO_APPLY_FILTER_CHANGE) {
            applySyncFilters(form, detail.values);
          }
          break;
        case 'submit':
          applySyncFilters(form, detail.values);
          break;
        default:
          break;
      }
    };
    ['change', 'submit', 'clear'].forEach((action) => {
      EventBus.on(`filters:${action}`, handler);
    });
    syncFilterEventHandler = handler;
    window.addEventListener('beforeunload', () => cleanupSyncFilters(), { once: true });
  }

  function cleanupSyncFilters() {
    if (!window.EventBus || !syncFilterEventHandler) {
      return;
    }
    ['change', 'submit', 'clear'].forEach((action) => {
      EventBus.off(`filters:${action}`, syncFilterEventHandler);
    });
    syncFilterEventHandler = null;
  }

  function applySyncFilters(form, values) {
    const targetForm = form || document.getElementById(SYNC_FILTER_FORM_ID);
    if (!targetForm) {
      return;
    }
    currentFilters = resolveSyncFilters(targetForm, values);
    currentPage = 1;
    loadSessions(1);
  }

  function resetSyncFilters(form) {
    const targetForm = form || document.getElementById(SYNC_FILTER_FORM_ID);
    if (targetForm) {
      targetForm.reset();
    }
    currentFilters = {};
    loadSessions(1);
  }

  function collectFormValues(form) {
    if (!form) {
      return {};
    }
    if (window.FilterUtils && typeof window.FilterUtils.serializeForm === 'function') {
      return window.FilterUtils.serializeForm(form);
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

  window.getStatusClass = function (status) {
    const map = { running: 'running', completed: 'completed', failed: 'failed', cancelled: 'cancelled' };
    return map[status] || '';
  }
  window.getStatusText = function (status) { return status; }
  window.getStatusColor = function (status) {
    const map = { running: 'success', completed: 'info', failed: 'danger', cancelled: 'secondary', pending: 'warning' };
    return map[status] || 'secondary';
  }
  window.getSyncTypeText = function (type) {
    const typeMap = {
      'manual_single': '手动单台',
      'manual_batch': '手动批量',
      'manual_task': '手动任务',
      'scheduled_task': '定时任务'
    };
    return typeMap[type] || type;
  }
  window.getSyncCategoryText = function (category) {
    const categoryMap = {
      'account': '账户同步',
      'capacity': '容量同步',
      'config': '配置同步',
      'aggregation': '统计聚合',
      'other': '其他'
    };
    return categoryMap[category] || category;
  }

  window.getDurationBadge = function (startedAt, completedAt) {
    if (!startedAt || !completedAt) return '<span class="text-muted">-</span>';
    
    // 使用统一的时间解析
    const s = timeUtils.parseTime(startedAt);
    const e = timeUtils.parseTime(completedAt);
    
    if (!s || !e) return '<span class="text-muted">-</span>';
    
    const sec = (e - s) / 1000;
    return window.NumberFormat.formatDurationSeconds(sec);
  }
})();
