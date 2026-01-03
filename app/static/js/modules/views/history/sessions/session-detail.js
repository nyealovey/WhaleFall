(function (global, document) {
  'use strict';

  /**
   * 创建会话详情渲染器。
   *
   * @param {Object} [options] - 选项
   * @param {HTMLElement} [options.container] - 详情目标容器
   * @param {string} [options.templateSelector] - 模板选择器
   * @param {Object} [options.timeUtils] - 时间工具
   * @param {Object} [options.toast] - 提示工具
   * @return {Object} 渲染器实例
   */
  function createRenderer(options = {}) {
    const {
      container,
      templateSelector = '#session-detail-template',
      timeUtils = global.timeUtils,
      toast = global.toast,
    } = options;

    if (!container) {
      throw new Error('SessionDetailView: container 未传入或未找到');
    }
    const template = document.querySelector(templateSelector);
    if (!template) {
      throw new Error('SessionDetailView: 未找到模板节点');
    }

    /**
     * 渲染会话详情。
     *
     * @param {Object} session - 会话数据
     * @return {void}
     */
    function render(session) {
      const safeSession = normalizeSession(session);
      const fragment = template.content.cloneNode(true);
      const root = fragment.querySelector('[data-session-detail-root]');
      if (!root) {
        throw new Error('SessionDetailView: 模板缺少 data-session-detail-root');
      }

      fillHeader(root, safeSession);
      fillMeta(root, safeSession);
      fillStats(root, safeSession);
      fillTimeline(root, safeSession, timeUtils);
      fillInstances(root, safeSession, timeUtils);

      const stackText = buildStackText(safeSession);
      fillStack(root, stackText);

      container.innerHTML = '';
      container.appendChild(fragment);

      bindActions(container, {
        stackText,
        sessionId: safeSession.session_id || '',
        toast,
      });
    }

    return { render };
  }

  /**
   * 绑定交互动作。
   *
   * @param {HTMLElement} scope - 容器
   * @param {Object} payloads - 复制文本与通知
   * @return {void}
   */
  function bindActions(scope, payloads) {
    scope.querySelector('[data-action="copy-stack"]')?.addEventListener('click', () => {
      copyText(payloads.stackText || '无错误堆栈', '堆栈已复制', payloads.toast);
    });
    scope.querySelector('[data-action="copy-session-id"]')?.addEventListener('click', () => {
      copyText(payloads.sessionId || '', '会话 ID 已复制', payloads.toast);
    });
  }

  /**
   * 复制文本到剪贴板。
   *
   * @param {string} text - 文本
   * @param {string} successMessage - 成功提示
   * @param {Object} toast - 提示实例
   * @return {void}
   */
  function copyText(text, successMessage, toast) {
   if (!text) {
      notify('暂无可复制内容', 'warn', toast);
      return;
    }
    if (!navigator.clipboard?.writeText) {
      notify('浏览器不支持快捷复制，请手动选择文本', 'error', toast);
      return;
    }
    navigator.clipboard.writeText(String(text)).then(
      () => notify(successMessage, 'success', toast),
      (error) => {
        console.error('复制失败', error);
        notify('复制失败，请手动选择文本', 'error', toast);
      },
    );
  }

  /**
   * 根据 tone 输出提示。
   *
   * @param {string} message - 信息
   * @param {string} tone - tone
   * @param {Object} toast - 提示实例
   * @return {void}
   */
  function notify(message, tone, toast) {
    if (!message) {
      return;
    }
    if (toast) {
      if (tone === 'success' && toast.success) {
        toast.success(message);
        return;
      }
      if (tone === 'warn' && (toast.warning || toast.info)) {
        (toast.warning || toast.info).call(toast, message);
        return;
      }
      if (tone === 'error' && toast.error) {
        toast.error(message);
        return;
      }
    }
    if (tone === 'error') {
      console.error(message);
    } else {
      console.info(message);
    }
  }

  /**
   * 填充标题区。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} session - 会话数据
   * @param {Object} timeUtils - 时间工具
   * @return {void}
   */
  function fillHeader(root, session) {
    const titleEl = root.querySelector('[data-field="title"]');
    if (titleEl) {
      titleEl.textContent = session.session_id ? `会话 ${session.session_id}` : '会话详情';
    }
    const subtitleEl = root.querySelector('[data-field="subtitle"]');
    if (subtitleEl) {
      subtitleEl.textContent = `${getSyncTypeText(session.sync_type)} · ${getSyncCategoryText(session.sync_category)}`;
    }
    const statusEl = root.querySelector('[data-field="status-pill"]');
    if (statusEl) {
      const meta = getStatusMeta(session.status);
      statusEl.innerHTML = renderStatusPill(meta.text, meta.tone, meta.icon);
    }
  }

  /**
   * 渲染基础信息 chip 集。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} session - 数据
   * @return {void}
   */
  function fillMeta(root, session) {
    const container = root.querySelector('[data-field="meta-chips"]');
    if (!container) {
      return;
    }
    const chips = [
      renderMetaChip('触发时间', formatTime(session.started_at), { tone: 'muted', icon: 'fas fa-play' }),
      renderMetaChip('完成时间', formatTime(session.completed_at) || '未完成', { tone: 'muted', icon: 'fas fa-flag-checkered' }),
      renderMetaChip('发起人', describeActor(session.created_by), { tone: 'muted', icon: 'fas fa-user' }),
    ];
    container.innerHTML = chips.join('');
  }

  /**
   * 渲染统计与进度。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} session - 会话
   * @return {void}
   */
  function fillStats(root, session) {
    const statsContainer = root.querySelector('[data-field="stats"]');
    const progressContainer = root.querySelector('[data-field="progress"]');
    const stats = [
      { label: '总实例', value: Number(session.total_instances) || 0 },
      { label: '成功实例', value: Number(session.successful_instances) || 0 },
      { label: '失败/取消', value: Number(session.failed_instances) || 0 },
    ];
    if (statsContainer) {
      statsContainer.innerHTML = stats
        .map((item) => `
          <div class="session-detail-stat">
            <div class="session-detail-stat__label">${escapeHtml(item.label)}</div>
            <div class="session-detail-stat__value">${escapeHtml(String(item.value))}</div>
          </div>
        `)
        .join('');
    }

    if (!progressContainer) {
      return;
    }
    const progress = resolveProgress(session);
    progressContainer.innerHTML = `
      <div class="session-detail-progress__bar">
        <div class="session-detail-progress__bar-inner session-detail-progress__bar-inner--${progress.variant}" style="width:${progress.percent}%"></div>
      </div>
      <div class="d-flex align-items-center justify-content-between">
        ${renderStatusPill(`${progress.percent}%`, progress.variant, 'fas fa-tachometer-alt')}
        <small class="text-muted">${escapeHtml(progress.detail)}</small>
      </div>
    `;
  }

  /**
   * 渲染时间线。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} session - 数据
   * @param {Object} timeUtils - 时间工具
   * @return {void}
   */
  function fillTimeline(root, session, timeUtils) {
    const container = root.querySelector('[data-field="timeline"]');
    if (!container) {
      return;
    }
    const items = buildTimelineItems(session, timeUtils);
    container.innerHTML = items
      .map(
        (item) => `
        <li class="session-timeline-item" data-state="${item.state}">
          <div class="session-timeline-item__point"></div>
          <div class="session-timeline-item__body">
            <div class="session-timeline-item__title">
              ${renderStatusPill(item.title, item.tone, item.icon)}
              <span class="text-muted small">${escapeHtml(item.time || '-')}</span>
            </div>
            <p class="session-timeline-item__desc">${escapeHtml(item.desc || '')}</p>
          </div>
        </li>
      `,
      )
      .join('');
  }

  /**
   * 渲染实例列表。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} session - 数据
   * @param {Object} timeUtils - 时间工具
   * @return {void}
   */
  function fillInstances(root, session, timeUtils) {
    const container = root.querySelector('[data-field="instance-list"]');
    const summaryEl = root.querySelector('[data-field="instance-summary"]');
    const records = Array.isArray(session.instance_records) ? session.instance_records : [];
    if (summaryEl) {
      summaryEl.textContent = `${records.length} 个实例 · 成功 ${session.successful_instances || 0} · 失败 ${session.failed_instances || 0}`;
    }
    if (!container) {
      return;
    }
    if (!records.length) {
      container.innerHTML = '<div class="session-detail__empty">暂无实例记录</div>';
      return;
    }
    container.innerHTML = records.map((record) => renderInstanceRow(record, timeUtils)).join('');
  }

  /**
   * 渲染堆栈。
   *
   * @param {HTMLElement} root - 根节点
   * @param {string} stackText - 堆栈文本
   * @return {void}
   */
  function fillStack(root, stackText) {
    const section = root.querySelector('[data-section="stack"]');
    const block = root.querySelector('[data-field="stack-block"]');
    const copyBtn = root.querySelector('[data-action="copy-stack"]');
    if (!section || !block) {
      return;
    }
    if (!stackText) {
      block.textContent = '暂无错误堆栈';
      copyBtn?.setAttribute('disabled', 'disabled');
      copyBtn?.classList.add('disabled');
      return;
    }
    block.textContent = stackText;
    copyBtn?.removeAttribute('disabled');
    copyBtn?.classList.remove('disabled');
  }

  /**
   * 生成实例行。
   *
   * @param {Object} record - 实例
   * @param {Object} timeUtils - 时间工具
   * @return {string} HTML 片段
   */
  function renderInstanceRow(record, timeUtils) {
    const statusMeta = getInstanceStatusMeta(record.status);
    const chips = [];
    if (record.items_synced) {
      chips.push(renderLedgerChip(`${record.items_synced} 项`, 'muted', 'fas fa-database'));
    }
    const duration = formatDuration(record.started_at, record.completed_at, timeUtils);
    const durationDisplay = duration || '0 秒';
    const started = formatTime(record.started_at, timeUtils);
    const finished = formatTime(record.completed_at, timeUtils) || '未完成';
    const errorHtml = record.error_message
      ? `<div class="session-detail__instance-error">${escapeHtml(record.error_message)}</div>`
      : '';
    return `
      <div class="ledger-row session-instance-row">
        <div class="session-instance-col session-instance-col--name">
          <div class="session-instance-row__title">${escapeHtml(record.instance_name || `实例 #${record.instance_id || '-'}`)}</div>
        </div>
        <div class="session-instance-col session-instance-col--chips">
          <div class="session-instance-row__chips ledger-chip-stack">${chips.join('')}</div>
        </div>
        <div class="session-instance-col session-instance-col--status">
          ${renderStatusPill(statusMeta.text, statusMeta.tone, statusMeta.icon)}
        </div>
        <div class="session-instance-col session-instance-col--times">
          <div class="session-detail__instance-meta">
            <span>开始：${escapeHtml(started || '-')}</span>
            <span>结束：${escapeHtml(finished)}</span>
          </div>
        </div>
        <div class="session-instance-col session-instance-col--duration">
          <span class="session-instance-duration">
            <i class="fas fa-clock" aria-hidden="true"></i>
            ${escapeHtml(durationDisplay)}
          </span>
        </div>
        ${errorHtml}
      </div>
    `;
  }

  /**
   * 构造时间线条目。
   *
   * @param {Object} session - 会话
   * @param {Object} timeUtils - 时间工具
   * @return {Array<Object>} 条目
   */
  function buildTimelineItems(session, timeUtils) {
    const items = [];
    const createdTime = formatTime(session.created_at || session.started_at, timeUtils);
    const startedTime = formatTime(session.started_at, timeUtils);
    const completedTime = formatTime(session.completed_at, timeUtils);
    const progress = resolveProgress(session);
    const statusMeta = getStatusMeta(session.status);

    items.push({
      title: '创建会话',
      desc: `触发者：${describeActor(session.created_by)}`,
      time: createdTime || '-',
      tone: 'info',
      icon: 'fas fa-flag',
      state: createdTime ? 'done' : 'upcoming',
    });

    items.push({
      title: '开始执行',
      desc: `共 ${session.total_instances || 0} 个实例待同步`,
      time: startedTime || '-',
      tone: startedTime ? 'success' : 'muted',
      icon: 'fas fa-play',
      state: startedTime ? (session.status === 'running' ? 'active' : 'done') : 'upcoming',
    });

    items.push({
      title: session.status === 'failed' ? '异常终止' : '执行进度',
      desc: `已完成 ${session.successful_instances || 0} · 失败 ${session.failed_instances || 0}`,
      time: `${progress.percent}%`,
      tone: progress.variant,
      icon: 'fas fa-tachometer-alt',
      state: session.status === 'running' ? 'active' : session.status === 'pending' ? 'upcoming' : 'done',
    });

    items.push({
      title: statusMeta.text,
      desc: completedTime ? `总耗时 ${formatDuration(session.started_at, session.completed_at, timeUtils)}` : '等待完成',
      time: completedTime || '-',
      tone: statusMeta.tone,
      icon: statusMeta.icon,
      state: completedTime ? 'done' : 'upcoming',
    });
    return items;
  }

  /**
   * 计算进度。
   *
   * @param {Object} session - 会话
   * @return {Object} 进度信息
   */
  function resolveProgress(session) {
    const total = Number(session.total_instances) || 0;
    const completed = Number(session.successful_instances || 0) + Number(session.failed_instances || 0);
    const percent = total > 0 ? Math.round((completed / total) * 100) : Number(session.progress_percentage) || 0;
    const clamped = Math.max(0, Math.min(percent, 100));
    let variant = 'info';
    if (session.status === 'completed') {
      variant = 'success';
    } else if (session.status === 'failed') {
      variant = 'danger';
    } else if (session.status === 'pending') {
      variant = 'warning';
    }
    const detail = total > 0 ? `已处理 ${completed}/${total}` : '等待实例调度';
    return { percent: clamped, variant, detail };
  }

  /**
   * 元信息 chip 渲染。
   *
   * @param {string} label - 标签
   * @param {string} value - 值
   * @param {Object} options - 选项
   * @return {string} HTML
   */
  function renderMetaChip(label, value, options = {}) {
    const classes = ['chip-outline'];
    if (options.tone === 'brand') {
      classes.push('chip-outline--brand');
    } else if (options.tone === 'muted') {
      classes.push('chip-outline--muted');
    }
    const valueClasses = [options.monospace ? 'font-monospace' : '', 'fw-semibold'].filter(Boolean).join(' ');
    const iconHtml = options.icon ? `<i class="${options.icon}" aria-hidden="true"></i>` : '';
    const resolvedValue = value === undefined || value === null || value === '' ? '-' : value;
    return `
      <span class="${classes.join(' ')}">
        ${iconHtml}
        <strong>${escapeHtml(label)}：</strong>
        <span class="${valueClasses}">${escapeHtml(resolvedValue)}</span>
      </span>
    `;
  }

  /**
   * ledger chip 渲染。
   *
   * @param {string} text - 文本
   * @param {string} tone - 色调
   * @param {string} icon - 图标
   * @return {string} HTML
   */
  function renderLedgerChip(text, tone, icon) {
    if (!text) {
      return '';
    }
    const classes = ['ledger-chip'];
    if (tone === 'muted') {
      classes.push('ledger-chip--muted');
    }
    if (tone === 'accent') {
      classes.push('ledger-chip--accent');
    }
    const iconHtml = icon ? `<i class="${icon}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text)}</span>`;
  }

  /**
   * 渲染状态 pill。
   *
   * @param {string} text - 文案
   * @param {string} variant - tone
   * @param {string} icon - 图标
   * @return {string} HTML
   */
  function renderStatusPill(text, variant = 'muted', icon) {
    const classes = ['status-pill'];
    if (variant) {
      classes.push(`status-pill--${variant}`);
    }
    const iconHtml = icon ? `<i class="${icon}" aria-hidden="true"></i>` : '';
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '-')}</span>`;
  }

  /**
   * 归一化 session。
   *
   * @param {Object} session - 输入
   * @return {Object} 输出
   */
  function normalizeSession(session) {
    const fallback = session && typeof session === 'object' ? session : {};
    if (!Array.isArray(fallback.instance_records)) {
      fallback.instance_records = [];
    }
    return fallback;
  }

  /**
   * 状态映射。
   *
   * @param {string} status - 状态值
   * @return {Object} 属性
   */
  function getStatusMeta(status) {
    const resolver = global.UI?.Terms?.resolveRunStatusText;
    switch (status) {
      case 'running':
        return { text: typeof resolver === 'function' ? resolver('running') : '运行中', tone: 'info', icon: 'fas fa-sync-alt' };
      case 'pending':
        return { text: typeof resolver === 'function' ? resolver('pending') : '等待中', tone: 'warning', icon: 'fas fa-hourglass-half' };
      case 'completed':
        return { text: typeof resolver === 'function' ? resolver('completed') : '已完成', tone: 'success', icon: 'fas fa-check' };
      case 'failed':
        return { text: typeof resolver === 'function' ? resolver('failed') : '失败', tone: 'danger', icon: 'fas fa-times' };
      case 'cancelled':
        return { text: typeof resolver === 'function' ? resolver('cancelled') : '已取消', tone: 'muted', icon: 'fas fa-ban' };
      case 'paused':
        return { text: typeof resolver === 'function' ? resolver('paused') : '已暂停', tone: 'warning', icon: 'fas fa-pause' };
      default:
        return { text: status || '未知状态', tone: 'muted', icon: 'fas fa-info-circle' };
    }
  }

  /**
   * 实例状态映射。
   *
   * @param {string} status - 状态
   * @return {Object} 属性
   */
  function getInstanceStatusMeta(status) {
    const resolver = global.UI?.Terms?.resolveRunStatusText;
    switch (status) {
      case 'completed':
        return { text: '成功', tone: 'success', icon: 'fas fa-check-circle' };
      case 'running':
        return { text: typeof resolver === 'function' ? resolver('running') : '运行中', tone: 'info', icon: 'fas fa-sync' };
      case 'failed':
        return { text: typeof resolver === 'function' ? resolver('failed') : '失败', tone: 'danger', icon: 'fas fa-times-circle' };
      case 'pending':
        return { text: typeof resolver === 'function' ? resolver('pending') : '等待中', tone: 'warning', icon: 'fas fa-hourglass-start' };
      case 'cancelled':
        return { text: typeof resolver === 'function' ? resolver('cancelled') : '已取消', tone: 'muted', icon: 'fas fa-ban' };
      default:
        return { text: status || '未知', tone: 'muted', icon: 'fas fa-info-circle' };
    }
  }

  /**
   * 同步类型中文。
   *
   * @param {string} type - 类型
   * @return {string} 文案
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
   * 同步分类中文。
   *
   * @param {string} category - 分类
   * @return {string} 文案
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
      case 'other':
        return '其他';
      default:
        return category || '-';
    }
  }

  /**
   * 描述发起人。
   *
   * @param {number|string} createdBy - 用户 ID
   * @return {string} 描述
   */
  function describeActor(createdBy) {
    if (!createdBy && createdBy !== 0) {
      return '系统任务';
    }
    return `用户 #${createdBy}`;
  }

  /**
   * 时间格式化。
   *
   * @param {string|Date} value - 原始值
   * @param {Object} timeUtils - 工具
   * @return {string} 文本
   */
  function formatTime(value, timeUtils = global.timeUtils) {
    if (!value) {
      return '';
    }
    if (timeUtils?.formatTime) {
      return timeUtils.formatTime(value, 'datetime');
    }
    try {
      return new Date(value).toLocaleString();
    } catch (error) {
      return String(error || value);
    }
  }

  /**
   * 计算耗时。
   *
   * @param {string} startedAt - 开始
   * @param {string} completedAt - 结束
   * @param {Object} timeUtils - 工具
   * @return {string} 耗时
   */
  function formatDuration(startedAt, completedAt, timeUtils = global.timeUtils) {
    if (!startedAt || !completedAt) {
      return '-';
    }
    if (timeUtils?.parseTime) {
      const start = timeUtils.parseTime(startedAt);
      const end = timeUtils.parseTime(completedAt);
      if (start && end) {
        const seconds = Math.max(0, Math.round((end - start) / 1000));
        if (seconds >= 60) {
          const minutes = Math.floor(seconds / 60);
          const remain = seconds % 60;
          return `${minutes}分${remain}秒`;
        }
        return `${seconds}秒`;
      }
    }
    try {
      const diff = Math.abs(new Date(completedAt) - new Date(startedAt));
      const seconds = Math.round(diff / 1000);
      return `${seconds}秒`;
    } catch (error) {
      return error?.message || '-';
    }
  }

  /**
   * 将对象格式化为 JSON。
   *
   * @param {Object} data - 数据
   * @return {string} JSON 文本
   */
  function safeStringify(data) {
    try {
      return JSON.stringify(data, null, 2);
    } catch (error) {
      return String(error || data);
    }
  }

  /**
   * 构建堆栈文本。
   *
   * @param {Object} session - 会话
   * @return {string} 文本
   */
  function buildStackText(session) {
    const failed = (session.instance_records || []).filter((record) => Boolean(record?.error_message));
    return failed
      .map((record) => {
        const header = `[${record.instance_name || '实例'} #${record.instance_id || '-'}]`;
        const details = record.error_message || safeStringify(record.sync_details || {});
        return `${header}\n${details}`;
      })
      .join('\n\n');
  }

  /**
   * HTML 转义。
   *
   * @param {*} value - 输入
   * @return {string} 输出
   */
  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  global.SessionDetailView = {
    createRenderer,
  };
})(window, document);
