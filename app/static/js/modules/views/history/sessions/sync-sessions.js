/**
 * 挂载同步会话列表页面。
 *
 * 初始化同步会话中心页面的所有组件，包括会话列表表格、筛选器、
 * 详情模态框和自动刷新功能。支持查看各类同步任务的执行历史。
 *
 * @param {Object} [global=window] - 全局 window 对象
 * @param {Document} [documentRef=document] - document 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountSyncSessionsPage();
 */
function mountSyncSessionsPage(global = window, documentRef = document) {
  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  const SyncSessionsService = global.SyncSessionsService;
  const gridHtml = gridjs?.html;

  if (!gridjs || !GridWrapper) {
    console.error('Grid.js 或 GridWrapper 未加载，会话中心无法初始化');
    return;
  }
  if (!SyncSessionsService) {
    console.error('SyncSessionsService 未加载，会话中心无法初始化');
    return;
  }

  const FILTER_FORM_ID = 'sync-sessions-filter-form';
  const GRID_CONTAINER_ID = 'sessions-grid';
  const AUTO_REFRESH_INTERVAL = 30000;

  let sessionsGrid = null;
  let filterCard = null;
  let syncSessionsService = null;
  let sessionDetailModalController = null;
  let autoRefreshTimer = null;

  const ready = () => {
    if (!initializeService()) {
      return;
    }
    initializeModals();
    initializeFilterCard();
    initializeSessionsGrid();
    bindGridEvents();
    setupAutoRefresh();
  };

  if (documentRef.readyState === 'loading') {
    documentRef.addEventListener('DOMContentLoaded', ready, { once: true });
  } else {
    ready();
  }

  /**
   * 初始化同步会话服务。
   *
   * 创建 SyncSessionsService 实例，用于后续的数据查询操作。
   *
   * @return {boolean} 初始化是否成功
   */
  function initializeService() {
    try {
      syncSessionsService = new SyncSessionsService(global.httpU);
      return true;
    } catch (error) {
      console.error('初始化 SyncSessionsService 失败:', error);
      return false;
    }
  }

  function initializeModals() {
    if (!global.SyncSessionDetailModal?.createController) {
      console.warn('SyncSessionDetailModal 未加载，将无法查看详情');
      return;
    }
    try {
      sessionDetailModalController = global.SyncSessionDetailModal.createController({
        ui: global.UI,
        timeUtils: global.timeUtils,
        modalSelector: '#sessionDetailModal',
        contentSelector: '#session-detail-content',
        getStatusColor,
        getStatusText,
        getSyncTypeText,
        getSyncCategoryText,
      });
    } catch (error) {
      console.error('初始化会话详情模态失败:', error);
    }
  }

  function initializeFilterCard() {
    const factory = global.UI?.createFilterCard;
    if (!factory) {
      console.warn('UI.createFilterCard 未加载，筛选无法自动应用');
      return;
    }
    filterCard = factory({
      formSelector: `#${FILTER_FORM_ID}`,
      autoSubmitOnChange: true,
      onSubmit: ({ values }) => applySyncFilters(values),
      onChange: ({ values }) => applySyncFilters(values),
      onClear: () => applySyncFilters({}),
    });
  }

  function initializeSessionsGrid() {
    const container = documentRef.getElementById(GRID_CONTAINER_ID);
    if (!container) {
      console.error('未找到 sessions-grid 容器');
      return;
    }

    sessionsGrid = new GridWrapper(container, {
      search: false,
      sort: false,
      columns: buildColumns(),
      server: {
        url: '/sync_sessions/api/sessions?sort=started_at&order=desc',
        then: handleServerResponse,
        total: (response) => {
          const payload = response?.data || response || {};
          return Number(payload.total) || 0;
        },
      },
      className: {
        table: 'table table-hover align-middle sessions-grid-table',
      },
    });

    const initialFilters = normalizeFilters(resolveSyncFilters());
    if (Object.keys(initialFilters).length) {
      sessionsGrid.setFilters(initialFilters, { silent: true });
    }
    sessionsGrid.init();
  }

  function buildColumns() {
    return [
      {
        id: 'session_id',
        name: '会话ID',
        width: '130px',
        formatter: (cell, row) => renderSessionId(resolveRowMeta(row)),
      },
      {
        id: 'status',
        name: '状态',
        width: '100px',
        formatter: (cell, row) => renderStatusBadge(resolveRowMeta(row)),
      },
      {
        id: 'progress',
        name: '进度',
        width: '200px',
        sort: false,
        formatter: (cell, row) => renderProgress(resolveRowMeta(row)),
      },
      {
        id: 'sync_type',
        name: '操作方式',
        width: '100px',
        formatter: (cell, row) => renderSyncType(resolveRowMeta(row)),
      },
      {
        id: 'sync_category',
        name: '分类',
        width: '100px',
        formatter: (cell, row) => renderSyncCategory(resolveRowMeta(row)),
      },
      {
        id: 'started_at',
        name: '开始时间',
        width: '150px',
        formatter: (cell) => renderTimestamp(cell),
      },
      {
        id: 'duration',
        name: '耗时',
        width: '100px',
        sort: false,
        formatter: (cell, row) => renderDuration(resolveRowMeta(row)),
      },
      {
        id: 'actions',
        name: '操作',
        width: '140px',
        sort: false,
        formatter: (cell, row) => renderActions(resolveRowMeta(row)),
      },
      { id: '__meta__', hidden: true },
    ];
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || [];
    return items.map((item) => [
      item.session_id || '-',
      item.status || '-',
      null,
      item.sync_type || '-',
      item.sync_category || '-',
      item.started_at || '',
      null,
      null,
      item,
    ]);
  }

  function resolveRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
  }

  function renderSessionId(meta) {
    if (!gridHtml) {
      return meta.session_id || '-';
    }
    const rawId = meta.session_id || '-';
    const truncated = rawId.length > 12 ? `${rawId.substring(0, 12)}…` : rawId;
    const sessionId = escapeHtml(truncated);
    return gridHtml(`<span class="font-monospace small" title="${escapeHtml(rawId)}">${sessionId}</span>`);
  }

  function renderSyncType(meta) {
    if (!gridHtml) {
      return getSyncTypeText(meta.sync_type);
    }
    const text = escapeHtml(getSyncTypeText(meta.sync_type));
    return gridHtml(`<span class="badge bg-primary">${text}</span>`);
  }

  function renderSyncCategory(meta) {
    if (!gridHtml) {
      return getSyncCategoryText(meta.sync_category);
    }
    const text = escapeHtml(getSyncCategoryText(meta.sync_category));
    const colorMap = {
      '账户同步': 'info',
      '容量同步': 'warning',
      '配置同步': 'secondary',
      '统计聚合': 'success',
      '其他': 'light text-dark',
    };
    const color = colorMap[text] || 'secondary';
    return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
  }

  function renderStatusBadge(meta) {
    if (!gridHtml) {
      return getStatusText(meta.status);
    }
    const color = getStatusColor(meta.status);
    const text = escapeHtml(getStatusText(meta.status));
    return gridHtml(`<span class="badge bg-${color}">${text}</span>`);
  }

  function renderProgress(meta) {
    if (!gridHtml) {
      return '-';
    }
    const total = meta.total_instances || 0;
    const success = meta.successful_instances || 0;
    const failed = meta.failed_instances || 0;
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0;
    const info = getProgressInfo(successRate, total, success, failed);
    return gridHtml(`
      <div class="session-progress">
        <div class="progress" style="height:10px;">
          <div class="progress-bar ${info.barClass}" role="progressbar" style="width:${successRate}%" title="${escapeHtml(info.tooltip)}"></div>
        </div>
        <div class="text-muted small mt-1">
          <span class="${info.textClass}">
            <i class="${info.icon}"></i> ${successRate}% (${success}/${total})
          </span>
        </div>
      </div>
    `);
  }

  function renderTimestamp(value) {
    if (!gridHtml) {
      return value || '-';
    }
    if (!value) {
      return gridHtml('<span class="text-muted">-</span>');
    }
    const formatted = global.timeUtils ? global.timeUtils.formatDateTime(value) : value;
    return gridHtml(`<span class="text-muted small">${escapeHtml(formatted || value)}</span>`);
  }

  function renderDuration(meta) {
    if (!gridHtml) {
      return getDurationBadge(meta.started_at, meta.completed_at);
    }
    return gridHtml(getDurationBadge(meta.started_at, meta.completed_at));
  }

  function renderActions(meta) {
    if (!gridHtml) {
      return '';
    }
    const viewBtn = `<button class="btn btn-sm btn-outline-primary" data-action="view" data-id="${escapeHtml(meta.session_id)}">
        <i class="fas fa-eye"></i> 详情
      </button>`;
    const cancelBtn = meta.status === 'running'
      ? `<button class="btn btn-sm btn-outline-danger" data-action="cancel" data-id="${escapeHtml(meta.session_id)}">
            <i class="fas fa-stop"></i> 取消
          </button>`
      : '';
    return gridHtml(`<div class="d-flex gap-2">${viewBtn}${cancelBtn}</div>`);
  }

  function bindGridEvents() {
    const container = documentRef.getElementById(GRID_CONTAINER_ID);
    if (!container) {
      return;
    }
    container.addEventListener('click', (event) => {
      const actionBtn = event.target.closest('[data-action]');
      if (!actionBtn) {
        return;
      }
      const sessionId = actionBtn.getAttribute('data-id');
      const action = actionBtn.getAttribute('data-action');
      if (action === 'view') {
        viewSessionDetail(sessionId);
      } else if (action === 'cancel') {
        cancelSession(sessionId);
      }
    });
  }

  function setupAutoRefresh() {
    if (!sessionsGrid) {
      return;
    }
    clearAutoRefresh();
    autoRefreshTimer = global.setInterval(() => {
      sessionsGrid?.refresh?.();
    }, AUTO_REFRESH_INTERVAL);
    global.addEventListener('beforeunload', clearAutoRefresh, { once: true });
  }

  function clearAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  function applySyncFilters(values) {
    if (!sessionsGrid) {
      return;
    }
    const filters = normalizeFilters(resolveSyncFilters(values));
    sessionsGrid.updateFilters(filters);
  }

  function resolveSyncFilters(overrideValues) {
    const rawValues = overrideValues && Object.keys(overrideValues || {}).length
      ? overrideValues
      : collectFormValues();
    const result = {};
    Object.entries(rawValues || {}).forEach(([key, value]) => {
      if (key === 'csrf_token') {
        return;
      }
      const normalized = sanitizeFilterValue(value);
      if (normalized === null || normalized === undefined) {
        return;
      }
      if (Array.isArray(normalized) && !normalized.length) {
        return;
      }
      result[key] = normalized;
    });
    return result;
  }

  function collectFormValues() {
    if (filterCard?.serialize) {
      return filterCard.serialize();
    }
    const form = documentRef.getElementById(FILTER_FORM_ID);
    if (!form) {
      return {};
    }
    if (global.UI?.serializeForm) {
      return global.UI.serializeForm(form);
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

  function normalizeFilters(raw) {
    const filters = { ...(raw || {}) };
    Object.keys(filters).forEach((key) => {
      const value = filters[key];
      if (value === undefined || value === null || value === '' || (Array.isArray(value) && !value.length)) {
        delete filters[key];
      }
    });
    return filters;
  }

  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return value
        .map((item) => sanitizePrimitiveValue(item))
        .filter((item) => item !== null && item !== undefined);
    }
    return sanitizePrimitiveValue(value);
  }

  function sanitizePrimitiveValue(value) {
    if (typeof value === 'string') {
      const trimmed = value.trim();
      return trimmed === '' ? null : trimmed;
    }
    if (value === undefined || value === null) {
      return null;
    }
    return value;
  }

  function viewSessionDetail(sessionId) {
    if (!sessionId) {
      return;
    }
    syncSessionsService
      .detail(sessionId)
      .then((response) => {
        const payload = response?.data || response || {};
        const session = payload.session || payload;
        showSessionDetail(session);
      })
      .catch((error) => {
        console.error('获取会话详情失败:', error);
        notifyError(error?.message || '获取会话详情失败');
      });
  }

  function showSessionDetail(session) {
    if (sessionDetailModalController) {
      sessionDetailModalController.open(session);
      return;
    }
    console.warn('会话详情模态未初始化');
  }

  function cancelSession(sessionId) {
    if (!sessionId) {
      return;
    }
    if (!global.confirm?.('确定要取消这个同步会话吗？')) {
      return;
    }
    syncSessionsService
      .cancel(sessionId, {})
      .then((response) => {
        const payload = response?.data || response || {};
        notifySuccess(payload?.message || '会话已取消');
        sessionsGrid?.refresh?.();
      })
      .catch((error) => {
        console.error('取消会话失败:', error);
        notifyError(error?.message || '取消会话失败');
      });
  }

  function notifySuccess(message) {
    if (global.toast?.success) {
      global.toast.success(message);
    } else {
      console.info(message);
    }
  }

  function notifyError(message) {
    if (global.toast?.error) {
      global.toast.error(message);
    } else {
      console.error(message);
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

  // 暴露给其他模块（如详情模态）
  global.viewSessionDetail = viewSessionDetail;
  global.cancelSession = cancelSession;
  global.getProgressInfo = getProgressInfo;
  global.getStatusText = getStatusText;
  global.getStatusColor = getStatusColor;
  global.getSyncTypeText = getSyncTypeText;
  global.getSyncCategoryText = getSyncCategoryText;
  global.getDurationBadge = getDurationBadge;
}

function getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances) {
  if (totalInstances === 0) {
    return { barClass: 'bg-secondary', textClass: 'text-muted', icon: 'fas fa-question-circle', tooltip: '无实例数据' };
  }
  if (successRate === 100) {
    return { barClass: 'bg-success', textClass: 'text-success', icon: 'fas fa-check-circle', tooltip: '全部成功' };
  }
  if (successRate === 0) {
    return { barClass: 'bg-danger', textClass: 'text-danger', icon: 'fas fa-times-circle', tooltip: '全部失败' };
  }
  if (successRate >= 70) {
    return {
      barClass: 'bg-warning',
      textClass: 'text-warning',
      icon: 'fas fa-exclamation-triangle',
      tooltip: `部分成功 (${successfulInstances} 成功, ${failedInstances} 失败)`,
    };
  }
  return {
    barClass: 'bg-danger',
    textClass: 'text-danger',
    icon: 'fas fa-exclamation-triangle',
    tooltip: `大部分失败 (${successfulInstances} 成功, ${failedInstances} 失败)`,
  };
}

