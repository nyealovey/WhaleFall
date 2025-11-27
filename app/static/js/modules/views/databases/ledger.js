(function (global) {
  "use strict";

  function mount() {
    const helpers = global.DOMHelpers;
    if (!helpers) {
      console.error("DOMHelpers 未初始化，无法加载数据库台账页面");
      return;
    }
    const gridjs = global.gridjs;
    const GridWrapper = global.GridWrapper;
    if (!gridjs || !GridWrapper) {
      console.error("Grid.js 未就绪");
      return;
    }

    const { ready } = helpers;
    const gridHtml = gridjs.html;
    const root = document.getElementById("database-ledger-root");
    if (!root) {
      return;
    }

    const apiUrl = root.dataset.apiUrl;
    const exportUrl = root.dataset.exportUrl || "";
    const capacityStatsUrl = root.dataset.capacityStatsUrl || "";
    let currentDbType = root.dataset.currentDbType || "all";
    const FILTER_FORM_ID = "database-ledger-filter-form";

    let ledgerGrid = null;
    let databaseStore = null;
    let databaseService = null;
    let modalInstance = null;
    let trendChart = null;

    ready(() => {
      initializeService();
      initializeStore();
      initializeGrid();
      bindFilterForm();
      bindTypeButtons();
      bindExportButton();
      delegateGridActions();
      mountModal();
    });

    function initializeService() {
      if (!global.DatabaseLedgerService) {
        console.warn("DatabaseLedgerService 未加载");
        return;
      }
      try {
        databaseService = new global.DatabaseLedgerService(global.httpU);
      } catch (error) {
        console.error("初始化 DatabaseLedgerService 失败", error);
      }
    }

    function initializeStore() {
      if (!global.createDatabaseStore || !databaseService) {
        return;
      }
      try {
        databaseStore = global.createDatabaseStore({
          service: databaseService,
          emitter: global.mitt ? global.mitt() : null,
        });
        databaseStore.subscribe(databaseStore.EVENTS.trendLoaded, (payload) => {
          renderTrendChart(payload);
        });
        databaseStore.subscribe(databaseStore.EVENTS.error, (error) => {
          console.error("容量趋势加载失败", error);
          showTrendError("加载容量趋势失败，请稍后再试。");
        });
      } catch (error) {
        console.error("初始化 DatabaseStore 失败", error);
      }
    }

    function initializeGrid() {
      const container = document.getElementById("database-ledger-grid");
      if (!container) {
        return;
      }
      ledgerGrid = new GridWrapper(container, {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: apiUrl,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            const total = payload.total || 0;
            updateTotalCount(total);
            return total;
          },
        },
      });
      const initialFilters = resolveFilters();
      initialFilters.db_type = currentDbType;
      ledgerGrid.setFilters(initialFilters, { silent: true });
      ledgerGrid.init();
    }

    function buildColumns() {
      return [
        {
          id: "database_name",
          name: "数据库/实例",
          formatter: (cell, row) => renderNameCell(resolveRowMeta(row)),
        },
        {
          id: "db_type",
          name: "类型",
          width: "110px",
          formatter: (cell, row) => renderDbTypeBadge(resolveRowMeta(row)?.db_type),
        },
        {
          id: "capacity",
          name: "数据库大小",
          formatter: (cell, row) => renderCapacityCell(resolveRowMeta(row)?.capacity),
        },
        {
          id: "sync_status",
          name: "状态",
          width: "100px",
          formatter: (cell, row) => renderStatusBadge(resolveRowMeta(row)?.sync_status),
        },
        {
          id: "actions",
          name: "操作",
          width: "140px",
          formatter: (cell, row) => renderActions(resolveRowMeta(row)),
        },
        { id: "__meta__", hidden: true },
      ];
    }

    function handleServerResponse(response) {
      const payload = response?.data || response || {};
      const items = payload.items || [];
      return items.map((item) => [item.database_name, item.db_type, item.capacity, item.sync_status, null, item]);
    }

    function resolveRowMeta(row) {
      return row?.cells?.[row.cells.length - 1]?.data || {};
    }

    function renderNameCell(meta) {
      if (!gridHtml) {
        return meta.database_name || "-";
      }
      const instanceName = meta.instance?.name || "未知实例";
      const host = meta.instance?.host || "-";
      return gridHtml(`
        <div>
            <strong>${escapeHtml(meta.database_name || "-")}</strong>
            <div class="text-muted small">
                <i class="fas fa-server me-1 text-info"></i>${escapeHtml(instanceName)} · ${escapeHtml(host)}
            </div>
        </div>
      `);
    }

    function renderDbTypeBadge(dbType) {
      if (!gridHtml) {
        return dbType || "-";
      }
      const labelMap = {
        mysql: "MySQL",
        postgresql: "PostgreSQL",
        sqlserver: "SQL Server",
        oracle: "Oracle",
      };
      const colorMap = {
        mysql: "success",
        postgresql: "info",
        sqlserver: "warning",
        oracle: "danger",
      };
      const color = colorMap[dbType] || "secondary";
      const label = labelMap[dbType] || (dbType || "未知");
      return gridHtml(`<span class="badge bg-${color}">${label}</span>`);
    }

    function renderCapacityCell(capacity) {
      if (!gridHtml) {
        return capacity?.label || "未采集";
      }
      const sizeLabel = escapeHtml(capacity?.label || "未采集");
      const collectedAt = capacity?.collected_at
        ? formatDate(capacity.collected_at)
        : "无采集记录";
      return gridHtml(`
        <div>
            <div class="fw-bold">${sizeLabel}</div>
            <small>${escapeHtml(collectedAt)}</small>
        </div>
      `);
    }

    function renderStatusBadge(status) {
      if (!gridHtml) {
        return status?.label || "未知";
      }
      const variant = status?.variant || "secondary";
      const label = status?.label || "未知";
      return gridHtml(`<span class="badge bg-${variant}">${escapeHtml(label)}</span>`);
    }

    function renderActions(meta) {
      if (!gridHtml) {
        return "";
      }
      const params = new URLSearchParams();
      if (meta?.database_name) {
        // database_aggregations 页面只识别 database/database_id，两者都写入可兼容旧逻辑
        params.set("database", meta.database_name);
      }
      if (meta?.id) {
        params.set("database_id", String(meta.id));
      }
      if (meta?.instance?.id) {
        params.set("instance", String(meta.instance.id));
      }
      const dbTypeParam = meta?.db_type || meta?.instance?.db_type;
      if (dbTypeParam) {
        params.set("db_type", dbTypeParam);
      }
      const queryString = params.toString();
      const separator = capacityStatsUrl.includes("?") ? "&" : "?";
      const capacityHref = capacityStatsUrl
        ? queryString
          ? `${capacityStatsUrl}${separator}${queryString}`
          : capacityStatsUrl
        : "#";
      return gridHtml(`
        <div class="btn-group btn-group-sm" role="group">
            <button type="button" class="btn btn-outline-primary" data-view-capacity data-database-id="${meta.id}">
                <i class="fas fa-chart-line"></i>
            </button>
            <a class="btn btn-outline-secondary" href="${capacityHref}" target="_blank" rel="noreferrer">
                <i class="fas fa-external-link-alt"></i>
            </a>
        </div>
      `);
    }

    function bindTypeButtons() {
      const buttons = root.querySelectorAll("[data-db-type-btn]");
      buttons.forEach((button) => {
        button.addEventListener("click", () => {
          currentDbType = button.dataset.dbType || "all";
          buttons.forEach((btn) => btn.classList.remove("btn-primary"));
          buttons.forEach((btn) => btn.classList.add("btn-outline-primary", "border-2", "fw-bold"));
          button.classList.add("btn-primary");
          button.classList.remove("btn-outline-primary", "border-2", "fw-bold");
          const filters = ledgerGrid ? { ...(ledgerGrid.currentFilters || {}) } : {};
          filters.db_type = currentDbType;
          setDbTypeFieldValue(currentDbType);
          if (ledgerGrid) {
            ledgerGrid.setFilters(filters);
          }
        });
      });
    }

    function bindFilterForm() {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return;
      }
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const filters = resolveFilters();
        currentDbType = filters.db_type || "all";
        if (ledgerGrid) {
          ledgerGrid.setFilters(filters);
        }
      });
      const clearButton = form.querySelector("[data-filter-clear]");
      if (clearButton) {
        clearButton.addEventListener("click", () => {
          form.reset();
          currentDbType = "all";
          setDbTypeFieldValue("all");
          if (ledgerGrid) {
            ledgerGrid.setFilters({ db_type: "all", search: "" });
          }
        });
      }
    }

    function resolveFilters() {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return { db_type: currentDbType, search: "" };
      }
      const formData = new FormData(form);
      return {
        search: (formData.get("search") || "").trim(),
        db_type: (formData.get("db_type") || currentDbType || "all").trim() || "all",
      };
    }

    function setDbTypeFieldValue(value) {
      const form = document.getElementById(FILTER_FORM_ID);
      if (!form) {
        return;
      }
      const select = form.querySelector('[name="db_type"]');
      if (select) {
        select.value = value || "all";
      }
    }

    function bindExportButton() {
      const exportBtn = root.querySelector("[data-export-ledger]");
      if (!exportBtn) {
        return;
      }
      exportBtn.addEventListener("click", () => {
        if (!exportUrl) {
          return;
        }
        const params = new URLSearchParams(ledgerGrid?.currentFilters || {});
        const query = params.toString();
        const downloadUrl = query ? `${exportUrl}?${query}` : exportUrl;
        global.open(downloadUrl, "_blank", "noreferrer");
      });
    }

    function delegateGridActions() {
      const gridContainer = document.getElementById("database-ledger-grid");
      if (!gridContainer) {
        return;
      }
      gridContainer.addEventListener("click", (event) => {
        const target = event.target.closest("[data-view-capacity]");
        if (!target) {
          return;
        }
        const databaseId = Number(target.dataset.databaseId);
        if (!databaseId) {
          return;
        }
        openCapacityModal(databaseId);
      });
    }

    function mountModal() {
      const modalElement = document.getElementById("databaseCapacityModal");
      if (!modalElement || !global.bootstrap?.Modal) {
        return;
      }
      modalInstance = new global.bootstrap.Modal(modalElement);
    }

    function openCapacityModal(databaseId) {
      if (!modalInstance) {
        return;
      }
      modalInstance.show();
      showTrendLoading();
      const request = databaseStore
        ? databaseStore.fetchCapacityTrend(databaseId)
        : databaseService.fetchCapacityTrend(databaseId);
      request.catch(() => {
        showTrendError("加载容量趋势失败，请稍后再试。");
      });
    }

    function showTrendLoading() {
      const loading = document.querySelector("[data-capacity-loading]");
      const emptyHint = document.querySelector("[data-capacity-empty]");
      if (loading) {
        loading.classList.remove("d-none");
      }
      if (emptyHint) {
        emptyHint.classList.add("d-none");
      }
      const subtitle = document.querySelector("[data-capacity-modal-subtitle]");
      if (subtitle) {
        subtitle.textContent = "正在加载最近 30 天的容量数据...";
      }
    }

    function showTrendError(message) {
      const loading = document.querySelector("[data-capacity-loading]");
      const emptyHint = document.querySelector("[data-capacity-empty]");
      if (loading) {
        loading.classList.add("d-none");
      }
      if (emptyHint) {
        emptyHint.classList.remove("d-none");
        emptyHint.textContent = message || "暂无数据";
      }
    }

    function renderTrendChart(payload) {
      const loading = document.querySelector("[data-capacity-loading]");
      const emptyHint = document.querySelector("[data-capacity-empty]");
      const subtitle = document.querySelector("[data-capacity-modal-subtitle]");
      const title = document.querySelector("[data-capacity-modal-title]");
      if (loading) {
        loading.classList.add("d-none");
      }

      if (title) {
        const instanceName = payload.database?.instance_name || "未知实例";
        const dbName = payload.database?.name || "-";
        title.textContent = `${dbName} @ ${instanceName}`;
      }

      if (!payload.points?.length) {
        if (emptyHint) {
          emptyHint.classList.remove("d-none");
          emptyHint.textContent = "暂无容量采集记录";
        }
        if (subtitle) {
          subtitle.textContent = "按需触发容量采集或等待下一次同步。";
        }
        if (trendChart) {
          trendChart.destroy();
          trendChart = null;
        }
        return;
      }

      if (emptyHint) {
        emptyHint.classList.add("d-none");
      }

      const labels = payload.points.map((point) => formatDate(point.collected_at || point.collected_date));
      const values = payload.points.map((point) => point.size_mb || 0);
      const datasetLabel = "数据库大小 (MB)";

      const ctx = document.getElementById("databaseCapacityChart");
      if (!ctx || !global.Chart) {
        return;
      }
      if (trendChart) {
        trendChart.destroy();
      }
      trendChart = new global.Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: datasetLabel,
              data: values,
              tension: 0.3,
              borderColor: "#2563eb",
              backgroundColor: "rgba(37, 99, 235, 0.15)",
              pointRadius: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                callback: (value) => `${value} MB`,
              },
            },
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  const point = payload.points?.[context.dataIndex];
                  const numberFormat = global.NumberFormat;
                  const sizeText = numberFormat?.formatBytesFromMB
                    ? numberFormat.formatBytesFromMB(point?.size_mb || 0, { maximumFractionDigits: 2 })
                    : `${point?.size_mb || 0} MB`;
                  return ` ${sizeText}`;
                },
              },
            },
          },
        },
      });

      if (subtitle) {
        subtitle.textContent = `最近更新：${formatDate(payload.points[payload.points.length - 1].collected_at)}`;
      }
    }

    function formatDate(value) {
      if (!value) {
        return "未采集";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }
      return date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    function updateTotalCount(total) {
      const target = document.getElementById("database-ledger-total");
      if (target) {
        target.textContent = `共 ${total} 条记录`;
      }
    }

    function escapeHtml(str) {
      if (typeof str !== "string") {
        return str ?? "";
      }
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }
  }

  global.DatabaseLedgerPage = {
    mount,
  };
})(window);
