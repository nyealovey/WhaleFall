(function (global, document) {
  'use strict';

  const DEFAULT_LOADING_TEXT = '创建中...';

  function createController(options = {}) {
    const {
      ui = global.UI,
      toast = global.toast,
      numberFormat = global.NumberFormat,
      modalSelector = '#batchCreateModal',
      fileInputSelector = '#csvFile',
      triggerSelector = '[data-action="create-instance-batch"]',
      instanceService,
      instanceStore,
      getInstanceStore,
      loadingText = DEFAULT_LOADING_TEXT,
    } = options;

    if (!ui?.createModal) {
      throw new Error('BatchCreateInstanceModal: UI.createModal 未加载');
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

    function open() {
      resetFileInput();
      modal.open();
    }

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

    function submit() {
      handleSubmit();
    }

    function handleSubmit() {
      const currentService = resolveInstanceService();
      if (!currentService) {
        toast?.error?.('实例服务未初始化');
        return;
      }
      const fileInput = document.querySelector(fileInputSelector);
      const file = fileInput?.files?.[0];
      if (!file) {
        toast?.warning?.('请选择CSV文件');
        return;
      }
      const formData = new FormData();
      formData.append('file', file);
      modal.setLoading(true, loadingText);
      const executor = executeBatchCreate(currentService, formData);
      if (!executor) {
        modal.setLoading(false);
        toast?.error?.('批量创建服务未初始化');
        return;
      }
      executor
        .then((response) => handleSuccess(response))
        .catch((error) => {
          console.error('批量创建实例失败:', error);
          toast?.error?.(error?.message || '批量创建失败');
        })
        .finally(() => {
          modal.setLoading(false);
        });
    }

    function executeBatchCreate(service, payload) {
      const store = resolveInstanceStore();
      if (store?.actions?.batchCreateInstances) {
        return store.actions.batchCreateInstances(payload);
      }
      if (service?.batchCreateInstances) {
        return service.batchCreateInstances(payload);
      }
      return null;
    }

    function handleSuccess(response) {
      const result = response?.response || response?.data || response;
      if (response?.success === false && !result) {
        toast?.error?.(response?.error || '批量创建失败');
        return;
      }
      const message = result?.message || response?.message || '批量创建成功';
      toast?.success?.(message);
      const errors = result?.errors || response?.errors;
      if (errors && errors.length > 0) {
        toast?.warning?.(`部分实例创建失败：\n${errors.join('\n')}`);
      }
      modal.close();
      setTimeout(() => global.location.reload(), 1000);
    }

    function resolveInstanceStore() {
      if (typeof getInstanceStore === 'function') {
        return getInstanceStore();
      }
      return instanceStore;
    }

    function resolveInstanceService() {
      const store = resolveInstanceStore();
      if (store?.service) {
        return store.service;
      }
      if (typeof instanceService !== 'undefined' && instanceService) {
        return instanceService;
      }
      return null;
    }

    function resetFileInput() {
      const fileInput = document.querySelector(fileInputSelector);
      if (fileInput) {
        fileInput.value = '';
        removeFileInfo(fileInput.parentNode || fileInput);
      }
    }

    function removeFileInfo(root) {
      if (!root) {
        return;
      }
      const info = root.querySelector?.('.file-info');
      if (info) {
        info.remove();
      }
    }

    function attachTriggerEvents() {
      const triggers = document.querySelectorAll(triggerSelector);
      triggers.forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
          event.preventDefault();
          open();
        });
      });
    }

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
