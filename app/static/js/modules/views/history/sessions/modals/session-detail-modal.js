(function (global, document) {
  'use strict';

  function createController(options = {}) {
    const {
      ui = global.UI,
      timeUtils = global.timeUtils,
      modalSelector = '#sessionDetailModal',
      contentSelector = '#session-detail-content',
      getStatusColor = () => 'secondary',
      getStatusText = (status) => status,
      getSyncTypeText = (type) => type,
      getSyncCategoryText = (category) => category,
    } = options;

    if (!ui?.createModal) {
      throw new Error('SyncSessionDetailModal: UI.createModal 未加载');
    }

    const contentElement = document.querySelector(contentSelector);
    if (!contentElement) {
      throw new Error('SyncSessionDetailModal: 未找到内容容器');
    }

    const modal = ui.createModal({
      modalSelector,
      onClose: clearContent,
    });

    function open(session) {
      renderContent(session);
      modal.open();
    }

    function renderContent(session) {
      const safeSession = session && typeof session === 'object' ? session : {};
      const records = Array.isArray(safeSession.instance_records) ? safeSession.instance_records : [];
      const recordsHtml = records.map(renderRecord).join('');
      contentElement.innerHTML = `
        <div class="row mb-3">
          <div class="col-6"><strong>会话ID:</strong> ${escapeHtml(safeSession.session_id || '未知')}</div>
          <div class="col-6"><strong>状态:</strong> <span class="badge bg-${getStatusColor(safeSession.status)}">${escapeHtml(getStatusText(safeSession.status))}</span></div>
        </div>
        <div class="row mb-3">
          <div class="col-6"><strong>操作方式:</strong> ${escapeHtml(getSyncTypeText(safeSession.sync_type))}</div>
          <div class="col-6"><strong>同步分类:</strong> ${escapeHtml(getSyncCategoryText(safeSession.sync_category))}</div>
        </div>
        <div class="row mb-3">
          <div class="col-6"><strong>开始时间:</strong> ${formatTime(safeSession.started_at)}</div>
          <div class="col-6"><strong>完成时间:</strong> ${safeSession.completed_at ? formatTime(safeSession.completed_at) : '未完成'}</div>
        </div>
        <div class="row mb-3">
          <div class="col-4"><strong>总实例数:</strong> ${safeSession.total_instances ?? 0}</div>
          <div class="col-4"><strong>成功:</strong> ${safeSession.successful_instances ?? 0}</div>
          <div class="col-4"><strong>失败:</strong> ${safeSession.failed_instances ?? 0}</div>
        </div>
        <hr>
        <h6>实例记录</h6>
        <div class="max-height-400 overflow-auto">${recordsHtml || '<div class="text-muted">暂无实例记录</div>'}</div>`;
    }

    function renderRecord(record) {
      const statusText = getStatusText(record.status);
      const duration = calculateDuration(record.started_at, record.completed_at);
      const startedAt = formatTime(record.started_at);
      const completedAt = record.completed_at ? formatTime(record.completed_at) : '-';
      return `
        <div class="card mb-2">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-3">
                <h6 class="mb-1"><strong>ID: ${escapeHtml(record.instance_id)}</strong> &nbsp;&nbsp; ${escapeHtml(record.instance_name || '')}</h6>
              </div>
              <div class="col-2">
                <span class="badge status-badge bg-${getStatusColor(record.status)}">${escapeHtml(statusText)}</span>
              </div>
              <div class="col-7">
                <small class="text-muted">
                  开始: ${startedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 完成: ${completedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 耗时: ${duration}
                  ${record.error_message ? ` &nbsp;&nbsp; | &nbsp;&nbsp; 错误: ${escapeHtml(record.error_message)}` : ''}
                </small>
              </div>
            </div>
          </div>
        </div>`;
    }

    function formatTime(value) {
      if (!value) {
        return '-';
      }
      if (timeUtils?.formatTime) {
        return timeUtils.formatTime(value, 'datetime');
      }
      try {
        return new Date(value).toLocaleString();
      } catch (error) {
        return String(value);
      }
    }

    function calculateDuration(startedAt, completedAt) {
      if (!startedAt || !completedAt || !timeUtils?.parseTime) {
        return '-';
      }
      const startTime = timeUtils.parseTime(startedAt);
      const endTime = timeUtils.parseTime(completedAt);
      if (!startTime || !endTime) {
        return '-';
      }
      const seconds = Math.round((endTime - startTime) / 1000);
      return `${seconds}秒`;
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

    function clearContent() {
      contentElement.innerHTML = '';
    }

    function destroy() {
      modal.destroy?.();
      clearContent();
    }

    return {
      open,
      destroy,
    };
  }

  global.SyncSessionDetailModal = {
    createController,
  };
})(window, document);
