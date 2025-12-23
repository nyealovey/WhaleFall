(function (global) {
  'use strict';

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error('DOMHelpers 未初始化，无法注册危险确认组件');
    return;
  }

  const ui = global.UI;
  if (!ui?.createModal) {
    console.error('UI.createModal 未初始化，无法注册危险确认组件');
    return;
  }

  const MODAL_SELECTOR = '#dangerConfirmModal';
  let controller = null;
  let activeRequest = null;
  let requestCounter = 0;

  function safeParseJson(raw) {
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function getRequestId(payload) {
    const parsed = typeof payload === 'string' ? safeParseJson(payload) : payload;
    return parsed?.request_id || parsed?.requestId || null;
  }

  function normalizeButtonClass(value, fallback = 'btn-danger') {
    const allowed = new Set([
      'btn-danger',
      'btn-outline-danger',
      'btn-warning',
      'btn-primary',
      'btn-outline-secondary',
    ]);
    if (!value) {
      return fallback;
    }
    const trimmed = String(value).trim();
    return allowed.has(trimmed) ? trimmed : fallback;
  }

  function ensureController() {
    if (controller) {
      return controller;
    }

    controller = ui.createModal({
      modalSelector: MODAL_SELECTOR,
      onOpen: () => {
        const cancelButton = document.querySelector(`${MODAL_SELECTOR} [data-modal-cancel]`);
        cancelButton?.focus?.();
      },
      onConfirm: ({ modal, payload }) => {
        const requestId = getRequestId(payload);
        if (!activeRequest || activeRequest.requestId !== requestId) {
          modal?.close?.();
          return;
        }
        const resolve = activeRequest.resolve;
        activeRequest = null;
        resolve(true);
        modal?.close?.();
      },
      onCancel: ({ payload }) => {
        const requestId = getRequestId(payload);
        if (!activeRequest || activeRequest.requestId !== requestId) {
          return;
        }
        const resolve = activeRequest.resolve;
        activeRequest = null;
        resolve(false);
      },
      onClose: ({ payload }) => {
        const requestId = getRequestId(payload);
        if (!activeRequest || activeRequest.requestId !== requestId) {
          return;
        }
        const resolve = activeRequest.resolve;
        activeRequest = null;
        resolve(false);
      },
    });

    return controller;
  }

  function applyOptions(options, modalElement) {
    const modal = modalElement || document.querySelector(MODAL_SELECTOR);
    if (!modal) {
      console.error('危险确认模态未找到', MODAL_SELECTOR);
      return;
    }

    const titleEl = modal.querySelector('#dangerConfirmModalLabel');
    const messageEl = modal.querySelector('[data-danger-confirm-message]');
    const detailsEl = modal.querySelector('[data-danger-confirm-details]');
    const resultWrapper = modal.querySelector('[data-danger-confirm-result]');
    const resultLink = modal.querySelector('[data-danger-confirm-result-link]');
    const confirmButton = modal.querySelector('[data-modal-confirm]');
    const cancelButton = modal.querySelector('[data-modal-cancel]');

    const title = options?.title || '确认操作';
    const message = options?.message || '请确认是否继续。';
    const details = Array.isArray(options?.details) ? options.details : [];
    const confirmText = options?.confirmText || '确认';
    const cancelText = options?.cancelText || '取消';
    const resultUrl = options?.resultUrl || '';
    const resultText = options?.resultText || '前往会话中心查看结果';
    const confirmButtonClass = normalizeButtonClass(options?.confirmButtonClass);

    if (titleEl) {
      titleEl.textContent = title;
    }
    if (messageEl) {
      messageEl.textContent = message;
    }

    if (detailsEl) {
      detailsEl.innerHTML = '';
      if (!details.length) {
        detailsEl.style.display = 'none';
      } else {
        detailsEl.style.display = '';
        details.forEach((item) => {
          const row = document.createElement('li');
          const label = document.createElement('span');
          const value = document.createElement('span');

          label.textContent = item?.label ? `${item.label}：` : '';
          value.textContent = item?.value ?? '';
          value.className = item?.tone ? `fw-semibold text-${item.tone}` : 'fw-semibold';

          row.appendChild(label);
          row.appendChild(value);
          detailsEl.appendChild(row);
        });
      }
    }

    if (resultWrapper && resultLink) {
      if (resultUrl) {
        resultWrapper.style.display = '';
        resultLink.setAttribute('href', resultUrl);
        resultLink.textContent = resultText;
      } else {
        resultWrapper.style.display = 'none';
        resultLink.setAttribute('href', '#');
        resultLink.textContent = resultText;
      }
    }

    if (confirmButton) {
      confirmButton.classList.remove('btn-danger', 'btn-outline-danger', 'btn-warning', 'btn-primary', 'btn-outline-secondary');
      confirmButton.classList.add(confirmButtonClass);
      confirmButton.textContent = confirmText;
    }

    if (cancelButton) {
      cancelButton.textContent = cancelText;
    }
  }

  /**
   * 统一危险操作确认模态（替代浏览器 confirm）。
   *
   * @param {Object} options 配置项。
   * @param {string} [options.title] 标题。
   * @param {string} [options.message] 主文案。
   * @param {Array<Object>} [options.details] 影响范围/提示列表：{ label, value, tone }。
   * @param {string} [options.confirmText] 确认按钮文案。
   * @param {string} [options.cancelText] 取消按钮文案。
   * @param {string} [options.confirmButtonClass] 确认按钮样式类。
   * @param {string} [options.resultUrl] 结果入口链接。
   * @param {string} [options.resultText] 结果入口文案。
   * @returns {Promise<boolean>} 用户确认返回 true，否则 false。
   */
  function confirmDanger(options = {}) {
    const modalElement = document.querySelector(MODAL_SELECTOR);
    if (!modalElement) {
      console.error('危险确认模态未找到', MODAL_SELECTOR);
      return Promise.resolve(false);
    }

    const modal = ensureController();
    if (!modal) {
      return Promise.resolve(false);
    }

    if (activeRequest?.resolve) {
      activeRequest.resolve(false);
    }

    requestCounter += 1;
    const requestId = `${Date.now()}_${requestCounter}`;
    applyOptions(options, modalElement);

    return new Promise((resolve) => {
      activeRequest = { requestId, resolve };
      modal.open({ request_id: requestId });
    });
  }

  global.UI = global.UI || {};
  global.UI.confirmDanger = confirmDanger;
})(window);

