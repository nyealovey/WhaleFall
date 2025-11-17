// 会话中心页脚本（从模板抽离）
// 依赖：toast.js, time-utils.js, UI.createModal

function mountSyncSessionsPage(window = globalThis.window, document = globalThis.document) {
  const LodashUtils = window.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

  const SyncSessionsService = window.SyncSessionsService;
  if (!SyncSessionsService) {
    throw new Error("SyncSessionsService 未加载，无法进行会话请求");
  }

  const debugEnabled = window.DEBUG_SYNC_SESSIONS ?? true;
  window.DEBUG_SYNC_SESSIONS = debugEnabled;

  function debugLog(message, payload) {
    if (!debugEnabled) {
      return;
    }
    const prefix = "[SyncSessionsPage]";
    if (payload !== undefined) {
      console.debug(`${prefix} ${message}`, payload);
    } else {
      console.debug(`${prefix} ${message}`);
    }
  }

  let syncSessionsService = null;
  try {
    syncSessionsService = new SyncSessionsService(window.httpU);
  } catch (error) {
    console.error("初始化 SyncSessionsService 失败:", error);
    debugLog("SyncSessionsService 初始化失败", error);
    return;
  }

  const SYNC_FILTER_FORM_ID = "sync-sessions-filter-form";
  const AUTO_APPLY_FILTER_CHANGE = true;
  const AUTO_REFRESH_INTERVAL_MS = 30000;
  const SESSION_DETAIL_MODAL_SELECTOR = '#sessionDetailModal';
  const ERROR_LOGS_MODAL_SELECTOR = '#errorLogsModal';

  function notifyAlert(message, type = 'info') {
    toast.show(type, message);
  }
  // 防抖/节流等工具可后续抽到 shared/utils

  let syncSessionsStore = null;
  const storeSubscriptions = [];
  let syncFilterCard = null;
  let filterUnloadHandler = null;
  let sessionDetailModal = null;
  let errorLogsModal = null;
  window.syncSessionsStore = null;

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

  document.addEventListener('DOMContentLoaded', function () {
    debugLog("DOM Ready，开始初始化会话中心");
    try {
      initializeSyncSessionsStore();
      initializeSyncFilterCard();
      initializeSyncModals();
      debugLog("会话中心初始化完成");
    } catch (error) {
      console.error("会话中心初始化失败:", error);
      debugLog("会话中心初始化失败", error);
      notifyAlert('会话中心初始化失败，请查看控制台日志', 'error');
    }
  });

  function initializeSyncModals() {
    const factory = window.UI?.createModal;
    if (!factory) {
      throw new Error('UI.createModal 未加载，会话中心模态无法初始化');
    }
    debugLog("初始化会话详情/错误日志模态");
    sessionDetailModal = factory({
      modalSelector: SESSION_DETAIL_MODAL_SELECTOR,
      onClose: clearSessionDetailContent,
    });
    errorLogsModal = factory({
      modalSelector: ERROR_LOGS_MODAL_SELECTOR,
      onClose: clearErrorLogsContent,
    });
  }

  function initializeSyncSessionsStore() {
    if (!window.createSyncSessionsStore) {
      console.error("createSyncSessionsStore 未加载");
      debugLog("createSyncSessionsStore 未加载");
      return;
    }
    try {
      debugLog("开始创建 SyncSessionsStore");
      syncSessionsStore = window.createSyncSessionsStore({
        service: syncSessionsService,
        emitter: window.mitt ? window.mitt() : null,
        autoRefreshInterval: AUTO_REFRESH_INTERVAL_MS,
      });
    } catch (error) {
      console.error("初始化 SyncSessionsStore 失败:", error);
      debugLog("SyncSessionsStore 创建失败", error);
      return;
    }
    bindStoreEvents();
    debugLog("SyncSessionsStore 初始化中");
    syncSessionsStore
      .init()
      .then(() => debugLog("SyncSessionsStore 初始化完成"))
      .catch(error => {
        console.error("SyncSessionsStore 初始化过程出现错误:", error);
        debugLog("SyncSessionsStore 初始化失败", error);
      });
    window.syncSessionsStore = syncSessionsStore;
    window.addEventListener('beforeunload', () => {
      teardownStore();
    }, { once: true });
  }

  function bindStoreEvents() {
    debugLog("绑定 SyncSessionsStore 事件");
    subscribeToStoreEvent('syncSessions:loading', () => {
      debugLog("收到事件 syncSessions:loading");
      showLoadingState();
    });
    subscribeToStoreEvent('syncSessions:updated', (state) => {
      debugLog("收到事件 syncSessions:updated", {
        sessionCount: state?.sessions?.length,
        pagination: state?.pagination,
      });
      hideLoadingState();
      renderSessions(state.sessions);
      renderPagination(state.pagination);
    });
    subscribeToStoreEvent('syncSessions:error', (payload) => {
      hideLoadingState();
      const message = payload?.error?.message || '会话操作失败';
      if (payload?.error) {
        console.error('SyncSessionsStore error:', payload.error);
        debugLog("收到事件 syncSessions:error", payload.error);
      }
      notifyAlert(message, 'error');
    });
    subscribeToStoreEvent('syncSessions:detailLoaded', (payload) => {
      debugLog("收到事件 syncSessions:detailLoaded", {
        sessionId: payload?.session?.session_id,
      });
      showSessionDetail(payload?.session || {});
    });
    subscribeToStoreEvent('syncSessions:errorLogsLoaded', (payload) => {
      debugLog("收到事件 syncSessions:errorLogsLoaded", {
        recordCount: payload?.errorRecords?.length,
      });
      showErrorLogs({ error_records: payload?.errorRecords || [] });
    });
    subscribeToStoreEvent('syncSessions:sessionCancelled', () => {
      debugLog("收到事件 syncSessions:sessionCancelled");
      notifyAlert('会话已取消', 'success');
    });
  }

  function subscribeToStoreEvent(eventName, handler) {
    if (!syncSessionsStore) {
      debugLog(`尝试订阅 ${eventName} 但 store 未初始化`);
      return;
    }
    debugLog(`订阅 Store 事件: ${eventName}`);
    storeSubscriptions.push({ eventName, handler });
    syncSessionsStore.subscribe(eventName, handler);
  }

  function teardownStore() {
    if (!syncSessionsStore) {
      return;
    }
    storeSubscriptions.forEach(({ eventName, handler }) => {
      syncSessionsStore.unsubscribe(eventName, handler);
    });
    storeSubscriptions.length = 0;
    syncSessionsStore.destroy?.();
    syncSessionsStore = null;
  }

  window.loadSessions = function (page = 1, options = {}) {
    if (!syncSessionsStore) {
      debugLog("loadSessions 调用但 store 未准备");
      return;
    }
    debugLog("loadSessions 调用", { page, options });
    syncSessionsStore.actions.loadSessions({
      page,
      silent: Boolean(options.silent),
    });
  };

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
    const hasPrev = (typeof paginationData.hasPrev === 'boolean')
      ? paginationData.hasPrev
      : (paginationData.has_prev ?? paginationData.has_previous ?? page > 1);
    const hasNext = (typeof paginationData.hasNext === 'boolean')
      ? paginationData.hasNext
      : (paginationData.has_next ?? paginationData.has_more ?? page < pages);
    const prevPage = paginationData.prevPage ?? paginationData.prev_num ?? paginationData.previous_page ?? (hasPrev ? page - 1 : 1);
    const nextPage = paginationData.nextPage ?? paginationData.next_num ?? paginationData.next_page ?? (hasNext ? page + 1 : pages);

    if (pages <= 1) {
      container.style.display = 'none';
      return;
    }

    let html = '<nav aria-label="会话分页"><ul class="pagination">';

    // 上一页
    if (hasPrev) {
      html += `<li class="page-item">
        <a class="page-link" href="#" onclick="loadSessions(${prevPage}); return false;">
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
    if (hasNext) {
      html += `<li class="page-item">
        <a class="page-link" href="#" onclick="loadSessions(${nextPage}); return false;">
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
    if (!syncSessionsStore) {
      return;
    }
    syncSessionsStore.actions.loadSessionDetail(sessionId);
  };

  window.viewErrorLogs = function (sessionId) {
    if (!syncSessionsStore) {
      return;
    }
    syncSessionsStore.actions.loadErrorLogs(sessionId);
  };

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

    openModal(errorLogsModal, 'errorLogs');
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

    openModal(sessionDetailModal, 'sessionDetail');
  }

  window.cancelSession = function (sessionId) {
    if (!syncSessionsStore) {
      return;
    }
    if (confirm('确定要取消这个同步会话吗？')) {
      syncSessionsStore.actions.cancelSession(sessionId);
    }
  };

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

  function initializeSyncFilterCard() {
    const factory = window.UI?.createFilterCard;
    if (!factory) {
      console.error('UI.createFilterCard 未加载，会话筛选无法初始化');
      debugLog('UI.createFilterCard 未加载');
      return;
    }
    debugLog('初始化筛选卡片');
    syncFilterCard = factory({
      formSelector: `#${SYNC_FILTER_FORM_ID}`,
      autoSubmitOnChange: AUTO_APPLY_FILTER_CHANGE,
      onSubmit: ({ values }) => applySyncFilters(null, values),
      onClear: () => resetSyncFilters(),
      onChange: ({ values }) => {
        if (AUTO_APPLY_FILTER_CHANGE) {
          applySyncFilters(null, values);
        }
      },
    });

    if (filterUnloadHandler) {
      window.removeEventListener('beforeunload', filterUnloadHandler);
    }
    filterUnloadHandler = () => {
      debugLog('销毁筛选卡片');
      destroySyncFilterCard();
      window.removeEventListener('beforeunload', filterUnloadHandler);
      filterUnloadHandler = null;
    };
    window.addEventListener('beforeunload', filterUnloadHandler);
  }

  function destroySyncFilterCard() {
    if (syncFilterCard?.destroy) {
      syncFilterCard.destroy();
    }
    syncFilterCard = null;
  }

  function applySyncFilters(form, values) {
    const targetForm = resolveSyncForm(form);
    if (!targetForm || !syncSessionsStore) {
      debugLog('applySyncFilters 忽略，form或store未准备');
      return;
    }
    const nextFilters = resolveSyncFilters(targetForm, values);
    debugLog('应用筛选条件', nextFilters);
    syncSessionsStore.actions.applyFilters(nextFilters);
  }

  function resetSyncFilters(form) {
    const targetForm = resolveSyncForm(form);
    if (targetForm) {
      targetForm.reset();
    }
    if (!syncSessionsStore) {
      debugLog('resetSyncFilters 忽略，store未准备');
      return;
    }
    debugLog('重置筛选条件');
    syncSessionsStore.actions.resetFilters();
  }

  function resolveSyncForm(form) {
    if (!form && syncFilterCard?.form) {
      return syncFilterCard.form;
    }
    if (!form) {
      return document.getElementById(SYNC_FILTER_FORM_ID);
    }
    return form;
  }

  function collectFormValues(form) {
    if (syncFilterCard?.serialize) {
      return syncFilterCard.serialize();
    }
    if (!form) {
      return {};
    }
    const serializer = window.UI?.serializeForm;
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

  function openModal(instance, name) {
    if (instance?.open) {
      instance.open();
      return;
    }
    console.error(`模态未初始化: ${name}`);
  }

  function clearSessionDetailContent() {
    const container = document.getElementById('session-detail-content');
    if (container) {
      container.innerHTML = '';
    }
  }

  function clearErrorLogsContent() {
    const container = document.getElementById('error-logs-content');
    if (container) {
      container.innerHTML = '';
    }
  }
}

window.SyncSessionsPage = {
  mount: mountSyncSessionsPage,
};
