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
  const SESSION_DETAIL_CONTENT_SELECTOR = '#session-detail-content';

  /**
   * 统一 toast 提示。
   */
  function notifyAlert(message, type = 'info') {
    toast.show(type, message);
  }
  // 防抖/节流等工具可后续抽到 shared/utils

  let syncSessionsStore = null;
  const storeSubscriptions = [];
  let syncFilterCard = null;
  let filterUnloadHandler = null;
  let sessionDetailModalController = null;
  window.syncSessionsStore = null;

  /**
   * 基础值清洗，去除空白。
   */
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

  /**
   * 过滤值标准化，支持数组。
   */
  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return LodashUtils.compact(value.map((item) => sanitizePrimitiveValue(item)));
    }
    return sanitizePrimitiveValue(value);
  }

  /**
   * 组合表单与覆盖值生成过滤参数。
   */
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

  /**
   * 页面初始化入口。
   */
  function startInitialization() {
    debugLog("开始初始化会话中心");
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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startInitialization, { once: true });
  } else {
    startInitialization();
  }

  /**
   * 创建会话详情/错误日志模态，并设定关闭时清理内容。
   */
  function initializeSyncModals() {
    const factory = window.UI?.createModal;
    if (!factory) {
      throw new Error('UI.createModal 未加载，会话中心模态无法初始化');
    }
    debugLog("初始化会话详情/错误日志模态");
    if (!window.SyncSessionDetailModal?.createController) {
      throw new Error('SyncSessionDetailModal 未加载，会话详情模态无法初始化');
    }
    try {
      sessionDetailModalController = window.SyncSessionDetailModal.createController({
        ui: window.UI,
        timeUtils: window.timeUtils,
        modalSelector: SESSION_DETAIL_MODAL_SELECTOR,
        contentSelector: SESSION_DETAIL_CONTENT_SELECTOR,
        getStatusColor,
        getStatusText,
        getSyncTypeText,
        getSyncCategoryText,
      });
    } catch (error) {
      console.error('初始化 SyncSessionDetailModal 失败:', error);
      debugLog('会话详情模态初始化失败', error);
    }
  }

  /**
   * 初始化会话 store，开启自动刷新并注册卸载清理。
   */
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
      sessionDetailModalController?.destroy?.();
    }, { once: true });
  }

  /**
   * 订阅 store 事件，更新列表、统计与提示。
   */
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
    subscribeToStoreEvent('syncSessions:sessionCancelled', () => {
      debugLog("收到事件 syncSessions:sessionCancelled");
      notifyAlert('会话已取消', 'success');
    });
  }

  /**
   * 统一订阅并记录 handler，便于 teardown 时移除。
   */
  function subscribeToStoreEvent(eventName, handler) {
    if (!syncSessionsStore) {
      debugLog(`尝试订阅 ${eventName} 但 store 未初始化`);
      return;
    }
    debugLog(`订阅 Store 事件: ${eventName}`);
    storeSubscriptions.push({ eventName, handler });
    syncSessionsStore.subscribe(eventName, handler);
  }

  /**
   * 解除订阅并销毁 store，防止泄漏。
   */
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

  /**
   * 外部调用入口：按页加载会话列表（支持 silent 刷新）。
   */
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

  /**
   * 渲染会话列表，包含状态/进度/指标展示。
   */
  window.renderSessions = function (sessions) {
    const container = document.getElementById('sessions-container');
    if (!container) return;

    if (!sessions || sessions.length === 0) {
      container.innerHTML = '<div class="text-center py-4 text-muted">暂无同步会话</div>';
      return;
    }

    const header = createSessionsHeader();
    const rows = sessions.map(session => {
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
        <div class="session-card-grid ${statusClass}">
          <div class="session-cell session-info">
            <div class="session-id">${session.session_id.substring(0, 8)}...</div>
            <div class="text-muted small">${getSyncTypeText(session.sync_type)} • ${getSyncCategoryText(session.sync_category)}</div>
          </div>
          <div class="session-cell session-status">
            <span class="badge bg-${getStatusColor(session.status)}">${statusText}</span>
          </div>
          <div class="session-cell session-progress">
            <div class="progress" style="height: 10px;">
              <div class="progress-bar ${progressInfo.barClass}" role="progressbar" style="width: ${successRate}%" title="${progressInfo.tooltip}"></div>
            </div>
            <div class="text-muted small mt-1">
              <span class="${progressInfo.textClass}">
                <i class="${progressInfo.icon}"></i> ${successRate}% (${successfulInstances}/${totalInstances})
              </span>
            </div>
          </div>
          <div class="session-cell">
            <div class="text-muted small">${startedAt}</div>
          </div>
          <div class="session-cell">
            <div class="text-muted small">${completedAt}</div>
          </div>
          <div class="session-cell session-duration">
            ${getDurationBadge(session.started_at, session.completed_at)}
          </div>
          <div class="session-cell session-actions">
            <button class="btn btn-sm btn-outline-primary" data-action="view" data-id="${session.session_id}">
              <i class="fas fa-eye"></i> 详情
            </button>
            ${session.status === 'running' ? `
            <button class="btn btn-sm btn-outline-danger" data-action="cancel" data-id="${session.session_id}">
              <i class="fas fa-stop"></i> 取消
            </button>` : ''}
          </div>
        </div>`;
    }).join('');

    container.innerHTML = header + rows;

    container.querySelectorAll('[data-action="view"]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        viewSessionDetail(id);
      });
    });
    container.querySelectorAll('[data-action="cancel"]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        cancelSession(id);
      });
    });

  }

  function createSessionsHeader() {
    return `
      <div class="session-card-grid session-card-header" role="presentation">
        <div class="session-cell">会话</div>
        <div class="session-cell">状态</div>
        <div class="session-cell">进度</div>
        <div class="session-cell">开始时间</div>
        <div class="session-cell">完成时间</div>
        <div class="session-cell">耗时</div>
        <div class="session-cell text-end">操作</div>
      </div>`;
  }

  // 渲染分页控件
  /**
   * 构建分页，调用 store actions 切换页码。
   */
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

  /**
   * 查看单个会话详情，触发 store 拉取后展示模态。
   */
  window.viewSessionDetail = function (sessionId) {
    if (!syncSessionsStore) {
      return;
    }
    syncSessionsStore.actions.loadSessionDetail(sessionId);
  };


  /**
   * 将会话详情渲染到模态内容区域。
   */
  window.showSessionDetail = function (session) {
    if (sessionDetailModalController) {
      sessionDetailModalController.open(session);
      return;
    }
    console.warn('sessionDetailModalController 未初始化');
  }

  /**
   * 请求取消会话，成功后刷新列表。
   */
  window.cancelSession = function (sessionId) {
    if (!syncSessionsStore) {
      return;
    }
    if (confirm('确定要取消这个同步会话吗？')) {
      syncSessionsStore.actions.cancelSession(sessionId);
    }
  };

  // 应用筛选条件
  /**
   * 将当前表单筛选应用到列表（重置页码为 1）。
   */
  function applyFilters() {
    applySyncFilters();
  }

  // 将函数暴露到全局作用域
  window.applyFilters = applyFilters;



  /**
   * 清空筛选表单并刷新列表。
   */
  window.clearFilters = function () {
    resetSyncFilters();
  }

  /**
   * 根据成功率计算进度条样式与提示。
   */
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

  /**
   * 构建筛选卡片：自动提交变更并注册卸载清理。
   */
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

  /**
   * 销毁筛选卡片实例，解除 beforeunload 监听。
   */
  function destroySyncFilterCard() {
    if (syncFilterCard?.destroy) {
      syncFilterCard.destroy();
    }
    syncFilterCard = null;
  }

  /**
   * 组合筛选参数并刷新页面或请求。
   */
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

  /**
   * 重置筛选表单并应用空过滤。
   */
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

  /**
   * 将多种 form 输入（原生/umbrella）归一化为 HTMLElement。
   */
  function resolveSyncForm(form) {
    if (!form && syncFilterCard?.form) {
      return syncFilterCard.form;
    }
    if (!form) {
      return document.getElementById(SYNC_FILTER_FORM_ID);
    }
    return form;
  }

  /**
   * 序列化筛选表单，兼容 FilterCard/原生 FormData。
   */
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

  /**
   * 将状态映射为卡片 CSS class。
   */
  function getStatusClass(status) {
    const map = { running: 'running', completed: 'completed', failed: 'failed', cancelled: 'cancelled' };
    return map[status] || '';
  }

  function getStatusText(status) {
    return status || '-';
  }

  /**
   * 将状态映射为 badge 颜色。
   */
  function getStatusColor(status) {
    const map = { running: 'success', completed: 'info', failed: 'danger', cancelled: 'secondary', pending: 'warning' };
    return map[status] || 'secondary';
  }

  /**
   * 同步类型 -> 展示文案。
   */
  function getSyncTypeText(type) {
    const typeMap = {
      'manual_single': '手动单台',
      'manual_batch': '手动批量',
      'manual_task': '手动任务',
      'scheduled_task': '定时任务'
    };
    return typeMap[type] || type || '-';
  }

  /**
   * 同步分类 -> 展示文案。
   */
  function getSyncCategoryText(category) {
    const categoryMap = {
      'account': '账户同步',
      'capacity': '容量同步',
      'config': '配置同步',
      'aggregation': '统计聚合',
      'other': '其他'
    };
    return categoryMap[category] || category || '-';
  }

  /**
   * 计算耗时徽标文本（包含起止时间）。
   */
  function getDurationBadge(startedAt, completedAt) {
    if (!startedAt || !completedAt) return '<span class="text-muted">-</span>';
    
    // 使用统一的时间解析
    const s = timeUtils.parseTime(startedAt);
    const e = timeUtils.parseTime(completedAt);
    
    if (!s || !e) return '<span class="text-muted">-</span>';
    
    const sec = (e - s) / 1000;
    return window.NumberFormat.formatDurationSeconds(sec);
  }

  window.getStatusClass = getStatusClass;
  window.getStatusText = getStatusText;
  window.getStatusColor = getStatusColor;
  window.getSyncTypeText = getSyncTypeText;
  window.getSyncCategoryText = getSyncCategoryText;
  window.getDurationBadge = getDurationBadge;

}

window.SyncSessionsPage = {
  mount: mountSyncSessionsPage,
};
