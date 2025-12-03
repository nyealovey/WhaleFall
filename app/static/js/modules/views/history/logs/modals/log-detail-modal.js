(function (global, document) {
  'use strict';

  /**
   * 创建日志详情模态控制器。
   *
   * @param {Object} [options] - 配置
   * @param {Object} [options.ui] - UI 工具
   * @param {Object} [options.timeUtils] - 时间工具
   * @param {string} [options.modalSelector] - 模态选择器
   * @param {string} [options.contentSelector] - 内容容器
   * @param {string} [options.templateSelector] - 模板选择器
   * @param {string} [options.copyButtonSelector] - 底部复制按钮
   * @return {Object} 控制器
   */
  function createController(options = {}) {
    const {
      ui = global.UI,
      timeUtils = global.timeUtils,
      modalSelector = '#logDetailModal',
      contentSelector = '#logDetailContent',
      templateSelector = '#log-detail-template',
      copyButtonSelector = '#copyLogDetailButton',
    } = options;

    if (!ui?.createModal) {
      throw new Error('LogsLogDetailModal: UI.createModal 未加载');
    }

    const contentElement = document.querySelector(contentSelector);
    if (!contentElement) {
      throw new Error('LogsLogDetailModal: 未找到内容容器');
    }

    const modal = ui.createModal({
      modalSelector,
      onClose: clearContent,
    });

    clearContent();

    let renderer = null;
    try {
      renderer = global.LogDetailView?.createRenderer({
        container: contentElement,
        templateSelector,
        timeUtils,
        toast: global.toast,
      });
    } catch (error) {
      console.error('LogsLogDetailModal: 初始化渲染器失败', error);
    }

    const copyButton = document.querySelector(copyButtonSelector);
    if (copyButton) {
      copyButton.addEventListener('click', () => {
        const text = contentElement.textContent || '';
        if (!text) {
          notify('暂无可复制内容', 'warn');
          return;
        }
        if (navigator.clipboard?.writeText) {
          navigator.clipboard.writeText(text).then(
            () => notify('日志详情已复制', 'success'),
            () => notify('复制失败，请手动选择内容', 'error'),
          );
          return;
        }
        notify('复制失败，请手动选择内容', 'error');
      });
    }

    /**
     * 打开模态。
     *
     * @param {Object} log - 日志对象
     * @return {void}
     */
    function open(log) {
      if (!renderer) {
        notify('日志详情组件未加载', 'error');
        return;
      }
      try {
        renderer.render(log);
      } catch (error) {
        console.error('渲染日志详情失败:', error);
        notify('渲染失败，请稍后再试', 'error');
        return;
      }
      modal.open({ logId: log?.id });
    }

    /**
     * 重置内容。
     *
     * @return {void}
     */
    function clearContent() {
      contentElement.innerHTML = `
        <div class="log-detail__placeholder text-muted text-center py-4" data-log-placeholder>
          尚未加载日志详情
        </div>
      `;
    }

    /**
     * 通知助手。
     *
     * @param {string} message - 文案
     * @param {string} tone - tone
     * @return {void}
     */
    function notify(message, tone = 'info') {
      const toast = global.toast;
      if (toast) {
        if (tone === 'success' && toast.success) {
          toast.success(message);
          return;
        }
        if (tone === 'error' && toast.error) {
          toast.error(message);
          return;
        }
        if (toast.info) {
          toast.info(message);
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
     * 销毁控制器。
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

  global.LogsLogDetailModal = {
    createController,
  };
})(window, document);
