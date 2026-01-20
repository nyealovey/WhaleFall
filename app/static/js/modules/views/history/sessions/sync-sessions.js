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
  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，会话中心无法初始化');
    return;
  }

  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  if (!gridjs || !GridWrapper) {
    console.error('Grid.js 或 GridWrapper 未加载，会话中心无法初始化');
    return;
  }

  const GridPage = global.Views?.GridPage;
  const GridPlugins = global.Views?.GridPlugins;
  if (!GridPage?.mount || !GridPlugins) {
    console.error('Views.GridPage 或 Views.GridPlugins 未加载，会话中心无法初始化');
    return;
  }

  const escapeHtml = global.UI?.escapeHtml;
  const rowMeta = global.GridRowMeta;
  if (typeof escapeHtml !== 'function' || typeof rowMeta?.get !== 'function') {
    console.error('UI.escapeHtml 或 GridRowMeta 未加载，会话中心无法初始化');
    return;
  }

  const TaskRunsService = global.TaskRunsService;
  if (!TaskRunsService) {
    console.error('TaskRunsService 未加载，运行中心无法初始化');
    return;
  }

  const pageRoot = documentRef.getElementById('task-runs-page-root');
  if (!pageRoot) {
    console.warn('未找到运行中心页面根元素');
    return;
  }

  const gridHtml = gridjs.html;
  const { ready } = helpers;

  const FILTER_FORM_ID = 'task-runs-filter-form';
  const GRID_CONTAINER_ID = 'task-runs-grid';
  const AUTO_REFRESH_INTERVAL = 30000;
  const SESSION_STATS_IDS = {
    total: 'totalSessions',
    running: 'runningSessions',
    completed: 'completedSessions',
    failed: 'failedSessions',
  };

  const getRowMeta = (row) => rowMeta.get(row);

  let gridPage = null;
  let sessionsGrid = null;
  let taskRunsService = null;
  let sessionDetailModalController = null;
  let autoRefreshTimer = null;

  ready(() => {
    if (!initializeService()) {
      return;
    }
    initializeModals();
    initializeGridPage();
    setupAutoRefresh();
  });

  /**
   * 初始化同步会话服务。
   *
   * 创建 TaskRunsService 实例，用于后续的数据查询操作。
   *
   * @param {void} 无参数。直接使用全局依赖。
   * @return {boolean} 初始化是否成功
   */
	  function initializeService() {
	    try {
	      taskRunsService = new TaskRunsService();
	      return true;
	    } catch (error) {
	      console.error('初始化 TaskRunsService 失败:', error);
	      return false;
	    }
	  }

  /**
   * 初始化同步会话详情模态。
   *
   * @param {void} 无参数。依赖全局 TaskRunDetailModal。
   * @returns {void}
   */
  function initializeModals() {
    if (!global.TaskRunDetailModal?.createController) {
      console.warn('TaskRunDetailModal 未加载，将无法查看详情');
      return;
    }
    try {
      sessionDetailModalController = global.TaskRunDetailModal.createController({
        ui: global.UI,
        timeUtils: global.timeUtils,
        modalSelector: '#sessionDetailModal',
        contentSelector: '#session-detail-content',
      });
    } catch (error) {
      console.error('初始化会话详情模态失败:', error);
    }
  }

  /**
   * 初始化会话列表 grid page skeleton。
   *
   * @param {void} 无参数。直接挂载到 GRID_CONTAINER_ID。
   * @returns {void}
   */
  function initializeGridPage() {
    const container = pageRoot.querySelector(`#${GRID_CONTAINER_ID}`);
    if (!container) {
      console.error('未找到 sessions-grid 容器');
      return;
    }

    gridPage = GridPage.mount({
      root: pageRoot,
      grid: `#${GRID_CONTAINER_ID}`,
      filterForm: `#${FILTER_FORM_ID}`,
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: taskRunsService.getGridUrl(),
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return Number(payload.total) || 0;
          },
        },
        className: {
          table: 'table table-hover align-middle sessions-grid-table',
        },
      },
      filters: {
        allowedKeys: ['status', 'trigger_source', 'task_category', 'task_key'],
        normalize: (filters) => normalizeGridFilters(filters),
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
        }),
        GridPlugins.actionDelegation({
          actions: {
            view: ({ event, el }) => {
              event.preventDefault();
              viewSessionDetail(el.getAttribute('data-id'));
            },
            cancel: ({ event, el }) => {
              event.preventDefault();
              cancelSession(el.getAttribute('data-id'));
            },
          },
        }),
      ],
    });

    sessionsGrid = gridPage?.gridWrapper || null;
  }

  function normalizeGridFilters(filters) {
    const source = filters && typeof filters === 'object' ? filters : {};
    const normalized = {};

    const status = typeof source.status === 'string' ? source.status.trim() : '';
    if (status && status !== 'all') {
      normalized.status = status;
    }

    const triggerSource = typeof source.trigger_source === 'string' ? source.trigger_source.trim() : '';
    if (triggerSource && triggerSource !== 'all') {
      normalized.trigger_source = triggerSource;
    }

    const taskCategory = typeof source.task_category === 'string' ? source.task_category.trim() : '';
    if (taskCategory && taskCategory !== 'all') {
      normalized.task_category = taskCategory;
    }

    const taskKey = typeof source.task_key === 'string' ? source.task_key.trim() : '';
    if (taskKey) {
      normalized.task_key = taskKey;
    }

    return normalized;
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
        id: 'run_id',
        name: '运行ID',
        width: '140px',
        formatter: (cell, row) => renderRunId(getRowMeta(row)),
      },
      {
        id: 'status',
        name: '状态',
        width: '100px',
        formatter: (cell, row) => renderStatusBadge(getRowMeta(row)),
      },
      {
        id: 'progress',
        name: '进度',
        width: '220px',
        sort: false,
        formatter: (cell, row) => renderProgress(getRowMeta(row)),
      },
      {
        id: 'task',
        name: '任务',
        width: '260px',
        formatter: (cell, row) => renderTask(getRowMeta(row)),
      },
      {
        id: 'trigger_source',
        name: '来源',
        width: '110px',
        formatter: (cell, row) => renderTriggerSource(getRowMeta(row)),
      },
      {
        id: 'task_category',
        name: '分类',
        width: '110px',
        formatter: (cell, row) => renderTaskCategory(getRowMeta(row)),
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
        formatter: (cell, row) => renderDuration(getRowMeta(row)),
      },
      {
        id: 'actions',
        name: '操作',
        width: '110px',
        sort: false,
        formatter: (cell, row) => renderActions(getRowMeta(row)),
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
      item.run_id || '-',
      item.status || '-',
      null,
      null,
      item.trigger_source || '-',
      item.task_category || '-',
      item.started_at || '',
      null,
      null,
      item,
    ]);
  }

  /**
   * 渲染运行 ID 单元格。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} gridjs formatter 结果。
   */
  function renderRunId(meta) {
    if (!gridHtml) {
      return meta.run_id || '-';
    }
    const rawId = meta.run_id || '-';
    const truncated = rawId.length > 12 ? `${rawId.substring(0, 12)}…` : rawId;
    const displayId = escapeHtml(truncated);
    return gridHtml(`<span class="font-monospace small" title="${escapeHtml(rawId)}">${displayId}</span>`);
  }

  /**
   * 渲染任务信息（task_name/task_key）。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 渲染后的 HTML。
   */
  function renderTask(meta) {
    const name = meta.task_name || meta.task_key || '-';
    const key = meta.task_key || '';
    if (!gridHtml) {
      return name;
    }
    const keyHtml = key ? `<span class="text-muted small font-monospace">${escapeHtml(key)}</span>` : '';
    return gridHtml(`
      <div class="d-flex flex-column">
        <span class="fw-semibold">${escapeHtml(name)}</span>
        ${keyHtml}
      </div>
    `);
  }

  /**
   * 渲染触发来源徽章。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 渲染后的 HTML。
   */
  function renderTriggerSource(meta) {
    const text = getTriggerSourceText(meta.trigger_source);
    if (!gridHtml) {
      return text;
    }
    return gridHtml(buildChipOutlineHtml(text, 'brand', 'fas fa-bolt'));
  }

  /**
   * 渲染任务分类徽章。
   *
   * @param {Object} meta 元数据对象。
   * @returns {string|Object} 渲染后的 HTML。
   */
  function renderTaskCategory(meta) {
    const text = getTaskCategoryText(meta.task_category);
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
    const total = meta.progress_total || 0;
    const success = meta.progress_completed || 0;
    const failed = meta.progress_failed || 0;
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
        <div class="progress wf-progress wf-progress--md">
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
      <button class="btn btn-outline-secondary btn-icon" data-action="view" data-id="${escapeHtml(meta.run_id)}" title="查看详情">
        <i class="fas fa-eye"></i>
      </button>`;
    const cancelBtn = meta.status === 'running'
      ? `
        <button class="btn btn-outline-danger btn-icon" data-action="cancel" data-id="${escapeHtml(meta.run_id)}" title="取消任务">
          <i class="fas fa-stop"></i>
        </button>`
      : '';
    return gridHtml(`<div class="d-flex gap-2 justify-content-center">${viewBtn}${cancelBtn}</div>`);
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
   * 打开详情模态。
   *
   * @param {string|number} sessionId 会话唯一标识。
   * @returns {void}
   */
  function viewSessionDetail(runId) {
    if (!runId) {
      return;
    }
    taskRunsService
      .detail(runId)
      .then((response) => {
        const payload = response?.data || response || {};
        showSessionDetail({
          run: payload.run || {},
          items: Array.isArray(payload.items) ? payload.items : [],
        });
      })
      .catch((error) => {
        console.error('获取任务详情失败:', error);
        notifyError(error?.message || '获取任务详情失败');
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
    console.warn('详情模态未初始化');
  }

  /**
   * 调用 API 取消会话。
   *
   * @param {string|number} sessionId 会话 ID。
   * @returns {void}
   */
  function cancelSession(runId) {
    if (!runId) {
      return;
    }

    const confirmDanger = global.UI?.confirmDanger;
    const confirmPromise = typeof confirmDanger === 'function'
      ? confirmDanger({
          title: '确认取消任务',
          message: '该操作仅标记取消（不会强制终止线程/进程），任务会在循环边界尽力提前退出。',
          details: [
            { label: '结果入口', value: '可在运行中心查看取消后的状态与错误信息', tone: 'warning' },
          ],
          confirmText: '取消任务',
          confirmButtonClass: 'btn-danger',
          resultUrl: '/history/sessions',
          resultText: '前往运行中心',
        })
      : Promise.resolve(global.confirm?.('确定要取消这个任务吗？') === true);

    confirmPromise.then((confirmed) => {
      if (!confirmed) {
        return;
      }
      return taskRunsService.cancel(runId, {});
    }).then((response) => {
      if (!response) {
        return;
      }
      const payload = response?.data || response || {};
      notifySuccess(payload?.message || '任务已取消');
      sessionsGrid?.refresh?.();
    }).catch((error) => {
      console.error('取消任务失败:', error);
      notifyError(error?.message || '取消任务失败');
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

  // 暴露给其他模块（如详情模态）
  global.viewSessionDetail = viewSessionDetail;
  global.cancelSession = cancelSession;
  global.getProgressInfo = getProgressInfo;
  global.getStatusText = getStatusText;
  global.getStatusColor = getStatusColor;
  global.getTriggerSourceText = getTriggerSourceText;
  global.getTaskCategoryText = getTaskCategoryText;
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
  const resolver = window.UI?.Terms?.resolveRunStatusText;
  if (typeof resolver === 'function') {
    return resolver(status);
  }
  switch (status) {
    case 'pending':
      return '等待中';
    case 'running':
      return '运行中';
    case 'completed':
      return '已完成';
    case 'failed':
      return '失败';
    case 'cancelled':
      return '已取消';
    case 'paused':
      return '已暂停';
    default:
      return status || '-';
  }
}

/**
 * 状态对应的徽章颜色。
 *
 * @param {string} status 状态常量。
 * @returns {string} Bootstrap 颜色名。
 */
function getStatusColor(status) {
  switch (status) {
    case 'running':
      return 'success';
    case 'completed':
      return 'info';
    case 'failed':
      return 'danger';
    case 'cancelled':
      return 'secondary';
    case 'pending':
    case 'paused':
      return 'warning';
    default:
      return 'secondary';
  }
}

function getStatusVariant(status) {
  const color = getStatusColor(status);
  switch (color) {
    case 'success':
      return 'success';
    case 'info':
      return 'info';
    case 'danger':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'secondary':
    default:
      return 'muted';
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'running':
      return 'fas fa-sync-alt';
    case 'pending':
      return 'fas fa-hourglass-half';
    case 'completed':
      return 'fas fa-check';
    case 'failed':
      return 'fas fa-times';
    case 'cancelled':
      return 'fas fa-ban';
    case 'paused':
      return 'fas fa-pause';
    default:
      return 'fas fa-info-circle';
  }
}

/**
 * 同步类型文本。
 *
 * @param {string} type 同步类型标识。
 * @returns {string} 对应的中文描述。
 */
function getSyncTypeText(type) {
  switch (type) {
    case 'manual_single':
      return '手动单台';
    case 'manual_batch':
      return '手动批量';
    case 'manual_task':
      return '手动任务';
    case 'scheduled_task':
      return '定时任务';
    default:
      return type || '-';
  }
}

/**
 * 同步类别文本。
 *
 * @param {string} category 同步类别标识。
 * @returns {string} 中文描述。
 */
function getSyncCategoryText(category) {
  switch (category) {
    case 'account':
      return '账户同步';
    case 'capacity':
      return '容量同步';
    case 'config':
      return '配置同步';
    case 'aggregation':
      return '统计聚合';
    case 'classification':
      return '账户分类';
    case 'other':
      return '其他';
    default:
      return category || '-';
  }
}

/**
 * 触发来源文本。
 *
 * @param {string} source 来源标识。
 * @returns {string} 中文描述。
 */
function getTriggerSourceText(source) {
  switch (source) {
    case 'scheduled':
      return '定时任务';
    case 'manual':
      return '手动触发';
    case 'api':
      return 'API';
    default:
      return source || '-';
  }
}

/**
 * 任务分类文本。
 *
 * @param {string} category 分类标识。
 * @returns {string} 中文描述。
 */
function getTaskCategoryText(category) {
  switch (category) {
    case 'account':
      return '账户';
    case 'capacity':
      return '容量';
    case 'aggregation':
      return '聚合';
    case 'classification':
      return '分类';
    case 'other':
      return '其他';
    default:
      return category || '-';
  }
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
