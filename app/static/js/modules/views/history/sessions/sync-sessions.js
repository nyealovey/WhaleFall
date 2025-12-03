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
  const SESSION_STATS_IDS = {
    total: 'totalSessions',
    running: 'runningSessions',
    completed: 'completedSessions',
    failed: 'failedSessions',
  };

  let sessionsGrid = null;
  let filterCard = null;
  let syncSessionsService = null;
  let sessionDetailModalController = null;
  let autoRefreshTimer = null;

  /**
   * DOM 就绪回调，负责初始化服务与组件。
   *
   * @param {void} 无参数。直接在 DOMContentLoaded 中执行。
   * @returns {void}
   */
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
   * @param {void} 无参数。直接使用全局依赖。
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

  /**
   * 初始化同步会话详情模态。
   *
   * @param {void} 无参数。依赖全局 SyncSessionDetailModal。
   * @returns {void}
   */
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

  /**
   * 初始化同步筛选表单。
   *
   * @param {void} 无参数。调用 UI.createFilterCard。
   * @returns {void}
   */
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

  /**
   * 初始化 gridjs 会话列表。
   *
   * @param {void} 无参数。直接挂载到 GRID_CONTAINER_ID。
   * @returns {void}
   */
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
        url: '/history/sessions/api/sessions?sort=started_at&order=desc',
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

  /**
   * 构建 Grid 列配置。
   *
   * @param {void} 无参数。基于 gridHtml 渲染。
   * @returns {Array<Object>} gridjs 列配置。
   */
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
        width: '220px',
        sort: false,
        formatter: (cell, row) => renderProgress(resolveRowMeta(row)),
      },
      {
        id: 'sync_type',
        name: '操作方式',
        width: '110px',
        formatter: (cell, row) => renderSyncType(resolveRowMeta(row)),
      },
      {
        id: 'sync_category',
        name: '分类',
        width: '110px',
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
        width: '110px',
        sort: false,
        formatter: (cell, row) => renderActions(resolveRowMeta(row)),
      },
      { id: '__meta__', hidden: true },
    ];
  }

  /**
   * 处理服务端响应，返回 gridjs 可消费数据。
   *
   * @param {Object} response 服务端返回的响应对象。
   * @returns {Array<Array>} gridjs 兼容的行数据。
   */
  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = payload.items || [];
    updateSessionStats(payload);
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

  /**
   * 从 gridjs 行取出原始数据。
   *
   * @param {Object} row gridjs 行对象。
   * @returns {Object} 行末尾的元数据。
   */
  function resolveRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
  }

  /**
   * 渲染会话 ID 单元格。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} gridjs formatter 结果。
   */
  function renderSessionId(meta) {
    if (!gridHtml) {
      return meta.session_id || '-';
    }
    const rawId = meta.session_id || '-';
    const truncated = rawId.length > 12 ? `${rawId.substring(0, 12)}…` : rawId;
    const sessionId = escapeHtml(truncated);
    return gridHtml(`<span class="font-monospace small" title="${escapeHtml(rawId)}">${sessionId}</span>`);
  }

  /**
   * 渲染同步类型徽章。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 渲染后的 HTML。
   */
  function renderSyncType(meta) {
    const text = getSyncTypeText(meta.sync_type);
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildChipOutlineHtml(text, 'brand', 'fas fa-random'));
  }

  /**
   * 渲染同步分类徽章。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 渲染后的 HTML。
   */
  function renderSyncCategory(meta) {
    const text = getSyncCategoryText(meta.sync_category);
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildChipOutlineHtml(text, 'muted', 'fas fa-layer-group'));
  }

  /**
   * 渲染状态标签。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 格式化后的状态内容。
   */
  function renderStatusBadge(meta) {
    const text = getStatusText(meta.status);
    const variant = getStatusVariant(meta.status);
    const icon = getStatusIcon(meta.status);
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildStatusPillHtml(text, variant, icon));
  }

  /**
   * 渲染进度条。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 包含进度信息的 HTML。
   */
  function renderProgress(meta) {
    const total = meta.total_instances || 0;
    const success = meta.successful_instances || 0;
    const failed = meta.failed_instances || 0;
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0;
    const info = getProgressInfo(successRate, total, success, failed);
    if (!gridHtml) {
      return `${successRate}% (${success}/${total})`;
    }
    const barClass = `progress-bar progress-bar--${info.variant}`;
    const pillHtml = buildStatusPillHtml(`${successRate}%`, info.variant, info.icon);
    const detail = escapeHtml(info.detail);
    return gridHtml(`
      <div class="session-progress">
        <div class="progress">
          <div class="${barClass}" role="progressbar" style="width:${successRate}%" aria-valuenow="${successRate}" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <div class="session-progress__meta">
          ${pillHtml}
          <span class="text-muted small">${detail}</span>
        </div>
      </div>
    `);
  }

  /**
   * 渲染任务开始时间。
   *
   * @param {string} value 后端提供的时间戳。
   * @returns {string|Object} 渲染后的时间文本。
   */
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

  /**
   * 渲染任务耗时。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 耗时徽章或 HTML。
   */
  function renderDuration(meta) {
    const durationText = getDurationBadge(meta.started_at, meta.completed_at);
    if (!gridHtml) {
      return durationText;
    }
    return gridHtml(buildChipOutlineHtml(durationText, 'muted', 'far fa-clock'));
  }

  /**
   * 渲染详情/取消按钮。
   *
   * @param {Object} meta 行元数据。
   * @returns {string|Object} 操作列 HTML。
   */
  function renderActions(meta) {
    if (!gridHtml) {
      return '查看';
    }
    const viewBtn = `
      <button class="btn btn-outline-secondary btn-icon" data-action="view" data-id="${escapeHtml(meta.session_id)}" title="查看详情">
        <i class="fas fa-eye"></i>
      </button>`;
    const cancelBtn = meta.status === 'running'
      ? `
        <button class="btn btn-outline-secondary btn-icon text-danger" data-action="cancel" data-id="${escapeHtml(meta.session_id)}" title="取消会话">
          <i class="fas fa-stop"></i>
        </button>`
      : '';
    return gridHtml(`<div class="d-flex gap-2 justify-content-center">${viewBtn}${cancelBtn}</div>`);
  }

  function renderStatusPill(text, variant = 'muted', iconClass) {
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildStatusPillHtml(text, variant, iconClass));
  }

  function renderChipOutline(text, tone = 'muted', iconClass) {
    if (!gridHtml) {
      return text || '-';
    }
    return gridHtml(buildChipOutlineHtml(text, tone, iconClass));
  }

  function buildStatusPillHtml(text, variant = 'muted', iconClass) {
    const classes = ['status-pill'];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '')}</span>`;
  }

  function buildChipOutlineHtml(text, tone = 'muted', iconClass) {
    const classes = ['chip-outline'];
    if (tone === 'brand') {
      classes.push('chip-outline--brand');
    } else if (tone === 'muted') {
      classes.push('chip-outline--muted');
    }
    const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '-')}</span>`;
  }

  /**
   * 绑定表格上的按钮事件。
   *
   * @param {void} 无参数。直接委托 GRID_CONTAINER_ID。
   * @returns {void}
   */
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

  /**
   * 启动自动刷新定时器。
   *
   * @param {void} 无参数。依赖 sessionsGrid 状态。
   * @returns {void}
   */
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

  /**
   * 停止自动刷新。
   *
   * @param {void} 无参数。清理 autoRefreshTimer。
   * @returns {void}
   */
  function clearAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  /**
   * 应用筛选条件。
   *
   * @param {Object} values 筛选项，通常来源于表单。
   * @returns {void}
   */
  function applySyncFilters(values) {
    if (!sessionsGrid) {
      return;
    }
    const filters = normalizeFilters(resolveSyncFilters(values));
    sessionsGrid.updateFilters(filters);
  }

  function updateSessionStats(payload) {
    const stats = {
      total: Number(payload.total) || 0,
      running: 0,
      completed: 0,
      failed: 0,
    };
    (payload.items || []).forEach((item) => {
      const status = (item?.status || '').toLowerCase();
      if (['running', 'pending', 'paused'].includes(status)) {
        stats.running += 1;
      } else if (status === 'completed') {
        stats.completed += 1;
      } else if (['failed', 'cancelled'].includes(status)) {
        stats.failed += 1;
      }
    });
    setStatValue(SESSION_STATS_IDS.total, stats.total);
    setStatValue(SESSION_STATS_IDS.running, stats.running);
    setStatValue(SESSION_STATS_IDS.completed, stats.completed);
    setStatValue(SESSION_STATS_IDS.failed, stats.failed);
  }

  function setStatValue(elementId, value) {
    if (!elementId) {
      return;
    }
    const element = documentRef.getElementById(elementId);
    if (element) {
      element.textContent = value;
    }
  }

  /**
   * 解析表单筛选值，支持覆盖。
   *
   * @param {Object} [overrideValues] 外部传入的筛选覆盖项。
   * @returns {Object} 规范化后的筛选值。
   */
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

  /**
   * 收集表单数据。
   *
   * @param {void} 无参数。默认读取 FILTER_FORM_ID。
   * @returns {Object} 表单键值对。
   */
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

  /**
   * 移除空值，返回有效过滤列表。
   *
   * @param {Object} raw 原始筛选值。
   * @returns {Object} 过滤后的参数。
   */
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

  /**
   * 规范化过滤值。
   *
   * @param {*} value 原始值，可能为数组或字符串。
   * @returns {*|null} 处理后的值。
   */
  function sanitizeFilterValue(value) {
    if (Array.isArray(value)) {
      return value
        .map((item) => sanitizePrimitiveValue(item))
        .filter((item) => item !== null && item !== undefined);
    }
    return sanitizePrimitiveValue(value);
  }

  /**
   * 处理单个值（数字/字符串）。
   *
   * @param {*} value 单个输入值。
   * @returns {*|null} 清洗后的值。
   */
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

  /**
   * 打开详情模态。
   *
   * @param {string|number} sessionId 会话唯一标识。
   * @returns {void}
   */
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

  /**
   * 渲染并展示详情模态内容。
   *
   * @param {Object} session 会话详情数据。
   * @returns {void}
   */
  function showSessionDetail(session) {
    if (sessionDetailModalController) {
      sessionDetailModalController.open(session);
      return;
    }
    console.warn('会话详情模态未初始化');
  }

  /**
   * 调用 API 取消会话。
   *
   * @param {string|number} sessionId 会话 ID。
   * @returns {void}
   */
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

  /**
   * 统一成功提示。
   *
   * @param {string} message 需要展示的提示。
   * @returns {void}
   */
  function notifySuccess(message) {
    if (global.toast?.success) {
      global.toast.success(message);
    } else {
      console.info(message);
    }
  }

  /**
   * 统一错误提示。
   *
   * @param {string} message 提示文本。
   * @returns {void}
   */
  function notifyError(message) {
    if (global.toast?.error) {
      global.toast.error(message);
    } else {
      console.error(message);
    }
  }

  /**
   * 简单 HTML 转义。
   *
   * @param {*} value 原始输入。
   * @returns {string} 转义后的字符串。
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

/**
 * 根据成功率返回进度条样式。
 *
 * @param {number} successRate 成功率（0-100）。
 * @param {number} totalInstances 总实例数。
 * @param {number} successfulInstances 成功的实例数。
 * @param {number} failedInstances 失败的实例数。
 * @returns {Object} 包含 barClass/textClass/icon/tooltip 的信息。
 */
function getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances) {
  if (totalInstances === 0) {
    return { variant: 'muted', icon: 'fas fa-minus', detail: '无实例数据' };
  }
  if (successRate === 100) {
    return { variant: 'success', icon: 'fas fa-check', detail: '全部成功' };
  }
  if (failedInstances === totalInstances) {
    return { variant: 'danger', icon: 'fas fa-times', detail: '全部失败' };
  }
  if (successRate >= 70) {
    return {
      variant: 'warning',
      icon: 'fas fa-exclamation-triangle',
      detail: `${successfulInstances}/${totalInstances} 成功`,
    };
  }
  return {
    variant: 'danger',
    icon: 'fas fa-exclamation-circle',
    detail: `${failedInstances} 个失败`,
  };
}

/**
 * 输出状态名称。
 *
 * @param {string} status 状态常量。
 * @returns {string} 展示文本。
 */
function getStatusText(status) {
  const map = {
    pending: '排队中',
    running: '进行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    paused: '已暂停',
  };
  return map[status] || status || '-';
}

/**
 * 状态对应的徽章颜色。
 *
 * @param {string} status 状态常量。
 * @returns {string} Bootstrap 颜色名。
 */
function getStatusColor(status) {
  const map = { running: 'success', completed: 'info', failed: 'danger', cancelled: 'secondary', pending: 'warning', paused: 'warning' };
  return map[status] || 'secondary';
}