function getStatusText(status) {
  return status || '-';
}

function getStatusColor(status) {
  const map = { running: 'success', completed: 'info', failed: 'danger', cancelled: 'secondary', pending: 'warning' };
  return map[status] || 'secondary';
}

function getSyncTypeText(type) {
  const typeMap = {
    manual_single: '手动单台',
    manual_batch: '手动批量',
    manual_task: '手动任务',
    scheduled_task: '定时任务',
  };
  return typeMap[type] || type || '-';
}

function getSyncCategoryText(category) {
  const categoryMap = {
    account: '账户同步',
    capacity: '容量同步',
    config: '配置同步',
    aggregation: '统计聚合',
    other: '其他',
  };
  return categoryMap[category] || category || '-';
}

function getDurationBadge(startedAt, completedAt) {
  if (!startedAt || !completedAt) {
    return '<span class="text-muted">-</span>';
  }
  const timeUtils = window.timeUtils;
  const NumberFormat = window.NumberFormat;
  const start = timeUtils?.parseTime ? timeUtils.parseTime(startedAt) : new Date(startedAt);
  const end = timeUtils?.parseTime ? timeUtils.parseTime(completedAt) : new Date(completedAt);
  if (!start || !end || Number.isNaN(start) || Number.isNaN(end)) {
    return '<span class="text-muted">-</span>';
  }
  const seconds = Math.max(0, (end - start) / 1000);
  if (NumberFormat?.formatDurationSeconds) {
    return NumberFormat.formatDurationSeconds(seconds);
  }
  return `<span class="text-muted">${seconds.toFixed(1)} s</span>`;
}

window.SyncSessionsPage = {
  mount: mountSyncSessionsPage,
};
