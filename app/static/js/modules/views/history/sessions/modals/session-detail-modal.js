(function (global, document) {
  'use strict';

  /**
   * 创建同步会话详情模态框控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.ui] - UI 工具对象
   * @param {Object} [options.timeUtils] - 时间工具对象
   * @param {string} [options.modalSelector] - 模态框选择器
   * @param {string} [options.contentSelector] - 内容容器选择器
   * @param {Function} [options.getStatusColor] - 获取状态颜色的函数
   * @param {Function} [options.getStatusText] - 获取状态文本的函数
   * @param {Function} [options.getSyncTypeText] - 获取同步类型文本的函数
   * @param {Function} [options.getSyncCategoryText] - 获取同步分类文本的函数
   * @return {Object} 控制器对象，包含 open 和 destroy 方法
   * @throws {Error} 当 UI.createModal 未加载或内容容器未找到时抛出
   */
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

    /**
     * 打开会话详情模态框。
     *
     * @param {Object} session - 会话对象
     * @param {string} [session.session_id] - 会话 ID
     * @param {string} [session.status] - 会话状态
     * @param {string} [session.sync_type] - 同步类型
     * @param {string} [session.sync_category] - 同步分类
     * @param {string} [session.started_at] - 开始时间
     * @param {string} [session.completed_at] - 完成时间
     * @param {number} [session.total_instances] - 总实例数
     * @param {number} [session.successful_instances] - 成功实例数
     * @param {number} [session.failed_instances] - 失败实例数
     * @param {Array<Object>} [session.instance_records] - 实例记录数组
     * @return {void}
     */
    function open(session) {
      renderContent(session);
      modal.open();
    }

    /**
     * 渲染会话详情内容。
     *
     * @param {Object} session - 会话对象
     * @return {void}
     */
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

    /**
     * 构建记录区域 HTML。
     *
     * @param {string} failedHtml - 失败记录 HTML
     * @param {string} successHtml - 成功记录 HTML
     * @return {string} 完整的记录区域 HTML
     */
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

    /**
     * 渲染单条实例记录。
     *
     * @param {Object} record - 实例记录对象
     * @param {number|string} record.instance_id - 实例 ID
     * @param {string} [record.instance_name] - 实例名称
     * @param {string} [record.started_at] - 开始时间
     * @param {string} [record.completed_at] - 完成时间
     * @param {string} [record.error_message] - 错误消息
     * @param {string} [highlightClass] - 高亮样式类
     * @return {string} 记录 HTML
     */
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

    /**
     * 格式化时间。
     *
     * @param {string|Date} value - 时间值
     * @return {string} 格式化后的时间字符串
     */
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

    /**
     * 计算持续时间。
     *
     * @param {string|Date} startedAt - 开始时间
     * @param {string|Date} completedAt - 完成时间
     * @return {string} 持续时间字符串
     */
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

    /**
     * 转义 HTML 特殊字符。
     *
     * @param {*} value - 要转义的值
     * @return {string} 转义后的字符串
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

    /**
     * 清空内容。
     *
     * @return {void}
     */
    function clearContent() {
      contentElement.innerHTML = '';
    }

    /**
     * 销毁控制器，清理资源。
     *
     * @return {void}
     */
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
