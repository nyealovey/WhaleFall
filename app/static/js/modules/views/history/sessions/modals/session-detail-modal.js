(function (global, document) {
  'use strict';

  /**
   * 创建任务运行详情模态控制器。
   *
   * @param {Object} [options] - 配置
   * @param {Object} [options.ui] - UI 工具
   * @param {Object} [options.timeUtils] - 时间工具
   * @param {string} [options.modalSelector] - 模态选择器
   * @param {string} [options.contentSelector] - 内容容器选择器
   * @param {string} [options.templateSelector] - 模板选择器
   * @return {Object} 控制器
   */
  function createController(options = {}) {
    const {
      ui = global.UI,
      timeUtils = global.timeUtils,
      modalSelector = '#sessionDetailModal',
      contentSelector = '#session-detail-content',
      templateSelector = '#session-detail-template',
    } = options;

    if (!ui?.createModal) {
      throw new Error('TaskRunDetailModal: UI.createModal 未加载');
    }

    const contentElement = document.querySelector(contentSelector);
    if (!contentElement) {
      throw new Error('TaskRunDetailModal: 未找到内容容器');
    }

    const modal = ui.createModal({
      modalSelector,
      onClose: clearContent,
    });

    clearContent();

    let renderer = null;
    try {
      renderer = global.SessionDetailView?.createRenderer({
        container: contentElement,
        templateSelector,
        timeUtils,
        toast: global.toast,
      });
    } catch (error) {
      console.error('TaskRunDetailModal: 初始化渲染器失败', error);
    }

    /**
     * 打开模态并渲染详情。
     *
     * @param {Object} session - 会话对象
     * @return {void}
     */
    function open(session) {
      if (!renderer) {
        notify('详情组件未加载，无法查看', 'error');
        return;
      }
      try {
        renderer.render(session);
      } catch (error) {
        console.error('渲染任务详情失败:', error);
        notify('渲染详情失败，请稍后再试', 'error');
        return;
      }
      modal.open({ runId: session?.run?.run_id });
    }

    /**
     * 清空内容。
     *
     * @return {void}
     */
    function clearContent() {
      contentElement.innerHTML = `
        <div class="session-detail__placeholder text-muted text-center py-4" data-session-placeholder>
          尚未加载任务详情
        </div>
      `;
    }

    /**
     * 用户可见通知。
     *
     * @param {string} message - 信息
     * @param {string} tone - tone
     * @return {void}
     */
    function notify(message, tone = 'info') {
      if (global.toast) {
        if (tone === 'error' && global.toast.error) {
          global.toast.error(message);
          return;
        }
        if (tone === 'success' && global.toast.success) {
          global.toast.success(message);
          return;
        }
        if (global.toast.info) {
          global.toast.info(message);
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
     * 销毁模态控制器。
     *
     * @return {void}
     */
    function destroy() {
      modal.destroy?.();
      renderer = null;
    }

    return {
      open,
      destroy,
    };
  }

  global.TaskRunDetailModal = {
    createController,
  };
})(window, document);
