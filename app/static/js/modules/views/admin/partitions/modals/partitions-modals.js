(function (global) {
  'use strict';

  /**
   * 创建分区创建/清理模态控制器。
   *
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.document] - Document 对象
   * @param {Object} [options.UI] - UI 工具对象
   * @param {Object} [options.toast] - Toast 通知工具
   * @param {Object} [options.service] - 分区服务对象
   * @param {Function} [options.getStore] - 获取状态管理的函数
   * @param {Object} [options.timeUtils] - 时间工具对象
   * @param {Function} [options.onReload] - 重载回调函数
   * @return {Object} 控制器对象，包含 openCreate、openCleanup 方法
   * @throws {Error} 当必需的依赖未初始化时抛出
   */
  function createController(options) {
    const {
      document,
      UI,
      toast,
      service,
      getStore,
      timeUtils,
      onReload,
    } = options || {};

    if (!document) {
      throw new Error('PartitionsModals: document is required');
    }
    if (!UI?.createModal) {
      throw new Error('PartitionsModals: UI.createModal 未加载');
    }

    const createModal = UI.createModal({
      modalSelector: '#createPartitionModal',
      onOpen: prepareCreatePartitionForm,
      onConfirm: handleCreatePartition,
    });

    const cleanupModal = UI.createModal({
      modalSelector: '#cleanupPartitionsModal',
      onConfirm: handleCleanupPartitions,
    });

    /**
     * 打开创建分区模态框。
     *
     * @param {Event} [event] - 触发事件
     * @return {void}
     */
    function openCreate(event) {
      event?.preventDefault?.();
      createModal?.open();
    }

    /**
     * 打开清理分区模态框。
     *
     * @param {Event} [event] - 触发事件
     * @return {void}
     */
    function openCleanup(event) {
      event?.preventDefault?.();
      cleanupModal?.open();
    }

    /**
     * 准备创建分区表单。
     *
     * 初始化年份和月份选择器，设置可选范围。
     *
     * @param {Document} [doc=document] 可选文档对象。
     * @returns {void}
     */
    function resolveDocumentArg(doc) {
      if (!doc) {
        return document;
      }
      if (doc instanceof Document) {
        return doc;
      }
      if (doc?.document instanceof Document) {
        return doc.document;
      }
      if (doc?.event instanceof Event) {
        return doc.event.target?.ownerDocument || document;
      }
      return document;
    }

    function prepareCreatePartitionForm(doc) {
      const targetDoc = resolveDocumentArg(doc);
      const yearSelect = targetDoc.getElementById('partitionYear');
      const monthSelect = targetDoc.getElementById('partitionMonth');
      if (!yearSelect || !monthSelect || !timeUtils) {
        return;
      }

      const now = timeUtils.getChinaTime ? timeUtils.getChinaTime() : new Date();
      const currentYear = now.getFullYear();
      const currentMonth = now.getMonth() + 1;

      yearSelect.innerHTML = '<option value="">请选择年份</option>';
      for (let year = currentYear; year <= currentYear + 2; year++) {
        const option = targetDoc.createElement('option');
        option.value = year;
        option.textContent = `${year}年`;
        yearSelect.appendChild(option);
      }

      /**
       * 根据当前年份更新月份选项。
       *
       * @param {void} 无参数。依赖当前年份选择器的值。
       * @returns {void}
       */
      const updateMonthOptions = () => {
        const selectedYear = parseInt(yearSelect.value, 10);
        Array.from(monthSelect.options).forEach((option) => {
          if (!option.value) {
            return;
          }
          const month = parseInt(option.value, 10);
          option.disabled = !Number.isNaN(selectedYear) && selectedYear === currentYear && month < currentMonth;
        });
      };
      monthSelect.innerHTML = '<option value="">请选择月份</option>';
      for (let month = 1; month <= 12; month++) {
        const option = targetDoc.createElement('option');
        option.value = month;
        option.textContent = `${month}月`;
        monthSelect.appendChild(option);
      }

      yearSelect.removeEventListener('change', updateMonthOptions);
      yearSelect.addEventListener('change', updateMonthOptions);
      updateMonthOptions();
    }

    /**
     * 处理创建分区请求。
     *
     * @returns {Promise<void>} 创建完成后 resolve。
     */
    async function handleCreatePartition() {
      const year = document.getElementById('partitionYear')?.value;
      const month = document.getElementById('partitionMonth')?.value;
      if (!year || !month) {
        toast?.error?.('请选择年份和月份');
        return;
      }
      const date = `${year}-${String(month).padStart(2, '0')}-01`;
      const store = getStore?.();
      const executor = store
        ? store.actions.createPartition({ date })
        : service?.createPartition({ date });
      if (!executor) {
        toast?.error?.('分区服务未初始化');
        return;
      }
      try {
        const result = await executor;
        if (store || result?.success) {
          toast?.success?.('分区创建成功');
          createModal?.close();
          onReload?.();
        } else {
          toast?.error?.(`分区创建失败: ${result?.error || '未知错误'}`);
        }
      } catch (error) {
        console.error('创建分区失败:', error);
        toast?.error?.(error?.message || '创建分区失败');
      }
    }

    /**
     * 处理清理分区请求。
     *
     * @returns {Promise<void>} 清理完成后 resolve。
     */
    async function handleCleanupPartitions() {
      const retentionInput = document.getElementById('retentionMonths');
      const retentionMonths = retentionInput ? Number(retentionInput.value) : 0;
      if (!retentionMonths || retentionMonths < 1) {
        toast?.error?.('请输入有效的保留月数');
        return;
      }
      if (!global.confirm(`确定要清理${retentionMonths}个月之前的分区吗？此操作不可恢复！`)) {
        return;
      }
      const store = getStore?.();
      const executor = store
        ? store.actions.cleanupPartitions({ retention_months: retentionMonths })
        : service?.cleanupPartitions({ retention_months: retentionMonths });
      if (!executor) {
        toast?.error?.('分区服务未初始化');
        return;
      }
      try {
        const result = await executor;
        if (store || result?.success) {
          toast?.success?.('分区清理成功');
          cleanupModal?.close();
          onReload?.();
        } else {
          toast?.error?.(`分区清理失败: ${result?.error || '未知错误'}`);
        }
      } catch (error) {
        console.error('清理分区失败:', error);
        toast?.error?.(error?.message || '清理分区失败');
      }
    }

    return {
      openCreate,
      openCleanup,
    };
  }

  global.PartitionsModals = {
    createController,
  };
})(window);
