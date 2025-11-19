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
      const failedRecords = records.filter((record) => record.status === 'failed' || record.status === 'error');
      const successRecords = records.filter((record) => record.status !== 'failed' && record.status !== 'error');
      const failedListHtml = failedRecords.map((record) => renderRecord(record, 'danger')).join('');
      const successListHtml = successRecords.map((record) => renderRecord(record, 'table')).join('');
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
        ${buildRecordSections(failedListHtml, successListHtml)}`;
    }

    function buildRecordSections(failedHtml, successHtml) {
      const failedSection = `
        <div class="session-detail-section mb-3">
          <h6 class="text-danger d-flex align-items-center">
            <i class="fas fa-exclamation-triangle me-2"></i>失败实例
          </h6>
          <div class="max-height-400 overflow-auto">
            ${failedHtml || '<div class="text-muted">暂无失败实例</div>'}
          </div>
        </div>`;
      const successSection = `
        <div class="session-detail-section">
          <h6 class="text-success d-flex align-items-center">
            <i class="fas fa-check-circle me-2"></i>成功实例
          </h6>
          <div class="table-responsive max-height-400 overflow-auto">
            ${successHtml
              ? `<table class="table table-sm mb-0">
                  <thead>
                    <tr>
                      <th>机器名</th>
                      <th>开始时间</th>
                      <th>完成时间</th>
                      <th>耗时</th>
                    </tr>
                  </thead>
                  <tbody>${successHtml}</tbody>
                </table>`
              : '<div class="text-muted">暂无成功实例</div>'}
          </div>
        </div>`;
      return `${failedSection}<hr>${successSection}`;
    }

    function renderRecord(record, highlightClass = '') {
      const duration = calculateDuration(record.started_at, record.completed_at);
      const startedAt = formatTime(record.started_at);
      const completedAt = record.completed_at ? formatTime(record.completed_at) : '-';
      if (highlightClass === 'danger') {
        return `
          <div class="session-record-danger mb-3">
            <div class="row g-3">
              <div class="col-md-3">
                <div class="fw-semibold mb-1">ID: ${escapeHtml(record.instance_id)}</div>
                <div class="text-muted">${escapeHtml(record.instance_name || '')}</div>
              </div>
              <div class="col-md-9">
                <div class="row text-muted record-meta-row align-items-center">
                  <div class="col-lg-3">
                    <div class="record-meta-label">开始</div>
                    <div class="record-meta-value">${startedAt}</div>
                  </div>
                  <div class="col-lg-3">
                    <div class="record-meta-label">完成</div>
                    <div class="record-meta-value">${completedAt}</div>
                  </div>
                  <div class="col-lg-2">
                    <div class="record-meta-label">耗时</div>
                    <div class="record-meta-value">${duration}</div>
                  </div>
                  <div class="col-lg-4">
                    <div class="record-meta-label text-danger">错误</div>
                    <div class="alert alert-danger mb-0 mt-1">
                      <pre class="mb-0" style="white-space: pre-wrap;">${escapeHtml(record.error_message || '')}</pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>`;
      }
      return `
        <tr>
          <td class="fw-semibold">ID: ${escapeHtml(record.instance_id)}<div class="text-muted small">${escapeHtml(record.instance_name || '')}</div></td>
          <td>${startedAt}</td>
          <td>${completedAt}</td>
          <td>${duration}</td>
        </tr>`;
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
