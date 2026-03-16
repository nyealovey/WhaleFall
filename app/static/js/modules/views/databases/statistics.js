/**
 * 挂载数据库统计页面。
 *
 * 页面负责刷新摘要卡、分布表与最新容量排行，不依赖页面重载。
 *
 * @param {Window} global - window 对象
 * @returns {void}
 */
function mountDatabaseStatisticsPage(global) {
  "use strict";

  const document = global.document;
  const root = document?.getElementById("database-statistics-root");
  if (!document || !root) {
    return;
  }

  const refreshButton = document.querySelector('[data-action="refresh-stats"]');
  if (!refreshButton) {
    return;
  }

  const DatabasesStatisticsService = global.DatabasesStatisticsService;
  if (typeof DatabasesStatisticsService !== "function") {
    console.error("DatabasesStatisticsService 未初始化");
    return;
  }

  let service = null;
  try {
    service = new DatabasesStatisticsService();
  } catch (error) {
    console.error("初始化 DatabasesStatisticsService 失败:", error);
    return;
  }

  const escapeHtml = global.UI?.escapeHtml || fallbackEscapeHtml;
  refreshButton.addEventListener("click", handleRefreshClick);

  function handleRefreshClick(event) {
    event.preventDefault();
    toggleLoading(true);

    service
      .fetchStatistics()
      .then((payload) => {
        const stats = payload?.data?.stats ?? payload?.stats ?? null;
        if (!stats || typeof stats !== "object") {
          throw new Error("数据库统计数据格式不正确");
        }
        applyStats(stats);
        notify("数据库统计已刷新", "success");
      })
      .catch((error) => {
        console.error("刷新数据库统计失败:", error);
        notify("刷新失败，请稍后再试", "error");
      })
      .finally(() => toggleLoading(false));
  }

  function applyStats(stats) {
    setMetricValue("total_databases", formatInteger(stats.total_databases));
    setMetricValue("active_databases", formatInteger(stats.active_databases));
    setMetricValue("total_instances", formatInteger(stats.total_instances));
    setMetricValue("total_size_mb", formatSize(stats.total_size_mb));
    updateSummaryMeta(stats);
    renderDbTypePanel(stats);
    renderInstancePanel(stats);
    renderSyncStatusPanel(stats);
    renderCapacityRankingPanel(stats);
  }

  function updateSummaryMeta(stats) {
    const total = Number(stats?.total_databases ?? 0) || 0;
    const active = Number(stats?.active_databases ?? 0) || 0;
    const inactive = Number(stats?.inactive_databases ?? 0) || 0;
    const deleted = Number(stats?.deleted_databases ?? 0) || 0;
    const totalInstances = Number(stats?.total_instances ?? 0) || 0;

    setText("dbStatsMetaActiveCount", formatInteger(active));
    setText("dbStatsMetaInactiveCount", formatInteger(inactive));
    setText("dbStatsMetaDeletedCount", formatInteger(deleted));
    setText("dbStatsMetaActiveRate", `${resolvePercent(active, total).toFixed(1)}%`);
    setText("dbStatsMetaDbPerInstance", formatDecimal(totalInstances > 0 ? active / totalInstances : 0));
    setText("dbStatsMetaAverageSize", formatSize(stats?.avg_size_mb));
    setText("dbStatsMetaMaxSize", formatSize(stats?.max_size_mb));
  }

  function renderDbTypePanel(stats) {
    renderDistributionPanel({
      containerSelector: '[data-role="db-type-panel"]',
      icon: "fa-layer-group",
      emptyText: "暂无数据库类型数据",
      headers: ["类型", "数量", "占比"],
      rows: Array.isArray(stats?.db_type_stats) ? stats.db_type_stats : [],
      total: Number(stats?.active_databases ?? 0) || 0,
      rowRenderer: (item, percent) => `
        <tr>
          <td><span class="chip-outline chip-outline--brand">${escapeHtml(String(item?.db_type || "").toUpperCase() || "-")}</span></td>
          <td class="text-end"><span class="statistics-number">${formatInteger(item?.count)}</span></td>
          <td>
            ${renderPercentCell(percent, "statistics-progress__bar--info")}
          </td>
        </tr>
      `,
    });
  }

  function renderInstancePanel(stats) {
    renderDistributionPanel({
      containerSelector: '[data-role="instance-panel"]',
      icon: "fa-server",
      emptyText: "暂无实例分布数据",
      headers: ["实例", "数据库数", "占比"],
      rows: Array.isArray(stats?.instance_stats) ? stats.instance_stats : [],
      total: Number(stats?.active_databases ?? 0) || 0,
      rowRenderer: (item, percent) => `
        <tr>
          <td>
            <div class="statistics-title-stack">
              <strong>${escapeHtml(String(item?.instance_name || "-"))}</strong>
              <span class="statistics-subtext">${escapeHtml(String(item?.db_type || "").toUpperCase() || "-")}</span>
            </div>
          </td>
          <td class="text-end"><span class="statistics-number">${formatInteger(item?.count)}</span></td>
          <td>
            ${renderPercentCell(percent, "statistics-progress__bar--success")}
          </td>
        </tr>
      `,
    });
  }

  function renderSyncStatusPanel(stats) {
    renderDistributionPanel({
      containerSelector: '[data-role="sync-status-panel"]',
      icon: "fa-arrows-rotate",
      emptyText: "暂无同步状态数据",
      headers: ["状态", "数量", "占比"],
      rows: Array.isArray(stats?.sync_status_stats) ? stats.sync_status_stats : [],
      total: Number(stats?.active_databases ?? 0) || 0,
      rowRenderer: (item, percent) => `
        <tr>
          <td><span class="status-pill status-pill--${escapeHtml(String(item?.variant || "muted"))}">${escapeHtml(String(item?.label || "-"))}</span></td>
          <td class="text-end"><span class="statistics-number">${formatInteger(item?.count)}</span></td>
          <td>
            ${renderPercentCell(percent, "statistics-progress__bar--muted")}
          </td>
        </tr>
      `,
    });
  }

  function renderCapacityRankingPanel(stats) {
    const container = document.querySelector('[data-role="capacity-ranking-panel"]');
    if (!container) {
      return;
    }

    const rows = Array.isArray(stats?.capacity_rankings) ? stats.capacity_rankings : [];
    if (!rows.length) {
      container.innerHTML = renderEmptyState("fa-trophy", "暂无容量排行数据");
      return;
    }

    container.innerHTML = `
      <div class="table-responsive statistics-panel__table">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>数据库</th>
              <th class="statistics-panel__col-size text-end">大小</th>
              <th class="text-end">采集时间</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (item) => `
                  <tr>
                    <td>
                      <div class="statistics-title-stack">
                        <strong>${escapeHtml(String(item?.database_name || "-"))}</strong>
                        <span class="statistics-subtext">${escapeHtml(String(item?.instance_name || "-"))} · ${escapeHtml(String(item?.db_type || "").toUpperCase() || "-")}</span>
                      </div>
                    </td>
                    <td class="text-end"><span class="statistics-number">${escapeHtml(String(item?.size_label || formatSize(item?.size_mb)))}</span></td>
                    <td class="text-end"><span class="statistics-subtext">${escapeHtml(formatDateTime(item?.collected_at))}</span></td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderDistributionPanel(options) {
    const container = document.querySelector(options.containerSelector);
    if (!container) {
      return;
    }

    const rows = Array.isArray(options.rows) ? options.rows : [];
    const total = Number(options.total) || 0;
    if (!rows.length) {
      container.innerHTML = renderEmptyState(options.icon, options.emptyText);
      return;
    }

    container.innerHTML = `
      <div class="table-responsive statistics-panel__table">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>${options.headers[0]}</th>
              <th class="text-end">${options.headers[1]}</th>
              <th class="statistics-panel__col-percent">${options.headers[2]}</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map((item) => {
                const percent = resolvePercent(item?.count, total);
                return options.rowRenderer(item, percent);
              })
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderPercentCell(percent, barClass) {
    return `
      <div class="statistics-progress" aria-label="占比 ${percent.toFixed(1)}%">
        <div class="statistics-progress__bar ${barClass}" style="width: ${percent}%"></div>
      </div>
      <span class="statistics-progress__value">${percent.toFixed(1)}%</span>
    `;
  }

  function renderEmptyState(icon, text) {
    return `
      <div class="statistics-empty">
        <i class="fas ${icon}"></i>
        <p>${escapeHtml(text)}</p>
      </div>
    `;
  }

  function setMetricValue(key, value) {
    document.querySelectorAll(`[data-stat-key="${key}"]`).forEach((card) => {
      const node = card.querySelector('[data-role="metric-value"]');
      if (node) {
        node.textContent = value;
      }
    });
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = value;
    }
  }

  function resolvePercent(count, total) {
    const numericCount = Number(count) || 0;
    if (!total || total <= 0) {
      return 0;
    }
    return Math.min(100, Math.max(0, (numericCount / total) * 100));
  }

  function formatInteger(value) {
    if (global.NumberFormat?.formatInteger) {
      return global.NumberFormat.formatInteger(value, { fallback: value || 0 });
    }
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
      return String(value ?? "-");
    }
    return numeric.toLocaleString();
  }

  function formatDecimal(value) {
    if (global.NumberFormat?.formatDecimal) {
      return global.NumberFormat.formatDecimal(value, { precision: 1, trimZero: true, fallback: "0" });
    }
    const numeric = Number(value) || 0;
    return numeric.toFixed(1).replace(/\.0$/, "");
  }

  function formatSize(value) {
    const numeric = Number(value) || 0;
    if (numeric >= 1024) {
      return `${(numeric / 1024).toFixed(2)} GB`;
    }
    return `${numeric.toFixed(0)} MB`;
  }

  function formatDateTime(value) {
    if (!value) {
      return "未采集";
    }
    const formatDateTimeValue = global.TimeUtils?.formatDateTime;
    if (typeof formatDateTimeValue === "function") {
      return formatDateTimeValue(value) || "未采集";
    }
    return String(value);
  }

  function toggleLoading(loading) {
    if (loading) {
      refreshButton.dataset.originalContent = refreshButton.innerHTML;
      refreshButton.setAttribute("disabled", "disabled");
      refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      return;
    }
    refreshButton.innerHTML = refreshButton.dataset.originalContent || '<i class="fas fa-sync-alt"></i>';
    refreshButton.removeAttribute("disabled");
  }

  function notify(message, tone) {
    if (!message) {
      return;
    }
    if (global.toast) {
      if (tone === "success" && global.toast.success) {
        global.toast.success(message);
        return;
      }
      if (tone === "error" && global.toast.error) {
        global.toast.error(message);
        return;
      }
    }
    if (tone === "error") {
      console.error(message);
      return;
    }
    console.info(message);
  }

  function fallbackEscapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
}

window.DatabaseStatisticsPage = {
  mount: function () {
    mountDatabaseStatisticsPage(window);
  },
};
