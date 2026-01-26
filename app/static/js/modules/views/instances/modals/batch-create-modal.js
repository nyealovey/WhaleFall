(function (global, document) {
  'use strict';

  const DEFAULT_LOADING_TEXT = '创建中...';

  /**
   * 创建批量创建实例模态框控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.ui] - UI 工具对象
   * @param {Object} [options.toast] - Toast 通知工具
   * @param {Object} [options.numberFormat] - 数字格式化工具
   * @param {string} [options.modalSelector] - 模态框选择器
   * @param {string} [options.fileInputSelector] - 文件输入框选择器
   * @param {string} [options.triggerSelector] - 触发按钮选择器
   * @param {Object} options.store - InstanceStore（由 Page Entry 注入）
   * @param {Function} [options.onSaved] - 批量创建成功后的回调（用于刷新列表等）
   * @param {string} [options.loadingText] - 加载文本
   * @return {Object} 控制器对象，包含 open、submit、handleFileSelect 方法
   * @throws {Error} 当 UI.createModal 未加载或模态框创建失败时抛出
   */
  function createController(options = {}) {
    const {
      ui = global.UI,
      toast = global.toast,
      numberFormat = global.NumberFormat,
      modalSelector = '#batchCreateModal',
      fileInputSelector = '#csvFile',
      triggerSelector = '[data-action="create-instance-batch"]',
      store = null,
      onSaved = null,
      loadingText = DEFAULT_LOADING_TEXT,
    } = options;

    if (!ui?.createModal) {
      throw new Error('BatchCreateInstanceModal: UI.createModal 未加载');
    }
    if (!store?.actions?.batchCreateInstances) {
      throw new Error('BatchCreateInstanceModal: store 未注入或缺少 batchCreateInstances');
    }

    const modal = ui.createModal({
      modalSelector,
      loadingText,
      onOpen: resetFileInput,
      onClose: resetFileInput,
      onConfirm: handleSubmit,
    });
    if (!modal) {
      throw new Error('BatchCreateInstanceModal: 无法创建批量创建模态');
    }

    attachTriggerEvents();
    attachFileChangeEvent();

    /**
     * 打开批量创建模态框。
     *
     * @return {void}
     */
    function open() {
      resetFileInput();
      modal.open();
    }

    /**
     * 处理文件选择事件。
     *
     * @param {Event} event - 文件选择事件
     * @return {void}
     */
    function handleFileSelect(event) {
      const input = event?.target;
      if (!input) {
        return;
      }
      const file = input.files?.[0];
      if (!file) {
        removeFileInfo(input);
        return;
      }
      if (!file.name.toLowerCase().endsWith('.csv')) {
        toast?.warning?.('请选择CSV格式文件');
        input.value = '';
        removeFileInfo(input);
        return;
      }
      const wrapper = input.parentNode;
      if (!wrapper) {
        return;
      }
      removeFileInfo(wrapper);
      const fileInfo = document.createElement('div');
      fileInfo.className = 'mt-2 text-muted file-info';
      const sizeLabel = numberFormat?.formatBytes
        ? numberFormat.formatBytes(file.size, {
            unit: 'KB',
            precision: 1,
            trimZero: true,
            fallback: '0 KB',
          })
        : `${(file.size / 1024).toFixed(1)} KB`;
      fileInfo.innerHTML = `<i class="fas fa-file-csv me-1"></i>已选择文件: ${file.name} (${sizeLabel})`;
      wrapper.appendChild(fileInfo);
    }

    /**
     * 提交批量创建请求。
     *
     * @return {void}
     */
    function submit() {
      handleSubmit();
    }

    /**
     * 处理表单提交。
     *
     * @return {void}
     */
    function handleSubmit() {
      const fileInput = document.querySelector(fileInputSelector);
      const file = fileInput?.files?.[0];
      if (!file) {
        toast?.warning?.('请选择CSV文件');
        return;
      }
      const formData = new FormData();
      formData.append('file', file);
      modal.setLoading(true, loadingText);
      store.actions
        .batchCreateInstances(formData)
        .then((response) => handleSuccess(response))
        .catch((error) => {
          console.error('批量创建实例失败:', error);
          toast?.error?.(error?.message || '批量创建失败');
        })
        .finally(() => {
          modal.setLoading(false);
        });
    }

    /**
     * 处理成功响应。
     *
     * @param {Object} response - 响应对象
     * @return {void}
     */
    function handleSuccess(response) {
      const payload = response?.data || response || {};
      const message = response?.message || '批量创建成功';
      toast?.success?.(message);
      const errors = payload?.errors || null;
      if (errors && errors.length > 0) {
        toast?.warning?.(`部分实例创建失败：\n${errors.join('\n')}`);
      }
      modal.close();
      if (typeof onSaved === 'function') {
        onSaved({ response });
      }
    }

    /**
     * 重置文件输入框。
     *
     * @return {void}
     */
    function resetFileInput() {
      const fileInput = document.querySelector(fileInputSelector);
      if (fileInput) {
        fileInput.value = '';
        removeFileInfo(fileInput.parentNode || fileInput);
      }
    }

    /**
     * 移除文件信息显示。
     *
     * @param {Element} root - 根元素
     * @return {void}
     */
    function removeFileInfo(root) {
      if (!root) {
        return;
      }
      const info = root.querySelector?.('.file-info');
      if (info) {
        info.remove();
      }
    }

    /**
     * 绑定触发按钮事件。
     *
     * @return {void}
     */
    function attachTriggerEvents() {
      const triggers = document.querySelectorAll(triggerSelector);
      triggers.forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
          event.preventDefault();
          open();
        });
      });
    }

    /**
     * 绑定文件选择事件。
     *
     * @return {void}
     */
    function attachFileChangeEvent() {
      const input = document.querySelector(fileInputSelector);
      if (!input) {
        return;
      }
      input.addEventListener('change', handleFileSelect);
    }

    return {
      open,
      submit,
      handleFileSelect,
    };
  }

  global.BatchCreateInstanceModal = {
    createController,
  };
})(window, document);
