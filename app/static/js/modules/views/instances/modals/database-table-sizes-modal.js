(function (window, document) {
  'use strict';

  const gridjs = window.gridjs;
  const toast = window.toast || {
    success: console.info,
    error: console.error,
    info: console.info,
    warning: console.warn,
  };

  function ensureDeps(options) {
    const ui = options?.ui || window.UI;
    const Service = options?.InstanceManagementService || window.InstanceManagementService;
    const http = options?.http || window.httpU;

    if (!ui?.createModal) {
      throw new Error('DatabaseTableSizesModal: UI.createModal 未初始化');
    }
    if (!ui?.escapeHtml) {
      throw new Error('DatabaseTableSizesModal: UI.escapeHtml 未初始化');
    }
    if (!Service) {
      throw new Error('DatabaseTableSizesModal: InstanceManagementService 未加载');
    }
    if (!http) {
      throw new Error('DatabaseTableSizesModal: httpU 未初始化');
    }
    if (!gridjs?.Grid) {
      throw new Error('DatabaseTableSizesModal: gridjs.Grid 未加载');
    }

    return {
      ui,
      service: new Service(http),
    };
  }

  function parsePayload(raw) {
    if (!raw) {
      return {};
    }
    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw);
      } catch (error) {
        console.warn('DatabaseTableSizesModal: payload 解析失败', error);
        return {};
      }
    }
    return raw;
  }

  function formatSizeFromMb(value) {
    const formatter = window.NumberFormat?.formatBytesFromMB;
    if (typeof formatter !== 'function') {
      const numeric = Number(value) || 0;
      return `${numeric} MB`;
    }
    if (value === null || value === undefined || value === '') {
      return '-';
    }
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric >= 0 && numeric < 1) {
      return '<1 MB';
    }
    return formatter(value, {
      unit: 'auto',
      precision: 2,
      trimZero: true,
      fallback: '-',
    });
  }

  function formatRowCount(value) {
    const formatter = window.NumberFormat?.formatInteger;
    if (typeof formatter !== 'function') {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? String(Math.round(numeric)) : '-';
    }
    return formatter(value, { fallback: '-' });
  }

  function formatCollectedAt(value) {
    const timeUtils = window.timeUtils;
    if (value && timeUtils?.formatDateTime) {
      return timeUtils.formatDateTime(value);
    }
    return value ? String(value) : '未刷新';
  }

  function createController(options) {
    const { ui, service } = ensureDeps(options);
    const escapeHtml = ui.escapeHtml;

    const modalEl = document.getElementById('tableSizesModal');
    if (!modalEl) {
      throw new Error('DatabaseTableSizesModal: 找不到 #tableSizesModal');
    }
    const dbNameEl = document.getElementById('tableSizesModalDatabaseName');
    const collectedAtEl = document.getElementById('tableSizesModalCollectedAt');
    const gridContainer = document.getElementById('tableSizesGrid');

    if (!gridContainer) {
      throw new Error('DatabaseTableSizesModal: 找不到 #tableSizesGrid');
    }

    let currentDatabaseId = null;
    let currentDatabaseName = null;
    let grid = null;
    let lastSnapshotPayload = null;

    function destroyGrid() {
      if (grid && typeof grid.destroy === 'function') {
        grid.destroy();
      }
      grid = null;
      gridContainer.innerHTML = '';
    }

    function renderLoading() {
      gridContainer.innerHTML = `
        <div class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <p class="mt-2 text-muted mb-0">正在加载表容量...</p>
        </div>
      `;
    }

    function renderError(message) {
      gridContainer.innerHTML = `
        <div class="text-center py-4">
          <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
          <p class="text-muted mb-2">加载表容量失败</p>
          <p class="text-danger">${escapeHtml(message || '请求失败')}</p>
          <button type="button" class="btn btn-outline-primary" data-action="retry-load-table-sizes">
            <i class="fas fa-redo me-1"></i>重试
          </button>
        </div>
      `;
    }

    function renderEmpty() {
      gridContainer.innerHTML = `
        <div class="text-center py-4">
          <i class="fas fa-table fa-3x text-muted mb-3"></i>
          <p class="text-muted mb-0">暂无表容量快照</p>
          <p class="text-muted">点击"刷新"采集最新数据</p>
        </div>
      `;
    }

    function setHeader(databaseName, collectedAt) {
      if (dbNameEl) {
        dbNameEl.textContent = databaseName ? String(databaseName) : '';
      }
      if (collectedAtEl) {
        collectedAtEl.textContent = formatCollectedAt(collectedAt);
      }
    }

    function renderGrid(tables) {
      destroyGrid();
      if (!Array.isArray(tables) || tables.length === 0) {
        renderEmpty();
        return;
      }

      const columns = [
        { name: 'Schema', id: 'schema_name', width: '140px' },
        { name: '表', id: 'table_name' },
        { name: '总大小', id: 'size_mb', width: '140px' },
        { name: '数据', id: 'data_size_mb', width: '140px' },
        { name: '索引', id: 'index_size_mb', width: '140px' },
        { name: '行数', id: 'row_count', width: '120px' },
      ];

      const data = tables.map((row) => ([
        row?.schema_name || '-',
        row?.table_name || '-',
        formatSizeFromMb(row?.size_mb),
        formatSizeFromMb(row?.data_size_mb),
        formatSizeFromMb(row?.index_size_mb),
        formatRowCount(row?.row_count),
      ]));

      grid = new gridjs.Grid({
        columns,
        data,
        sort: true,
        search: true,
        pagination: {
          enabled: true,
          limit: 20,
          summary: true,
        },
        fixedHeader: true,
        height: '420px',
      });

      grid.render(gridContainer);
    }

    async function loadSnapshot(params = {}) {
      if (!currentDatabaseId) {
        renderError('缺少数据库信息');
        return;
      }
      renderLoading();
      try {
        const resp = await service.fetchDatabaseTableSizes(currentDatabaseId, params);
        if (!resp?.success) {
          throw new Error(resp?.message || '加载失败');
        }
        const payload = resp?.data || resp || {};
        lastSnapshotPayload = payload;
        setHeader(currentDatabaseName, payload.collected_at);
        renderGrid(payload.tables);
      } catch (error) {
        console.error('加载表容量失败', error);
        const message = ui.resolveErrorMessage?.(error, '加载表容量失败') || String(error);
        toast.error(message);
        renderError(message);
      }
    }

    async function refreshSnapshot(modalApi) {
      if (!currentDatabaseId) {
        toast.error('缺少数据库信息');
        return;
      }

      modalApi?.setLoading?.(true, '刷新中...');
      try {
        const resp = await service.refreshDatabaseTableSizes(currentDatabaseId, {
          limit: 2000,
          page: 1,
        });
        if (!resp?.success) {
          throw new Error(resp?.message || '刷新失败');
        }
        const payload = resp?.data || resp || {};
        lastSnapshotPayload = payload;
        setHeader(currentDatabaseName, payload.collected_at);
        renderGrid(payload.tables);

        const saved = payload.saved_count ?? 0;
        const deleted = payload.deleted_count ?? 0;
        const elapsed = payload.elapsed_ms ?? 0;
        toast.success(`刷新成功: 写入 ${saved} 条, 清理 ${deleted} 条, 耗时 ${elapsed} ms`);
      } catch (error) {
        console.error('刷新表容量失败', error);
        const message = ui.resolveErrorMessage?.(error, '刷新表容量失败') || String(error);
        toast.error(message);
        if (lastSnapshotPayload) {
          renderGrid(lastSnapshotPayload.tables);
        }
      } finally {
        modalApi?.setLoading?.(false);
      }
    }

    const modal = ui.createModal({
      modalSelector: '#tableSizesModal',
      onOpen: ({ modal: api, payload }) => {
        const parsed = parsePayload(payload);
        currentDatabaseId = parsed?.database_id || parsed?.databaseId || null;
        currentDatabaseName = parsed?.database_name || parsed?.databaseName || null;
        lastSnapshotPayload = null;
        setHeader(currentDatabaseName, null);
        loadSnapshot({ limit: 2000, page: 1 });
        api?.setLoading?.(false);
      },
      onConfirm: ({ modal: api }) => {
        refreshSnapshot(api);
      },
      onClose: () => {
        currentDatabaseId = null;
        currentDatabaseName = null;
        lastSnapshotPayload = null;
        destroyGrid();
      },
    });

    modalEl.addEventListener('click', (event) => {
      const actionEl = event.target.closest('[data-action]');
      if (!actionEl) {
        return;
      }
      const action = actionEl.getAttribute('data-action');
      if (action === 'retry-load-table-sizes') {
        event.preventDefault();
        loadSnapshot({ limit: 2000, page: 1 });
      }
    });

    return {
      open(databaseId, databaseName) {
        modal.open({
          database_id: databaseId,
          database_name: databaseName,
        });
      },
    };
  }

  window.InstanceDatabaseTableSizesModal = window.InstanceDatabaseTableSizesModal || {};
  window.InstanceDatabaseTableSizesModal.createController = createController;
})(window, document);
