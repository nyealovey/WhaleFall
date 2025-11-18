(function (global) {
  'use strict';

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

    function openCreate(event) {
      event?.preventDefault?.();
      createModal?.open();
    }

    function openCleanup(event) {
      event?.preventDefault?.();
      cleanupModal?.open();
    }

    function prepareCreatePartitionForm() {
      const yearSelect = document.getElementById('partitionYear');
      const monthSelect = document.getElementById('partitionMonth');
      if (!yearSelect || !monthSelect || !timeUtils) {
        return;
      }

      const now = timeUtils.getChinaTime ? timeUtils.getChinaTime() : new Date();
      const currentYear = now.getFullYear();
      const currentMonth = now.getMonth() + 1;

      yearSelect.innerHTML = '<option value="">请选择年份</option>';
      for (let year = currentYear; year <= currentYear + 2; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `${year}年`;
        yearSelect.appendChild(option);
      }

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

      yearSelect.removeEventListener('change', updateMonthOptions);
      yearSelect.addEventListener('change', updateMonthOptions);
      updateMonthOptions();
    }

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
