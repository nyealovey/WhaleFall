(function (global, document) {
  'use strict';

  /**
   * 创建日志详情渲染器。
   *
   * @param {Object} [options] - 选项
   * @param {HTMLElement} [options.container] - 容器元素
   * @param {string} [options.templateSelector] - 模板选择器
   * @param {Object} [options.timeUtils] - 时间工具
   * @param {Object} [options.toast] - 通知工具
   * @return {Object} 渲染器实例
   */
  function createRenderer(options = {}) {
    const {
      container,
      templateSelector = '#log-detail-template',
      timeUtils = global.timeUtils,
      toast = global.toast,
    } = options;

    if (!container) {
      throw new Error('LogDetailView: container 未提供');
    }
    const template = document.querySelector(templateSelector);
    if (!template) {
      throw new Error('LogDetailView: 未找到模板节点');
    }

    /**
     * 渲染日志详情。
     *
     * @param {Object} log - 日志数据
     * @return {void}
     */
    function render(log) {
      const safeLog = normalizeLog(log);
      const fragment = template.content.cloneNode(true);
      const root = fragment.querySelector('[data-log-detail-root]');
      if (!root) {
        throw new Error('LogDetailView: 模板缺少 data-log-detail-root');
      }

      fillHeader(root, safeLog, timeUtils);
      fillMessage(root, safeLog);
      const payloadText = fillPayload(root, safeLog);
      const stackText = fillStack(root, safeLog);

      container.innerHTML = '';
      container.appendChild(fragment);

      bindActions(container, {
        message: safeLog.message || '',
        payload: payloadText,
        stack: stackText,
        toast,
      });
    }

    return { render };
  }

  /**
   * 绑定交互按钮。
   *
   * @param {HTMLElement} scope - 容器
   * @param {Object} payloads - 可复制内容
   * @return {void}
   */
  function bindActions(scope, payloads) {
    scope.querySelector('[data-action="copy-message"]')?.addEventListener('click', () => {
      copyText(payloads.message, '日志消息已复制', payloads.toast);
    });
    scope.querySelector('[data-action="copy-payload"]')?.addEventListener('click', () => {
      copyText(payloads.payload, 'JSON 已复制', payloads.toast);
    });
    scope.querySelector('[data-action="toggle-payload"]')?.addEventListener('click', () => {
      const block = scope.querySelector('[data-field="payload-block"]');
      block?.classList.toggle('is-expanded');
    });
    scope.querySelector('[data-action="copy-stack"]')?.addEventListener('click', () => {
      copyText(payloads.stack, '堆栈已复制', payloads.toast);
    });
  }

  /**
   * 复制文本。
   *
   * @param {string} text - 文本
   * @param {string} successMessage - 成功提示
   * @param {Object} toast - 提示工具
   * @return {void}
   */
  function copyText(text, successMessage, toast) {
    const payload = text || '';
    if (!payload) {
      notify('暂无可复制内容', 'warn', toast);
      return;
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(payload).then(
        () => notify(successMessage, 'success', toast),
        () => fallbackCopy(payload, successMessage, toast),
      );
      return;
    }
    fallbackCopy(payload, successMessage, toast);
  }

  /**
   * 退化复制逻辑。
   *
   * @param {string} text - 文本
   * @param {string} successMessage - 成功提示
   * @param {Object} toast - 提示工具
   * @return {void}
   */
  function fallbackCopy(text, successMessage, toast) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      notify(successMessage, 'success', toast);
    } catch (error) {
      console.error('复制失败', error);
      notify('复制失败，请手动选择文本', 'error', toast);
    }
  }

  /**
   * 统一通知。
   *
   * @param {string} message - 文案
   * @param {string} tone - tone
   * @param {Object} toast - 提示
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
   * 填充头部。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} log - 日志数据
   * @param {Object} timeUtils - 时间工具
   * @return {void}
   */
  function fillHeader(root, log, timeUtils) {
    const levelEl = root.querySelector('[data-field="level-pill"]');
    const chipsEl = root.querySelector('[data-field="meta-chips"]');

    const levelMeta = getLevelMeta(log.level);
    if (levelEl) {
      levelEl.innerHTML = renderStatusPill(levelMeta.text, levelMeta.tone, levelMeta.icon);
    }
    if (chipsEl) {
      const chips = [];
      const timestampText = formatTime(log.timestamp, timeUtils) || '-';
      chips.push(renderMetaChip('时间', timestampText, 'fas fa-clock'));
      chips.push(renderMetaChip('日志 ID', log.id, 'fas fa-hashtag'));
      if (log.module) {
        chips.push(renderMetaChip('模块', log.module, 'fas fa-layer-group'));
      }
      if (log.request_id) {
        chips.push(renderMetaChip('请求 ID', log.request_id, 'fas fa-barcode'));
      }
      if (log.user_id) {
        chips.push(renderMetaChip('用户', `#${log.user_id}`, 'fas fa-user')); 
      }
      chipsEl.innerHTML = chips.filter(Boolean).join('');
    }
  }

  /**
   * 渲染消息。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} log - 数据
   * @return {void}
   */
  function fillMessage(root, log) {
    const block = root.querySelector('[data-field="message-block"]');
    if (block) {
      block.textContent = log.message || '无日志消息';
    }
  }

  /**
   * 渲染 JSON。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} log - 数据
   * @return {string} JSON 文本
   */
  function fillPayload(root, log) {
    const payloadBlock = root.querySelector('[data-field="payload-block"]');
    const payloadBody = root.querySelector('[data-panel-body="payload"]');
    const payloadText = formatPayload(extractPayload(log));
    if (payloadBlock) {
      payloadBlock.textContent = payloadText || '';
    }
    if (payloadBody) {
      payloadBody.classList.toggle('log-detail__body--empty', !payloadText);
    }
    return payloadText;
  }

  /**
   * 渲染堆栈。
   *
   * @param {HTMLElement} root - 根节点
   * @param {Object} log - 数据
   * @return {string} 堆栈文本
   */
  function fillStack(root, log) {
    const stackBlock = root.querySelector('[data-field="stack-block"]');
    const stackBody = root.querySelector('[data-panel-body="stack"]');
    const stackText = log.traceback || '';
    if (stackBlock) {
      stackBlock.textContent = stackText;
    }
    if (stackBody) {
      stackBody.classList.toggle('log-detail__body--empty', !stackText);
    }
    return stackText;
  }

  /**
   * 生成状态 pill。
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
    return `<span class="${classes.join(' ')}">${iconHtml}${escapeHtml(text || '-') }</span>`;
  }

  /**
   * 渲染 meta chip。
   *
   * @param {string} label - 标签
   * @param {string|number} value - 值
   * @param {string} icon - 图标
   * @return {string} HTML
   */
  function renderMetaChip(label, value, icon) {
    if (value === undefined || value === null || value === '') {
      return '';
    }
    const iconHtml = icon ? `<i class="${icon}" aria-hidden="true"></i>` : '';
    return `
      <span class="chip-outline chip-outline--muted">
        ${iconHtml}
        <strong>${escapeHtml(label)}：</strong>
        <span class="fw-semibold">${escapeHtml(String(value))}</span>
      </span>
    `;
  }

  /**
   * 归一化日志对象。
   *
   * @param {Object} log - 输入
   * @return {Object} 对象
   */
  function normalizeLog(log) {
    if (!log || typeof log !== 'object') {
      return {};
    }
    return log;
  }

  /**
   * 获取级别元数据。
   *
   * @param {string} level - 日志级别
   * @return {Object} 元数据
   */
  function getLevelMeta(level) {
    const normalized = (level || 'info').toUpperCase();
    switch (normalized) {
      case 'DEBUG':
        return { text: 'DEBUG', tone: 'muted', icon: 'fas fa-bug' };
      case 'INFO':
        return { text: 'INFO', tone: 'info', icon: 'fas fa-info-circle' };
      case 'WARNING':
        return { text: 'WARNING', tone: 'warning', icon: 'fas fa-exclamation-triangle' };
      case 'ERROR':
        return { text: 'ERROR', tone: 'danger', icon: 'fas fa-times-circle' };
      case 'CRITICAL':
        return { text: 'CRITICAL', tone: 'danger', icon: 'fas fa-fire-alt' };
      default:
        return { text: normalized, tone: 'info', icon: 'fas fa-info-circle' };
    }
  }

  /**
   * 提取 payload。
   *
   * @param {Object} log - 日志
   * @return {Object|string|null} payload
   */
  function extractPayload(log) {
    if (log.context && Object.keys(log.context).length) {
      return log.context;
    }
    if (log.metadata && Object.keys(log.metadata).length) {
      return log.metadata;
    }
    if (log.payload) {
      return log.payload;
    }
    return null;
  }

  /**
   * JSON 格式化。
   *
   * @param {Object|string|null} payload - 数据
   * @return {string} 文本
   */
  function formatPayload(payload) {
    if (payload === null || payload === undefined) {
      return '';
    }
    if (typeof payload === 'string') {
      return payload;
    }
    try {
      return JSON.stringify(payload, null, 2);
  } catch (error) {
    return String(payload ?? error);
  }
  }

  /**
   * 时间格式化。
   *
   * @param {string|Date} value - 时间
   * @param {Object} timeUtils - 工具
   * @return {string} 字符串
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
   * HTML 转义。
   *
   * @param {*} value - 输入
   * @return {string} 结果
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

  global.LogDetailView = {
    createRenderer,
  };
})(window, document);
