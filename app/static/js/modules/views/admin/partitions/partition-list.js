(function (global) {
  "use strict";

  const PARTITION_GRID_REFRESH_EVENT = "partitionList:refresh";
  let partitionGrid = null;
  let refreshHandlerBound = false;
  let initialized = false;

  function mount() {
    const helpers = global.DOMHelpers;
    if (!helpers) {
      console.error("DOMHelpers 未初始化，无法挂载分区列表");
      return;
    }
    if (initialized) {
      return;
    }
    initialized = true;
    const { ready } = helpers;
    ready(() => {
      initializeGrid();
      bindRefreshEvent();
    });
  }

  function initializeGrid() {
    const container = document.getElementById("partitions-grid");
    if (!container) {
      console.warn("未找到分区列表容器，跳过 Grid 初始化");
      return;
    }
    if (!global.GridWrapper || !global.gridjs) {
      console.error("Grid.js 或 GridWrapper 未加载，无法初始化分区列表");
      return;
    }
    partitionGrid = new global.GridWrapper(container, {
      columns: buildColumns(),
      server: {
        url: "/partition/api/partitions?sort=date&order=desc",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        then: (response) => {
          const payload = response?.data || response || {};
          const items = payload.items || [];
          return items.map((item) => [
            item.table_type || "unknown",
            item.name || "-",
            item.size || "0 B",
            item.record_count ?? 0,
            item.status || "unknown",
            item,
          ]);
        },
        total: (response) => {
          const payload = response?.data || response || {};
          return payload.total || 0;
        },
      },
    });
    partitionGrid.init();
  }

  function buildColumns() {
    const gridHtml = global.gridjs?.html;
    return [
      {
        name: "表类型",
        id: "table_type",
        formatter: (cell, row) => {
          const meta = resolveRowMeta(row);
          const label = meta.display_name || cell || "未知";
          if (!gridHtml) {
            return label;
          }
          return gridHtml(`<span class="badge bg-secondary">${escapeHtml(label)}</span>`);
        },
      },
      {
        name: "分区名称",
        id: "name",
        formatter: (cell, row) => {
          const meta = resolveRowMeta(row);
          const date = meta.date ? `<div class="text-muted small">${escapeHtml(meta.date)}</div>` : "";
          const text = escapeHtml(cell || "-");
          return gridHtml ? gridHtml(`<div class="fw-semibold">${text}</div>${date}`) : `${text}`;
        },
      },
      {
        name: "大小",
        id: "size",
        formatter: (cell, row) => {
          const meta = resolveRowMeta(row);
          const formatted = cell || meta.size || "0 B";
          if (!gridHtml) {
            return formatted;
          }
          return gridHtml(`<span class="badge bg-light text-dark">${escapeHtml(formatted)}</span>`);
        },
      },
      {
        name: "记录数",
        id: "record_count",
        formatter: (cell) => {
          const count = Number(cell) || 0;
          if (!gridHtml) {
            return count.toLocaleString();
          }
          return gridHtml(`<span class="badge bg-info text-dark">${count.toLocaleString()}</span>`);
        },
      },
      {
        name: "状态",
        id: "status",
        formatter: (cell) => renderStatusBadge(cell, gridHtml),
      },
      {
        id: "__meta__",
        hidden: true,
      },
    ];
  }

  function resolveRowMeta(row) {
    return row?.cells?.[row.cells.length - 1]?.data || {};
  }

  function renderStatusBadge(status, gridHtml) {
    const normalized = (status || "unknown").toLowerCase();
    const meta = {
      current: { color: "success", text: "当前" },
      past: { color: "secondary", text: "历史" },
      future: { color: "info", text: "未来" },
      unknown: { color: "warning", text: "未知" },
    };
    const resolved = meta[normalized] || meta.unknown;
    if (!gridHtml) {
      return resolved.text;
    }
    return gridHtml(`<span class="badge bg-${resolved.color}">${resolved.text}</span>`);
  }

  function escapeHtml(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function bindRefreshEvent() {
    if (refreshHandlerBound) {
      return;
    }
    const handler = () => {
      if (!partitionGrid) {
        return;
      }
      partitionGrid.refresh?.();
    };
    global.addEventListener(PARTITION_GRID_REFRESH_EVENT, handler);
    refreshHandlerBound = true;
  }

  function refresh() {
    if (partitionGrid) {
      partitionGrid.refresh?.();
      return;
    }
    global.dispatchEvent?.(new CustomEvent(PARTITION_GRID_REFRESH_EVENT));
  }

  global.PartitionsListGrid = {
    mount,
    refresh,
  };
})(window);