function getStatusVariant(status) {
  const color = getStatusColor(status);
  const map = { success: 'success', info: 'info', danger: 'danger', warning: 'warning', secondary: 'muted' };
  return map[color] || 'muted';
}

function getStatusIcon(status) {
  const map = {
    running: 'fas fa-sync-alt',
    pending: 'fas fa-hourglass-half',
    completed: 'fas fa-check',
    failed: 'fas fa-times',
    cancelled: 'fas fa-ban',
    paused: 'fas fa-pause',
  };
  return map[status] || 'fas fa-info-circle';
}

/**
 * 同步类型文本。
 *
 * @param {string} type 同步类型标识。
 * @returns {string} 对应的中文描述。
 */
function getSyncTypeText(type) {
  const typeMap = {
    manual_single: '手动单台',
    manual_batch: '手动批量',
    manual_task: '手动任务',
    scheduled_task: '定时任务',
  };
  return typeMap[type] || type || '-';
}

/**
 * 同步类别文本。
 *
 * @param {string} category 同步类别标识。
 * @returns {string} 中文描述。
 */
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

/**
 * 构造耗时徽章 HTML。
 *
 * @param {string} startedAt 开始时间。
 * @param {string} completedAt 结束时间。
 * @returns {string} 渲染后的耗时描述。
 */
function getDurationBadge(startedAt, completedAt) {
  if (!startedAt || !completedAt) {
    return '-';
  }
  const timeUtils = window.timeUtils;
  const NumberFormat = window.NumberFormat;
  const start = timeUtils?.parseTime ? timeUtils.parseTime(startedAt) : new Date(startedAt);
  const end = timeUtils?.parseTime ? timeUtils.parseTime(completedAt) : new Date(completedAt);
  if (!start || !end || Number.isNaN(start) || Number.isNaN(end)) {
    return '-';
  }
  const seconds = Math.max(0, (end - start) / 1000);
  if (NumberFormat?.formatDurationSeconds) {
    return stripHtmlTags(NumberFormat.formatDurationSeconds(seconds));
  }
  if (seconds >= 60) {
    return `${(seconds / 60).toFixed(1)} min`;
  }
  return `${seconds.toFixed(1)} s`;
}

function stripHtmlTags(content) {
  if (typeof content !== 'string') {
    return content;
  }
  return content.replace(/<[^>]+>/g, '');
}

window.SyncSessionsPage = {
  mount: mountSyncSessionsPage,
};
