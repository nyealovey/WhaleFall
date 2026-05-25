(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  const gridjs = global.gridjs;
  const GridPage = global.Views?.GridPage;
  const GridPlugins = global.Views?.GridPlugins;
  const escapeHtml = global.UI?.escapeHtml;
  const resolveErrorMessage = global.UI?.resolveErrorMessage;
  const rowMeta = global.GridRowMeta;

  if (!helpers || !gridjs || !GridPage?.mount || !GridPlugins) {
    console.error("SQL Server AG 数据库状态页依赖未加载");
    return;
  }
  if (typeof escapeHtml !== "function" || typeof rowMeta?.get !== "function") {
    console.error("SQL Server AG 数据库状态页 UI helpers 未加载");
    return;
  }

  const root = document.getElementById("sqlserver-status-root");
  if (!root) {
    return;
  }

  const gridHtml = gridjs.html;
  const { ready } = helpers;
  const apiUrl = root.dataset.apiUrl || "/api/v1/sqlserver-clusters/database-sync-states";
  let gridPage = null;
  let clustersService = null;

  ready(() => {
    const SQLServerClustersService = global.SQLServerClustersService;
    clustersService = typeof SQLServerClustersService === "function" ? new SQLServerClustersService() : null;
    initializeGrid();
    bindClusterSelection();
    bindSyncCurrentCluster();
    updateSyncButtonState();
  });

  function initializeGrid() {
    gridPage = GridPage.mount({
      root,
      grid: "#sqlserver-status-grid",
      filterForm: "#sqlserver-status-filter-form",
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: apiUrl,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            updateKpis(payload.kpis || {});
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "cluster_id", "ag_name", "status"],
        normalize: normalizeFilters,
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          autoSubmitDebounce: 300,
        }),
      ],
    });
  }

  function buildColumns() {
    return [
      {
        name: "状态",
        id: "status",
        formatter: (value) => gridHtml(renderStatusPill(value)),
      },
      {
        name: "群集",
        id: "cluster_name",
        formatter: (value) => value || "-",
      },
      {
        name: "AG",
        id: "ag_name",
        formatter: (value) => value || "-",
      },
      {
        name: "数据库",
        id: "database_name",
        formatter: (value) => gridHtml(`<span class="fw-semibold">${escapeHtml(value || "-")}</span>`),
      },
      {
        name: "Replica",
        id: "replica_names",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return gridHtml(renderReplicaSummary(meta));
        },
      },
      {
        name: "队列",
        id: "max_log_send_queue_size",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return renderQueueSummary(meta);
        },
      },
      {
        name: "原因",
        id: "error_summary",
        formatter: (value) => value || "-",
      },
      {
        name: "最近检测",
        id: "last_checked_at",
        formatter: (value) => formatDate(value),
      },
    ];
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = Array.isArray(payload.items) ? payload.items : [];
    return items.map((item) => [
      item.status,
      item.cluster_name,
      item.ag_name,
      item.database_name,
      item.replica_names,
      item.max_log_send_queue_size,
      item.error_summary,
      item.last_checked_at,
      item,
    ]);
  }

  function normalizeFilters(filters) {
    const normalized = filters && typeof filters === "object" ? filters : {};
    const cleaned = {};
    const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
    if (search) {
      cleaned.search = search;
    }
    const clusterId = typeof normalized.cluster_id === "string" ? normalized.cluster_id.trim() : "";
    if (clusterId) {
      cleaned.cluster_id = clusterId;
    }
    const agName = typeof normalized.ag_name === "string" ? normalized.ag_name.trim() : "";
    if (agName) {
      cleaned.ag_name = agName;
    }
    const status = typeof normalized.status === "string" ? normalized.status.trim() : "all";
    cleaned.status = status || "all";
    return cleaned;
  }

  function bindClusterSelection() {
    root.querySelector('[name="cluster_id"]')?.addEventListener("change", updateSyncButtonState);
  }

  function bindSyncCurrentCluster() {
    root.querySelector('[data-action="sync-current-cluster"]')?.addEventListener("click", (event) => {
      event.preventDefault();
      syncCurrentCluster(event.currentTarget);
    });
  }

  function getSelectedClusterId() {
    return root.querySelector('[name="cluster_id"]')?.value || "";
  }

  function updateSyncButtonState() {
    const button = root.querySelector('[data-action="sync-current-cluster"]');
    if (!button) {
      return;
    }
    button.disabled = !getSelectedClusterId();
  }

  async function syncCurrentCluster(button) {
    const clusterId = getSelectedClusterId();
    if (!clusterId || !clustersService) {
      return;
    }
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>检测中';
    try {
      const response = await clustersService.syncStatus(clusterId);
      if (response?.success === false) {
        throw new Error(response.message || "检测失败");
      }
      global.toast?.success?.("SQL Server AG 数据库状态检测完成");
      gridPage?.gridWrapper?.refresh?.();
    } catch (error) {
      const message = typeof resolveErrorMessage === "function" ? resolveErrorMessage(error, "检测失败") : error.message;
      global.toast?.error?.(message || "检测失败");
    } finally {
      button.innerHTML = original;
      updateSyncButtonState();
    }
  }

  function updateKpis(kpis) {
    [
      ["total_databases", kpis.total_databases],
      ["abnormal_databases", kpis.abnormal_databases],
      ["normal_databases", kpis.normal_databases],
      ["affected_replicas", kpis.affected_replicas],
    ].forEach(([key, value]) => {
      const node = root.querySelector(`[data-kpi="${key}"]`);
      if (node) {
        node.textContent = String(Number(value || 0));
      }
    });
  }

  function renderStatusPill(status) {
    if (status === "abnormal") {
      return '<span class="status-pill status-pill--danger">异常</span>';
    }
    return '<span class="status-pill status-pill--success">正常</span>';
  }

  function renderReplicaSummary(item) {
    const abnormal = Array.isArray(item.abnormal_replica_names) ? item.abnormal_replica_names : [];
    if (abnormal.length > 0) {
      return `<span class="status-pill status-pill--danger">${escapeHtml(abnormal.join(", "))}</span>` +
        `<small class="text-muted ms-2">${Number(item.abnormal_replica_count || 0)} / ${Number(item.replica_count || 0)}</small>`;
    }
    return `<span class="status-pill status-pill--success">${Number(item.replica_count || 0)} 个</span>`;
  }

  function renderQueueSummary(item) {
    const logSend = item.max_log_send_queue_size ?? "-";
    const redo = item.max_redo_queue_size ?? "-";
    return `log ${logSend} / redo ${redo}`;
  }

  function formatDate(value) {
    if (!value) {
      return "-";
    }
    if (global.timeUtils?.formatDateTime) {
      return global.timeUtils.formatDateTime(value);
    }
    return String(value);
  }
})(window);
