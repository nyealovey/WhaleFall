// 同步会话管理页脚本（从模板抽离）
// 依赖：bootstrap, alert-utils.js, time-utils.js

(function() {
  // 防抖/节流等工具可后续抽到 shared/utils

  let currentSessions = [];
  let currentFilters = {};

  document.addEventListener('DOMContentLoaded', function() {
    loadSessions();
    setInterval(loadSessions, 30000);

    // 绑定筛选按钮（如果存在）
    const applyBtn = document.querySelector('#status-filter')?.closest('.row')?.querySelector('button.btn-outline-primary');
    if (applyBtn) {
      applyBtn.addEventListener('click', applyFilters);
    }
  });

  window.loadSessions = function() {
    const params = new URLSearchParams();
    if (currentFilters.sync_type) params.append('sync_type', currentFilters.sync_type);
    if (currentFilters.sync_category) params.append('sync_category', currentFilters.sync_category);
    if (currentFilters.status) params.append('status', currentFilters.status);

    fetch(`/sync_sessions/api/sessions?${params.toString()}`)
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          currentSessions = data.data;
          renderSessions(data.data);
          const loading = document.getElementById('sessions-loading');
          const container = document.getElementById('sessions-container');
          if (loading) loading.style.display = 'none';
          if (container) container.style.display = 'block';
        } else {
          showAlert('加载会话列表失败: ' + data.message, 'error');
        }
      })
      .catch(err => {
        console.error('加载会话列表出错:', err);
        showAlert('加载会话列表出错', 'error');
      });
  }

  window.renderSessions = function(sessions) {
    const container = document.getElementById('sessions-container');
    if (!container) return;

    if (!sessions || sessions.length === 0) {
      container.innerHTML = '<div class="text-center py-4 text-muted">暂无同步会话</div>';
      return;
    }

    const html = sessions.map(session => {
      const statusClass = getStatusClass(session.status);
      const statusText = getStatusText(session.status);
      const startedAt = formatTime(session.started_at, 'datetime');
      const completedAt = session.completed_at ? formatTime(session.completed_at, 'datetime') : '-';

      const totalInstances = session.total_instances || 0;
      const successfulInstances = session.successful_instances || 0;
      const failedInstances = session.failed_instances || 0;
      const successRate = totalInstances > 0 ? Math.round((successfulInstances / totalInstances) * 100) : 0;
      const progressInfo = getProgressInfo(successRate, totalInstances, successfulInstances, failedInstances);

      return `
        <div class="card session-card ${statusClass} mb-3">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-md-2">
                <h6 class="mb-1">${session.session_id.substring(0, 8)}...</h6>
                <small class="text-muted">${getSyncTypeText(session.sync_type)} - ${getSyncCategoryText(session.sync_category)}</small>
              </div>
              <div class="col-md-2">
                <span class="badge status-badge bg-${getStatusColor(session.status)}">${statusText}</span>
              </div>
              <div class="col-md-3">
                <div class="progress" style="height: 12px;">
                  <div class="progress-bar ${progressInfo.barClass}" role="progressbar" style="width: ${successRate}%" title="${progressInfo.tooltip}"></div>
                </div>
                <small class="text-muted">
                  <span class="${progressInfo.textClass}">
                    <i class="${progressInfo.icon}"></i> ${successRate}% (${successfulInstances}/${totalInstances})
                  </span>
                </small>
              </div>
              <div class="col-md-2">
                <small class="text-muted">
                  <i class="fas fa-clock"></i> ${startedAt}<br>
                  <i class="fas fa-check-circle"></i> ${completedAt}
                </small>
              </div>
              <div class="col-md-1">
                ${getDurationBadge(session.started_at, session.completed_at)}
              </div>
              <div class="col-md-2 text-end">
                <button class="btn btn-sm btn-outline-primary" data-action="view" data-id="${session.session_id}">
                  <i class="fas fa-eye"></i> 详情
                </button>
                ${failedInstances > 0 ? `
                <button class="btn btn-sm btn-outline-warning" data-action="error" data-id="${session.session_id}" title="查看错误">
                  <i class="fas fa-exclamation-triangle"></i> 错误
                </button>` : ''}
                ${session.status === 'running' ? `
                <button class="btn btn-sm btn-outline-danger" data-action="cancel" data-id="${session.session_id}">
                  <i class="fas fa-stop"></i> 取消
                </button>` : ''}
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    container.innerHTML = html;

    container.querySelectorAll('[data-action="view"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      viewSessionDetail(id);
    }));
    container.querySelectorAll('[data-action="error"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      viewErrorLogs(id);
    }));
    container.querySelectorAll('[data-action="cancel"]').forEach(btn => btn.addEventListener('click', e => {
      const id = e.currentTarget.getAttribute('data-id');
      cancelSession(id);
    }));
  }

  window.viewSessionDetail = function(sessionId) {
    fetch(`/sync_sessions/api/sessions/${sessionId}`)
      .then(r => r.json())
      .then(data => data.success ? showSessionDetail(data.data) : showAlert('加载会话详情失败: ' + data.message, 'error'))
      .catch(err => { console.error('加载会话详情出错:', err); showAlert('加载会话详情出错', 'error'); });
  }

  window.viewErrorLogs = function(sessionId) {
    fetch(`/sync_sessions/api/sessions/${sessionId}/error-logs`)
      .then(r => r.json())
      .then(data => data.success ? showErrorLogs(data.data) : showAlert('加载错误信息失败: ' + data.message, 'error'))
      .catch(err => { console.error('加载错误信息出错:', err); showAlert('加载错误信息出错', 'error'); });
  }

  window.showErrorLogs = function(data) {
    const content = document.getElementById('error-logs-content');
    if (!content) return;
    const errorRecords = data.error_records || [];

    if (errorRecords.length === 0) {
      content.innerHTML = '<div class="text-center py-4 text-muted">没有发现错误记录</div>';
    } else {
      const recordsHtml = errorRecords.map(record => `
        <div class="card mb-3 border-danger">
          <div class="card-header bg-danger text-white">
            <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>${record.instance_name} (ID: ${record.instance_id})</h6>
          </div>
          <div class="card-body">
            ${record.error_message ? `
            <div class="alert alert-danger mb-0">
              <h6 class="alert-heading"><i class="fas fa-bug me-2"></i>错误信息</h6>
              <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${record.error_message}</pre>
            </div>` : '<div class="text-muted">没有具体错误信息</div>'}
          </div>
        </div>`).join('');
      content.innerHTML = recordsHtml;
    }

    const modal = new bootstrap.Modal(document.getElementById('errorLogsModal'));
    modal.show();
  }

  window.showSessionDetail = function(session) {
    const content = document.getElementById('session-detail-content');
    if (!content) return;
    const records = session.instance_records || [];

    const recordsHtml = records.map(record => {
      const statusClass = getStatusClass(record.status);
      const statusText = getStatusText(record.status);
      const duration = record.started_at && record.completed_at ? Math.round((new Date(record.completed_at) - new Date(record.started_at)) / 1000) + '秒' : '-';
      const startedAt = formatTime(record.started_at, 'datetime');
      const completedAt = record.completed_at ? formatTime(record.completed_at, 'datetime') : '-';

      return `
        <div class="card mb-2">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-md-3">
                <h6 class="mb-1"><strong>ID: ${record.instance_id}</strong> &nbsp;&nbsp; ${record.instance_name}</h6>
              </div>
              <div class="col-md-2">
                <span class="badge status-badge bg-${getStatusColor(record.status)}">${statusText}</span>
              </div>
              <div class="col-md-7">
                <small class="text-muted">
                  开始: ${startedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 完成: ${completedAt} &nbsp;&nbsp; | &nbsp;&nbsp; 耗时: ${duration}
                  ${record.error_message ? ` &nbsp;&nbsp; | &nbsp;&nbsp; 错误: ${record.error_message}` : ''}
                </small>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    content.innerHTML = `
      <div class="row mb-3">
        <div class="col-md-6"><strong>会话ID:</strong> ${session.session_id}</div>
        <div class="col-md-6"><strong>状态:</strong> <span class="badge bg-${getStatusColor(session.status)}">${getStatusText(session.status)}</span></div>
      </div>
      <div class="row mb-3">
        <div class="col-md-6"><strong>同步类型:</strong> ${getSyncTypeText(session.sync_type)}</div>
        <div class="col-md-6"><strong>同步分类:</strong> ${getSyncCategoryText(session.sync_category)}</div>
      </div>
      <div class="row mb-3">
        <div class="col-md-6"><strong>开始时间:</strong> ${formatTime(session.started_at, 'datetime')}</div>
        <div class="col-md-6"><strong>完成时间:</strong> ${session.completed_at ? formatTime(session.completed_at, 'datetime') : '未完成'}</div>
      </div>
      <div class="row mb-3">
        <div class="col-md-4"><strong>总实例数:</strong> ${session.total_instances}</div>
        <div class="col-md-4"><strong>成功:</strong> ${session.successful_instances}</div>
        <div class="col-md-4"><strong>失败:</strong> ${session.failed_instances}</div>
      </div>
      <hr>
      <h6>实例记录</h6>
      <div class="max-height-400 overflow-auto">${recordsHtml || '<div class="text-muted">暂无实例记录</div>'}</div>`;

    const modal = new bootstrap.Modal(document.getElementById('sessionDetailModal'));
    modal.show();
  }

  window.cancelSession = function(sessionId) {
    if (confirm('确定要取消这个同步会话吗？')) {
      fetch(`/sync_sessions/api/sessions/${sessionId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() }
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) { showAlert('会话已取消', 'success'); loadSessions(); }
        else { showAlert('取消会话失败: ' + data.message, 'error'); }
      })
      .catch(err => { console.error('取消会话出错:', err); showAlert('取消会话出错', 'error'); });
    }
  }

  window.applyFilters = function() {
    currentFilters = {
      sync_type: document.getElementById('sync-type-filter')?.value || '',
      sync_category: document.getElementById('sync-category-filter')?.value || '',
      status: document.getElementById('status-filter')?.value || ''
    };
    loadSessions();
  }

  window.refreshData = function() { loadSessions(); }

  window.getProgressInfo = function(successRate, totalInstances, successfulInstances, failedInstances) {
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

  window.getStatusClass = function(status) {
    const map = { running: 'running', completed: 'completed', failed: 'failed', cancelled: 'cancelled' };
    return map[status] || '';
  }
  window.getStatusText = function(status) { return status; }
  window.getStatusColor = function(status) {
    const map = { running: 'success', completed: 'info', failed: 'danger', cancelled: 'secondary', pending: 'warning' };
    return map[status] || 'secondary';
  }
  window.getSyncTypeText = function(type) { return type; }
  window.getSyncCategoryText = function(category) { return category; }

  window.getDurationBadge = function(startedAt, completedAt) {
    if (!startedAt || !completedAt) return '<span class="text-muted">-</span>';
    const s = new Date(startedAt), e = new Date(completedAt);
    const sec = (e - s) / 1000;
    if (sec < 60) return `<span class="badge bg-info">${sec.toFixed(1)}秒</span>`;
    if (sec < 3600) return `<span class="badge bg-info">${(sec/60).toFixed(1)}分钟</span>`;
    return `<span class="badge bg-info">${(sec/3600).toFixed(1)}小时</span>`;
  }
})();