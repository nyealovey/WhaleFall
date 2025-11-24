(function (global, document) {
  'use strict';

  function createController(options = {}) {
    const {
      ui = global.UI,
      toast = global.toast,
      timeUtils = global.timeUtils,
      modalSelector = '#logDetailModal',
      contentSelector = '#logDetailContent',
      copyButtonSelector = '#copyLogDetailButton',
    } = options;

    if (!ui?.createModal) {
      throw new Error('LogsLogDetailModal: UI.createModal 未加载');
    }

    const modal = ui.createModal({
      modalSelector,
    });
    if (!modal) {
      throw new Error('LogsLogDetailModal: 无法创建日志详情模态');
    }

    const contentElement = document.querySelector(contentSelector);
    if (!contentElement) {
      throw new Error('LogsLogDetailModal: 未找到日志详情内容容器');
    }

    const copyButton = document.querySelector(copyButtonSelector);
    if (copyButton) {
      copyButton.addEventListener('click', handleCopyClick);
    }

    function open(log) {
      const safeLog = log && typeof log === 'object' ? log : {};
      renderLogDetail(safeLog);
      modal.open({ logId: safeLog.id });
    }

    function renderLogDetail(log) {
      const detailPayload = log.context || log.metadata || {};
      const detailTitle = log.context ? '上下文' : log.metadata ? '元数据' : '详情';
      const contextHtml = buildContextContent(detailPayload);
      const formattedTime = formatTimestamp(log.timestamp);
      const detailHtml = `
        <div class="mb-3">
            <strong>日志 ID：</strong>${escapeHtml(log.id) || '-'}
        </div>
        <div class="mb-3">
            <strong>级别：</strong>${escapeHtml(log.level) || '-'}
        </div>
        <div class="mb-3">
            <strong>模块：</strong>${escapeHtml(log.module) || '-'}
        </div>
        <div class="mb-3">
            <strong>时间：</strong>${formattedTime}
        </div>
        <div class="mb-3">
            <strong>消息：</strong>
            <pre class="bg-light p-3 rounded">${escapeHtml(log.message || '')}</pre>
        </div>
        ${
          log.traceback
            ? `<div class="mb-3">
                  <strong>堆栈：</strong>
                  <pre class="bg-dark text-light p-3 rounded overflow-auto">${escapeHtml(log.traceback)}</pre>
               </div>`
            : ''
        }
        <div class="mb-3">
            <strong>${detailTitle}：</strong>
            ${contextHtml}
        </div>
      `;
      contentElement.innerHTML = detailHtml;
    }

    function buildContextContent(payload) {
      if (payload === null || payload === undefined) {
        return '<div class="text-muted">暂无上下文数据</div>';
      }
      if (typeof payload === 'string') {
        return `<pre class="bg-light p-3 rounded">${escapeHtml(payload)}</pre>`;
      }
      if (typeof payload === 'object') {
        const entries = Object.entries(payload);
        if (!entries.length) {
          return '<div class="text-muted">暂无上下文数据</div>';
        }
        const rows = entries
          .map(([key, value]) => {
            const normalized = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
            return `
              <div class="mb-2">
                  <div class="text-muted small">${escapeHtml(key)}</div>
                  <pre class="bg-light p-3 rounded mb-0">${escapeHtml(String(normalized ?? ''))}</pre>
              </div>`;
          })
          .join('');
        return `<div class="log-context-section">${rows}</div>`;
      }
      return `<pre class="bg-light p-3 rounded">${escapeHtml(String(payload))}</pre>`;
    }

    function formatTimestamp(timestamp) {
      if (!timestamp) {
        return '-';
      }
      if (timeUtils?.formatTime) {
        return escapeHtml(timeUtils.formatTime(timestamp, 'datetime'));
      }
      try {
        return escapeHtml(new Date(timestamp).toLocaleString());
      } catch (error) {
        return escapeHtml(String(timestamp));
      }
    }

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

    async function handleCopyClick(event) {
      event?.preventDefault?.();
      const text = contentElement.innerText || contentElement.textContent || '';
      if (!text || !text.trim()) {
        toast?.info?.('暂无可复制的日志详情');
        return;
      }
      try {
        const success = await copyToClipboard(text);
        if (!success) {
          throw new Error('COPY_FALLBACK_FAILED');
        }
        toast?.success?.('日志详情已复制');
      } catch (error) {
        console.error('复制日志详情失败:', error);
        toast?.error?.('复制失败，请手动选择文本');
      }
    }

    async function copyToClipboard(text) {
      if (navigator.clipboard?.writeText && global.isSecureContext !== false) {
        await navigator.clipboard.writeText(text);
        return true;
      }
      if (copyUsingTextarea(text)) {
        return true;
      }
      if (copyUsingSelection(contentElement)) {
        return true;
      }
      return false;
    }

    function copyUsingTextarea(text) {
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.pointerEvents = 'none';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        return successful;
      } catch (error) {
        console.warn('copyUsingTextarea 失败:', error);
        return false;
      }
    }

    function copyUsingSelection(target) {
      if (!target) {
        return false;
      }
      try {
        const selection = window.getSelection();
        if (!selection) {
            return false;
        }
        selection.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(target);
        selection.addRange(range);
        const successful = document.execCommand('copy');
        selection.removeAllRanges();
        return successful;
      } catch (error) {
        console.warn('copyUsingSelection 失败:', error);
        return false;
      }
    }

    function destroy() {
      copyButton?.removeEventListener('click', handleCopyClick);
      modal.destroy?.();
      contentElement.innerHTML = '';
    }

    return {
      open,
      destroy,
    };
  }

  global.LogsLogDetailModal = {
    createController,
  };
})(window, document);
